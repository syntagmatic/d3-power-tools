---
name: linked-views
description: "Coordinate multiple D3.js visualizations that share state. Use this skill when the user wants linked charts, crossfilter-style filtering, coordinated brushing across views, overview+detail patterns, shared selection highlighting, master-detail layouts, synchronized zoom/pan, or any multi-view dashboard where interacting with one chart updates others. Covers event bus architecture, shared state management, coordinated brushing, zoom propagation, state serialization, and performance patterns for keeping linked views responsive."
---

# Linked Views

Patterns for coordinating multiple D3 visualizations that share state.

For brush mechanics and lasso selection, see `brushing`. For scale construction, see `scales`. For zoom API details, see `navigation`. For faceted layouts of the same chart type, see `small-multiples`. For data reshaping, see `data-gathering`. For parallel coordinates linking, see `parallel-coordinates`.

## Coordination Architecture

Three patterns for wiring charts together:

1. **Direct coupling** (2 charts) — wire chart A's output directly to chart B's input. No abstraction. Adding a third chart makes this unwieldy.
2. **Event bus with `d3.dispatch`** (3-8 charts) — named event channels. Charts emit events and subscribe independently. The standard choice for dashboards.
3. **Shared state store** (complex state, undo/redo) — a plain object holds full view state, mutations go through a single function that notifies subscribers.

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
      return () => listeners.delete(fn); // returns unsubscribe
    },
  };
}
```

## Selection Model

Multiple charts must agree on "the same datum." Never link by array index — sorting, filtering, or async loading breaks the mapping. Use a stable key.

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

Each chart translates its native interaction into the shared key-based model: scatter emits 2D brush keys, histogram emits bin keys, table emits toggle on row click, map emits region keys. Each chart skips events it originated via `source` check.

## Bitmap Index for 100K+ Rows (Crossfilter)

Precompute a bitmask per dimension. AND the masks for the intersection.

```js
class BitFilter {
  #n; #masks;
  constructor(n) { this.#n = n; this.#masks = new Map(); }

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

## Preventing Infinite Loops

Zoom/brush propagation is the most common source of infinite loops. Three strategies, from simplest to most robust:

1. **Check `event.sourceEvent`** — programmatic calls have `sourceEvent === null`. Sufficient for most cases.
2. **Boolean guard flag** — set `syncing = true` before propagating, skip if already syncing. Use when `sourceEvent` alone is insufficient.
3. **Compare transforms** — skip if `k`, `x`, `y` are unchanged. Additional safety net.

```js
let syncing = false;
.on("zoom", (event) => {
  if (!event.sourceEvent || syncing) return;
  syncing = true;
  propagateToOtherCharts(event.transform);
  syncing = false;
});
```

## Scale Domain Strategies

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

## State Serialization and Undo

Encode view state in the URL so users can share specific views. Serialize filter, selection (as comma-joined keys), and zoom transform (k,x,y). Push with `history.replaceState`.

For undo/redo, keep a state history stack. Snapshot on meaningful interactions (brush `end`, not during drag). Discard future states on new action (`stack.length = index`). Use `structuredClone` for snapshots.

## Performance

### Debouncing Brush Events

Brushes fire ~60x/sec during drag. Do cheap updates (opacity) immediately; debounce expensive updates (histogram recomputation) with `setTimeout(..., 16)`.

### requestAnimationFrame Coalescing

When multiple state changes fire in the same frame, batch into one render:

```js
let renderPending = false;
function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(() => { renderPending = false; renderAll(store.getState()); });
}
store.subscribe(scheduleRender);
```

### Canvas Two-Layer Highlight

Maintain background (all data, dim) and foreground (selected, vivid) canvas layers.

### Render Queue

When multiple charts need updating, render the chart the user is interacting with first, then queue others at lower priority via `requestAnimationFrame`. Source chart feels responsive; linked charts follow within 1-2 frames.

## Common Pitfalls

**Memory leaks from event listeners.** Destroyed charts still subscribed to the store keep receiving events. Store the unsubscribe function and call it on teardown.

**Stale closures.** A listener captures the initial scale in its closure. When scales update, the listener uses the old one. Read current state from the store, not from a closed-over variable.

**Brush visual not cleared on reset.** When another chart clears the selection, a brush remains visible. Programmatically clear with `brushGroup.call(brush.move, null)` in the reset handler.

**Tooltip fights.** Multiple charts showing tooltips simultaneously is noisy. Use a single shared tooltip element positioned by whichever chart the pointer is over.

**Transitions during continuous interaction.** Long transitions (300ms) on linked views feel sluggish during brush drag. Skip transitions during `brush` events; animate only on `end`.

## References

- [Crossfilter](https://square.github.io/crossfilter/) — fast multidimensional filter library
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — pioneering multi-axis linked brushing
- [Linking Views](https://www.cs.ubc.ca/~tmm/vadbook/ch13-linkedviews.pdf) — Tamara Munzner's Visualization Analysis & Design, Chapter 13
- [Dynamic Queries](https://www.cs.umd.edu/~ben/papers/Shneiderman1994Dynamic.pdf) — Shneiderman's direct manipulation filtering (CHI 1994)
