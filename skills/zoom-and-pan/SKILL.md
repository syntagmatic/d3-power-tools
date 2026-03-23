---
name: zoom-and-pan
description: "D3.js zoom and pan interactions: d3-zoom API, geometric vs semantic zoom, SVG and Canvas zoom patterns, rescaleX/rescaleY for axis integration, zoom extent and translate constraints, programmatic zoom (zoom-to-fit, zoom-to-element), minimap/overview+detail, pinch-to-zoom and touch gestures, zoom-linked views, level-of-detail rendering, brush-to-zoom (focus+context), smooth animated transitions between zoom states, and Canvas zoom with quadtree culling. Use this skill when the user needs zoom, pan, scroll-to-zoom, pinch-to-zoom, zoom-to-fit, minimap, semantic zoom, focus+context navigation, or any d3.zoom integration with charts or maps."
---

# Zoom and Pan

D3's `d3-zoom` manages transform state (translate + scale) and maps pointer, wheel, and touch gestures to smooth, interruptible transitions. The critical design choice is **geometric vs semantic zoom**: whether zooming magnifies pixels or reveals more detail.

Related skills: `axes-and-scales` (rescaled axes), `canvas-rendering` (quadtree culling, LOD), `brushing-and-selection` (brush-to-zoom), `geographic-maps` (map zoom), `hierarchy-interaction` (zoomable treemap/sunburst).

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

## Core API

Every zoom state is a `d3.ZoomTransform`: `k` (scale), `x`/`y` (translation). Maps point `[px, py]` to screen via `[px * k + x, py * k + y]`.

```js
const zoom = d3.zoom()
  .scaleExtent([1, 20])
  .on("zoom", ({ transform }) => { /* respond */ });

svg.call(zoom);

// Read current transform
const t = d3.zoomTransform(svg.node());
t.apply([x, y]);     // data → screen
t.invert([sx, sy]);  // screen → data
```

Check `event.sourceEvent` to distinguish user-initiated zoom from programmatic — important for avoiding infinite loops in linked views.

## Geometric Zoom (SVG)

Apply transform to a `<g>` container. Simple, but text and strokes scale too.

```js
const g = svg.append("g");
// draw everything inside g...

const zoom = d3.zoom().scaleExtent([1, 10]).on("zoom", ({ transform }) => {
  g.attr("transform", transform);
});
svg.call(zoom);
```

### Counter-Scaling Strokes and Text

```js
g.selectAll("circle")
  .attr("r", 4 / transform.k)
  .attr("stroke-width", 1 / transform.k);
g.selectAll("text").attr("font-size", `${12 / transform.k}px`);
```

Or use CSS `vector-effect: non-scaling-stroke` (doesn't apply to `r`, `font-size`, or `stroke-dasharray`).

## Semantic Zoom (SVG)

Rescale axes and reposition elements — text and strokes stay constant size.

```js
function zoomed({ transform }) {
  const zx = transform.rescaleX(xScale);
  const zy = transform.rescaleY(yScale);

  xAxisGroup.call(d3.axisBottom(zx));
  yAxisGroup.call(d3.axisLeft(zy));

  svg.selectAll("circle")
    .attr("cx", d => zx(d.x))
    .attr("cy", d => zy(d.y));
}
```

`rescaleX(xScale)` returns a new scale with the same range but an inverse-transformed domain — the domain narrows as you zoom in.

### X-Only or Y-Only Zoom

Only call `rescaleX` and ignore `rescaleY` (or vice versa). For a clean constraint, reconstruct the transform:

```js
const constrained = d3.zoomIdentity.translate(transform.x, 0).scale(transform.k);
```

## Canvas Zoom

Canvas has no DOM to transform — redraw everything each frame.

### Geometric (Canvas Transform)

```js
function zoomed({ transform }) {
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  drawData(ctx, data);
  ctx.restore();
  drawAxes(ctx); // outside transform so axes don't scale
}
```

### Semantic (Rescaled Coordinates)

```js
function zoomed({ transform }) {
  const zx = transform.rescaleX(xScale);
  const zy = transform.rescaleY(yScale);
  const [xMin, xMax] = zx.domain();
  const [yMin, yMax] = zy.domain();

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

For large datasets, use `quadtree.visit()` to enumerate only visible points instead of scanning all data. See `canvas-rendering` skill for the pattern.

## SVG Overlay for Canvas/WebGL Zoom

Attach `d3-zoom` to an SVG layer stacked on top, then pipe the transform to Canvas or WebGL layers below. The SVG captures all pointer events and gives you DOM-based interaction (tooltips, axes, annotations) for free, while the heavy data rendering stays on Canvas/WebGL.

```js
const container = d3.select("#chart").style("position", "relative");

// Canvas layer (below) — data rendering
const canvas = container.append("canvas")
  .style("position", "absolute")
  .attr("width", width).attr("height", height);
const ctx = canvas.node().getContext("2d");

// SVG layer (above) — zoom target + axes/annotations
const svg = container.append("svg")
  .style("position", "absolute")
  .attr("width", width).attr("height", height);

// Transparent rect so SVG captures pointer events in empty space
svg.append("rect")
  .attr("width", width).attr("height", height)
  .attr("fill", "none").attr("pointer-events", "all");

const xAxisGroup = svg.append("g")
  .attr("transform", `translate(0,${height - marginBottom})`);

const zoom = d3.zoom().scaleExtent([1, 40]).on("zoom", ({ transform }) => {
  // Update Canvas
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  drawData(ctx, data);
  ctx.restore();
  // Update SVG axes
  xAxisGroup.call(d3.axisBottom(transform.rescaleX(xScale)));
});

svg.call(zoom); // zoom lives on SVG, drives Canvas below
```

This separates concerns cleanly: the SVG never holds thousands of data elements, and the Canvas never needs to handle pointer events. The same pattern works for WebGL — replace the Canvas draw calls with GL uniform updates for the transform matrix.

## Zoom Constraints

```js
d3.zoom()
  .scaleExtent([1, 40])          // min/max zoom level
  .translateExtent([[0, 0], [width, height]])  // pan bounds
  .extent([[marginLeft, marginTop], [width - marginRight, height - marginBottom]]); // viewport for wheel centering
```

Combine all three for a chart with margins. `translateExtent` accounts for current zoom level — more panning at higher zoom.

## Programmatic Zoom

### Zoom to Fit

```js
function zoomToFit(selection, data, padding = 20) {
  const [[x0, y0], [x1, y1]] = [
    [d3.min(data, d => xScale(d.x)), d3.min(data, d => yScale(d.y))],
    [d3.max(data, d => xScale(d.x)), d3.max(data, d => yScale(d.y))]
  ];
  const cw = width - marginLeft - marginRight;
  const ch = height - marginTop - marginBottom;
  const k = Math.min(cw / (x1 - x0), ch / (y1 - y0)) * (1 - 2 * padding / Math.min(cw, ch));

  const transform = d3.zoomIdentity
    .translate(cw / 2 + marginLeft, ch / 2 + marginTop)
    .scale(k)
    .translate(-(x0 + x1) / 2, -(y0 + y1) / 2);

  selection.transition().duration(750).call(zoom.transform, transform);
}
```

### Zoom to Point / Reset

```js
function zoomToPoint(selection, point, scale = 5) {
  selection.transition().duration(750).call(zoom.transform,
    d3.zoomIdentity.translate(width / 2, height / 2).scale(scale)
      .translate(-xScale(point.x), -yScale(point.y)));
}

function resetZoom(selection) {
  selection.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
}
```

### Programmatic Pan/Scale

```js
svg.transition().call(zoom.translateBy, -100, 0);  // pan right 100px
svg.transition().call(zoom.scaleBy, 2);             // 2x zoom in
svg.transition().call(zoom.scaleBy, 2, [cx, cy]);   // zoom centered on point
```

D3 uses `d3.interpolateZoom` (van Wijk & Nuij) for smooth transitions between distant zoom states.

## Minimap (Overview + Detail)

A small overview with a viewport rectangle showing the current zoom region.

```js
const mScale = 0.15;
const mx = xScale.copy().range([0, width * mScale]);
const my = yScale.copy().range([0, height * mScale]);

// Draw all data at reduced scale in minimap SVG
// Add a viewport rect updated on each zoom event:
function updateMinimap(transform) {
  const zx = transform.rescaleX(xScale);
  const zy = transform.rescaleY(yScale);
  const [x0, x1] = zx.domain();
  const [y0, y1] = zy.domain();
  viewport.attr("x", mx(x0)).attr("y", my(y1))
    .attr("width", mx(x1) - mx(x0)).attr("height", my(y0) - my(y1));
}

// Click minimap to navigate
minimap.on("click", (event) => {
  const [px, py] = d3.pointer(event);
  zoomToPoint(svg, { x: mx.invert(px), y: my.invert(py) });
});
```

## Brush-to-Zoom (Focus + Context)

A brush in a context chart drives zoom in the main chart:

```js
function brushed({ selection }) {
  if (!selection) return;
  const [sx0, sx1] = selection;
  const k = (xScale.range()[1] - xScale.range()[0]) / (sx1 - sx0);
  const tx = xScale.range()[0] - sx0 * k;
  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, 0).scale(k));
}

// Inverse: zoom updates brush
function zoomed({ transform, sourceEvent }) {
  const zx = transform.rescaleX(xScale);
  if (sourceEvent?.type !== "brush") {
    const [d0, d1] = zx.domain();
    contextSvg.select(".brush").call(brush.move, [xContext(d0), xContext(d1)]);
  }
}
```

## Level-of-Detail (LOD)

Show different representations at different zoom levels:

```js
const zx = transform.rescaleX(xScale);
const zy = transform.rescaleY(yScale);

if (transform.k < 2) drawHexbinDensity(ctx, data, zx, zy);
else if (transform.k < 8) drawPoints(ctx, data, zx, zy, { labels: false });
else drawPoints(ctx, data, zx, zy, { labels: true });
```

Smooth LOD transitions: cross-fade by interpolating `globalAlpha` in the crossover range (e.g., k = 1.5–2.5).

## Touch and Gestures

`d3-zoom` handles multi-touch pinch natively. Key setup:

```css
svg, canvas { touch-action: none; }  /* d3-zoom handles all touch */
```

```js
svg.on("wheel", (e) => e.preventDefault(), { passive: false }); // prevent page scroll
```

For mobile, consider filtering single-touch to prevent accidental zoom while scrolling:

```js
zoom.filter((event) => {
  if (event.type === "wheel") return true;
  if (event.touches?.length >= 2) return true; // pinch
  if (!event.touches) return !event.button;      // mouse left-click
  return false; // ignore single touch
});
```

## Zoom-Linked Views

Coordinate zoom across multiple charts. Guard against infinite loops:

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

For X-linked, independent Y: apply only the x-component of one chart's transform to the other, preserving each chart's y-translation.

## Zoom Buttons (Accessibility)

```js
d3.select("#zoom-in").on("click", () => svg.transition().call(zoom.scaleBy, 1.5));
d3.select("#zoom-out").on("click", () => svg.transition().call(zoom.scaleBy, 1 / 1.5));
d3.select("#zoom-reset").on("click", () => svg.transition().call(zoom.transform, d3.zoomIdentity));
```

## Clip Path for Zoomed Content

Prevent data from rendering outside chart area:

```js
svg.append("clipPath").attr("id", "clip")
  .append("rect")
    .attr("x", marginLeft).attr("y", marginTop)
    .attr("width", width - marginLeft - marginRight)
    .attr("height", height - marginTop - marginBottom);

chartArea.attr("clip-path", "url(#clip)");
```

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

Essential for Canvas with 10K+ elements. For SVG with <1K elements, direct updates are fine.

## Common Pitfalls

1. **Zoom on the wrong element.** Attach zoom to the outermost SVG/Canvas, not an inner `<g>` — the listening area may be too small (only the group's bbox).

2. **Missing `touch-action: none`.** Mobile browsers intercept pinch as page zoom and drag as scroll.

3. **Transform state desync.** D3 stores the transform on the element via `__zoom`. Setting a transform manually (e.g., `g.attr("transform", ...)`) without `zoom.transform` causes the stored state to diverge — next gesture jumps.

4. **Infinite loops in linked views.** View A → updates B → B's handler → updates A → loop. Guard with `syncing` flag or check `event.sourceEvent === null`.

5. **Geometric zoom of text.** Font size scales with zoom. Either counter-scale (`fontSize / k`) or use semantic zoom.

6. **`rescaleX` with time scales.** Works fine — domain becomes a narrower time range. But tick formatting may need adjustment: use multi-level time format (see `axes-and-scales` skill).

7. **Canvas zoom without clearing.** Forgetting `ctx.clearRect()` produces layered artifacts.

8. **`scaleExtent([1, ...])` prevents zoom-out.** Set minimum to a fraction (e.g., 0.5) to allow zooming out.

9. **Wheel zoom hijacks page scroll.** If the chart fills the viewport, wheel events get captured. Use `zoom.filter()` to require a modifier key (Ctrl+wheel) or only enable on hover/focus.

10. **Programmatic zoom without transition.** `svg.call(zoom.transform, t)` is instant and disorienting. Almost always use `svg.transition().duration(500).call(zoom.transform, t)`.

## References

- [D3 Zoom](https://d3js.org/d3-zoom) — API reference
- [Zoom to Bounding Box](https://observablehq.com/@d3/zoom-to-bounding-box) — programmatic zoom-to-fit
- [Semantic Zoom](https://observablehq.com/@d3/semantic-zoom) — rescaleX/rescaleY pattern
- [Smooth Zooming](https://www.win.tue.nl/~vanwijk/zoompan.pdf) — van Wijk & Nuij, 2003
- [Pan & Zoom Axes](https://observablehq.com/@d3/pan-zoom-axes) — axis-integrated zoom
- [Focus + Context](https://observablehq.com/@d3/focus-context) — brush-driven zoom
