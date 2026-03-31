#!/usr/bin/env python3
"""Measure FPS during interactions for D3 blocks.

Loads a block, injects a rAF frame counter, performs sustained interactions
(brush, drag, pan), and reports min/median/p5 FPS over the interaction window.

Usage:
  python3 scripts/bench-fps.py blocks/standalone/blockbuilder.html
  python3 scripts/bench-fps.py blocks/standalone/blockbuilder.html --interactions brush,drag
  python3 scripts/bench-fps.py --all --block-set v2-claude-opus-4-6
  python3 scripts/bench-fps.py --all --block-set standalone --out evals/block-fps.json
"""
import argparse
import http.server
import json
import socket
import statistics
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())

# JS injected into page to measure performance via PerformanceObserver
# Captures long tasks (>50ms) and uses a rAF loop to measure frame delivery
FPS_INJECT = """
window.__perfData = { frameTimes: [], longTasks: [] };
window.__perfRunning = false;

// Long task observer — catches any JS execution >50ms
if (typeof PerformanceObserver !== 'undefined') {
    try {
        const obs = new PerformanceObserver(list => {
            if (!window.__perfRunning) return;
            for (const entry of list.getEntries()) {
                window.__perfData.longTasks.push(entry.duration);
            }
        });
        obs.observe({ entryTypes: ['longtask'] });
    } catch(e) {}
}

window.__fpsStart = () => {
    window.__perfData = { frameTimes: [], longTasks: [] };
    window.__perfRunning = true;
    let last = performance.now();
    function tick() {
        if (!window.__perfRunning) return;
        const now = performance.now();
        window.__perfData.frameTimes.push(now - last);
        last = now;
        requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
};
window.__fpsStop = () => {
    window.__perfRunning = false;
};
"""

# JS to collect results
FPS_COLLECT = """() => {
    window.__fpsStop();
    const data = window.__perfData;
    if (!data.frameTimes.length) return null;

    // Frame delivery times → FPS
    const deltas = data.frameTimes.filter(d => d > 0);
    const fps = deltas.map(d => 1000 / d);
    fps.sort((a, b) => a - b);
    deltas.sort((a, b) => a - b);

    const pct = (arr, p) => arr[Math.floor(arr.length * p)] || 0;
    const mean = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    // Jank = frames taking >33ms (below 30fps)
    const jankFrames = deltas.filter(d => d > 33);
    // Stutter = frames taking >100ms
    const stutterFrames = deltas.filter(d => d > 100);

    return {
        frames: deltas.length,
        fps_median: pct(fps, 0.5),
        fps_p5: pct(fps, 0.05),
        fps_min: fps[0] || 0,
        frame_ms_median: pct(deltas, 0.5),
        frame_ms_p95: pct(deltas, 0.95),
        frame_ms_max: deltas[deltas.length - 1] || 0,
        jank_count: jankFrames.length,
        jank_pct: (jankFrames.length / deltas.length) * 100,
        stutter_count: stutterFrames.length,
        long_tasks: data.longTasks.length,
        long_task_max_ms: data.longTasks.length ? Math.max(...data.longTasks) : 0,
    };
}"""

INTERACTION_DURATION_MS = 2000  # how long to sustain each interaction
SETTLE_MS = 1000  # wait after load before measuring


def find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(directory, port):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        def log_message(self, *_):
            pass
    httpd = http.server.HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def run_interaction(page, interaction, duration_ms):
    """Perform a sustained interaction for duration_ms.

    Starts rAF frame counter, performs Playwright mouse actions (which
    correctly trigger d3 event handlers), then stops counter.
    """
    vp = page.viewport_size
    cx, cy = vp["width"] // 2, vp["height"] // 2
    steps = max(duration_ms // 16, 30)  # ~60fps worth of mouse moves

    # Start measurement before interaction
    page.evaluate("window.__fpsStart()")

    if interaction == "brush":
        page.mouse.move(cx - 150, cy - 100)
        page.mouse.down()
        page.mouse.move(cx + 150, cy + 100, steps=steps)
        page.wait_for_timeout(200)
        page.mouse.move(cx, cy, steps=steps // 2)
        page.mouse.up()

    elif interaction == "drag":
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + 200, cy + 100, steps=steps)
        page.mouse.move(cx - 100, cy - 50, steps=steps // 2)
        page.mouse.up()

    elif interaction == "pan":
        page.mouse.move(cx, cy)
        for _ in range(steps // 5):
            page.mouse.wheel(0, -30)
            page.wait_for_timeout(16)
        for _ in range(steps // 5):
            page.mouse.wheel(0, 30)
            page.wait_for_timeout(16)

    elif interaction == "hover":
        for i in range(steps):
            dx = (i * 400) // steps - 200
            dy = (i * 200) // steps - 100
            page.mouse.move(cx + dx, cy + dy)

    else:
        page.wait_for_timeout(duration_ms)


def bench_block(html_path, interactions, wait_for="svg", timeout=10000):
    """Measure FPS for a block across interactions. Returns dict of results."""
    html_path = Path(html_path).resolve()
    port = find_free_port()
    httpd = start_server(str(html_path.parent), port)
    results = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 800})

            url = f"http://127.0.0.1:{port}/{html_path.name}"
            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Wait for viz to render
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=timeout)
                except Exception:
                    pass

            # Let animations settle
            page.wait_for_timeout(SETTLE_MS)

            # Inject FPS counter
            page.evaluate(FPS_INJECT)

            # Measure idle FPS as baseline
            page.evaluate("window.__fpsStart()")
            page.wait_for_timeout(1000)
            idle = page.evaluate(FPS_COLLECT)
            if idle:
                results["idle"] = {k: round(v, 1) if isinstance(v, float) else v
                                   for k, v in idle.items()}

            # Measure each interaction
            for interaction in interactions:
                try:
                    run_interaction(page, interaction, INTERACTION_DURATION_MS)
                    fps_data = page.evaluate(FPS_COLLECT)
                    if fps_data:
                        results[interaction] = {
                            k: round(v, 1) if isinstance(v, float) else v
                            for k, v in fps_data.items()
                        }
                except Exception as e:
                    results[interaction] = {"error": str(e)}

            browser.close()
    finally:
        httpd.shutdown()

    return results


def detect_interactions(block_id, features=None):
    """Guess which interactions to test based on structural features."""
    if features is None:
        feat_file = PROJ / "evals" / "block-features.json"
        if feat_file.exists():
            all_feat = json.loads(feat_file.read_text()).get("blocks", {})
            features = all_feat.get(block_id, {})

    if not features:
        return ["hover"]

    interactions = []
    block_interactions = features.get("interactions", [])
    if "brush" in block_interactions:
        interactions.append("brush")
    if "drag" in block_interactions or "force" in block_interactions:
        interactions.append("drag")
    if "zoom" in block_interactions:
        interactions.append("pan")
    if not interactions:
        interactions.append("hover")
    return interactions


def find_html(block_id, block_set=None):
    sets = [block_set] if block_set else [
        "standalone", "v2-claude-opus-4-6", "v0-claude-opus-4-6",
        "v2-claude-sonnet-4-6", "v1-claude-sonnet-4-6",
    ]
    for bs in sets:
        p = PROJ / "blocks" / bs / f"{block_id}.html"
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="Measure FPS during interactions")
    ap.add_argument("file", nargs="?", help="Single HTML file to benchmark")
    ap.add_argument("--interactions", default=None,
                    help="Comma-separated: brush,drag,pan,hover (auto-detected if omitted)")
    ap.add_argument("--all", action="store_true", help="Benchmark all blocks in manifest")
    ap.add_argument("--blocks", nargs="*", help="Specific block IDs")
    ap.add_argument("--block-set", default=None)
    ap.add_argument("--out", default=None, help="Write results to JSON file")
    ap.add_argument("--timeout", type=int, default=15000)
    args = ap.parse_args()

    if args.file:
        # Single file mode
        interactions = args.interactions.split(",") if args.interactions else ["hover", "brush", "drag"]
        print(f"Benchmarking {args.file}")
        print(f"Interactions: {interactions}\n")
        results = bench_block(args.file, interactions, timeout=args.timeout)
        for name, data in results.items():
            if "error" in data:
                print(f"  {name}: ERROR {data['error']}")
            else:
                print(f"  {name}: {data['fps_median']:.0f}fps med, {data['fps_p5']:.0f}fps p5"
                      f"  frame={data['frame_ms_median']:.1f}/{data['frame_ms_p95']:.1f}ms"
                      f"  jank={data['jank_count']}/{data['frames']}"
                      f"  long_tasks={data['long_tasks']}"
                      f"  ({data['frames']} frames)")
        if args.out:
            Path(args.out).write_text(json.dumps(results, indent=2))
        return

    # Multi-block mode
    if args.all:
        targets = MANIFEST["blocks"]
    elif args.blocks:
        targets = [b for b in MANIFEST["blocks"]
                   for spec in args.blocks if b["id"] == spec or b["id"].startswith(spec)]
    else:
        print("Specify a file, --all, or --blocks"); sys.exit(1)

    all_results = {}
    for b in targets:
        bid = b["id"]
        html = find_html(bid, args.block_set)
        if not html:
            continue

        interactions = (args.interactions.split(",") if args.interactions
                        else detect_interactions(bid))
        wait_for = b.get("wait_for", "svg")

        print(f"{bid} [{','.join(interactions)}]...", end=" ", flush=True)
        try:
            results = bench_block(str(html), interactions, wait_for, args.timeout)
            # Summarize
            worst_jank = 0
            worst_frame = 0
            for name, data in results.items():
                if name == "idle" or "error" in data:
                    continue
                worst_jank = max(worst_jank, data.get("jank_count", 0))
                worst_frame = max(worst_frame, data.get("frame_ms_p95", 0))
            if worst_frame > 0:
                print(f"p95={worst_frame:.1f}ms jank={worst_jank}")
            else:
                print("no interaction data")
            all_results[bid] = results
        except Exception as e:
            print(f"ERROR: {e}")
            all_results[bid] = {"error": str(e)}

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
        print(f"\nWritten to {args.out}")

    # Summary
    worst = []
    for bid, data in all_results.items():
        for name, d in data.items():
            if name != "idle" and isinstance(d, dict) and "jank_count" in d:
                worst.append((bid, name, d["frame_ms_p95"], d["jank_count"], d["long_tasks"]))
    if worst:
        worst.sort(key=lambda x: -x[2])
        print(f"\n=== Heaviest frames (by p95 frame time) ===")
        for bid, interaction, p95, jank, lt in worst[:10]:
            print(f"  {bid}/{interaction}: p95={p95:.1f}ms jank={jank} long_tasks={lt}")


if __name__ == "__main__":
    main()
