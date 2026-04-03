#!/usr/bin/env python3
"""Transition evaluator for hierarchy-bundles block.

Clicks through 7 layouts, captures mid-transition frames, runs programmatic
checks on node positions, stitches filmstrips, sends to Sonnet for scoring,
then runs visual_critic if transition score > 5.

Usage:
  python3 scripts/eval-hierarchy-bundles.py blocks/hierarchy-bundles.html
  python3 scripts/eval-hierarchy-bundles.py evals/iterations/prototypes/131-prompt-hierarchy-bundles.html
  python3 scripts/eval-hierarchy-bundles.py path/to/file.html --exp-id 131 --out-dir evals/iterations/filmstrips
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJ = Path(__file__).resolve().parent.parent
CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/usr/local/share/npm-global/bin/claude"
VISUAL_CRITIC_SKILL = PROJ / "meta" / "visual-critic" / "SKILL.md"

FILMSTRIP_DIR = PROJ / "evals" / "iterations" / "filmstrips"
EXPERIMENTS_DIR = PROJ / "evals" / "experiments"
RUNS_FILE = EXPERIMENTS_DIR / "hierarchy-bundles-runs.json"

# Layout buttons we expect — used to filter non-layout buttons
KNOWN_NON_LAYOUT = {"new dataset", "new data", "regenerate", "reset", "randomize",
                     "links behind", "links on top", "links hidden"}

# Mid-transition capture times (ms after click)
CAPTURE_TIMES_MS = [100, 350, 700]

# Rapid-switch delay between clicks (ms)
RAPID_SWITCH_DELAY_MS = 150


def discover_layout_buttons(page):
    """Find layout-switching buttons, filtering out non-layout ones."""
    buttons = page.query_selector_all("button")
    layout_buttons = []
    for btn in buttons:
        text = (btn.text_content() or "").strip()
        if not text:
            continue
        if text.lower() in KNOWN_NON_LAYOUT:
            continue
        # Skip buttons that look like controls (contain slider-like text)
        if any(kw in text.lower() for kw in ("slider", "toggle", "show", "hide", "behind", "on top")):
            continue
        layout_buttons.append((text, btn))
    return layout_buttons


def get_node_rects(page):
    """Extract bounding rects for all visible node elements via getBoundingClientRect."""
    return page.evaluate("""() => {
        // Try common node selectors in order of specificity
        const selectors = [
            'circle', 'rect:not(defs rect)', 'path[d*="A"]',  // arcs
            '.node', '[class*="node"]'
        ];
        // Find the main SVG's primary data group
        const svg = document.querySelector('svg');
        if (!svg) return [];

        // Collect all shape elements that look like data nodes
        const shapes = new Set();
        for (const el of svg.querySelectorAll('circle, rect, path')) {
            // Skip axis elements, grid lines, links/edges
            const parent = el.parentElement;
            if (!parent) continue;
            const pcn = parent.className;
            const cls = (typeof pcn === 'string' ? pcn : pcn?.baseVal || '').toLowerCase();
            const ecn = el.className;
            const elCls = (typeof ecn === 'string' ? ecn : ecn?.baseVal || '').toLowerCase();
            if (cls.includes('axis') || cls.includes('tick') || cls.includes('grid')) continue;
            if (cls.includes('link') || cls.includes('edge') || cls.includes('bundle')) continue;
            if (elCls.includes('link') || elCls.includes('edge') || elCls.includes('bundle')) continue;

            const rect = el.getBoundingClientRect();
            // Skip zero-size or invisible elements
            if (rect.width < 0.5 && rect.height < 0.5) continue;
            // Skip very large elements (likely backgrounds)
            if (rect.width > 800 && rect.height > 800) continue;

            shapes.add(el);
        }

        return Array.from(shapes).map(el => {
            const r = el.getBoundingClientRect();
            return {
                x: r.x, y: r.y, width: r.width, height: r.height,
                cx: r.x + r.width / 2, cy: r.y + r.height / 2,
                tag: el.tagName.toLowerCase()
            };
        });
    }""")


def check_nodes(rects, viewport_width, viewport_height, label=""):
    """Run programmatic checks on node positions. Returns dict of check results."""
    checks = {
        "node_count": len(rects),
        "offscreen": 0,
        "at_origin": 0,
        "too_small": 0,
        "too_large": 0,
        "issues": [],
    }
    if not rects:
        checks["issues"].append("no nodes found")
        return checks

    vw, vh = viewport_width, viewport_height
    center_x, center_y = vw / 2, vh / 2
    origin_threshold = 20  # pixels from center to count as "at origin"

    for r in rects:
        cx, cy = r["cx"], r["cy"]
        w, h = r["width"], r["height"]

        # Offscreen: center is outside viewport with margin
        if cx < -50 or cx > vw + 50 or cy < -50 or cy > vh + 50:
            checks["offscreen"] += 1

        # Clustered at origin/center (svg center, not page origin)
        if abs(cx - center_x) < origin_threshold and abs(cy - center_y) < origin_threshold:
            checks["at_origin"] += 1

        # Too small (collapsed)
        if max(w, h) < 1.0:
            checks["too_small"] += 1

        # Too large (likely a background rect, but flag if many)
        if w > 400 or h > 400:
            checks["too_large"] += 1

    # Flag issues
    n = len(rects)
    if checks["offscreen"] > n * 0.1:
        checks["issues"].append(f"{checks['offscreen']}/{n} nodes offscreen")
    if checks["at_origin"] > n * 0.5:
        checks["issues"].append(f"{checks['at_origin']}/{n} nodes clustered at center")
    if checks["too_small"] > n * 0.3:
        checks["issues"].append(f"{checks['too_small']}/{n} nodes too small")

    return checks


def check_layout_structure(page, layout_label):
    """Check whether the final state actually looks like the named layout.

    Returns {"correct": bool, "reason": str, "details": dict}.
    Uses DOM inspection — what element types are present and how they're arranged.
    """
    label = layout_label.lower()
    data = page.evaluate("""() => {
        const svg = document.querySelector('svg');
        if (!svg) return null;
        const box = svg.getBoundingClientRect();

        const circles = [], rects = [], arcs = [];
        for (const el of svg.querySelectorAll('circle, rect, path')) {
            const pcn = el.parentElement?.className;
            const cls = (typeof pcn === 'string' ? pcn : pcn?.baseVal || '').toLowerCase();
            const ecn = el.className;
            const elCls = (typeof ecn === 'string' ? ecn : ecn?.baseVal || '').toLowerCase();
            if (cls.includes('link') || cls.includes('edge') || cls.includes('bundle')) continue;
            if (elCls.includes('link') || elCls.includes('edge') || elCls.includes('bundle')) continue;
            if (cls.includes('axis') || cls.includes('tick')) continue;

            const r = el.getBoundingClientRect();
            if (r.width < 0.5 && r.height < 0.5) continue;
            if (r.width > 800 && r.height > 800) continue;

            const tag = el.tagName.toLowerCase();
            const entry = {
                cx: r.x + r.width / 2, cy: r.y + r.height / 2,
                w: r.width, h: r.height, tag
            };

            if (tag === 'circle') circles.push(entry);
            else if (tag === 'rect') rects.push(entry);
            else if (tag === 'path') {
                const d = el.getAttribute('d') || '';
                if (d.includes('A') || d.includes('a')) arcs.push(entry);
            }
        }

        // Compute spatial spread
        const all = [...circles, ...rects, ...arcs];
        if (!all.length) return null;
        const xs = all.map(e => e.cx), ys = all.map(e => e.cy);
        const xSpread = Math.max(...xs) - Math.min(...xs);
        const ySpread = Math.max(...ys) - Math.min(...ys);

        // Check for size variance (treemap/icicle rects vary in size)
        const rectSizes = rects.map(r => r.w * r.h);
        const rectSizeVar = rectSizes.length > 1
            ? Math.sqrt(rectSizes.reduce((s, v) => s + (v - rectSizes.reduce((a,b)=>a+b,0)/rectSizes.length)**2, 0) / rectSizes.length)
            : 0;

        // Check for containment (circle pack has nested circles)
        let nestedCircles = 0;
        for (let i = 0; i < circles.length; i++) {
            for (let j = 0; j < circles.length; j++) {
                if (i === j) continue;
                const a = circles[i], b = circles[j];
                if (a.w > b.w * 1.5 &&
                    Math.abs(a.cx - b.cx) < a.w / 2 &&
                    Math.abs(a.cy - b.cy) < a.h / 2) {
                    nestedCircles++;
                    break;
                }
            }
        }

        // Radial distribution: how many nodes are at similar distance from center
        const svgCx = box.x + box.width / 2, svgCy = box.y + box.height / 2;
        const dists = all.map(e => Math.sqrt((e.cx - svgCx)**2 + (e.cy - svgCy)**2));
        const meanDist = dists.reduce((a,b) => a+b, 0) / dists.length;
        const distVar = dists.length > 1
            ? Math.sqrt(dists.reduce((s, d) => s + (d - meanDist)**2, 0) / dists.length) / (meanDist || 1)
            : 0;

        // Rect fill ratio: what fraction of the svg area is covered by rects (treemap indicator)
        const svgArea = box.width * box.height;
        const rectArea = rects.reduce((s, r) => s + r.w * r.h, 0);
        const rectFillRatio = svgArea > 0 ? rectArea / svgArea : 0;

        return {
            circles: circles.length, rects: rects.length, arcs: arcs.length,
            total: all.length,
            xSpread, ySpread,
            nestedCircles,
            distVar,
            rectFillRatio,
            rectSizeVar,
            svgW: box.width, svgH: box.height
        };
    }""")

    if not data:
        return {"correct": False, "reason": "no SVG data found", "details": {}}

    result = {"details": data}

    # Layout-specific checks
    if "pack" in label:
        # Circle pack: should have circles with nesting
        has_circles = data["circles"] > 10
        has_nesting = data["nestedCircles"] > 3
        if has_circles and has_nesting:
            result["correct"] = True
            result["reason"] = f"{data['circles']} circles, {data['nestedCircles']} nested"
        else:
            result["correct"] = False
            result["reason"] = (f"expected nested circles, got {data['circles']} circles "
                               f"({data['nestedCircles']} nested), {data['rects']} rects, {data['arcs']} arcs")

    elif "treemap" in label:
        # Treemap: many rects filling most of the SVG area
        has_rects = data["rects"] > 10
        fills_space = data["rectFillRatio"] > 0.3
        if has_rects and fills_space:
            result["correct"] = True
            result["reason"] = f"{data['rects']} rects, {data['rectFillRatio']:.0%} fill"
        else:
            result["correct"] = False
            result["reason"] = (f"expected space-filling rects, got {data['rects']} rects "
                               f"({data['rectFillRatio']:.0%} fill), {data['circles']} circles")

    elif "sunburst" in label:
        # Sunburst: arc paths arranged radially with low distance variance
        has_arcs = data["arcs"] > 10
        is_radial = data["distVar"] < 0.8
        if has_arcs:
            result["correct"] = True
            result["reason"] = f"{data['arcs']} arcs, dist variance {data['distVar']:.2f}"
        else:
            result["correct"] = False
            result["reason"] = (f"expected arc paths, got {data['arcs']} arcs, "
                               f"{data['circles']} circles, {data['rects']} rects")

    elif "icicle" in label:
        # Icicle/partition: rects arranged in bands (horizontal or vertical)
        has_rects = data["rects"] > 10
        if has_rects:
            result["correct"] = True
            result["reason"] = f"{data['rects']} rects"
        else:
            result["correct"] = False
            result["reason"] = (f"expected rectangular partition, got {data['rects']} rects, "
                               f"{data['circles']} circles, {data['arcs']} arcs")

    elif "dendrogram" in label or "dendro" in label:
        # Dendrogram: tree spread — wide x range, circles or small nodes
        wide_spread = data["xSpread"] > data["svgW"] * 0.4 or data["ySpread"] > data["svgH"] * 0.4
        has_nodes = data["total"] > 10
        if wide_spread and has_nodes:
            result["correct"] = True
            result["reason"] = f"spread {data['xSpread']:.0f}x{data['ySpread']:.0f}, {data['total']} nodes"
        else:
            result["correct"] = False
            result["reason"] = (f"expected wide tree spread, got {data['xSpread']:.0f}x{data['ySpread']:.0f} "
                               f"in {data['svgW']:.0f}x{data['svgH']:.0f}")

    elif "radial" in label:
        # Radial tree: nodes spread radially from center
        is_radial = data["distVar"] < 0.6
        has_nodes = data["total"] > 10
        spread = data["xSpread"] > data["svgW"] * 0.3 and data["ySpread"] > data["svgH"] * 0.3
        if has_nodes and spread:
            result["correct"] = True
            result["reason"] = f"radial spread, dist variance {data['distVar']:.2f}, {data['total']} nodes"
        else:
            result["correct"] = False
            result["reason"] = (f"expected radial spread, got variance {data['distVar']:.2f}, "
                               f"spread {data['xSpread']:.0f}x{data['ySpread']:.0f}")

    elif "force" in label:
        # Force: just needs to have spread nodes (no rigid structure expected)
        has_nodes = data["total"] > 10
        spread = data["xSpread"] > data["svgW"] * 0.2
        if has_nodes and spread:
            result["correct"] = True
            result["reason"] = f"{data['total']} nodes, spread {data['xSpread']:.0f}x{data['ySpread']:.0f}"
        else:
            result["correct"] = False
            result["reason"] = f"expected spread nodes, got {data['total']} nodes"

    else:
        # Unknown layout — skip structural check
        result["correct"] = True
        result["reason"] = f"unknown layout '{label}', skipped structural check"

    return result


def stitch_filmstrip(stitch_page, screenshots, output_path):
    """Stitch multiple screenshot buffers into a horizontal filmstrip using the existing page.

    stitch_page: an open Playwright page (avoids nested sync_playwright contexts)
    screenshots: list of (label, png_bytes)
    output_path: Path to write the filmstrip PNG
    """
    if not screenshots:
        return False

    images_b64 = [
        {"label": label, "data": base64.b64encode(png_bytes).decode("ascii")}
        for label, png_bytes in screenshots
    ]

    result = stitch_page.evaluate("""async (images) => {
        const GAP = 4;
        const LABEL_H = 20;

        const loaded = await Promise.all(images.map(img => {
            return new Promise((resolve, reject) => {
                const i = new Image();
                i.onload = () => resolve({img: i, label: img.label});
                i.onerror = reject;
                i.src = 'data:image/png;base64,' + img.data;
            });
        }));

        if (!loaded.length) return null;

        const h = loaded[0].img.height;
        const totalW = loaded.reduce((s, l) => s + l.img.width, 0) + GAP * (loaded.length - 1);

        const canvas = document.createElement('canvas');
        canvas.width = totalW;
        canvas.height = h + LABEL_H;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        let x = 0;
        ctx.font = '12px system-ui, sans-serif';
        ctx.textAlign = 'center';
        for (const {img, label} of loaded) {
            ctx.drawImage(img, x, LABEL_H);
            ctx.fillStyle = '#666';
            ctx.fillText(label, x + img.width / 2, 14);
            x += img.width + GAP;
        }

        return canvas.toDataURL('image/png').split(',')[1];
    }""", images_b64)

    if result:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(result))
        return True
    return False


def run_visual_critic(html_path, screenshot_path, model="sonnet"):
    """Run the visual_critic audit. Returns {"score": N, "note": "..."} or None."""
    if not VISUAL_CRITIC_SKILL.exists():
        return None

    skill_content = VISUAL_CRITIC_SKILL.read_text()
    out_path = Path(tempfile.mktemp(suffix=".json", prefix="vc-"))
    prompt = f"""Evaluate this D3.js visualization.

## Criteria
{skill_content}

## Task
1. Read the screenshot at {screenshot_path}
2. Read the HTML source at {html_path}
3. Score 1-10 per the criteria. Write JSON to {out_path}

Format: {{"score":<1-10>,"note":"<1 sentence what works or doesn't>"}}
Write the file now. No markdown, no explanation."""

    bare = tempfile.mkdtemp(prefix="vc-")
    try:
        subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--allowedTools", "Read,Write",
             "--max-turns", "25", "--model", model,
             "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=120, cwd=bare)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    finally:
        try:
            os.rmdir(bare)
        except OSError:
            pass

    if out_path.exists() and out_path.stat().st_size > 5:
        try:
            return json.loads(out_path.read_text())
        finally:
            out_path.unlink(missing_ok=True)
    return None


def run_transition_judge(filmstrip_paths, programmatic_report, html_path, model="sonnet"):
    """Send filmstrips + programmatic report to LLM for transition scoring.

    Returns {"score": N, "note": "..."} or None.
    """
    out_path = Path(tempfile.mktemp(suffix=".json", prefix="transition-"))

    # Build the filmstrip file list for the prompt
    filmstrip_lines = "\n".join(f"  - {p}" for p in filmstrip_paths)

    prompt = f"""You are evaluating the transition quality of a D3.js visualization that switches between 7 hierarchical layouts.

## Filmstrip Images

Each filmstrip shows frames captured during a layout transition. The frames are labeled with timestamps (ms after button click). Read each image:

{filmstrip_lines}

## Programmatic Check Results

These are automated checks on node positions at each frame:

{programmatic_report}

## Failure Modes to Watch For

1. **Teleporting**: nodes jump instantly to new positions instead of interpolating smoothly
2. **Origin clustering**: nodes collapse to the center then expand outward
3. **Offscreen flight**: nodes fly in from far outside the viewport
4. **Size instability**: nodes become extremely small or change size drastically mid-transition
5. **Chaotic movement**: nodes move in random/erratic directions rather than along smooth paths
6. **Snapping**: transition appears to jump to the end state (interrupt failure)
7. **Orphaned elements**: nodes disappear or duplicate during transition

## Scoring Scale

| Score | Meaning |
|:-----:|---------|
| 1-2 | Broken: nodes teleport, cluster at origin, or fly from offscreen on most transitions |
| 3-4 | Poor: multiple transitions show teleporting or chaotic movement |
| 5-6 | Acceptable: most transitions are smooth with 1-2 minor glitches |
| 7-8 | Good: all transitions interpolate smoothly, node counts stay consistent |
| 9-10 | Excellent: silky smooth morphing, creative interpolation paths, no artifacts |

## Task

1. Read each filmstrip image above
2. Read the HTML source at {html_path}
3. Consider the programmatic check results
4. Score the overall transition quality 1-10. Write JSON to {out_path}

Format: {{"score":<1-10>,"note":"<2-3 sentences describing transition quality, specific failures>"}}
Write the file now. No markdown, no explanation."""

    bare = tempfile.mkdtemp(prefix="tj-")
    try:
        subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--allowedTools", "Read,Write",
             "--max-turns", "25", "--model", model,
             "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=180, cwd=bare)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    finally:
        try:
            os.rmdir(bare)
        except OSError:
            pass

    if out_path.exists() and out_path.stat().st_size > 5:
        try:
            return json.loads(out_path.read_text())
        finally:
            out_path.unlink(missing_ok=True)
    return None


def evaluate(html_path, exp_id=None, out_dir=None, model="sonnet", viewport=(1200, 900)):
    """Run the full evaluation pipeline. Returns results dict."""
    html_path = Path(html_path).resolve()
    if not html_path.exists():
        print(f"File not found: {html_path}")
        return None

    out_dir = Path(out_dir) if out_dir else FILMSTRIP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    tag = f"{exp_id:03d}" if exp_id is not None else html_path.stem
    vw, vh = viewport

    results = {
        "html_path": str(html_path),
        "exp_id": exp_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "transitions": {},
        "rapid_switch": {},
        "bundling": {},
        "interaction": {},
        "filmstrip_paths": [],
        "programmatic_report": "",
        "transition_score": None,
        "transition_note": None,
        "visual_critic_score": None,
        "visual_critic_note": None,
        "composite": None,
    }

    # Start HTTP server and browser
    import http.server
    import threading
    serve_dir = str(html_path.parent)
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=serve_dir, **kw)
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/{html_path.name}"

    print(f"=== Evaluating: {html_path.name} ===")
    print(f"  Serving at {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": vw, "height": vh})
        # Utility page for filmstrip stitching (avoids polluting the viz page)
        stitch_page = browser.new_page()

        # Collect JS errors
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)  # let initial render settle

        # Take initial screenshot
        initial_ss = page.screenshot()

        # Discover layout buttons
        layout_buttons = discover_layout_buttons(page)
        button_count = len(layout_buttons)
        print(f"  Found {button_count} layout buttons: {[t for t, _ in layout_buttons]}")

        if button_count < 2:
            print("  ERROR: fewer than 2 layout buttons found")
            results["programmatic_report"] = "ERROR: fewer than 2 layout buttons found"
            browser.close()
            server.shutdown()
            return results

        # --- Phase 1: Per-transition evaluation ---
        report_lines = []
        all_filmstrip_paths = []
        prev_label = "initial"

        for i, (label, btn) in enumerate(layout_buttons):
            print(f"  Transition {i+1}/{button_count}: → {label}")
            transition_data = {"label": label, "frames": [], "checks": []}

            # Capture pre-state rects
            pre_rects = get_node_rects(page)

            # Click and capture mid-transition frames
            frames = []
            btn.click()
            prev_ms = 0

            for delay_ms in CAPTURE_TIMES_MS:
                page.wait_for_timeout(delay_ms - prev_ms)
                prev_ms = delay_ms
                ss = page.screenshot()
                rects = get_node_rects(page)
                checks = check_nodes(rects, vw, vh, f"{label}@{delay_ms}ms")
                frames.append((f"{delay_ms}ms", ss))
                transition_data["frames"].append({"time_ms": delay_ms, "checks": checks})
                transition_data["checks"].append(checks)

            # Wait for transition to fully settle
            page.wait_for_timeout(800)
            final_ss = page.screenshot()
            final_rects = get_node_rects(page)
            final_checks = check_nodes(final_rects, vw, vh, f"{label}@final")
            frames.append(("final", final_ss))
            transition_data["frames"].append({"time_ms": "final", "checks": final_checks})
            transition_data["checks"].append(final_checks)

            # Layout structural correctness check
            structure = check_layout_structure(page, label)
            transition_data["structure"] = structure
            if not structure["correct"]:
                transition_data.setdefault("issues", []).append(
                    f"wrong layout structure: {structure['reason']}")
                print(f"    STRUCTURAL FAIL: {structure['reason']}")

            # Node count consistency
            pre_count = len(pre_rects)
            final_count = final_checks["node_count"]
            if pre_count > 0 and final_count > 0:
                ratio = final_count / pre_count
                if ratio < 0.5 or ratio > 2.0:
                    transition_data.setdefault("issues", []).append(
                        f"node count changed dramatically: {pre_count}→{final_count}")

            # Stitch filmstrip
            filmstrip_name = f"{tag}-{i+1}-{label.lower().replace(' ', '-')}.png"
            filmstrip_path = out_dir / filmstrip_name
            if stitch_filmstrip(stitch_page, frames, filmstrip_path):
                all_filmstrip_paths.append(filmstrip_path)
                transition_data["filmstrip"] = str(filmstrip_path)

            results["transitions"][label] = transition_data

            # Build report section
            report_lines.append(f"\n### Transition: {prev_label} → {label}")
            for frame_data in transition_data["frames"]:
                t = frame_data["time_ms"]
                c = frame_data["checks"]
                issues_str = ", ".join(c["issues"]) if c["issues"] else "ok"
                report_lines.append(
                    f"  {t}: {c['node_count']} nodes, "
                    f"{c['offscreen']} offscreen, {c['at_origin']} at center, "
                    f"{c['too_small']} too small — {issues_str}")
            # Structural check result
            struct_ok = "✓" if structure["correct"] else "✗"
            report_lines.append(f"  Structure: {struct_ok} {structure['reason']}")
            if transition_data.get("issues"):
                report_lines.append(f"  ⚠ {'; '.join(transition_data['issues'])}")

            prev_label = label

        # Count structural failures
        struct_failures = sum(
            1 for t in results["transitions"].values()
            if not t.get("structure", {}).get("correct", True)
        )
        if struct_failures:
            print(f"  {struct_failures}/{len(results['transitions'])} layouts have wrong structure")
        results["structural_failures"] = struct_failures

        # --- Phase 2: Rapid-switch test ---
        print("  Rapid-switch test...")
        if len(layout_buttons) >= 3:
            # Click 3 different layouts in quick succession
            targets = [layout_buttons[0], layout_buttons[len(layout_buttons)//2], layout_buttons[-1]]
            for _, btn in targets:
                btn.click()
                page.wait_for_timeout(RAPID_SWITCH_DELAY_MS)

            # Wait for everything to settle
            page.wait_for_timeout(1500)
            rapid_ss = page.screenshot()
            rapid_rects = get_node_rects(page)
            rapid_checks = check_nodes(rapid_rects, vw, vh, "rapid-switch")
            results["rapid_switch"] = {
                "buttons_clicked": [t for t, _ in targets],
                "checks": rapid_checks,
            }

            # Stitch rapid-switch filmstrip (just before + after)
            rapid_name = f"{tag}-rapid-switch.png"
            rapid_path = out_dir / rapid_name
            stitch_filmstrip(stitch_page, [
                ("before", initial_ss),
                (f"after ({targets[-1][0]})", rapid_ss),
            ], rapid_path)
            if rapid_path.exists():
                all_filmstrip_paths.append(rapid_path)

            report_lines.append(f"\n### Rapid-Switch Test")
            report_lines.append(f"  Clicked: {' → '.join(t for t, _ in targets)} (each {RAPID_SWITCH_DELAY_MS}ms apart)")
            issues_str = ", ".join(rapid_checks["issues"]) if rapid_checks["issues"] else "ok"
            report_lines.append(f"  Result: {rapid_checks['node_count']} nodes — {issues_str}")

        # --- Phase 3: Bundling slider ---
        print("  Bundling slider test...")
        slider = page.query_selector('input[type="range"]')
        if slider:
            # Set to 0
            page.evaluate("el => { el.value = 0; el.dispatchEvent(new Event('input', {bubbles:true})); }", slider)
            page.wait_for_timeout(500)
            bundle_0_ss = page.screenshot()

            # Set to 1
            page.evaluate("el => { el.value = 1; el.dispatchEvent(new Event('input', {bubbles:true})); }", slider)
            page.wait_for_timeout(500)
            bundle_1_ss = page.screenshot()

            bundle_name = f"{tag}-bundling.png"
            bundle_path = out_dir / bundle_name
            stitch_filmstrip(stitch_page, [("beta=0", bundle_0_ss), ("beta=1", bundle_1_ss)], bundle_path)
            if bundle_path.exists():
                all_filmstrip_paths.append(bundle_path)
                results["bundling"]["filmstrip"] = str(bundle_path)

            results["bundling"]["tested"] = True
            report_lines.append(f"\n### Bundling Slider")
            report_lines.append(f"  Tested beta=0 and beta=1")
        else:
            results["bundling"]["tested"] = False
            report_lines.append(f"\n### Bundling Slider")
            report_lines.append(f"  No range slider found")

        # --- Phase 4: Hover/click interaction ---
        print("  Interaction test...")
        # Click first layout to get to a known state
        layout_buttons[0][1].click()
        page.wait_for_timeout(1500)

        # Hover center of SVG
        svg = page.query_selector("svg")
        if svg:
            box = svg.bounding_box()
            if box:
                cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                page.mouse.move(cx, cy)
                page.wait_for_timeout(300)
                hover_ss = page.screenshot()

                page.mouse.click(cx, cy)
                page.wait_for_timeout(300)
                click_ss = page.screenshot()

                interact_name = f"{tag}-interaction.png"
                interact_path = out_dir / interact_name
                stitch_filmstrip(stitch_page, [("hover", hover_ss), ("click", click_ss)], interact_path)
                if interact_path.exists():
                    all_filmstrip_paths.append(interact_path)
                    results["interaction"]["filmstrip"] = str(interact_path)

                results["interaction"]["tested"] = True
                report_lines.append(f"\n### Interaction")
                report_lines.append(f"  Hover + click tested at SVG center")

        # Final screenshot for visual_critic
        final_full_ss_path = out_dir / f"{tag}-final.png"
        final_full_ss_path.write_bytes(page.screenshot())

        browser.close()

    server.shutdown()

    # Compile programmatic report
    programmatic_report = "\n".join(report_lines)
    results["programmatic_report"] = programmatic_report
    results["filmstrip_paths"] = [str(p) for p in all_filmstrip_paths]
    results["js_errors"] = js_errors[:10]

    print(f"\n  Generated {len(all_filmstrip_paths)} filmstrips")
    if js_errors:
        print(f"  JS errors: {len(js_errors)}")

    # --- Phase 5: LLM transition scoring ---
    print(f"  Sending filmstrips to {model} for transition scoring...")
    transition_result = run_transition_judge(
        all_filmstrip_paths, programmatic_report, html_path, model=model)

    if transition_result:
        raw_score = transition_result.get("score")
        results["transition_note"] = transition_result.get("note")
        print(f"  LLM transition score: {raw_score}/10")

        # Penalize for structural failures — layouts that don't match their names
        sf = results.get("structural_failures", 0)
        total_layouts = len(results.get("transitions", {}))
        if sf > 0 and total_layouts > 0:
            penalty = (sf / total_layouts) * raw_score
            adjusted = max(1, round(raw_score - penalty))
            print(f"  Structural penalty: {sf}/{total_layouts} wrong layouts, "
                  f"{raw_score}→{adjusted}")
            results["transition_score"] = adjusted
            results["transition_note"] += (
                f" [STRUCTURAL: {sf}/{total_layouts} layouts incorrect — "
                f"score penalized from {raw_score}]")
        else:
            results["transition_score"] = raw_score

        print(f"  Transition score: {results['transition_score']}/10")
    else:
        print("  Transition scoring failed")

    # --- Phase 6: Visual critic (only if transition > 5) ---
    t_score = results["transition_score"]
    if t_score is not None and t_score > 5:
        print(f"  Transition passed gate (>{5}), running visual_critic...")
        vc_result = run_visual_critic(html_path, final_full_ss_path, model=model)
        if vc_result:
            results["visual_critic_score"] = vc_result.get("score")
            results["visual_critic_note"] = vc_result.get("note")
            print(f"  Visual critic: {results['visual_critic_score']}/10")

            # Composite: 0.6 * transition + 0.4 * visual_critic
            vc = results["visual_critic_score"]
            results["composite"] = round(0.6 * t_score + 0.4 * vc, 1)
            print(f"  Composite: {results['composite']}")
        else:
            print("  Visual critic failed, using transition score only")
            results["composite"] = round(float(t_score), 1)
    elif t_score is not None:
        print(f"  Transition score {t_score} ≤ 5, skipping visual_critic")
        results["composite"] = round(float(t_score), 1)
    else:
        print("  No transition score, no composite")

    # --- Save results ---
    # Per-experiment JSON (alongside filmstrips)
    exp_json = out_dir / f"{tag}-results.json"
    exp_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"  Results: {exp_json}")

    # Append to runs manifest
    _append_to_manifest(results)

    return results


def _append_to_manifest(results):
    """Append evaluation results to the runs manifest."""
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    runs = []
    if RUNS_FILE.exists():
        try:
            runs = json.loads(RUNS_FILE.read_text())
        except json.JSONDecodeError:
            runs = []

    # Resolve prototype + prompt paths relative to experiments dir
    html_abs = Path(results["html_path"])
    prototype_rel = os.path.relpath(str(html_abs), str(EXPERIMENTS_DIR)) if html_abs.exists() else None

    # Look for the prompt that generated this prototype
    prompt_text = None
    exp_id = results.get("exp_id")
    if exp_id is not None:
        # Check experiment JSON for prompt
        exp_json = PROJ / "evals" / "iterations" / f"{exp_id:03d}-prompt-hierarchy-bundles.json"
        if exp_json.exists():
            try:
                exp_data = json.loads(exp_json.read_text())
                prompt_text = exp_data.get("prompt")
            except (json.JSONDecodeError, KeyError):
                pass
        # Fallback: check best-prompts.json
        if not prompt_text:
            best = PROJ / "evals" / "best-prompts.json"
            if best.exists():
                try:
                    bp = json.loads(best.read_text())
                    prompt_text = bp.get("hierarchy-bundles", {}).get("prompt")
                except (json.JSONDecodeError, KeyError):
                    pass

    # Compact summary for manifest (filmstrip paths are relative)
    entry = {
        "exp_id": results.get("exp_id"),
        "timestamp": results["timestamp"],
        "html_path": results["html_path"],
        "prototype_path": prototype_rel,
        "prompt": prompt_text,
        "button_count": len(results.get("transitions", {})),
        "transition_score": results["transition_score"],
        "transition_note": results.get("transition_note"),
        "visual_critic_score": results.get("visual_critic_score"),
        "visual_critic_note": results.get("visual_critic_note"),
        "composite": results["composite"],
        "structural_failures": results.get("structural_failures", 0),
        "filmstrip_paths": [
            os.path.relpath(p, str(EXPERIMENTS_DIR)) for p in results.get("filmstrip_paths", [])
        ],
        "js_errors": results.get("js_errors", []),
        "programmatic_issues": [],
    }

    # Collect all programmatic issues
    for label, tdata in results.get("transitions", {}).items():
        for frame in tdata.get("frames", []):
            for issue in frame.get("checks", {}).get("issues", []):
                entry["programmatic_issues"].append(f"{label}: {issue}")
    rapid = results.get("rapid_switch", {}).get("checks", {})
    for issue in rapid.get("issues", []):
        entry["programmatic_issues"].append(f"rapid-switch: {issue}")

    runs.append(entry)
    RUNS_FILE.write_text(json.dumps(runs, indent=2, ensure_ascii=False))
    print(f"  Manifest updated: {RUNS_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Transition evaluator for hierarchy-bundles")
    parser.add_argument("html", help="Path to the block HTML file")
    parser.add_argument("--exp-id", type=int, help="Experiment ID (for naming)")
    parser.add_argument("--out-dir", help="Output directory for filmstrips")
    parser.add_argument("--model", default="sonnet", help="Model for LLM scoring")
    parser.add_argument("--viewport", default="1200x900", help="Viewport WxH")
    args = parser.parse_args()

    vw, vh = map(int, args.viewport.split("x"))
    out_dir = args.out_dir or str(FILMSTRIP_DIR)

    results = evaluate(
        args.html,
        exp_id=args.exp_id,
        out_dir=out_dir,
        model=args.model,
        viewport=(vw, vh),
    )

    if results and results.get("composite") is not None:
        print(f"\n  FINAL: composite={results['composite']} "
              f"(transition={results['transition_score']}, "
              f"visual_critic={results.get('visual_critic_score', 'n/a')})")
        sys.exit(0)
    else:
        print("\n  FINAL: evaluation incomplete")
        sys.exit(1)


if __name__ == "__main__":
    main()
