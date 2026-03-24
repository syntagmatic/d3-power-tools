---
name: geographic-maps
description: "D3.js geographic maps and spatial visualization: projections, choropleth, point maps, TopoJSON, zoom-to-feature, canvas geo rendering, tile layers, and geodesic operations. Use this skill whenever the user wants to build maps, choropleths, cartograms, dot maps, flow maps, tile/slippy maps, hex bin maps, bubble maps, bivariate choropleth, or any geographic visualization. Also use when the user mentions d3.geoPath, d3.geoProjection, geoMercator, geoAlbersUsa, geoEqualEarth, geoOrthographic, geoNaturalEarth1, fitSize, fitExtent, topojson, topojson.feature, topojson.mesh, topojson.merge, topojson.neighbors, d3.tile, d3.geoGraticule, d3.geoCircle, d3.geoDistance, d3.geoContains, d3.geoStream, d3.hexbin, projection.clipAngle, projection.clipExtent, choropleth, geographic brushing, zoom-to-feature, canvas map rendering, cartogram, flow map, or bivariate choropleth."
---

# Geographic Maps

D3's geographic stack is its deepest subsystem — spherical math, streaming geometry, topological operations — and production maps require architectural decisions that simple examples don't reveal.

Related: `shape-morphing` (projection transitions), `color-and-compositing` (choropleth color scales, bivariate palettes), `patterned-fills` (accessible pattern choropleth), `canvas-rendering` (DPR, batching), `canvas-accessibility` (keyboard nav for canvas maps).

```
GeoJSON / TopoJSON ──► topojson.feature() / mesh() / merge() / neighbors()
        ↓
[lon, lat] ──► projection ──► [x, y]
        ↓
d3.geoPath(projection) ──► SVG <path> or Canvas ctx
        ↓
layers: tiles → fills → borders → points → labels → legend
```

## Projection Selection

| Need | Projection | Properties |
|------|-----------|------------|
| Equal-area world | `d3.geoEqualEarth()` | Equal-area, pseudocylindrical |
| Web map (familiar) | `d3.geoMercator()` | Conformal, extreme polar distortion |
| USA with AK/HI inset | `d3.geoAlbersUsa()` | Composite, equal-area |
| Continent, equal-area | `d3.geoAlbers()` | Two standard parallels |
| Globe view | `d3.geoOrthographic()` | Perspective, shows hemisphere |
| Low distortion | `d3.geoNaturalEarth1()` | Compromise |
| Great-circle lines | `d3.geoGnomonic()` | All great circles → straight lines |
| Thematic world | `d3.geoWinkel3()` | Requires d3-geo-projection |
| Polar regions | `d3.geoAzimuthalEqualArea()` | Centered on pole |
| Small country/city | `d3.geoTransverseMercator()` | Minimal distortion in narrow N-S strip |

**When projection choice matters**: choropleth demands equal-area (area distortion misleads). Navigation demands conformal. Equal Earth is the modern default for thematic world maps.

### Rotation

Re-centers the projection. Longitudes are negated: to center on `[lon, lat]`, rotate by `[-lon, -lat]`. Three rotation angles: `[λ, φ, γ]` — yaw, pitch, roll. Roll is rarely used but essential for some polar projections.

## Topology Operations

TopoJSON encodes shared borders once — ~80% smaller, plus `mesh()` for borders, `merge()` for dissolving, `neighbors()` for adjacency.

**Dissolve regions** — merge geometries to create custom regions (e.g., Census divisions from states):

```js
const geos = us.objects.states.geometries.filter(g => fips.includes(String(g.id).padStart(2, "0")));
const merged = topojson.merge(us, geos); // dissolves internal borders
```

**Adjacency analysis** — `topojson.neighbors()` returns for each geometry the indices of neighbors sharing a border:

```js
const neighbors = topojson.neighbors(us.objects.states.geometries);
// Use case: four-color theorem — no two adjacent regions share a color
const colorAssignment = new Array(neighbors.length);
neighbors.forEach((nbrs, i) => {
  const used = new Set(nbrs.map(j => colorAssignment[j]));
  colorAssignment[i] = colors.find(c => !used.has(c));
});
```

**Selective mesh** — borders between specific groups:

```js
const interRegionBorders = topojson.mesh(us, us.objects.states,
  (a, b) => a !== b && regionOf.get(a.id) !== regionOf.get(b.id));
```

The mesh filter `(a, b) => a !== b` keeps internal borders only. `a === b` gives outer boundary.

### FIPS Code Joining

FIPS codes in US Atlas: stored as numbers, so `"06"` becomes `6`. Pad when joining: `String(id).padStart(5, "0")`. State FIPS are 2 digits, county FIPS are 5 (state prefix + 3-digit county).

## Bivariate Choropleth

Encode two variables using a 3×3 color matrix. Each variable maps to 3 bins; cross-product gives 9 cells.

```js
const qx = d3.scaleQuantile(data.map(d => d.income), [0, 1, 2]);
const qy = d3.scaleQuantile(data.map(d => d.education), [0, 1, 2]);

// Joshua Stevens palette (most established)
const biColors = [
  ["#e8e8e8", "#ace4e4", "#5ac8c8"],  // low y
  ["#dfb0d6", "#a5add3", "#5698b9"],  // mid y
  ["#be64ac", "#8c62aa", "#3b4994"],  // high y
];

const biColor = f => biColors[qy(f.properties.education)]?.[qx(f.properties.income)] ?? "#ccc";
```

The legend is a 3×3 grid with axis labels — without it, bivariate choropleths are unreadable. Keep to 3×3; 4×4 has 16 colors and overwhelms.

## Bubble Maps with Force-Collision

Proportional circles overlap in dense regions. Use `d3.forceSimulation` to nudge apart while anchoring to geography:

```js
const nodes = projected.map(d => ({
  ...d, targetX: d.x, targetY: d.y, r: radius(d.value),
}));

const sim = d3.forceSimulation(nodes)
  .force("x", d3.forceX(d => d.targetX).strength(0.8))
  .force("y", d3.forceY(d => d.targetY).strength(0.8))
  .force("collide", d3.forceCollide(d => d.r + 1).iterations(3))
  .stop();
for (let i = 0; i < 120; i++) sim.tick();
```

`strength(0.8)` keeps circles near true location. Lower (~0.3) lets collision dominate — this becomes a **Dorling cartogram**.

## Hex Bin Maps

Aggregate points into hexagonal bins. Solves "too many overlapping dots" while preserving spatial distribution.

```js
const hexbin = d3Hexbin().x(d => d.x).y(d => d.y).radius(12)
  .extent([[0, 0], [width, height]]);
const bins = hexbin(projected);
```

**Hex radius choice**: too small → dots again; too large → loses detail. Start at `Math.min(width, height) / 40`. The hex grid is in screen space — bins near poles cover more real-world area under Mercator. Use equal-area projections for honest hex binning.

**Area encoding** requires scaling the hexagon path per bin:
```js
const areaScale = d3.scaleSqrt().domain([0, d3.max(bins, d => d.length)]).range([0, hexbin.radius()]);
path.attr("d", d => hexbin.hexagon(areaScale(d.length)));
```

## Cartograms

### Non-Contiguous Cartogram

Scale each feature around its centroid. Simple, preserves shape, but gaps appear:

```js
// Scale path around centroid without scaling strokes — use geoTransform
function scaledPath(feature, scaleFactor) {
  const [cx, cy] = path.centroid(feature);
  const transform = d3.geoTransform({
    point(x, y) {
      this.stream.point(cx + (x - cx) * scaleFactor, cy + (y - cy) * scaleFactor);
    }
  });
  return d3.geoPath(transform)(feature);
}
```

### Dorling Cartogram

Replace shapes with circles sized by data, positioned by force simulation with low position strength (~0.05) to let collision dominate. Trade-off: geographic fidelity vs readability.

## Flow Maps — Great-Circle Math

D3 renders `LineString` coordinates as geodesic curves automatically. **Always `scaleSqrt` for stroke width** — linear exaggerates high-volume flows.

### Curved Arcs (Non-Geodesic)

For many flows from one hub, add curvature with a perpendicular control point:

```js
function curvedArc(source, target, projection, curvature = 0.3) {
  const [sx, sy] = projection(source), [tx, ty] = projection(target);
  const mx = (sx + tx) / 2, my = (sy + ty) / 2;
  const dx = tx - sx, dy = ty - sy;
  // Perpendicular offset
  const cx = mx - dy * curvature, cy = my + dx * curvature;
  return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`;
}
```

## Geographic Label Placement

### Pole of Inaccessibility (polylabel)

Point farthest from any edge — always inside the polygon. Better than centroid for concave/elongated shapes (e.g., centroid for Florida ends up in the Gulf):

```js
import polylabel from "https://cdn.jsdelivr.net/npm/polylabel@2/+esm";

// polylabel works on projected coordinates
const projected = f.geometry.coordinates.map(ring =>
  ring.map(([lon, lat]) => projection([lon, lat]) ?? [0, 0])
);
const [x, y] = polylabel(projected, 1.0); // precision in pixels
```

For MultiPolygon, use the largest polygon by projected area.

### Label Collision Avoidance

Use force simulation to nudge labels apart:
```js
const sim = d3.forceSimulation(labelNodes)
  .force("x", d3.forceX(d => d.targetX).strength(0.5))
  .force("y", d3.forceY(d => d.targetY).strength(0.5))
  .force("collide", d3.forceCollide(8))
  .stop();
for (let i = 0; i < 60; i++) sim.tick();
```

For publication quality, measure text width with `ctx.measureText()` and use rectangular collision.

## Versor Rotation (3-Axis Globe Drag)

For proper globe rotation without gimbal lock, use quaternion math:

```js
import versor from "https://cdn.jsdelivr.net/npm/versor@0.2/+esm";

let r0, q0, p0;
d3.drag()
  .on("start", (event) => {
    r0 = projection.rotate();
    q0 = versor(r0);
    p0 = projection.invert(d3.pointer(event));
  })
  .on("drag", (event) => {
    const p1 = projection.rotate(r0).invert(d3.pointer(event));
    if (!p1) return;
    const q1 = versor.multiply(q0, versor.delta(p0, p1));
    projection.rotate(versor.rotation(q1));
    render();
  });
```

Simple 2-axis drag (`λ += event.dx * 0.5; φ -= event.dy * 0.5`) works for demos but has gimbal lock at poles.

### Back-Face Rendering

Show back-hemisphere features dimmed: use a second projection with `clipAngle(180)`, draw at `globalAlpha = 0.15` underneath the front face.

## Canvas Multi-Layer Architecture

```
┌─────────────────────────┐
│   SVG overlay           │ ← tooltips, hover highlight, legend
├─────────────────────────┤
│   Interaction canvas    │ ← cursor tracking, selection highlight
├─────────────────────────┤
│   Data canvas           │ ← choropleth fills, borders
├─────────────────────────┤
│   Tile canvas           │ ← raster tiles
└─────────────────────────┘
```

### Color-Pick Hit Detection

Render each feature with a unique encoded RGB color to a hidden canvas, read pixel under cursor:

```js
const hctx = hiddenCanvas.getContext("2d", { willReadFrequently: true });

features.forEach((f, i) => {
  const r = (i + 1) >> 16 & 255;   // +1 so index 0 isn't black
  const g = (i + 1) >> 8 & 255;
  const b = (i + 1) & 255;
  indexToFeature.set((r << 16) | (g << 8) | b, f);
  hctx.beginPath(); hiddenPath(f);
  hctx.fillStyle = `rgb(${r},${g},${b})`;
  hctx.fill();
});

// Lookup on mousemove
const [r, g, b] = hctx.getImageData(mx, my, 1, 1).data;
const feature = indexToFeature.get((r << 16) | (g << 8) | b);
```

Supports 16.7M features (2^24). Anti-aliasing causes edge artifacts — disable with `imageSmoothingEnabled = false` and no strokes on hidden canvas. `d3.geoContains` is simpler but O(n) per mousemove — fine for ≤200 features.

### Canvas Batch by Fill Color

Group features by color, one `beginPath`/`fill` per color — reduces `fill()` calls from N to ~5-9:

```js
const byColor = d3.group(features, f => color(f.properties.value) ?? "#ccc");
for (const [c, group] of byColor) {
  context.beginPath();
  for (const f of group) path(f);
  context.fillStyle = c;
  context.fill();
}
```

## Projection-Based Zoom (Canvas)

Re-project on every zoom instead of transforming a group — avoids stroke scaling:

```js
const [baseScale, baseTranslate] = [projection.scale(), projection.translate()];
function zoomed({ transform }) {
  projection
    .scale(baseScale * transform.k)
    .translate([transform.x + transform.k * baseTranslate[0],
                transform.y + transform.k * baseTranslate[1]]);
  render();
}
```

**Viewport culling** for performance at high zoom — skip features outside visible bounds with quick centroid check.

## Projection Transitions

Interpolate between projections in screen space:

```js
function interpolateProjection(proj0, proj1) {
  return t => point => {
    const p0 = proj0(point), p1 = proj1(point);
    if (!p0 || !p1) return null;
    return [p0[0] * (1 - t) + p1[0] * t, p0[1] * (1 - t) + p1[1] * t];
  };
}

svg.selectAll("path").transition().duration(2000)
  .attrTween("d", d => {
    const interp = interpolateProjection(proj0, proj1);
    return t => d3.geoPath(interp(t))(d);
  });
```

This is screen-space interpolation. For smoother globe transitions, interpolate projection parameters directly.

## Large Geometry LOD / Simplification

### Pre-simplified TopoJSON

```bash
topojson -q 1e6 -o counties-full.json counties.geojson    # full detail
topojson -q 1e4 -s 1e-7 -o counties-simple.json counties.geojson  # overview
```

Client-side with `topojson-simplify`:
```js
import { presimplify, simplify } from "https://cdn.jsdelivr.net/npm/topojson-simplify@3/+esm";
const simplified = simplify(presimplify(topology), 0.01);
```

### Level-of-Detail by Zoom

| Zoom level | Geometry |
|------------|----------|
| 1–2 | 110m (coarse) |
| 3–5 | 10m (medium) |
| 6+ | Full resolution, lazy-loaded |

Lazy-load detailed geometry only when zoom demands it.

## Common Pitfalls

1. **Coordinate order.** GeoJSON uses `[longitude, latitude]`, not `[lat, lon]`. Google Maps, Leaflet, and many databases use `[lat, lon]` — always check.

2. **AlbersUsa gotchas.** No `rotate()`, `center()`, or `clipAngle()`. `invert()` returns `null` outside composite regions (including gaps between AK/HI/lower 48). Cannot be used with `d3.tile`.

3. **Antimeridian cutting.** Features crossing 180° need proper cutting. D3 handles this in rendering, but raw coordinates may have artifacts. Reputable TopoJSON sources are pre-cut. Fix with `d3.geoProject` CLI.

4. **Winding order.** GeoJSON specifies counterclockwise outer rings (RFC 7946). Reversed winding fills the globe minus your target. Detect: `d3.geoArea()` > 2π steradians means winding is inverted. Fix with `@turf/rewind`.

5. **Null projections.** `projection([lon, lat])` returns `null` outside the clip region (e.g., back of globe). Always guard: `projection(point) ?? [NaN, NaN]`.

6. **Stroke scaling on zoom.** Transforming a `<g>` scales strokes. Fixes: divide `stroke-width` by `transform.k`, use `vector-effect: non-scaling-stroke` (SVG only, no transitions), or re-project (Canvas).

7. **FIPS code type mismatch.** TopoJSON stores FIPS as numbers; CSV has leading zeros as strings. Normalize before joining.

8. **Canvas anti-aliasing on hidden canvas.** Color-picking breaks when anti-aliasing blends unique colors at edges. Set `imageSmoothingEnabled = false`, no strokes.

9. **Re-projecting on every frame.** Computing `d3.geoPath` for 3000+ features at 60fps is slow. Use geometric zoom (transform `<g>`) for SVG, viewport-cull for Canvas. Reserve projection-based zoom for final renders.

10. **`d3.geoArea` units.** Returns steradians (solid angle), not km². Multiply by R² (6371² ≈ 40.6M) for km².

11. **Forgetting the Sphere.** World maps without `{ type: "Sphere" }` have no water. Draw it first — also serves as clip boundary for graticules.

12. **`topojson.mesh` filter confusion.** `(a, b) => a !== b` = internal borders. `(a, b) => a === b` = outer boundary. No filter = all borders. Getting this backwards doubles stroke weight on some edges.

13. **Mercator for choropleth.** Areas near poles appear much larger. Use equal-area projections for choropleth.

## References

- [D3 Geo](https://d3js.org/d3-geo) — projection and path API
- [D3 Geo Projection (extended)](https://github.com/d3/d3-geo-projection)
- [TopoJSON spec](https://github.com/topojson/topojson-specification) and [client API](https://github.com/topojson/topojson-client)
- [topojson-simplify](https://github.com/topojson/topojson-simplify)
- [d3-tile](https://github.com/d3/d3-tile) — raster tile rendering
- [d3-hexbin](https://github.com/d3/d3-hexbin)
- [d3-geo-voronoi](https://github.com/Fil/d3-geo-voronoi) — spherical Voronoi
- [polylabel](https://github.com/mapbox/polylabel) — pole of inaccessibility
- [versor](https://github.com/Fil/versor) — quaternion rotation for globes
- [US Atlas](https://github.com/topojson/us-atlas) / [World Atlas](https://github.com/topojson/world-atlas)
- [Joshua Stevens: Bivariate Choropleth](https://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/)
