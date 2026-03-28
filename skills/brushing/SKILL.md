---
name: brushing
description: "Build advanced brushing, selection, and cross-chart linking interactions for D3.js visualizations. Use this skill whenever the user wants to add brushing, filtering, linked views, coordinated highlighting, lasso selection, fisheye distortion, or any form of interactive data selection to a D3 visualization. Also use when the user mentions cross-filtering, brush-and-link, focus+context, intersection brushing, or wants to connect multiple charts that highlight the same data."
---

# Advanced Brushing & Selection

Selection and filtering interactions for data-dense visualizations. Modernizes techniques from d3.parcoords -- line intersection brushing, cross-chart linking, fisheye focus -- with Web Workers and Pointer Events.

## Choosing a Selection Approach

| Scenario | Technique | Why |
|---|---|---|
| <1K points, simple views | `d3.brush` + SelectionManager | Direct, no optimization needed |
| 1K-50K points, scatter/parcoords | Lasso or intersection brush + Web Worker | Worker prevents jank during drag |
| 50K+ points, histogram/aggregate | Falcon-style prefetch or DuckDB-WASM | O(1) brush updates via prefetched aggregation |
| 50K+ points, scatter/item views | Sample-first progressive filtering | Approximate feedback, refine on idle |
| Multiple disjoint regions | Shift+drag additive brush | Union of rectangles on one view |
| Cross-view, same dimension | SelectionManager with union mode | Any brush selects |
| Cross-view, different dimensions | SelectionManager with intersect mode | All brushes must agree |

**Observable Plot note:** Plot's built-in brush handles simple linked brushing. Drop to raw D3 for lasso, intersection brushing, fisheye, or custom composition.

## Line Intersection Brushing

### Segment Intersection Test

```js
// Cross-product orientation test: true if segment (p1->p2) crosses (p3->p4)
function segmentsIntersect(p1, p2, p3, p4) {
  const d1 = direction(p3, p4, p1), d2 = direction(p3, p4, p2);
  const d3 = direction(p1, p2, p3), d4 = direction(p1, p2, p4);
  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
  if (d1 === 0 && onSegment(p3, p4, p1)) return true;
  if (d2 === 0 && onSegment(p3, p4, p2)) return true;
  if (d3 === 0 && onSegment(p1, p2, p3)) return true;
  if (d4 === 0 && onSegment(p1, p2, p4)) return true;
  return false;
}
const direction = (pi, pj, pk) =>
  (pk[0] - pi[0]) * (pj[1] - pi[1]) - (pj[0] - pi[0]) * (pk[1] - pi[1]);
const onSegment = (pi, pj, pk) =>
  Math.min(pi[0], pj[0]) <= pk[0] && pk[0] <= Math.max(pi[0], pj[0]) &&
  Math.min(pi[1], pj[1]) <= pk[1] && pk[1] <= Math.max(pi[1], pj[1]);
```

### Applying to Parallel Coordinates

```js
function intersectionBrush(queryStart, queryEnd, data, dimensions, scales, xPositions) {
  return data.filter(d => {
    const pts = dimensions.map((dim, i) => [xPositions[i], scales[dim](d[dim])]);
    return pts.slice(0, -1).some((p, i) =>
      segmentsIntersect(p, pts[i + 1], queryStart, queryEnd));
  });
}
```

### Interaction

Alt+click or right-click starts the query line. On `pointermove`, update the line endpoint and run `intersectionBrush`. On `pointerup`, finalize. Use `setPointerCapture` so the drag works outside the SVG.

**Web Worker for 10K+ rows:** post `{queryStart, queryEnd, polylines}` to a worker containing `segmentsIntersect`. The worker returns `{selectedIndices}`. This keeps the main thread free during drag.

## Render Queue

See `canvas` skill for `createRenderQueue`. For brushing: call `cancel()` when selection changes to prevent stale renders. In workers (no `rAF`), use `setTimeout(0)` between batches.

## Fisheye Distortion

Core formula: distance `d` (normalized to `[0, radius]`) maps through `d*(k+1)/(d*k+1)` where `k` is distortion strength.

### Cartesian Fisheye (for parallel coordinate axes)

```js
function cartesianFisheye(positions, focus, distortion = 3, radius) {
  radius = radius || Math.max(...positions) * 0.4;
  return positions.map(x => {
    const dx = x - focus, dd = Math.abs(dx);
    if (dd >= radius) return x;
    const t = (dd / radius) * (distortion + 1) / ((dd / radius) * distortion + 1);
    return focus + Math.sign(dx) * t * radius;
  });
}
```

Apply on `pointermove` to axis positions; snap back on `pointerleave` with a 300ms transition.

**Radial fisheye** (scatterplots, node-link, maps): same formula applied to `Math.hypot(dx, dy)` in 2D. Scale `dx`/`dy` by `t * radius / dd` to get the distorted `[x, y]`.

## Cross-Chart Linking

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

### SelectionManager

```js
class SelectionManager extends EventTarget {
  #selected = new Set();
  #data = [];
  constructor(data) { super(); this.#data = data; }

  select(indices, source) {
    this.#selected = new Set(indices);
    this.dispatchEvent(new CustomEvent("selection", { detail: { indices, source } }));
  }
  toggle(index, source) {
    this.#selected[this.#selected.has(index) ? "delete" : "add"](index);
    this.dispatchEvent(new CustomEvent("selection", {
      detail: { indices: [...this.#selected], source }
    }));
  }
  clear(source) { this.select([], source); }

  // "All selected if empty" -- views show full dataset until brushed
  isSelected(index) { return this.#selected.size === 0 || this.#selected.has(index); }
  get selected() {
    return this.#selected.size === 0 ? this.#data.map((_, i) => i) : [...this.#selected];
  }
  get selectedData() { return this.selected.map(i => this.#data[i]); }
}
```

### Connecting Views

```js
const manager = new SelectionManager(data);
manager.addEventListener("selection", ({ detail: { indices, source } }) => {
  if (source !== "scatter") scatterView.highlight(indices);
  if (source !== "parcoords") parcoordView.highlight(indices);
});
scatterView.onBrush = (indices) => manager.select(indices, "scatter");
histogramView.onClick = (index) => manager.toggle(index, "histogram");
```

### Canvas Highlight Pattern

Two canvas layers -- background (all data, `globalAlpha: 0.05`) and foreground (selected, `globalAlpha: 0.8`). Clear both, draw all to background, draw selected to foreground.

### Linked View Timing

Use 80ms transitions with `d3.easeExpOut` -- front-loads motion so it feels snappy. For expensive recomputation (re-binning), skip transitions.

## Lasso Selection

Freeform closed-shape selection. Shift+click starts drawing, `pointermove` appends points (use `getCoalescedEvents` for smooth paths), `pointerup` closes the polygon and tests containment.

```js
// Ray-casting point-in-polygon
function pointInPolygon([x, y], poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi)
      inside = !inside;
  }
  return inside;
}
```

Use `setPointerCapture` so the drag works outside the element. `d3.polygonContains` from d3-polygon is the D3 equivalent when available; the ray-casting version above works in Web Workers.

## Pointer Events

Always use `pointerdown`/`pointermove`/`pointerup` over mouse events. Key patterns:
- **Pointer capture**: `this.setPointerCapture(event.pointerId)` so drag works outside the element.
- **Coalesced events**: `event.getCoalescedEvents?.() || [event]` for smooth freeform drawing.
- **Touch**: no hover state -- use tap/long-press instead of mouseover for essential interactions.

## Keyboard Brush Adjustment

Make brushes keyboard-accessible: set `tabindex="0"` and `role="slider"` on the brush group. Arrow keys move the brush extent (Up/Down shift both handles, Left/Right shrink/expand), Shift multiplies step by 5, Escape clears. Read current extent with `d3.brushSelection(node)`, update with `brushBehavior.move(group, [y0, y1])`.

## Spatial Indexing for Intersection Testing

For 10K+ rows, partition segments into grid cells. Build once; queries are O(cells touched) vs O(all segments):

```js
function buildSegmentGrid(polylines, cellSize = 50) {
  const grid = new Map(), cell = v => Math.floor(v / cellSize);
  polylines.forEach((pts, pi) => {
    for (let si = 0; si < pts.length - 1; si++) {
      const [x0, y0] = pts[si], [x1, y1] = pts[si + 1];
      for (let c = cell(Math.min(x0, x1)); c <= cell(Math.max(x0, x1)); c++)
        for (let r = cell(Math.min(y0, y1)); r <= cell(Math.max(y0, y1)); r++) {
          const key = `${c},${r}`;
          if (!grid.has(key)) grid.set(key, []);
          grid.get(key).push({ pi, si });
        }
    }
  });
  return { grid, cellSize };
}
```

Query: iterate grid cells overlapping the query line, test only those segments with `segmentsIntersect`. Collect unique polyline indices in a Set.

## Brush Composition

### Multi-Region Selection (Shift+Drag)

```js
let regions = [];
brush.on("end", ({ selection, sourceEvent }) => {
  if (!selection) return;
  regions = sourceEvent?.shiftKey ? [...regions, selection] : [selection];
  const selected = new Set();
  for (const [[x0, y0], [x1, y1]] of regions)
    data.forEach((d, i) => {
      if (xScale(d.x) >= x0 && xScale(d.x) <= x1 && yScale(d.y) >= y0 && yScale(d.y) <= y1) selected.add(i);
    });
  manager.select([...selected], "scatter");
});
```

### Cross-View Composition (Union vs. Intersect)

**Union**: selected if in *any* active brush. **Intersect**: selected if in *all* active brushes (the common cross-filtering pattern).

```js
class ComposableSelectionManager extends EventTarget {
  #sources = new Map(); // source -> Set<index>
  #mode;
  constructor(mode = "intersect") { super(); this.#mode = mode; }

  update(source, indices) {
    if (!indices.length) this.#sources.delete(source);
    else this.#sources.set(source, new Set(indices));
    const active = [...this.#sources.values()].filter(s => s.size > 0);
    if (!active.length) { this.#emit([]); return; }
    const result = this.#mode === "union"
      ? new Set(active.flatMap(s => [...s]))
      : active.reduce((acc, s) => { for (const i of acc) if (!s.has(i)) acc.delete(i); return acc; }, new Set(active[0]));
    this.#emit([...result]);
  }
  #emit(indices) { this.dispatchEvent(new CustomEvent("selection", { detail: { indices } })); }
}
```

## Scalable Cross-Filtering (Falcon Pattern)

Beyond ~50K rows, the Falcon approach (Moritz & Heer, CHI 2019) makes brush updates O(1) by prefetching aggregation indices. On `pointerenter`, prefetch a prefix-sum index for the hovered view's dimension; during brushing, compute updated counts via constant-time lookups.

```js
views.forEach(view => {
  view.container.on("pointerenter", async () => {
    activeIndex = await buildPrefixSumIndex(data, {
      active: view.dimension,
      passive: views.filter(v => v !== view).map(v => v.dimension),
      bins: view.bins,
    });
  });
});
function onBrush(extent) {
  if (!activeIndex) return;
  activeIndex.query(extent).forEach(({ dimension, counts }) =>
    findView(dimension).updateCounts(counts));
}
```

The [falcon-vis](https://github.com/cmudig/falcon-vis) library provides a ready-made DuckDB-WASM/Arrow implementation.

**Progressive filtering for item views (50K+ scatter):** test a reservoir sample (~2K) immediately for instant approximate feedback, then full-scan on `requestIdleCallback` for exact results. On `brush.end`, run the full scan synchronously.

## Performance at Scale

See `canvas` skill for frame budgeting and rAF-gated redraws during continuous brush updates. See `webgl` skill for `bufferSubData` partial updates.

## Common Pitfalls

1. **Brush coordinates in transformed space**: If your SVG has zoom transforms, convert with `d3.zoomTransform(svg.node()).invert([x, y])`.
2. **Selection flicker**: When hover and selection both trigger redraws, debounce or use separate render passes.
3. **Fisheye performance**: Recalculating positions on every pointermove is expensive. Throttle to every other frame or use a spatial index.
4. **Lasso on Canvas**: The lasso UI must be on SVG or a separate canvas layer -- drawing it on the data canvas requires full redraws.
5. **Cross-view infinite loops**: A view that emits and listens to the selection manager re-triggers itself. The `source` parameter prevents this.
6. **Touch vs. mouse**: Touch has no hover. Use tap/long-press instead of mouseover for essential interactions.

## References

- [D3 Brush documentation](https://d3js.org/d3-brush) -- API reference for `d3-brush`
- [d3-polygon](https://d3js.org/d3-polygon) -- `polygonContains` for point-in-polygon testing
- [Crossfilter](https://square.github.io/crossfilter/) -- conceptual foundation for linked brushing
- [Falcon (CHI 2019)](https://idl.cs.washington.edu/files/2019-Falcon-CHI.pdf) -- prefetch-based O(1) cross-filtering
- [falcon-vis](https://github.com/cmudig/falcon-vis) -- Falcon with DuckDB-WASM and Arrow backends
- [Focus + Context via Brushing](https://observablehq.com/@d3/focus-context) -- canonical brush-driven zoom
- [d3-lasso](https://github.com/skokenes/d3-lasso) -- Steve Kokenes's lasso selection plugin
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) -- Kai Chang's parallel coordinates library
- [Nutrient Parallel Coordinates](https://blocks.roadtolarissa.com/syntagmatic/3150059) -- multi-axis brushing example
- [Dynamic Queries](https://www.cs.umd.edu/~ben/papers/Shneiderman1994Dynamic.pdf) -- Shneiderman, CHI 1994
- [Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events) -- MDN unified input reference
