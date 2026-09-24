# Rendering and zoom

From the v2 `cartography` skill. Open when a map goes to Canvas, needs hit detection, zooms, or outgrows pure D3.

## Canvas layer stack

Bottom to top: tile canvas (raster tiles) → data canvas (fills, borders) → interaction canvas (hover/selection highlight only, cheap to clear) → SVG overlay (legend, tooltips). Hover redraws only the interaction canvas.

## Color-pick hit detection

Draw each feature in a unique RGB on a hidden canvas and read the pixel under the cursor. Handles up to 16.7M features at O(1) per lookup.

```js
function buildPicker(hiddenCanvas, hiddenPath, features) {
  const hctx = hiddenCanvas.getContext("2d", { willReadFrequently: true });
  const byColor = new Map();
  features.forEach((f, i) => {
    const id = i + 1, r = id >> 16 & 255, g = id >> 8 & 255, b = id & 255;
    byColor.set(id, f);
    hctx.beginPath(); hiddenPath(f);
    hctx.fillStyle = `rgb(${r},${g},${b})`; hctx.fill();
  });
  return (x, y) => {
    const [r, g, b] = hctx.getImageData(x, y, 1, 1).data;
    return byColor.get((r << 16) | (g << 8) | b) ?? null; // edge pixels blend: unmatched = miss
  };
}
```

Canvas path fills are always anti-aliased (`imageSmoothingEnabled` only affects `drawImage`), so edge pixels decode to bogus ids. No strokes on the hidden canvas, and treat unmatched colors as a miss. Match the hidden canvas's DPR scaling to the visible one, or pass device-pixel coordinates. For ≤200 features, `d3.geoContains` per feature is simpler.

## Batch fills by color

A classed choropleth has 5-9 colors. One path per color, not per feature:

```js
function drawBatched(ctx, path, features, fillOf) {
  for (const [c, group] of d3.group(features, fillOf)) {
    ctx.beginPath();
    for (const f of group) path(f);
    ctx.fillStyle = c; ctx.fill();
  }
}
```

## Zoom to feature

Frame a clicked region with the zoom behavior so wheel and drag keep working afterward:

```js
function zoomToFeature(svg, zoom, path, d, width, height) {
  const [[x0, y0], [x1, y1]] = path.bounds(d);
  const k = Math.max(1, Math.min(8, 0.9 / Math.max((x1 - x0) / width, (y1 - y0) / height)));
  svg.transition().duration(750).call(zoom.transform,
    d3.zoomIdentity.translate(width / 2, height / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
}
```

Clamp `k` to the zoom's `scaleExtent`. Double-click (or a reset button) transitions back to `zoomIdentity`. In SVG the zoom handler transforms a `<g>`, so fix stroke widths (`vector-effect: non-scaling-stroke`).

## Projection zoom (Canvas)

Re-project instead of transforming, so strokes stay crisp. Save the fitted scale and translate once:

```js
const s0 = projection.scale(), t0 = projection.translate();
const zoomed = ({ transform: { x, y, k } }) => {
  projection.scale(s0 * k).translate([x + k * t0[0], y + k * t0[1]]);
  render();
};
```

Cull features whose bounds fall outside the viewport at high zoom.

## Level of detail

| Zoom | Geometry |
|---|---|
| 1-2 | world-atlas 110m |
| 3-5 | 50m |
| 6+ | 10m, lazy-loaded |

Or simplify on the client: `simplify(presimplify(topology), minWeight)` from `topojson-simplify@3`.

## When to leave pure D3

| Signal | Stay with D3 | Escalate |
|---|---|---|
| Basemap | the data is the map | streets, terrain, satellite |
| Zoom | 1-3 fixed views | continuous 0-22 slippy map |
| Features | <5K SVG, <100K Canvas | 100K+: WebGL |
| Interaction | fixed view with hover/click | pan/zoom "Google Maps" UX |

MapLibre GL + D3 overlay: a `d3.geoTransform` whose `point()` calls `map.project(new maplibregl.LngLat(lon, lat))`. Append the SVG to `map.getCanvasContainer()`, re-render on `move`/`moveend`/`viewreset`, and set `pointer-events: all` on D3 elements that need clicks. PMTiles serves vector tiles from static storage.
