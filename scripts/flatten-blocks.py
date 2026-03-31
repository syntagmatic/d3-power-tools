#!/usr/bin/env python3
"""Flatten blocks/ to a single directory with archive.

For each block, picks the best version (by audit composite, then priority
order), copies it to blocks/{id}.html, and moves all block-set directories
to blocks/archive/.

Usage:
  python3 scripts/flatten-blocks.py --dry-run     # preview what would happen
  python3 scripts/flatten-blocks.py               # do it
"""
import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
BEST_FILE = PROJ / "evals" / "best-blocks.json"
RUNS_DIR = PROJ / "evals" / "runs"

# Priority order when no scores exist — prefer opus, then sonnet, then gemini
PRIORITY = [
    "standalone",
    "v2-claude-opus-4-6",
    "v0-claude-opus-4-6",
    "v2-claude-sonnet-4-6",
    "v1-claude-sonnet-4-6",
    "v2-gemini-3.1-pro-preview",
    "v1-gemini-3-flash-preview",
    "v0-gemini-3-flash-preview",
    "v2-claude-opus-4-6-noskills",
    "v2-claude-sonnet-4-6-noskills",
    "v2-gemini-3.1-pro-preview-noskills",
]

ARCHIVE_DIR = PROJ / "blocks" / "archive"
SKIP_DIRS = {"archive", "standalone"}  # standalone gets merged, not archived separately


def find_all_versions():
    """Find all HTML files per block across all block-sets."""
    versions = defaultdict(dict)  # bid -> {block_set: path}
    blocks_dir = PROJ / "blocks"
    for d in sorted(blocks_dir.iterdir()):
        if not d.is_dir() or d.name in ("archive",):
            continue
        for f in d.glob("*.html"):
            versions[f.stem][d.name] = f
    return versions


def load_scores():
    """Load best composite per (block_id, block_set) from run files."""
    scores = defaultdict(lambda: defaultdict(list))
    for f in sorted(RUNS_DIR.glob("*.json")):
        try:
            run = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        bs = run.get("block_set", "")
        for bid, entry in run.get("blocks", {}).items():
            if entry.get("composite") is not None:
                scores[bid][bs].append(entry["composite"])
    # Median per (bid, bs)
    result = {}
    for bid, bs_scores in scores.items():
        result[bid] = {}
        for bs, vals in bs_scores.items():
            vals.sort()
            result[bid][bs] = vals[len(vals) // 2]
    return result


def pick_best(bid, versions, scores, best_blocks):
    """Pick the best version of a block. Returns (block_set, path, reason)."""
    # 1. Check best-blocks.json
    if bid in best_blocks:
        bs = best_blocks[bid].get("block_set", "")
        if bs in versions:
            return bs, versions[bs], f"best-blocks.json (composite {best_blocks[bid].get('composite', '?')})"

    # 2. Pick by highest audit composite
    bid_scores = scores.get(bid, {})
    if bid_scores:
        # Only consider block-sets we actually have
        available = {bs: score for bs, score in bid_scores.items() if bs in versions}
        if available:
            best_bs = max(available, key=lambda bs: available[bs])
            return best_bs, versions[best_bs], f"highest composite ({available[best_bs]:.1f})"

    # 3. Fall back to priority order
    for bs in PRIORITY:
        if bs in versions:
            return bs, versions[bs], "priority order (no scores)"

    # 4. Take whatever exists
    bs = next(iter(versions))
    return bs, versions[bs], "only version"


def main():
    ap = argparse.ArgumentParser(description="Flatten blocks to single directory")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    versions = find_all_versions()
    scores = load_scores()
    best_blocks = json.loads(BEST_FILE.read_text()) if BEST_FILE.exists() else {}

    print(f"Found {len(versions)} unique blocks across {len(set(bs for v in versions.values() for bs in v))} directories\n")

    # Skip non-manifest blocks (like generation.json artifacts)
    manifest_ids = {b["id"] for b in MANIFEST["blocks"]}

    picks = []
    for bid in sorted(versions.keys()):
        if bid not in manifest_ids:
            continue
        block_versions = versions[bid]
        bs, path, reason = pick_best(bid, block_versions, scores, best_blocks)
        picks.append((bid, bs, path, reason))

    # Report
    source_counts = defaultdict(int)
    reason_counts = defaultdict(int)
    for bid, bs, path, reason in picks:
        source_counts[bs] += 1
        reason_counts[reason.split("(")[0].strip()] += 1
        if args.dry_run:
            print(f"  {bid:45s} ← {bs:30s} ({reason})")

    print(f"\n=== Summary ===")
    print(f"Blocks to flatten: {len(picks)}")
    print(f"\nBy source:")
    for bs, n in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {bs}: {n}")
    print(f"\nBy selection reason:")
    for reason, n in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {n}")

    if args.dry_run:
        print("\nDRY RUN — no changes made")
        return

    # Execute
    blocks_dir = PROJ / "blocks"
    ARCHIVE_DIR.mkdir(exist_ok=True)

    # Copy best versions to blocks/{id}.html
    for bid, bs, path, reason in picks:
        dest = blocks_dir / f"{bid}.html"
        shutil.copy2(path, dest)

    print(f"\nCopied {len(picks)} blocks to blocks/")

    # Move block-set directories to archive
    moved = 0
    for d in sorted(blocks_dir.iterdir()):
        if not d.is_dir():
            continue
        if d.name in ("archive",) or d == ARCHIVE_DIR:
            continue
        # Don't archive manifest.json, GENERATE.md, etc.
        dest = ARCHIVE_DIR / d.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(d), str(dest))
        moved += 1
        print(f"  Archived: {d.name}/")

    # Move loose non-HTML files back (manifest.json, GENERATE.md)
    for f in ARCHIVE_DIR.parent.glob("*"):
        if f.is_file() and not f.name.endswith(".html"):
            pass  # already in blocks/, leave them

    print(f"\nArchived {moved} directories to blocks/archive/")
    print(f"blocks/ now has {len(list(blocks_dir.glob('*.html')))} HTML files + archive/")


if __name__ == "__main__":
    main()
