#!/usr/bin/env python3
"""Generate blocks using Gemini CLI. Reads manifest.json, outputs to blocks/{version}/gem/."""
import json
import subprocess
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = PROJ / "blocks" / "manifest.json"
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v0"
OUTDIR = PROJ / "blocks" / VERSION / "gem"
LOGFILE = PROJ / "temp" / f"generate-blocks-gemini-{VERSION}.log"
MAX_PARALLEL = 5

OUTDIR.mkdir(parents=True, exist_ok=True)

def run_block(idx, block):
    bid = block["id"]
    outfile = OUTDIR / f"{bid}.html"

    if outfile.exists() and outfile.stat().st_size > 0:
        print(f"[{idx}] SKIP {bid} (exists)")
        return ("skip", bid)

    prompt = (
        f"Build this D3.js visualization and save it as blocks/{VERSION}/gem/{bid}.html\n\n"
        f"IMPORTANT: The output file must contain ONLY valid HTML starting with "
        f"<!DOCTYPE html>. Do not include any markdown fences or explanation.\n\n"
        f"{block['prompt']}"
    )

    print(f"[{idx}] START {bid}")
    t0 = time.time()

    try:
        result = subprocess.run(
            ["gemini", "-p", prompt, "--sandbox", "--yolo"],
            capture_output=True, text=True, timeout=300,
            cwd=str(PROJ),
        )
    except subprocess.TimeoutExpired:
        print(f"[{idx}] TIMEOUT {bid}")
        return ("fail", bid, "timeout")

    elapsed = time.time() - t0

    # Check for rate limit
    if "429" in result.stderr or "RESOURCE_EXHAUSTED" in result.stderr:
        print(f"[{idx}] THROTTLED {bid} ({elapsed:.0f}s)")
        return ("throttle", bid)

    # Check output file
    if outfile.exists() and outfile.stat().st_size > 0:
        first_line = outfile.read_text().split("\n")[0].lower()
        if "<!doctype" in first_line or "<html" in first_line:
            lines = len(outfile.read_text().splitlines())
            print(f"[{idx}] PASS {bid} ({lines} lines, {elapsed:.0f}s)")
            return ("pass", bid)
        else:
            print(f"[{idx}] FAIL {bid} (not valid HTML)")
            outfile.unlink()
            return ("fail", bid, "invalid html")
    else:
        print(f"[{idx}] FAIL {bid} (no output file)")
        # Save stderr for debugging
        errfile = OUTDIR / f".{bid}.stderr"
        errfile.write_text(result.stderr)
        return ("fail", bid, "no file")


def main():
    manifest = json.loads(MANIFEST.read_text())
    blocks = manifest["blocks"]
    print(f"Generating {len(blocks)} blocks with up to {MAX_PARALLEL} parallel jobs\n")

    results = {"pass": 0, "fail": 0, "skip": 0, "throttle": 0}
    throttle_count = 0
    log_lines = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {}
        for i, block in enumerate(blocks):
            f = pool.submit(run_block, i + 1, block)
            futures[f] = block["id"]

        for f in as_completed(futures):
            r = f.result()
            status = r[0]
            results[status] += 1
            log_lines.append(f"{r[1]}: {status}")

            if status == "throttle":
                throttle_count += 1
                if throttle_count >= 3:
                    print("\n!!! Too many throttles, consider reducing parallelism")

    # Write log
    LOGFILE.write_text("\n".join(sorted(log_lines)) + "\n")

    print(f"\n=== DONE ===")
    print(f"Pass: {results['pass']}  Fail: {results['fail']}  "
          f"Skip: {results['skip']}  Throttled: {results['throttle']}")
    print(f"Output: {OUTDIR}")
    print(f"Log: {LOGFILE}")


if __name__ == "__main__":
    main()
