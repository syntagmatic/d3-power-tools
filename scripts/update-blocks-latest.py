#!/usr/bin/env python3
"""Merge audit run data into blocks-latest.html inline JSON.

Reads the latest run file for a given block-set, extracts per-block scores,
and patches the inline `const blocks = [...]` data in blocks-latest.html.

Usage:
  python3 scripts/update-blocks-latest.py                              # auto-detect latest runs
  python3 scripts/update-blocks-latest.py --run evals/runs/2026-03-31T0800-v0-claude-opus-4-6-sonnet.json --variant v0_opus
"""
import argparse
import json
import re
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
HTML_FILE = PROJ / "blocks-latest.html"
RUNS_DIR = PROJ / "evals" / "runs"

# Map run block-set names to variant keys in blocks-latest data
VARIANT_MAP = {
    "v0-claude-opus-4-6": "v0_opus",
    "v0-gemini-3-flash-preview": "v0_gemini",
    "v1-claude-sonnet-4-6": "v1_sonnet",
    "v1-gemini-3-flash-preview": "v1_gemini",
    "v2-claude-opus-4-6": "v2_opus",
    "v2-claude-sonnet-4-6": "v2_sonnet",
    "v2-gemini-3.1-pro-preview": "v2_gemini",
    "v2-claude-opus-4-6-noskills": "v2_opus_noskills",
    "v2-claude-sonnet-4-6-noskills": "v2_sonnet_noskills",
    "v2-gemini-3.1-pro-preview-noskills": "v2_gemini_noskills",
}

AUDIT_FIELDS = [
    "visual_critic", "encoding_integrity", "stress_test", "cognitive_load",
    "composite",
    "visual_critic_note", "encoding_integrity_note", "stress_test_note", "cognitive_load_note",
]


def load_inline_blocks(html):
    """Extract the blocks array from inline JS."""
    m = re.search(r'const blocks = (\[.*?\]);\s*\n', html, re.DOTALL)
    if not m:
        print("ERROR: Could not find 'const blocks = [...]' in HTML")
        sys.exit(1)
    return json.loads(m.group(1)), m.start(1), m.end(1)


def merge_run(blocks, run_data, variant_key):
    """Merge audit scores from a run into the blocks array."""
    updated = 0
    for block in blocks:
        bid = block["id"]
        run_block = run_data.get("blocks", {}).get(bid)
        if not run_block:
            continue

        # Build variant entry
        entry = block.get(variant_key, {})
        if isinstance(entry, str):
            # Was just "pass"/"fail" string — upgrade to dict
            entry = {"status": entry}

        entry["audit_render"] = run_block.get("render", False)
        for field in AUDIT_FIELDS:
            val = run_block.get(field)
            if val is not None:
                entry[f"audit_{field}"] = val

        block[variant_key] = entry
        updated += 1

    return updated


def find_latest_runs():
    """Find the most recent run file for each block-set."""
    latest = {}
    for f in sorted(RUNS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        bs = data.get("block_set", "")
        if bs in VARIANT_MAP:
            latest[bs] = (f, data)
    return latest


def main():
    ap = argparse.ArgumentParser(description="Update blocks-latest.html with audit scores")
    ap.add_argument("--run", help="Specific run file to merge")
    ap.add_argument("--variant", help="Variant key (e.g. v0_opus)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    html = HTML_FILE.read_text()
    blocks, start, end = load_inline_blocks(html)
    print(f"Loaded {len(blocks)} blocks from blocks-latest.html")

    if args.run:
        run_data = json.loads(Path(args.run).read_text())
        variant = args.variant or VARIANT_MAP.get(run_data.get("block_set", ""))
        if not variant:
            print(f"ERROR: Can't determine variant for block_set '{run_data.get('block_set')}'")
            print(f"Known: {list(VARIANT_MAP.keys())}")
            sys.exit(1)
        n = merge_run(blocks, run_data, variant)
        print(f"  {variant}: merged {n} blocks from {args.run}")
    else:
        # Auto-detect latest runs
        latest = find_latest_runs()
        if not latest:
            print("No run files found in evals/runs/"); sys.exit(1)
        total = 0
        for bs, (f, data) in sorted(latest.items()):
            variant = VARIANT_MAP[bs]
            n = merge_run(blocks, data, variant)
            total += n
            print(f"  {variant}: merged {n} blocks from {f.name}")
        print(f"Total: {total} block-variant scores merged")

    if args.dry_run:
        print("DRY RUN — not writing")
        return

    # Write back
    new_json = json.dumps(blocks, ensure_ascii=False, separators=(",", ":"))
    new_html = html[:start] + new_json + html[end:]
    HTML_FILE.write_text(new_html)
    print(f"Written to {HTML_FILE}")


if __name__ == "__main__":
    main()
