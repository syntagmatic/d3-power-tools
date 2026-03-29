#!/usr/bin/env python3
"""Generate blocks using Claude Code CLI. Reads manifest.json, outputs to blocks/{version}-{model}/."""
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from staging import create_staging_dir, cleanup_staging_dir, parse_skill_reads

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = PROJ / "blocks" / "manifest.json"
MAX_PARALLEL = 5

# Parse args
args = sys.argv[1:]
all_skills = "--all-skills" in args
no_skills = "--no-skills" in args
args = [a for a in args if a not in ("--all-skills", "--no-skills")]
MODEL = None
for i, a in enumerate(args):
    if a == "--model" and i + 1 < len(args):
        MODEL = args[i + 1]
        args = args[:i] + args[i + 2:]
        break

VERSION = args[0] if args else "v1"
ONLY_IDS = set(args[1:]) if len(args) > 1 else None

OUTDIR = PROJ / "blocks" / VERSION
LOGFILE = PROJ / "temp" / f"generate-blocks-claude-{VERSION}.json"

OUTDIR.mkdir(parents=True, exist_ok=True)


def run_block(idx, block, defaults):
    bid = block["id"]
    outfile = OUTDIR / f"{bid}.html"

    if outfile.exists() and outfile.stat().st_size > 0:
        print(f"[{idx}] SKIP {bid} (exists)")
        return None

    suffix = defaults.get("suffix", "")
    abs_outpath = str(outfile)
    prompt = (
        f"Build a standalone D3.js visualization as a single HTML file.\n\n"
        f"{block['prompt']}\n\n"
        f"{suffix}\n"
        f"Generate ALL synthetic data inline. No external data files.\n"
        f"Write the complete file to {abs_outpath}"
    )

    skills_list = [] if no_skills else block["skills"]
    staging = create_staging_dir(bid, skills_list, PROJ, all_skills=all_skills, prefix=VERSION)
    print(f"[{idx}] START {bid} (skills: {', '.join(skills_list) or 'none'})")
    t0 = time.time()

    try:
        cmd = [
            "claude", "-p", prompt,
            "--allowedTools", "Write,Read",
            "--disallowedTools", "Bash,Glob,Grep,Agent",
            "--max-turns", "25",
            "--output-format", "stream-json",
            "--verbose",
        ]
        if MODEL:
            cmd.extend(["--model", MODEL])
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=300,
            cwd=str(staging),
        )
    except subprocess.TimeoutExpired:
        print(f"[{idx}] TIMEOUT {bid}")
        return {"bid": bid, "status": "fail", "error": "timeout",
                "skills_requested": block["skills"], "skills_triggered": [],
                "skills_missed": block["skills"], "elapsed_s": 300}
    finally:
        cleanup_staging_dir(staging)

    elapsed = time.time() - t0

    # Parse which skills were read
    triggered = parse_skill_reads(result.stdout)
    record = {
        "bid": bid,
        "skills_requested": block["skills"],
        "skills_triggered": triggered,
        "skills_missed": [s for s in block["skills"] if s not in triggered],
        "elapsed_s": round(elapsed, 1),
    }

    # Check output file
    if outfile.exists() and outfile.stat().st_size > 100:
        content = outfile.read_text()
        first_line = content.split("\n")[0].lower()
        if "<!doctype" in first_line or "<html" in first_line:
            lines = len(content.splitlines())
            record["status"] = "pass"
            record["lines"] = lines
            print(f"[{idx}] PASS {bid} ({lines} lines, {elapsed:.0f}s, read: {triggered})")
            return record
        else:
            record["status"] = "fail"
            record["error"] = "invalid html"
            print(f"[{idx}] FAIL {bid} (not valid HTML)")
            outfile.unlink()
            return record
    else:
        record["status"] = "fail"
        # With stream-json, errors are in stdout; stderr may be empty
        err_content = result.stderr[:2000] if result.stderr else ""
        if not err_content and result.stdout:
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                    if event.get("type") == "result" and event.get("is_error"):
                        err_content = event.get("result", "unknown error")
                        break
                except (json.JSONDecodeError, ValueError):
                    pass
        record["error"] = err_content or "no output"
        print(f"[{idx}] FAIL {bid} (no output file)")
        return record


def main():
    manifest = json.loads(MANIFEST.read_text())
    blocks = manifest["blocks"]
    defaults = manifest.get("defaults", {})

    if ONLY_IDS:
        blocks = [b for b in blocks if b["id"] in ONLY_IDS]

    # Filter to only missing blocks
    missing = [b for b in blocks if not (OUTDIR / f"{b['id']}.html").exists()]
    mode = "no skills" if no_skills else "all skills" if all_skills else "manifest skills"
    print(f"{len(missing)} blocks to generate (of {len(blocks)} selected), {mode}, up to {MAX_PARALLEL} parallel\n")

    if not missing:
        print("All blocks already exist. Done.")
        return

    records = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {}
        for i, block in enumerate(missing):
            f = pool.submit(run_block, i + 1, block, defaults)
            futures[f] = block["id"]

        for f in as_completed(futures):
            r = f.result()
            if r is not None:
                records.append(r)

    records.sort(key=lambda r: r["bid"])
    counts = {"pass": 0, "fail": 0}
    all_missed = []
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        all_missed.extend(r.get("skills_missed", []))

    missed_counts = Counter(all_missed)

    report = {
        "version": VERSION,
        "mode": "all_skills" if all_skills else "manifest_only",
        "summary": counts,
        "skills_missed_counts": dict(missed_counts.most_common()),
        "blocks": records,
    }

    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    LOGFILE.write_text(json.dumps(report, indent=2) + "\n")

    # Update generation.json in the output directory
    gen_file = OUTDIR / "generation.json"
    if gen_file.exists():
        gen = json.loads(gen_file.read_text())
    else:
        model_id = MODEL or "claude-opus-4-6"
        skill_mode = "none" if no_skills else "all" if all_skills else "manifest"
        gen = {"model": model_id, "cli": "claude", "version": VERSION,
               "skill_mode": skill_mode, "block_count": 0, "blocks": {}}
    for r in records:
        if r["status"] == "pass":
            entry = {"status": "pass", "lines": r.get("lines"),
                     "skills_triggered": r.get("skills_triggered", []),
                     "elapsed_s": r.get("elapsed_s")}
            gen["blocks"][r["bid"]] = entry
    gen["block_count"] = len(gen["blocks"])
    gen_file.write_text(json.dumps(gen, indent=2, ensure_ascii=False) + "\n")

    print(f"\n=== DONE ===")
    print(f"Pass: {counts.get('pass', 0)}  Fail: {counts.get('fail', 0)}")
    if missed_counts:
        print(f"Skills never read: {dict(missed_counts.most_common(10))}")
    print(f"Output: {OUTDIR}")
    print(f"Report: {LOGFILE}")


if __name__ == "__main__":
    main()
