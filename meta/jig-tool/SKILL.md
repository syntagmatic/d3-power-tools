---
name: jig-tool
description: "Architectural patterns for combining multiple D3 visualization skills into a single application. Use this skill when building any non-trivial visualization that layers Canvas rendering with SVG interaction, coordinates multiple views, sequences initialization, manages shared state, or needs a performance budget across composed concerns. Also use when the user asks about SVG vs Canvas tradeoffs, layer stacking, resize handling across mixed renderers, or how to wire brushing/zoom/animation/accessibility together in one visualization."
---

# Cross-Skill Composition

A single chart shows one relationship. Composition lets the viewer hold multiple relationships in mind at once — brush a scatterplot and watch a histogram reshape, revealing that high-revenue companies cluster in one industry. The architecture exists to make that moment of connection feel instant and seamless. When the glue is wrong, latency breaks the cognitive link between views and the viewer sees two charts instead of one insight.

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

All layers share identical coordinate systems. Container is `position: relative`; children `position: absolute`. Key detail: `ctx.translate(margin.left, margin.top)` once after setup so Canvas coordinates match SVG's `g` transform.

## SVG vs Canvas Decision

| | Few updates | Continuous updates (animation, drag) |
|---|---|---|
| **<500 elements** | SVG | SVG |
| **500–5K** | SVG or Canvas | Canvas |
| **5K–100K** | Canvas | Canvas + render queue |
| **100K+** | Canvas + typed arrays | WebGL |

But element count is only one factor:
- **Interaction type**: 2K SVG circles with hover = fine. 2K with drag-to-reorder = stutter (reflow per frame).
- **Update frequency**: Force simulation at 300 nodes redraws 60×/sec — Canvas even at low counts.
- **Shape complexity**: 500 complex paths (geo boundaries) slower in SVG than 5000 circles.

### The Hybrid Pattern

**Canvas for data marks, SVG for interaction chrome.** Not a compromise — the optimal architecture. Canvas renders per-datum marks; SVG renders axes, brushes, focus rings, tooltips. The viewer gets smooth interaction at high element counts without losing the browser's built-in accessibility and event handling for chrome elements.

### The Handoff Pattern

1. **Animate in Canvas** — smooth 60fps morphing
2. **On end, render final state in SVG** — interactive, accessible

Useful for layout transitions where animation needs Canvas but resting state needs SVG interactivity. The viewer experiences fluid motion, then lands in a state where every element is clickable and screen-reader-visible.

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

The ordering prevents three real bugs: scales built before container measurement (width=0), interactions bound before elements exist (silent no-ops), and selection managers firing before all views initialize (cascade during setup). Wrap steps 4-10 in `render(width, height)` — resize, data change, and theme change all call it.

### What Re-Runs When

| Trigger | Steps |
|---------|-------|
| Resize | 3-10 (layer stack resizes, scales recompute, everything redraws) |
| Data change | 1, 4-10 (scales may need new domains) |
| Theme change | 7, 10 only (Canvas re-reads CSS properties; SVG auto-updates if using CSS classes) |

## State Architecture

Three kinds of state. Mixing them causes bugs.

**Data State** — raw dataset, cleaned. Never mutated by interaction. `Object.freeze(data)`.

**View State** — scales, layout positions, bin boundaries. Derived from data + dimensions. Recomputed on resize/data change.

**Interaction State** — selection sets, brush extents, zoom transforms, hover targets. Flows between skills via `d3.dispatch` or `createStore` (see `linked-views`).

**Key rule:** Interaction state references data by **key**, never by index or object reference. Keys survive sorting, filtering, data updates. Indices don't.

### The Dirty Flag

Coalesce layer redraws into one `requestAnimationFrame`:

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

// Brush → only highlight redraws
selection.on("change", () => markDirty(LAYER_HIGHLIGHT));
// Zoom → all layers redraw
zoom.on("zoom", () => markDirty(LAYER_DATA | LAYER_HIGHLIGHT | LAYER_AXES));
```

Without this, a brush event that updates three views triggers three separate `requestAnimationFrame` calls that all run in the same frame anyway — but with stale intermediate states visible between them.

## Performance Budgets

### The 16.6ms Frame Budget

Example: brush event on 10K rows:

| Step | Cost | Skill |
|------|------|-------|
| Brush event handler | ~0.5ms | brushing |
| Filter 10K rows | ~1ms | linked-views |
| Re-bin histogram | ~0.5ms | scales |
| Canvas scatter redraw (10K) | ~3ms | canvas |
| Canvas histogram (20 bars) | ~0.5ms | canvas |
| SVG axis transition | ~1ms | scales |
| Quadtree rebuild | ~2ms | canvas |
| **Total** | **~8.5ms** | |

### When Exceeded

1. **Split cheap/expensive.** Highlight immediately; debounce histogram rebin 16ms after last brush event. The viewer sees instant feedback on the primary view while secondary views catch up imperceptibly.
2. **Progressive rendering** for data layer (see `canvas` `createRenderQueue`).
3. **Skip transitions during continuous interaction.** Apply only on brush `end`. Transitions during dragging compound with the next frame's work.
4. **Offload filtering to Worker** — see `canvas` for transfer pattern.
5. **Bitmap indexing** — `BitFilter` from `linked-views` for 100K+ rows.

## Composition Archetypes

### The Explorer

**Viewer experience:** "I can ask questions by selecting, and every view answers simultaneously." The viewer brushes a scatterplot and sees a histogram reshape, a table re-sort, a map re-shade — all within the same frame. The insight comes from cross-view correlation: patterns invisible in any single view become obvious when views respond together.

Multiple views of one dataset, all linked. Shared `SelectionModel`, each view subscribes, skips own events. Canvas data + SVG interaction. Key challenge: every brush frame triggers N view updates — dirty-flag with layer granularity keeps it under 16.6ms.

**When it works:** Multivariate data where the viewer needs to find which dimensions correlate. Three to four linked views is the sweet spot — beyond that, the viewer can't track all responses to a single brush action.

### The Narrative

**Viewer experience:** "The data reveals itself in a guided sequence, each step building on the last." The viewer scrolls or clicks through stages, and transitions show how the same data transforms under different lenses. The power is in the *transition* — watching bars sort, scales shift, and annotations appear tells a story that a static sequence of charts cannot.

Scroll/step-driven sequence. Linear state machine. Key challenge: transition choreography — exit annotations, update scales, enter data, enter annotations, sequenced with delays.

**When it works:** When you have a specific argument to make and the viewer's exploration would be unproductive without guidance. Falls apart when the argument requires the viewer to compare non-adjacent steps — they can't scroll to two places at once.

### The Dashboard

**Viewer experience:** "I see all KPIs at a glance and can drill into any one." Each chart answers a different question; filtering one filters all. The viewer builds context from the ensemble, not from any single panel.

CSS Grid of charts sharing dataset and color scale. `createStore` with filter predicates. Key challenge: responsive layout with per-chart `ResizeObserver`. Shared color scale must use full-data domain (not filtered), or colors shift meaning when filters change.

**When it works:** Monitoring and operational contexts where the viewer returns repeatedly and knows what each panel means. Fails as an analytical tool — too many panels compete for attention and none gets deep enough to reveal structure.

### The Spatial Explorer

**Viewer experience:** "I can see where things happen and what they look like up close." Zoom reveals detail; linked panels show attributes of the visible region. The map provides spatial context that no other layout can.

Map + overlaid data + zoom LOD + linked panels. Projection = scale (data-to-screen transform). Key challenge: coordinate system composition — projection, DPR, viewBox, zoom transform all compose and all must agree.

**When it works:** Data with meaningful geographic or spatial coordinates. If location is incidental (company headquarters on a map of revenue data), a scatterplot is almost always better.

### The Layout Morpher

**Viewer experience:** "I can see the same data reorganize itself, revealing different structure each time." Switching from treemap to sunburst preserves object constancy — the viewer tracks individual nodes through the transition and understands that depth emphasis has replaced size emphasis.

Switch layout algorithms with smooth transitions. Key challenge: shape interpolation (rect-to-arc requires point resampling — see `shape-morphing`).

**When it works:** When two layouts reveal genuinely different aspects of the same hierarchy. If the viewer learns nothing new from the second layout, the transition is decoration.

## When Not to Compose

Composition adds complexity that compounds: resize handling, state synchronization, initialization ordering, memory from multiple canvases. Don't pay that cost without a viewer benefit.

- **Single question, single chart.** If one scatterplot answers the question, adding a linked histogram just adds cognitive load. The viewer's eye has to travel between panels, and the connection between them may not be worth the effort.
- **Linked views with no cross-view insight.** Two views of the same dimension (a bar chart and a table of the same column) give the viewer two places to look but nothing new to see. Link views that show *different* dimensions so brushing one reveals a pattern in the other.
- **Dashboards with more than 6-8 panels.** Beyond this, the viewer cannot track which panels responded to a filter action. Each additional panel dilutes attention. If the viewer has to scroll to see all panels, the "at a glance" benefit is gone.
- **Narrative with no transitions.** If each step is a completely new chart with no shared elements, scrollytelling adds complexity (state machine, scroll observer, transition choreography) for a slideshow that would work as static images.
- **Morphing between unrelated layouts.** Animating from a bar chart to a map preserves no object constancy and teaches the viewer nothing — it just looks like the screen is melting.

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

### Debouncing

Canvas-only: 0ms (redraw is cheap). Canvas+SVG hybrid: 100ms. Full dashboard: 150ms. The tradeoff: shorter debounce = more responsive resize, but SVG reflows during intermediate sizes are wasted work.

### Preserving Interaction State

Brush extents are pixel coordinates — stale after resize. Re-map:

```js
function remapBrush(brushG, brush, oldX, newX) {
  const sel = d3.brushSelection(brushG.node());
  if (!sel) return;
  const [d0, d1] = sel.map(oldX.invert);
  brushG.call(brush.move, [newX(d0), newX(d1)]);
}
```

## Common Composition Pitfalls

1. **Scales built before container measured.** `range([0, width])` where width=0. Fix: measure inside `ResizeObserver` or after `requestAnimationFrame`.

2. **Canvas/SVG coordinate mismatch.** Canvas origin at (0,0) but SVG offset by margin. Fix: `ctx.translate(margin.left, margin.top)` once.

3. **Zoom transform on wrong layer.** Canvas: `ctx.translate(t.x, t.y); ctx.scale(t.k, t.k)`. SVG: `attr("transform")`. Mixing = double-offset.

4. **Selection manager fires during init.** Chart A sets default selection → triggers chart B's listener before B finishes init. Fix: defer interaction binding to step 8, or guard with `initialized` flag.

5. **Resize destroys brush state.** Scale ranges change, pixel extent invalid. Fix: convert to data coords before, back after (see `remapBrush`).

6. **Theme change doesn't reach Canvas.** CSS auto-updates SVG, but Canvas must re-read `getComputedStyle` and redraw.

7. **Progressive render interrupted by interaction.** Stale queued frames overwrite fresh highlight. Fix: cancel render queue on interaction, redraw immediately.

8. **Accessibility tree stale after filter.** Hidden DOM mirror built at init but never updated. Fix: update in same `flush()` that redraws Canvas.

9. **Quadtree stale after zoom.** Built in data coords but hit detection uses pixel coords. Either rebuild with zoomed positions or inverse-transform mouse coords.

10. **Too many layers.** Each canvas at 2× DPR costs ~7.7MB (1200×800). Five = 38MB. Merge layers that always redraw together.

## References

- [A Layered Grammar of Graphics](https://doi.org/10.1198/jcgs.2009.07098) — Wickham
- [Visualization Analysis and Design, Ch. 12-13](https://www.cs.ubc.ca/~tmm/vadbook/) — Munzner
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — canonical Canvas+SVG hybrid
- [Crossfilter](https://square.github.io/crossfilter/) — fast multi-dimensional filtering
- [Multi-View Composition](https://idl.uw.edu/visualization-curriculum/altair_view_composition.html) — UW IDL Visualization Curriculum
