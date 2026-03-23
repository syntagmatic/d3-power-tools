---
name: geographic-maps
description: "D3.js geographic maps and spatial visualization: projections, choropleth, point maps, TopoJSON, zoom-to-feature, canvas geo rendering, tile layers, and geodesic operations. Use this skill whenever the user wants to build maps, choropleths, cartograms, dot maps, flow maps, tile/slippy maps, or any geographic visualization. Also use when the user mentions d3.geoPath, d3.geoProjection, geoMercator, geoAlbersUsa, geoEqualEarth, geoOrthographic, geoNaturalEarth1, fitSize, fitExtent, topojson, topojson.feature, topojson.mesh, topojson.merge, d3.tile, d3.geoGraticule, d3.geoCircle, d3.geoDistance, d3.geoContains, d3.geoStream, projection.clipAngle, projection.clipExtent, choropleth, geographic brushing, zoom-to-feature, or canvas map rendering."
---

# Geographic Maps

Patterns for geographic visualization with D3's geo module.

Related: `shape-morphing` (projection transitions), `color-and-compositing` (choropleth color scales), `patterned-fills` (accessible pattern choropleth).

```
GeoJSON / TopoJSON ──► topojson.feature() / mesh() / merge()
        ↓
[lon, lat] ──► projection ──► [x, y]
        ↓
d3.geoPath(projection) ──► SVG <path> or Canvas ctx
        ↓
interaction: zoom-to-feature, tooltip, geo brushing
```

## Projections

### Choosing a Projection

| Need | Projection | D3 constructor |
|------|-----------|----------------|
| Equal-area world | Equal Earth | `d3.geoEqualEarth()` |
| Web map (familiar) | Mercator | `d3.geoMercator()` |
| USA with AK/HI inset | Albers USA | `d3.geoAlbersUsa()` |
| Continent, equal-area | Albers conic | `d3.geoAlbers()` |
| Globe view | Orthographic | `d3.geoOrthographic()` |
| Low distortion | Natural Earth | `d3.geoNaturalEarth1()` |
| Great-circle lines | Gnomonic | `d3.geoGnomonic()` |
| Thematic world | Winkel Tripel | `d3.geoWinkel3()` (d3-geo-projection) |

### Configuration

```js
const projection = d3.geoMercator()
  .center([12.5, 41.9])    // [lon, lat] at viewport center
  .scale(2000)               // pixels per radian
  .translate([width / 2, height / 2]);
```

**`fitSize` / `fitExtent`** — auto-compute scale and translate. Almost always prefer this over manual configuration:

```js
projection.fitSize([width, height], geojson);
projection.fitExtent([[20, 20], [width - 20, height - 20]], geojson); // with margins
projection.fitSize([width, height], singleFeature); // fit to one region
```

### Rotation

Re-centers the projection. Longitudes are negated: to center on `[lon, lat]`, rotate by `[-lon, -lat]`.

```js
d3.geoOrthographic().rotate([-139.7, -35.7]).clipAngle(90); // Tokyo-centered globe
```

### Clipping

- `clipAngle(90)` — front hemisphere for globes
- `clipExtent([[x0, y0], [x1, y1]])` — rectangular pixel clip for insets

## GeoJSON and TopoJSON

TopoJSON encodes shared borders once — ~80% smaller, plus `mesh()` for clean borders, `merge()` for dissolving regions, `neighbors()` for adjacency.

```js
const us = await d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json");

const states = topojson.feature(us, us.objects.states);       // FeatureCollection
const borders = topojson.mesh(us, us.objects.states, (a, b) => a !== b); // internal borders
const nation = topojson.merge(us, us.objects.states.geometries);          // dissolved outline
```

The mesh filter `(a, b) => a !== b` keeps internal borders only. Use `a === b` for outer boundary.

### Common Data Sources

| Dataset | npm package |
|---------|-------------|
| US states | `us-atlas@3/states-10m.json` |
| US counties | `us-atlas@3/counties-10m.json` |
| World 110m | `world-atlas@2/countries-110m.json` |
| World 50m | `world-atlas@2/countries-50m.json` |

### Joining Data to Geography

```js
const dataById = new Map(data.map(d => [d.id, d]));
features.forEach(f => {
  const row = dataById.get(f.id);
  if (row) Object.assign(f.properties, row);
});
```

FIPS codes in US Atlas: stored as numbers, so `"06"` becomes `6`. Pad when joining: `d.fips.padStart(5, "0")`.

## Path Rendering

### SVG

```js
const path = d3.geoPath(projection);

svg.selectAll("path").data(features).join("path")
  .attr("d", path)
  .attr("fill", d => color(d.properties.value));

// Borders as a single mesh path (faster than per-feature strokes)
svg.append("path").datum(borders).attr("d", path)
  .attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 0.5);
```

### Canvas

Assign context to path generator. Draw fills first, then borders.

```js
const path = d3.geoPath(projection, context);

// Per-feature choropleth
for (const f of features) {
  context.beginPath(); path(f);
  context.fillStyle = color(f.properties.value);
  context.fill();
}

// Single-pass borders
context.beginPath(); path(borders);
context.strokeStyle = "#fff"; context.lineWidth = 0.5; context.stroke();
```

Batch by fill color for better performance — see `canvas-rendering` skill. Always set up DPR scaling.

### Graticules

```js
svg.append("path").datum(d3.geoGraticule().step([10, 10])())
  .attr("d", path).attr("fill", "none").attr("stroke", "#ccc").attr("stroke-width", 0.5);
```

## Choropleth Maps

### Color Scales

```js
d3.scaleSequential(d3.interpolateBlues).domain(extent);           // continuous
d3.scaleQuantize(extent, d3.schemeBlues[9]);                       // equal intervals
d3.scaleQuantile(values, d3.schemeBlues[9]);                       // equal counts
d3.scaleThreshold([.02, .04, .06, .08, .10], d3.schemeBlues[6]); // custom breaks
d3.scaleDiverging(d3.interpolateRdBu).domain([min, mid, max]);   // diverging
```

Quantile often works better than quantize for skewed distributions. Always handle missing data with a fallback color.

### Layer Order

1. Background/water rect
2. Feature fills (choropleth)
3. Internal borders (mesh — single path)
4. Outer boundary
5. Points, labels, legend on top

## Point and Symbol Maps

Project `[lon, lat]` to pixels. Cache projected coordinates to avoid projecting twice:

```js
const projected = data.map(d => {
  const [x, y] = projection([d.lon, d.lat]) ?? [NaN, NaN];
  return { ...d, x, y };
}).filter(d => !isNaN(d.x));
```

**Always `scaleSqrt`** for proportional circles — `scaleLinear` on radius makes large values quadratically exaggerated. Sort large-behind-small to prevent occlusion.

For 10K+ points with overlap, use `globalCompositeOperation` for density — see `color-and-compositing` skill.

## Zoom-to-Feature

### viewBox Approach (Simple)

```js
let active = null;
function clicked(event, d) {
  if (active === d) { active = null; svg.transition().duration(750).attr("viewBox", `0 0 ${width} ${height}`); return; }
  active = d;
  const [[x0, y0], [x1, y1]] = path.bounds(d);
  const scale = Math.max(1, Math.min(8, 0.9 / Math.max((x1 - x0) / width, (y1 - y0) / height)));
  svg.transition().duration(750).attr("viewBox",
    `${(x0 + x1) / 2 - width / scale / 2} ${(y0 + y1) / 2 - height / scale / 2} ${width / scale} ${height / scale}`);
}
```

### d3.zoom Approach (Interactive Pan+Zoom)

```js
function zoomTo(feature) {
  const [[x0, y0], [x1, y1]] = path.bounds(feature);
  svg.transition().duration(750).call(zoom.transform,
    d3.zoomIdentity
      .translate(width / 2, height / 2)
      .scale(Math.min(8, 0.9 / Math.max((x1 - x0) / width, (y1 - y0) / height)))
      .translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
}
```

Counter-scale strokes by dividing `stroke-width` by `transform.k`, or use `vector-effect: non-scaling-stroke`.

### Projection-Based Zoom (Canvas)

Re-project on every zoom instead of transforming a group — avoids stroke scaling:

```js
function zoomed({ transform }) {
  const p = d3.geoMercator()
    .scale(baseScale * transform.k)
    .translate([transform.x + transform.k * baseTranslate[0],
                transform.y + transform.k * baseTranslate[1]]);
  const pathGen = d3.geoPath(p, context);
  // Re-render...
}
```

## Tile Layers

Use `d3-tile` for raster tile backgrounds (OpenStreetMap, etc.) behind D3 vector overlays:

```js
const tileGen = d3tile().size([width, height])
  .scale(projection.scale() * 2 * Math.PI)
  .translate(projection([0, 0]));
const tiles = tileGen();

svg.selectAll("image").data(tiles).join("image")
  .attr("xlink:href", d => `https://tile.openstreetmap.org/${d[2]}/${d[0]}/${d[1]}.png`)
  .attr("x", d => (d[0] + tiles.translate[0]) * tiles.scale)
  .attr("y", d => (d[1] + tiles.translate[1]) * tiles.scale)
  .attr("width", tiles.scale).attr("height", tiles.scale);
```

For zoomable slippy maps, combine `d3-tile` with `d3.zoom`. For Canvas tiles, cache loaded images and re-render on zoom.

## Geodesic Operations

```js
// Great-circle arc — d3.geoPath renders geodesics automatically for LineStrings
svg.append("path").datum({ type: "LineString", coordinates: [[-122.4, 37.8], [139.7, 35.7]] })
  .attr("d", path).attr("fill", "none").attr("stroke", "red");

// Geographic distance (radians × Earth radius)
d3.geoDistance([-122.4, 37.8], [139.7, 35.7]) * 6371; // ~8270 km

// Point-in-polygon (spherical)
d3.geoContains(california, [-118.2, 34.1]); // true

// Circle on sphere (range ring, geographic brush)
d3.geoCircle().center([-122.4, 37.8]).radius(5)(); // 5° radius GeoJSON
```

### Geographic Brushing

Select features within a geodesic radius of cursor:

```js
svg.on("mousemove", (event) => {
  const lonlat = projection.invert(d3.pointer(event));
  if (!lonlat) return;
  const highlighted = features.filter(d =>
    d3.geoDistance(d3.geoCentroid(d), lonlat) * 180 / Math.PI < radiusDeg);
});
```

For nearest-point queries, use `d3-geo-voronoi`:

```js
const voronoi = geoVoronoi()(points.map(d => [d.lon, d.lat]));
const nearest = voronoi.find(lon, lat);
```

## Globe Rendering

Canvas orthographic projection with drag-to-rotate:

```js
const projection = d3.geoOrthographic()
  .scale(height / 2.2).translate([width / 2, height / 2]).clipAngle(90);

// Simple 2-axis drag rotation
let [λ, φ] = projection.rotate();
d3.drag().on("drag", (event) => {
  λ += event.dx * 0.5;
  φ = Math.max(-90, Math.min(90, φ - event.dy * 0.5));
  projection.rotate([λ, φ]);
  render();
});
```

For proper 3-axis rotation, use the `versor` library with quaternion math.

## Performance

| Scenario | Approach |
|----------|----------|
| <500 features, interactive | SVG |
| 500–3000 choropleth | Either |
| 3000+ features | Canvas |
| Mixed (choropleth + tooltips) | Canvas fill + SVG overlay |

Batch by fill color. Pre-render static layers to offscreen canvas. Simplify geometry at load time for zoomed-out views.

### Hit Detection on Canvas Maps

**Color picking**: render each feature with a unique encoded color to a hidden canvas, read pixel under cursor. **`d3.geoContains`**: slower but simpler, good for sparse maps. See `canvas-rendering` skill for patterns.

## Common Pitfalls

1. **Coordinate order.** GeoJSON uses `[longitude, latitude]`, not `[lat, lon]`. Most common geographic data bug.

2. **AlbersUsa gotchas.** No `rotate()`, `center()`, or `clipAngle()`. `invert()` returns `null` outside composite regions.

3. **Antimeridian cutting.** Features crossing 180° need proper cutting. D3 handles this in rendering, but raw coordinates may have artifacts. Reputable TopoJSON sources are pre-cut.

4. **Winding order.** GeoJSON specifies counterclockwise outer rings. Reversed winding fills the globe minus your target. Fix with `@turf/rewind`.

5. **`fitSize` with multiple features.** Fits the bounding box of all features passed. To fit one region but render more, call `fitSize` on the region first, then render everything.

6. **Null projections.** `projection([lon, lat])` returns `null` outside the clip region (e.g., back of globe). Always guard.

7. **Stroke scaling on zoom.** Transforming a `<g>` scales strokes. Divide by `transform.k`, use `vector-effect`, or re-project instead.

8. **FIPS code type mismatch.** TopoJSON stores FIPS as numbers; CSV data often has leading zeros as strings. Normalize before joining.

## References

- [D3 Geo](https://d3js.org/d3-geo) — projection and path API
- [D3 Geo Projection (extended)](https://github.com/d3/d3-geo-projection)
- [TopoJSON spec](https://github.com/topojson/topojson-specification) and [client API](https://github.com/topojson/topojson-client)
- [d3-tile](https://github.com/d3/d3-tile)
- [US Atlas](https://github.com/topojson/us-atlas) / [World Atlas](https://github.com/topojson/world-atlas)
- [Observable: Choropleth](https://observablehq.com/@d3/choropleth)
- [Observable: Zoom to Bounding Box](https://observablehq.com/@d3/zoom-to-bounding-box)
- [Observable: Versor Dragging](https://observablehq.com/@d3/versor-dragging)
