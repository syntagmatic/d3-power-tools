---
name: parallel-coordinates
description: "Build high-performance parallel coordinates visualizations with D3.js. Use this skill whenever the user wants to visualize multivariate or high-dimensional data, compare items across many variables, build parallel coordinates plots, or explore datasets with 5+ numeric dimensions. Also use when the user mentions parcoords, parallel axes, multi-axis plots, or wants to brush/filter across multiple dimensions simultaneously."
---

# Parallel Coordinates

Build high-performance, interactive parallel coordinates visualizations that scale to tens of thousands of rows and hundreds of dimensions.

## Architecture

### Canvas + SVG Hybrid (Required for >500 rows)

The critical insight: Canvas renders the polylines, SVG handles everything interactive.

```
┌─────────────────────────────────┐
│  SVG layer (top, pointer-events)│  ← axes, labels, brushes
│  Canvas layer (bottom, drawing) │  ← polylines, fills
│  Container div (position:rel)   │
└─────────────────────────────────┘
```

- The Canvas and SVG share identical coordinate systems via matching width/height/margins
- SVG captures all pointer events; Canvas has `pointer-events: none`
- Axes are SVG `<g>` elements positioned with `transform: translate(x, 0)`
- Polylines are drawn on Canvas with `ctx.beginPath()` per line

### Rendering Pipeline

```
data → scales → polyline paths → canvas draw → brush filter → highlight redraw
```

1. **Scales**: One scale per axis. Map data domain → pixel range (vertical). Use `d3.scaleLinear`, `d3.scaleLog`, `d3.scalePoint` (ordinal), `d3.scaleBand`.
2. **Axis positions**: Evenly spaced horizontally, or draggable.
3. **Path generation**: For each row, generate a polyline through (axis_x, scale(value)) for each axis.
4. **Draw**: Clear canvas, draw all lines (dimmed), then draw selected/highlighted lines on top.

### Progressive Rendering (Render Queue)

For large datasets, don't draw all lines in one frame. Use the `createRenderQueue` from the `canvas` skill — it renders in chunks via `requestAnimationFrame` with shuffle support so partial renders are representative. Shuffle is especially important for parallel coordinates: without it, the first frame shows only the first N rows (often sorted by a default column).

### Opacity Scaling

Auto-scale line opacity based on dataset size:

```js
const alpha = Math.max(0.01, Math.min(0.8, 100 / data.length));
ctx.strokeStyle = `rgba(0, 100, 160, ${alpha})`;
```

This prevents oversaturation with large datasets and ensures visibility with small ones.

## Reading Crossing Patterns (Duality)

The geometry of line crossings between adjacent axes encodes variable relationships — these are consequences of Inselberg's point-line duality, not just visual heuristics:

| Pattern between axes Xi, Xi+1 | Meaning | What to look for |
|-------------------------------|---------|-----------------|
| Parallel segments (no crossings) | Strong positive correlation | Lines flow smoothly left to right |
| X-pattern (lines cross between axes) | Negative correlation | Lines form an hourglass at the midpoint |
| Tight "bowtie" / hyperbolic envelope | Elliptical cluster in (xi, xi+1) space | Waist width = correlation strength |
| All segments converge to a point | Perfect linear relationship | All data on one line in that 2D projection |
| Random crossings, no structure | Independence | Uniform tangle |

The bowtie pattern is the most actionable: when you see a tight hyperbolic envelope between two axes, you're looking at a cluster. The waist width tells you how tight the cluster is; the orientation tells you the correlation sign. This is why **axis ordering matters** — you can only see pairwise relationships between adjacent axes.

## Axis Ordering Strategies

Drag-to-reorder is necessary but insufficient. Guide users toward meaningful orderings:

| Strategy | When to use | How |
|----------|-------------|-----|
| Correlation-based | Default for numeric exploration | Place highly correlated axes adjacent; use `|r|` to maximize visible structure |
| Domain grouping | Dimensions have natural categories (e.g., demographics, performance, cost) | Group related dimensions; place the "outcome" axis at the far right |
| Variance-first | Screening many dimensions | Put highest-variance axes at left where they get the most visual attention |
| Manual hypothesis | User has a specific question | Let them drag to test specific adjacencies |

For automatic ordering, compute the pairwise correlation matrix and use a greedy nearest-neighbor traversal: start with the highest-variance dimension, then always place the most-correlated unplaced dimension next. This maximizes visible structure between adjacent axes without requiring the user to know the data.

```js
// Greedy correlation-based ordering
function correlationOrder(data, dims) {
  const corr = (a, b) => {
    const va = data.map(d => d[a]), vb = data.map(d => d[b]);
    const ma = d3.mean(va), mb = d3.mean(vb);
    const num = d3.sum(va.map((v, i) => (v - ma) * (vb[i] - mb)));
    const den = Math.sqrt(d3.sum(va.map(v => (v - ma) ** 2))
              * d3.sum(vb.map(v => (v - mb) ** 2)));
    return den === 0 ? 0 : num / den;
  };
  const remaining = new Set(dims);
  const ordered = [dims[0]]; // start with first dimension
  remaining.delete(dims[0]);
  while (remaining.size > 0) {
    const last = ordered[ordered.length - 1];
    let best = null, bestCorr = -Infinity;
    for (const d of remaining) {
      const r = Math.abs(corr(last, d));
      if (r > bestCorr) { bestCorr = r; best = d; }
    }
    ordered.push(best);
    remaining.delete(best);
  }
  return ordered;
}
```

## Interaction Patterns

### Axis Brushing

Use `d3.brushY()` on each axis. The brush extent maps back through the scale to filter data:

```js
const brush = d3.brushY()
  .extent([[-10, 0], [10, height]])
  .on("brush end", brushed);

function brushed(event, dimension) {
  if (!event.selection) {
    // brush cleared
    delete filters[dimension];
  } else {
    const [y0, y1] = event.selection;
    const scale = scales[dimension];
    filters[dimension] = d => {
      const v = scale(d[dimension]);
      return v >= y0 && v <= y1;
    };
  }
  updateCanvas();
}
```

**Multi-brush**: Allow multiple brushes per axis for disjoint selections. Store an array of [min, max] ranges per dimension.

### Strum Brushing (Between-Axis Selection)

Standard axis brushes select by **value** on one dimension. Strum brushing selects by **relationship** between two dimensions — it draws a line between adjacent axes and selects polylines that intersect it. This is Inselberg's angular brushing made interactive.

```js
// Test if a data polyline segment intersects the user-drawn strum line
function intersectsStrum(axX1, axX2, ya, yb, strum) {
  // Cross-product segment intersection test
  const cross = (ux, uy, vx, vy) => ux * vy - uy * vx;
  const d1 = cross(strum.x2-strum.x1, strum.y2-strum.y1, axX1-strum.x1, ya-strum.y1);
  const d2 = cross(strum.x2-strum.x1, strum.y2-strum.y1, axX2-strum.x1, yb-strum.y1);
  const d3 = cross(axX2-axX1, yb-ya, strum.x1-axX1, strum.y1-ya);
  const d4 = cross(axX2-axX1, yb-ya, strum.x2-axX1, strum.y2-ya);
  return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0))
      && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0));
}
```

Strum brushing is strictly more expressive than axis brushing for finding correlations — it selects wedge-shaped regions in the dual scatterplot, which axis brushes cannot. Combine both: axis brushes for value-range filtering, strum brushes for relationship filtering.

### Axis Reordering (Drag)

Make axes draggable to reorder dimensions — this is essential for finding patterns:

```js
const drag = d3.drag()
  .on("start", function(event, d) {
    d3.select(this).raise(); // bring to front
  })
  .on("drag", function(event, d) {
    // constrain to horizontal movement
    const x = Math.max(0, Math.min(width, event.x));
    d3.select(this).attr("transform", `translate(${x}, 0)`);
    // reorder dimensions array based on current positions
    dimensions.sort((a, b) => position(a) - position(b));
    updateCanvas();
  })
  .on("end", function(event, d) {
    // snap to grid position
    const newX = xScale(d);
    d3.select(this)
      .transition().duration(300)
      .attr("transform", `translate(${newX}, 0)`);
    updateCanvas();
  });
```

### Axis Inversion

Click an axis label to flip its scale. This reveals negative correlations.

Track inversion state in a `Set` — don't rely solely on mutating the scale's range, because rebuilding scales (e.g., on data update) would lose the inversion. The Set is the source of truth; apply it when (re)building scales:

```js
const inverted = new Set();

function toggleInvert(dimension) {
  if (inverted.has(dimension)) {
    inverted.delete(dimension);
  } else {
    inverted.add(dimension);
  }
  rebuildScale(dimension);
  updateAxis(dimension);
  updateCanvas();
}

function rebuildScale(dimension) {
  const range = inverted.has(dimension) ? [0, height] : [height, 0];
  scales[dimension] = inferScale(data, dimension).range(range);
}
```

### Fisheye Distortion (for many dimensions)

When you have 30+ axes, use fisheye distortion to magnify the area near the cursor:

```js
function fisheye(x, focus, distortion = 3, radius = 200) {
  const dx = x - focus;
  const dd = Math.abs(dx);
  if (dd >= radius) return x;
  const k = distortion;
  const d = dd / radius;
  const t = d * (k + 1) / (d * k + 1); // fisheye formula
  return focus + Math.sign(dx) * t * radius;
}
```

Apply this to axis x-positions on mousemove. Original positions stay in a separate array for restoration.

### Column Deletion

Drag an axis off the left edge to remove it. Useful for narrowing focus in high-dimensional data.

### Text Search

Filter dimensions by name with an input field — essential when you have 50+ columns:

```js
input.on("input", function() {
  const query = this.value.toLowerCase();
  dimensions = allDimensions.filter(d =>
    d.toLowerCase().includes(query)
  );
  updateLayout();
});
```

## Line Styling

### Curves vs. Straight Lines

- **Straight lines** (default): Clearest for reading values at axes. Use `ctx.lineTo()`.
- **Bezier curves**: Smoother appearance, better for seeing flow. Use `ctx.bezierCurveTo()` with control points at 1/3 and 2/3 between adjacent axes.
- Let the user toggle between them.

### Color Encoding

Color lines by a selected dimension's value:

```js
const colorScale = d3.scaleSequential(d3.interpolateViridis)
  .domain(d3.extent(data, d => d[colorDimension]));
```

Or use categorical colors for grouping variables.

## Handling Data Types

### Mixed Scales

Real datasets have mixed types. Detect and assign scales:

```js
function inferScale(data, dim) {
  const values = data.map(d => d[dim]).filter(v => v != null);
  const numeric = values.every(v => !isNaN(+v));

  if (numeric) {
    const extent = d3.extent(values, v => +v);
    return d3.scaleLinear().domain(extent).nice().range([height, 0]);
  } else {
    const cats = [...new Set(values)];
    return d3.scalePoint().domain(cats).range([height, 0]).padding(0.1);
  }
}
```

### Null/Missing Values

Draw lines to a "null zone" at the bottom of the axis (below the scale range), styled differently (dashed, dimmed). Don't silently drop rows with nulls — the missingness pattern is often informative.

### Log Scales

For highly skewed data (e.g., populations, prices), offer log scale toggle per axis. Handle zeros by adding 1 or using symlog.

## Performance Targets

| Rows | Dimensions | Target | Technique |
|------|-----------|--------|-----------|
| < 500 | < 20 | SVG only, instant | Basic D3 path elements |
| 500-5,000 | < 30 | Canvas, <100ms | Single-frame canvas draw |
| 5,000-50,000 | < 50 | Canvas + render queue, <2s | Progressive rendering |
| 50,000+ | Any | Canvas + Web Worker | OffscreenCanvas in worker |
| Any | 50-200 | Fisheye + column management | Fisheye distortion |

### OffscreenCanvas in Web Worker (Modern Approach)

For 50K+ rows, move rendering to a worker via `canvas.transferControlToOffscreen()`. See the `canvas` skill for the full OffscreenCanvas pattern — transfer the canvas to a worker, render polylines there, and report progress back to the main thread.

## Data Export

Always include CSV export of the current brushed selection:

```js
function exportCSV(selected, dimensions) {
  const csv = d3.csvFormat(selected, dimensions);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  // trigger download...
}
```

## Canvas Hit Detection (Hover-to-Highlight)

Canvas doesn't have DOM elements to attach event listeners to. Use the **color-picking** technique: render each line in a unique color to a hidden canvas, then read the pixel under the cursor to identify which line is hovered.

### Setup

```js
// Hidden canvas — same dimensions, never displayed
const hitCanvas = document.createElement('canvas');
hitCanvas.width = width; hitCanvas.height = height;
const hitCtx = hitCanvas.getContext('2d', { willReadFrequently: true });

// Map unique colors → data indices
const colorToIndex = new Map();

function indexToColor(i) {
  // Pack index into RGB (supports up to 16M lines)
  const r = (i >> 16) & 0xff;
  const g = (i >> 8) & 0xff;
  const b = i & 0xff;
  return `rgb(${r},${g},${b})`;
}
```

### Render the Hit Canvas

Draw the same polylines, but each in its unique color with no alpha, no antialiasing:

```js
function renderHitCanvas(data, dimensions, scales, xPositions) {
  hitCtx.clearRect(0, 0, width, height);
  hitCtx.lineWidth = 3; // wider than visual lines for easier picking
  colorToIndex.clear();

  data.forEach((d, i) => {
    const color = indexToColor(i);
    colorToIndex.set(color, i);
    hitCtx.strokeStyle = color;
    hitCtx.beginPath();
    dimensions.forEach((dim, j) => {
      const x = xPositions[j], y = scales[dim](d[dim]);
      j === 0 ? hitCtx.moveTo(x, y) : hitCtx.lineTo(x, y);
    });
    hitCtx.stroke();
  });
}
```

### Lookup on Hover

```js
container.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event, canvas);
  const pixel = hitCtx.getImageData(mx, my, 1, 1).data;
  const color = `rgb(${pixel[0]},${pixel[1]},${pixel[2]})`;
  const idx = colorToIndex.get(color);

  if (idx !== undefined) {
    highlightLine(idx);
  } else {
    clearHighlight();
  }
});
```

Re-render the hit canvas whenever the layout changes (axis reorder, brush, resize).

## Responsive Design

Use `ResizeObserver` on the container to trigger resize. On resize: update canvas dimensions (see `canvas` skill for DPR setup), rebuild all scales with the new height/width, update SVG viewBox, and redraw. Also listen for DPR changes when the window moves between displays — the `canvas` skill covers the `matchMedia` pattern for this.

Re-render the hit canvas whenever the layout changes (resize, axis reorder, brush).

## Accessibility: Color Blindness

Avoid red-green palettes entirely. Safe defaults:

- **Categorical**: `d3.schemeTableau10` — designed for distinguishability
- **Sequential**: `d3.interpolateViridis` or `d3.interpolatePlasma`
- **Diverging**: `d3.interpolatePuOr` or `d3.interpolateBrBG` (avoid RdYlGn)

```js
// Safe categorical palette
const color = d3.scaleOrdinal(d3.schemeTableau10);

// Also consider pairing color with a secondary channel (line dash, width)
// for critical distinctions
```

For parallel coordinates specifically, color encodes a dimension's value across all lines — pair it with opacity so the pattern is readable even in grayscale.

## When to Use Parallel Coordinates

Parallel coordinates are powerful but not always the right choice. Decision framework:

| Situation | Use parallel coordinates | Use instead |
|-----------|------------------------|-------------|
| 5+ numeric dimensions, want to see all at once | Yes | — |
| Comparing individual items across dimensions | Yes | — |
| Finding clusters in high-dimensional data | Yes, with brushing | Scatterplot matrix for < 5 dims |
| 2-3 dimensions | No | Scatterplot or small multiples |
| Categorical data (mostly) | No | Parallel sets (Kosara), alluvial diagrams |
| Time series across dimensions | Maybe | Small multiples of line charts usually clearer |
| > 50 dimensions | Yes, with fisheye + column management | Dimensionality reduction (t-SNE, UMAP) for overview |

The key advantage is **brushing as analysis**: no other chart type lets users interactively define multi-dimensional filters and immediately see which items pass. If the workflow is "explore, filter, export subset," parallel coordinates are the right tool.

Observable Plot (as of March 2026) does not have a parallel coordinates mark. Build with D3 directly.

## Common Pitfalls

1. **Canvas blurriness on retina displays**: See the `canvas` skill's DPR section. TL;DR: set `canvas.width = width * dpr`, `ctx.scale(dpr, dpr)`, CSS size stays at `width`.
2. **Brush coordinates after axis reorder**: Brushes are attached to axis groups — when axes move, brush extents are still valid because they're in local coordinates.
3. **Ordinal axis sorting**: Sort categories by frequency or a meaningful order, not alphabetically (unless that's meaningful).
4. **Too many colors**: With >7 categories, color encoding becomes useless. Fall back to highlight-on-hover.
5. **Axis label overlap**: Rotate labels or use fisheye when dimensions are dense.
6. **Forgetting to clear canvas**: Always `ctx.clearRect(0, 0, width, height)` before redraw. Failing to clear creates ghosting.

## References

- [The Plane with Parallel Coordinates](https://doi.org/10.1007/BF01898350) — Alfred Inselberg's foundational paper on parallel coordinates (The Visual Computer, 1985)
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — Kai Chang's D3 parallel coordinates library, the reference implementation for brushing, axis reordering, and Canvas rendering
- [Nutrient Parallel Coordinates](https://blocks.roadtolarissa.com/syntagmatic/3150059) — interactive nutrient explorer demonstrating brushing and axis reordering
- [Parallel Coordinates](https://eagereyes.org/techniques/parallel-coordinates) — Robert Kosara's accessible introduction to the technique
- [Brushable Parallel Coordinates](https://observablehq.com/@d3/parallel-coordinates) — Mike Bostock's Observable notebook
- [High-Dimensional Data Analysis with Parallel Coordinates](https://doi.org/10.1145/1281500.1281552) — Xiaoru Yuan et al.'s survey of interaction techniques for parallel coordinates (2007)
- [Crossfilter](https://square.github.io/crossfilter/) — fast multidimensional filtering, often paired with parallel coordinates
- [Parallel Sets](https://eagereyes.org/parallel-sets) — Robert Kosara & Caroline Ziemkiewicz's categorical variant of parallel coordinates
- [Hauser, Ledermann, Doleisch, "Angular Brushing of Extended Parallel Coordinates" (InfoVis 2002)](https://ieeexplore.ieee.org/document/1173157/) — angular/strum brushing theory and implementation
- [Heinrich & Weiskopf, "State of the Art of Parallel Coordinates" (2013)](https://joules.de/files/heinrich_state_2013.pdf) — comprehensive survey of rendering and interaction techniques
