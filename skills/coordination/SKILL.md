---
name: coordination
description: "The technical foundation for multi-chart communication. Use this skill to wire independent D3 components together using d3.dispatch, shared state stores, or selection models. Covers namespacing, update storms, framework bridges (React, Vue, Angular), and high-performance bitmap indexing for 100K+ rows."
---

# Coordination

A single chart is a statement; coordinated charts are a conversation. Coordination is the technical "wiring" that allows a brush in one view to update a filter in another. The judgment is choosing the right abstraction level—O(n²) direct coupling, O(n) event buses, or a centralized state store—to keep the system responsive and maintainable.

For design patterns (Overview+Detail, Cross-filtering), see `linked-views`. For brush mechanics, see `brushing`. For faceted layouts of the same chart type, see `small-multiples`.

## Coordination Architecture

Choose your architecture based on the number of charts and the complexity of the state:

### 1. Event Bus with `d3.dispatch` (3–8 charts)
The standard choice. Charts emit events and subscribe independently. Use **namespaced listeners** (`event.id`) to prevent collisions and allow easy teardown.

```js
const dispatch = d3.dispatch("brush", "hover", "filter");

// In Chart A
dispatch.on("brush.chartA", (range) => {
  // Update local view based on brush from elsewhere
});

// To trigger:
dispatch.call("brush", this, range);
```

### 2. Shared State Store (Complex state, Undo/Redo)
Use a plain object to hold the "Source of Truth." Changes go through a single function that notifies subscribers. This is more robust than `d3.dispatch` for deep state (e.g., zoom + filter + sort).

```js
function createStore(initialState) {
  let state = { ...initialState };
  const listeners = new Set();
  return {
    getState: () => state,
    setState(updates) {
      state = { ...state, ...updates };
      for (const fn of listeners) fn(state);
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}
```

### 3. Selection Model
A specialized class for managing "which rows are active." Critical for ensuring every chart agrees on the same datum without relying on fragile array indices.

```js
class SelectionModel {
  #keys = new Set();
  #dispatch = d3.dispatch("change");

  select(keys, source) {
    this.#keys = new Set(keys);
    this.#dispatch.call("change", null, { keys: this.#keys, source });
  }
  isSelected(key) { return this.#keys.size === 0 || this.#keys.has(key); }
  on(event, fn) { this.#dispatch.on(event, fn); return this; }
}
```

## Framework Bridges

Bridging D3's imperative event system to a declarative framework's render loop is the most common source of performance bottlenecks and "update storms."

### React: The Context/Hook Pattern
Use `useMemo` for a stable dispatcher and `useEffect` with cleanup to prevent memory leaks.

```js
const DispatchContext = createContext(d3.dispatch("highlight"));

// Chart Component
const dispatch = useContext(DispatchContext);
useEffect(() => {
  dispatch.on("highlight.myChart", id => updateChart(id));
  return () => dispatch.on("highlight.myChart", null);
}, [dispatch]);
```

### Vue: The Provide/Inject Pattern
`provide` the dispatcher in a parent Dashboard and `inject` it in child charts. Use `onUnmounted` to clear listeners.

### Angular: The `runOutsideAngular` Pattern
High-frequency events (brushes/zooms) should bypass Angular's change detection. Trigger updates manually when a "meaningful" change occurs.

```typescript
this.ngZone.runOutsideAngular(() => {
  this.dispatch.on("brush", (range) => {
    this.updateD3(range); // Direct DOM/Canvas manipulation
    if (range.isFinal) this.ngZone.run(() => this.syncToState());
  });
});
```

## Performance & Optimization

### 1. requestAnimationFrame (RAF) Coalescing
Prevent "update storms" by batching multiple simultaneous state changes (e.g., resetting 3 brushes) into a single render pass per frame.

```js
let pending = false;
function scheduleRender() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => { pending = false; renderAll(); });
}
```

### 2. Bitmap Indexing (Crossfilter Pattern)
For 100K+ rows, `Array.filter` is too slow for 60fps interaction. Use bitmasks where bit `i` represents if row `i` passes a filter. Bitwise ANDing dimension masks is ~32x faster than naive iteration.

```js
// AND all dimension masks
for (const mask of dimensionMasks) {
  for (let w = 0; w < words; w++) result[w] &= mask[w];
}
```

### 3. Render Priority (Source First)
When updating multiple charts, render the chart currently under the user's pointer first. Delay others by one frame. This ensures the chart the user is "touching" never lags, maintaining the illusion of responsiveness.

## Common Pitfalls

- **Feedback Loops:** Chart A updates B, which triggers A. **Fix:** Always check `event.sourceEvent` or pass a `source` ID to your dispatcher/store. If the event originated from *this* chart, skip the update.
- **Stale Closures:** Listeners capture old scales or data. **Fix:** Always read the *current* state from your store or closure inside the listener function.
- **Memory Leaks:** Forgetting to remove `.on("name", null)` when a component unmounts. In long-lived single-page apps, this will eventually crash the browser.
