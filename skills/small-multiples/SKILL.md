---
name: small-multiples
description: "Build small multiples (trellis/faceted) layouts with D3.js. Use this skill when the user wants to show the same chart repeated across categories, faceted grids, trellis plots, panel charts, or lattice displays. Covers grid layout calculation, shared vs independent scales, synchronized interactions, responsive reflow, and Canvas-based small multiples for large facet counts."
---

# Small Multiples

Patterns for building small multiples (trellis, faceted, lattice) layouts with D3.

For axes and tick formatting, see `axes-and-scales`. For brushing and cross-chart linking, see `brushing`. For canvas rendering patterns, see `canvas`.

## Scale Strategies

The most important design decision: should all panels share the same scales?

### Shared scales — enables comparison across facets

All panels use the same x and y domain. Visual differences between panels are directly comparable.

**When to use:** Comparing magnitudes across categories. "Which city has the highest temperature?"

### Independent scales — shows local patterns

Each panel has its own domain, normalized to fill the available space.

**When to use:** Showing shape/trend within each category. "Does this city have a seasonal pattern?"

**Warning:** Independent y-scales are misleading when viewers assume panels are comparable. Always label axes clearly or add a visual cue (different axis color, annotation).

### Hybrid — shared x, independent y

Common for time series with different units or magnitudes (e.g., temperature vs precipitation).

### Implementation note

Compute shared domains **before** the per-facet loop from the full dataset. Creating scales inside the loop with `d3.extent(facetData, ...)` is a common bug that accidentally produces independent scales.

Use `.copy()` to share domain but set per-panel range: `xScale.copy().range([0, plotWidth])`.

## Cross-Tabulation (facet_grid)

Like ggplot's `facet_grid`: one variable maps to rows, another to columns.

```js
const nested = d3.group(data, rowVar, colVar);
rowKeys.forEach((row, ri) => {
  colKeys.forEach((col, ci) => {
    const cellData = nested.get(row)?.get(col) ?? [];
    renderPanel(cellData, ci * (cellWidth + gap), ri * (cellHeight + gap));
  });
});
```

Add row labels on the left edge and column labels on the top edge.

## Synchronized Interaction

The key UX pattern: interacting with one panel affects all panels simultaneously.

### Shared crosshair

```js
panels.append("rect")
  .attr("width", plotWidth).attr("height", plotHeight)
  .attr("fill", "none").attr("pointer-events", "all")
  .on("pointermove", (event) => {
    const [mx] = d3.pointer(event);
    // Broadcast to ALL panels — works because shared xScale means same pixel = same data
    crosshairs.attr("x1", mx).attr("x2", mx).style("display", null);
    updateTooltips(xScale.invert(mx));
  })
  .on("pointerleave", () => crosshairs.style("display", "none"));
```

### Shared brush — critical: prevent event loops

```js
const brush = d3.brushX()
  .extent([[0, 0], [plotWidth, plotHeight]])
  .on("brush end", (event) => {
    if (!event.sourceEvent) return; // prevent loops
    const selection = event.selection;
    // Apply visual filtering to all panels
    // Move brush in other panels without triggering events:
    panels.selectAll(".brush")
      .filter(function() { return this !== event.target; })
      .call(brush.move, selection);
  });
```

### Linked zoom — same loop-prevention pattern

```js
const zoom = d3.zoom()
  .scaleExtent([1, 10])
  .on("zoom", (event) => {
    if (!event.sourceEvent) return;
    panels.each(function() { d3.select(this).call(zoom.transform, event.transform); });
    updateAllPanels(event.transform.rescaleX(xScale));
  });
```

## Axis Efficiency

Redundant axes waste space. Only draw y-axis on leftmost column, x-axis on bottom row. Use a single shared axis label for the whole grid.

## Canvas Small Multiples

For large facet counts (50+) or data-dense panels, Canvas outperforms SVG.

### Performance tradeoffs

| Approach | Facets | DOM elements | Hit detection | Interaction |
|---|---|---|---|---|
| SVG per facet | < 50 | N * elements/facet | Built-in | Easy (D3 events) |
| Canvas per facet | 50-200 | N canvases | Manual per canvas | Moderate |
| Shared Canvas | 200+ | 1 canvas | Global quadtree | Complex |

### Shared Canvas with viewport clipping

One large canvas, clip each panel region:

```js
facets.forEach((facet, i) => {
  const x = cellX(i) + cellMargin.left;
  const y = cellY(i) + cellMargin.top;
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, plotWidth, plotHeight);
  ctx.clip();
  ctx.translate(x, y);
  renderLine(ctx, facet.values, xScale, yScale);
  ctx.restore();
});
```

### Shared canvas hit detection

Determine which cell the pointer is over from pixel coordinates, then do local hit detection:

```js
canvas.addEventListener("pointermove", (event) => {
  const rect = canvas.getBoundingClientRect();
  const mx = event.clientX - rect.left, my = event.clientY - rect.top;
  const col = Math.floor((mx - containerPadding.left) / (cellWidth + gap));
  const row = Math.floor((my - containerPadding.top) / (cellHeight + gap));
  const idx = row * cols + col;
  if (idx < 0 || idx >= n) return;
  const localX = mx - cellX(idx) - cellMargin.left;
  const localY = my - cellY(idx) - cellMargin.top;
  if (localX >= 0 && localX <= plotWidth && localY >= 0 && localY <= plotHeight)
    handleHover(idx, localX, localY);
});
```

## Lazy Rendering

### IntersectionObserver — render panels as they scroll into view

```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !entry.target.dataset.rendered) {
      renderPanel(entry.target, facets[+entry.target.dataset.index]);
      entry.target.dataset.rendered = "true";
    }
  });
}, { rootMargin: "200px" }); // pre-render 200px ahead
```

### Virtual scrolling for 1000+ facets

Only create DOM elements for visible facets. Recycle elements as the user scrolls:

```js
const visibleRows = Math.ceil(containerHeight / (cellHeight + gap)) + 1;
const visibleCells = visibleRows * cols;

container.addEventListener("scroll", () => {
  const startRow = Math.floor(container.scrollTop / (cellHeight + gap));
  const startIdx = startRow * cols;
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
// Set total scrollable height on a spacer element
spacer.style.height = `${rows * (cellHeight + gap) - gap}px`;
```

## Common Pitfalls

**All panels look identical.** You're using the same data for every facet — usually a scoping bug. Check that each panel receives its own data slice, not a reference to the same array.

**Scales not shared when they should be.** If you create scales inside the per-facet loop using `d3.extent(facetData, ...)`, each panel gets its own domain. Compute shared domains before the loop from the full dataset.

**Too many axis labels.** Every panel rendering its own x and y axes creates visual noise. Only draw y-axis on leftmost panels and x-axis on bottom panels.

**Panels overflow their cells.** Forgetting to account for cell margins. Always compute `plotWidth = cellWidth - margin.left - margin.right` and clip data to the plot area.

**Crosshair breaks across panels.** If each panel has its own `xScale` with its own range, the pixel position in one panel doesn't map to the same pixel in another. Use a shared scale and `.copy().range()` for each panel.

**Responsive reflow jank.** Re-rendering all panels on every resize frame is expensive. Debounce (100-150ms) and only re-render if column count actually changed.

**Memory leaks on reflow.** When removing and recreating SVGs, event listeners leak. Use `.remove()` on old SVGs, or better, reuse existing SVGs with join patterns.

**CSS Grid `auto-fill` vs `auto-fit`.** `auto-fill` creates empty columns; `auto-fit` collapses them. For small multiples, `auto-fill` is usually correct — it keeps consistent cell sizes even with few facets.

**Canvas DPI.** On retina displays, canvas content looks blurry without DPI scaling. Always set `canvas.width = w * devicePixelRatio` and `ctx.scale(devicePixelRatio, devicePixelRatio)`.

## References

- [Small Multiples](https://observablehq.com/@d3/small-multiples) — canonical D3 example
- [Trellis Display](https://en.wikipedia.org/wiki/Small_multiple) — origin of the concept (Tufte, Cleveland)
- [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) — lazy rendering
