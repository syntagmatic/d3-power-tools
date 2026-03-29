#!/usr/bin/env python3
"""Generate blocks using Claude Code CLI. Reads manifest.json, outputs to blocks/{version}/."""
import json
import subprocess
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = PROJ / "blocks" / "manifest.json"
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v1"
OUTDIR = PROJ / "blocks" / VERSION
LOGFILE = PROJ / "temp" / f"generate-blocks-claude-{VERSION}.log"
MAX_PARALLEL = 5

# Optional: only generate specific block IDs (pass as args after version)
ONLY_IDS = set(sys.argv[2:]) if len(sys.argv) > 2 else None

OUTDIR.mkdir(parents=True, exist_ok=True)


def run_block(idx, block, defaults):
    bid = block["id"]
    outfile = OUTDIR / f"{bid}.html"

    if outfile.exists() and outfile.stat().st_size > 0:
        print(f"[{idx}] SKIP {bid} (exists)")
        return ("skip", bid)

    skills = ", ".join(block["skills"])
    suffix = defaults.get("suffix", "")
    prompt = (
        f"Build a standalone D3.js visualization as a single HTML file.\n"
        f"Skills to use: {skills}\n\n"
        f"{block['prompt']}\n\n"
        f"{suffix}\n"
        f"Generate ALL synthetic data inline. No external data files.\n"
        f"Write the complete file to blocks/{VERSION}/{bid}.html"
    )

    print(f"[{idx}] START {bid}")
    t0 = time.time()

    try:
        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--allowedTools", "Write,Read,Bash",
                "--max-turns", "3",
            ],
            capture_output=True, text=True, timeout=300,
            cwd=str(PROJ),
        )
    except subprocess.TimeoutExpired:
        print(f"[{idx}] TIMEOUT {bid}")
        return ("fail", bid, "timeout")

    elapsed = time.time() - t0

    # Check output file
    if outfile.exists() and outfile.stat().st_size > 100:
        content = outfile.read_text()
        first_line = content.split("\n")[0].lower()
        if "<!doctype" in first_line or "<html" in first_line:
            lines = len(content.splitlines())
            print(f"[{idx}] PASS {bid} ({lines} lines, {elapsed:.0f}s)")
            return ("pass", bid)
        else:
            print(f"[{idx}] FAIL {bid} (not valid HTML)")
            outfile.unlink()
            return ("fail", bid, "invalid html")
    else:
        print(f"[{idx}] FAIL {bid} (no output file)")
        errfile = OUTDIR / f".{bid}.stderr"
        errfile.write_text(result.stderr[:2000] if result.stderr else "no stderr")
        return ("fail", bid, "no file")


def main():
    manifest = json.loads(MANIFEST.read_text())
    blocks = manifest["blocks"]
    defaults = manifest.get("defaults", {})

    if ONLY_IDS:
        blocks = [b for b in blocks if b["id"] in ONLY_IDS]

    # Filter to only missing blocks
    missing = [b for b in blocks if not (OUTDIR / f"{b['id']}.html").exists()]
    print(f"{len(missing)} blocks to generate (of {len(blocks)} selected), up to {MAX_PARALLEL} parallel\n")

    if not missing:
        print("All blocks already exist. Done.")
        return

    results = {"pass": 0, "fail": 0, "skip": 0}
    log_lines = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {}
        for i, block in enumerate(missing):
            f = pool.submit(run_block, i + 1, block, defaults)
            futures[f] = block["id"]

        for f in as_completed(futures):
            r = f.result()
            status = r[0]
            results[status] += 1
            log_lines.append(f"{r[1]}: {status}")

    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    LOGFILE.write_text("\n".join(sorted(log_lines)) + "\n")

    print(f"\n=== DONE ===")
    print(f"Pass: {results['pass']}  Fail: {results['fail']}  Skip: {results['skip']}")
    print(f"Output: {OUTDIR}")
    print(f"Log: {LOGFILE}")


if __name__ == "__main__":
    main()
