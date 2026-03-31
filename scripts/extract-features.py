#!/usr/bin/env python3
"""Extract structural features from block HTML files via static analysis.

Outputs evals/block-features.json — deterministic, re-runnable anytime.

Usage:
  python3 scripts/extract-features.py                        # all blocks
  python3 scripts/extract-features.py --blocks 04 22 55      # specific blocks
"""
import argparse
import json
import re
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
FEATURES_FILE = PROJ / "evals" / "block-features.json"

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

# D3 scale constructors
D3_SCALES = [
    "scaleLinear", "scaleLog", "scaleSqrt", "scalePow", "scaleSymlog",
    "scaleTime", "scaleUtc", "scaleBand", "scalePoint", "scaleOrdinal",
    "scaleSequential", "scaleDiverging", "scaleThreshold", "scaleQuantize",
    "scaleQuantile",
]

# D3 layout / simulation constructors
D3_LAYOUTS = [
    "forceSimulation", "tree", "cluster", "treemap", "pack", "partition",
    "stratify", "hierarchy", "chord", "sankey", "stack", "pie",
]

# D3 shape generators
D3_GENERATORS = [
    "arc", "line", "area", "ribbon", "lineRadial", "areaRadial",
    "curveBundle", "geoPath", "linkHorizontal", "linkVertical", "linkRadial",
    "symbol",
]

# D3 interaction constructors
D3_INTERACTIONS = {
    "brush": r"d3\.brush(?:X|Y)?\(",
    "zoom": r"d3\.zoom\(",
    "drag": r"d3\.drag\(",
    "dispatch": r"d3\.dispatch\(",
    "force": r"d3\.forceSimulation",
}


def find_html(block_id):
    for bs in BLOCK_SETS:
        p = PROJ / "blocks" / bs / f"{block_id}.html"
        if p.exists():
            return p
    return None


def extract(block_id, html_path):
    code = html_path.read_text()
    lines = len(code.splitlines())

    # --- Size & complexity ---
    d3_calls = set(re.findall(r"d3\.(\w+)", code))
    d3_api_count = len(d3_calls)

    scales_found = [s for s in D3_SCALES if s in d3_calls]
    scale_count = len(scales_found)

    event_matches = re.findall(r'\.on\(["\'](\w+)', code)
    event_types = sorted(set(event_matches))
    event_handler_count = len(event_types)

    # Count function declarations and arrow functions (rough proxy)
    fn_keyword = len(re.findall(r"\bfunction\b", code))
    fn_arrow = len(re.findall(r"=>\s*[{(]", code))
    # Also count concise arrows: ) => expr (no brace/paren)
    fn_arrow += len(re.findall(r"=>\s*\w", code))
    function_count = fn_keyword + fn_arrow

    # --- Renderer stack ---
    has_svg = bool(re.search(r"<svg|\.append\([\"']svg", code))
    has_canvas = bool(re.search(r"getContext\([\"']2d", code))
    has_webgl = bool(re.search(r"getContext\([\"']webgl", code))

    if has_webgl:
        renderer = "webgl" if not has_svg else "hybrid"
    elif has_canvas and has_svg:
        renderer = "hybrid"
    elif has_canvas:
        renderer = "canvas"
    else:
        renderer = "svg"

    has_transition = bool(re.search(r"\.transition\(", code))
    has_raf = bool(re.search(r"requestAnimationFrame", code))
    has_timer = bool(re.search(r"d3\.timer|setInterval", code))

    # --- Interaction model ---
    interactions = [name for name, pat in D3_INTERACTIONS.items() if re.search(pat, code)]

    # --- Layout & projection ---
    layouts = [l for l in D3_LAYOUTS if l in d3_calls]
    generators = [g for g in D3_GENERATORS if g in d3_calls]
    scales = scales_found
    has_geo = bool(re.search(r"d3\.geo|topojson", code))

    # --- Accessibility & responsiveness ---
    has_aria = bool(re.search(r"aria-|role=", code))
    has_resize_observer = bool(re.search(r"ResizeObserver", code))
    has_reduced_motion = bool(re.search(r"prefers-reduced-motion", code))
    has_container_query = bool(re.search(r"container-type", code))

    # --- External dependencies ---
    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)', code)
    external_libs = [s for s in script_srcs if "d3" not in s.split("/")[-1].lower() or "d3" not in s]
    # Filter to just lib names
    lib_names = []
    for src in script_srcs:
        name = src.split("/")[-1].split(".")[0].lower()
        if name not in ("d3", ""):
            lib_names.append(name)
    external_libs = sorted(set(lib_names))

    has_fetch = bool(re.search(r"\bfetch\(", code))

    return {
        # Size & complexity
        "lines": lines,
        "d3_api_count": d3_api_count,
        "scale_count": scale_count,
        "event_handler_count": event_handler_count,
        "function_count": function_count,
        # Renderer stack
        "renderer": renderer,
        "has_transition": has_transition,
        "has_raf": has_raf,
        "has_timer": has_timer,
        # Interaction model
        "interactions": sorted(interactions),
        "event_types": event_types,
        # Layout & projection
        "d3_layouts": sorted(layouts),
        "d3_generators": sorted(generators),
        "d3_scales": sorted(scales),
        "has_geo": has_geo,
        # Accessibility & responsiveness
        "has_aria": has_aria,
        "has_resize_observer": has_resize_observer,
        "has_reduced_motion": has_reduced_motion,
        "has_container_query": has_container_query,
        # External dependencies
        "external_libs": external_libs,
        "has_fetch": has_fetch,
    }


def main():
    ap = argparse.ArgumentParser(description="Extract structural features from blocks")
    ap.add_argument("--blocks", nargs="*", help="Specific block IDs or prefixes")
    args = ap.parse_args()

    all_blocks = MANIFEST["blocks"]
    if args.blocks:
        targets = []
        for spec in args.blocks:
            for b in all_blocks:
                if b["id"] == spec or b["id"].startswith(spec):
                    targets.append(b)
    else:
        targets = all_blocks

    results = {}
    for b in targets:
        bid = b["id"]
        html = find_html(bid)
        if not html:
            print(f"  {bid}: no HTML found, skipping")
            continue
        features = extract(bid, html)
        results[bid] = features

    results = dict(sorted(results.items()))

    data = {
        "_schema": {
            "version": 1,
            "description": "Structural features extracted from block HTML via static analysis. Deterministic — re-run anytime with extract-features.py.",
            "features": {
                "lines": "Line count",
                "d3_api_count": "Unique d3.* API calls",
                "scale_count": "Number of d3.scale* instantiations",
                "event_handler_count": "Unique event types bound via .on()",
                "function_count": "Function declarations + arrow functions",
                "renderer": "svg | canvas | webgl | hybrid",
                "has_transition": "Uses .transition()",
                "has_raf": "Uses requestAnimationFrame",
                "has_timer": "Uses d3.timer or setInterval",
                "interactions": "D3 interaction primitives: brush, zoom, drag, dispatch, force",
                "event_types": "Raw event names from .on() bindings",
                "d3_layouts": "D3 layout algorithms used",
                "d3_generators": "D3 shape generators used",
                "d3_scales": "D3 scale types used",
                "has_geo": "Uses d3.geo* or topojson",
                "has_aria": "Has ARIA attributes or role=",
                "has_resize_observer": "Uses ResizeObserver",
                "has_reduced_motion": "Checks prefers-reduced-motion",
                "has_container_query": "Uses CSS container queries",
                "external_libs": "Non-D3 script dependencies",
                "has_fetch": "Uses fetch() API",
            },
        },
        "blocks": results,
    }

    FEATURES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Extracted features for {len(results)} blocks → {FEATURES_FILE}")

    # Summary stats
    renderers = {}
    for f in results.values():
        r = f["renderer"]
        renderers[r] = renderers.get(r, 0) + 1
    print(f"Renderers: {dict(sorted(renderers.items(), key=lambda x: -x[1]))}")

    interaction_counts = {}
    for f in results.values():
        for i in f["interactions"]:
            interaction_counts[i] = interaction_counts.get(i, 0) + 1
    print(f"Interactions: {dict(sorted(interaction_counts.items(), key=lambda x: -x[1]))}")

    lines = [f["lines"] for f in results.values()]
    print(f"Lines: min={min(lines)} max={max(lines)} mean={sum(lines)//len(lines)}")

    api = [f["d3_api_count"] for f in results.values()]
    print(f"D3 API breadth: min={min(api)} max={max(api)} mean={sum(api)//len(api)}")


if __name__ == "__main__":
    main()
