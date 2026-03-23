---
name: responsive-charts
description: "Making D3.js visualizations responsive and adaptive. Use this skill when the user needs charts that resize with their container, adapt layout at different screen sizes, handle mobile/touch interactions, embed charts in iframes, support retina/HiDPI Canvas, print cleanly, or implement any resize-aware D3 visualization. Covers ResizeObserver lifecycle, container-based sizing, viewBox vs redraw-on-resize, aspect ratio strategies, responsive margins, breakpoint-driven layout changes, responsive text and labels, touch adaptation, Canvas DPI handling, iframe embedding with postMessage, and print styles."
---

# Responsive Charts

Patterns for making D3 visualizations adapt to any container size, device, and context. The core principle: **observe the container, re-render the chart**. CSS handles layout; D3 handles drawing.

Related skills: `axes-and-scales` (tick formatting, label collision), `canvas-rendering` (DPI, layer architecture), `small-multiples` (responsive reflow), `sparkcharts` (inline sizing), `color-themes` (media queries, CSS custom properties), `zoom-and-pan` (touch gestures).

```
container resizes (CSS, window, iframe)
         |
    ResizeObserver fires
         |
    debounce (100-150ms)
         |
    render(width, height)
         |
    scales + axes + data redraw
```

## ResizeObserver Lifecycle

ResizeObserver is the correct API for responsive D3 charts. It fires when an element's size changes regardless of cause (window resize, sidebar toggle, CSS animation, iframe resize).

### Debounced setup (recommended)

```js
const container = document.getElementById("chart");
let resizeTimer;
const ro = new ResizeObserver(([entry]) => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const { width, height } = entry.contentRect;
    if (width > 0 && height > 0) render(width, height);
  }, 150);
});
ro.observe(container);
```

`entry.contentRect` returns the content box (excluding padding). For border-box dimensions, pass `{ box: "border-box" }` to `observe()` and read `entry.borderBoxSize[0].inlineSize` / `.blockSize`.

### Cleanup

```js
function destroyChart() {
  ro.disconnect();
  clearTimeout(resizeTimer);
  container.innerHTML = "";
}
```

### Avoiding infinite resize loops

The chart render changes the container's size, which triggers the observer, which renders again. **Fix:** observe a wrapper div that doesn't change size with chart content.

```html
<div id="chart-wrapper" style="width: 100%; height: 400px; overflow: hidden;">
  <div id="chart-inner"></div>
</div>
```

```js
ro.observe(document.getElementById("chart-wrapper")); // fixed-size wrapper
// render into chart-inner — its content can't change wrapper's size
```

Alternatively, use `position: absolute` on the SVG so it doesn't affect container layout:

```css
#chart { position: relative; }
#chart svg { position: absolute; top: 0; left: 0; }
```

## Container-Based Sizing

Read dimensions from the container, not the window. The chart doesn't know what's around it.

### viewBox scaling vs redraw-on-resize

**viewBox** — draw once, scale everything:

```js
const svg = d3.select("#chart").append("svg")
  .attr("viewBox", `0 0 960 540`)
  .attr("preserveAspectRatio", "xMidYMid meet")
  .style("width", "100%").style("height", "auto");
```

| | viewBox | Redraw-on-resize |
|---|---|---|
| Text | Scales with chart (gets tiny on mobile) | Stays readable at any size |
| Tick count | Fixed (may crowd or sparse) | Adapts to available space |
| Layout | Fixed (legend always on right) | Can reflow (legend moves below) |
| Performance | Excellent (no reflow cost) | Re-renders on every resize |
| Best for | Icons, logos, simple diagrams | Data-heavy charts, dashboards |

**Recommendation:** Use redraw-on-resize for any chart with text, axes, or interactive elements.

## Aspect Ratio Strategies

### Fixed aspect ratio with max-width (most common)

```css
#chart { width: 100%; max-width: 960px; aspect-ratio: 16 / 9; }
```

Fallback for older browsers — padding-bottom trick:

```css
#chart-wrapper { width: 100%; max-width: 960px; position: relative; }
#chart-wrapper::before { content: ""; display: block; padding-bottom: 56.25%; }
#chart { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
```

### Other patterns

- **Fluid width, fixed height:** `width: 100%; height: 300px;` — common for dashboards
- **Fully fluid:** `width: 100%; height: 100%; min-height: 200px;` — full-screen visualizations
- **Square:** `width: min(100%, 600px); aspect-ratio: 1;` — scatterplots, correlation matrices

## Responsive Margin Convention

Static margins waste space on small screens. Scale them with the container.

```js
function getMargins(width, height) {
  return {
    top: Math.max(20, height * 0.05),
    right: Math.max(15, width * 0.03),
    bottom: Math.max(30, height * 0.08),
    left: Math.max(40, width * 0.06),
  };
}
```

For data-driven left margin, measure the widest tick label:

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
  return Math.ceil(maxW) + 12; // tick marks + gap
}
```

## Breakpoint-Driven Layout

Different chart configurations at different widths.

```js
function getConfig(width) {
  if (width < 480) return {
    tickCount: 3, legendPosition: "bottom", showGridlines: false,
    barOrientation: "horizontal", fontSize: 11, showAnnotations: false,
  };
  if (width < 768) return {
    tickCount: 5, legendPosition: "bottom", showGridlines: true,
    barOrientation: "vertical", fontSize: 12, showAnnotations: false,
  };
  return {
    tickCount: 8, legendPosition: "right", showGridlines: true,
    barOrientation: "vertical", fontSize: 14, showAnnotations: true,
  };
}
```

### Legend position switching

```js
function renderLegend(g, colorScale, config, plotWidth, plotHeight) {
  const legend = g.append("g").attr("class", "legend");
  if (config.legendPosition === "right") {
    legend.attr("transform", `translate(${plotWidth + 16}, 0)`);
    colorScale.domain().forEach((d, i) => {
      const row = legend.append("g").attr("transform", `translate(0, ${i * 20})`);
      row.append("rect").attr("width", 12).attr("height", 12).attr("fill", colorScale(d));
      row.append("text").attr("x", 18).attr("y", 10).attr("font-size", "12px").text(d);
    });
  } else {
    legend.attr("transform", `translate(0, ${plotHeight + 36})`);
    let xOff = 0;
    colorScale.domain().forEach(d => {
      const item = legend.append("g").attr("transform", `translate(${xOff}, 0)`);
      item.append("rect").attr("width", 10).attr("height", 10).attr("fill", colorScale(d));
      item.append("text").attr("x", 14).attr("y", 10).attr("font-size", "11px").text(d);
      xOff += 14 + d.length * 7 + 12;
    });
  }
}
```

## Responsive Text

### Tick label collision — detect and rotate

```js
function fitXLabels(axisGroup) {
  const labels = axisGroup.selectAll(".tick text").nodes();
  for (let i = 1; i < labels.length; i++) {
    const prev = labels[i - 1].getBoundingClientRect();
    const curr = labels[i].getBoundingClientRect();
    if (prev.right > curr.left - 4) {
      axisGroup.selectAll(".tick text")
        .attr("text-anchor", "end").attr("dx", "-0.5em")
        .attr("dy", "0.3em").attr("transform", "rotate(-45)");
      return;
    }
  }
}
```

### Abbreviating labels and responsive font sizing

```js
const fmt = width < 480 ? d3.timeFormat("%b") : d3.timeFormat("%B");
const fontSize = Math.max(10, Math.min(14, width * 0.015));
```

CSS clamp for text that doesn't need JS:

```css
.chart-title { font-size: clamp(14px, 2vw, 22px); }
.axis-label  { font-size: clamp(10px, 1.5vw, 14px); }
```

## Responsive Interaction

### Pointer events unify mouse and touch — but hover doesn't exist on touch

```css
@media (hover: hover) { .bar:hover { opacity: 0.8; } }
```

```js
const hasHover = matchMedia("(hover: hover)").matches;
if (hasHover) {
  bars.on("pointerenter", showTooltip).on("pointerleave", hideTooltip);
} else {
  bars.on("pointerdown", showTooltip);
  svg.on("pointerdown", (e) => { if (!e.target.closest(".bar")) hideTooltip(); });
}
```

### Minimum 44px hit targets on touch

```js
const pad = ("ontouchstart" in window) ? 22 : 4;
g.selectAll(".hit-target").data(data).join("rect")
  .attr("x", d => xScale(d.x) - pad).attr("y", d => yScale(d.y) - pad)
  .attr("width", pad * 2).attr("height", pad * 2)
  .attr("fill", "none").attr("pointer-events", "all")
  .on("pointerenter", (e, d) => showTooltip(d))
  .on("pointerleave", hideTooltip);
```

### Adaptive tooltip positioning

```js
function positionTooltip(tooltip, event, containerWidth) {
  if (containerWidth < 480) {
    // Bottom sheet on narrow screens
    tooltip.style("position", "fixed").style("bottom", "0").style("left", "0")
      .style("right", "0").style("top", "auto").style("width", "100%");
  } else {
    const [mx, my] = d3.pointer(event, document.body);
    tooltip.style("position", "absolute")
      .style("left", `${mx + 12}px`).style("top", `${my - 28}px`).style("width", "auto");
  }
}
```

### Brush adaptation

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

## Canvas Responsiveness

### devicePixelRatio handling (the most common Canvas bug)

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

### Resizing Canvas

Changing `canvas.width` or `canvas.height` resets all context state. Must re-apply `ctx.scale(dpr, dpr)` and any custom state after resize.

### Detecting DPR changes (window dragged between displays)

```js
matchMedia(`(resolution: ${devicePixelRatio}dppx)`)
  .addEventListener("change", () => resizeAndRedraw(), { once: true });
```

## Iframe Embedding

### Self-sizing embedded chart

**Inside iframe (chart.html):**

```js
function render(width) {
  const height = Math.round(width * 0.5);
  // ... render chart

  // Report height to host
  window.parent.postMessage({ type: "chart-resize", height, id: "my-chart" }, "*");
}

const ro = new ResizeObserver(([e]) => {
  if (e.contentRect.width > 0) render(e.contentRect.width);
});
ro.observe(document.body);
```

**Host page:**

```js
const iframe = document.getElementById("chart-iframe");
window.addEventListener("message", (e) => {
  if (e.data.type === "chart-resize" && e.data.id === "my-chart")
    iframe.style.height = `${e.data.height}px`;
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
  .axis text { fill: #222 !important; }
  .axis line, .axis path { stroke: #444 !important; }
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

## Interaction Recipes

### Responsive line chart

```js
function renderLineChart(container, data, width, height) {
  const config = getConfig(width);
  const margin = { top: 20, right: 20, bottom: 30, left: config.tickCount > 5 ? 50 : 35 };
  const w = width - margin.left - margin.right;
  const h = height - margin.top - margin.bottom;

  d3.select(container).selectAll("*").remove();
  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x = d3.scaleTime().domain(d3.extent(data, d => d.date)).range([0, w]);
  const y = d3.scaleLinear().domain([0, d3.max(data, d => d.value)]).nice().range([h, 0]);

  g.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(config.tickCount).tickSizeOuter(0));
  g.append("g").call(d3.axisLeft(y).ticks(config.tickCount));

  g.append("path").datum(data)
    .attr("fill", "none").attr("stroke", "steelblue").attr("stroke-width", 1.5)
    .attr("d", d3.line().x(d => x(d.date)).y(d => y(d.value)).curve(d3.curveMonotoneX));

  // Tooltip adapts to width
  const tooltip = d3.select(container).append("div").attr("class", "tooltip").style("display", "none");
  const bisect = d3.bisector(d => d.date).left;
  g.append("rect").attr("width", w).attr("height", h)
    .attr("fill", "none").attr("pointer-events", "all")
    .on("pointermove", (event) => {
      const [mx] = d3.pointer(event);
      const d = data[bisect(data, x.invert(mx), 1)];
      tooltip.style("display", null).html(`${d3.timeFormat("%b %d")(d.date)}: ${d.value}`);
      positionTooltip(tooltip, event, width);
    })
    .on("pointerleave", () => tooltip.style("display", "none"));
}
```

### Responsive bar chart — horizontal on mobile, vertical on desktop

```js
function renderBarChart(container, data, width, height) {
  const horiz = width < 480;
  const margin = horiz ? { top: 10, right: 20, bottom: 20, left: 80 }
                       : { top: 10, right: 10, bottom: 60, left: 40 };
  const w = width - margin.left - margin.right;
  const h = height - margin.top - margin.bottom;

  d3.select(container).selectAll("*").remove();
  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  if (horiz) {
    const x = d3.scaleLinear().domain([0, d3.max(data, d => d.value)]).nice().range([0, w]);
    const y = d3.scaleBand().domain(data.map(d => d.label)).range([0, h]).padding(0.2);
    g.append("g").call(d3.axisLeft(y));
    g.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x).ticks(4));
    g.selectAll("rect").data(data).join("rect")
      .attr("y", d => y(d.label)).attr("width", d => x(d.value)).attr("height", y.bandwidth())
      .attr("fill", "steelblue");
  } else {
    const x = d3.scaleBand().domain(data.map(d => d.label)).range([0, w]).padding(0.2);
    const y = d3.scaleLinear().domain([0, d3.max(data, d => d.value)]).nice().range([h, 0]);
    const ax = g.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x));
    ax.selectAll("text").attr("text-anchor", "end").attr("transform", "rotate(-45)");
    g.append("g").call(d3.axisLeft(y));
    g.selectAll("rect").data(data).join("rect")
      .attr("x", d => x(d.label)).attr("y", d => y(d.value))
      .attr("width", x.bandwidth()).attr("height", d => h - y(d.value))
      .attr("fill", "steelblue");
  }
}
```

### Responsive dashboard — CSS Grid + ResizeObserver

```css
.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px; padding: 16px;
}
.panel { min-height: 250px; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }
```

```js
[
  { el: "#panel-line", render: renderLineChart, data: lineData },
  { el: "#panel-bar", render: renderBarChart, data: barData },
].forEach(({ el, render, data }) => {
  const container = document.querySelector(el);
  let timer;
  const ro = new ResizeObserver(([entry]) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) render(container, data, width, height);
    }, 150);
  });
  ro.observe(container);
});
```

## Architecture Patterns

### The render function pattern

All chart logic in a single function that takes dimensions. The foundation of responsive D3.

```js
function render(width, height) {
  const margin = getMargins(width, height);
  const w = width - margin.left - margin.right;
  const h = height - margin.top - margin.bottom;
  d3.select("#chart").selectAll("*").remove();
  const svg = d3.select("#chart").append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  // scales, axes, data joins — all using w, h
}
```

For charts with expensive data processing, separate prep from rendering:

```js
const processed = processData(rawData); // compute once
function render(width, height) { drawChart(processed, width, height); } // cheap on resize
```

### CSS custom properties for responsive theming

```css
:root { --chart-font: 14px; --chart-stroke: 1.5; --chart-dot-r: 4; }
@media (max-width: 480px) { :root { --chart-font: 11px; --chart-stroke: 1; --chart-dot-r: 3; } }
```

```js
const styles = getComputedStyle(document.documentElement);
const fontSize = parseFloat(styles.getPropertyValue("--chart-font"));
```

### Progressive enhancement

```js
const svg = renderStaticChart(container, data, width, height);
if (matchMedia("(hover: hover) and (pointer: fine)").matches) {
  addTooltips(svg, data);
  addBrush(svg, data);
}
if ("ontouchstart" in window) { addTapToSelect(svg, data); }
```

## Performance

### Debounce vs throttle

**Debounce** (render at final size) is almost always right. **Throttle** (render during resize at capped rate) is useful for live preview in resizable panels.

### Avoiding layout thrashing

Batch DOM reads before writes. Interleaving forces synchronous layout recalculation.

```js
// Bad: read-write-read-write forces 2 layouts
const w1 = el1.clientWidth; el1.style.height = w1 + "px";
const w2 = el2.clientWidth; el2.style.height = w2 + "px";
// Good: batch reads, then batch writes
const w1 = el1.clientWidth; const w2 = el2.clientWidth;
el1.style.height = w1 + "px"; el2.style.height = w2 + "px";
```

### Conditional rendering at small sizes

Skip decorative elements below size thresholds:

```js
if (w > 400) drawGridlines(g, y, w);
if (w > 600) drawPointLabels(g, data, x, y);
```

### ResizeObserver vs window.onresize

| | ResizeObserver | window.onresize |
|---|---|---|
| Scope | Per element | Global |
| Sidebar toggle | Fires | Does not fire |
| Iframe resize | Fires | Does not fire |

Always prefer ResizeObserver.

## Common Pitfalls

**ResizeObserver loop error.** Chart render changes container height, observer fires again. Fix: observe a fixed-size wrapper, render inside a child element. Or use `overflow: hidden` on the observed element.

**Canvas blurriness on retina.** Must set `canvas.width = w * dpr`, `canvas.height = h * dpr`, then `ctx.scale(dpr, dpr)`. CSS dimensions stay at `w`/`h`. Forgetting any of these three steps produces blurry output.

**Text doesn't scale with viewBox.** 14px text at 960px becomes 7px at 480px. Unreadable. Use redraw-on-resize for text-heavy charts.

**Touch vs mouse.** Pointer events unify them, but hover states don't exist on touch. Use `@media (hover: hover)` to gate hover-only interactions.

**Mobile address bar resize.** Address bar show/hide triggers resize with height change but no width change. Debounce, and optionally skip if width hasn't changed:

```js
let lastWidth = 0;
const ro = new ResizeObserver(([entry]) => {
  const w = entry.contentRect.width;
  if (Math.abs(w - lastWidth) < 1) return;
  lastWidth = w;
  debouncedRender(w, entry.contentRect.height);
});
```

**SVG `width="100%"` without viewBox.** Collapses to 150px tall (browser default). Always set explicit height or use viewBox.

**Hidden tabs/panels.** `getBoundingClientRect()` returns zero for `display: none` elements. Defer rendering until visible using IntersectionObserver:

```js
const io = new IntersectionObserver(([entry]) => {
  if (entry.isIntersecting) { initChart(entry.target); io.unobserve(entry.target); }
});
io.observe(document.getElementById("chart"));
```

**Transition interruption on resize.** Active D3 transitions get interrupted by re-render. Skip transitions during resize or cancel them explicitly before clearing.

**Forgetting cleanup.** ResizeObserver, event listeners, and setTimeout handles leak when charts are removed. Always provide a destroy function.

## References

- [ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver) — MDN reference
- [CSS aspect-ratio](https://developer.mozilla.org/en-US/docs/Web/CSS/aspect-ratio) — intrinsic ratio without padding trick
- [High-DPI Canvas](https://web.dev/articles/canvas-hidipi) — crisp Canvas on retina displays
- [Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events) — unified mouse/touch/pen API
- [postMessage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage) — iframe communication
- [CSS Grid Layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout) — responsive dashboard grids
- [Interaction Media Features](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/hover) — hover and pointer capability queries
