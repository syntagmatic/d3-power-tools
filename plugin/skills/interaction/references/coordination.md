# Coordination: wiring views together

Absorbed from the v2 `coordination` skill plus the cross-chart linking sections of `brushing`. Open when writing the code that carries a selection, hover, filter, or zoom from one chart to others.

## Architecture by size

| Situation | Wiring | Why |
|---|---|---|
| 2 views, one direction | direct call (`detail.setDomain(d)`) | anything more is ceremony |
| 3-8 views, events | `d3.dispatch` with a namespace per listener (`"brush.scatter"`) | O(n) fan-out; namespaces let each view register and tear down without clobbering others |
| deep state (filter + zoom + sort), undo, URL sync | one store: `setState` → notify subscribers | single source of truth; render reads state, never event payloads |
| "which rows are selected" across views | keyed selection model (below) | every view agrees on identity; array indices break the moment one view sorts or filters |
| 100K+ rows cross-filtering | bitmap masks | 32 rows per bitwise op |

`dispatch.on("brush", fn)` without a namespace *replaces* the previous "brush" listener. Every view must use its own `.name`.

## Store

```js
function createStore(initial) {
  let state = { ...initial };
  const listeners = new Set();
  return {
    get: () => state,
    set(updates, source) {
      state = { ...state, ...updates };
      for (const fn of listeners) fn(state, source);
    },
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
  };
}
```

## Keyed selection model

One class for all selection composition. Each source (a brush, a lasso, a legend click) owns one key set; the model combines them. `intersect` is cross-filtering (row must pass every active filter); `union` is "any brush selects." An empty model means everything is selected, so views show full data until someone brushes.

```js
class SelectionModel {
  #sources = new Map();          // source id -> Set of keys
  #dispatch = d3.dispatch("change");
  constructor(mode = "intersect") { this.mode = mode; }

  update(source, keys) {
    if (keys?.length) this.#sources.set(source, new Set(keys));
    else this.#sources.delete(source);
    this.#dispatch.call("change", null, { source, keys: this.keys() });
  }
  keys() {
    const sets = [...this.#sources.values()];
    if (!sets.length) return null;               // null = no filter active
    if (this.mode === "union") return new Set(sets.flatMap(s => [...s]));
    return sets.slice(1).reduce((acc, s) => new Set([...acc].filter(k => s.has(k))), sets[0]);
  }
  isSelected(key) { const k = this.keys(); return !k || k.has(key); }
  on(type, fn) { this.#dispatch.on(type, fn); return this; }
}
```

`keys()` recomputes on each call; cache it in `update` if views call `isSelected` per mark. Listeners receive `source` so the view that emitted can skip redrawing its own brush.

## Update storms: one render per frame

Resetting three brushes, or one brush firing at 120Hz, must produce one render, not dozens. Mark dirty, render in rAF:

```js
let pending = false;
function scheduleRender() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => { pending = false; renderAll(); });
}
```

The *computation* belongs inside the frame too. Recomputing a filter mask synchronously in the brush handler and only deferring the paint still burns the main thread per event. Store the latest extent in the handler; compute and draw in the frame.

**Render priority**: in the frame, draw the view under the pointer first and push the others to the next frame if the budget is spent.

## Bitmap cross-filtering (crossfilter pattern)

Bit `i` of a dimension's mask is set when row `i` passes that dimension's filter. The combined filter is the AND of all masks.

```js
const words = Math.ceil(n / 32);
function combine(masks, skip) {               // skip: the dimension being drawn
  const out = new Uint32Array(words).fill(0xFFFFFFFF);
  for (const [dim, mask] of masks) {
    if (dim === skip) continue;
    for (let w = 0; w < words; w++) out[w] &= mask[w];
  }
  return out;
}
const passes = (bits, i) => (bits[i >>> 5] >>> (i & 31)) & 1;
```

A histogram in a cross-filter shows rows that pass every *other* dimension's filter (`combine(masks, ownDim)`); applying its own filter to itself makes the brushed region the only non-empty bins. Only rebuild the mask for the dimension whose brush moved.

## Framework bridges

- **React**: create the dispatcher once (`useMemo` or module scope), register in `useEffect` with a unique namespace, return `() => dispatch.on("highlight.myChart", null)`. Never push per-pointermove state into React state.
- **Vue**: `provide` the dispatcher in the dashboard, `inject` in charts, clear listeners in `onUnmounted`.
- **Angular**: attach brush/zoom listeners inside `ngZone.runOutsideAngular` and re-enter with `ngZone.run` only on brush `end` or other meaningful changes.

## Traps

- **Feedback loop**: A updates B, B's handler updates A. Tag every emit with a source id and skip your own; for d3 behaviors, ignore events whose `sourceEvent` is null (they came from code, not the user).
- **Stale closure**: a listener registered at setup captured `x` and `data`; after resize or reload it uses the old ones. Read scales and data from the store, or from a mutable chart object, inside the listener.
- **Leaked listeners**: views that unmount without `.on("name", null)` keep firing into detached DOM, and a remount adds a second copy.
- **Index identity**: selecting by array index across views that sort or filter differently highlights the wrong rows. Select by key.
