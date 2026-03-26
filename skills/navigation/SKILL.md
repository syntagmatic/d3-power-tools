---
name: navigation
description: "D3.js zoom and pan interactions: d3-zoom API, geometric vs semantic zoom, SVG and Canvas zoom patterns, rescaleX/rescaleY for axis integration, zoom extent and translate constraints, programmatic zoom (zoom-to-fit, zoom-to-element), minimap/overview+detail, pinch-to-zoom and touch gestures, zoom-linked views, level-of-detail rendering, brush-to-zoom (focus+context), smooth animated transitions between zoom states, and Canvas zoom with quadtree culling. Use this skill when the user needs zoom, pan, scroll-to-zoom, pinch-to-zoom, zoom-to-fit, minimap, semantic zoom, focus+context navigation, or any d3.zoom integration with charts or maps."
---

# Zoom and Pan

Most charts should not zoom. Zoom is for datasets where the overview hides meaningful detail — scatter plots with clusters inside clusters, time series spanning years where daily patterns matter, maps, or network graphs with hundreds of nodes. If the viewer can read the chart at its default scale, adding zoom just adds complexity and accessibility burden.

## When to Add Zoom

Add zoom when the data has **detail across scales** — information that only appears when you get closer. Concrete signals:
- More data points than pixels (scatter with 1K+ points, time series with 10K+ samples)
- Hierarchical structure where sub-patterns emerge at higher magnification
- Spatial data (maps, floor plans) where position is the primary encoding
- The viewer's task requires comparing distant points at high precision

**Don't add zoom when:**
- The dataset fits comfortably at the default scale (most bar charts, small scatter plots)
- The viewer needs to compare all values simultaneously — zoom hides context
- Small multiples or filtering would answer the same question without disorienting the viewer
- Wheel zoom would hijack page scrolling (dashboards, embedded charts, scrollytelling)

## Geometric vs Semantic: The Real Choice

D3's `d3-zoom` manages transform state (translate + scale) and maps pointer, wheel, and touch gestures to smooth, interruptible transitions.

```
user gesture (wheel/pinch/drag)
         ↓
    d3.zoom() → transform {x, y, k}
         ↓
  ┌──────┴──────┐
  │  geometric  │  semantic
  │  (transform │  (rescale domains,
  │   a group)  │   recompute layout)
  └─────────────┘
         ↓
    redraw axes + data
```

**Geometric zoom** applies the transform to a container — everything scales uniformly, like pinch-to-zoom on a photo. Simple to implement but text and strokes scale too, which makes labels unreadable at extremes. Best for maps and diagrams where the visual metaphor is "getting closer."

**Semantic zoom** rescales the data domain and repositions elements — text and marks stay constant size. The viewer sees more detail without the visual distortion of giant strokes. Best for data charts where you want axes to update and points to stay legible.

**Choose geometric when** the content is inherently spatial (maps, floor plans, node-link diagrams) and scaling artifacts are acceptable or counter-scaled.
**Choose semantic when** the chart has axes that should update with zoom level, or when consistent mark size matters for readability.

Related skills: `scales` (rescaled axes), `canvas` (quadtree culling, LOD), `brushing` (brush-to-zoom), `cartography` (map zoom), `hierarchy-interaction` (zoomable treemap/sunburst).

## Geometric Zoom (SVG)

Apply transform to a `<g>` — simple, but text and strokes scale too.

```js
const g = svg.append("g");
svg.call(d3.zoom().scaleExtent([1, 10]).on("zoom", ({ transform }) => {
  g.attr("transform", transform);
}));
```

Counter-scale strokes/text to prevent ballooning at high zoom:

```js
g.selectAll("circle").attr("r", 4 / transform.k).attr("stroke-width", 1 / transform.k);
g.selectAll("text").attr("font-size", `${12 / transform.k}px`);
```

CSS `vector-effect: non-scaling-stroke` works for strokes but not `r`, `font-size`, or `stroke-dasharray`.

## Semantic Zoom (SVG)

Rescale axes and reposition elements — text and strokes stay constant size.

```js
function zoomed({ transform }) {
  const zx = transform.rescaleX(xScale);
  const zy = transform.rescaleY(yScale);
  xAxisGroup.call(d3.axisBottom(zx));
  yAxisGroup.call(d3.axisLeft(zy));
  svg.selectAll("circle").attr("cx", d => zx(d.x)).attr("cy", d => zy(d.y));
}
```

`rescaleX(xScale)` returns a new scale with inverse-transformed domain — domain narrows as you zoom in. Always pass the **original** scale, not a previously rescaled one, or the transform compounds on itself.

**X-only or Y-only zoom:** Only call `rescaleX`, ignore `rescaleY`. For a clean constraint:

```js
const constrained = d3.zoomIdentity.translate(transform.x, 0).scale(transform.k);
```

## Canvas Zoom

Canvas has no DOM to transform — redraw each frame.

**Geometric** — apply canvas transform, draw axes outside:

```js
function zoomed({ transform }) {
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  drawData(ctx, data);
  ctx.restore();
  drawAxes(ctx);
}
```

**Semantic** — rescale coordinates, cull to viewport:

```js
function zoomed({ transform }) {
  const zx = transform.rescaleX(xScale), zy = transform.rescaleY(yScale);
  const [xMin, xMax] = zx.domain(), [yMin, yMax] = zy.domain();
  ctx.clearRect(0, 0, width, height);
  ctx.beginPath();
  for (const d of data) {
    if (d.x < xMin || d.x > xMax || d.y < yMin || d.y > yMax) continue;
    ctx.moveTo(zx(d.x) + 3, zy(d.y));
    ctx.arc(zx(d.x), zy(d.y), 3, 0, Math.PI * 2);
  }
  ctx.fill();
}
```

For large datasets, use `quadtree.visit()` to enumerate only visible points. See `canvas` skill.

## SVG Overlay for Canvas/WebGL Zoom

Attach `d3-zoom` to an SVG layer stacked over Canvas/WebGL. SVG captures pointer events and provides DOM interaction (tooltips, axes); heavy data rendering stays on Canvas/WebGL. This separation means you get crisp axes at every zoom level without redrawing them on Canvas.

```js
// Transparent rect so SVG captures events in empty space
svg.append("rect").attr("width", width).attr("height", height)
  .attr("fill", "none").attr("pointer-events", "all");

svg.call(d3.zoom().scaleExtent([1, 40]).on("zoom", ({ transform }) => {
  // Canvas: redraw data
  drawData(ctx, data, transform);
  // SVG: rescaled axes
  xAxisGroup.call(d3.axisBottom(transform.rescaleX(xScale)));
}));
```

## Zoom Constraints

Always set all three constraints for charts with margins — without them, users can pan data off-screen or zoom to unusable levels:

```js
d3.zoom()
  .scaleExtent([1, 40])          // min/max zoom level
  .translateExtent([[0, 0], [width, height]])  // pan bounds
  .extent([[marginLeft, marginTop], [width - marginRight, height - marginBottom]]); // viewport for wheel centering
```

## Programmatic Zoom

**Zoom to fit** — compute the bounding box of a data subset, calculate scale to fill the viewport:

```js
function zoomToFit(selection, data, padding = 20) {
  const [[x0, y0], [x1, y1]] = [
    [d3.min(data, d => xScale(d.x)), d3.min(data, d => yScale(d.y))],
    [d3.max(data, d => xScale(d.x)), d3.max(data, d => yScale(d.y))]
  ];
  const cw = width - marginLeft - marginRight, ch = height - marginTop - marginBottom;
  const k = Math.min(cw / (x1 - x0), ch / (y1 - y0)) * (1 - 2 * padding / Math.min(cw, ch));
  selection.transition().duration(750).call(zoom.transform,
    d3.zoomIdentity.translate(cw / 2 + marginLeft, ch / 2 + marginTop)
      .scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
}
```

Always use `transition()` for programmatic zoom — instant transform changes are disorienting because the viewer loses spatial context. D3 uses `d3.interpolateZoom` (van Wijk & Nuij) for smooth transitions between distant zoom states.

```js
selection.transition().duration(500).call(zoom.transform, d3.zoomIdentity); // reset
svg.transition().call(zoom.scaleBy, 2, [cx, cy]); // zoom centered on point
```

## Minimap (Overview + Detail)

A minimap gives the viewer spatial context during deep zoom — without it, they lose track of where they are in the dataset. Essential when `scaleExtent` allows more than ~5x zoom.

```js
const mScale = 0.15;
const mx = xScale.copy().range([0, width * mScale]);
const my = yScale.copy().range([0, height * mScale]);

function updateMinimap(transform) {
  const [x0, x1] = transform.rescaleX(xScale).domain();
  const [y0, y1] = transform.rescaleY(yScale).domain();
  viewport.attr("x", mx(x0)).attr("y", my(y1))
    .attr("width", mx(x1) - mx(x0)).attr("height", my(y0) - my(y1));
}

minimap.on("click", (event) => {
  const [px, py] = d3.pointer(event);
  const pt = { x: mx.invert(px), y: my.invert(py) };
  const k = d3.zoomTransform(svg.node()).k;
  svg.transition().duration(750).call(zoom.transform,
    d3.zoomIdentity.translate(width / 2, height / 2).scale(k)
      .translate(-xScale(pt.x), -yScale(pt.y)));
});
```

## Brush-to-Zoom (Focus + Context)

Brush in a context chart drives zoom in the main chart. The `sourceEvent` check prevents infinite loops — brush updates zoom, zoom updates brush:

```js
function brushed({ selection }) {
  if (!selection) return;
  const [sx0, sx1] = selection;
  const k = (xScale.range()[1] - xScale.range()[0]) / (sx1 - sx0);
  svg.call(zoom.transform, d3.zoomIdentity.translate(xScale.range()[0] - sx0 * k, 0).scale(k));
}

// Inverse: zoom updates brush
function zoomed({ transform, sourceEvent }) {
  if (sourceEvent?.type === "brush") return;
  const [d0, d1] = transform.rescaleX(xScale).domain();
  contextSvg.select(".brush").call(brush.move, [xContext(d0), xContext(d1)]);
}
```

## Level-of-Detail (LOD)

Show different representations at different zoom levels — density heatmap zoomed out, individual points zoomed in, labeled points at maximum zoom. This matches how the viewer's task changes: at overview they want patterns, zoomed in they want specifics.

```js
const zx = transform.rescaleX(xScale), zy = transform.rescaleY(yScale);
if (transform.k < 2) drawHexbinDensity(ctx, data, zx, zy);
else if (transform.k < 8) drawPoints(ctx, data, zx, zy, { labels: false });
else drawPoints(ctx, data, zx, zy, { labels: true });
```

Smooth LOD transitions: cross-fade by interpolating `globalAlpha` in the crossover range (e.g., k = 1.5–2.5). Hard cuts between LOD levels are jarring and make the viewer think data changed.

### LOD State Machine with Hysteresis

Naive threshold checks cause flickering when the user hovers near a boundary — zoom in at k=2 triggers "points" mode, the tiniest zoom-out at k=1.99 snaps back to "density." Fix with hysteresis: use different thresholds for zooming in vs. out.

```js
const LOD_STATES = [
  { name: "density",  enterAbove: 0,   exitBelow: 0 },
  { name: "points",   enterAbove: 2.5, exitBelow: 2.0 },
  { name: "labeled",  enterAbove: 8,   exitBelow: 6.5 }
];

let lodIndex = 0;
function updateLOD(k) {
  // Check if we should move to a higher-detail state
  while (lodIndex < LOD_STATES.length - 1 && k >= LOD_STATES[lodIndex + 1].enterAbove)
    lodIndex++;
  // Check if we should move to a lower-detail state
  while (lodIndex > 0 && k < LOD_STATES[lodIndex].exitBelow)
    lodIndex--;
  return LOD_STATES[lodIndex].name;
}
```

The hysteresis band (here 0.5–1.5 units wide) should be proportional to the zoom speed your users exhibit. Wider bands for touch (coarse, fast gestures), narrower for wheel (fine control). Google Maps uses this pattern at every scale transition.

## Touch and Gestures

`d3-zoom` handles multi-touch pinch natively, but mobile has two traps:

```css
svg, canvas { touch-action: none; }  /* d3-zoom handles all touch */
```

Without `touch-action: none`, the browser intercepts pinch as page zoom and drag as scroll — the chart never receives the events.

Filter single-touch on mobile to prevent accidental zoom while scrolling — otherwise any finger drag on the chart triggers panning instead of page scroll:

```js
zoom.filter((event) => {
  if (event.type === "wheel") return true;
  if (event.touches?.length >= 2) return true;  // pinch always works
  if (!event.touches) return !event.button;      // desktop: left button
  return false;                                   // single touch: ignore
});
```

## Zoom-Linked Views

Guard against infinite loops — View A zooms, updates View B, whose handler tries to update View A:

```js
let syncing = false;
function zoomed1({ transform, sourceEvent }) {
  updateChart1(transform);
  if (syncing || !sourceEvent) return;
  syncing = true;
  svg2.call(zoom2.transform, transform);
  syncing = false;
}
```

For X-linked, independent Y: apply only the x-component of one chart's transform to the other.

## Debouncing Expensive Redraws

```js
let pending = null, frameId = null;
function zoomed({ transform }) {
  pending = transform;
  if (!frameId) frameId = requestAnimationFrame(() => {
    expensiveRedraw(pending);
    frameId = null;
  });
}
```

Essential for Canvas with 10K+ elements — without rAF gating, fast wheel scrolling queues dozens of redraws per frame. For SVG with <1K elements, direct updates are fine.

## Common Pitfalls

1. **Zoom on the wrong element.** Attach zoom to the outermost SVG/Canvas, not an inner `<g>` — the listening area is only the group's bbox, so empty space doesn't respond to gestures.

2. **Transform state desync.** D3 stores the transform on the element via `__zoom`. Setting a transform manually (e.g., `g.attr("transform", ...)`) without `zoom.transform` causes the stored state to diverge — next gesture jumps.

3. **Infinite loops in linked views.** View A updates B, B's handler updates A. Guard with `syncing` flag or check `event.sourceEvent === null`.

4. **Geometric zoom of text.** Font size scales with zoom, becoming unreadable at low zoom and oversized at high zoom. Either counter-scale (`fontSize / k`) or use semantic zoom.

5. **`rescaleX` with stale scales.** Always pass the original scale to `rescaleX`, not a previously rescaled copy. The transform already encodes cumulative zoom — applying it to an already-rescaled scale doubles the effect.

6. **`scaleExtent([1, ...])` prevents zoom-out.** Set minimum to a fraction (e.g., 0.5) if you want the viewer to see more than the initial viewport.

7. **Wheel zoom hijacks page scroll.** If the chart doesn't fill the viewport, wheel events get captured before the page can scroll. Use `zoom.filter()` to require a modifier key (Ctrl+wheel) or only enable zoom on focus. A subtler fix: let wheel events pass through to page scroll when the user is already at the zoom limit. `scaleExtent` does this by default as of d3-zoom v3 — wheel events that would exceed the extent are not consumed, so page scroll resumes naturally. If you override `wheelDelta`, preserve this pass-through behavior or users get trapped.

8. **Programmatic zoom without transition.** `svg.call(zoom.transform, t)` is instant — the viewer loses spatial context and can't track what moved. Almost always use `svg.transition().duration(500).call(zoom.transform, t)`.

9. **Canvas zoom without clearing.** Forgetting `ctx.clearRect()` produces layered artifacts — each frame draws on top of the previous one.

## Scroll-Driven Animations vs. d3-zoom

CSS scroll-driven animations (`animation-timeline: scroll()`) let you bind keyframe animations to scroll position with zero JS — useful for scrollytelling where chart elements animate as the user scrolls through a narrative. As of March 2026, shipped in Chrome and Edge; Firefox and Safari support is partial.

**Don't use them for interactive zoom.** Scroll-driven CSS can't manage the `{x, y, k}` transform matrix that `rescaleX`/`rescaleY` depend on. For anything with axes, pan, or continuous zoom state, `d3-zoom` remains the right tool. The overlap is narrow: if your "zoom" is really "scroll position drives an animation," CSS handles it natively. If the user needs to pan, pinch, or zoom to arbitrary levels, that's `d3-zoom`.

## References

- [D3 Zoom](https://d3js.org/d3-zoom) — API reference
- [Zoom to Bounding Box](https://observablehq.com/@d3/zoom-to-bounding-box) — programmatic zoom-to-fit
- [Semantic Zoom](https://observablehq.com/@d3/semantic-zoom) — rescaleX/rescaleY pattern
- [Smooth Zooming](https://www.win.tue.nl/~vanwijk/zoompan.pdf) — van Wijk & Nuij, 2003
- [Focus + Context](https://observablehq.com/@d3/focus-context) — brush-driven zoom
