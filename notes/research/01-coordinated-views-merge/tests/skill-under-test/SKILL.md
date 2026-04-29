---
name: coordinated-views
description: "Design and implement coordinated multi-view D3 dashboards: linked highlighting, cross-filtering, overview+detail, shared selection state, d3.dispatch/store wiring, render priority, and ghost/active feedback. Use when independent charts need to share selection, hover, filter, zoom, or tooltip state. For lasso, intersection brushing, fisheye, or low-level brush geometry, use brushing."
---

# Coordinated Views

Coordinated views let a viewer ask in one chart and see the answer in the others. The core job is not "add more charts"; it is preserving one shared interpretation of selection, hover, filters, zoom, and tooltips across independent views.

For low-level brush geometry, lasso containment, intersection brushing, fisheye distortion, pointer capture, or keyboard-adjustable brush extents, use `brushing`. This skill starts after a view can produce selected datum keys or a filter predicate.

## When To Link

Link views only when each view contributes a different read of the same underlying records.

- **Complementarity:** the target view must answer "what does this selection look like from that angle?"
- **Parsimony:** 2-4 active views is the normal range. For 5+ views, choose one driver view and cluster the rest as detail panels.
- **Stable identity:** every coordinated mark needs a durable key. Do not coordinate by array index once data can be sorted, filtered, joined, or reloaded.
- **Source awareness:** every emitted change carries a `source` id so the originating chart does not re-trigger itself.

Do not link charts just because they share a page. If two views answer unrelated questions, keep interactions local.

## Core Patterns

### Overview + Detail

An overview chart controls the domain or filter of a detail chart. Keep the overview domain fixed; update the detail view after brush movement. During drag, prefer direct redraw over animated transitions.

### Cross-Filtering

Multiple views act as simultaneous filters over the same records. Each view owns one filter predicate or selected-key set; the active result is the intersection of all non-empty filters.

### Ghost + Active Layers

Show the selected subset against the full dataset.

- Background or ghost layer: all records, muted and stable.
- Foreground or active layer: selected records, higher contrast.
- Density views: scale active density by `selected.length / total.length` so small subsets do not visually overclaim.

### Shared Tooltip

Use one tooltip element for the full dashboard. Pointer focus in one chart hides or replaces tooltip content from any other chart.

## Canonical Selection Model

Use keys, not row indices. Empty selection means "all active." Each view owns one source id and contributes one filter; the model combines them by `mode` (`intersect` for cross-filtering, `union` for "any of these brushes").

```js
class SelectionModel {
  #byKey;
  #filters = new Map(); // source -> Set<key>
  #mode;
  #key;
  #dispatch = d3.dispatch("change", "hover");

  constructor(data, key = d => d.id, { mode = "intersect" } = {}) {
    this.#key = key;
    this.#byKey = new Map(data.map(d => [key(d), d]));
    this.#mode = mode;
  }

  set(source, keys) {
    if (!keys || !keys.length) this.#filters.delete(source);
    else this.#filters.set(source, new Set(keys));
    this.#emit(source);
  }
  clear(source = "reset") {
    this.#filters.clear();
    this.#emit(source);
  }
  hover(source, k) {
    this.#dispatch.call("hover", null, { source, key: k, datum: this.#byKey.get(k) });
  }
  isActive(k) {
    const key = typeof k === "object" ? this.#key(k) : k;
    return this.#activeKeys().has(key);
  }
  on(event, name, fn) {
    this.#dispatch.on(`${event}.${name}`, fn);
    return () => this.#dispatch.on(`${event}.${name}`, null);
  }

  #activeKeys() {
    const sets = [...this.#filters.values()].filter(s => s.size);
    if (!sets.length) return new Set(this.#byKey.keys());
    if (this.#mode === "union") return new Set(sets.flatMap(s => [...s]));
    const out = new Set(sets[0]);
    for (let i = 1; i < sets.length; i++)
      for (const k of out) if (!sets[i].has(k)) out.delete(k);
    return out;
  }
  #emit(source) {
    const keys = this.#activeKeys();
    this.#dispatch.call("change", null, {
      source, keys,
      data: [...keys].map(k => this.#byKey.get(k)).filter(Boolean),
    });
  }
}
```

Views emit only their own source id and ignore changes from themselves:

```js
const selection = new SelectionModel(data, d => d.id);

scatter.onBrush = keys => selection.set("scatter", keys);
histogram.onBrush = keys => selection.set("histogram", keys);

selection.on("change", "scatter", ({ source, keys }) => {
  if (source !== "scatter") scatter.highlight(keys);
});
selection.on("change", "histogram", ({ source, keys }) => {
  if (source !== "histogram") histogram.highlight(keys);
});
```

`mode: "union"` replaces the older `ComposableSelectionManager`: shift-drag a second brush in the same view, emit the merged key set under that source, and the model's intersect across other sources still works.

## Architecture Choice

### Direct Calls: 2 Views

Direct calls are acceptable for a simple overview/detail pair, but still pass `source` and stable keys.

### `d3.dispatch` or `SelectionModel`: 3-8 Views

Use `SelectionModel` above for selection/filter state. Use a bare `d3.dispatch("hover", "zoom")` for state that doesn't fit the keyed-selection contract (e.g. shared zoom transform). Namespace listeners (`change.scatter`) so teardown is explicit.

### Store: Complex State

Use a plain store when selection must coordinate with zoom transforms, sort order, URL state, undo/redo, or multiple interaction modes.

```js
function createStore(initial) {
  let state = { ...initial };
  const listeners = new Set();
  return {
    get: () => state,
    set(patch, source) {
      state = { ...state, ...patch, source };
      for (const fn of listeners) fn(state);
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}
```

## Rendering Rules

- Render the source chart first. Linked targets can update one frame later.
- Coalesce bursts of state changes with `requestAnimationFrame`.
- Avoid transitions during drag. Use short transitions on brush end or click selection.
- Reset must be global: Escape or clicking empty dashboard space clears every active filter.
- Preserve scale domains during continuous interaction; if auto-rescaling is useful, apply it on interaction end.

```js
let pending = false;
function scheduleRender(renderAll) {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {
    pending = false;
    renderAll();
  });
}
```

## Large Cross-Filters

For 100K+ rows, keep one bitmask per active filter and AND masks to compute the current selection. This belongs in the coordination layer because every view needs the same active set.

```js
function andMasks(masks, words) {
  const out = new Uint32Array(words);
  out.fill(0xffffffff);
  for (const mask of masks)
    for (let w = 0; w < words; w++) out[w] &= mask[w];
  return out;
}
```

If the dashboard needs SQL-backed aggregation, DuckDB-WASM, or server-side predicates, treat that as a large-data architecture decision rather than ordinary coordinated-view wiring.

## Common Pitfalls

1. **Index identity:** selected row 17 changes meaning after sorting or filtering. Coordinate by key.
2. **Feedback loops:** a chart responds to the event it emitted. Check `source`.
3. **Update storms:** three filters reset and trigger three redraws. Coalesce with RAF.
4. **No context layer:** selected marks appear alone, so the viewer loses the denominator. Use ghost + active layers.
5. **Rescale during drag:** moving targets destroy spatial memory. Keep domains fixed until interaction end.
6. **Too many simultaneous views:** beyond 3-4 active panels, coordination becomes noise unless the layout establishes a driver/detail hierarchy.
