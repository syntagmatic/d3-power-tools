#!/usr/bin/env python3
"""
Playwright test runner for D3 visualizations.

Single file mode:
  python3 scripts/test-viz.py path/to/viz.html
  python3 scripts/test-viz.py path/to/viz.html --interactions hover,brush --out /tmp/shot.png

Config mode (runs a test suite):
  python3 scripts/test-viz.py --config bubble-treemap/tests/test.config.json
  python3 scripts/test-viz.py --config d3-power-tools/tests/test.config.json

Run all configs in the repo:
  python3 scripts/test-viz.py --all

Config format (test.config.json):
  {
    "name": "my-project",
    "root": "..",                     // resolved relative to config file
    "screenshot_dir": "/tmp/tests",   // where screenshots go
    "defaults": {                     // applied to all tests unless overridden
      "timeout": 10000,
      "width": 1200,
      "height": 800
    },
    "tests": [
      {
        "file": "index.html",
        "wait_for": "svg",
        "interactions": ["hover", "brush"],
        "setup": "document.querySelector('#preset-btns button:nth-child(2)').click()"
      }
    ]
  }

Exit code 0 = all pass, 1 = any failure.
"""

import argparse
import http.server
import json
import os
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

def start_server(directory, port):
    """Start a server rooted at `directory` without changing cwd."""
    import functools

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Core test logic
# ---------------------------------------------------------------------------

def run_single_test(pw_browser, test_spec):
    """
    Run checks against one HTML file. Returns a results dict.

    test_spec keys:
      file        (str, required) absolute path to HTML
      out         (str) screenshot path
      width       (int) viewport width
      height      (int) viewport height
      timeout     (int) ms
      wait_for    (str) CSS selector
      interactions (list[str])
      setup       (str) JS to evaluate after load, before checks
    """
    html_path = Path(test_spec["file"]).resolve()
    width = test_spec.get("width", 1200)
    height = test_spec.get("height", 800)
    timeout = test_spec.get("timeout", 10000)
    wait_for = test_spec.get("wait_for")
    interactions = test_spec.get("interactions", [])
    setup_js = test_spec.get("setup")
    out_path = test_spec.get("out", f"/tmp/d3-test-{html_path.stem}.png")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Serve from the file's directory
    serve_dir = str(html_path.parent)
    port = find_free_port()
    httpd = start_server(serve_dir, port)
    url = f"http://127.0.0.1:{port}/{html_path.name}"

    results = {
        "file": str(html_path),
        "checks": [],
        "screenshot": out_path,
        "passed": True,
    }

    def check(name, passed, detail=""):
        results["checks"].append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            results["passed"] = False

    js_errors = []
    console_warnings = []

    page = pw_browser.new_page(viewport={"width": width, "height": height})
    page.on("pageerror", lambda err: js_errors.append(str(err)))
    page.on("console", lambda msg: (
        console_warnings.append(msg.text) if msg.type == "warning" else None
    ))

    # Load
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout)
        check("page_loads", True)
    except Exception as e:
        check("page_loads", False, str(e))
        page.screenshot(path=out_path)
        page.close()
        httpd.shutdown()
        results["warnings"] = console_warnings[:10] if console_warnings else []
        return results

    # Run setup JS (e.g. click a preset button, load specific data)
    # Wrap in async IIFE so `await` works in setup scripts
    if setup_js:
        try:
            if "await " in setup_js:
                page.evaluate(f"() => (async () => {{ {setup_js} }})()")
            else:
                page.evaluate(f"() => {{ {setup_js} }}")
            page.wait_for_timeout(500)
            check("setup_script", True)
        except Exception as e:
            check("setup_script", False, str(e))

    # Wait for selector
    if wait_for:
        try:
            page.wait_for_selector(wait_for, timeout=timeout)
            check("wait_for_selector", True, wait_for)
        except Exception:
            check("wait_for_selector", False, f"'{wait_for}' not found within {timeout}ms")

    # Let async rendering settle
    page.wait_for_timeout(500)

    # No JS errors
    check("no_js_errors", len(js_errors) == 0,
          "; ".join(js_errors[:5]) if js_errors else "")

    # D3 loaded (global script or ES module import)
    d3_loaded = page.evaluate("""() => {
        if (typeof d3 !== 'undefined') return true;
        // ES module imports don't expose d3 globally — check for d3-generated DOM
        const hasD3Class = document.querySelector('[class*="tick"], [class*="domain"], [class*="axis"]') !== null;
        const hasD3Data = document.querySelector('[data-ready], [__data__]') !== null;
        // Check for d3 import in module scripts
        const scripts = document.querySelectorAll('script[type=module]');
        const hasD3Import = Array.from(scripts).some(s => /import.*d3/.test(s.textContent));
        return hasD3Class || hasD3Data || hasD3Import;
    }"""
    )
    check("d3_loaded", d3_loaded,
          "" if d3_loaded else "d3 is not defined — check script import")

    # SVG or Canvas has content
    viz_info = page.evaluate("""() => {
        const svgs = document.querySelectorAll('svg');
        const canvases = document.querySelectorAll('canvas');
        const svgChildren = Array.from(svgs).reduce((n, s) => n + s.children.length, 0);
        const canvasHasContent = Array.from(canvases).some(c => {
            const ctx = c.getContext('2d');
            if (!ctx) return false;
            try {
                const data = ctx.getImageData(0, 0, c.width, c.height).data;
                return data.some(v => v !== 0);
            } catch(e) { return false; }
        });
        return {
            svgCount: svgs.length,
            canvasCount: canvases.length,
            svgChildren,
            canvasHasContent,
        };
    }""")

    has_viz = (viz_info["svgCount"] > 0 and viz_info["svgChildren"] > 0) or \
              (viz_info["canvasCount"] > 0 and viz_info["canvasHasContent"])
    check("has_visible_content", has_viz,
          f"SVG: {viz_info['svgCount']} ({viz_info['svgChildren']} children), "
          f"Canvas: {viz_info['canvasCount']} (has pixels: {viz_info['canvasHasContent']})")

    # Page not blank
    not_blank = page.evaluate("""() => {
        const body = document.body;
        const rect = body.getBoundingClientRect();
        return rect.height > 100 && body.innerHTML.trim().length > 100;
    }""")
    check("not_blank_page", not_blank)

    # No broken resources
    broken = page.evaluate("""() => {
        const imgs = document.querySelectorAll('img');
        return Array.from(imgs).filter(i => !i.complete || i.naturalWidth === 0)
                    .map(i => i.src);
    }""")
    check("no_broken_resources", len(broken) == 0,
          ", ".join(broken) if broken else "")

    # Interaction smoke tests
    if interactions:
        _run_interaction_tests(page, interactions, check)

    # Screenshot (after interactions, so we capture final state)
    page.screenshot(path=out_path)

    if console_warnings:
        results["warnings"] = console_warnings[:10]

    page.close()
    httpd.shutdown()
    return results


def _run_interaction_tests(page, interactions, check):
    viewport = page.viewport_size
    cx, cy = viewport["width"] // 2, viewport["height"] // 2

    for interaction in interactions:
        try:
            if interaction == "hover":
                page.mouse.move(cx, cy)
                page.wait_for_timeout(100)
                page.mouse.move(cx + 100, cy + 50)
                page.wait_for_timeout(100)

            elif interaction == "click":
                page.mouse.click(cx, cy)
                page.wait_for_timeout(300)

            elif interaction == "brush":
                page.mouse.move(cx - 100, cy - 100)
                page.mouse.down()
                page.mouse.move(cx + 100, cy + 100, steps=10)
                page.mouse.up()
                page.wait_for_timeout(300)

            elif interaction == "drag":
                page.mouse.move(cx, cy)
                page.mouse.down()
                page.mouse.move(cx + 50, cy, steps=5)
                page.mouse.up()
                page.wait_for_timeout(300)

            elif interaction == "zoom":
                page.mouse.move(cx, cy)
                page.mouse.wheel(0, -300)
                page.wait_for_timeout(300)
                page.mouse.wheel(0, 300)
                page.wait_for_timeout(300)

            else:
                check(f"interaction_{interaction}", False, f"Unknown: {interaction}")
                continue

            check(f"interaction_{interaction}", True)
        except Exception as e:
            check(f"interaction_{interaction}", False, str(e))


# ---------------------------------------------------------------------------
# Config mode
# ---------------------------------------------------------------------------

def load_config(config_path):
    """Load a test.config.json and resolve paths relative to it."""
    config_path = Path(config_path).resolve()
    with open(config_path) as f:
        config = json.load(f)

    config_dir = config_path.parent
    root = (config_dir / config.get("root", ".")).resolve()
    defaults = config.get("defaults", {})
    screenshot_dir = config.get("screenshot_dir", "/tmp/d3-tests")

    specs = []
    for i, test in enumerate(config.get("tests", [])):
        spec = {**defaults, **test}
        spec["file"] = str((root / spec["file"]).resolve())
        label = test.get("name", Path(test["file"]).stem)
        spec["out"] = f"{screenshot_dir}/{config.get('name', 'project')}/{label}.png"
        # Ensure interactions is a list
        if isinstance(spec.get("interactions"), str):
            spec["interactions"] = [x.strip() for x in spec["interactions"].split(",")]
        specs.append(spec)

    return config.get("name", config_path.parent.name), specs


def find_all_configs(repo_root):
    """Find all test.config.json files under the repo."""
    return sorted(Path(repo_root).rglob("tests/test.config.json"))


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report_single(results, as_json=False):
    if as_json:
        print(json.dumps(results, indent=2))
        return

    passed = sum(1 for c in results["checks"] if c["passed"])
    total = len(results["checks"])
    status = "PASS" if results["passed"] else "FAIL"

    print(f"  {status}  {passed}/{total}  {Path(results['file']).name}")
    for c in results["checks"]:
        if not c["passed"]:
            detail = f"  — {c['detail']}" if c.get("detail") else ""
            print(f"    [x] {c['name']}{detail}")

    if results.get("warnings"):
        for w in results["warnings"][:3]:
            print(f"    [!] {w[:120]}")


def report_suite(name, all_results, as_json=False):
    if as_json:
        print(json.dumps({"suite": name, "results": all_results}, indent=2))
        return

    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    status = "PASS" if passed == total else "FAIL"

    print(f"\n{'=' * 55}")
    print(f"  {name}: {status}  {passed}/{total} files passed")
    print(f"{'=' * 55}")

    for r in all_results:
        report_single(r)

    print(f"\n  Screenshots: {os.path.dirname(all_results[0]['screenshot'])}/")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Test D3 visualizations with Playwright")

    # Modes (mutually exclusive)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("html_file", nargs="?", default=None,
                      help="Single HTML file to test")
    mode.add_argument("--config", default=None,
                      help="Path to test.config.json")
    mode.add_argument("--all", action="store_true",
                      help="Find and run all test.config.json files in repo")

    # Single-file options
    p.add_argument("--out", default=None, help="Screenshot output path")
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--height", type=int, default=800)
    p.add_argument("--timeout", type=int, default=10000)
    p.add_argument("--wait-for", default=None, help="CSS selector to wait for")
    p.add_argument("--interactions", default=None,
                   help="Comma-separated: hover,click,brush,drag,zoom")
    p.add_argument("--setup", default=None, help="JS to run after page load")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    args = p.parse_args()

    all_passed = True

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        if args.html_file:
            # Single file mode
            spec = {
                "file": args.html_file,
                "out": args.out or f"/tmp/d3-test-{Path(args.html_file).stem}.png",
                "width": args.width,
                "height": args.height,
                "timeout": args.timeout,
                "wait_for": args.wait_for,
                "setup": args.setup,
                "interactions": (
                    [x.strip() for x in args.interactions.split(",")]
                    if args.interactions else []
                ),
            }
            result = run_single_test(browser, spec)
            all_passed = result["passed"]

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print()
                report_single(result)
                print(f"\n  Screenshot: {result['screenshot']}\n")

        elif args.config:
            # Single config mode
            name, specs = load_config(args.config)
            results = [run_single_test(browser, spec) for spec in specs]
            all_passed = all(r["passed"] for r in results)
            report_suite(name, results, args.json)

        elif args.all:
            # Find all configs
            repo_root = Path(__file__).resolve().parent.parent
            configs = find_all_configs(repo_root)
            if not configs:
                print("No test.config.json files found.", file=sys.stderr)
                sys.exit(1)

            for config_path in configs:
                name, specs = load_config(config_path)
                results = [run_single_test(browser, spec) for spec in specs]
                if not all(r["passed"] for r in results):
                    all_passed = False
                report_suite(name, results, args.json)

        browser.close()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
