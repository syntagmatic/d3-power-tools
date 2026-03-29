---
name: cartography
description: "D3.js geographic maps and spatial visualization: projections, choropleth, point maps, TopoJSON, zoom-to-feature, canvas geo rendering, tile layers, and geodesic operations. Use this skill whenever the user wants to build maps, choropleths, cartograms, dot maps, flow maps, tile/slippy maps, hex bin maps, bubble maps, bivariate choropleth, or any geographic visualization. Also use when the user mentions d3.geoPath, d3.geoProjection, geoMercator, geoAlbersUsa, geoEqualEarth, geoOrthographic, geoNaturalEarth1, fitSize, fitExtent, topojson, topojson.feature, topojson.mesh, topojson.merge, topojson.neighbors, d3.tile, d3.geoGraticule, d3.geoCircle, d3.geoDistance, d3.geoContains, d3.geoStream, d3.hexbin, projection.clipAngle, projection.clipExtent, choropleth, geographic brushing, zoom-to-feature, canvas map rendering, cartogram, flow map, or bivariate choropleth."
---

# Geographic Maps

Production maps require architectural decisions that simple examples don't reveal.

Related: `shape-morphing` (projection transitions), `color` (choropleth palettes, bivariate, dark mode), `visual-texture` (pattern choropleth), `canvas` (DPR, batching), `canvas-accessibility` (keyboard nav), `scales` (classification).

Pipeline: GeoJSON/TopoJSON -> `topojson.feature()/mesh()/merge()` -> projection `[lon,lat]->[x,y]` -> `d3.geoPath` -> SVG/Canvas. Layer order: tiles -> fills -> borders -> points -> labels -> legend.

## Canonical Data Sources

**Never synthesize geometry.** Always load from canonical TopoJSON atlases -- pre-cut at antimeridian, correctly wound, topologically consistent.

```js
import * as topojson from "https://cdn.jsdelivr.net/npm/topojson-client@3/+esm";
const us = await d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json");
const counties  = topojson.feature(us, us.objects.counties).features;
const states    = topojson.feature(us, us.objects.states).features;
const stateMesh = topojson.mesh(us, us.objects.states, (a, b) => a !== b); // internal borders only
const nation    = topojson.merge(us, us.objects.states.geometries);        // dissolved outline

const world     = await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json");
const countries = topojson.feature(world, world.objects.countries).features;
const land      = topojson.feature(world, world.objects.land);
const borders   = topojson.mesh(world, world.objects.countries, (a, b) => a !== b);
```

Fit to the **merged outline**, not individual features:
```js
const projection = d3.geoAlbersUsa().fitSize([width, height], nation);
const projection = d3.geoEqualEarth().fitSize([width, height], { type: "Sphere" }); // world: fit Sphere
```

Choropleth rendering order -- fills, internal borders (mesh), outer boundary:
```js
const path = d3.geoPath(projection, ctx);
for (const f of features) {
  ctx.beginPath(); path(f);
  ctx.fillStyle = color(data.get(f.id)); ctx.fill();
}
ctx.beginPath(); path(stateMesh);
ctx.strokeStyle = "#fff"; ctx.lineWidth = 0.5; ctx.stroke();
ctx.beginPath(); path(nation);
ctx.strokeStyle = "#333"; ctx.lineWidth = 1; ctx.stroke();
```

## Projection Selection

### Distortion Properties

- **Equal-area** (mandatory for choropleth, density, hex bins, cartograms) -- area distortion misleads about magnitude. EqualEarth (world), Albers/ConicEqualArea (continent), AzimuthalEqualArea (polar).
- **Conformal** (navigation, weather, tile basemaps) -- preserves local angles/shapes. Mercator is conformal; that's why tiles use it, not because it's good.
- **Compromise** (reference maps, general-purpose) -- minimizes all distortions, maximizes none. NaturalEarth1, Robinson, Winkel3.

Regional maps: E-W extent -> conic, N-S extent -> transverse cylindrical, round -> azimuthal. See [Projection Wizard](https://projectionwizard.org/).

```js
d3.geoConicEqualArea().rotate([-15, 0]).center([0, 52]).parallels([35, 65])  // Europe
d3.geoAlbers().rotate([96, 0]).center([0, 38]).parallels([29.5, 45.5])       // Contiguous US
```

**Rotation** re-centers the projection. Longitudes negated: center on `[lon, lat]` -> rotate `[-lon, -lat]`. Three angles: `[lambda, phi, gamma]` -- yaw, pitch, roll.

## Topology Operations

TopoJSON encodes shared borders once -- ~80% smaller, plus `mesh()` for borders, `merge()` for dissolving, `neighbors()` for adjacency.

**Dissolve regions** (e.g., Census divisions from states): `topojson.merge(us, filteredGeometries)`.

**Selective mesh** -- borders between groups: `topojson.mesh(us, us.objects.states, (a, b) => a !== b && regionOf.get(a.id) !== regionOf.get(b.id))`. Filter `(a, b) => a !== b` = internal; `a === b` = outer boundary.

**FIPS codes** in US Atlas are numbers. Pad when joining: `String(id).padStart(5, "0")`. State = 2 digits, county = 5.

**Adjacency** for four-color assignment:
```js
const neighbors = topojson.neighbors(us.objects.states.geometries);
const colorAssignment = new Array(neighbors.length);
neighbors.forEach((nbrs, i) => {
  const used = new Set(nbrs.map(j => colorAssignment[j]));
  colorAssignment[i] = colors.find(c => !used.has(c));
});
```

## Bivariate Choropleth

Two variables on a 3x3 color matrix -- each `scaleQuantile` into `[0,1,2]`, cross-product gives 9 cells. Joshua Stevens palette: `[["#e8e8e8","#ace4e4","#5ac8c8"],["#dfb0d6","#a5add3","#5698b9"],["#be64ac","#8c62aa","#3b4994"]]`. Lookup: `biColors[qy(val)]?.[qx(val)] ?? "#ccc"`. The legend must be a 3x3 grid with axis labels -- without it, bivariate choropleths are unreadable.

## Bubble Maps and Cartograms

Force simulation nudges proportional circles apart while anchoring to geography:
```js
const nodes = projected.map(d => ({ ...d, targetX: d.x, targetY: d.y, r: radius(d.value) }));
const sim = d3.forceSimulation(nodes)
  .force("x", d3.forceX(d => d.targetX).strength(0.8))
  .force("y", d3.forceY(d => d.targetY).strength(0.8))
  .force("collide", d3.forceCollide(d => d.r + 1).iterations(3))
  .stop();
for (let i = 0; i < 120; i++) sim.tick();
```
`strength(0.8)` anchors near true location. Lower (~0.3) -> **Dorling cartogram**. At ~0.05, collision dominates.

**Non-contiguous cartogram** -- scale each feature around its centroid via `geoTransform`:
```js
function scaledPath(feature, scaleFactor) {
  const [cx, cy] = path.centroid(feature);
  const t = d3.geoTransform({
    point(x, y) { this.stream.point(cx + (x - cx) * scaleFactor, cy + (y - cy) * scaleFactor); }
  });
  return d3.geoPath(t)(feature);
}
```

## Hex Bin Maps

```js
import { hexbin as d3Hexbin } from "https://cdn.jsdelivr.net/npm/d3-hexbin@0.2/+esm";
const hexbin = d3Hexbin().x(d => d.x).y(d => d.y).radius(12).extent([[0, 0], [width, height]]);
const bins = hexbin(projected);
const areaScale = d3.scaleSqrt([0, d3.max(bins, d => d.length)], [0, hexbin.radius()]);
```
Start radius at `Math.min(width, height) / 40`. Bins are in screen space -- under Mercator they cover more real-world area near poles. Use equal-area projections.

## Flow Maps

D3 renders `LineString` as geodesic curves automatically. **Always `scaleSqrt` for stroke width.**

Curved arcs for many flows from one hub -- perpendicular control point:
```js
function curvedArc(source, target, projection, curvature = 0.3) {
  const [sx, sy] = projection(source), [tx, ty] = projection(target);
  const mx = (sx + tx) / 2, my = (sy + ty) / 2, dx = tx - sx, dy = ty - sy;
  return `M${sx},${sy} Q${mx - dy * curvature},${my + dx * curvature} ${tx},${ty}`;
}
```

## Geographic Labels

**Pole of inaccessibility** (polylabel) -- point farthest from any edge, always inside the polygon. Better than centroid for concave shapes (Florida's centroid lands in the Gulf). Project coordinates first, then `polylabel(projCoords, 1.0)`. Import from `https://cdn.jsdelivr.net/npm/polylabel@2/+esm`. For MultiPolygon, use the largest polygon by projected area.

## Versor Rotation (Globe Drag)

Quaternion math avoids gimbal lock at poles:
```js
import versor from "https://cdn.jsdelivr.net/npm/versor@0.2/+esm";
let r0, q0, p0;
d3.drag()
  .on("start", (event) => {
    r0 = projection.rotate(); q0 = versor(r0);
    p0 = projection.invert(d3.pointer(event));
  })
  .on("drag", (event) => {
    const p1 = projection.rotate(r0).invert(d3.pointer(event));
    if (!p1) return;
    projection.rotate(versor.rotation(versor.multiply(q0, versor.delta(p0, p1))));
    render();
  });
```
Simple 2-axis drag (`lambda += dx * 0.5; phi -= dy * 0.5`) works for demos but locks at poles. Back-hemisphere: second projection with `clipAngle(180)`, draw at `globalAlpha = 0.15`.

## Canvas Multi-Layer Architecture

Stack (bottom to top): tile canvas (raster tiles) -> data canvas (choropleth fills, borders) -> interaction canvas (selection highlight) -> SVG overlay (tooltips, legend).

### Color-Pick Hit Detection

Render each feature with a unique RGB to a hidden canvas, read pixel under cursor:
```js
const hctx = hiddenCanvas.getContext("2d", { willReadFrequently: true });
features.forEach((f, i) => {
  const r = (i + 1) >> 16 & 255, g = (i + 1) >> 8 & 255, b = (i + 1) & 255;
  indexToFeature.set((r << 16) | (g << 8) | b, f);
  hctx.beginPath(); hiddenPath(f);
  hctx.fillStyle = `rgb(${r},${g},${b})`; hctx.fill();
});
// Lookup: hctx.getImageData(mx, my, 1, 1).data -> decode RGB -> indexToFeature.get()
```
Supports 16.7M features. Disable anti-aliasing (`imageSmoothingEnabled = false`, no strokes) or edge colors blend. `d3.geoContains` is simpler but O(n) -- fine for <=200 features.

### Batch by Fill Color

One `beginPath`/`fill` per color reduces calls from N to ~5-9:
```js
const byColor = d3.group(features, f => color(f.properties.value) ?? "#ccc");
for (const [c, group] of byColor) {
  ctx.beginPath();
  for (const f of group) path(f);
  ctx.fillStyle = c; ctx.fill();
}
```

### Dark Mode

Design separate schemes, don't invert. Dark gray background (`#1a1a2e`, not black), mid-gray borders (`#444`), off-white labels with text shadow. Multi-hue sequential (viridis, plasma) outperforms single-hue.

## Projection-Based Zoom (Canvas)

Re-project on every zoom -- avoids stroke scaling. Save `baseScale`/`baseTranslate`, then in `zoomed({transform})`: `projection.scale(baseScale * transform.k).translate([transform.x + transform.k * baseTranslate[0], transform.y + transform.k * baseTranslate[1]])`. Viewport-cull at high zoom -- skip features outside visible bounds.

## Projection Transitions

### Screen-Space Interpolation

Interpolate projected [x, y] between two projections -- works for any pair but clips abruptly:
```js
function interpolateProjection(proj0, proj1) {
  return t => d3.geoTransform({
    point(x, y) {
      const p0 = proj0([x, y]), p1 = proj1([x, y]);
      if (!p0 || !p1) return;
      this.stream.point(p0[0] * (1 - t) + p1[0] * t, p0[1] * (1 - t) + p1[1] * t);
    }
  });
}
```
**Pitfall**: when one projection clips a point the other shows, paths vanish. Mitigate by pre-clipping to intersection of both visible regions, or cross-fading opacity.

### Parameter Interpolation (Preferred)

Within the same projection type -- interpolate parameters directly, no artifacts:
```js
const r0 = projection.rotate(), r1 = [-lon, -lat, 0];
svg.transition().duration(1000).tween("rotate", () => {
  const interp = d3.interpolate(r0, r1);
  return t => { projection.rotate(interp(t)); svg.selectAll("path").attr("d", path); };
});
```
Between types in the same family (conic -> conic), interpolating `.scale()/.translate()/.rotate()` is smoother. For orthographic, animate `clipAngle` 90->180 to soften pop-in.

## Large Geometry LOD

Client-side simplification:
```js
import { presimplify, simplify } from "https://cdn.jsdelivr.net/npm/topojson-simplify@3/+esm";
const simplified = simplify(presimplify(topology), 0.01);
```

| Zoom | Geometry |
|------|----------|
| 1-2 | 110m coarse |
| 3-5 | 10m medium |
| 6+ | Full, lazy-loaded |

## When to Escalate Beyond Pure D3

| Signal | Stay with D3 | Escalate |
|--------|-------------|----------|
| Basemap | Data is the map | Need streets/terrain/satellite |
| Zoom | 1-3 fixed views | Continuous 0-22 slippy map |
| Features | < 5K SVG, < 100K Canvas | 100K+ need WebGL |
| Interaction | Fixed view with hover/click | Pan/zoom "Google Maps" UX |

### MapLibre GL JS + D3 Overlay

Bridge via `d3.geoTransform` that calls `map.project(new maplibregl.LngLat(lon, lat))` inside `point()`. Append SVG to `map.getCanvasContainer()`, re-render on `viewreset`/`move`/`moveend`. Set `pointer-events: all` on D3 elements needing clicks. [PMTiles](https://github.com/protomaps/PMTiles) serves tiles from static storage.

## Common Pitfalls

1. **AlbersUsa gotchas.** No `rotate()`, `center()`, or `clipAngle()`. `invert()` returns `null` outside composite regions. Cannot use with `d3.tile`.
2. **Winding order.** RFC 7946: counterclockwise outer rings. Reversed winding fills the globe minus your target. Detect: `d3.geoArea()` > 2pi. Fix: `@turf/rewind`.
3. **Null projections.** `projection([lon, lat])` returns `null` outside clip region. Guard: `?? [NaN, NaN]`.
4. **Stroke scaling on zoom.** Transforming `<g>` scales strokes. Fix: divide by `transform.k`, `vector-effect: non-scaling-stroke` (SVG only), or re-project.
5. **Hidden canvas anti-aliasing.** Color-picking breaks at edges. `imageSmoothingEnabled = false`, no strokes.
6. **Re-projecting every frame.** `geoPath` for 3000+ features at 60fps is slow. Geometric zoom for SVG, viewport-cull for Canvas.
7. **`d3.geoArea` units.** Returns steradians. Multiply by 6371^2 for km^2.
8. **Forgetting the Sphere.** World maps need `{ type: "Sphere" }` for water and graticule clipping.
9. **Mercator for choropleth.** Polar areas appear larger. Use equal-area projections.
10. **Synthesizing geometry.** Never create GeoJSON by hand. Use `us-atlas`/`world-atlas`.

## References

- [D3 Geo](https://d3js.org/d3-geo) -- projection and path API
- [TopoJSON client API](https://github.com/topojson/topojson-client)
- [US Atlas](https://github.com/topojson/us-atlas) / [World Atlas](https://github.com/topojson/world-atlas)
- [versor](https://github.com/Fil/versor) -- quaternion rotation for globes
- [Projection Wizard](https://projectionwizard.org/) -- systematic projection selection
