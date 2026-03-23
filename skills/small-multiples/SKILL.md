---
name: small-multiples
description: "Build small multiples (trellis/faceted) layouts with D3.js. Use this skill when the user wants to show the same chart repeated across categories, faceted grids, trellis plots, panel charts, or lattice displays. Covers grid layout calculation, shared vs independent scales, synchronized interactions, responsive reflow, and Canvas-based small multiples for large facet counts."
---

# Small Multiples

Patterns for building small multiples (trellis, faceted, lattice) layouts with D3. Covers grid layout math, scale strategies, faceting approaches, synchronized interaction, responsive reflow, Canvas rendering, and scroll-based patterns.

For axes and tick formatting, see `axes-and-scales`. For brushing and cross-chart linking, see `brushing-and-selection`. For canvas rendering patterns, see `canvas-rendering`.

## Grid Layout Math

Small multiples arrange N panels in a grid. The core problem: given N facets and a container width, compute rows, columns, and cell dimensions.

### Column count from container width

```js
const minCellWidth = 200; // minimum readable panel width
const gap = 12;
const cols = Math.max(1, Math.floor((containerWidth + gap) / (minCellWidth + gap)));
const rows = Math.ceil(n / cols);
```

### Cell sizing with margins

Each cell has its own margin for axes/labels. The outer container has padding for the overall title.

```js
const containerPadding = { top: 40, right: 20, bottom: 20, left: 20 };
const cellMargin = { top: 24, right: 8, bottom: 24, left: 40 };
const gap = 12;

const availableWidth = containerWidth - containerPadding.left - containerPadding.right;
const cellWidth = (availableWidth - gap * (cols - 1)) / cols;
const cellHeight = cellWidth * 0.6; // aspect ratio

const plotWidth = cellWidth - cellMargin.left - cellMargin.right;
const plotHeight = cellHeight - cellMargin.top - cellMargin.bottom;
```

### Positioning cells in the grid

```js
const cellX = (i) => containerPadding.left + (i % cols) * (cellWidth + gap);
const cellY = (i) => containerPadding.top + Math.floor(i / cols) * (cellHeight + gap);
```

### CSS Grid alternative — let the browser handle reflow

```css
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 20px;
}
.cell { aspect-ratio: 5 / 3; }
```

Then render an SVG inside each cell with D3. This is the recommended approach for responsive layouts — CSS Grid handles column count automatically.

## Scale Strategies

The most important design decision: should all panels share the same scales?

### Shared scales — enables comparison across facets

All panels use the same x and y domain. A difference in one panel is visually comparable to another.

```js
const xDomain = d3.extent(allData, d => d.date);
const yDomain = [0, d3.max(allData, d => d.value)];

const xScale = d3.scaleTime().domain(xDomain);
const yScale = d3.scaleLinear().domain(yDomain).nice();

// Set range per cell
facets.forEach((data, i) => {
  const x = xScale.copy().range([0, plotWidth]);
  const y = yScale.copy().range([plotHeight, 0]);
  renderPanel(data, x, y, i);
});
```

**When to use:** Comparing magnitudes across categories. "Which city has the highest temperature?"

### Independent scales — shows local patterns

Each panel has its own domain, normalized to fill the available space.

```js
facets.forEach((data, i) => {
  const x = d3.scaleTime()
    .domain(d3.extent(data, d => d.date))
    .range([0, plotWidth]);
  const y = d3.scaleLinear()
    .domain(d3.extent(data, d => d.value))
    .nice()
    .range([plotHeight, 0]);
  renderPanel(data, x, y, i);
});
```

**When to use:** Showing shape/trend within each category. "Does this city have a seasonal pattern?"

**Warning:** Independent y-scales are misleading when viewers assume panels are comparable. Always label axes clearly or add a visual cue (different axis color, annotation).

### Hybrid — shared x, independent y

Common for time series with different units or magnitudes (e.g., temperature vs precipitation).

```js
const sharedX = d3.scaleTime().domain(d3.extent(allData, d => d.date));

facets.forEach((data, i) => {
  const x = sharedX.copy().range([0, plotWidth]);
  const y = d3.scaleLinear()
    .domain(d3.extent(data, d => d.value)).nice()
    .range([plotHeight, 0]);
  renderPanel(data, x, y, i);
});
```

## Faceting Approaches

### By category — one chart per group

The most common pattern. Split data by a categorical variable.

```js
const grouped = d3.group(data, d => d.category);
const facets = Array.from(grouped, ([key, values]) => ({ key, values }));
facets.sort((a, b) => d3.ascending(a.key, b.key));
```

### By variable — one chart per metric

Each panel shows a different measure for the same entities.

```js
const metrics = ["temperature", "humidity", "pressure", "windSpeed"];
const facets = metrics.map(metric => ({
  key: metric,
  values: data.map(d => ({ date: d.date, value: d[metric] }))
}));
```

### Cross-tabulation — row x col grid (facet_grid)

Like ggplot's `facet_grid`: one variable maps to rows, another to columns.

```js
const rowVar = d => d.region;   // e.g., North, South
const colVar = d => d.quarter;  // e.g., Q1, Q2, Q3, Q4

const rowKeys = [...new Set(data.map(rowVar))].sort();
const colKeys = [...new Set(data.map(colVar))].sort();

const nested = d3.group(data, rowVar, colVar);

rowKeys.forEach((row, ri) => {
  colKeys.forEach((col, ci) => {
    const cellData = nested.get(row)?.get(col) ?? [];
    const x = ci * (cellWidth + gap);
    const y = ri * (cellHeight + gap);
    renderPanel(cellData, x, y, row, col);
  });
});
```

Add row labels on the left and column labels on top:

```js
// Row labels — centered vertically on left edge
rowKeys.forEach((row, ri) => {
  svg.append("text")
    .attr("x", -10)
    .attr("y", ri * (cellHeight + gap) + cellHeight / 2)
    .attr("text-anchor", "end")
    .attr("dominant-baseline", "middle")
    .text(row);
});

// Column labels — centered horizontally on top edge
colKeys.forEach((col, ci) => {
  svg.append("text")
    .attr("x", ci * (cellWidth + gap) + cellWidth / 2)
    .attr("y", -10)
    .attr("text-anchor", "middle")
    .text(col);
});
```

## Synchronized Interaction

The key UX pattern: interacting with one panel affects all panels simultaneously.

### Shared crosshair — hover one panel, see position in all

```js
const crosshairs = panels.append("line")
  .attr("class", "crosshair")
  .attr("y1", 0).attr("y2", plotHeight)
  .attr("stroke", "#999").attr("stroke-dasharray", "3,3")
  .style("display", "none");

panels.append("rect")
  .attr("class", "overlay")
  .attr("width", plotWidth).attr("height", plotHeight)
  .attr("fill", "none").attr("pointer-events", "all")
  .on("pointermove", (event) => {
    const [mx] = d3.pointer(event);
    // Broadcast to ALL panels
    crosshairs.attr("x1", mx).attr("x2", mx).style("display", null);
    // Find nearest data point using bisector
    const date = xScale.invert(mx);
    updateTooltips(date);
  })
  .on("pointerleave", () => {
    crosshairs.style("display", "none");
    hideTooltips();
  });
```

### Shared brush — brush in one panel filters all

```js
const brush = d3.brushX()
  .extent([[0, 0], [plotWidth, plotHeight]])
  .on("brush end", (event) => {
    if (!event.sourceEvent) return; // prevent loops
    const selection = event.selection;
    if (!selection) { resetAll(); return; }
    const [x0, x1] = selection.map(xScale.invert);

    // Apply to all panels
    panels.each(function(facet) {
      const panel = d3.select(this);
      panel.selectAll(".data-line")
        .attr("opacity", d => (d.date >= x0 && d.date <= x1) ? 1 : 0.2);
    });

    // Move brush in other panels (without triggering events)
    panels.selectAll(".brush")
      .filter(function() { return this !== event.target; })
      .call(brush.move, selection);
  });
```

### Shared tooltip — single tooltip follows mouse across panels

```js
const tooltip = d3.select("body").append("div")
  .attr("class", "tooltip")
  .style("position", "absolute")
  .style("display", "none");

function updateTooltips(date) {
  const bisect = d3.bisector(d => d.date).left;
  panels.each(function(facet) {
    const i = bisect(facet.values, date);
    const d = facet.values[i];
    // Highlight point in this panel
    d3.select(this).select(".hover-dot")
      .attr("cx", xScale(d.date))
      .attr("cy", yScale(d.value))
      .style("display", null);
  });
  // Position tooltip near cursor
  tooltip.style("display", null)
    .html(`<strong>${d3.timeFormat("%b %Y")(date)}</strong>`);
}
```

### Linked zoom — zoom one panel zooms all

```js
const zoom = d3.zoom()
  .scaleExtent([1, 10])
  .on("zoom", (event) => {
    if (!event.sourceEvent) return; // prevent loops
    const transform = event.transform;
    panels.each(function() {
      d3.select(this).call(zoom.transform, transform);
    });
    // Rescale axes
    const newX = transform.rescaleX(xScale);
    updateAllPanels(newX);
  });
```

## Label and Axis Efficiency

Redundant axes waste space and add clutter. Only show axes where necessary.

### Y-axis only on leftmost column

```js
facets.forEach((facet, i) => {
  const col = i % cols;
  const row = Math.floor(i / cols);
  const isLeftEdge = col === 0;
  const isBottomEdge = row === rows - 1 || i >= n - cols;

  if (isLeftEdge) {
    panel.append("g").call(d3.axisLeft(yScale).ticks(4));
  }
  if (isBottomEdge) {
    panel.append("g")
      .attr("transform", `translate(0,${plotHeight})`)
      .call(d3.axisBottom(xScale).ticks(4));
  }
});
```

### Facet titles above each panel

```js
panel.append("text")
  .attr("x", plotWidth / 2)
  .attr("y", -8)
  .attr("text-anchor", "middle")
  .attr("font-size", "12px")
  .attr("font-weight", "600")
  .text(facet.key);
```

### Shared axis labels — one label for the whole grid

```js
// Single y-axis label for the entire grid
svg.append("text")
  .attr("transform", "rotate(-90)")
  .attr("x", -totalHeight / 2)
  .attr("y", 12)
  .attr("text-anchor", "middle")
  .text("Value (units)");

// Single x-axis label
svg.append("text")
  .attr("x", totalWidth / 2)
  .attr("y", totalHeight + containerPadding.bottom - 4)
  .attr("text-anchor", "middle")
  .text("Date");
```

## Responsive Reflow

### CSS Grid + D3 hybrid (recommended)

Let CSS Grid handle column count and cell sizing. Use ResizeObserver to re-render D3 content when cells resize.

```js
const container = document.querySelector(".grid");

const ro = new ResizeObserver(entries => {
  for (const entry of entries) {
    const cell = entry.target;
    const { width, height } = entry.contentRect;
    rerenderPanel(cell, width, height);
  }
});

document.querySelectorAll(".cell").forEach(cell => ro.observe(cell));
```

### Column count breakpoints (manual)

```js
function getColumnCount(width) {
  if (width < 480) return 1;
  if (width < 768) return 2;
  if (width < 1200) return 3;
  return 4;
}

const ro = new ResizeObserver(([entry]) => {
  const width = entry.contentRect.width;
  const newCols = getColumnCount(width);
  if (newCols !== currentCols) {
    currentCols = newCols;
    relayout();
  }
});
ro.observe(container);
```

### Debouncing relayout

```js
let resizeTimer;
const ro = new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(relayout, 100);
});
```

## Canvas Small Multiples

For large facet counts (50+) or data-dense panels, Canvas outperforms SVG.

### One Canvas per facet

Simple to implement. Each canvas is independent. Good for up to ~100 facets.

```js
cells.forEach((facet, i) => {
  const canvas = document.createElement("canvas");
  canvas.width = cellWidth * devicePixelRatio;
  canvas.height = cellHeight * devicePixelRatio;
  canvas.style.width = cellWidth + "px";
  canvas.style.height = cellHeight + "px";
  container.appendChild(canvas);

  const ctx = canvas.getContext("2d");
  ctx.scale(devicePixelRatio, devicePixelRatio);
  renderCanvasPanel(ctx, facet, xScale, yScale, plotWidth, plotHeight);
});
```

### Shared Canvas with viewport clipping

One large canvas, clip each panel region. Better for 100+ facets — fewer DOM elements.

```js
const canvas = document.createElement("canvas");
canvas.width = totalWidth * devicePixelRatio;
canvas.height = totalHeight * devicePixelRatio;
const ctx = canvas.getContext("2d");
ctx.scale(devicePixelRatio, devicePixelRatio);

facets.forEach((facet, i) => {
  const x = cellX(i) + cellMargin.left;
  const y = cellY(i) + cellMargin.top;

  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, plotWidth, plotHeight);
  ctx.clip();
  ctx.translate(x, y);

  // Draw data within clipped region
  renderLine(ctx, facet.values, xScale, yScale);

  ctx.restore();
});
```

### Performance tradeoffs

| Approach | Facets | DOM elements | Hit detection | Interaction |
|---|---|---|---|---|
| SVG per facet | < 50 | N * elements/facet | Built-in | Easy (D3 events) |
| Canvas per facet | 50–200 | N canvases | Manual per canvas | Moderate |
| Shared Canvas | 200+ | 1 canvas | Global quadtree | Complex |

For shared canvas interaction, determine which cell the pointer is over from pixel coordinates, then do local hit detection within that cell.

```js
canvas.addEventListener("pointermove", (event) => {
  const rect = canvas.getBoundingClientRect();
  const mx = event.clientX - rect.left;
  const my = event.clientY - rect.top;

  // Which cell?
  const col = Math.floor((mx - containerPadding.left) / (cellWidth + gap));
  const row = Math.floor((my - containerPadding.top) / (cellHeight + gap));
  const idx = row * cols + col;
  if (idx < 0 || idx >= n) return;

  // Local coordinates within the cell
  const localX = mx - cellX(idx) - cellMargin.left;
  const localY = my - cellY(idx) - cellMargin.top;

  if (localX < 0 || localX > plotWidth || localY < 0 || localY > plotHeight) return;
  handleHover(idx, localX, localY);
});
```

## Scroll-Based Patterns

### Vertical scroll with sticky facet header

For many facets (20+), scroll vertically with a sticky header showing the current facet range.

```css
.grid-container {
  max-height: 80vh;
  overflow-y: auto;
}
.grid-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
}
```

### Lazy rendering — only render visible facets

Use IntersectionObserver to render panels as they scroll into view.

```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !entry.target.dataset.rendered) {
      const idx = +entry.target.dataset.index;
      renderPanel(entry.target, facets[idx]);
      entry.target.dataset.rendered = "true";
    }
  });
}, { rootMargin: "200px" }); // pre-render 200px ahead

document.querySelectorAll(".cell").forEach(cell => observer.observe(cell));
```

### Virtual scrolling for 1000+ facets

Only create DOM elements for visible facets. Recycle elements as the user scrolls.

```js
const visibleRows = Math.ceil(containerHeight / (cellHeight + gap)) + 1;
const visibleCells = visibleRows * cols;

container.addEventListener("scroll", () => {
  const scrollTop = container.scrollTop;
  const startRow = Math.floor(scrollTop / (cellHeight + gap));
  const startIdx = startRow * cols;

  // Reposition and re-render only visible cells
  for (let i = 0; i < visibleCells && startIdx + i < n; i++) {
    const idx = startIdx + i;
    const cell = cellPool[i];
    cell.style.transform = `translate(${cellX(idx)}px, ${cellY(idx)}px)`;
    if (cell.dataset.facet !== String(idx)) {
      rerenderPanel(cell, facets[idx]);
      cell.dataset.facet = String(idx);
    }
  }
});

// Set total scrollable height
spacer.style.height = `${rows * (cellHeight + gap) - gap}px`;
```

## Rendering a Panel

### SVG line chart panel — the common case

```js
function renderPanel(container, facet, xScale, yScale) {
  const svg = d3.select(container).append("svg")
    .attr("width", cellWidth).attr("height", cellHeight);

  const g = svg.append("g")
    .attr("transform", `translate(${cellMargin.left},${cellMargin.top})`);

  // Gridlines
  g.append("g").attr("class", "grid")
    .call(d3.axisLeft(yScale).ticks(4).tickSize(-plotWidth).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll("line").attr("stroke", "#e0e0e0"));

  // Line
  const line = d3.line()
    .x(d => xScale(d.date))
    .y(d => yScale(d.value))
    .curve(d3.curveMonotoneX);

  g.append("path")
    .datum(facet.values)
    .attr("d", line)
    .attr("fill", "none")
    .attr("stroke", "steelblue")
    .attr("stroke-width", 1.5);

  // Title
  g.append("text")
    .attr("x", plotWidth / 2)
    .attr("y", -8)
    .attr("text-anchor", "middle")
    .attr("font-size", "12px")
    .attr("font-weight", "600")
    .text(facet.key);
}
```

### Canvas line chart panel

```js
function renderCanvasPanel(ctx, facet, xScale, yScale, w, h) {
  // Gridlines
  ctx.strokeStyle = "#e0e0e0";
  ctx.lineWidth = 0.5;
  yScale.ticks(4).forEach(tick => {
    const y = yScale(tick);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  });

  // Data line
  ctx.strokeStyle = "steelblue";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  facet.values.forEach((d, i) => {
    const x = xScale(d.date), y = yScale(d.value);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}
```

## Common Pitfalls

**All panels look identical.** You're using the same data for every facet — usually a scoping bug. Check that each panel receives its own data slice, not a reference to the same array.

**Scales not shared when they should be.** If you create scales inside the per-facet loop using `d3.extent(facetData, ...)`, each panel gets its own domain. Compute shared domains before the loop from the full dataset.

**Too many axis labels.** Every panel rendering its own x and y axes creates visual noise. Only draw y-axis on leftmost panels and x-axis on bottom panels. Use shared axis labels for the whole grid.

**Panels overflow their cells.** Forgetting to account for cell margins, or setting SVG viewBox wrong. Always compute `plotWidth = cellWidth - margin.left - margin.right` and clip data to the plot area.

**Crosshair breaks across panels.** If each panel has its own `xScale` with its own range, the pixel position in one panel doesn't map to the same pixel in another. Use a shared scale (same domain) and copy it with `.copy().range([0, plotWidth])` for each panel so pixel positions are consistent.

**Responsive reflow jank.** Re-rendering all panels on every resize frame is expensive. Debounce the resize handler (100–150ms) and only re-render if column count actually changed.

**Memory leaks on reflow.** When removing and recreating SVGs, event listeners and D3 selections can leak. Use `.remove()` on old SVGs, or better, reuse existing SVGs and update their contents with join patterns.

**CSS Grid `auto-fill` vs `auto-fit`.** `auto-fill` creates empty columns; `auto-fit` collapses them. For small multiples, `auto-fill` is usually correct — it keeps consistent cell sizes even with few facets.

**Canvas DPI.** On retina displays, canvas content looks blurry without DPI scaling. Always set `canvas.width = w * devicePixelRatio` and `ctx.scale(devicePixelRatio, devicePixelRatio)`.

## References

- [Small Multiples](https://observablehq.com/@d3/small-multiples) — canonical D3 example
- [Trellis Display](https://en.wikipedia.org/wiki/Small_multiple) — origin of the concept (Tufte, Cleveland)
- [CSS Grid Layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout) — browser layout for responsive grids
- [ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver) — responsive re-rendering
- [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) — lazy rendering
