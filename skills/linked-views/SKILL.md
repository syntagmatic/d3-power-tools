---
name: linked-views
description: "Coordinate multiple D3.js visualizations that share state. Use this skill when the user wants linked charts, crossfilter-style filtering, coordinated brushing across views, overview+detail patterns, shared selection highlighting, master-detail layouts, synchronized zoom/pan, or any multi-view dashboard where interacting with one chart updates others. Covers event bus architecture, shared state management, coordinated brushing, zoom propagation, state serialization, and performance patterns for keeping linked views responsive."
---

# Linked Views

Patterns for coordinating multiple D3 visualizations that share state. Covers coordination architecture, shared selection, crossfilter-style filtering, coordinated brushing and zoom, overview+detail, focus+context, shared scales, heterogeneous chart linking, state serialization, and performance.

For brush mechanics and lasso selection, see `brushing-and-selection`. For scale construction, see `axes-and-scales`. For zoom API details, see `zoom-and-pan`. For faceted layouts of the same chart type, see `small-multiples`. For data reshaping, see `data-preparation`. For parallel coordinates linking, see `parallel-coordinates`.

## Coordination Architecture

Three patterns for wiring charts together. Choose based on chart count and complexity.

### Direct Coupling — 2 charts, simple

Wire chart A's output directly to chart B's input. No abstraction layer.

```js
const scatter = createScatter(data, {
  onBrush(extent) { histogram.filter(extent); }
});
const histogram = createHistogram(data, {
  onBarClick(range) { scatter.highlight(range); }
});
```

**When to use:** Exactly two charts with simple bidirectional linking. Adding a third chart makes this unwieldy.

### Event Bus with d3.dispatch — 3-8 charts, decoupled

`d3.dispatch` provides named event channels. Charts emit events and subscribe independently — no chart knows about any other.

```js
const dispatch = d3.dispatch("filter", "highlight", "zoom", "reset");

// Scatter emits filter events
scatter.onBrush = (extent) => dispatch.call("filter", null, {
  source: "scatter", extent
});

// Histogram and table listen — the .namespace suffix lets each register independently
dispatch.on("filter.histogram", ({ source, extent }) => {
  if (source === "histogram") return; // skip own events
  histogram.filter(extent);
});
dispatch.on("filter.table", ({ source, extent }) => {
  if (source === "table") return;
  table.filter(extent);
});
```

**When to use:** Multiple charts that need loose coupling. The standard choice for dashboards.

### Shared State Store — complex state, undo/redo

A plain object holds the full view state. Mutations go through a single function that notifies subscribers — a minimal Redux-like pattern without a framework.

```js
function createStore(initialState) {
  let state = { ...initialState };
  const listeners = new Set();
  return {
    getState: () => state,
    setState(updates) {
      const prev = state;
      state = { ...state, ...updates };
      for (const fn of listeners) fn(state, prev);
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn); // returns unsubscribe function
    },
  };
}

const store = createStore({
  filter: null, selected: new Set(),
  zoomTransform: d3.zoomIdentity, timeRange: null,
});

// Each chart subscribes and re-renders on relevant state changes
store.subscribe((state, prev) => {
  if (state.filter !== prev.filter) histogram.update(state.filter);
  if (state.selected !== prev.selected) scatter.highlight(state.selected);
});
```

**When to use:** Complex dashboards with many interacting state dimensions, or when you need undo/redo (keep a state history stack).

## Shared Selection State

Multiple charts must agree on "the same datum." This requires a stable identity key and a shared selection model.

### Data Identity

Never link by array index — sorting, filtering, or async loading breaks the mapping. Use a stable key.

```js
const keyFn = d => d.id;                    // unique ID field
const keyFn = d => `${d.name}-${d.date}`;   // composite key
// Bad: (d, i) => i — breaks on sort/filter
```

### Selection Model

```js
class SelectionModel {
  #keys = new Set();
  #dispatch = d3.dispatch("change");

  select(keys, source) {
    this.#keys = new Set(keys);
    this.#dispatch.call("change", null, { keys: this.#keys, source });
  }

  toggle(key, source) {
    this.#keys.has(key) ? this.#keys.delete(key) : this.#keys.add(key);
    this.#dispatch.call("change", null, { keys: new Set(this.#keys), source });
  }

  clear(source) {
    this.#keys.clear();
    this.#dispatch.call("change", null, { keys: this.#keys, source });
  }

  // Empty selection = everything selected (avoids blank state)
  isSelected(key) { return this.#keys.size === 0 || this.#keys.has(key); }
  get size() { return this.#keys.size; }
  get keys() { return this.#keys; }
  on(event, fn) { this.#dispatch.on(event, fn); return this; }
}
```

### Connecting Charts

```js
const selection = new SelectionModel();

selection.on("change.scatter", ({ keys, source }) => {
  if (source === "scatter") return;
  scatterPoints.attr("opacity", d => selection.isSelected(keyFn(d)) ? 0.9 : 0.08);
});

selection.on("change.table", ({ keys, source }) => {
  if (source === "table") return;
  tableRows.classed("selected", d => selection.isSelected(keyFn(d)));
});

selection.on("change.histogram", ({ keys, source }) => {
  if (source === "histogram") return;
  const filtered = keys.size === 0 ? data : data.filter(d => keys.has(keyFn(d)));
  histogram.update(filtered);
});
```

## Crossfilter Pattern

Interactive filtering across multiple dimensions. Brush one dimension and all views update.

### Lightweight Crossfilter with d3.group

For moderate datasets (under 50K rows), D3's built-in grouping is sufficient:

```js
const filters = new Map(); // dimension name -> filter predicate

function setFilter(dim, predicate) {
  if (predicate) filters.set(dim, predicate);
  else filters.delete(dim);
  updateAll();
}

function getFiltered() {
  return data.filter(d => [...filters.values()].every(fn => fn(d)));
}

function updateAll() {
  const filtered = getFiltered();
  scatter.update(filtered);
  histogram.update(filtered);
  table.update(filtered);
}

// Brush on income axis
setFilter("income", d => d.income >= 40000 && d.income <= 80000);
setFilter("income", null); // clear
```

### Bitmap Index for 100K+ Rows

Precompute a bitmask per dimension. AND the masks for the intersection.

```js
class BitFilter {
  #n; #masks;

  constructor(n) {
    this.#n = n;
    this.#masks = new Map();
  }

  set(dim, predicate, data) {
    const words = Math.ceil(this.#n / 32);
    const mask = new Uint32Array(words);
    for (let i = 0; i < this.#n; i++) {
      if (predicate(data[i])) mask[i >> 5] |= 1 << (i & 31);
    }
    this.#masks.set(dim, mask);
  }

  clear(dim) { this.#masks.delete(dim); }

  filtered() {
    const words = Math.ceil(this.#n / 32);
    const result = new Uint32Array(words).fill(0xFFFFFFFF);
    for (const mask of this.#masks.values()) {
      for (let w = 0; w < words; w++) result[w] &= mask[w];
    }
    const indices = [];
    for (let w = 0; w < words; w++) {
      let bits = result[w];
      while (bits) {
        const bit = bits & -bits;
        indices.push((w << 5) + Math.log2(bit));
        bits ^= bit;
      }
    }
    return indices;
  }
}
```

Bit operations on typed arrays are extremely fast — filtering 500K rows across 5 dimensions takes under 2ms.

## Coordinated Brushing

Brush in one chart, other charts highlight or filter accordingly.

### Scatter + Histogram + Table

```js
const dispatch = d3.dispatch("filter", "reset");

const brush = d3.brush()
  .extent([[0, 0], [scatterWidth, scatterHeight]])
  .on("brush end", (event) => {
    if (!event.sourceEvent) return;
    if (!event.selection) { dispatch.call("reset"); return; }
    const [[x0, y0], [x1, y1]] = event.selection;
    const keys = new Set(
      data.filter(d => xScale(d.x) >= x0 && xScale(d.x) <= x1 &&
                       yScale(d.y) >= y0 && yScale(d.y) <= y1)
          .map(keyFn)
    );
    dispatch.call("filter", null, { source: "scatter", keys });
  });

dispatch.on("filter.histogram", ({ keys }) => {
  const filtered = keys.size === 0 ? data : data.filter(d => keys.has(keyFn(d)));
  const bins = d3.bin().domain(xHistScale.domain()).thresholds(20)(filtered.map(d => d.value));
  histBars.data(bins)
    .attr("y", d => yHistScale(d.length))
    .attr("height", d => histHeight - yHistScale(d.length));
});

dispatch.on("filter.table", ({ keys }) => {
  tableRows.style("display", d => keys.size === 0 || keys.has(keyFn(d)) ? null : "none");
});

dispatch.on("reset", () => {
  scatterSvg.select(".brush").call(brush.move, null);
  tableRows.style("display", null);
});
```

### Bidirectional: Any Chart Drives All Others

The key rule: charts skip events they originated. For bidirectional brushing, a chart receiving an external filter can programmatically set its brush to match:

```js
dispatch.on("filter.scatter", ({ source, keys }) => {
  if (source === "scatter") return;
  if (keys.size === 0) {
    scatterSvg.select(".brush").call(brush.move, null);
  } else {
    const sel = data.filter(d => keys.has(keyFn(d)));
    scatterSvg.select(".brush").call(brush.move, [
      [d3.min(sel, d => xScale(d.x)) - 5, d3.min(sel, d => yScale(d.y)) - 5],
      [d3.max(sel, d => xScale(d.x)) + 5, d3.max(sel, d => yScale(d.y)) + 5],
    ]);
  }
});
```

## Coordinated Zoom and Pan

Linked zoom keeps charts sharing an axis in sync — e.g., two time-series with the same x-axis.

### Transform Propagation

```js
const zoom = d3.zoom()
  .scaleExtent([1, 50])
  .on("zoom", (event) => {
    if (!event.sourceEvent) return; // skip programmatic calls — prevents loops
    store.setState({ zoomTransform: event.transform });
  });

store.subscribe((state, prev) => {
  if (state.zoomTransform === prev.zoomTransform) return;
  const t = state.zoomTransform;
  const newX = t.rescaleX(xScale);

  charts.forEach(chart => {
    chart.svg.call(zoom.transform, t);
    chart.xAxisG.call(d3.axisBottom(newX));
    chart.redraw(newX);
  });
});
```

### Preventing Infinite Loops

Zoom propagation is the most common source of infinite loops. Three strategies, from simplest to most robust:

1. **Check `event.sourceEvent`** — programmatic zoom calls have `sourceEvent === null`. This is the standard approach and sufficient for most cases.
2. **Boolean guard flag** — set `syncing = true` before propagating, skip if already syncing. Use when you have chains of updates where `sourceEvent` alone is insufficient.
3. **Compare transforms** — skip if `k`, `x`, `y` are unchanged. Useful as an additional safety net.

```js
// Combine strategies 1 + 2 for robust loop prevention
let syncing = false;
.on("zoom", (event) => {
  if (!event.sourceEvent || syncing) return;
  syncing = true;
  propagateToOtherCharts(event.transform);
  syncing = false;
});
```

## Overview + Detail

A small overview chart with a brush controls a larger detail view. The classic pattern for navigating long time series.

```js
const overviewX = d3.scaleTime().domain(d3.extent(data, d => d.date)).range([0, width]);
const detailX = d3.scaleTime().domain(overviewX.domain()).range([0, width]);
const detailY = d3.scaleLinear().range([detailHeight, 0]);

const overviewBrush = d3.brushX()
  .extent([[0, 0], [width, overviewHeight]])
  .on("brush end", (event) => {
    if (!event.sourceEvent) return;
    const sel = event.selection || overviewX.range();
    const [d0, d1] = sel.map(overviewX.invert);
    detailX.domain([d0, d1]);

    const visible = data.filter(d => d.date >= d0 && d.date <= d1);
    detailY.domain([0, d3.max(visible, d => d.value)]).nice();

    detailLine.attr("d", line.x(d => detailX(d.date)).y(d => detailY(d.value)));
    detailXAxis.call(d3.axisBottom(detailX));
    detailYAxis.transition().duration(80).call(d3.axisLeft(detailY));
  });

overviewG.append("g").call(overviewBrush)
  .call(overviewBrush.move, overviewX.range()); // start fully selected
```

### Minimap for Spatial Data

Same pattern in 2D. A small version of the map shows the current viewport as a draggable rectangle:

```js
const minimapScale = 0.15;
const viewRect = minimapSvg.append("rect")
  .attr("fill", "none").attr("stroke", "steelblue").attr("stroke-width", 2);

// Update minimap viewport when main view zooms
store.subscribe((state) => {
  const t = state.zoomTransform;
  viewRect
    .attr("x", -t.x / t.k * minimapScale)
    .attr("y", -t.y / t.k * minimapScale)
    .attr("width", width / t.k * minimapScale)
    .attr("height", height / t.k * minimapScale);
});

// Drag minimap viewport to pan main view
minimapSvg.call(d3.drag().on("drag", (event) => {
  const t = store.getState().zoomTransform;
  const newT = t.translate(-event.dx / minimapScale, -event.dy / minimapScale);
  store.setState({ zoomTransform: newT });
}));
```

## Focus + Context

One chart shows the full dataset; user interaction drives a detail panel.

### Master-Detail with Animated Transitions

```js
store.subscribe((state, prev) => {
  if (state.focusedItem === prev.focusedItem) return;
  const item = state.focusedItem;
  const detail = detailData.get(item);

  detailBars.data(detail, d => d.metric)
    .join(
      enter => enter.append("rect")
        .attr("x", 0).attr("y", d => detailY(d.metric))
        .attr("width", 0).attr("height", detailY.bandwidth())
        .call(e => e.transition().duration(300).attr("width", d => detailX(d.value))),
      update => update.transition().duration(300).attr("width", d => detailX(d.value)),
      exit => exit.transition().duration(150).attr("width", 0).remove()
    );

  masterBars
    .attr("opacity", d => d.key === item ? 1 : 0.4)
    .attr("stroke", d => d.key === item ? "#333" : "none");
});
```

For exploratory views, use hover to preview and click to pin:

```js
masterBars
  .on("pointerenter", (event, d) => updateDetail(d.key))
  .on("pointerleave", () => {
    const pinned = store.getState().focusedItem;
    if (pinned) updateDetail(pinned);
  })
  .on("click", (event, d) => store.setState({ focusedItem: d.key }));
```

## Shared Scales

When multiple charts should map the same data values to the same visual encoding.

### Shared Color Scale

```js
const categories = [...new Set(data.map(d => d.category))].sort();
const color = d3.scaleOrdinal().domain(categories).range(d3.schemeTableau10);
// Pass to every chart
createScatter(data, { color });
createHistogram(data, { color });
```

### Dynamic Domain Updates

**Fixed domain (stable):** Compute once from the full dataset, never change. Prevents jarring scale jumps during brushing.

**Auto-rescale (responsive):** Recompute domain when filter changes. Only rescale on brush *end*, not during drag:

```js
brush.on("brush", () => { /* use fixed domain during drag */ });
brush.on("end", () => {
  const filtered = getFiltered();
  yScale.domain([0, d3.max(filtered, d => d.value)]).nice();
  yAxisG.transition().duration(300).call(d3.axisLeft(yScale));
});
```

## Linking Heterogeneous Chart Types

Scatter, histogram, table, and map can all link despite different interaction semantics. Each chart translates its native interaction into the shared key-based selection model:

```js
const selection = new SelectionModel();

// Scatter: 2D brush → keys
scatterBrush.on("brush end", (event) => {
  if (!event.sourceEvent) return;
  if (!event.selection) { selection.clear("scatter"); return; }
  const [[x0, y0], [x1, y1]] = event.selection;
  const keys = data
    .filter(d => xS(d.x) >= x0 && xS(d.x) <= x1 && yS(d.y) >= y0 && yS(d.y) <= y1)
    .map(keyFn);
  selection.select(keys, "scatter");
});

// Histogram: bar click → keys in that bin
histBars.on("click", (event, bin) => selection.select(bin.map(keyFn), "histogram"));

// Table: row click → toggle one key
tableRows.on("click", (event, d) => selection.toggle(keyFn(d), "table"));

// Map: region click → all keys in that region
mapRegions.on("click", (event, feature) => {
  selection.select(data.filter(d => d.region === feature.properties.name).map(keyFn), "map");
});
```

Each chart responds to selection changes in its own way: scatter dims unselected points, histogram overlays selected distribution, table sorts selected rows to top, map highlights selected regions.

## State Serialization

Encode view state in the URL so users can share specific views.

### URL-Encodable State

```js
function stateToURL(state) {
  const params = new URLSearchParams();
  if (state.filter) params.set("f", `${state.filter.field}:${state.filter.min}:${state.filter.max}`);
  if (state.selected.size > 0) params.set("sel", [...state.selected].join(","));
  if (state.zoomTransform !== d3.zoomIdentity) {
    const t = state.zoomTransform;
    params.set("z", `${t.k.toFixed(2)},${t.x.toFixed(0)},${t.y.toFixed(0)}`);
  }
  return params.toString();
}

function urlToState(search) {
  const params = new URLSearchParams(search);
  const state = { filter: null, selected: new Set(), zoomTransform: d3.zoomIdentity };
  const f = params.get("f");
  if (f) {
    const [field, min, max] = f.split(":");
    state.filter = { field, min: +min, max: +max };
  }
  const sel = params.get("sel");
  if (sel) state.selected = new Set(sel.split(","));
  const z = params.get("z");
  if (z) {
    const [k, x, y] = z.split(",").map(Number);
    state.zoomTransform = d3.zoomIdentity.translate(x, y).scale(k);
  }
  return state;
}

// Push state on change
store.subscribe((state) => {
  history.replaceState(null, "", `${location.pathname}?${stateToURL(state)}`);
});
```

### Undo/Redo with State Snapshots

```js
class StateHistory {
  #stack = []; #index = -1; #store;
  constructor(store) { this.#store = store; }

  push(state) {
    this.#index++;
    this.#stack.length = this.#index; // discard future states
    this.#stack.push(structuredClone(state));
  }
  undo() {
    if (this.#index <= 0) return;
    this.#store.setState(this.#stack[--this.#index]);
  }
  redo() {
    if (this.#index >= this.#stack.length - 1) return;
    this.#store.setState(this.#stack[++this.#index]);
  }
}

// Snapshot on meaningful interactions, not during drag
brush.on("end", () => stateHistory.push(store.getState()));
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "z") { e.preventDefault(); stateHistory.undo(); }
  if (e.ctrlKey && e.key === "y") { e.preventDefault(); stateHistory.redo(); }
});
```

## Interaction Recipes

### Map + Bar Chart

```js
const dispatch = d3.dispatch("selectRegion");

mapRegions.on("click", (event, feature) => {
  dispatch.call("selectRegion", null, feature.properties.name);
});

dispatch.on("selectRegion.bars", (region) => {
  const regionData = data.filter(d => d.region === region);
  const grouped = d3.rollup(regionData, v => d3.sum(v, d => d.value), d => d.category);
  const barData = Array.from(grouped, ([key, value]) => ({ key, value }));
  barX.domain(barData.map(d => d.key));
  barY.domain([0, d3.max(barData, d => d.value)]).nice();
  bars.data(barData, d => d.key).join("rect")
    .transition().duration(300)
    .attr("x", d => barX(d.key)).attr("y", d => barY(d.value))
    .attr("width", barX.bandwidth()).attr("height", d => barHeight - barY(d.value));
});

dispatch.on("selectRegion.map", (region) => {
  mapRegions.attr("fill", d =>
    d.properties.name === region ? "#e15759" : color(d.properties.value));
});
```

### Time-Series + Event Timeline

```js
const timelineBrush = d3.brushX()
  .extent([[0, 0], [width, timelineHeight]])
  .on("brush end", (event) => {
    if (!event.sourceEvent) return;
    if (!event.selection) { store.setState({ timeRange: null }); return; }
    store.setState({ timeRange: event.selection.map(timeX.invert) });
  });

store.subscribe((state) => {
  const [t0, t1] = state.timeRange || timeX.domain();
  eventMarkers.attr("display", d => d.date >= t0 && d.date <= t1 ? null : "none");
  detailX.domain([t0, t1]);
  detailXAxis.call(d3.axisBottom(detailX));
  detailLine.attr("d", line.x(d => detailX(d.date)));
});
```

### Parallel Coordinates + Scatter Matrix

```js
parcoords.on("brush", (selectedKeys) => selection.select(selectedKeys, "parcoords"));

selection.on("change.scatterMatrix", ({ keys, source }) => {
  if (source === "scatterMatrix") return;
  scatterCells.selectAll("circle")
    .attr("fill", d => selection.isSelected(keyFn(d)) ? color(d.category) : "#ddd")
    .attr("opacity", d => selection.isSelected(keyFn(d)) ? 0.8 : 0.15);
});
```

## Performance

### Debouncing Brush Events

Brushes fire ~60x/sec during drag. For expensive linked views, debounce or throttle:

```js
let brushTimer;
brush.on("brush", (event) => {
  if (!event.sourceEvent) return;
  // Cheap updates: do immediately
  scatterPoints.attr("opacity", d => inBrush(d) ? 0.9 : 0.08);
  // Expensive updates: debounce
  clearTimeout(brushTimer);
  brushTimer = setTimeout(() => histogram.update(computeFiltered(event.selection)), 16);
});
```

### requestAnimationFrame Coalescing

When multiple state changes fire in the same frame, batch into one render:

```js
let renderPending = false;
function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(() => {
    renderPending = false;
    renderAll(store.getState());
  });
}
store.subscribe(scheduleRender);
```

### Canvas Two-Layer Highlight

For Canvas views, maintain background (all data, dim) and foreground (selected, vivid) layers:

```js
function highlightCanvas(fgCtx, bgCtx, data, selectedKeys, drawFn) {
  bgCtx.clearRect(0, 0, width, height);
  bgCtx.globalAlpha = 0.05;
  for (const d of data) drawFn(bgCtx, d);

  fgCtx.clearRect(0, 0, width, height);
  fgCtx.globalAlpha = 0.8;
  for (const d of data) {
    if (selectedKeys.has(keyFn(d))) drawFn(fgCtx, d);
  }
}
```

### Render Queue — Prioritize the Active Chart

When multiple charts need updating, render the chart the user is interacting with first, then queue others at lower priority via `requestAnimationFrame`. This ensures the source chart feels responsive while linked charts follow within 1-2 frames.

## Common Pitfalls

**Infinite event loops.** Chart A updates state, chart B re-renders and triggers its own update, which re-triggers chart A. Fix: every event carries a `source` identifier; charts skip events they originated. For zoom, also check `event.sourceEvent` — programmatic transforms have `sourceEvent === null`.

**Scale domain drift.** Auto-rescaling the y-axis on every brush update causes jarring jumps. Fix: use a fixed domain during active brushing, rescale with a transition only on brush end.

**Identity confusion.** Linking by array index breaks on sort/filter. Fix: always use a stable key field and pass sets of keys between charts, never indices.

**Memory leaks from event listeners.** Destroyed charts still subscribed to the store keep receiving events. Fix: store the unsubscribe function and call it on teardown:

```js
const unsub = store.subscribe(updateChart);
// On destroy:
unsub();
chartSvg.remove();
```

**Stale closures.** A listener captures the initial scale in its closure. When scales update, the listener uses the old one. Fix: read current state from the store, not from a closed-over variable.

**Brush visual not cleared on reset.** When another chart clears the selection, a brush remains visible. Fix: programmatically clear with `brushGroup.call(brush.move, null)` in the reset handler.

**Tooltip fights.** Multiple charts showing tooltips simultaneously is noisy. Fix: use a single shared tooltip element positioned by whichever chart the pointer is over.

**Transitions during continuous interaction.** Long transitions (300ms) on linked views feel sluggish during brush drag. Fix: skip transitions during `brush` events; animate only on `end`.

## References

- [Crossfilter](https://square.github.io/crossfilter/) — fast multidimensional filter library
- [D3 Dispatch](https://d3js.org/d3-dispatch) — named event channels for decoupled communication
- [D3 Brush](https://d3js.org/d3-brush) — rectangular selection for driving linked views
- [D3 Zoom](https://d3js.org/d3-zoom) — transform propagation for coordinated zoom
- [Focus + Context via Brushing](https://observablehq.com/@d3/focus-context) — canonical overview+detail pattern
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — pioneering multi-axis linked brushing
- [Linking Views](https://www.cs.ubc.ca/~tmm/vadbook/ch13-linkedviews.pdf) — Tamara Munzner's Visualization Analysis & Design, Chapter 13
- [Dynamic Queries](https://www.cs.umd.edu/~ben/papers/Shneiderman1994Dynamic.pdf) — Shneiderman's direct manipulation filtering (CHI 1994)
