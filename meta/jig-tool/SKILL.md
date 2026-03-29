---
name: jig-tool
description: "Architectural patterns for combining multiple D3 skills into one visualization — the jig that holds pieces in alignment. Trigger: 'jig', 'compose', 'combine skills', 'layer stack', 'multi-view architecture'. Use when layering Canvas+SVG, coordinating linked views, sequencing initialization, managing shared state, budgeting performance across composed concerns, or deciding SVG vs Canvas tradeoffs."
---

# Jig Tool

A single chart shows one relationship. Composition lets the viewer hold multiple relationships in mind at once — brush a scatterplot and watch a histogram reshape, revealing that high-revenue companies cluster in one industry. The architecture exists to make that moment of connection feel instant and seamless. When the glue is wrong, latency breaks the cognitive link and the viewer sees two charts instead of one insight.

## The Layer Stack

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

Collapse based on complexity:

| Scenario | Layers |
|----------|--------|
| <500 elements, full interaction | SVG only |
| 500–50K elements, brush/hover | Canvas data + SVG overlay |
| 50K+ with selection highlighting | Canvas data + Canvas highlight + SVG overlay |
| Hit detection on lines/paths | Add hidden hit canvas |
| Controls, legend, or data table | Add HTML layer |

All layers share identical coordinate systems. Container `position: relative`; children `position: absolute`. Key: `ctx.translate(margin.left, margin.top)` once so Canvas matches SVG's `g` transform.

## SVG vs Canvas Decision

| | Few updates | Continuous updates (animation, drag) |
|---|---|---|
| **<500 elements** | SVG | SVG |
| **500–5K** | SVG or Canvas | Canvas |
| **5K–100K** | Canvas | Canvas + render queue |
| **100K+** | Canvas + typed arrays | WebGL |

Element count isn't the only factor — 2K SVG circles with drag-to-reorder stutter (reflow per frame), force sims need Canvas even at 300 nodes, and 500 complex geo paths are slower in SVG than 5K circles.

**Hybrid pattern:** Canvas for data marks, SVG for interaction chrome (axes, brushes, focus rings, tooltips). Not a compromise — the optimal architecture for high counts with full accessibility.

**Handoff pattern:** Animate in Canvas (smooth 60fps), render final state in SVG (interactive, accessible). For layout transitions where motion needs Canvas but resting state needs interactivity.

## Initialization Sequence

```
1. Data load + clean        (data-gathering)
2. Container measure        (responsive)
3. Layer stack create       (canvas + this skill)
4. Scales construct         (scales)
5. Layout compute           (hierarchy-layouts, force, d3.bin)
6. Static chrome render     (axes, gridlines, legends)
7. Data render              (marks on Canvas or SVG)
8. Interaction bind         (brushes, zoom, drag, tooltips)
9. Accessibility setup      (canvas-accessibility, data-table)
10. Theme apply             (color)
```

This ordering prevents: scales with width=0 (measure before build), silent no-op event listeners (bind after render), and cascade during setup (interactions after all views init). Wrap steps 4–10 in `render(width, height)` — resize, data change, and theme change all call it.

**What re-runs:** Resize → steps 3–10. Data change → 1, 4–10 (scales need new domains). Theme change → 7, 10 only (Canvas re-reads CSS; SVG auto-updates via classes).

## State Architecture

Three kinds — mixing them causes bugs.

**Data State** — raw dataset, cleaned. Never mutated by interaction. `Object.freeze(data)`.

**View State** — scales, layout positions, bin boundaries. Derived from data + dimensions. Recomputed on resize/data change.

**Interaction State** — selection sets, brush extents, zoom transforms, hover targets. Flows between skills via `d3.dispatch` or `createStore` (see `linked-views`).

**Key rule:** Interaction state references data by **key**, never by index or object reference. Keys survive sorting, filtering, data updates.

### The Dirty Flag

Coalesce layer redraws into one `requestAnimationFrame`:

```js
let dirty = 0;
const DATA = 1, HIGHLIGHT = 2, AXES = 4;

function markDirty(layers) {
  dirty |= layers;
  requestAnimationFrame(flush);
}
function flush() {
  if (dirty & DATA) drawData(dataCtx, data, scales);
  if (dirty & HIGHLIGHT) drawHighlight(hlCtx, selected, scales);
  if (dirty & AXES) updateAxes(g, scales);
  dirty = 0;
}

selection.on("change", () => markDirty(HIGHLIGHT));
zoom.on("zoom", () => markDirty(DATA | HIGHLIGHT | AXES));
```

Without this, a brush event updating three views triggers three RAF calls in the same frame with stale intermediate states.

## Performance Budgets

### When the 16.6ms Frame Budget Is Exceeded

1. **Split cheap/expensive.** Highlight immediately; debounce histogram rebin 16ms later.
2. **Progressive rendering** for data layer (`canvas` `createRenderQueue`).
3. **Skip transitions during continuous interaction.** Apply only on brush `end`.
4. **Offload filtering to Worker** — see `canvas` for transfer pattern.
5. **Bitmap indexing** — `BitFilter` from `linked-views` for 100K+ rows.

## Composition Archetypes

**Explorer** — Multiple linked views; brush one, all respond. Insight from cross-view correlation. Challenge: N view updates per brush frame; dirty-flag keeps it under 16.6ms.

**Narrative** — Scroll/step-driven sequence; transitions show data transforming under different lenses. Challenge: choreographing exit→update→enter across annotations, scales, and data.

**Dashboard** — CSS Grid of charts sharing dataset and color scale, each answering a different question. Challenge: per-chart `ResizeObserver`; shared color scale must use full-data domain or colors shift on filter.

**Spatial Explorer** — Map + overlaid data + zoom LOD + linked panels. Challenge: projection, DPR, viewBox, zoom transform all compose and must agree.

**Layout Morpher** — Switch layout algorithms with smooth transitions preserving object constancy. Challenge: shape interpolation requires point resampling (see `shape-morphing`).

## When Not to Compose

Composition adds complexity that compounds (resize, state sync, init ordering, memory). Don't pay that cost without a viewer benefit.

- **Single question, single chart.** If one scatterplot answers the question, a linked histogram just adds cognitive load.
- **Linked views with no cross-view insight.** Two views of the same dimension give the viewer two places to look but nothing new. Link views showing *different* dimensions.
- **Dashboards beyond 6–8 panels.** The viewer can't track which panels responded to a filter. If scrolling is needed, the "at a glance" benefit is gone.

## The Resize Contract

| Skill | On Resize |
|-------|-----------|
| `canvas` | Resize backing store (`canvas.width = w * dpr`), re-apply DPR, clear, redraw |
| `scales` | Recompute scale ranges, re-call generators |
| `brushing` | Update extent, clear or re-map existing selection |
| `navigation` | Recompute `translateExtent`, preserve viewport center |
| `force` | Update center force, reheat |
| quadtree | Rebuild — spatial index is in pixel coordinates |
| `annotation` | Recompute positions, re-check collision |
| `canvas-accessibility` | Update hidden DOM positions, resize focus ring |

Debounce: Canvas-only 0ms, Canvas+SVG hybrid 100ms, full dashboard 150ms.

Brush extents are pixel coordinates — stale after resize. Re-map:

```js
function remapBrush(brushG, brush, oldX, newX) {
  const sel = d3.brushSelection(brushG.node());
  if (!sel) return;
  brushG.call(brush.move, sel.map(oldX.invert).map(d => newX(d)));
}
```

## Common Composition Pitfalls

1. **Scales built before container measured.** `range([0, 0])`. Fix: measure in `ResizeObserver` or after RAF.
2. **Canvas/SVG coordinate mismatch.** Fix: `ctx.translate(margin.left, margin.top)` once.
3. **Zoom transform on wrong layer.** Canvas vs SVG transform APIs differ; mixing = double-offset.
4. **Selection manager fires during init.** Fix: defer interaction binding to step 8 or guard with `initialized` flag.
5. **Resize destroys brush state.** Fix: convert to data coords before resize, back after (see `remapBrush`).
6. **Theme change doesn't reach Canvas.** CSS auto-updates SVG; Canvas must re-read `getComputedStyle` and redraw.
7. **Progressive render interrupted by interaction.** Fix: cancel render queue on interaction, redraw immediately.
8. **Accessibility tree stale after filter.** Fix: update hidden DOM in same `flush()` that redraws Canvas.
9. **Quadtree stale after zoom.** Fix: rebuild with zoomed positions or inverse-transform mouse coords.
10. **Too many layers.** Each 2× DPR canvas at 1200×800 ≈ 7.7MB. Five = 38MB. Merge layers that always redraw together.

## References

- [A Layered Grammar of Graphics](https://doi.org/10.1198/jcgs.2009.07098) — Wickham
- [Visualization Analysis and Design, Ch. 12-13](https://www.cs.ubc.ca/~tmm/vadbook/) — Munzner
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — canonical Canvas+SVG hybrid
- [Crossfilter](https://square.github.io/crossfilter/) — fast multi-dimensional filtering
- [Multi-View Composition](https://idl.uw.edu/visualization-curriculum/altair_view_composition.html) — UW IDL Visualization Curriculum
