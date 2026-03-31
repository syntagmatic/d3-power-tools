#!/usr/bin/env python3
"""Batch-tag blocks using an LLM to assign semantic tags and audit hints.

Reads the rubric from evals/block-tags.json (_schema), finds untagged blocks,
calls claude -p for each, merges results back.

Usage:
  python3 scripts/tag-blocks.py                          # tag all untagged
  python3 scripts/tag-blocks.py --blocks 01 02 03        # specific blocks
  python3 scripts/tag-blocks.py --parallel 4             # 4 workers (default)
  python3 scripts/tag-blocks.py --model haiku            # cheaper model
  python3 scripts/tag-blocks.py --dry-run                # print prompt, don't call
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
TAGS_FILE = PROJ / "evals" / "block-tags.json"
CLAUDE_BIN = shutil.which("claude") or "/usr/local/share/npm-global/bin/claude"

MODEL_IDS = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

# Preferred block-set order for finding HTML
BLOCK_SETS = [
    "standalone",
    "v2-claude-opus-4-6",
    "v0-claude-opus-4-6",
    "v2-claude-sonnet-4-6",
    "v1-claude-sonnet-4-6",
    "v2-gemini-3.1-pro-preview",
    "v1-gemini-3-flash-preview",
    "v0-gemini-3-flash-preview",
]

RUBRIC = """You are tagging a D3.js visualization for a scoring/training system.

## Schema

### tags.compositional_ambition (integer 0-4)
How much the viewer must hold in their head simultaneously.
- 0: Formatted values, no spatial encoding (KPI card, big number, Tufte sparkline-as-dataword)
- 1: One positional/shape mapping (Bostock's bar chart, single Circos ring, one Kaplan-Meier curve, one force layout)
- 2: Layered encodings or non-trivial interaction (Bostock's zoomable sunburst, IGV genome browser, Minard's Napoleon march)
- 3: Multiple coordinated views (Bostock's crossfilter flights, SPLOM with linked brush, MultiQC report)
- 4: Multi-view with cross-cutting interaction or morphing (Galaxy genome workbench, hierarchy-bundles with 6 layouts + bundling + morphing)

### tags.encoding_density (integer 1-4)
Effective simultaneous decoding load. Pre-attentive encodings (color category) count less than competing encodings (dual-y axes).
- 1: 1-2 encodings (bar chart: position + length)
- 2: 3-4 encodings (bubble chart: x, y, size, color)
- 3: 5-6 encodings (Minard: x, y, width, color, direction, temperature)
- 4: 7+ encodings (Circos multi-ring, textured treemap)

### tags.encoding_count (integer)
Raw count of data→visual mappings. Count each scale binding: x-position, y-position, color hue, color lightness, size/area, shape, angle/rotation, line width, pattern/texture, opacity, text labels bound to data.

### tags.data_source (enum)
- "inline": all data literal in JS (arrays, generators)
- "static-external": loads a file (CSV, JSON, TopoJSON)
- "self-referential": data from the project itself (manifest, evals, git)
- "live": API fetch, WebSocket, streaming

### audit_hints.runtime_deps (string[])
Browser APIs beyond baseline: "canvas", "webgl", "prefers-reduced-motion", "container-queries", etc. Empty array if none.

### audit_hints.settle_ms (integer)
Milliseconds before a screenshot is meaningful. 0 for static. 500 for force layout settling. 1000+ for animations/streaming.

### audit_hints.required_states (string[])
Interaction states to exercise for a fair audit. Examples: "brush", "hover", "zoom", "expand", "collapse", "drag-rotate", "layout-switch", "toggle", "sort", "filter", "play". Empty array if the default view is sufficient.

## Task

Read the HTML source. Assign all fields. Return ONLY a JSON object, no markdown, no explanation:

{"tags":{"compositional_ambition":<int>,"encoding_density":<int>,"encoding_count":<int>,"data_source":"<enum>"},"audit_hints":{"runtime_deps":[<strings>],"settle_ms":<int>,"required_states":[<strings>]}}"""


def find_html(block_id):
    """Find the best available HTML file for a block."""
    for bs in BLOCK_SETS:
        p = PROJ / "blocks" / bs / f"{block_id}.html"
        if p.exists():
            return p
    return None


def tag_one_block(block_id, html_path, model):
    """Call claude -p to tag a single block. Returns parsed dict or None."""
    prompt = f"""{RUBRIC}

Block ID: {block_id}
HTML file: {html_path}

Read the file, then output the JSON."""

    bare = tempfile.mkdtemp(prefix="tag-")
    try:
        r = subprocess.run(
            [CLAUDE_BIN, "-p", prompt,
             "--allowedTools", "Read",
             "--max-turns", "10",
             "--model", MODEL_IDS.get(model, model),
             "--output-format", "json",
             "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=120, cwd=bare)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"  {block_id}: ERROR {e}")
        return None
    finally:
        try:
            import shutil as sh
            sh.rmtree(bare, ignore_errors=True)
        except OSError:
            pass

    # Parse the LLM response — extract JSON from the result field
    try:
        outer = json.loads(r.stdout)
        result_text = outer.get("result", "")
    except (json.JSONDecodeError, ValueError):
        result_text = r.stdout or ""

    # The result field may itself be a JSON string that needs parsing
    candidates = [result_text]
    if result_text:
        try:
            parsed_inner = json.loads(result_text)
            if isinstance(parsed_inner, dict):
                candidates.insert(0, parsed_inner)
        except (json.JSONDecodeError, ValueError):
            pass
    candidates.append(r.stdout or "")

    for candidate in candidates:
        if isinstance(candidate, dict):
            if "tags" in candidate:
                return candidate
            continue
        if not candidate:
            continue
        # Try to find JSON object boundaries
        start = candidate.find("{")
        end = candidate.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(candidate[start:end])
                if "tags" in data:
                    return data
            except json.JSONDecodeError:
                continue

    print(f"  {block_id}: PARSE FAIL")
    if r.stdout:
        print(f"    stdout: {r.stdout[:200]}")
    return None


def validate(data):
    """Basic validation of tag structure."""
    tags = data.get("tags", {})
    hints = data.get("audit_hints", {})

    ok = True
    if not isinstance(tags.get("compositional_ambition"), int) or not 0 <= tags["compositional_ambition"] <= 4:
        ok = False
    if not isinstance(tags.get("encoding_density"), int) or not 1 <= tags["encoding_density"] <= 4:
        ok = False
    if not isinstance(tags.get("encoding_count"), int) or tags["encoding_count"] < 1:
        ok = False
    if tags.get("data_source") not in ("inline", "static-external", "self-referential", "live"):
        ok = False
    if not isinstance(hints.get("runtime_deps"), list):
        ok = False
    if not isinstance(hints.get("settle_ms"), int):
        ok = False
    if not isinstance(hints.get("required_states"), list):
        ok = False
    return ok


def main():
    ap = argparse.ArgumentParser(description="Batch-tag blocks")
    ap.add_argument("--blocks", nargs="*", help="Specific block IDs or prefixes")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-tag already tagged blocks")
    args = ap.parse_args()

    # Load existing tags
    if TAGS_FILE.exists():
        tags_data = json.loads(TAGS_FILE.read_text())
    else:
        tags_data = {"_schema": {}, "blocks": {}}

    existing = set(tags_data.get("blocks", {}).keys())

    # Determine which blocks to tag
    all_blocks = MANIFEST["blocks"]
    if args.blocks:
        targets = []
        for spec in args.blocks:
            for b in all_blocks:
                if b["id"] == spec or b["id"].startswith(spec):
                    targets.append(b)
    else:
        targets = all_blocks

    # Filter to untagged unless --force
    if not args.force:
        targets = [b for b in targets if b["id"] not in existing]

    # Find HTML files
    work = []
    for b in targets:
        html = find_html(b["id"])
        if html:
            work.append((b["id"], html))
        else:
            print(f"  {b['id']}: no HTML found, skipping")

    print(f"Tagging {len(work)} blocks ({len(existing)} already tagged)")
    print(f"Model: {MODEL_IDS.get(args.model, args.model)}")
    print(f"Parallel: {args.parallel}\n")

    if args.dry_run:
        print("DRY RUN — would tag:")
        for bid, html in work:
            print(f"  {bid} ({html})")
        return

    if not work:
        print("Nothing to tag.")
        return

    # Run in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(tag_one_block, bid, str(html), args.model): bid
                   for bid, html in work}
        for f in as_completed(futures):
            bid = futures[f]
            data = f.result()
            if data and validate(data):
                results[bid] = data
                ca = data["tags"]["compositional_ambition"]
                ed = data["tags"]["encoding_density"]
                ec = data["tags"]["encoding_count"]
                ds = data["tags"]["data_source"]
                print(f"  {bid}: ambition={ca} density={ed} count={ec} source={ds}")
            else:
                print(f"  {bid}: FAILED validation")

    # Merge into tags file
    if results:
        tags_data["blocks"].update(results)
        # Sort blocks by ID for readability
        tags_data["blocks"] = dict(sorted(tags_data["blocks"].items()))
        TAGS_FILE.write_text(json.dumps(tags_data, indent=2, ensure_ascii=False))
        print(f"\nTagged {len(results)}/{len(work)} blocks")
        print(f"Total tagged: {len(tags_data['blocks'])} blocks")
        print(f"Written to: {TAGS_FILE}")
    else:
        print("\nNo blocks tagged successfully.")


if __name__ == "__main__":
    main()
