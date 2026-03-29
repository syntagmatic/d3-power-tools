#!/usr/bin/env python3
"""Generate blocks using Gemini CLI. Reads manifest.json, outputs to blocks/{version}-{model}/."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from staging import create_staging_dir, cleanup_staging_dir

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

VERSION = args[0] if args else "v0"
ONLY_IDS = set(args[1:]) if len(args) > 1 else None

OUTDIR = PROJ / "blocks" / VERSION
LOGFILE = PROJ / "temp" / f"generate-blocks-gemini-{VERSION}.log"

OUTDIR.mkdir(parents=True, exist_ok=True)

TIMEOUT_S = 600


def run_block(idx, block):
    bid = block["id"]
    outfile = OUTDIR / f"{bid}.html"

    if outfile.exists() and outfile.stat().st_size > 0:
        print(f"[{idx}] SKIP {bid} (exists)")
        return None

    skills_list = [] if no_skills else block["skills"]
    staging = create_staging_dir(bid, skills_list, PROJ, all_skills=all_skills, prefix=VERSION)

    # Write to staging dir, then copy out
    staging_outfile = staging / f"{bid}.html"
    prompt = (
        f"Build this D3.js visualization and save it as {bid}.html\n\n"
        f"IMPORTANT: The output file must contain ONLY valid HTML starting with "
        f"<!DOCTYPE html>. Do not include any markdown fences or explanation.\n\n"
        f"{block['prompt']}"
    )
    print(f"[{idx}] START {bid}")
    t0 = time.time()

    try:
        cmd = ["gemini", "-p", prompt, "--yolo"]
        if MODEL:
            cmd.extend(["--model", MODEL])
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=TIMEOUT_S,
            cwd=str(staging),
        )
    except subprocess.TimeoutExpired:
        cleanup_staging_dir(staging)
        print(f"[{idx}] TIMEOUT {bid}")
        return {"bid": bid, "status": "fail", "error": "timeout",
                "elapsed_s": TIMEOUT_S}

    elapsed = time.time() - t0

    # Check for rate limit
    if "429" in result.stderr or "RESOURCE_EXHAUSTED" in result.stderr:
        cleanup_staging_dir(staging)
        print(f"[{idx}] THROTTLED {bid} ({elapsed:.0f}s)")
        return {"bid": bid, "status": "fail", "error": "throttled",
                "elapsed_s": round(elapsed, 1)}

    # Copy from staging dir to output dir, then clean up
    if staging_outfile.exists():
        shutil.copy2(staging_outfile, outfile)
    cleanup_staging_dir(staging)

    record = {"bid": bid, "elapsed_s": round(elapsed, 1)}

    # Check output file
    if outfile.exists() and outfile.stat().st_size > 0:
        first_line = outfile.read_text().split("\n")[0].lower()
        if "<!doctype" in first_line or "<html" in first_line:
            lines = len(outfile.read_text().splitlines())
            record["status"] = "pass"
            record["lines"] = lines
            print(f"[{idx}] PASS {bid} ({lines} lines, {elapsed:.0f}s)")
            return record
        else:
            record["status"] = "fail"
            record["error"] = "invalid html"
            print(f"[{idx}] FAIL {bid} (not valid HTML)")
            outfile.unlink()
            return record
    else:
        record["status"] = "fail"
        record["error"] = "no output"
        print(f"[{idx}] FAIL {bid} (no output file)")
        return record


def main():
    manifest = json.loads(MANIFEST.read_text())
    blocks = manifest["blocks"]

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
        futures = {pool.submit(run_block, i + 1, block): block["id"]
                   for i, block in enumerate(missing)}
        for f in as_completed(futures):
            r = f.result()
            if r is not None:
                records.append(r)

    records.sort(key=lambda r: r["bid"])
    counts = {"pass": 0, "fail": 0}
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    # Update generation.json
    gen_file = OUTDIR / "generation.json"
    if gen_file.exists():
        gen = json.loads(gen_file.read_text())
    else:
        model_id = MODEL or "gemini-3-flash-preview"
        skill_mode = "none" if no_skills else "all" if all_skills else "manifest"
        gen = {"model": model_id, "cli": "gemini", "version": VERSION,
               "skill_mode": skill_mode, "block_count": 0, "blocks": {}}
    for r in records:
        entry = {"status": r["status"]}
        for field in ("lines", "elapsed_s", "error"):
            if r.get(field) is not None:
                entry[field] = r[field]
        gen["blocks"][r["bid"]] = entry
    gen["block_count"] = sum(1 for b in gen["blocks"].values() if b.get("status") == "pass")
    gen_file.write_text(json.dumps(gen, indent=2, ensure_ascii=False) + "\n")

    print(f"\n=== DONE ===")
    print(f"Pass: {counts.get('pass', 0)}  Fail: {counts.get('fail', 0)}")
    print(f"Output: {OUTDIR}")
    print(f"Report: {gen_file}")


if __name__ == "__main__":
    main()
