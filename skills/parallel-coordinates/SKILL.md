---
name: parallel-coordinates
description: "Build high-performance parallel coordinates visualizations with D3.js. Use this skill whenever the user wants to visualize multivariate or high-dimensional data, compare items across many variables, build parallel coordinates plots, or explore datasets with 5+ numeric dimensions. Also use when the user mentions parcoords, parallel axes, multi-axis plots, or wants to brush/filter across multiple dimensions simultaneously."
---

# Parallel Coordinates

Build high-performance, interactive parallel coordinates visualizations that scale to tens of thousands of rows and hundreds of dimensions.

## Architecture

### Canvas + SVG Hybrid (Required for >500 rows)

Canvas renders the polylines, SVG handles everything interactive.

```
┌─────────────────────────────────┐
│  SVG layer (top, pointer-events)│  ← axes, labels, brushes
│  Canvas layer (bottom, drawing) │  ← polylines, fills
│  Container div (position:rel)   │
└─────────────────────────────────┘
```

- Canvas and SVG share identical coordinate systems via matching width/height/margins
- SVG captures all pointer events; Canvas has `pointer-events: none`
- Axes are SVG `<g>` elements positioned with `transform: translate(x, 0)`

### Rendering Pipeline

```
data → scales → polyline paths → canvas draw → brush filter → highlight redraw
```

1. **Scales**: One per axis. `d3.scaleLinear`, `d3.scaleLog`, `d3.scalePoint` (ordinal), `d3.scaleBand`.
2. **Axis positions**: Evenly spaced horizontally, or draggable.
3. **Path generation**: For each row, polyline through `(axis_x, scale(value))` per axis.
4. **Draw**: Clear canvas, draw all lines (dimmed), then selected/highlighted lines on top.

### Progressive Rendering

For large datasets, use `createRenderQueue` from the `canvas` skill -- it renders in chunks via `requestAnimationFrame` with shuffle support so partial renders are representative. Shuffle is critical for parallel coordinates: without it, the first frame shows only the first N rows (often sorted by a default column).

### Opacity Scaling

Auto-scale line opacity by dataset size:

```js
const alpha = Math.max(0.01, Math.min(0.8, 100 / data.length));
ctx.strokeStyle = `rgba(0, 100, 160, ${alpha})`;
```

## Reading Crossing Patterns (Duality)

Line crossings between adjacent axes encode variable relationships -- consequences of Inselberg's point-line duality:

| Pattern between axes Xi, Xi+1 | Meaning | What to look for |
|-------------------------------|---------|-----------------|
| Parallel segments (no crossings) | Strong positive correlation | Lines flow smoothly left to right |
| X-pattern (lines cross) | Negative correlation | Hourglass at midpoint |
| Tight "bowtie" / hyperbolic envelope | Elliptical cluster in (xi, xi+1) space | Waist width = correlation strength |
| All segments converge to a point | Perfect linear relationship | All data on one line in that 2D projection |
| Random crossings, no structure | Independence | Uniform tangle |

The bowtie is the most actionable: a tight hyperbolic envelope between two axes reveals a cluster. Waist width = tightness; orientation = correlation sign. This is why **axis ordering matters** -- you can only see pairwise relationships between adjacent axes.

## Axis Ordering Strategies

Drag-to-reorder is necessary but insufficient. Guide users toward meaningful orderings:

| Strategy | When to use | How |
|----------|-------------|-----|
| Correlation-based | Default for numeric exploration | Place highly correlated axes adjacent; use `|r|` to maximize visible structure |
| Domain grouping | Dimensions have natural categories | Group related dimensions; outcome axis at far right |
| Variance-first | Screening many dimensions | Highest-variance axes at left where they get most visual attention |
| Manual hypothesis | User has a specific question | Drag to test specific adjacencies |

For automatic ordering, compute the pairwise correlation matrix and use greedy nearest-neighbor traversal: start with the highest-variance dimension, then always place the most-correlated unplaced dimension next.

```js
function correlationOrder(data, dims) {
  const corr = (a, b) => {
    const va = data.map(d => d[a]), vb = data.map(d => d[b]),
          ma = d3.mean(va), mb = d3.mean(vb);
    const num = d3.sum(va.map((v, i) => (v - ma) * (vb[i] - mb)));
    const den = Math.sqrt(d3.sum(va.map(v => (v - ma) ** 2))
              * d3.sum(vb.map(v => (v - mb) ** 2)));
    return den === 0 ? 0 : num / den;
  };
  const remaining = new Set(dims), ordered = [dims[0]];
  remaining.delete(dims[0]);
  while (remaining.size > 0) {
    const last = ordered.at(-1);
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
    delete filters[dimension];
  } else {
    const [y0, y1] = event.selection, scale = scales[dimension];
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

Axis brushes select by **value** on one dimension. Strum brushing selects by **relationship** between two dimensions -- draws a line between adjacent axes and selects polylines that intersect it (Inselberg's angular brushing made interactive).

```js
// Test if a data polyline segment intersects the user-drawn strum line
// Cross-product segment intersection test
function intersectsStrum(axX1, axX2, ya, yb, strum) {
  const cross = (ux, uy, vx, vy) => ux * vy - uy * vx;
  const c1 = cross(strum.x2-strum.x1, strum.y2-strum.y1, axX1-strum.x1, ya-strum.y1);
  const c2 = cross(strum.x2-strum.x1, strum.y2-strum.y1, axX2-strum.x1, yb-strum.y1);
  const c3 = cross(axX2-axX1, yb-ya, strum.x1-axX1, strum.y1-ya);
  const c4 = cross(axX2-axX1, yb-ya, strum.x2-axX1, strum.y2-ya);
  return ((c1 > 0 && c2 < 0) || (c1 < 0 && c2 > 0))
      && ((c3 > 0 && c4 < 0) || (c3 < 0 && c4 > 0));
}
```

Strum brushing selects wedge-shaped regions in the dual scatterplot, which axis brushes cannot. Combine both: axis brushes for value-range filtering, strum brushes for relationship filtering.

### Axis Reordering (Drag)

```js
const drag = d3.drag()
  .on("start", function() { d3.select(this).raise(); })
  .on("drag", function(event) {
    const x = Math.max(0, Math.min(width, event.x));
    d3.select(this).attr("transform", `translate(${x}, 0)`);
    dimensions.sort((a, b) => position(a) - position(b));
    updateCanvas();
  })
  .on("end", function(event, d) {
    d3.select(this).transition().duration(300)
      .attr("transform", `translate(${xScale(d)}, 0)`);
    updateCanvas();
  });
```

### Axis Inversion

Click an axis label to flip its scale. Track inversion state in a `Set` -- don't mutate the scale's range directly, because rebuilding scales on data update would lose the inversion:

```js
const inverted = new Set();

function toggleInvert(dimension) {
  inverted.has(dimension) ? inverted.delete(dimension) : inverted.add(dimension);
  scales[dimension] = inferScale(data, dimension)
    .range(inverted.has(dimension) ? [0, height] : [height, 0]);
  updateAxis(dimension);
  updateCanvas();
}
```

### Fisheye Distortion (30+ dimensions)

Magnify the area near the cursor when axes are too dense. See the `brushing` skill for the fisheye formula. Apply to axis x-positions on mousemove; keep original positions in a separate array for restoration.

### Column Deletion

Drag an axis off the left edge to remove it. Useful for narrowing focus in high-dimensional data.

### Text Search

Filter dimensions by name with an input field -- essential with 50+ columns. Match `d.toLowerCase().includes(query)` and call `updateLayout()`.

## Line Styling

- **Straight lines** (default): Clearest for reading values at axes. `ctx.lineTo()`.
- **Bezier curves**: Smoother, better for seeing flow. `ctx.bezierCurveTo()` with control points at 1/3 and 2/3 between adjacent axes.
- Let the user toggle between them.

### Color Encoding

Color lines by a selected dimension's value. Use `d3.scaleSequential(d3.interpolateViridis)` for continuous, `d3.scaleOrdinal(d3.schemeTableau10)` for categorical. With >7 categories, fall back to highlight-on-hover. See the `color` skill for colorblind-safe palette selection and CVD simulation.

## Handling Data Types

### Mixed Scales

Real datasets have mixed types. Detect and assign:

```js
function inferScale(data, dim) {
  const values = data.map(d => d[dim]).filter(v => v != null);
  if (values.every(v => !isNaN(+v))) {
    return d3.scaleLinear().domain(d3.extent(values, v => +v)).nice().range([height, 0]);
  }
  return d3.scalePoint().domain([...new Set(values)]).range([height, 0]).padding(0.1);
}
```

### Null/Missing Values

Draw lines to a "null zone" at the bottom of the axis (below the scale range), styled differently (dashed, dimmed). Don't silently drop rows -- the missingness pattern is often informative.

### Log Scales

For highly skewed data, offer log scale toggle per axis. Handle zeros with symlog.

## Performance Targets

| Rows | Dimensions | Target | Technique |
|------|-----------|--------|-----------|
| < 500 | < 20 | SVG only, instant | Basic D3 path elements |
| 500-5K | < 30 | Canvas, <100ms | Single-frame canvas draw |
| 5K-50K | < 50 | Canvas + render queue, <2s | Progressive rendering |
| 50K+ | Any | Canvas + Web Worker | OffscreenCanvas in worker |
| Any | 50-200 | Fisheye + column management | Fisheye distortion |

For 50K+ rows, move rendering to a worker via `canvas.transferControlToOffscreen()`. See the `canvas` skill for the full OffscreenCanvas pattern.

## Canvas Hit Detection (Hover-to-Highlight)

Render each line in a unique color to a hidden canvas, then read the pixel under the cursor to identify the hovered line.

```js
const hitCanvas = document.createElement('canvas');
hitCanvas.width = width; hitCanvas.height = height;
const hitCtx = hitCanvas.getContext('2d', { willReadFrequently: true });
const colorToIndex = new Map();

// Pack index into RGB (supports up to 16M lines)
function indexToColor(i) {
  return `rgb(${(i >> 16) & 0xff},${(i >> 8) & 0xff},${i & 0xff})`;
}

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

container.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event, canvas);
  const pixel = hitCtx.getImageData(mx, my, 1, 1).data;
  const color = `rgb(${pixel[0]},${pixel[1]},${pixel[2]})`;
  const idx = colorToIndex.get(color);
  idx !== undefined ? highlightLine(idx) : clearHighlight();
});
```

Re-render the hit canvas whenever the layout changes (axis reorder, brush, resize).

## Responsive Design

Use `ResizeObserver` on the container. On resize: update canvas dimensions, rebuild scales, redraw. See the `canvas` skill for DPR setup and the `responsive` skill for the full resize pattern.

## Data Export

Include CSV export of the current brushed selection: `d3.csvFormat(selected, dimensions)` into a `Blob` for download.

## When to Use Parallel Coordinates

| Situation | Use parallel coordinates | Use instead |
|-----------|------------------------|-------------|
| 5+ numeric dimensions, see all at once | Yes | -- |
| Comparing individual items across dimensions | Yes | -- |
| Finding clusters in high-dimensional data | Yes, with brushing | Scatterplot matrix for < 5 dims |
| 2-3 dimensions | No | Scatterplot or small multiples |
| Categorical data (mostly) | No | Parallel sets (Kosara), alluvial diagrams |
| Time series across dimensions | Maybe | Small multiples usually clearer |
| > 50 dimensions | Yes, with fisheye + column management | Dimensionality reduction (t-SNE, UMAP) for overview |

The key advantage is **brushing as analysis**: no other chart type lets users interactively define multi-dimensional filters and immediately see which items pass.

Observable Plot (as of March 2026) does not have a parallel coordinates mark. Build with D3 directly.

## Common Pitfalls

1. **Canvas blurriness on retina displays**: See the `canvas` skill's DPR section. TL;DR: `canvas.width = width * dpr`, `ctx.scale(dpr, dpr)`, CSS size stays at `width`.
2. **Brush coordinates after axis reorder**: Brushes are attached to axis groups -- when axes move, brush extents are still valid because they're in local coordinates.
3. **Ordinal axis sorting**: Sort categories by frequency or meaningful order, not alphabetically (unless that's meaningful).
4. **Too many colors**: With >7 categories, color encoding becomes useless. Fall back to highlight-on-hover.
5. **Axis label overlap**: Rotate labels or use fisheye when dimensions are dense.
6. **Forgetting to clear canvas**: Always `ctx.clearRect(0, 0, width, height)` before redraw. Failing to clear creates ghosting.

## References

- [The Plane with Parallel Coordinates](https://doi.org/10.1007/BF01898350) -- Inselberg's foundational paper (The Visual Computer, 1985)
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) -- Kai Chang's D3 parallel coordinates library, reference implementation for brushing, axis reordering, and Canvas rendering
- [Nutrient Parallel Coordinates](https://blocks.roadtolarissa.com/syntagmatic/3150059) -- interactive nutrient explorer
- [Parallel Coordinates](https://eagereyes.org/techniques/parallel-coordinates) -- Robert Kosara's accessible introduction
- [Brushable Parallel Coordinates](https://observablehq.com/@d3/parallel-coordinates) -- Mike Bostock's Observable notebook
- [High-Dimensional Data Analysis with Parallel Coordinates](https://doi.org/10.1145/1281500.1281552) -- Yuan et al.'s survey of interaction techniques (2007)
- [Crossfilter](https://square.github.io/crossfilter/) -- fast multidimensional filtering, often paired with parallel coordinates
- [Parallel Sets](https://eagereyes.org/parallel-sets) -- Kosara & Ziemkiewicz's categorical variant
- [Angular Brushing of Extended Parallel Coordinates (InfoVis 2002)](https://ieeexplore.ieee.org/document/1173157/) -- strum brushing theory
- [State of the Art of Parallel Coordinates (2013)](https://joules.de/files/heinrich_state_2013.pdf) -- Heinrich & Weiskopf's comprehensive survey
