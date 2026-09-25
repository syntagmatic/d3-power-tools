#!/usr/bin/env node
// Drive a D3 page headlessly and report robustness findings as JSON.
//   node plugin/scripts/probe.mjs <file-or-url> [--checks load,nan,hover,brush,storm,resize,keys,click] [--out dir]
// Checks:
//   load    console/page errors, blank canvases, empty page
//   nan     NaN/undefined in geometry attributes (broken scales or joins)
//   hover   pointer sweep over the main viz; errors and whether anything responds
//   brush   drag across a d3-brush overlay; selection must appear and survive
//   storm   300 rapid pointermoves; long tasks and DOM mutations per event
//   resize  1280 -> 700 -> 375 -> 1280; errors, NaN, horizontal overflow, whether layout reflows
//   keys    Tab walk; what receives focus, whether focus is visible, arrow-key response
//   click   click every button/select option twice rapidly (transition handoff); errors and NaN after settle
// Exit 0 when no finding has severity "error".
import { resolve, join, dirname, relative, extname, sep } from "node:path";
import { mkdirSync, existsSync, readFile } from "node:fs";
import { createServer } from "node:http";

let chromium;
try { ({ chromium } = await import("playwright")); }
catch { ({ chromium } = await import(new URL("../node_modules/playwright/index.mjs", import.meta.url).href)); }

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); return i >= 0 ? args[i + 1] : dflt; };
const target = args.find((a, i) => !a.startsWith("--") && !args[i - 1]?.startsWith("--"));
if (!target) { console.error("usage: probe.mjs <file-or-url> [--checks a,b] [--out dir]"); process.exit(2); }
const checks = new Set(opt("checks", "load,nan,hover,brush,storm,resize,keys,click").split(","));
const outDir = opt("out", null);
if (outDir) mkdirSync(outDir, { recursive: true });

// Local files are served over http, not file://: ES module imports and fetch() of data files fail
// under file:// CORS. The root is the nearest project root (git repo, plugin, or package) so
// sibling dirs like ../vendor resolve, including from an installed plugin with no .git.
const MIME = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".csv": "text/csv", ".tsv": "text/tab-separated-values", ".svg": "image/svg+xml",
  ".png": "image/png", ".jpg": "image/jpeg", ".wasm": "application/wasm", ".txt": "text/plain" };
let server = null;
async function serve(file) {
  let root = dirname(file);
  const markers = [".git", ".claude-plugin", "package.json"];
  for (let d = root; d !== dirname(d); d = dirname(d)) if (markers.some(m => existsSync(join(d, m)))) { root = d; break; }
  server = createServer((req, res) => {
    const p = join(root, decodeURIComponent(new URL(req.url, "http://x").pathname));
    if (p !== root && !p.startsWith(root + sep)) { res.writeHead(403).end(); return; }
    readFile(p, (err, buf) => {
      if (err) { res.writeHead(404).end(); return; }
      res.writeHead(200, { "content-type": MIME[extname(p)] || "application/octet-stream" }).end(buf);
    });
  });
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  return `http://127.0.0.1:${server.address().port}/${relative(root, file).split(sep).map(encodeURIComponent).join("/")}`;
}
const url = /^https?:/.test(target) ? target : await serve(resolve(target));

const findings = [];
const add = (check, severity, detail) => findings.push({ check, severity, detail });
const stats = {};
const errors = [];
const settle = ms => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", e => errors.push(e.message));
const newErrors = (() => { let seen = 0; return () => { const e = errors.slice(seen); seen = errors.length; return e; }; })();
const shot = async name => { if (outDir) await page.screenshot({ path: join(outDir, `${name}.png`) }); };

// In-page helpers: NaN scan, mutation counter, long-task observer, main-viz bbox.
const install = () => page.evaluate(() => {
  if (window.__probe) return;
  const p = window.__probe = { mutations: 0, longTasks: [] };
  new MutationObserver(ms => { p.mutations += ms.length; })
    .observe(document.documentElement, { subtree: true, childList: true, attributes: true, characterData: true });
  try {
    new PerformanceObserver(l => { for (const e of l.getEntries()) p.longTasks.push(e.duration); })
      .observe({ type: "longtask", buffered: true });
  } catch {}
  const GEOM = ["x", "y", "x1", "x2", "y1", "y2", "cx", "cy", "r", "rx", "ry", "width", "height", "d", "transform", "points", "opacity", "fill-opacity"];
  p.nan = () => {
    const bad = [];
    for (const el of document.querySelectorAll("svg *")) {
      for (const a of GEOM) {
        const v = el.getAttribute(a);
        if (v && /NaN|undefined|Infinity/.test(v)) { bad.push(`<${el.tagName} ${a}="${v.slice(0, 40)}">`); break; }
      }
    }
    return { count: bad.length, sample: bad.slice(0, 5) };
  };
  p.main = () => {
    const els = [...document.querySelectorAll("svg, canvas")]
      .map(e => ({ e, r: e.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 50 && r.height > 50)
      .sort((a, b) => b.r.width * b.r.height - a.r.width * a.r.height);
    if (!els.length) return null;
    const { x, y, width, height } = els[0].r;
    return { x, y, width, height, tag: els[0].e.tagName.toLowerCase() };
  };
  p.blankCanvases = () => [...document.querySelectorAll("canvas")].filter(c => {
    if (!c.width || !c.height) return false;
    try {
      const ctx = c.getContext("2d");
      if (!ctx) return false; // webgl canvases: can't sample cheaply, skip
      const d = ctx.getImageData(0, 0, c.width, c.height).data;
      for (let i = 3; i < d.length; i += 4 * 97) if (d[i]) return false;
      return true;
    } catch { return false; }
  }).length;
  p.overflow = () => document.documentElement.scrollWidth - document.documentElement.clientWidth;
});
const probe = (fn, ...a) => page.evaluate(([fn, a]) => window.__probe[fn](...a), [fn, a]);
const counters = () => page.evaluate(() => ({ m: window.__probe.mutations, lt: window.__probe.longTasks.length }));

try {
  await page.goto(url, { waitUntil: "load", timeout: 20000 });
  await settle(1500);
  await install();
  const main = await probe("main");

  if (checks.has("load")) {
    const e = newErrors();
    if (e.length) add("load", "error", `${e.length} error(s) on load: ${e.slice(0, 3).join(" | ")}`);
    if (!main) add("load", "error", "no svg or canvas larger than 50x50");
    const blank = await probe("blankCanvases");
    if (blank) add("load", "warn", `${blank} 2d canvas(es) appear blank`);
    stats.main = main;
    await shot("load");
  }

  if (checks.has("nan")) {
    const n = await probe("nan");
    stats.nan = n.count;
    if (n.count) add("nan", "error", `${n.count} element(s) with NaN/undefined geometry: ${n.sample.join(" ")}`);
  }

  if (checks.has("hover") && main) {
    const before = await counters();
    for (let gy = 1; gy < 8; gy++)
      for (let gx = 1; gx < 12; gx++)
        await page.mouse.move(main.x + (main.width * gx) / 12, main.y + (main.height * gy) / 8, { steps: 2 });
    const after = await counters();
    stats.hoverMutations = after.m - before.m;
    if (!stats.hoverMutations) add("hover", "info", "pointer sweep over main viz changed nothing in the DOM (no hover feedback, or canvas-only)");
    const e = newErrors();
    if (e.length) add("hover", "error", `errors during hover: ${e.slice(0, 3).join(" | ")}`);
    await shot("hover");
  }

  if (checks.has("brush")) {
    const overlay = await page.$(".overlay, .brush rect.overlay");
    if (!overlay) stats.brush = "no d3-brush overlay found";
    else {
      const r = await overlay.boundingBox();
      await page.mouse.move(r.x + r.width * 0.3, r.y + r.height * 0.3);
      await page.mouse.down();
      await page.mouse.move(r.x + r.width * 0.6, r.y + r.height * 0.7, { steps: 15 });
      await page.mouse.up();
      await settle(400);
      const sel = await page.$$eval(".selection", els => els.map(e => +e.getAttribute("width") || 0).filter(w => w > 0).length);
      stats.brushSelections = sel;
      if (!sel) add("brush", "warn", "drag across brush overlay left no visible .selection");
      const e = newErrors();
      if (e.length) add("brush", "error", `errors during brush: ${e.slice(0, 3).join(" | ")}`);
      const n = await probe("nan");
      if (n.count) add("brush", "error", `NaN geometry after brush: ${n.sample.join(" ")}`);
      await shot("brush");
    }
  }

  if (checks.has("storm") && main) {
    const before = await counters();
    const t0 = Date.now();
    for (let i = 0; i < 300; i++) {
      const t = i / 300;
      await page.mouse.move(main.x + main.width * (0.1 + 0.8 * t), main.y + main.height * (0.5 + 0.3 * Math.sin(t * 20)));
    }
    await settle(300);
    const after = await counters();
    const longTasks = await page.evaluate(n => window.__probe.longTasks.slice(n), before.lt);
    stats.storm = { ms: Date.now() - t0, mutationsPerMove: +((after.m - before.m) / 300).toFixed(1), longTasks: longTasks.length, worstLongTaskMs: Math.round(Math.max(0, ...longTasks)) };
    if (longTasks.length > 5) add("storm", "warn", `${longTasks.length} long tasks during 300 pointermoves (worst ${stats.storm.worstLongTaskMs}ms): handlers likely not coalesced to rAF`);
    if (stats.storm.mutationsPerMove > 200) add("storm", "warn", `${stats.storm.mutationsPerMove} DOM mutations per pointermove: redraw-per-event update storm`);
    const e = newErrors();
    if (e.length) add("storm", "error", `errors during storm: ${e.slice(0, 3).join(" | ")}`);
  }

  if (checks.has("resize")) {
    stats.resize = {};
    for (const w of [700, 375, 1280]) {
      const before = await counters();
      await page.setViewportSize({ width: w, height: 800 });
      await settle(600);
      const after = await counters();
      const overflow = await probe("overflow");
      const n = await probe("nan");
      stats.resize[w] = { reflowMutations: after.m - before.m, overflowPx: overflow };
      if (overflow > 4 && w <= 700) add("resize", "warn", `horizontal overflow of ${overflow}px at ${w}px wide`);
      if (n.count) add("resize", "error", `NaN geometry at ${w}px: ${n.sample.join(" ")}`);
      await shot(`resize-${w}`);
    }
    if (Object.values(stats.resize).every(r => r.reflowMutations === 0)) add("resize", "info", "no DOM change on resize (fixed size, or viewBox scaling)");
    const e = newErrors();
    if (e.length) add("resize", "error", `errors during resize: ${e.slice(0, 3).join(" | ")}`);
  }

  if (checks.has("keys")) {
    await page.mouse.click(2, 2);
    const stops = [];
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab");
      stops.push(await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        const cs = getComputedStyle(el);
        const visible = cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0 || cs.boxShadow !== "none";
        return { tag: el.tagName.toLowerCase(), role: el.getAttribute("role"), label: (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 40), inViz: !!el.closest("svg") || el.tagName === "CANVAS", focusStyle: visible };
      }));
    }
    const real = stops.filter(Boolean);
    stats.keys = { stops: real.length, inViz: real.filter(s => s.inViz).length, unlabeled: real.filter(s => !s.label).length };
    if (!real.some(s => s.inViz)) add("keys", "info", "no focus stop inside the visualization (keyboard users can't reach data)");
    if (real.length && real.every(s => !s.focusStyle)) add("keys", "warn", "focused elements show no outline or box-shadow (may rely on custom drawing)");
    if (stats.keys.unlabeled) add("keys", "warn", `${stats.keys.unlabeled} focus stop(s) without an accessible label`);
    const beforeArrow = await counters();
    for (const k of ["ArrowRight", "ArrowRight", "ArrowDown"]) await page.keyboard.press(k);
    stats.keys.arrowMutations = (await counters()).m - beforeArrow.m;
    const e = newErrors();
    if (e.length) add("keys", "error", `errors during keyboard walk: ${e.slice(0, 3).join(" | ")}`);
  }

  if (checks.has("click")) {
    const buttons = await page.$$("button:visible, [role=button]:visible, input[type=radio]:visible, input[type=checkbox]:visible");
    for (const b of buttons.slice(0, 20)) {
      try { await b.click({ timeout: 500 }); await settle(50); await b.click({ timeout: 500 }); } catch {}
    }
    for (const s of (await page.$$("select:visible")).slice(0, 5)) {
      const values = await s.$$eval("option", os => os.map(o => o.value));
      for (const v of values.slice(0, 6)) { try { await s.selectOption(v); await settle(40); } catch {} }
    }
    await settle(1500);
    stats.controls = buttons.length;
    const n = await probe("nan");
    if (n.count) add("click", "error", `NaN geometry after rapid control changes (transition handoff?): ${n.sample.join(" ")}`);
    const e = newErrors();
    if (e.length) add("click", "error", `errors during rapid clicks: ${e.slice(0, 3).join(" | ")}`);
    await shot("click");
  }
} catch (e) {
  add("probe", "error", `probe aborted: ${e.message.split("\n")[0]}`);
} finally {
  await browser.close();
  server?.close();
}

console.log(JSON.stringify({ target, findings, stats }, null, 2));
process.exit(findings.some(f => f.severity === "error") ? 1 : 0);
