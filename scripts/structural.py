"""Structural fingerprint check for corpus outputs (ported from d3pt's scripts/run/structural.sh).

A corpus task's verify.json names DOM selectors with count bands and interactions with an expected
effect. This checks a rendered page against them mechanically, with no LLM, so "runs but is the wrong
chart" is caught before any critic scores it. Selectors are deliberately loose; they were calibrated
on d3pt's April/May 2026 runs and may still reject valid charts that name their classes differently.

Usage as a module: check_all([(html_path, verify_dict)], serve_root) -> {html_path: result}.
"""
import http.server
import json
import socketserver
import threading
from pathlib import Path

SETTLE_MS = 1500
TIMEOUT_MS = 10000

SVG_CLASSES_JS = """() => Array.from(document.querySelectorAll('svg *[class]')).map(el => {
    const cn = el.className; return cn.baseVal !== undefined ? cn.baseVal : String(cn);
}).join('|')"""

MORPH_SAMPLES_JS = """async () => {
    const sel = document.querySelector('path, g[class*="node"], rect[class*="node"]');
    if (!sel) return [];
    const out = [];
    for (let i = 0; i < 5; i++) {
        out.push((sel.getAttribute('d') || '') + '|' + (sel.getAttribute('transform') || ''));
        await new Promise(r => setTimeout(r, 80));
    }
    return out;
}"""


def _count_check(spec, count, rows):
    """(check-name suffix, ok, detail) for one dom entry, or None if it declares no check."""
    band = spec.get("count")
    if isinstance(band, dict):
        ok = band.get("min", 0) <= count <= band.get("max", float("inf")) and band.get("exact", count) == count
        return "count", ok, f"count={count} band={band}"
    if isinstance(spec.get("rows"), dict):
        band = spec["rows"]
        ok = band.get("min", 0) <= rows() <= band.get("max", float("inf"))
        return "rows", ok, f"rows={rows()} band={band}"
    if spec.get("required") is True:
        return "required", count > 0, f"count={count}"
    if "min" in spec:
        return "min", count >= spec["min"], f"count={count}"
    return None


def check_page(page, url, verify):
    res = {"pass": True, "checks": []}

    def record(name, ok, detail=""):
        res["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
        res["pass"] = res["pass"] and bool(ok)

    try:
        page.goto(url, timeout=TIMEOUT_MS, wait_until="networkidle")
    except Exception:
        pass  # best-effort, as in d3pt: static checks may still resolve
    page.wait_for_timeout(SETTLE_MS)

    for key, spec in verify.get("dom", {}).items():
        if not isinstance(spec, dict) or not spec.get("selector"):
            continue
        loc = page.locator(spec["selector"])
        try:
            count = loc.count()
        except Exception as e:
            record(f"dom.{key}.selector-eval", False, str(e))
            continue
        c = _count_check(spec, count, lambda: loc.locator("tr, [role='row']").count())
        if c:
            record(f"dom.{key}.{c[0]}", c[1], c[2])

    # Interactions sharing a trigger are dispatched once and all asserted against the same after-state.
    by_trigger = {}
    for key, spec in verify.get("interactions", {}).items():
        if spec.get("trigger"):
            by_trigger.setdefault(spec["trigger"], []).append((key, spec))

    for trigger, group in by_trigger.items():
        event = group[0][1].get("event", "click")
        is_brush = group[0][1].get("effect") == "filtered-mark-count-changes" or any("brush" in k for k, _ in group)
        is_hover = "hover" in event or any("hover" in k for k, _ in group)
        try:
            # .first for brush (needs the draggable region); .last otherwise (deeper nodes, non-active toggle).
            loc = page.locator(trigger).first if is_brush else page.locator(trigger).last
            before = page.evaluate("() => document.body.innerHTML.length")
            before_cls = page.evaluate(SVG_CLASSES_JS)
            if is_brush:
                box = loc.bounding_box()
                if not box:
                    for k, _ in group:
                        record(f"interaction.{k}", False, "trigger has no bounding box")
                    continue
                page.mouse.move(box["x"] + box["width"] * .25, box["y"] + box["height"] * .25)
                page.mouse.down()
                page.mouse.move(box["x"] + box["width"] * .75, box["y"] + box["height"] * .75, steps=8)
                page.mouse.up()
                page.wait_for_timeout(300)
            elif is_hover:
                loc.hover(force=True, timeout=TIMEOUT_MS)
                page.wait_for_timeout(200)
            else:
                loc.click(timeout=TIMEOUT_MS)
                page.wait_for_timeout(200)
            after = page.evaluate("() => document.body.innerHTML.length")
            after_cls = page.evaluate(SVG_CLASSES_JS)
            for k, spec in group:
                eff = spec.get("effect", "")
                if eff == "path-to-root-highlights":
                    record(f"interaction.{k}.{eff}", before_cls != after_cls)
                elif eff == "transition-attributes-animate":
                    n = len(set(page.evaluate(MORPH_SAMPLES_JS)))
                    record(f"interaction.{k}.{eff}", n > 1, f"distinct-samples={n}")
                else:
                    record(f"interaction.{k}.dom-diff", before != after, f"before={before} after={after}")
        except Exception as e:
            for k, _ in group:
                record(f"interaction.{k}", False, f"error: {str(e).splitlines()[0]}")
    return res


def check_all(items, serve_root):
    """items: [(html_path, verify_dict)], every html_path under serve_root. One server, fresh page per item."""
    from playwright.sync_api import sync_playwright
    root = Path(serve_root).resolve()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):
            pass

    out = {}
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        port = httpd.server_address[1]
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                for html, verify in items:
                    rel = Path(html).resolve().relative_to(root).as_posix()
                    ctx = browser.new_context(viewport={"width": 1024, "height": 768})
                    try:
                        out[str(html)] = check_page(ctx.new_page(), f"http://127.0.0.1:{port}/{rel}", verify)
                    except Exception as e:
                        out[str(html)] = {"pass": False, "checks": [], "error": str(e).splitlines()[0]}
                    finally:
                        ctx.close()
                browser.close()
        finally:
            httpd.shutdown()
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        sys.exit("usage: structural.py <page.html> <verify.json>")
    page_path = Path(sys.argv[1])
    r = check_all([(page_path, json.loads(Path(sys.argv[2]).read_text()))], page_path.parent)
    print(json.dumps(r[str(page_path)], indent=2, ensure_ascii=False))
    sys.exit(0 if r[str(page_path)]["pass"] else 1)
