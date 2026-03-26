---
name: linked-views
description: "Coordinate multiple D3.js visualizations that share state. Use this skill when the user wants linked charts, crossfilter-style filtering, coordinated brushing across views, overview+detail patterns, shared selection highlighting, master-detail layouts, synchronized zoom/pan, or any multi-view dashboard where interacting with one chart updates others. Covers event bus architecture, shared state management, coordinated brushing, zoom propagation, state serialization, and performance patterns for keeping linked views responsive."
---

# Linked Views

A single chart shows one question. Linked views let the viewer ask a question in one chart and see the answer ripple across others — brushing a time range in a line chart instantly filters a scatter plot, a histogram, and a map. The power is combinatorial: N views give N simultaneous angles on the same data without N separate mental models, but only if the coordination is fast enough to feel like a single instrument.

For brush mechanics and lasso selection, see `brushing`. For scale construction, see `axes-and-scales`. For zoom API details, see `navigation`. For faceted layouts of the same chart type, see `small-multiples`. For data reshaping, see `data-gathering`. For parallel coordinates linking, see `parallel-coordinates`.

## When Not to Link

Linking views has a real cost: every added view splits attention and forces context-switching. Research on coordinated multiple views (Baldonado et al., "Guidelines for Using Multiple Views in Information Visualization") identifies key traps:

- **More than 3-4 linked views demands strong spatial grouping.** Working memory holds ~4 chunks. Beyond that, viewers forget which chart they brushed and lose the thread. If you need 6+ views, group them into 2-3 clusters with clear visual hierarchy — an overview panel and detail panels — so the viewer always knows where to look.
- **Linking unrelated dimensions confuses more than it reveals.** If brushing price range highlights points on a map with no spatial pattern, the link teaches nothing — it just makes things blink. Every link should answer: "what does this selection look like from that angle?" If the answer is "random noise," drop the link.
- **Linking everything to everything creates update storms.** Chart A brushes, which updates chart B, which fires a filter change, which updates chart A. The viewer sees a flicker and has no idea what happened. Be explicit about which interactions propagate and which are local-only.
- **Small multiples often beat linked views.** When comparing the same measure across categories, small multiples (one chart per category, shared scale) impose lower cognitive load than a linked scatter + bar + table. Use linked views when the dimensions are heterogeneous — spatial + temporal + categorical — not when they're facets of the same thing.

## Coordination Architecture

Three patterns, chosen by how many charts need wiring:

1. **Direct coupling** (2 charts) — wire chart A's output directly to chart B's input. No abstraction needed. Adding a third chart makes this O(n^2) in wiring complexity.
2. **Event bus with `d3.dispatch`** (3-8 charts) — named event channels. Charts emit events and subscribe independently. The standard choice because adding a chart means adding one subscriber, not rewiring everything.
3. **Shared state store** (complex state, undo/redo) — a plain object holds full view state, mutations go through a single function that notifies subscribers. Use when you need time-travel debugging or URL-serialized state.

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

Multiple charts must agree on "the same datum." Never link by array index — sorting, filtering, or async loading breaks the mapping. Use a stable key (an ID column, a composite key).

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
  // Empty selection = everything selected — avoids the "blank dashboard" trap
  // where clearing a brush makes all charts go empty
  isSelected(key) { return this.#keys.size === 0 || this.#keys.has(key); }
  get size() { return this.#keys.size; }
  get keys() { return this.#keys; }
  on(event, fn) { this.#dispatch.on(event, fn); return this; }
}
```

Each chart translates its native interaction into the shared key-based model: scatter emits 2D brush keys, histogram emits bin keys, table emits toggle on row click, map emits region keys. Each chart skips events it originated via `source` check — this is the primary defense against feedback loops.

## Bitmap Index for 100K+ Rows (Crossfilter Pattern)

The original crossfilter library used sorted indexes with incremental filtering. For multi-dimension AND queries — "show me rows where price is in [10,50] AND date is in March AND region is West" — a bitmap approach is simpler to implement and often faster. Each dimension gets a bitmask where bit `i` is 1 if row `i` passes that dimension's filter. AND all masks together to get the intersection. Bit operations on typed arrays are cache-friendly and branch-free, so filtering 500K rows across 5 dimensions takes under 2ms.

Why bitmaps beat naive iteration: iterating 500K rows per dimension per frame is O(N * D). Bitmaps reduce this to O(N/32 * D) word-level AND operations — a 32x constant-factor improvement, and the tight loop plays well with CPU cache prefetching.

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

  // AND all dimension masks — rows passing every active filter
  filtered() {
    const words = Math.ceil(this.#n / 32);
    const result = new Uint32Array(words).fill(0xFFFFFFFF);
    for (const mask of this.#masks.values()) {
      for (let w = 0; w < words; w++) result[w] &= mask[w];
    }
    // Extract set bit indices using bit-twiddling
    const indices = [];
    for (let w = 0; w < words; w++) {
      let bits = result[w];
      while (bits) {
        const bit = bits & -bits;          // isolate lowest set bit
        indices.push((w << 5) + Math.log2(bit));
        bits ^= bit;                       // clear it
      }
    }
    return indices;
  }

  // For histograms: count passing rows per bin without extracting indices.
  // Much faster when you need aggregates, not individual rows.
  count() {
    const words = Math.ceil(this.#n / 32);
    let total = 0;
    const result = new Uint32Array(words).fill(0xFFFFFFFF);
    for (const mask of this.#masks.values()) {
      for (let w = 0; w < words; w++) result[w] &= mask[w];
    }
    for (let w = 0; w < words; w++) {
      // popcount via bit manipulation
      let v = result[w];
      v = v - ((v >> 1) & 0x55555555);
      v = (v & 0x33333333) + ((v >> 2) & 0x33333333);
      total += (((v + (v >> 4)) & 0x0F0F0F0F) * 0x01010101) >> 24;
    }
    return total;
  }
}
```

**Incremental updates:** When the user drags a brush, only one dimension changes. Recompute only that dimension's mask, then re-AND. The other masks are already cached in the `Map`. This is what makes crossfilter feel instant during brush drag.

**When to skip bitmaps:** Below ~5K rows, plain `Array.filter` with a Set lookup is fast enough and far simpler to debug. The bitmap overhead (allocation, bit extraction) only pays off when N is large enough that the 32x speedup matters.

## Feedback Loops and Update Storms

Zoom/brush propagation is the most common source of infinite loops. Three strategies, from simplest to most robust:

1. **Check `event.sourceEvent`** — programmatic calls (like `selection.call(zoom.transform, t)`) have `sourceEvent === null`. Skip those. Sufficient for most two-chart cases.
2. **Boolean guard flag** — set `syncing = true` before propagating, skip if already syncing. Use when multiple charts chain-react and `sourceEvent` alone is insufficient.
3. **Compare transforms** — skip if `k`, `x`, `y` are unchanged. Additional safety net for floating-point edge cases.

```js
let syncing = false;
.on("zoom", (event) => {
  if (!event.sourceEvent || syncing) return;
  syncing = true;
  propagateToOtherCharts(event.transform);
  syncing = false;
});
```

**Update storms** happen when multiple dimensions fire filter changes simultaneously (e.g., resetting all brushes). Each change triggers a full re-render of all views. The fix is `requestAnimationFrame` coalescing — batch all state changes into one render pass per frame (see Performance below).

## Scale Domain Strategies

**Fixed domain (stable):** Compute once from the full dataset, never change. Prevents jarring scale jumps during brushing — the viewer's spatial memory of "high values are at the top" stays valid.

**Auto-rescale (responsive):** Recompute domain when filter changes. Reveals local structure but destroys spatial consistency. Only rescale on brush *end*, not during drag — rescaling 60x/sec during a drag makes the chart feel like it's fighting the user:

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

Brushes fire ~60x/sec during drag. Do cheap updates (opacity toggle, canvas foreground/background swap) immediately; debounce expensive updates (histogram recomputation, aggregation) with `setTimeout(..., 16)` or, better, fold them into the RAF coalescing pattern below.

### requestAnimationFrame Coalescing

When multiple state changes fire in the same frame (e.g., resetting three brushes at once), batch into one render. Without this, you get three full re-renders in one frame — the update storm problem.

```js
let renderPending = false;
function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(() => { renderPending = false; renderAll(store.getState()); });
}
store.subscribe(scheduleRender);
```

### Ghost/Active Pattern

Show filtered subsets against the full dataset using two layers: a static ghost (all data, dimmed) and a dynamic foreground (filtered subset, vivid). This works for three view types:

**Discrete bins (histograms, bars):** Background bars show total counts in gray. Foreground bars show filtered counts with accent color. Same bin thresholds, same y-scale — only the heights change. See `blocks/05-crossfilter-flight-explorer.html`.

**Continuous densities (KDE, violins, area charts):** Background paths show full-data density in gray. Foreground paths recompute KDE from the filtered subset. **Critical pitfall:** KDE on a small subset with the same bandwidth produces artificially tall peaks — 5 points selected from 200 can spike 10x higher than the full dataset. Fix: scale the density by `subset.length / fullGroup.length` so visual height represents proportion, not raw density. Without this, selecting a few points sends the curve shooting outside the chart bounds.

```js
const density = kde(gaussian, bandwidth, subsetValues)(ticks);
const scale = subset.length / fullGroup.length;
const scaled = density.map(([x, y]) => [x, y * scale]);
foregroundPath.datum(scaled).attr("d", area);
```

**Canvas scatter:** Maintain background (all data, dimmed) and foreground (selected, vivid) canvas layers. On brush, only repaint the foreground. The background stays static. This cuts render cost roughly in half.

### Render Queue

When multiple charts need updating, render the chart the user is interacting with first, then queue others at lower priority via `requestAnimationFrame`. The source chart responds instantly; linked charts follow within 1-2 frames. The viewer perceives the system as responsive because the chart under their hand never lags.

## Common Pitfalls

**Memory leaks from event listeners.** Destroyed charts still subscribed to the store keep receiving events, causing errors or phantom renders. Store the unsubscribe function returned by `subscribe()` and call it on teardown.

**Stale closures.** A listener captures the initial scale in its closure. When scales update, the listener uses the old one. Read current state from the store at render time, not from a closed-over variable.

**Brush visual not cleared on reset.** When another chart clears the selection, a brush overlay remains visible in the originating chart. Programmatically clear with `brushGroup.call(brush.move, null)` in the reset handler.

**Tooltip fights.** Multiple charts showing tooltips simultaneously is noisy and distracting. Use a single shared tooltip element positioned by whichever chart the pointer is currently over.

**Transitions during continuous interaction.** A 300ms transition on a linked histogram feels fine on brush *end* but makes the chart feel sluggish during brush *drag*. Skip transitions during continuous events; animate only on `end`.

**Linking charts with incompatible data granularity.** A scatter plot shows individual rows; a bar chart shows category aggregates. Brushing the bar chart selects a category, but the scatter plot needs row keys. The selection model must translate between granularities — typically by expanding a category selection into its constituent row keys.

## References

- [Crossfilter](https://square.github.io/crossfilter/) — fast multidimensional filter library; study its sorted-index approach alongside the bitmap alternative above
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — pioneering multi-axis linked brushing
- [Linking Views](https://www.cs.ubc.ca/~tmm/vadbook/ch13-linkedviews.pdf) — Tamara Munzner's Visualization Analysis & Design, Chapter 13
- [Dynamic Queries](https://www.cs.umd.edu/~ben/papers/Shneiderman1994Dynamic.pdf) — Shneiderman's direct manipulation filtering (CHI 1994)
- [Guidelines for Using Multiple Views](https://www.cs.ubc.ca/~tmm/courses/old533/readings/baldonado.pdf) — Baldonado, Woodruff & Kuchinsky (2000); the "diversity" and "parsimony" guidelines for when linking helps vs. hurts
