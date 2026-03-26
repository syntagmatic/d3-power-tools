# Linked Views — State of the Art Research

Research date: 2026-03-25

## Current Coverage

The `skills/linked-views/SKILL.md` already covers:

- **When not to link** — Baldonado guidelines (3-4 view working memory limit, avoid linking unrelated dimensions, update storms, small multiples vs linked views)
- **Coordination architecture** — three tiers: direct coupling (2 charts), d3.dispatch event bus (3-8 charts), shared state store (complex state / undo/redo)
- **SelectionModel** — key-based selection with toggle, clear, empty-means-all semantics, source-based feedback loop prevention
- **Bitmap crossfilter** — Uint32Array bitmask per dimension, AND-based intersection, popcount for aggregates, incremental single-dimension updates, O(N/32 * D) vs O(N * D) naive
- **Feedback loops** — sourceEvent check, boolean guard flag, transform comparison
- **Scale domain strategies** — fixed vs auto-rescale, rescale on end not drag
- **State serialization** — URL encoding, undo/redo with history stack
- **RAF coalescing** — batch multiple state changes into one render pass
- **Ghost/active pattern** — dimmed background + vivid foreground for histograms, KDE, canvas scatter
- **Render queue** — prioritize source chart, queue linked charts
- **Pitfalls** — memory leaks, stale closures, brush visual not cleared, tooltip fights, transitions during drag, granularity mismatch

References include crossfilter, d3.parcoords, Munzner Ch.13, Shneiderman Dynamic Queries, and Baldonado et al.

**Gaps identified:** No coverage of server-side / database-backed filtering (Mosaic), declarative interaction grammars (Vega-Lite selections), Falcon prefetching for billion-scale data, Observable Framework reactive patterns, or GPU-accelerated filtering (cuxfilter). The Baldonado guidelines are mentioned but the eight rules aren't enumerated.

---

## Mosaic Framework (UW, server-side filtering, DuckDB integration)

**What it is.** Mosaic (Heer et al., IEEE TVCG 2024) is an architecture for linking databases and interactive views. Interface components publish their data needs as declarative SQL queries. A central Coordinator manages query dispatch to DuckDB (either server-side or client-side via DuckDB-WASM).

**Key abstractions:**
- **Coordinator** — collects queries from clients, issues them to DuckDB, returns results. Manages filter groups (collections of clients sharing a `filterBy` selection). Applies optimizations: query caching, consolidation, and data cube index construction.
- **Selections** — represent filter criteria as SQL WHERE clauses. A single selection can combine predicates from diverse clients. Selections "resolve" different criteria for different clients, enabling cross-filtering where each chart excludes its own filter (so brushing a histogram doesn't filter itself).
- **Params** — for linking scalar values (e.g., a slider controlling a threshold across views).
- **Data cube indexes** — precomputed aggregation cubes that allow instant cross-filter updates without re-querying the database. The Coordinator automatically builds these for filter groups involving supported aggregation queries.
- **MosaicClient interface** — any component implementing `query()` and accepting result data can participate. Custom D3 visualizations can implement this interface.

**Scale limits:** Cross-filters 10M flight records interactively in the browser (DuckDB-WASM). With a server-side DuckDB instance, scales further. The data cube index optimization is what makes this feasible — without it, each brush drag would require a full SQL query round-trip.

**D3 integration path:** Mosaic's `vgplot` layer uses Observable Plot (which wraps D3 internally). For custom D3 charts, implement the MosaicClient interface: provide a `query()` method returning a SQL query and a `queryResult()` method accepting the data. The chart then participates in Mosaic's selection/filter system. This is a real integration path — you keep your D3 rendering code and gain server-backed cross-filtering.

**When to use vs hand-rolling:**
- Use Mosaic when data exceeds browser memory (>50MB), when you need cross-filtering over aggregated views (histograms, heatmaps), or when you want SQL as the coordination language.
- Hand-roll with d3.dispatch when data fits in memory, you need fine-grained control over rendering, or your coordination logic is simple (2-4 views with highlight/brush).

Sources:
- [Mosaic GitHub](https://github.com/uwdata/mosaic)
- [Mosaic paper (TVCG 2024)](https://idl.cs.washington.edu/files/2024-Mosaic-TVCG.pdf)
- [Cross-Filter Flights 10M example](https://idl.uw.edu/mosaic/examples/flights-10m.html)
- [Mosaic Core API](https://idl.uw.edu/mosaic/core/)
- [vgplot API](https://idl.uw.edu/mosaic/vgplot/)

---

## Vega-Lite Selections (declarative interaction, when it saves time)

**What it is.** Vega-Lite provides a grammar of interaction via *selection parameters*. Instead of wiring event handlers and state management imperatively, you declare what interactions do in JSON.

**Selection types:**
- **Point selection** — discrete data points. Triggered by click (default). Supports multi-select with shift. Values are specific data tuples.
- **Interval selection** — continuous ranges. Triggered by brush/drag. Produces extent ranges over encoding channels.

**What selections can do:**
- **Filter data** — use a selection as a filter transform to show only selected points in a linked view.
- **Drive conditional encodings** — `"condition": {"param": "brush", "value": "steelblue"}` makes unselected points gray.
- **Control scale domains** — bind an interval selection to a scale's domain, creating overview+detail (brush in overview, detail view zooms).
- **Compose** — logical `and`, `or`, `not` operators combine multiple selections.

**Abstraction over D3:** Vega-Lite selections eliminate the need to write:
1. Event listeners (mouse, touch, keyboard modifiers)
2. State management (what's selected, what's the brush extent)
3. Predicate testing (is this datum in the selection?)
4. Cross-view propagation (how does view A's selection affect view B?)
5. Visual feedback (conditional encoding for selected vs unselected)

All of this collapses into a few JSON properties. The Vega-Lite compiler synthesizes the event handling and data flow.

**Limits:**
- You get Vega-Lite's rendering, not your own. Custom D3 rendering requires dropping down to Vega signals or leaving the Vega ecosystem entirely.
- The interaction vocabulary is fixed — point and interval. Custom interactions (lasso, force-directed drag) aren't expressible.
- Performance caps around 10K-50K marks in SVG. No Canvas path.

**When to use:**
- Prototyping linked views quickly to test whether a coordination pattern is useful before investing in D3 implementation.
- Dashboards where the standard interaction vocabulary (click, brush, filter, highlight) is sufficient.
- When the team includes non-programmers who can work with JSON specs.

**Migration path to D3:** Vega-Lite is useful as a design tool. Build the interaction in Vega-Lite, verify the coordination logic works, then re-implement in D3 with d3.dispatch if you need custom rendering or performance beyond SVG limits. The selection model concept maps directly to the SelectionModel class in the current skill.

Sources:
- [Vega-Lite Selection Parameters](https://vega.github.io/vega-lite/docs/selection.html)
- [Vega-Lite paper (InfoVis 2017)](https://idl.cs.washington.edu/files/2017-VegaLite-InfoVis.pdf)
- [Dynamic Behaviors with Parameters](https://vega.github.io/vega-lite/docs/parameter.html)

---

## Crossfilter Evolution (crossfilter2, Falcon, modern alternatives)

### crossfilter2
The community-maintained fork of Square's original crossfilter. Still uses sorted indexes with incremental filtering. Key insight: most interactions only adjust one dimension, so incremental re-filtering is much faster than recomputing from scratch. Handles ~1M records client-side with <30ms updates.

**Status:** Maintained but architecturally unchanged. The sorted-index approach is well-understood. The bitmap approach in the current skill is a simpler alternative that trades sorted-index sophistication for cache-friendly bitwise operations.

### Falcon (CMU, Moritz/Howe/Heer, CHI 2019)
**Key innovation: user-centered prefetching.** Falcon observes which view the user is actively brushing and precomputes data cubes for that view's cross-filter interactions. Two strategies:

1. **Active view reindexing** — when the user starts brushing a view, Falcon precomputes aggregation indices for all linked views relative to that view's filter dimension. Brushing then reads from the precomputed index instead of re-querying.
2. **Progressive resolution** — initially loads reduced resolution (fewer bins), then progressively improves. Cold-start exploration of billion-record datasets becomes feasible because the initial view loads fast.

**Performance:** 50 fps brush updates, invariant from thousands to billions of records. Connected to a backing database for billion-scale; in-browser for millions.

**Scale limits:** Billions of records with a database backend. The cost shifts from query time to prefetch time — there's a brief pause when switching active views while the system prefetches new indices.

**D3 integration:** Falcon is a data-layer optimization. It doesn't dictate rendering. You can use Falcon's indices to feed D3 histograms/charts. The npm package `falcon-vis` provides the prefetching logic.

### cuxfilter (RAPIDS/NVIDIA)
GPU-accelerated cross-filtering using cuDF (GPU DataFrames). Relevant for Python/CUDA environments, not browser-based D3. Mentioned for completeness — if your pipeline includes GPU-backed data processing, cuxfilter can feed pre-filtered data to a D3 frontend via websockets.

### Landscape summary

| Approach | Scale | Latency | Where it runs |
|----------|-------|---------|---------------|
| Array.filter + Set | <5K rows | <1ms | Browser |
| Bitmap (current skill) | 5K-500K | <2ms | Browser |
| crossfilter2 sorted index | <1M | <30ms | Browser |
| Falcon prefetch | Millions-billions | <20ms brush | Browser + optional DB |
| Mosaic + DuckDB | Millions-billions | <100ms query | Browser (WASM) or server |
| cuxfilter | Billions | <10ms | GPU server |

Sources:
- [crossfilter2 npm](https://www.npmjs.com/package/crossfilter2)
- [crossfilter GitHub](https://github.com/crossfilter/crossfilter)
- [Falcon paper (CHI 2019)](https://www.domoritz.de/papers/2019-Falcon-CHI.pdf)
- [Falcon GitHub](https://github.com/cmudig/falcon-vis)
- [cuxfilter GitHub](https://github.com/rapidsai/cuxfilter)

---

## Scalability Research (how many views, cognitive limits, Baldonado guidelines)

### Baldonado, Woodruff & Kuchinsky (AVI 2000) — Eight Guidelines

The canonical guidelines, organized by selection, presentation, and interaction:

1. **Diversity** — use multiple views when there is a diversity of attributes, models, user profiles, levels of abstraction, or genres. Don't add views that show the same thing differently without reason.
2. **Complementarity** — use multiple views when different views bring out correlations or disparities not visible in any single view.
3. **Decomposition** — partition complex data into manageable chunks across views when a single view would be overwhelmingly complex.
4. **Parsimony** — use the fewest views necessary. Each added view has cognitive cost (attention splitting, context switching). If one view suffices, don't add a second.
5. **Space/time resource optimization** — balance the computational and screen-space cost of views against their benefit. A view that's too small to read wastes space; one that's too expensive to update breaks interactivity.
6. **Self-evidence** — make the relationships between views self-evident through visual design. If the user can't tell that brushing view A affects view B, the link is useless.
7. **Consistency** — maintain consistent visual encodings across views (same color scale, same axis orientation) so users can transfer knowledge between views without re-learning.
8. **Attention management** — guide the user's attention to the right view at the right time. Highlight changes, animate transitions between states, use visual cues to indicate which view responded to an interaction.

### Cognitive limits

- **Working memory ~4 chunks** (Cowan, 2001): beyond 3-4 simultaneously active views, users lose track of which view they brushed and what the response means. Group views into clusters with clear hierarchy (overview panel + detail panels).
- **Context switching cost** — switching between substantially different visual representations (e.g., scatter to map to table) is more expensive than switching between similar ones (scatter to scatter with different axes). Minimize heterogeneity of view types when possible.
- **Change blindness** — users may not notice changes in peripheral views when focused on the view they're interacting with. Use animation, color flash, or progressive highlighting to draw attention to updates in linked views.
- **Information overload** — dashboards with many coordinated views can overwhelm. Progressive disclosure (show detail on demand) is better than showing everything at once.

### Practical view count guidance

- **2 views** — overview+detail or same data, two encodings. Almost always beneficial.
- **3-4 views** — the sweet spot for exploratory analysis. One spatial, one temporal, one categorical.
- **5-8 views** — requires strong spatial grouping and clear hierarchy. Common in analyst dashboards.
- **8+ views** — diminishing returns. Users satisfice (look at 2-3 views) rather than integrate all of them. Consider progressive disclosure or view switching rather than simultaneous display.

Sources:
- [Baldonado et al. (AVI 2000)](https://courses.ischool.berkeley.edu/i247/f05/readings/Baldonado_MultipleViews_AVI00.pdf)
- [Scherr — Multiple and Coordinated Views survey](https://www.mmi.ifi.lmu.de/lehre/ws0809/hs/docs/scherr.pdf)
- [Roberts — State of the Art: Coordinated & Multiple Views](https://www.researchgate.net/publication/4259731_State_of_the_Art_Coordinated_Multiple_Views_in_Exploratory_Visualization)

---

## Observable View Coordination (Inputs, Generators, synchronized state)

### Observable Notebooks (legacy, still widely used)

- **`viewof`** — a cell that exposes both a DOM element and a reactive value. When the user interacts with the element, the value updates, and all cells that reference it re-run. This is implicit coordination — no explicit event wiring.
- **`mutable`** — a cell whose value can be set programmatically from other cells. Used when coordination goes beyond simple input-output (e.g., one chart sets a value that drives another).
- **Views are mutable values** — Mike Bostock's pattern: treat a view as a mutable container. One "primary" view owns the value; "secondary" views listen and mutate. This avoids feedback loops by establishing a clear ownership hierarchy.
- **Reactive dependency graph** — the Observable runtime tracks which cells depend on which values. When a value changes, only dependent cells re-run. This is automatic — no manual subscription management.

### Observable Framework (2024+)

- **Shift from `viewof` to plain JS** — Observable Framework uses Markdown files with embedded JavaScript blocks. Reactivity is still present but via a simpler file-based model. `viewof` from notebooks is removed; state is managed with standard JS patterns.
- **`Mutable()` function** — declares reactive state at the page level. Components receive state as props. All reactive state lives at the page level, not inside components.
- **Client-side reactivity** — unlike Shiny (server-side), Observable handles everything client-side. Updates are instantaneous for small-to-medium data.
- **D3 integration** — D3 is a first-class citizen. You write D3 code in JS blocks and it participates in the reactive graph naturally.

### Patterns for D3 power-tools

The Observable patterns are useful reference but not directly portable — they depend on Observable's runtime. The transferable ideas:

1. **Ownership hierarchy** — designate one view as the "source of truth" for each piece of shared state. Others read from it. This prevents the bidirectional update storms that plague naive d3.dispatch setups.
2. **Dependency-driven updates** — instead of subscribing everything to everything, model the dependency graph explicitly. Only update what actually depends on the changed state.
3. **Reactive state containers** — the `Mutable()` pattern is essentially the `createStore()` pattern from the current skill, with automatic subscriber notification.

Sources:
- [Synchronized Views — Mike Bostock](https://observablehq.com/@mbostock/synchronized-views)
- [Synchronized Inputs — Observable](https://observablehq.com/@observablehq/synchronized-inputs)
- [Views are Mutable Values — Bostock](https://observablehq.com/@mbostock/views-are-mutable-values)
- [Interesting ideas in Observable Framework — Simon Willison](https://simonwillison.net/2024/Mar/3/interesting-ideas-in-observable-framework/)

---

## When to Use a Framework vs Hand-Roll (decision criteria)

| Criterion | Hand-roll (d3.dispatch / store) | Mosaic | Vega-Lite |
|-----------|-------------------------------|--------|-----------|
| **Data fits in browser memory** (<50MB) | Best choice | Overkill | Good for prototyping |
| **Data exceeds memory** (>100MB) | Not feasible | Built for this | Not feasible |
| **Custom rendering needed** (Canvas, WebGL, unusual layouts) | Only option | Possible via MosaicClient | Not supported |
| **Standard chart types** (scatter, bar, line, histogram) | Works but verbose | Good | Best — minimal code |
| **Complex interactions** (lasso, force drag, custom brushes) | Only option | Limited | Not supported |
| **Team skill** | Requires D3 expertise | SQL + some JS | JSON spec, low barrier |
| **Coordination complexity** (2-3 views) | Simple and direct | Overhead not justified | Good |
| **Coordination complexity** (5+ views with cross-filter) | Lots of plumbing | Handles automatically | Good if standard interactions |
| **Performance at scale** (>1M points) | Requires bitmap/Canvas optimization | DuckDB handles filtering | SVG limits ~10K-50K marks |
| **Embeddability** | Full control | Needs Mosaic runtime | Needs Vega runtime |

### Decision flowchart

1. **Is the data >50MB or does filtering require aggregation over large datasets?**
   - Yes → Mosaic (or Falcon for prefetch-based approach)
   - No → continue

2. **Do you need custom rendering (Canvas, WebGL, unusual mark types)?**
   - Yes → hand-roll with d3.dispatch/store
   - No → continue

3. **Are standard interactions (click select, brush filter, hover highlight) sufficient?**
   - Yes → Vega-Lite for speed, or hand-roll if you need full control over styling/animation
   - No → hand-roll

4. **How many views need coordination?**
   - 2 → direct coupling, no framework needed
   - 3-8 → d3.dispatch event bus
   - 8+ with complex state → shared state store with RAF coalescing

---

## Code Patterns

### Mosaic client interface for custom D3 charts

```js
// Implement MosaicClient to plug a D3 chart into Mosaic's coordination
class D3ScatterClient {
  constructor(container, coordinator) {
    this.container = container;
    this.coordinator = coordinator;
    // Standard D3 setup: svg, scales, axes...
    this.svg = d3.select(container).append("svg");
    // Register with coordinator
    coordinator.connect(this);
  }

  // Called by Coordinator — return the SQL query for this view's data
  query(filter = []) {
    const where = filter.length ? `WHERE ${filter.join(" AND ")}` : "";
    return `SELECT x, y, category FROM dataset ${where}`;
  }

  // Called by Coordinator with query results
  queryResult(data) {
    // Standard D3 join with the filtered data
    this.svg.selectAll("circle")
      .data(data, d => d.id)
      .join("circle")
      .attr("cx", d => this.xScale(d.x))
      .attr("cy", d => this.yScale(d.y))
      .attr("r", 3);
  }
}
```

### Falcon-style prefetch index for D3 crossfilter

```js
// Precompute 2D histogram counts for all brush positions on active dimension
function buildPrefetchIndex(data, activeDim, linkedDims, binCounts) {
  // For each possible bin of activeDim, precompute counts for all linkedDims
  const activeBins = d3.bin().thresholds(binCounts[activeDim])(
    data.map(d => d[activeDim])
  );

  // Build cube: activeBins × linkedDim bins
  const cubes = new Map();
  for (const dim of linkedDims) {
    const bins = binCounts[dim];
    // cube[activeBinIndex] = Uint32Array of counts for each linked bin
    const cube = activeBins.map(() => new Uint32Array(bins));
    for (let i = 0; i < data.length; i++) {
      const aIdx = bisect(activeBins, data[i][activeDim]);
      const lIdx = bisect(bins, data[i][dim]);
      cube[aIdx][lIdx]++;
    }
    cubes.set(dim, cube);
  }

  // On brush: sum cube slices for bins within brush extent
  return {
    query(brushLo, brushHi) {
      const results = new Map();
      const loIdx = bisect(activeBins, brushLo);
      const hiIdx = bisect(activeBins, brushHi);
      for (const [dim, cube] of cubes) {
        const counts = new Uint32Array(cube[0].length);
        for (let a = loIdx; a < hiIdx; a++) {
          for (let l = 0; l < counts.length; l++) counts[l] += cube[a][l];
        }
        results.set(dim, counts);
      }
      return results; // per-linked-dim histogram counts, no re-scan needed
    }
  };
}
```

### Vega-Lite linked brushing (declarative, for comparison)

```json
{
  "hconcat": [
    {
      "mark": "point",
      "params": [{"name": "brush", "select": "interval"}],
      "encoding": {
        "x": {"field": "x", "type": "quantitative"},
        "y": {"field": "y", "type": "quantitative"},
        "color": {
          "condition": {"param": "brush", "field": "category", "type": "nominal"},
          "value": "lightgray"
        }
      }
    },
    {
      "mark": "bar",
      "transform": [{"filter": {"param": "brush"}}],
      "encoding": {
        "x": {"field": "category", "type": "nominal"},
        "y": {"aggregate": "count"}
      }
    }
  ]
}
```

This produces a linked scatter + bar chart with brushing in ~15 lines of JSON. The equivalent D3 implementation would be ~150 lines. The tradeoff is control: the Vega-Lite version uses SVG with Vega's default styling and interaction semantics.

### Observable-style ownership hierarchy (portable pattern)

```js
// Designate one view as owner per state dimension — prevents feedback loops
// without needing boolean guard flags

function createOwnedState(owner) {
  let value = undefined;
  const listeners = new Set();
  return {
    get: () => value,
    // Only the owner can set; others must request via the owner
    set(newValue, source) {
      if (source !== owner && source !== "reset") return;
      value = newValue;
      for (const fn of listeners) fn(value);
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    }
  };
}

// Usage: timeline owns the time range, scatter owns the point selection
const timeRange = createOwnedState("timeline");
const pointSelection = createOwnedState("scatter");
```
