---
name: small-multiples
description: "Build small multiples (trellis/faceted) layouts with D3.js. Use this skill when the user wants to show the same chart repeated across categories, faceted grids, trellis plots, panel charts, or lattice displays. Covers grid layout calculation, shared vs independent scales, synchronized interactions, responsive reflow, and Canvas-based small multiples for large facet counts."
---

# Small Multiples

Small multiples solve the overplotting problem: when too many series on one chart turn it into spaghetti, repeating the same chart structure across panels lets the eye compare without untangling.

For axes and tick formatting, see `scales`. For brushing and cross-chart linking, see `brushing`. For canvas rendering patterns, see `canvas`.

## When Small Multiples Beat a Single Chart

Use small multiples when a combined chart forces the viewer to decode rather than perceive. Specific triggers:

- **More than 4-5 overlapping series.** Line charts with 6+ series become unreadable — the eye can't track individual lines through crossings. Small multiples let each series breathe.
- **The comparison is about shape, not intersection.** If the question is "do these series follow the same trend?" rather than "where do they cross?", separated panels make shape comparison easier.
- **Categories have natural meaning.** When facets represent real-world groups (cities, products, cohorts), panels create a visual lookup table the viewer already understands.

A single chart is better when the viewer needs to see exact crossover points, when you have 2-3 series, or when the story is about the aggregate rather than the parts.

## How Many Panels

The eye compares by scanning — it holds one panel's shape in visual memory and checks it against the next. This works well up to about 16-20 panels on screen (4x4 or 4x5 grid). Beyond that:

- **20-50 panels:** Still works if charts are simple (sparkline-like). Reduce each panel to its essential shape — drop axes, gridlines, labels. The grid itself becomes the visualization.
- **50-200:** The viewer shifts from comparison to lookup. Provide sorting controls and search. Consider Canvas rendering (see below).
- **200+:** Scrolling kills comparison — you can't compare what you can't see simultaneously. Use aggregation, filtering, or drill-down instead.

The binding constraint is screen real estate. Each panel needs enough pixels to show its pattern — below ~120px wide, line charts lose their shape and bars become indistinguishable.

## Panel Ordering

Order determines what patterns the viewer discovers. Alphabetical is the default but rarely the best choice.

- **By a summary statistic** (mean, max, slope, variance): creates a visual gradient across the grid that reveals ranking. The viewer sees which panels are "high" vs "low" without reading values. In D3: `facets.sort((a, b) => d3.descending(d3.mean(a.values, v => v.y), d3.mean(b.values, v => v.y)))`.
- **By similarity** (correlation, DTW distance): groups panels with similar shapes together, making clusters visible. Useful for time series.
- **By a meaningful category** (geography, time period): when the faceting variable has inherent order (months, age groups, income brackets), respect it.
- **Alphabetical:** Only when the viewer needs to find a specific panel by name and there's no data-driven logic. Works as a fallback for large panel counts.

Ordering by a data property often creates a subtle animation effect across the grid — each panel shifts slightly from its neighbor — which helps the viewer perceive gradual trends.

## Scale Strategies

The most important design decision: should all panels share the same scales?

### Shared scales — enables magnitude comparison

All panels use the same x and y domain. A tall peak in one panel and a flat line in another are directly comparable because identical pixels encode identical values.

**When to use:** "Which city has the highest temperature?" — any question about relative magnitude across facets.

### Independent scales — reveals local patterns

Each panel normalizes to its own domain. This sacrifices cross-panel magnitude comparison but reveals patterns hidden by scale differences — a small seasonal swing in a high-baseline series becomes visible.

**When to use:** "Does each city have a seasonal pattern?" — questions about shape within each facet.

**Danger:** Viewers instinctively assume panels are comparable. Independent y-scales silently mislead — a panel that looks "high" may just have a narrow range. Mitigate with: (1) explicit annotation ("scales differ"), (2) different axis styling per panel, or (3) a summary panel showing all series at shared scale alongside the faceted view.

### Hybrid — shared x, independent y

Common for time series with different units or magnitudes (e.g., temperature vs precipitation). The shared time axis enables temporal comparison while independent y-axes let each variable fill its panel.

### Implementation

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

## Facet Wrap

When you have one faceting variable with many levels (not a row x column cross), wrap panels into a grid. Compute row and column from index:

```js
const keys = [...d3.group(data, d => d.category).keys()];
const cols = Math.ceil(Math.sqrt(keys.length * aspectRatio));
keys.forEach((key, i) => {
  const col = i % cols;
  const row = Math.floor(i / cols);
  renderPanel(grouped.get(key), col * (cellWidth + gap), row * (cellHeight + gap));
});
```

The column count formula `Math.ceil(Math.sqrt(n * aspectRatio))` produces roughly square grids adjusted for wide containers. For a fixed 4-column layout, just hardcode `cols = 4`.

> **Observable Plot note:** Plot's `fx` and `fy` channels handle faceting declaratively — shared scales, axis deduplication, and empty facet suppression are automatic. Mark-level `facet: "exclude"` lets annotations repeat across all panels. As of March 2026, auto-wrapping single-dimension facets is still manual in Plot (compute `fx = i % cols`, `fy = Math.floor(i / cols)`).

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

Only draw y-axis on leftmost column, x-axis on bottom row. Redundant axes waste 30-40% of each panel's pixel budget on repeated information — space better used for data. Use a single shared axis label for the whole grid.

## Canvas Small Multiples

For large facet counts (50+) or data-dense panels, Canvas outperforms SVG.

| Approach | Facets | Hit detection | Tradeoff |
|---|---|---|---|
| SVG per facet | < 50 | Built-in | Simple but DOM-heavy |
| Canvas per facet | 50-200 | Manual per canvas | Moderate complexity |
| Shared Canvas | 200+ | Global quadtree | Fast but complex interaction |

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

Map pixel coordinates to cell index, then do local hit detection:

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

For scrollable grids with 50+ panels, use `IntersectionObserver` with `rootMargin: "200px"` to pre-render panels just before they scroll into view. For 1000+ facets, virtual-scroll: maintain a pool of DOM elements equal to visible rows + 1, reposition and re-render them on scroll. Set a spacer element's height to the total grid height so the scrollbar is accurate.

## When Not to Use Small Multiples

- **The viewer needs to compare exact values at specific points.** Superimposed lines on one chart let the eye measure gaps directly; small multiples force the viewer to hold a value in memory across panels. Use a single chart with a tooltip or data table instead.
- **You have fewer than 3 categories.** Two or three series on one chart are trivially readable. Small multiples add layout complexity for no perceptual gain.
- **Panels would be too small to show the pattern.** If your data needs axis labels, gridlines, and annotation to be readable, and the available space gives each panel less than ~150px, the panels become illegible. Consider a scrollable single chart or a data table.
- **The story is about the aggregate.** If the insight is "overall, X is rising," a single aggregated chart communicates this faster than 20 panels that each wiggle differently.

## Common Pitfalls

**All panels look identical.** You're using the same data for every facet — usually a scoping bug. Check that each panel receives its own data slice, not a reference to the same array.

**Scales not shared when they should be.** If you create scales inside the per-facet loop using `d3.extent(facetData, ...)`, each panel gets its own domain. Compute shared domains before the loop from the full dataset.

**Too many axis labels.** Every panel rendering its own axes creates visual noise and steals space from data. Only draw y-axis on leftmost panels and x-axis on bottom panels.

**Panels overflow their cells.** Forgetting to account for cell margins. Always compute `plotWidth = cellWidth - margin.left - margin.right` and clip data to the plot area.

**Crosshair breaks across panels.** If each panel has its own `xScale` with its own range, the pixel position in one panel doesn't map to the same pixel in another. Use a shared scale and `.copy().range()` for each panel.

**Responsive reflow jank.** Re-rendering all panels on every resize frame is expensive. Debounce (100-150ms) and only re-render if column count actually changed.

**CSS Grid `auto-fill` vs `auto-fit`.** `auto-fill` creates empty columns; `auto-fit` collapses them. For small multiples, `auto-fill` is usually correct — it keeps consistent cell sizes even with few facets.

**Canvas DPI.** On retina displays, canvas content looks blurry without DPI scaling. Always set `canvas.width = w * devicePixelRatio` and `ctx.scale(devicePixelRatio, devicePixelRatio)`.
