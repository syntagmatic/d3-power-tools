---
name: responsive
description: "Making D3.js visualizations responsive and adaptive. Use this skill when the user needs charts that resize with their container, adapt layout at different screen sizes, handle mobile/touch interactions, embed charts in iframes, support retina/HiDPI Canvas, print cleanly, or implement any resize-aware D3 visualization."
---

# Responsive Charts

The core principle: **observe the container, re-render the chart**. CSS handles layout; D3 handles drawing.

Related skills: `axes-and-scales` (tick formatting), `canvas` (DPI, layers), `small-multiples` (responsive reflow).

## ResizeObserver: Avoiding Infinite Loops

The most common bug: chart render changes the container's size, triggering the observer again. **Fix:** observe a wrapper div that doesn't change size with chart content.

```html
<div id="chart-wrapper" style="width: 100%; height: 400px; overflow: hidden;">
  <div id="chart-inner"></div>
</div>
```

```js
ro.observe(document.getElementById("chart-wrapper")); // fixed-size wrapper
// render into chart-inner — its content can't change wrapper's size
```

Alternatively, use `position: absolute` on the SVG so it doesn't affect container layout.

## viewBox vs Redraw-on-Resize

| | viewBox | Redraw-on-resize |
|---|---|---|
| Text | Scales with chart (gets tiny on mobile) | Stays readable at any size |
| Tick count | Fixed (may crowd or sparse) | Adapts to available space |
| Layout | Fixed (legend always on right) | Can reflow (legend moves below) |
| Performance | Excellent (no reflow cost) | Re-renders on every resize |

**Use redraw-on-resize** for any chart with text, axes, or interactive elements.

## Data-Driven Left Margin

Measure the widest tick label to avoid clipping:

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
  return Math.ceil(maxW) + 12;
}
```

## Brush Extent Remapping

When the chart resizes while a brush is active, the brush extent is in old pixel coordinates. Remap it:

```js
if (width >= 600) {
  g.append("g").call(d3.brushX().extent([[0,0],[w,h]]).on("brush end", brushed));
} else {
  // Range slider fallback on narrow screens
  d3.select("#chart").append("input").attr("type", "range")
    .attr("min", 0).attr("max", 100).style("width", "100%")
    .on("input", (e) => filterData(+e.target.value));
}
```

## Canvas DPI Handling

### The most common Canvas bug

```js
function setupCanvas(container, width, height) {
  const dpr = devicePixelRatio || 1;
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * dpr);   // backing store at physical pixels
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;        // CSS at logical pixels
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);                      // draw in CSS pixel coordinates
  container.appendChild(canvas);
  return ctx;
}
```

### Resizing Canvas resets all context state

Changing `canvas.width` or `canvas.height` resets transforms, styles, everything. **Must re-apply `ctx.scale(dpr, dpr)` and all custom state after every resize.**

### Detecting DPR changes (window dragged between displays)

```js
matchMedia(`(resolution: ${devicePixelRatio}dppx)`)
  .addEventListener("change", () => resizeAndRedraw(), { once: true });
```

## Iframe Embedding with postMessage

**Inside iframe (chart.html):**

```js
function render(width) {
  const height = Math.round(width * 0.5);
  // ... render chart
  window.parent.postMessage({ type: "chart-resize", height, id: "my-chart" }, "*");
}
const ro = new ResizeObserver(([e]) => {
  if (e.contentRect.width > 0) render(e.contentRect.width);
});
ro.observe(document.body);
```

**Host page:**

```js
window.addEventListener("message", (e) => {
  if (e.data.type === "chart-resize" && e.data.id === "my-chart")
    document.getElementById("chart-iframe").style.height = `${e.data.height}px`;
});
```

Sandbox: requires `allow-scripts`. Add `allow-same-origin` if the chart loads data from the same domain.

## Print Styles

```css
@media print {
  :root { --bg: #fff; --fg: #222; --grid: #ddd; }
  .tooltip, .controls, .brush, .zoom-buttons, button, input, select {
    display: none !important;
  }
  #chart {
    width: 100% !important; max-width: none !important;
    break-inside: avoid; page-break-inside: avoid;
  }
}
```

Canvas prints poorly. Convert to image before print:

```js
window.addEventListener("beforeprint", () => {
  const img = document.createElement("img");
  img.src = canvas.toDataURL("image/png"); img.style.width = "100%";
  img.classList.add("print-fallback");
  canvas.parentNode.insertBefore(img, canvas);
  canvas.style.display = "none";
});
window.addEventListener("afterprint", () => {
  document.querySelector(".print-fallback")?.remove();
  canvas.style.display = "";
});
```

## Architecture: The Render Function Pattern

All chart logic in a single function that takes dimensions. For charts with expensive data processing, separate prep from rendering:

```js
const processed = processData(rawData); // compute once
function render(width, height) { drawChart(processed, width, height); } // cheap on resize
```

## Performance

**Debounce vs throttle.** Debounce (render at final size) is almost always right. Throttle (render during resize) only for live-preview in resizable panels.

**Layout thrashing.** Batch DOM reads before writes. Interleaving `clientWidth` reads with style writes forces synchronous layout recalculation.

**Mobile address bar resize.** Address bar show/hide triggers resize with height change but no width change. Skip if width hasn't changed:

```js
let lastWidth = 0;
const ro = new ResizeObserver(([entry]) => {
  const w = entry.contentRect.width;
  if (Math.abs(w - lastWidth) < 1) return;
  lastWidth = w;
  debouncedRender(w, entry.contentRect.height);
});
```

## Common Pitfalls

**ResizeObserver loop error.** Chart render changes container height, observer fires again. Fix: observe a fixed-size wrapper, render inside a child element.

**Canvas blurriness on retina.** Must set `canvas.width = w * dpr`, `canvas.height = h * dpr`, then `ctx.scale(dpr, dpr)`. CSS dimensions stay at `w`/`h`. Forgetting any of these three steps produces blurry output.

**Text doesn't scale with viewBox.** 14px text at 960px becomes 7px at 480px. Use redraw-on-resize for text-heavy charts.

**SVG `width="100%"` without viewBox.** Collapses to 150px tall (browser default). Always set explicit height or use viewBox.

**Hidden tabs/panels.** `getBoundingClientRect()` returns zero for `display: none` elements. Defer rendering until visible using IntersectionObserver.

**Transition interruption on resize.** Active D3 transitions get interrupted by re-render. Skip transitions during resize or cancel them explicitly.

**Forgetting cleanup.** ResizeObserver, event listeners, and setTimeout handles leak when charts are removed. Always provide a destroy function.

## References

- [High-DPI Canvas](https://web.dev/articles/canvas-hidipi) — crisp Canvas on retina displays
- [postMessage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage) — iframe communication
- [Interaction Media Features](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/hover) — hover and pointer capability queries
