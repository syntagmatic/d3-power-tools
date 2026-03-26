# Brushing & Selection Research

Research into state-of-the-art brushing and selection techniques beyond what the current skill covers.

## Current Coverage

The `skills/brushing/SKILL.md` covers:

- **Line intersection brushing** ("pinch"): query line across polylines, segment intersection test with cross product math, applied to parallel coordinates
- **Web Worker offloading**: move intersection testing off main thread for 10k+ rows
- **Render queue**: progressive canvas rendering with shuffle (delegates to canvas skill)
- **Fisheye distortion**: cartesian (for axes) and radial (for 2D layouts)
- **Cross-chart linking**: `SelectionManager` extending `EventTarget`, foreground/background canvas pattern, linked view transition timing (80ms with easeExpOut)
- **Lasso selection**: freeform polygon drawing with pointer capture, ray-casting point-in-polygon test, coalesced events for smooth drawing
- **Keyboard brush adjustment**: arrow keys to move/resize brush extents, ARIA roles
- **Spatial indexing**: grid-based segment index for fast intersection queries
- **Pointer Events best practices**: capture, coalesced events

Gaps identified: scalable cross-filtering for large data, brush composition (union/intersection/difference), progressive/approximate filtering during drag, Observable Plot integration patterns.

## Falcon and Scalable Cross-Filtering

**Source**: [Falcon (CHI 2019)](https://dl.acm.org/doi/10.1145/3290605.3300924) by Moritz and Heer. Library: [falcon-vis](https://github.com/cmudig/falcon-vis).

### Core Insight

Cross-filtering is fundamentally an aggregation problem. When the user brushes one view (the *active view*), all other views (*passive views*) must recompute their histograms/aggregations. Naively, this is O(N) per brush update per passive view. Falcon makes it O(1) per update by prefetching a data structure called the **Falcon index**.

### How It Works

1. **On hover** over a view (before the brush starts), Falcon prefetches the index for that view. The index is a set of 2D aggregation cubes: for each passive view's binned dimension, it stores prefix sums over the active view's dimension.
2. **During brushing**, computing updated counts for all passive views is a constant-time lookup into the prefix sums, regardless of data size.
3. **Resolution sensitivity**: Falcon balances index resolution against latency. Users are less sensitive to resolution at the edges of a brush (they're still dragging), so Falcon uses lower resolution there and high resolution at the brush center.

### Performance

- 50fps brush updates, invariant from thousands to billions of records
- Browser-only: 10M rows with Arrow, 33M with DuckDB-WASM
- With backend: 180M flights (OmniSciDB), 1.7B stars (Gaia)

### Architecture Pattern

```
User hovers view A → prefetch Falcon index for A
User brushes view A → for each passive view B:
  counts_B = prefixSum[bin_hi] - prefixSum[bin_lo]  // O(1)
  redraw histogram B with counts_B
```

### What to Add to the Skill

The current `SelectionManager` operates on row indices — it refilters data on every brush event. For datasets beyond ~50K rows, this becomes the bottleneck. The skill should document:

1. **When to use Falcon vs. SelectionManager**: SelectionManager for <50K rows or non-histogram views; Falcon for histogram-based cross-filtering at scale.
2. **DuckDB-WASM integration**: for medium-scale (100K–30M), DuckDB in the browser can serve as the aggregation backend without a server.
3. **Prefetch-on-hover**: start computing the index when the user *hovers* a view, not when they start brushing. This hides latency.

## Lasso and Freeform Selection

### Current State of d3-lasso

The [d3-lasso](https://github.com/skokenes/d3-lasso) plugin by Spencer Kokenes provides a D3 v4/v5 lasso with:
- `closePathSelect(true)`: select items enclosed by the polygon (point-in-polygon)
- `closePathSelect(false)`: select items the lasso path crosses (intersection)
- State tagging: elements get `possible`, `not_possible`, `selected`, `not_selected` classes during and after the lasso gesture

The library hasn't been updated for D3 v7 and uses mouse events, but the API design is worth noting.

### Fil's Observable Lasso Notebooks

Fil (Philippe Riviere) published clean lasso implementations on Observable:
- [Lasso selection (SVG)](https://observablehq.com/@fil/lasso-selection) — uses `d3.polygonContains` for point-in-polygon
- [Lasso selection (Canvas)](https://observablehq.com/@fil/lasso-selection-canvas) — Canvas rendering with the same containment test

Key technique: use `d3.polygonContains(polygon, point)` from d3-polygon instead of rolling your own ray-casting. It's the same algorithm but tested and maintained.

### Patterns Worth Adding

1. **d3.polygonContains over custom pointInPolygon**: the current skill has a hand-rolled ray-casting test. `d3.polygonContains` from d3-polygon is equivalent and more idiomatic. Mention both — the manual version is useful in workers where you can't import d3-polygon.

2. **Lasso for Canvas hit testing**: for scatter plots rendered to Canvas, you still need the data coordinates to test against the lasso polygon. Store the projected [x,y] per datum in a typed array; test against the lasso polygon. No quadtree needed — the polygon test is fast for point data.

3. **Progressive lasso feedback**: while drawing, test containment on every `pointermove` (throttled) to highlight elements inside the partial polygon. The current skill does this for intersection brushing but not for lasso.

4. **Lasso + linked views**: connect lasso output to SelectionManager, same as box brush. The lasso just produces a set of indices.

## Brush Composition

### The Problem

D3's `d3.brush` creates a single rectangular region. Users often want to select multiple disjoint regions, or combine selections from different views with boolean logic (union, intersection, difference).

### Vega-Lite / Altair Approach

Vega-Lite's selection system supports `resolve: "union"` and `resolve: "intersect"` for multi-view selections:
- **Union**: a point is selected if it falls in *any* brush across views
- **Intersect**: a point is selected if it falls in *all* active brushes

This is the most well-developed model for brush composition in the grammar-of-graphics world.

### Implementation Patterns

**Multi-region selection on a single view:**

```js
// Track multiple brush regions
const regions = []; // array of [x0, y0, x1, y1]

function addRegion(extent) {
  regions.push(extent);
  updateSelection();
}

function updateSelection() {
  const selected = new Set();
  for (const [x0, y0, x1, y1] of regions) {
    data.forEach((d, i) => {
      const px = xScale(d.x), py = yScale(d.y);
      if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
        selected.add(i);
      }
    });
  }
  manager.select([...selected], "scatter");
}
```

**Cross-view composition:**

```js
class ComposableSelectionManager extends EventTarget {
  #selections = new Map(); // source → Set of indices
  #mode = "intersect"; // "union" | "intersect" | "difference"

  updateSource(source, indices) {
    this.#selections.set(source, new Set(indices));
    this.#resolve();
  }

  #resolve() {
    const sources = [...this.#selections.values()].filter(s => s.size > 0);
    if (sources.length === 0) {
      this.dispatchEvent(new CustomEvent("selection", { detail: { indices: [] } }));
      return;
    }

    let result;
    if (this.#mode === "union") {
      result = new Set();
      for (const s of sources) for (const i of s) result.add(i);
    } else if (this.#mode === "intersect") {
      result = new Set(sources[0]);
      for (let k = 1; k < sources.length; k++) {
        for (const i of result) if (!sources[k].has(i)) result.delete(i);
      }
    } else if (this.#mode === "difference") {
      result = new Set(sources[0]);
      for (let k = 1; k < sources.length; k++) {
        for (const i of sources[k]) result.delete(i);
      }
    }
    this.dispatchEvent(new CustomEvent("selection", { detail: { indices: [...result] } }));
  }
}
```

### What to Add to the Skill

- Extend `SelectionManager` with a `mode` property and multi-source composition
- Show how to implement shift+drag for additive brush regions in a single view
- Document the union/intersect/difference semantics clearly

## Progressive Filtering

### The Problem

During a brush drag, recomputing the full selection on every `pointermove` event can be too slow for large datasets. The user sees lag between moving the brush and seeing the updated view.

### Progressive Visual Analytics (PVA)

Research from INRIA, CMU, and Georgia Tech describes systems that return approximate results immediately and refine them over time:

- **Approximate early, refine later**: process a random sample first, show approximate counts/aggregations, then refine as computation continues
- **Steering-by-example**: users select data items to prioritize computation in that subspace
- **Confidence indicators**: show uncertainty (error bars, fading) on approximate results

Key paper: [How Progressive Visualizations Affect Exploratory Analysis](https://emanuelzgraggen.com/assets/pdf/progressive_jrnl.pdf) — Zgraggen et al. found that progressive results improve exploration speed even when final results differ slightly.

### Practical Patterns for D3

**Sample-first filtering:**

```js
// During brush drag: test a random sample for instant feedback
const SAMPLE_SIZE = 2000;
const sampleIndices = reservoir(data.length, SAMPLE_SIZE);

function onBrushMove(extent) {
  // Fast path: test only the sample
  const approx = sampleIndices.filter(i => inExtent(data[i], extent));
  manager.select(approx, "scatter", { approximate: true });

  // Schedule full computation
  cancelIdleCallback(fullComputeId);
  fullComputeId = requestIdleCallback(() => {
    const full = data.reduce((acc, d, i) => {
      if (inExtent(d, extent)) acc.push(i);
      return acc;
    }, []);
    manager.select(full, "scatter", { approximate: false });
  });
}
```

**Chunked filtering with progress:**

```js
function* filterChunked(data, predicate, chunkSize = 5000) {
  const results = [];
  for (let i = 0; i < data.length; i += chunkSize) {
    const end = Math.min(i + chunkSize, data.length);
    for (let j = i; j < end; j++) {
      if (predicate(data[j])) results.push(j);
    }
    yield { results: [...results], progress: end / data.length };
  }
}
```

### Falcon's Approach (Revisited)

Falcon solves this differently — by prefetching, the brush updates are O(1) so no approximation is needed. This is the best solution when views are histograms/aggregations. Progressive filtering is more relevant when the view shows individual data items (scatter, parallel coordinates).

### What to Add to the Skill

- Sample-first pattern for immediate brush feedback on 50K+ point datasets
- `requestIdleCallback` for deferred full computation
- Confidence indicator pattern (alpha encoding for approximate vs confirmed selections)

## Observable Plot Brush Patterns

### Current State (as of 2025)

Observable Plot added brush/selection support experimentally. The [linked brushing blog post](https://observablehq.com/blog/linked-brushing) (January 2025) describes the interaction model:

- Brushing is built on `d3.brush` under the hood
- Plot's faceting system (`fx`, `fy`) creates small multiples, and brushing can be coordinated across facets
- The `pointer` interaction (Plot 0.6.7+) provides hover-based selection with the `tip` mark

### Integration with D3 Skills

Plot's brush is high-level and opinionated — good for dashboards, but for custom interactions (lasso, intersection brush, fisheye), you need raw D3. The relevant patterns:

1. **Plot for passive views, D3 for active views**: use Plot to render linked histograms that update from a SelectionManager, while the primary view uses custom D3 brushing.
2. **Shared data filtering**: Plot's `transform` option can filter data reactively. Connect it to SelectionManager events.
3. **Plot's facet brush**: when using small multiples, Plot handles the per-facet brush automatically. For custom cross-facet linking, use D3's brush on each facet SVG and connect through SelectionManager.

### What to Add to the Skill

Minimal — Plot integration is more of a composition concern than a brushing concern. A brief note pointing to Plot for simple linked brushing use cases would suffice.

## Decision Guidance

| Scenario | Technique | Why |
|---|---|---|
| <1K points, simple views | `d3.brush` + SelectionManager | Direct, no optimization needed |
| 1K–50K points, scatter/parcoords | Lasso or intersection brush + Web Worker | Worker prevents jank during drag |
| 50K+ points, histogram views | Falcon index or DuckDB-WASM | O(1) brush updates via prefetched aggregation |
| 50K+ points, scatter views | Sample-first progressive filtering | Immediate approximate feedback |
| Multiple disjoint regions | Shift+drag additive brush regions | Union of rectangles |
| Cross-view, same dimension | SelectionManager with union mode | Any brush selects |
| Cross-view, different dimensions | SelectionManager with intersect mode | All brushes must agree |
| Small multiples / facets | Per-facet brush + shared SelectionManager | Or use Observable Plot's built-in facet brush |
| Touch / pen input | Pointer Events + capture | Already covered in skill |

## Code Patterns

### Pattern 1: d3.polygonContains for Lasso (Idiomatic)

Replace the hand-rolled ray-casting with D3's built-in:

```js
import { polygonContains } from "d3-polygon";

// In lasso pointerup handler:
const selected = data.reduce((acc, d, i) => {
  const pt = pointAccessor(d);
  if (polygonContains(lassoPoly, pt)) acc.push(i);
  return acc;
}, []);
```

The manual `pointInPolygon` is still useful in Web Workers where importing d3-polygon adds bundle complexity.

### Pattern 2: Falcon-Style Prefetch-on-Hover

```js
import { FalconIndex } from "falcon-vis";

const views = [histA, histB, histC];
let activeIndex = null;

// Prefetch when user hovers a view — before they start brushing
views.forEach(view => {
  view.container.on("pointerenter", async () => {
    activeIndex = await FalconIndex.build(data, {
      active: view.dimension,
      passive: views.filter(v => v !== view).map(v => v.dimension),
      bins: view.bins,
    });
  });
});

// During brush: O(1) lookups
function onBrush(extent) {
  if (!activeIndex) return; // fallback to naive
  const updates = activeIndex.query(extent);
  updates.forEach(({ dimension, counts }) => {
    const view = views.find(v => v.dimension === dimension);
    view.updateCounts(counts);
  });
}
```

### Pattern 3: Additive Multi-Region Brush

```js
let regions = [];

const brush = d3.brush()
  .on("end", ({ selection }) => {
    if (!selection) return;
    if (d3.event?.sourceEvent?.shiftKey) {
      regions.push(selection); // add to existing
    } else {
      regions = [selection]; // replace
    }
    const selected = new Set();
    for (const [[x0, y0], [x1, y1]] of regions) {
      data.forEach((d, i) => {
        const px = xScale(d.x), py = yScale(d.y);
        if (px >= x0 && px <= x1 && py >= y0 && py <= y1) selected.add(i);
      });
    }
    manager.select([...selected], "scatter");

    // Draw all active regions
    regionsGroup.selectAll("rect")
      .data(regions)
      .join("rect")
      .attr("x", d => d[0][0]).attr("y", d => d[0][1])
      .attr("width", d => d[1][0] - d[0][0])
      .attr("height", d => d[1][1] - d[0][1])
      .attr("class", "brush-region");
  });
```

### Pattern 4: ComposableSelectionManager

```js
class ComposableSelectionManager extends EventTarget {
  #sources = new Map(); // source → Set<index>
  #data;
  #mode; // "union" | "intersect"

  constructor(data, mode = "intersect") {
    super();
    this.#data = data;
    this.#mode = mode;
  }

  set mode(m) { this.#mode = m; this.#emit(); }

  update(source, indices) {
    if (indices.length === 0) {
      this.#sources.delete(source);
    } else {
      this.#sources.set(source, new Set(indices));
    }
    this.#emit();
  }

  #emit() {
    const active = [...this.#sources.values()].filter(s => s.size > 0);
    let resolved;

    if (active.length === 0) {
      resolved = this.#data.map((_, i) => i); // all-selected-if-empty
    } else if (this.#mode === "union") {
      resolved = [...new Set(active.flatMap(s => [...s]))];
    } else {
      // intersect: start with first, keep only those in all others
      resolved = [...active[0]];
      for (let k = 1; k < active.length; k++) {
        resolved = resolved.filter(i => active[k].has(i));
      }
    }

    this.dispatchEvent(new CustomEvent("selection", {
      detail: { indices: resolved, mode: this.#mode }
    }));
  }

  isSelected(index) {
    const active = [...this.#sources.values()].filter(s => s.size > 0);
    if (active.length === 0) return true;
    return this.#mode === "union"
      ? active.some(s => s.has(index))
      : active.every(s => s.has(index));
  }
}
```

### Pattern 5: Sample-First Progressive Brush

```js
// Build a fixed random sample for fast approximate filtering
function buildSample(n, sampleSize) {
  const indices = new Uint32Array(sampleSize);
  // Reservoir sampling
  for (let i = 0; i < n; i++) {
    if (i < sampleSize) {
      indices[i] = i;
    } else {
      const j = Math.floor(Math.random() * (i + 1));
      if (j < sampleSize) indices[j] = i;
    }
  }
  return indices;
}

const sample = buildSample(data.length, 2000);
let idleId;

brush.on("brush", ({ selection }) => {
  if (!selection) return;
  const [[x0, y0], [x1, y1]] = selection;

  // Immediate: test sample only
  const approx = [];
  for (const i of sample) {
    const px = projected[i * 2], py = projected[i * 2 + 1];
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) approx.push(i);
  }
  manager.select(approx, "scatter");

  // Deferred: full scan
  cancelIdleCallback(idleId);
  idleId = requestIdleCallback(() => {
    const full = [];
    for (let i = 0; i < data.length; i++) {
      const px = projected[i * 2], py = projected[i * 2 + 1];
      if (px >= x0 && px <= x1 && py >= y0 && py <= y1) full.push(i);
    }
    manager.select(full, "scatter");
  });
});

brush.on("end", () => {
  // Ensure we have the full result on brush end
  cancelIdleCallback(idleId);
  // run full scan synchronously
});
```

---

Sources:
- [falcon-vis (GitHub)](https://github.com/cmudig/falcon-vis)
- [Falcon paper (CHI 2019)](https://dl.acm.org/doi/10.1145/3290605.3300924)
- [Falcon PDF](https://idl.cs.washington.edu/files/2019-Falcon-CHI.pdf)
- [FalconVis + DuckDB demo](https://dig.cmu.edu/falcon-vis/crossfilter-duckdb/)
- [Cross-filtering 3M with FalconVis (Observable)](https://observablehq.com/@cmudig/falcon-vis-3m)
- [d3-lasso plugin](https://github.com/skokenes/d3-lasso)
- [Fil's lasso selection (SVG)](https://observablehq.com/@fil/lasso-selection)
- [Fil's lasso selection (Canvas)](https://observablehq.com/@fil/lasso-selection-canvas)
- [d3-polygon](https://d3js.org/d3-polygon)
- [Observable linked brushing blog](https://observablehq.com/blog/linked-brushing)
- [d3-brush docs](https://d3js.org/d3-brush)
- [Vega-Lite interaction curriculum](https://idl.uw.edu/visualization-curriculum/altair_interaction.html)
- [Progressive Visual Analytics (INRIA)](https://www.aviz.fr/Research/ProgressiveDataAnalysis)
- [Progressive Visualizations and Exploratory Analysis](https://emanuelzgraggen.com/assets/pdf/progressive_jrnl.pdf)
- [Steering-by-Example for PVA](https://vis-au.github.io/prosteer/)
- [Brushable scatterplot matrix (Observable)](https://observablehq.com/@d3/brushable-scatterplot-matrix)
