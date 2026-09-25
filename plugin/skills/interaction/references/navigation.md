# Navigation: zoom and pan

Absorbed from the v2 `navigation` skill. Open when a chart needs d3-zoom: geometric vs semantic zoom, Canvas zoom, constraints, zoom-to-fit, minimap, brush-to-zoom, linked zoom, level of detail, or touch.

Most charts shouldn't zoom. Add it when the data has detail across scales: more points than pixels, clusters inside clusters, years of data where days matter, maps, networks with hundreds of nodes. Skip it when the chart reads at default scale, when the task is comparing everything at once (zoom hides context), when small multiples or a filter would answer the question, or when wheel capture would hijack page scroll.

## Geometric vs semantic

| | Geometric | Semantic |
|---|---|---|
| Mechanism | `g.attr("transform", transform)` | `zx = transform.rescaleX(x)`, reposition marks |
| Text and strokes | grow with k; counter-scale (`r = 4 / k`, `font-size = 12 / k`) | stay constant |
| Axes | don't update | re-render from `zx`, `zy` |
| Use for | maps, floor plans, node-link | anything with data axes |

`vector-effect: non-scaling-stroke` fixes stroke width only, not `r`, `font-size`, or `stroke-dasharray`.

```js
function zoomed({ transform }) {
  const zx = transform.rescaleX(x), zy = transform.rescaleY(y);   // always the ORIGINAL x, y
  xAxisG.call(d3.axisBottom(zx));
  yAxisG.call(d3.axisLeft(zy));
  dots.attr("cx", d => zx(d.x)).attr("cy", d => zy(d.y));
}
```

X-only zoom: use `rescaleX` and ignore `transform.y`.

## Canvas zoom

Attach the zoom to an SVG overlay (a transparent `rect` with `pointer-events: all`) stacked over the canvas; the SVG also draws crisp axes. On each (rAF-coalesced) zoom, clear and redraw only points inside `zx.domain()` × `zy.domain()`; past ~10K points enumerate them with `quadtree.visit()` instead of scanning. For geometric canvas zoom, `ctx.save(); ctx.translate(t.x, t.y); ctx.scale(t.k, t.k)`, draw, `ctx.restore()`, and draw axes outside the transform.

## Constraints

Set all three on any chart with margins. `extent` is the viewport that `scaleBy`/`scaleTo` center on and that `translateExtent` is checked against; the default is the whole svg, margins included.

```js
const zoom = d3.zoom()
  .scaleExtent([1, 40])
  .extent([[marginLeft, marginTop], [width - marginRight, height - marginBottom]])
  .translateExtent([[0, 0], [width, height]]);   // pan bounds: data can't leave the frame
```

`scaleExtent([1, ...])` forbids zooming out past the initial view; use 0.5 if the viewer should see more.

## Zoom to fit

```js
function zoomToFit(sel, [[x0, y0], [x1, y1]], pad = 20) {   // bounds in pixels
  const cw = width - marginLeft - marginRight, ch = height - marginTop - marginBottom;
  const k = Math.min((cw - 2 * pad) / (x1 - x0), (ch - 2 * pad) / (y1 - y0));
  sel.transition().duration(750).call(zoom.transform, d3.zoomIdentity
    .translate(marginLeft + cw / 2, marginTop + ch / 2)
    .scale(Math.min(k, zoom.scaleExtent()[1]))
    .translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
}
```

`zoom.transform` does not clamp k to `scaleExtent`; clamp it yourself. Programmatic zoom should almost always animate (500-750ms); d3 interpolates with van Wijk & Nuij's smooth zoom, so distant jumps zoom out, pan, and zoom back in.

## Minimap

Add one when `scaleExtent` allows more than ~5×. Draw the viewport rect from the rescaled domains on a copy of the scales with a small range:

```js
const mx = x.copy().range([0, width * 0.15]), my = y.copy().range([height * 0.15, 0]);
function updateMinimap(t) {
  const [a, b] = t.rescaleX(x).domain(), [c, d] = t.rescaleY(y).domain();
  viewport.attr("x", mx(a)).attr("y", my(d)).attr("width", mx(b) - mx(a)).attr("height", my(c) - my(d));
}
```

Clicking the minimap recenters: keep the current k, `translate(width / 2, height / 2).scale(k).translate(-x(mx.invert(px)), -y(my.invert(py)))`.

## Brush-to-zoom (focus + context)

The context brush sets the focus zoom; the focus zoom moves the context brush. Both directions fire the other's handler synchronously, so guard both. The focus must still redraw when the zoom came from the brush, so don't early-return before the redraw.

```js
let syncing = false;
function brushed({ selection, sourceEvent }) {
  if (syncing || !sourceEvent || !selection) return;
  const [r0, r1] = x.range(), k = (r1 - r0) / (selection[1] - selection[0]);
  syncing = true;
  focus.call(zoom.transform, d3.zoomIdentity.translate(r0 - selection[0] * k, 0).scale(k));
  syncing = false;
}
function zoomed({ transform }) {
  const zx = transform.rescaleX(x);
  redrawFocus(zx);                                   // always
  if (syncing) return;                               // zoom came from brushed
  syncing = true;
  brushG.call(brush.move, zx.domain().map(xContext));
  syncing = false;
}
```

This assumes the focus `x` and `xContext` share a pixel range. The v2 version returned from `zoomed` on any programmatic zoom, so the focus never redrew when brushed; an earlier version guarded on `sourceEvent.type === "brush"`, which is never true for a programmatic zoom and looped.

## Linked zoom

Same guard for two zoomable views: `if (syncing) return; syncing = true; other.call(zoom2.transform, transform); syncing = false;` after updating the local chart. For shared x with independent y, copy only `x` and `k`: `d3.zoomIdentity.translate(t.x, other.y).scale(t.k)` (keep the other chart's own y).

## Level of detail with hysteresis

Density (hexbin) zoomed out, points in the middle, labeled points deep in. A single threshold flickers when k hovers at it; use separate enter and exit thresholds.

```js
const LOD = [
  { name: "density", enterAbove: 0, exitBelow: 0 },
  { name: "points", enterAbove: 2.5, exitBelow: 2.0 },
  { name: "labeled", enterAbove: 8, exitBelow: 6.5 },
];
let lod = 0;
function updateLOD(k) {
  while (lod < LOD.length - 1 && k >= LOD[lod + 1].enterAbove) lod++;
  while (lod > 0 && k < LOD[lod].exitBelow) lod--;
  return LOD[lod].name;
}
```

Widen the band for touch (coarse, fast gestures). Cross-fade `globalAlpha` across the band rather than hard-cutting.

## Touch and wheel

- `touch-action: none` on the zoomed element, or the browser takes pinch as page zoom and drag as scroll.
- Don't filter out single-finger touches to keep page scroll: d3-zoom only tracks fingers from `touchstart` events it accepted, so the second finger alone becomes a one-finger pan and pinch never starts.
- For embedded charts, require a modifier for wheel zoom (`zoom.filter(e => e.type !== "wheel" || e.ctrlKey || e.metaKey)`) or enable zoom on click/focus.
- At `scaleExtent` limits, d3-zoom lets wheel events through (once the current wheel gesture idles) so the page scrolls. A custom `wheelDelta` keeps this; a wheel listener that always `preventDefault`s doesn't.

## Traps

- Zoom attached to an inner `<g>` only listens where the group has painted content. Attach it to the svg or an overlay rect.
- Setting `g.attr("transform", ...)` without `zoom.transform` desyncs the stored `__zoom`; the next gesture jumps back.
- `transform.rescaleX(zx)` on an already-rescaled scale compounds the zoom. Keep the original.
- A wheel spin fires dozens of zoom events per frame. Store the transform and redraw in rAF.
