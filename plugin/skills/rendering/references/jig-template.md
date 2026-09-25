# Jig template (multi-view composition)

Absorbed from the v2 `jig-template` meta skill. Open when combining several views or skills into one piece: a layer stack, linked views, a dashboard, a map with panels.

Composition lets the viewer hold two relationships at once: brush a scatterplot, watch a histogram reshape. When the glue lags, the viewer sees two charts instead of one insight.

## Layer stack

Container `position: relative`; every layer `position: absolute`, same size, same coordinates. From top: HTML (controls, legend) → SVG overlay (axes, brush, focus; takes pointer events) → highlight canvas → data canvas → hidden hit canvas (never displayed).

| Scenario | Layers |
|---|---|
| < 500 elements, full interaction | SVG only |
| 500-50K, brush/hover | data canvas + SVG overlay |
| 50K+ with selection highlight | data canvas + highlight canvas + SVG |
| hit testing lines/paths | + hidden hit canvas |
| controls, legend, table | + HTML |

`ctx.translate(margin.left, margin.top)` once so canvas coordinates match the SVG `g`.

**Handoff:** animate on Canvas, then render the resting state in SVG for interaction and accessibility.

## Initialization order

1. load and clean data
2. measure container
3. create layers
4. build scales
5. compute layout
6. static chrome (axes, grid, legend)
7. data marks
8. bind interactions
9. accessibility layer
10. apply theme

Measure before scales (else `range([0, 0])`); bind after all views exist (else a selection manager fires into views that aren't there). Wrap 4-10 in `render(width, height)`. Resize re-runs 3-10; data change 1 and 4-10; theme change 7 and 10 (Canvas re-reads `getComputedStyle`; SVG follows CSS).

## State

- **Data**: cleaned, never mutated by interaction. `Object.freeze`.
- **View**: scales, layout positions, bins. Derived from data + size.
- **Interaction**: selections, brush extents, zoom transforms, hover. Shared via `d3.dispatch` or a small store. References data **by key**, never index or object reference, so it survives sort, filter, and reload.

Dirty bits coalesce many events into one draw per frame:

```js
const DATA = 1, HIGHLIGHT = 2, AXES = 4;
let dirty = 0;
function markDirty(layers) {
  if (!dirty) requestAnimationFrame(flush);
  dirty |= layers;
}
function flush() {
  const d = dirty; dirty = 0;
  if (d & DATA) drawData();
  if (d & HIGHLIGHT) drawHighlight();
  if (d & AXES) updateAxes();
}
```

## Over budget (16.6ms)

1. Split cheap from expensive: highlight now, rebin a frame later.
2. Progressive rendering for the data layer.
3. No transitions during continuous interaction; apply on brush `end`.
4. Filter in a Worker.
5. Bitmap indexing for 100K+ rows (see the linked-views material).

## Archetypes

| Archetype | Challenge |
|---|---|
| Explorer (linked views) | N view updates per brush frame; dirty bits keep it in budget |
| Narrative (scroll/step) | choreographing exit → update → enter across marks, scales, annotations |
| Dashboard (grid) | per-chart observers; a shared color scale must use the full-data domain or colors shift on filter |
| Spatial explorer (map + panels) | projection, DPR, viewBox, and zoom transform must all agree |
| Layout morpher | object constancy across layouts; shapes need point resampling |

Don't compose when one chart answers the question, when two views show the same dimension, or past 6-8 dashboard panels (nobody can track which responded).

## Resize contract

| Part | On resize |
|---|---|
| canvas | reset backing store, re-apply DPR, redraw |
| scales | new ranges, re-call axes and generators |
| brush | update extent, re-map the selection through data space |
| zoom | recompute `translateExtent`, keep the viewport center |
| force | move the center force, reheat |
| quadtree | rebuild (it's in pixels) |
| annotations | recompute positions and collisions |
| a11y mirror | move hidden DOM, resize focus ring |

```js
function remapBrush(brushG, brush, oldX, newX) {
  const sel = d3.brushSelection(brushG.node());
  if (sel) brushG.call(brush.move, sel.map(v => newX(oldX.invert(v))));
}
```

## Pitfalls

- Zoom applied to the wrong layer: Canvas and SVG transforms differ, and mixing them double-offsets.
- Theme change doesn't reach Canvas until it re-reads CSS and redraws.
- A progressive render keeps drawing stale data after interaction. Cancel it.
- Hidden accessibility DOM goes stale after a filter. Update it in the same `flush()`.
- Quadtree stale after zoom: rebuild, or inverse-transform the pointer.
- Memory: a 1200×800 canvas at 2× DPR is 2400×1600×4 bytes ≈ 15MB. Five layers ≈ 77MB. Merge layers that always redraw together.
