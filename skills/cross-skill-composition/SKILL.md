---
name: cross-skill-composition
description: "Architectural patterns for combining multiple D3 visualization skills into a single application. Use this skill when building any non-trivial visualization that layers Canvas rendering with SVG interaction, coordinates multiple views, sequences initialization, manages shared state, or needs a performance budget across composed concerns. Also use when the user asks about SVG vs Canvas tradeoffs, layer stacking, resize handling across mixed renderers, or how to wire brushing/zoom/animation/accessibility together in one visualization."
---

# Cross-Skill Composition

Every interesting visualization is a composition. A brushable Canvas scatterplot with linked histogram is five skills at once: `canvas-rendering`, `axes-and-scales`, `brushing-and-selection`, `linked-views`, `responsive-charts`. Each skill documents its own patterns — this skill documents the **glue**: how they initialize, how state flows between them, where the performance budget goes, and what breaks when you get the ordering wrong.

For coordination between separate charts, see `linked-views`. For Canvas layer setup, see `canvas-rendering`. For brush mechanics, see `brushing-and-selection`. This skill covers what none of them cover: how they compose within a single visualization.

## The Layer Stack

Every composed visualization is a vertical stack of rendering layers. The critical decision is what goes on which layer.

```
┌─────────────────────────────────────┐
│  HTML        (controls, legend)     │  ← DOM, always on top
│  SVG overlay (axes, brushes, focus) │  ← pointer-events: all
│  Canvas: highlight                  │  ← selected/hovered subset
│  Canvas: data                       │  ← full dataset, dimmed when brushed
│  Canvas: hit detection (hidden)     │  ← color-picking, never displayed
│  Container div (position: relative) │
└─────────────────────────────────────┘
```

Not every visualization needs all layers. Collapse them based on complexity:

| Scenario | Layers |
|----------|--------|
| <500 elements, full interaction | SVG only |
| 500–50K elements, brush/hover | Canvas data + SVG overlay |
| 50K+ with selection highlighting | Canvas data + Canvas highlight + SVG overlay |
| Hit detection on lines/paths | Add hidden hit canvas |
| Controls, legend, or data table | Add HTML layer |

### Wiring the Stack

All layers share identical coordinate systems — same `width`, `height`, `margin`. The container is `position: relative`; children are `position: absolute` stacked with DOM order (later = on top) or explicit `z-index`.

```js
function createLayerStack(container, width, height, margin) {
  const div = container.append("div")
    .style("position", "relative")
    .style("width", `${width}px`)
    .style("height", `${height}px`);

  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  // Canvas layers — bottom of stack
  const dataCtx = addCanvas(div, width, height, "data");
  const hlCtx = addCanvas(div, width, height, "highlight");

  // SVG overlay — top of stack, captures pointer events
  const svg = div.append("svg")
    .attr("width", width).attr("height", height)
    .style("position", "absolute").style("top", 0).style("left", 0);
  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // Translate canvas origins to match SVG margin convention
  [dataCtx, hlCtx].forEach(ctx => ctx.translate(margin.left, margin.top));

  return { div, dataCtx, hlCtx, svg, g, innerW, innerH };
}
```

See `canvas-rendering` for `addCanvas` with DPR setup. The key detail: `ctx.translate(margin.left, margin.top)` once after setup, so all Canvas drawing coordinates match SVG's `g` transform.

## SVG vs Canvas Decision

The decision is not about element count alone. It depends on three axes:

| | Few updates | Continuous updates (animation, drag) |
|---|---|---|
| **<500 elements** | SVG | SVG (transitions are cheap) |
| **500–5K elements** | SVG or Canvas | Canvas |
| **5K–100K elements** | Canvas | Canvas + render queue |
| **100K+ elements** | Canvas + typed arrays | WebGL |

But element count is only one factor:

- **Interaction type matters.** 2K SVG circles with hover work fine. 2K SVG circles with drag-to-reorder stutter because each drag frame recalculates layout and forces a reflow.
- **Update frequency matters.** A force simulation with 300 nodes redraws 60x/sec — Canvas even at low counts, because SVG attribute updates at that rate cause layout thrashing.
- **Shape complexity matters.** 500 complex paths (geographic boundaries) are slower in SVG than 5000 circles, because path rendering is more expensive per element.

### The Hybrid Pattern

The most common composition: **Canvas for data marks, SVG for interaction chrome.** This is not a compromise — it is the optimal architecture. Canvas is fast for rendering; SVG is fast for events. Use each where it is best.

Canvas renders: data points, lines, filled areas, heatmaps — anything that is drawn per-datum.
SVG renders: axes, axis labels, brush overlays, focus rings, annotations, tooltips — anything the user interacts with or that needs DOM accessibility.

### The Handoff Pattern

For transitions between states with different performance profiles:

1. **Animate in Canvas** — smooth 60fps morphing, interpolating positions
2. **On animation end, render final state in SVG** — interactive, accessible, selectable

This is useful for layout transitions (treemap→pack) where the animation needs Canvas performance but the resting state needs SVG interactivity. The swap is invisible if Canvas and SVG coordinates match exactly.

```js
function animateToSVG(canvasCtx, svgGroup, data, targetPositions, duration = 600) {
  // 1. Hide SVG during animation
  svgGroup.style("opacity", 0);
  // 2. Animate on Canvas
  const interp = data.map((d, i) => ({
    x: d3.interpolateNumber(d.x, targetPositions[i].x),
    y: d3.interpolateNumber(d.y, targetPositions[i].y),
  }));
  const timer = d3.timer(elapsed => {
    const t = Math.min(1, d3.easeCubicInOut(elapsed / duration));
    canvasCtx.clearRect(-margin.left, -margin.top, width, height);
    data.forEach((d, i) => {
      drawMark(canvasCtx, interp[i].x(t), interp[i].y(t), d);
    });
    if (t >= 1) {
      timer.stop();
      // 3. Swap to SVG
      canvasCtx.clearRect(-margin.left, -margin.top, width, height);
      svgGroup.style("opacity", 1);
      updateSVGPositions(svgGroup, data, targetPositions);
    }
  });
}
```

## Initialization Sequence

Skills have implicit dependencies that create a required initialization order. Getting this wrong produces blank frames, wrong scales, or race conditions.

### The Canonical Pipeline

```
1. Data load + clean        (data-preparation)
2. Container measure        (responsive-charts)
3. Layer stack create       (canvas-rendering + this skill)
4. Scales construct         (axes-and-scales)
5. Layout compute           (hierarchy-layouts, force-simulation, d3.bin)
6. Static chrome render     (axes, gridlines, legends)
7. Data render              (marks on Canvas or SVG)
8. Interaction bind         (brushes, zoom, drag, tooltips)
9. Accessibility setup      (canvas-accessibility, fallback-table)
10. Theme apply             (color-themes)
```

Why this order:
- **Scales need container dimensions** (step 4 depends on step 2). Building scales before measuring the container produces a 0-width range.
- **Layouts need scales** (step 5 depends on step 4). Force simulations need center coordinates; binning needs the scale domain.
- **Interactions need rendered elements** (step 8 depends on step 7). Brush extents reference the rendering area; zoom translateExtent needs the content bounds.
- **Accessibility needs final DOM** (step 9 depends on step 7-8). Hidden DOM mirrors and ARIA attributes reference the rendered state.

### The Render Function

Wrap steps 4-10 in a single `render(width, height)` function. This is the unit of reuse — resize calls it, data change calls it, theme change calls it.

```js
function render(width, height) {
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  // 4. Scales
  const x = d3.scaleLinear().domain(d3.extent(data, d => d.a)).nice().range([0, innerW]);
  const y = d3.scaleLinear().domain(d3.extent(data, d => d.b)).nice().range([innerH, 0]);
  const color = d3.scaleOrdinal(d3.schemeTableau10).domain(categories);

  // 5. Layout (if needed)
  const bins = d3.bin().domain(x.domain()).thresholds(20)(data.map(d => d.a));

  // 6. Static chrome
  xAxisG.call(d3.axisBottom(x));
  yAxisG.call(d3.axisLeft(y));

  // 7. Data render
  drawScatter(dataCtx, data, x, y, color);
  drawHistogram(histG, bins, histY);

  // 8. Interactions (rebind with new scales)
  bindBrush(g, x, y, data, selection);
  bindZoom(svg, x, y, dataCtx, hlCtx);

  // 9. Accessibility
  updateHiddenTable(data, selection);

  // 10. Theme
  applyTheme(dataCtx, svg);
}
```

### What Runs on Resize

Not everything re-runs. The resize subset is steps 3-10 (layer stack resizes, scales recompute, everything redraws). Steps 1-2 do not re-run — data doesn't change on resize, and the new container dimensions come from the ResizeObserver callback.

```js
const ro = new ResizeObserver(entries => {
  const { width, height } = entries[0].contentRect;
  resizeCanvases(width, height);  // step 3
  render(width, height);          // steps 4-10
});
ro.observe(container.node());
```

### What Runs on Data Change

Steps 1, 4-10. Container size doesn't change, layer stack doesn't change. But scales may need new domains, layouts recompute, and interactions rebind.

### What Runs on Theme Change

Steps 7, 10 only. Canvas must re-read CSS custom properties and redraw; SVG updates automatically if colors are set via CSS classes rather than inline attributes. See `color-themes` for the CSS-driven SVG pattern that avoids JS rebuilds.

## State Architecture

Composed visualizations have three kinds of state. Mixing them up causes bugs.

### Data State (Immutable After Load)

The raw dataset, cleaned and typed. Never mutated by interaction. Every derived computation (scales, bins, layouts) reads from this.

```js
const data = await loadAndClean("data.csv");
Object.freeze(data); // enforce immutability
```

### View State (Derived, Recomputed)

Scales, layout positions, bin boundaries, axis configurations. Derived from data + container dimensions. Recomputed on resize or data change. Not directly mutated by the user — it changes as a consequence of container or data changes.

### Interaction State (Transient, User-Driven)

Selection sets, brush extents, zoom transforms, hover targets, expanded/collapsed nodes. This is the state that flows between skills via `d3.dispatch`, `SelectionModel`, or `createStore` (see `linked-views` for these patterns).

The key rule: **interaction state references data state by key, never by index or direct object reference.** Keys survive sorting, filtering, and data updates. Indices don't.

```js
// Good: interaction state holds keys
const selected = new Set(["item-42", "item-17"]);

// Bad: interaction state holds indices or object refs
const selected = [data[42], data[17]]; // breaks on sort/filter
```

### The Dirty Flag

When interaction state changes, mark the affected layers dirty and coalesce into one `requestAnimationFrame`:

```js
let dirtyLayers = 0;
const LAYER_DATA = 1, LAYER_HIGHLIGHT = 2, LAYER_AXES = 4;

function markDirty(layers) {
  dirtyLayers |= layers;
  if (dirtyLayers) requestAnimationFrame(flush);
}
function flush() {
  if (dirtyLayers & LAYER_DATA) drawData(dataCtx, data, scales);
  if (dirtyLayers & LAYER_HIGHLIGHT) drawHighlight(hlCtx, selected, scales);
  if (dirtyLayers & LAYER_AXES) updateAxes(g, scales);
  dirtyLayers = 0;
}

// Brush changes selection → only highlight layer needs redraw
selection.on("change", () => markDirty(LAYER_HIGHLIGHT));

// Zoom changes scales → data + highlight + axes all need redraw
zoom.on("zoom", () => markDirty(LAYER_DATA | LAYER_HIGHLIGHT | LAYER_AXES));
```

This avoids redundant redraws when multiple state changes fire in the same frame, and avoids redrawing layers that haven't changed.

## Performance Budgets

Each skill has a cost. Composing them multiplies costs because interactions trigger cascading updates.

### The 16.6ms Frame Budget

A brush event fires → filter 10K rows → re-bin histogram → redraw Canvas scatter → redraw Canvas histogram → update axes. Here's what that costs:

| Step | Cost | Skill |
|------|------|-------|
| Brush event handler | ~0.5ms | brushing-and-selection |
| Filter 10K rows (predicate) | ~1ms | linked-views |
| Re-bin histogram (d3.bin) | ~0.5ms | axes-and-scales |
| Canvas scatter redraw (10K points) | ~3ms | canvas-rendering |
| Canvas histogram redraw (20 bars) | ~0.5ms | canvas-rendering |
| SVG axis transition | ~1ms | axes-and-scales |
| Quadtree rebuild | ~2ms | canvas-rendering |
| **Total** | **~8.5ms** | |

8.5ms leaves headroom within 16.6ms. But double the data to 50K and the filter + scatter redraw alone exceed the budget.

### When the Budget is Exceeded

Strategies in order of preference:

1. **Split cheap and expensive updates.** Highlight the brushed points immediately (fast — just redraw the highlight layer). Debounce the histogram re-bin and axis rescale to fire 16ms after the last brush event.

2. **Progressive rendering for the data layer.** Use `createRenderQueue` from `canvas-rendering`. The highlight layer still redraws fully and immediately.

3. **Skip transitions during continuous interaction.** Axis transitions during brush drag feel sluggish. Apply transitions only on brush `end`.

4. **Offload filtering to a Web Worker.** The filter predicate runs on the worker; main thread receives the result and redraws. See `canvas-rendering` for the worker + typed array transfer pattern.

5. **Use bitmap indexing.** For 100K+ rows with multiple filter dimensions, `BitFilter` from `linked-views` reduces filter time from O(n × dimensions) to O(n/32 × dimensions) via bitwise AND on Uint32Arrays.

### Profiling Recipe

Wrap each skill's render function with `performance.mark` / `performance.measure`:

```js
function profiledDraw(name, fn) {
  return (...args) => {
    performance.mark(`${name}-start`);
    fn(...args);
    performance.mark(`${name}-end`);
    performance.measure(name, `${name}-start`, `${name}-end`);
  };
}

const drawScatter = profiledDraw("scatter", _drawScatter);
const drawHistogram = profiledDraw("histogram", _drawHistogram);
// Read results: performance.getEntriesByType("measure")
```

## Composition Archetypes

Most composed visualizations fall into one of five architectural patterns. Recognizing the archetype tells you which skills apply and how they wire.

### The Explorer

**Skills:** `canvas-rendering` + `brushing-and-selection` + `linked-views` + `axes-and-scales` + `zoom-and-pan`

Multiple views of one dataset, all linked. Brush in any view, all others filter. Parallel coordinates is the prototypical explorer.

**State flow:** Shared `SelectionModel`. Each view subscribes, skips own events. Canvas for data density, SVG for interaction.

**Key challenge:** Performance. Every brush frame triggers N view updates. Use the dirty-flag pattern with layer-level granularity.

### The Narrative

**Skills:** `animated-transitions` + `annotations-and-labels` + `responsive-charts` + `color-themes`

A sequence of states driven by scroll or step buttons. Each state changes the data subset, scale domain, annotation set, or chart type. Transitions communicate what changed.

**State flow:** Linear state machine. Current step index drives everything. No user-driven filtering — the author controls the path.

**Key challenge:** Transition choreography. Exit old annotations → update scales → enter new data → enter new annotations, all sequenced with delays. See `animated-transitions` for staged transition patterns.

### The Dashboard

**Skills:** `responsive-charts` + `linked-views` + `axes-and-scales` + `color-themes` + `fallback-table`

CSS Grid of independent charts sharing a dataset and color scale. Filters at the top drive all views.

**State flow:** `createStore` with filter predicates. Each chart reads `getFiltered()` and re-renders. See `linked-views`.

**Key challenge:** Responsive layout. Charts must resize independently as the grid reflows. Each chart owns its own `ResizeObserver`. Shared scales (especially color) must not change domain during filtering — use the full data domain.

### The Spatial Explorer

**Skills:** `geographic-maps` + `zoom-and-pan` + `canvas-rendering` + `brushing-and-selection` + `annotations-and-labels`

A map with overlaid data, zoom-driven LOD, tooltips, and linked summary panels.

**State flow:** Zoom transform drives LOD and culling. Brush on data triggers summary. The map projection is a scale — it transforms data coordinates to screen coordinates, just like `d3.scaleLinear`.

**Key challenge:** Coordinate systems. Geographic projection, Canvas DPR, SVG viewBox, and zoom transform all compose. Getting one wrong offsets everything.

### The Layout Morpher

**Skills:** `hierarchy-layouts` + `shape-morphing` + `animated-transitions` + `hierarchy-interaction`

Switch between layout algorithms (treemap → sunburst → pack) with smooth transitions. Nodes maintain identity across layouts.

**State flow:** Layout type selector triggers layout recomputation. Position interpolation drives the animation. Key function preserves identity across layouts.

**Key challenge:** Shape interpolation. A rectangle (treemap cell) morphing to an arc (sunburst wedge) requires point resampling. See `shape-morphing` for the `resamplePath` + `bestRotation` pattern.

## The Resize Contract

Every composed visualization must handle resize. Resize interacts with every skill, and each skill has specific resize obligations:

| Skill | On Resize |
|-------|-----------|
| `canvas-rendering` | Resize backing store (`canvas.width = w * dpr`), re-apply DPR scale, clear and redraw |
| `axes-and-scales` | Recompute scale ranges, re-call axis generators |
| `brushing-and-selection` | Update brush extent, clear or re-map existing brush selection |
| `zoom-and-pan` | Recompute `translateExtent`, preserve current viewport center |
| `force-simulation` | Update center force target, reheat simulation |
| `canvas-rendering` (quadtree) | Rebuild — spatial index is in pixel coordinates |
| `annotations-and-labels` | Recompute positions, re-check collision |
| `canvas-accessibility` | Update hidden DOM positions, resize focus ring |

The resize cascade: container measurement → Canvas resize → scale rebuild → layout recompute → redraw → interaction rebind.

### Debouncing

Canvas-only views: 0ms debounce (redraw is cheap, instant feedback).
Canvas+SVG hybrid: 100ms debounce (SVG DOM manipulation is expensive in aggregate).
Full dashboard: 150ms debounce (multiple charts resizing simultaneously).

```js
let resizeTimer;
const ro = new ResizeObserver(entries => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const { width, height } = entries[0].contentRect;
    render(width, height);
  }, 100);
});
```

### Preserving Interaction State Across Resize

Brush extents are in pixel coordinates. When scales change on resize, the brush selection becomes stale. Re-map it:

```js
function remapBrush(brushG, brush, oldX, newX) {
  const sel = d3.brushSelection(brushG.node());
  if (!sel) return;
  // Convert pixel extent to data extent using OLD scale, then back to pixels with NEW scale
  const [d0, d1] = sel.map(oldX.invert);
  brushG.call(brush.move, [newX(d0), newX(d1)]);
}
```

## Common Composition Pitfalls

1. **Scales built before container measured.** `d3.scaleLinear().range([0, width])` where `width` is 0 because the container hasn't rendered yet. Fix: measure inside `ResizeObserver` or after `requestAnimationFrame`.

2. **Canvas and SVG coordinate mismatch.** Canvas origin at (0,0) but SVG content offset by margin. Fix: `ctx.translate(margin.left, margin.top)` once after canvas setup, so both coordinate systems align.

3. **Zoom transform applied to wrong layer.** Canvas uses `ctx.translate(t.x, t.y); ctx.scale(t.k, t.k)`. SVG uses `attr("transform", ...)`. Mixing them up causes double-offset. Fix: apply zoom to the Canvas context in the draw function, and to the SVG group in the zoom handler.

4. **Selection manager fires during initialization.** Chart A sets a default selection during setup, which triggers chart B's listener before chart B has finished initializing. Fix: defer interaction binding to after all charts are rendered (step 8 in the pipeline), or guard listeners with an `initialized` flag.

5. **Resize destroys brush state.** Scale ranges change, brush pixel extent becomes invalid. Fix: convert to data coordinates before resize, convert back after (see `remapBrush` above).

6. **Theme change doesn't reach Canvas.** CSS custom properties auto-update SVG via stylesheets, but Canvas must explicitly re-read `getComputedStyle` values and redraw. Fix: listen for theme change events and call `markDirty(LAYER_DATA | LAYER_HIGHLIGHT)`.

7. **Progressive render interrupted by interaction.** User brushes while the render queue is mid-flight. Stale queued frames overwrite the fresh highlight. Fix: cancel the render queue on any interaction event, redraw immediately with the new state.

8. **Accessibility tree stale after filter.** Hidden DOM mirror built at initialization but never updated when brush/filter changes the visible data. Fix: update the mirror in the same `flush()` that redraws Canvas.

9. **Quadtree stale after zoom.** Quadtree built in data coordinates, but zoom changes which data coordinates map to which pixels. If hit detection uses pixel coordinates, rebuild the quadtree with zoomed positions. Alternative: transform the mouse coordinates inversely instead of rebuilding the quadtree.

10. **Too many layers.** Five canvases + two SVGs + three HTML divs. Each layer has a memory cost (canvas backing store at 4 bytes/pixel × DPR²). A 1200×800 canvas at 2× DPR costs 7.7MB. Five of them: 38MB. Fix: merge layers that always redraw together. Separate only layers with different update frequencies.

## References

- [A Layered Grammar of Graphics](https://doi.org/10.1198/jcgs.2009.07098) — Wickham. The theoretical foundation for thinking about visualization as composed layers.
- [Visualization Analysis and Design, Ch. 12-13](https://www.cs.ubc.ca/~tmm/vadbook/) — Munzner. Multi-view design taxonomy: juxtapose, superimpose, small multiples.
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — The canonical real-world composition: Canvas+SVG hybrid, brushing, axis reordering, linked views, progressive rendering.
- [Crossfilter](https://square.github.io/crossfilter/) — The reference for fast multi-dimensional filtering across composed views.
- [Responsive D3](https://observablehq.com/@d3/responsive-d3) — Container-based sizing for composed layouts.
