---
name: responsive
description: "Making D3.js visualizations responsive and adaptive. Use this skill when the user needs charts that resize with their container, adapt layout at different screen sizes, handle mobile/touch interactions, embed charts in iframes, support retina/HiDPI Canvas, print cleanly, or implement any resize-aware D3 visualization."
---

# Responsive Charts

A chart built for 960px becomes unreadable at 320px — not because the data changed, but because tick labels overlap, legends occlude data, and 14px text shrinks to 7px. Responsive D3 means adapting the *design decisions* (tick count, margin, layout) to the available space, not just scaling pixels.

Related skills: `axes-and-scales` (tick formatting at narrow widths), `canvas` (DPI, layers), `small-multiples` (responsive reflow), `visual-texture` (pattern fills for print).

## viewBox vs Redraw: When Scaling Breaks

| | viewBox (scale) | Redraw-on-resize |
|---|---|---|
| Text | Shrinks proportionally — 14px becomes 7px at half width | Stays readable at every size |
| Tick count | Fixed — crowds at narrow, wastes space at wide | Adapts via `scale.ticks(width / 80)` |
| Layout | Fixed — legend pinned to right even at 320px | Can reflow: legend moves below chart |
| Interaction targets | Shrink with chart — hard to tap on mobile | Stay at usable sizes |
| Cost | Zero — browser handles it | Re-renders on every resize |

**Use viewBox** only for decorative/iconic graphics where text doesn't matter. **Use redraw-on-resize** for any chart with axes, labels, or interaction. Most D3 charts need redraw.

## Don't Use Responsive Redraw When...

- **The chart is a static export** (PNG/PDF generation). Fix dimensions, skip the observer.
- **The container never resizes** (fixed-size dashboard cell with no breakpoints). Add unnecessary complexity for zero benefit.
- **You're inside a scrollytelling step** with a fixed viewport. The chart dimensions are locked to the step; resize the outer container instead.

## ResizeObserver: The One Bug Everyone Hits

Chart render changes container height, observer fires, chart re-renders, observer fires again — infinite loop. Fix: observe a wrapper whose size is set by CSS, not by chart content.

```js
// Wrapper has explicit height from CSS — chart content can't change it
const wrapper = document.getElementById("chart-wrapper");
const ro = new ResizeObserver(([entry]) => {
  const { width, height } = entry.contentRect;
  if (width > 0) render(width, height);
});
ro.observe(wrapper);
```

Set the wrapper with `overflow: hidden` so the SVG/Canvas inside can't push its boundaries.

## Container Queries for CSS-Level Adaptation

Container queries (`@container`) let chart CSS respond to the container's width, not the viewport. This matters because charts are often embedded as components where viewport width is irrelevant. As of March 2026, size queries work in all major browsers.

**Use container queries for presentation**: legend placement, font sizes, showing/hiding annotations. **Use ResizeObserver for data**: tick counts, scale recalculation, layout algorithm changes. Production chart components benefit from both.

```css
.chart-wrapper { container-type: inline-size; }

@container (max-width: 500px) {
  .legend { flex-direction: column; font-size: 0.8rem; }
  .annotation { display: none; }
}
@container (max-width: 350px) {
  .legend { display: none; }
}
```

**Container collapse caveat.** `container-type: inline-size` applies size containment — the element cannot derive its width from its children. The container must get its size from CSS (grid, flex, percentage), which matches the ResizeObserver rule: observe a wrapper whose size comes from CSS, not chart content.

| Adaptation | Container Query | ResizeObserver |
|---|---|---|
| Legend layout, font size, hide annotations | Yes — declarative, no FOUC | Overkill |
| Tick count, scale domain, point radius | Cannot control JS | Yes — requires D3 recalc |
| Layout switching (bar → sparkline) | No | Yes |

## Margins That Respond to Content

Hard-coded margins clip labels at narrow widths and waste space at wide ones. Measure the widest tick label:

```js
function getLeftMargin(yScale, format) {
  const temp = d3.select("body").append("svg").style("visibility", "hidden");
  const maxW = d3.max(yScale.ticks(), t => {
    const text = temp.append("text").text(format(t));
    const w = text.node().getBBox().width;
    text.remove();
    return w;
  });
  temp.remove();
  return Math.ceil(maxW) + 12; // 12px padding from axis line
}
```

For the bottom margin, rotate labels at narrow widths and increase margin to match:

```js
const rotate = width < 500;
const margin = { bottom: rotate ? 60 : 30 };
xAxis.selectAll("text")
  .attr("transform", rotate ? "rotate(-45)" : null)
  .style("text-anchor", rotate ? "end" : "middle");
```

## Tick Density by Width

Too many ticks at 320px crowd and overlap. Too few at 1920px waste the axis. Tie tick count to available pixels:

```js
// ~80px per tick is readable for most numeric labels
xAxis.call(d3.axisBottom(x).ticks(Math.max(2, Math.floor(innerWidth / 80))));

// For time axes, D3's multi-scale time format handles density well,
// but you still need to cap the count
xAxis.call(d3.axisBottom(x).ticks(Math.min(width / 100, 12)));
```

For categorical axes that don't fit, filter to every Nth label:

```js
xAxis.selectAll(".tick text")
  .style("display", (d, i) => i % Math.ceil(categories.length / (width / 60)) ? "none" : null);
```

## Brush and Interaction at Small Sizes

A d3.brushX selection is stored in pixel coordinates. After resize, those pixels map to different data values. Convert to data domain before resize, restore after:

```js
let brushedDomain = null; // store in data space, not pixels

function brushed(event) {
  if (!event.selection) return;
  brushedDomain = event.selection.map(xScale.invert);
}

function render(width) {
  // ... rebuild scales with new width ...
  if (brushedDomain) {
    const px = brushedDomain.map(xScale); // domain → new pixels
    brushGroup.call(brush.move, px);
  }
}
```

On screens narrower than ~400px, brush handles are hard to grab. Fall back to an HTML range input:

```js
if (width < 400) {
  brushGroup.style("display", "none");
  d3.select("#range-fallback").style("display", null)
    .on("input", e => filterByValue(+e.target.value));
} else {
  brushGroup.style("display", null);
  d3.select("#range-fallback").style("display", "none");
}
```

## Canvas DPI

Forgetting any of the three steps — backing store size, CSS size, context scale — produces blurry Canvas on retina displays.

```js
function setupCanvas(container, width, height) {
  const dpr = devicePixelRatio || 1;
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * dpr);   // physical pixels
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;        // CSS pixels
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);                      // draw in CSS coordinates
  container.appendChild(canvas);
  return ctx;
}
```

Setting `canvas.width` or `canvas.height` resets *all* context state (transforms, styles, clip). Re-apply `ctx.scale(dpr, dpr)` after every resize.

Detect DPR changes (user drags window between monitors):

```js
matchMedia(`(resolution: ${devicePixelRatio}dppx)`)
  .addEventListener("change", () => resizeAndRedraw(), { once: true });
```

## Mobile Address Bar Resize

On mobile browsers, the address bar showing/hiding fires a resize event that changes height but not width. Since most charts only depend on width, skip the redraw:

```js
let lastWidth = 0;
const ro = new ResizeObserver(([entry]) => {
  const w = entry.contentRect.width;
  if (Math.abs(w - lastWidth) < 1) return; // height-only change, skip
  lastWidth = w;
  debouncedRender(w, entry.contentRect.height);
});
```

## Touch Targets and Pointer Adaptation

WCAG 2.2 requires interactive targets of at least 24x24 CSS pixels (44x44 recommended). On coarse-pointer devices, enlarge hit areas without changing visual size:

```js
const isTouch = matchMedia("(pointer: coarse)").matches;
const hitRadius = isTouch ? 22 : 8; // 44px vs 16px diameter
```

For SVG: add a larger transparent circle behind visible data points. For Canvas: expand quadtree search radius. Brush handles need 44px touch targets at minimum — the existing `< 400px` range fallback handles this.

## Reduced Motion

Users with vestibular sensitivity set `prefers-reduced-motion`. Respect it for all D3 transitions:

```js
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const duration = reduceMotion ? 0 : 750;
selection.transition().duration(duration)...
```

Functional animations (data enter/exit) become instant state changes. Decorative animations (loading spinners, ambient motion) are fully disabled.

## Iframe Embedding

Chart inside iframe reports its needed height to the host page so the iframe can size itself:

```js
// Inside iframe
function render(width) {
  const height = Math.round(width * 0.5);
  // ... render ...
  window.parent.postMessage({ type: "chart-resize", height }, "*");
}
new ResizeObserver(([e]) => {
  if (e.contentRect.width > 0) render(e.contentRect.width);
}).observe(document.body);
```

```js
// Host page
window.addEventListener("message", (e) => {
  if (e.data.type === "chart-resize")
    document.getElementById("chart-iframe").style.height = `${e.data.height}px`;
});
```

Sandbox requires `allow-scripts`. Add `allow-same-origin` if the chart fetches data from the host domain.

## Print Styles

```css
@media print {
  :root { --bg: #fff; --fg: #222; --grid: #ddd; }
  .tooltip, .controls, .brush, .zoom-buttons, button, input, select {
    display: none !important;
  }
  #chart { width: 100% !important; break-inside: avoid; }
}
```

**SVG prints sharp** (vector). **Canvas prints blurry** (rasterized at screen DPI). Convert Canvas to a high-DPI image before print:

```js
window.addEventListener("beforeprint", () => {
  const printDpr = 300 / 96; // 300 DPI for print
  const offscreen = document.createElement("canvas");
  offscreen.width = Math.round(width * printDpr);
  offscreen.height = Math.round(height * printDpr);
  const ctx = offscreen.getContext("2d");
  ctx.scale(printDpr, printDpr);
  renderChart(ctx, width, height); // reuse chart render logic
  const img = new Image();
  img.src = offscreen.toDataURL("image/png");
  img.style.width = "100%";
  img.classList.add("print-fallback");
  canvas.parentNode.insertBefore(img, canvas);
  canvas.style.display = "none";
});
window.addEventListener("afterprint", () => {
  document.querySelector(".print-fallback")?.remove();
  canvas.style.display = "";
});
```

For color-encoded data printed in grayscale, use pattern fills as a dual encoding — see `visual-texture` skill. Debug print styles in Chrome DevTools: Rendering panel → Emulate CSS media type → print.

## Common Pitfalls

**SVG `width="100%"` without viewBox.** Browser gives it a default 150px height. Always set explicit height or use viewBox.

**Hidden tabs/panels.** `getBoundingClientRect()` returns zero for `display: none` elements. Defer chart init until the tab is visible (IntersectionObserver or tab-switch event).

**Transitions interrupted by resize.** A running `d3.transition` gets cancelled when you re-binddata and re-render. Either skip transitions during resize (`if (resizing) duration = 0`) or let the transition finish before applying the new size.

**Forgetting cleanup.** ResizeObserver, matchMedia listeners, and requestAnimationFrame handles leak when the chart DOM is removed. Provide a `destroy()` function that disconnects them.

## Choosing the Right Responsive Approach

| Technique | Use when | Skip when |
|---|---|---|
| **viewBox scaling** | Decorative/iconic graphics without text | Any chart with axes, labels, or interaction |
| **ResizeObserver + redraw** | Production charts needing tick/label/layout adaptation | Static exports, fixed containers |
| **Container queries** | CSS adaptations (legend layout, font size, show/hide) | Data-level changes (tick count, scale recalc) |
| **Both CQ + ResizeObserver** | Chart components embedded in unknown contexts | Quick prototypes |
| **Debounced redraw** | Expensive renders (Canvas, WebGL, large data) | Simple SVG charts (< 100 elements) |
| **Layout switching** | Charts viewed across phone-to-desktop range | Fixed-context dashboards |

Observable Plot (as of March 2026) handles basic responsive sizing automatically via its `width` auto-detection, but D3 gives you control over layout switching, tick adaptation, and interaction fallbacks that Plot does not expose.

## References

- [High-DPI Canvas](https://web.dev/articles/canvas-hidipi)
- [Responsive charts (webkid)](https://webkid.io/blog/responsive-chart-usability-d3/) — practical D3 responsive patterns
