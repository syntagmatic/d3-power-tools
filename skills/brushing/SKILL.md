---
name: brushing
description: "Build advanced brushing, selection, and cross-chart linking interactions for D3.js visualizations. Use this skill whenever the user wants to add brushing, filtering, linked views, coordinated highlighting, lasso selection, fisheye distortion, or any form of interactive data selection to a D3 visualization. Also use when the user mentions cross-filtering, brush-and-link, focus+context, intersection brushing, or wants to connect multiple charts that highlight the same data."
---

# Advanced Brushing & Selection

Build sophisticated selection and filtering interactions for data-dense visualizations. Modernizes techniques from d3.parcoords — line intersection brushing, cross-chart linking, progressive canvas rendering, and fisheye focus — with OffscreenCanvas, Web Workers, and Pointer Events.

## Origin

These patterns come from syntagmatic's parallel coordinates work, generalized for any multi-view or data-dense visualization. The key ideas:

- **Line intersection brushing** ("pinch"): select lines by drawing a crossing line, from Inselberg's Parallax
- **Render queue**: progressive rendering with shuffled order for immediate representative samples
- **Fisheye focus**: distort layout to magnify region of interest while preserving global context
- **Brush & link**: coordinated selection across multiple views

## Choosing a Selection Approach

Start here. The right technique depends on data size, view type, and what the viewer is asking.

| Scenario | Technique | Why |
|---|---|---|
| <1K points, simple views | `d3.brush` + SelectionManager | Direct, no optimization needed |
| 1K–50K points, scatter/parcoords | Lasso or intersection brush + Web Worker | Worker prevents jank during drag |
| 50K+ points, histogram/aggregate views | Falcon-style prefetch or DuckDB-WASM | O(1) brush updates via prefetched aggregation |
| 50K+ points, scatter/item views | Sample-first progressive filtering | Immediate approximate feedback, refine on idle |
| Multiple disjoint regions | Shift+drag additive brush | Union of rectangles on one view |
| Cross-view, same dimension | SelectionManager with union mode | Any brush selects |
| Cross-view, different dimensions | SelectionManager with intersect mode | All brushes must agree |
| Small multiples / facets | Per-facet brush + shared manager | Observable Plot handles this natively for simple cases |

**Observable Plot note:** For straightforward linked brushing across Plot charts, Plot's built-in brush interaction (built on `d3.brush`) handles the plumbing automatically. Drop to raw D3 when you need lasso, intersection brushing, fisheye, or custom composition logic.

## Line Intersection Brushing

Traditional brushes select by bounding box — you define a range on one axis. Line intersection brushing lets you draw a line across the visualization and select all data lines that cross it. This is powerful for finding correlations in parallel coordinates, scatterplots, or any path-based visualization.

### How It Works

1. User drags to define a query line segment (P1 → P2)
2. For each data polyline, test each segment against the query line
3. Lines that intersect are selected

### Segment Intersection Test

```js
// Returns true if segment (p1→p2) intersects segment (p3→p4)
function segmentsIntersect(p1, p2, p3, p4) {
  const d1 = direction(p3, p4, p1);
  const d2 = direction(p3, p4, p2);
  const d3 = direction(p1, p2, p3);
  const d4 = direction(p1, p2, p4);

  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
    return true;
  }

  // Collinear cases
  if (d1 === 0 && onSegment(p3, p4, p1)) return true;
  if (d2 === 0 && onSegment(p3, p4, p2)) return true;
  if (d3 === 0 && onSegment(p1, p2, p3)) return true;
  if (d4 === 0 && onSegment(p1, p2, p4)) return true;

  return false;
}

function direction(pi, pj, pk) {
  return (pk[0] - pi[0]) * (pj[1] - pi[1]) - (pj[0] - pi[0]) * (pk[1] - pi[1]);
}

function onSegment(pi, pj, pk) {
  return Math.min(pi[0], pj[0]) <= pk[0] && pk[0] <= Math.max(pi[0], pj[0]) &&
         Math.min(pi[1], pj[1]) <= pk[1] && pk[1] <= Math.max(pi[1], pj[1]);
}
```

### Applying to Parallel Coordinates

```js
// For each data row, generate polyline segments
function getPolylineSegments(d, dimensions, scales, xPositions) {
  const points = dimensions.map((dim, i) => [xPositions[i], scales[dim](d[dim])]);
  const segments = [];
  for (let i = 0; i < points.length - 1; i++) {
    segments.push([points[i], points[i + 1]]);
  }
  return segments;
}

// Test a query line against all data
function intersectionBrush(queryStart, queryEnd, data, dimensions, scales, xPositions) {
  return data.filter(d => {
    const segments = getPolylineSegments(d, dimensions, scales, xPositions);
    return segments.some(([p1, p2]) =>
      segmentsIntersect(p1, p2, queryStart, queryEnd)
    );
  });
}
```

### Interaction: Drawing the Query Line

Use Pointer Events (not mouse events) for touch + pen support:

```js
let queryStart = null;

svg.on("pointerdown", (event) => {
  if (event.altKey || event.button === 2) { // alt+click or right-click
    queryStart = d3.pointer(event);
    svg.append("line")
      .attr("class", "query-line")
      .attr("x1", queryStart[0]).attr("y1", queryStart[1])
      .attr("x2", queryStart[0]).attr("y2", queryStart[1]);
  }
});

svg.on("pointermove", (event) => {
  if (!queryStart) return;
  const current = d3.pointer(event);
  svg.select(".query-line")
    .attr("x2", current[0]).attr("y2", current[1]);

  // live preview of selection
  const selected = intersectionBrush(queryStart, current, data, dims, scales, xPos);
  highlightSelection(selected);
});

svg.on("pointerup", (event) => {
  if (!queryStart) return;
  const queryEnd = d3.pointer(event);
  const selected = intersectionBrush(queryStart, queryEnd, data, dims, scales, xPos);
  applySelection(selected);
  queryStart = null;
});
```

### Offloading to a Web Worker

For 10k+ rows, intersection testing is CPU-heavy. Move it to a worker:

```js
// main.js
const worker = new Worker('intersection-worker.js');

worker.postMessage({
  queryStart, queryEnd,
  polylines, // pre-computed array of point arrays
});

worker.onmessage = ({ data: { selectedIndices } }) => {
  highlightByIndices(selectedIndices);
};

// intersection-worker.js
self.onmessage = ({ data: { queryStart, queryEnd, polylines } }) => {
  const selectedIndices = [];
  polylines.forEach((points, index) => {
    for (let i = 0; i < points.length - 1; i++) {
      if (segmentsIntersect(points[i], points[i + 1], queryStart, queryEnd)) {
        selectedIndices.push(index);
        break;
      }
    }
  });
  self.postMessage({ selectedIndices });
};
```

## Render Queue

Use the `createRenderQueue` from the `canvas` skill for progressive rendering with shuffle support. For brushing visualizations, connect the render queue's `onProgress` callback to a progress indicator and use `cancel()` to abort in-flight renders when the selection changes — this prevents stale renders from overwriting fresh ones.

For very large datasets, move rendering to a Web Worker via `OffscreenCanvas` (also covered in the `canvas` skill). Note: workers don't have `requestAnimationFrame` — use `setTimeout(0)` between batches to stay responsive to cancel messages.

## Fisheye Distortion

Magnify a region of interest while keeping everything visible. Two variants:

### Cartesian Fisheye (for axes)

Distort x-positions of parallel coordinate axes based on pointer proximity:

```js
function cartesianFisheye(positions, focus, distortion = 3, radius) {
  radius = radius || Math.max(...positions) * 0.4;
  return positions.map(x => {
    const dx = x - focus;
    const dd = Math.abs(dx);
    if (dd >= radius) return x;
    const k = distortion;
    const d = dd / radius;
    const t = d * (k + 1) / (d * k + 1);
    return focus + Math.sign(dx) * t * radius;
  });
}
```

Apply on pointermove:

```js
container.on("pointermove", (event) => {
  const [mx] = d3.pointer(event);
  const distorted = cartesianFisheye(axisPositions, mx);

  axisGroups.attr("transform", (d, i) => `translate(${distorted[i]}, 0)`);
  updateCanvasWithPositions(distorted);
});

container.on("pointerleave", () => {
  // snap back to uniform spacing
  axisGroups.transition().duration(300)
    .attr("transform", (d, i) => `translate(${axisPositions[i]}, 0)`);
  updateCanvasWithPositions(axisPositions);
});
```

### Radial Fisheye (for 2D layouts)

For scatterplots, node-link diagrams, maps:

```js
function radialFisheye(points, focus, distortion = 3, radius = 200) {
  return points.map(([x, y]) => {
    const dx = x - focus[0];
    const dy = y - focus[1];
    const dd = Math.hypot(dx, dy);
    if (dd >= radius || dd === 0) return [x, y];
    const k = distortion;
    const d = dd / radius;
    const t = d * (k + 1) / (d * k + 1);
    const scale = t * radius / dd;
    return [focus[0] + dx * scale, focus[1] + dy * scale];
  });
}
```

## Cross-Chart Linking (Brush & Link)

Coordinated selection across multiple views of the same data.

### Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  View A      │    │  View B      │    │  View C      │
│  (scatter)   │    │  (parcoords) │    │  (histogram) │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────┬───────┘───────────────────┘
                   │
            ┌──────▼──────┐
            │  Selection  │
            │  Manager    │
            │  (EventTarget)│
            └─────────────┘
```

### Selection Manager

```js
class SelectionManager extends EventTarget {
  #selected = new Set();
  #data = [];

  constructor(data) {
    super();
    this.#data = data;
  }

  select(indices, source) {
    this.#selected = new Set(indices);
    this.dispatchEvent(new CustomEvent("selection", {
      detail: { indices, source }
    }));
  }

  toggle(index, source) {
    if (this.#selected.has(index)) {
      this.#selected.delete(index);
    } else {
      this.#selected.add(index);
    }
    this.dispatchEvent(new CustomEvent("selection", {
      detail: { indices: [...this.#selected], source }
    }));
  }

  clear(source) {
    this.#selected.clear();
    this.dispatchEvent(new CustomEvent("selection", {
      detail: { indices: [], source }
    }));
  }

  // "All selected if empty" semantics: when nothing is explicitly selected,
  // treat every item as selected. This avoids a blank visualization state
  // and means views always show the full dataset until the user brushes.
  isSelected(index) {
    return this.#selected.size === 0 || this.#selected.has(index);
  }
  get selected() {
    return this.#selected.size === 0
      ? this.#data.map((_, i) => i)
      : [...this.#selected];
  }
  get selectedData() { return this.selected.map(i => this.#data[i]); }
}
```

### Connecting Views

```js
const manager = new SelectionManager(data);

// Each view listens and updates when selection changes
manager.addEventListener("selection", ({ detail: { indices, source } }) => {
  if (source !== "scatter") scatterView.highlight(indices);
  if (source !== "parcoords") parcoordView.highlight(indices);
  if (source !== "histogram") histogramView.highlight(indices);
});

// Each view reports selections
scatterView.onBrush = (indices) => manager.select(indices, "scatter");
parcoordView.onBrush = (indices) => manager.select(indices, "parcoords");
histogramView.onClick = (index) => manager.toggle(index, "histogram");
```

### Highlight Rendering Pattern

For canvas views, maintain two canvases — background (all data, dimmed) and foreground (selection, vivid):

```js
function highlight(ctx, bgCtx, data, selectedSet, drawFn) {
  // Background: all data, very dim
  bgCtx.clearRect(0, 0, width, height);
  bgCtx.globalAlpha = 0.05;
  data.forEach(d => drawFn(bgCtx, d));

  // Foreground: selected data, full color
  ctx.clearRect(0, 0, width, height);
  ctx.globalAlpha = 0.8;
  data.forEach((d, i) => {
    if (selectedSet.has(i)) drawFn(ctx, d);
  });
}
```

### Linked View Transition Timing

Linked views must feel instantaneous during brushing. Long transitions (300ms+) make the interface feel sluggish because the brush fires continuously as the user drags.

For small datasets (<1k elements), use a very short transition with an aggressive ease-out so the view snaps to the new state:

```js
manager.addEventListener("selection", ({ detail: { indices } }) => {
  bars.data(computeSelected(indices))
    .transition().duration(80).ease(d3.easeExpOut)
    .attr("y", d => d.y)
    .attr("height", d => d.h);
});
```

`easeExpOut` front-loads the motion — the bar jumps most of the way in the first frame, then settles. This feels responsive while avoiding jarring pops.

For large datasets where the linked view does expensive recomputation (re-binning, re-aggregating), skip the transition entirely and update with direct `.attr()` calls. The recomputation cost already provides enough visual delay.

## Lasso Selection

Freeform selection by drawing an arbitrary closed shape. For the point-in-polygon test, prefer `d3.polygonContains` from d3-polygon — it's the same ray-casting algorithm but tested and maintained. The hand-rolled version below is still useful in Web Workers where importing d3-polygon adds bundle complexity.

```js
function lasso(container, pointAccessor) {
  let path = [];
  let lassoPoly = null;

  container.on("pointerdown", (event) => {
    if (!event.shiftKey) return; // shift+drag for lasso
    path = [d3.pointer(event)];
    container.setPointerCapture(event.pointerId);
  });

  container.on("pointermove", (event) => {
    if (!path.length) return;
    path.push(d3.pointer(event));
    drawLassoPath(path);
  });

  container.on("pointerup", (event) => {
    if (!path.length) return;
    path.push(path[0]); // close the polygon
    lassoPoly = path;

    // test which points are inside the polygon
    const selected = data.reduce((acc, d, i) => {
      const pt = pointAccessor(d);
      if (pointInPolygon(pt, lassoPoly)) acc.push(i);
      return acc;
    }, []);

    onSelect(selected);
    path = [];
  });
}

// Ray-casting point-in-polygon test
function pointInPolygon([x, y], polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if ((yi > y) !== (yj > y) &&
        x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}
```

## Pointer Events Best Practices

Always use Pointer Events over Mouse Events:

```js
// Good: works with mouse, touch, pen
element.on("pointerdown", handler);
element.on("pointermove", handler);
element.on("pointerup", handler);

// Bad: mouse-only
element.on("mousedown", handler);
```

### Pointer Capture

Capture the pointer so drag operations work even when the cursor leaves the element:

```js
element.on("pointerdown", function(event) {
  this.setPointerCapture(event.pointerId);
  // now pointermove/pointerup fire on this element
  // even if the pointer moves outside it
});
```

### Coalesced Events for Smooth Drawing

For lasso/freeform drawing, use coalesced events to capture all intermediate points:

```js
element.on("pointermove", (event) => {
  const coalesced = event.getCoalescedEvents?.() || [event];
  coalesced.forEach(e => {
    path.push(d3.pointer(e));
  });
});
```

## Accessibility: Keyboard Brush Adjustment

Brushes are pointer-driven by default. Add keyboard alternatives so users can adjust brush extents without a mouse:

```js
function keyboardBrush(brushGroup, brushBehavior, scale, dimension, step = 5) {
  // Make the brush group focusable
  brushGroup.attr("tabindex", 0).attr("role", "slider")
    .attr("aria-label", `Filter on ${dimension}`);

  brushGroup.on("keydown", (event) => {
    const sel = d3.brushSelection(brushGroup.node());
    if (!sel) return;

    let [y0, y1] = sel;
    const delta = event.shiftKey ? step * 5 : step; // shift = bigger steps

    switch (event.key) {
      case "ArrowUp":   y0 -= delta; y1 -= delta; break; // move brush up
      case "ArrowDown": y0 += delta; y1 += delta; break; // move brush down
      case "ArrowLeft": y1 -= delta; break;               // shrink extent
      case "ArrowRight": y1 += delta; break;              // grow extent
      case "Escape":    brushBehavior.move(brushGroup, null); return;
      case "Enter":     /* confirm — trigger linked update */ break;
      default: return;
    }
    event.preventDefault();

    // Clamp to axis range
    y0 = Math.max(0, y0);
    y1 = Math.min(height, y1);
    if (y1 - y0 < 1) return; // don't collapse to nothing

    brushBehavior.move(brushGroup, [y0, y1]);
  });
}
```

## Spatial Indexing for Intersection Testing

For 10k+ rows, testing every polyline segment against the query line is slow. A simple grid index partitions segments into cells so you only test segments near the query line.

### Grid-Based Spatial Index

```js
function buildSegmentGrid(polylines, cellSize = 50, bounds) {
  const cols = Math.ceil(bounds.width / cellSize);
  const grid = new Map(); // "col,row" → [{polylineIdx, segIdx}]

  polylines.forEach((points, pi) => {
    for (let si = 0; si < points.length - 1; si++) {
      const [x0, y0] = points[si];
      const [x1, y1] = points[si + 1];
      // Rasterize the segment's bounding box into grid cells
      const minC = Math.floor(Math.min(x0, x1) / cellSize);
      const maxC = Math.floor(Math.max(x0, x1) / cellSize);
      const minR = Math.floor(Math.min(y0, y1) / cellSize);
      const maxR = Math.floor(Math.max(y0, y1) / cellSize);
      for (let c = minC; c <= maxC; c++) {
        for (let r = minR; r <= maxR; r++) {
          const key = `${c},${r}`;
          if (!grid.has(key)) grid.set(key, []);
          grid.get(key).push({ pi, si });
        }
      }
    }
  });
  return { grid, cellSize };
}

function queryGrid(index, queryStart, queryEnd, polylines) {
  const { grid, cellSize } = index;
  const [qx0, qy0] = queryStart;
  const [qx1, qy1] = queryEnd;

  // Find cells the query line passes through
  const minC = Math.floor(Math.min(qx0, qx1) / cellSize);
  const maxC = Math.floor(Math.max(qx0, qx1) / cellSize);
  const minR = Math.floor(Math.min(qy0, qy1) / cellSize);
  const maxR = Math.floor(Math.max(qy0, qy1) / cellSize);

  const hits = new Set();
  for (let c = minC; c <= maxC; c++) {
    for (let r = minR; r <= maxR; r++) {
      const candidates = grid.get(`${c},${r}`) || [];
      for (const { pi, si } of candidates) {
        if (hits.has(pi)) continue; // already selected
        const seg = [polylines[pi][si], polylines[pi][si + 1]];
        if (segmentsIntersect(seg[0], seg[1], queryStart, queryEnd)) {
          hits.add(pi);
        }
      }
    }
  }
  return [...hits];
}
```

Build the grid once when data/layout changes. Queries against it are O(cells touched) instead of O(all segments).

## Brush Composition

D3's `d3.brush` creates a single rectangular region. Two common needs require composition logic on top.

### Multi-Region Selection (Shift+Drag)

Hold shift to add a new brush rectangle without clearing the previous ones. Store regions as an array of extents, render them as SVG rects, and union-test all regions on each update:

```js
let regions = [];

brush.on("end", ({ selection, sourceEvent }) => {
  if (!selection) return;
  if (sourceEvent?.shiftKey) {
    regions.push(selection);
  } else {
    regions = [selection];
  }
  const selected = new Set();
  for (const [[x0, y0], [x1, y1]] of regions) {
    data.forEach((d, i) => {
      const px = xScale(d.x), py = yScale(d.y);
      if (px >= x0 && px <= x1 && py >= y0 && py <= y1) selected.add(i);
    });
  }
  manager.select([...selected], "scatter");
});
```

### Cross-View Composition (Union vs. Intersect)

When multiple views each produce a selection, you need a rule for combining them. Extend `SelectionManager` with a `mode` property:

- **Union**: a point is selected if it falls in *any* active brush. Use when brushes filter the same dimension (e.g., two histograms of the same variable).
- **Intersect**: a point is selected if it satisfies *all* active brushes. Use when brushes filter different dimensions (e.g., scatter X brush + histogram Y brush). This is the more common cross-filtering pattern.

```js
class ComposableSelectionManager extends EventTarget {
  #sources = new Map(); // source → Set<index>
  #mode; // "union" | "intersect"

  constructor(mode = "intersect") {
    super();
    this.#mode = mode;
  }

  update(source, indices) {
    if (indices.length === 0) this.#sources.delete(source);
    else this.#sources.set(source, new Set(indices));
    this.#resolve();
  }

  #resolve() {
    const active = [...this.#sources.values()].filter(s => s.size > 0);
    let result;
    if (active.length === 0) {
      this.dispatchEvent(new CustomEvent("selection", { detail: { indices: [] } }));
      return;
    }
    if (this.#mode === "union") {
      result = new Set(active.flatMap(s => [...s]));
    } else {
      result = new Set(active[0]);
      for (let k = 1; k < active.length; k++) {
        for (const i of result) if (!active[k].has(i)) result.delete(i);
      }
    }
    this.dispatchEvent(new CustomEvent("selection", { detail: { indices: [...result] } }));
  }
}
```

## Scalable Cross-Filtering (Falcon Pattern)

The `SelectionManager` refilters data on every brush event — O(N) per update per view. Beyond ~50K rows, this becomes the bottleneck. The Falcon approach (Moritz & Heer, CHI 2019) makes brush updates O(1) by prefetching aggregation indices.

### When to Use

- **SelectionManager** (above): <50K rows, or views that show individual items (scatter, parallel coordinates).
- **Falcon-style prefetch**: 50K+ rows with histogram/aggregate passive views. The key insight is that cross-filtering is an *aggregation* problem — you don't need to refilter individual rows, just recompute bin counts.
- **DuckDB-WASM**: 100K–30M rows in the browser without a server. Serves as the aggregation backend for Falcon-style queries.

### How It Works

1. **On hover** over a view (before the brush starts), prefetch a prefix-sum index for that view's dimension against all passive views.
2. **During brushing**, compute updated counts for all passive views via constant-time prefix-sum lookups.
3. **Resolution trade-off**: lower resolution at brush edges (still dragging), high resolution at center.

```js
// Prefetch when user hovers — hides latency before they start brushing
views.forEach(view => {
  view.container.on("pointerenter", async () => {
    activeIndex = await buildPrefixSumIndex(data, {
      active: view.dimension,
      passive: views.filter(v => v !== view).map(v => v.dimension),
      bins: view.bins,
    });
  });
});

// During brush: O(1) lookups instead of O(N) scans
function onBrush(extent) {
  if (!activeIndex) return; // fallback to naive filtering
  const updates = activeIndex.query(extent);
  updates.forEach(({ dimension, counts }) => {
    findView(dimension).updateCounts(counts);
  });
}
```

The [falcon-vis](https://github.com/cmudig/falcon-vis) library (as of March 2026) provides a ready-made implementation with DuckDB-WASM and Arrow backends. For a pure D3 solution, build the prefix sums yourself over binned data — the math is straightforward for 1D histograms.

### Progressive Filtering for Item Views

Falcon solves aggregation views. For scatter/item views with 50K+ points where you must test each item, use sample-first progressive filtering:

```js
// Build a fixed random sample via reservoir sampling
const sample = reservoirSample(data.length, 2000);
let idleId;

brush.on("brush", ({ selection }) => {
  if (!selection) return;
  const [[x0, y0], [x1, y1]] = selection;

  // Immediate: test sample only (~2K items, <1ms)
  const approx = [];
  for (const i of sample) {
    const px = projected[i * 2], py = projected[i * 2 + 1];
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) approx.push(i);
  }
  manager.select(approx, "scatter");

  // Deferred: full scan when idle
  cancelIdleCallback(idleId);
  idleId = requestIdleCallback(() => {
    const full = [];
    for (let i = 0; i < data.length; i++) {
      if (inExtent(i, x0, y0, x1, y1)) full.push(i);
    }
    manager.select(full, "scatter");
  });
});
```

On `brush.end`, run the full scan synchronously to ensure the final selection is exact. The visual effect: the viewer sees an approximate highlight instantly during drag, refined to the exact set when they stop.

## Performance at Scale

For brushing over 10K+ elements on Canvas, see the `canvas` skill's frame budgeting and render queue patterns — rAF-gated redraws prevent main-thread blocking during continuous brush updates. For WebGL-backed views, see `webgl` for `bufferSubData` partial updates during interaction.

## Common Pitfalls

1. **Brush coordinates in transformed space**: If your SVG has zoom transforms, convert pointer coordinates with `d3.zoomTransform(svg.node()).invert([x, y])`.
2. **Selection flicker**: When hover and selection both trigger redraws, debounce or use separate render passes.
3. **Fisheye performance**: Recalculating positions on every pointermove is expensive for large layouts. Throttle to every other frame or use a spatial index.
4. **Lasso on Canvas**: The lasso UI (the drawn path) must be on SVG or a separate canvas layer — drawing it on the data canvas requires full redraws.
5. **Cross-view infinite loops**: A view that both emits and listens to the selection manager will re-trigger itself. The `source` parameter prevents this.
6. **Touch vs. mouse semantics**: Touch has no hover state. Don't rely on mouseover for essential interactions — use tap/long-press alternatives.

## References

- [D3 Brush documentation](https://d3js.org/d3-brush) — Mike Bostock's API reference for `d3-brush`
- [d3-polygon](https://d3js.org/d3-polygon) — `polygonContains` for idiomatic point-in-polygon testing
- [Crossfilter](https://square.github.io/crossfilter/) — fast multidimensional filtering, the conceptual foundation for linked brushing
- [Falcon (CHI 2019)](https://idl.cs.washington.edu/files/2019-Falcon-CHI.pdf) — Moritz & Heer, prefetch-based O(1) cross-filtering
- [falcon-vis](https://github.com/cmudig/falcon-vis) — library implementing Falcon with DuckDB-WASM and Arrow backends
- [Focus + Context via Brushing](https://observablehq.com/@d3/focus-context) — canonical brush-driven zoom pattern
- [d3-lasso](https://github.com/skokenes/d3-lasso) — Steve Kokenes's lasso selection plugin for D3
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — Kai Chang's parallel coordinates library, pioneering axis-specific brush-linked views in D3
- [Nutrient Parallel Coordinates](https://blocks.roadtolarissa.com/syntagmatic/3150059) — interactive example of multi-axis brushing with linked highlighting
- [Dynamic Queries for Information Exploration](https://www.cs.umd.edu/~ben/papers/Shneiderman1994Dynamic.pdf) — Ben Shneiderman's research on direct manipulation filtering (CHI 1994)
- [Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events) — MDN reference for unified mouse/touch/pen input
