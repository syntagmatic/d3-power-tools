---
name: geographic-maps
description: "D3.js geographic maps and spatial visualization: projections, choropleth, point maps, TopoJSON, zoom-to-feature, canvas geo rendering, tile layers, and geodesic operations. Use this skill whenever the user wants to build maps, choropleths, cartograms, dot maps, flow maps, tile/slippy maps, hex bin maps, bubble maps, bivariate choropleth, or any geographic visualization. Also use when the user mentions d3.geoPath, d3.geoProjection, geoMercator, geoAlbersUsa, geoEqualEarth, geoOrthographic, geoNaturalEarth1, fitSize, fitExtent, topojson, topojson.feature, topojson.mesh, topojson.merge, topojson.neighbors, d3.tile, d3.geoGraticule, d3.geoCircle, d3.geoDistance, d3.geoContains, d3.geoStream, d3.hexbin, projection.clipAngle, projection.clipExtent, choropleth, geographic brushing, zoom-to-feature, canvas map rendering, cartogram, flow map, or bivariate choropleth."
---

# Geographic Maps

Patterns for geographic visualization with D3's geo module. D3's geographic stack is its deepest subsystem — spherical math, streaming geometry, topological operations — and production maps require architectural decisions that simple examples don't reveal.

Related: `shape-morphing` (projection transitions), `color-and-compositing` (choropleth color scales, bivariate palettes), `patterned-fills` (accessible pattern choropleth), `canvas-rendering` (DPR, batching, progressive render), `canvas-accessibility` (keyboard nav for canvas maps).

```
GeoJSON / TopoJSON ──► topojson.feature() / mesh() / merge() / neighbors()
        ↓
[lon, lat] ──► projection ──► [x, y]
        ↓
d3.geoPath(projection) ──► SVG <path> or Canvas ctx
        ↓
layers: tiles → fills → borders → points → labels → legend
        ↓
interaction: zoom-to-feature, tooltip, geo brushing, linked filtering
```

## Projections

### Choosing a Projection

| Need | Projection | D3 constructor | Properties |
|------|-----------|----------------|------------|
| Equal-area world | Equal Earth | `d3.geoEqualEarth()` | Equal-area, pseudocylindrical |
| Web map (familiar) | Mercator | `d3.geoMercator()` | Conformal, extreme polar distortion |
| USA with AK/HI inset | Albers USA | `d3.geoAlbersUsa()` | Composite, equal-area |
| Continent, equal-area | Albers conic | `d3.geoAlbers()` | Equal-area, two standard parallels |
| Globe view | Orthographic | `d3.geoOrthographic()` | Perspective, shows hemisphere |
| Low distortion | Natural Earth | `d3.geoNaturalEarth1()` | Compromise (neither equal-area nor conformal) |
| Great-circle lines | Gnomonic | `d3.geoGnomonic()` | All great circles render as straight lines |
| Thematic world | Winkel Tripel | `d3.geoWinkel3()` | Compromise, requires d3-geo-projection |
| Polar regions | Azimuthal Equal Area | `d3.geoAzimuthalEqualArea()` | Equal-area, centered on pole |
| Small country/city | Transverse Mercator | `d3.geoTransverseMercator()` | Conformal, minimal distortion in narrow N-S strip |

**When projection choice matters**: choropleth demands equal-area (otherwise area distortion misleads). Navigation demands conformal (angles preserved). Thematic world maps are a judgment call — Equal Earth is the modern default.

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

**`fitSize` accepts any GeoJSON object** — FeatureCollection, Feature, or geometry. To fit a Sphere (full globe):

```js
projection.fitSize([width, height], { type: "Sphere" });
```

### Rotation

Re-centers the projection. Longitudes are negated: to center on `[lon, lat]`, rotate by `[-lon, -lat]`.

```js
d3.geoOrthographic().rotate([-139.7, -35.7]).clipAngle(90); // Tokyo-centered globe
```

Three rotation angles: `[λ, φ, γ]` — yaw (longitude), pitch (latitude), roll. Roll is rarely used but essential for some polar projections.

### Clipping

- `clipAngle(90)` — front hemisphere for globes
- `clipExtent([[x0, y0], [x1, y1]])` — rectangular pixel clip for insets or small multiples

### Inset Maps

For custom insets (detail view of a region alongside the main map), use `clipExtent` on a second projection:

```js
const mainProjection = d3.geoAlbers().fitSize([width, height], nation);
const insetProjection = d3.geoMercator()
  .fitExtent([[width - 200, height - 150], [width - 10, height - 10]], alaska);

// Render main map with mainProjection, inset with insetProjection
// Draw a border rect around the inset area
svg.append("rect")
  .attr("x", width - 200).attr("y", height - 150)
  .attr("width", 190).attr("height", 140)
  .attr("fill", "none").attr("stroke", "#333");
```

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

FIPS codes in US Atlas: stored as numbers, so `"06"` becomes `6`. Pad when joining: `d.fips.padStart(5, "0")`. State FIPS are 2 digits, county FIPS are 5 (state prefix + 3-digit county).

### Topology Operations

TopoJSON's real power is topological operations on shared boundaries.

**Dissolve regions** — merge geometries to create custom regions (e.g., Census divisions from states):

```js
// Group state geometries by region
const regionMap = new Map([["Northeast", ["09","23","25","33","44","50","34","36","42"]], /* ... */]);
const regionFeatures = [];
for (const [name, fips] of regionMap) {
  const geos = us.objects.states.geometries.filter(g => fips.includes(String(g.id).padStart(2, "0")));
  const merged = topojson.merge(us, geos); // dissolves internal borders
  regionFeatures.push({ type: "Feature", properties: { name }, geometry: merged });
}
```

**Adjacency analysis** — `topojson.neighbors()` returns an array of arrays: for each geometry, the indices of its neighbors (shared borders):

```js
const neighbors = topojson.neighbors(us.objects.states.geometries);
// neighbors[i] = [j, k, ...] — indices of geometries sharing a border with geometry i

// Use case: no two adjacent regions share a color (four-color theorem)
const colors = d3.schemeCategory10;
const colorAssignment = new Array(neighbors.length);
neighbors.forEach((nbrs, i) => {
  const used = new Set(nbrs.map(j => colorAssignment[j]));
  colorAssignment[i] = colors.find(c => !used.has(c));
});
```

**Selective mesh** — extract borders between specific groups:

```js
// Borders between regions (not within regions)
const regionOf = new Map(/* stateId → regionName */);
const interRegionBorders = topojson.mesh(us, us.objects.states,
  (a, b) => a !== b && regionOf.get(a.id) !== regionOf.get(b.id));
```

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

**Batch by fill color** — Canvas state changes (`fillStyle`) are cheap individually but add up at 3000+ features. Group features by color and issue one `beginPath` per color:

```js
// Group features by fill color
const byColor = d3.group(features, f => color(f.properties.value) ?? "#ccc");
for (const [c, group] of byColor) {
  context.beginPath();
  for (const f of group) path(f);
  context.fillStyle = c;
  context.fill();
}
// Then borders in one pass
context.beginPath(); path(borders);
context.strokeStyle = "#fff"; context.lineWidth = 0.5; context.stroke();
```

This reduces `fill()` calls from N to the number of distinct colors (typically 5–9). See `canvas-rendering` skill for DPR setup.

### Graticules

```js
svg.append("path").datum(d3.geoGraticule().step([10, 10])())
  .attr("d", path).attr("fill", "none").attr("stroke", "#ccc").attr("stroke-width", 0.5);
```

Graticule outline (the outer ring at ±180°/±90°) can be suppressed with `.extent([[-179.99, -89.99], [179.99, 89.99]])` if you're drawing a separate sphere outline.

## Choropleth Maps

### Color Scales

```js
d3.scaleSequential(d3.interpolateBlues).domain(extent);           // continuous
d3.scaleQuantize(extent, d3.schemeBlues[9]);                       // equal intervals
d3.scaleQuantile(values, d3.schemeBlues[9]);                       // equal counts
d3.scaleThreshold([.02, .04, .06, .08, .10], d3.schemeBlues[6]); // custom breaks
d3.scaleDiverging(d3.interpolateRdBu).domain([min, mid, max]);   // diverging
```

**Choosing a scale type**: Quantile spreads features evenly across color bins — reveals relative rank but hides absolute differences. Quantize shows absolute magnitude but can leave bins empty if data is skewed. Threshold gives editorial control. Continuous (sequential) avoids binning artifacts but makes exact comparison harder.

Always handle missing data with a fallback color (`"#ccc"` or `"#ddd"`). Missing ≠ zero — render them distinctly.

### Bivariate Choropleth

Encode two variables simultaneously using a 3×3 color matrix. Each variable maps to one of 3 bins; the cross-product gives 9 cells.

```js
// Two variables, each quantized to 3 bins (0, 1, 2)
const qx = d3.scaleQuantile(data.map(d => d.income), [0, 1, 2]);
const qy = d3.scaleQuantile(data.map(d => d.education), [0, 1, 2]);

// 3×3 color matrix — rows = y bins, cols = x bins
// Joshua Stevens palette (most established for bivariate choropleths)
const biColors = [
  ["#e8e8e8", "#ace4e4", "#5ac8c8"],  // low y
  ["#dfb0d6", "#a5add3", "#5698b9"],  // mid y
  ["#be64ac", "#8c62aa", "#3b4994"],  // high y
];

features.forEach(f => {
  const ix = qx(f.properties.income);
  const iy = qy(f.properties.education);
  f.properties._biColor = biColors[iy]?.[ix] ?? "#ccc";
});
```

The legend is a 3×3 grid with axis labels — position it in a corner with clear axis titles. Without the legend, bivariate choropleths are unreadable. Keep to 3×3; 4×4 has 16 colors and overwhelms.

### Layer Order

1. Background/water rect (or Sphere path)
2. Feature fills (choropleth)
3. Internal borders (mesh — single path)
4. Outer boundary
5. Points, symbols, flow lines
6. Labels
7. Legend on top

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

### Bubble Maps with Collision Avoidance

Proportional circles on a map often overlap in dense regions. Use `d3.forceSimulation` to nudge circles apart while keeping them near their geographic anchor:

```js
const nodes = projected.map(d => ({
  ...d,
  targetX: d.x, targetY: d.y,       // geographic anchor
  r: radius(d.value),
}));

const sim = d3.forceSimulation(nodes)
  .force("x", d3.forceX(d => d.targetX).strength(0.8))
  .force("y", d3.forceY(d => d.targetY).strength(0.8))
  .force("collide", d3.forceCollide(d => d.r + 1).iterations(3))
  .stop();

// Run synchronously — no animation needed, just layout
for (let i = 0; i < 120; i++) sim.tick();

// Draw circles at sim-adjusted positions
svg.selectAll("circle").data(nodes).join("circle")
  .attr("cx", d => d.x).attr("cy", d => d.y)
  .attr("r", d => d.r)
  .attr("fill", d => color(d.category))
  .attr("fill-opacity", 0.7)
  .attr("stroke", "#fff").attr("stroke-width", 0.5);
```

The `strength(0.8)` on position forces keeps circles near their true location. Lower values allow more displacement (less overlap but less geographic accuracy). This is the **Dorling cartogram** technique when you push strength down to ~0.3 and let collision dominate.

### Hex Bin Maps

Aggregate point data into hexagonal bins projected onto geography. Solves the "too many overlapping dots" problem while preserving spatial distribution:

```js
import { hexbin as d3Hexbin } from "https://cdn.jsdelivr.net/npm/d3-hexbin@0.2/+esm";

const hexbin = d3Hexbin()
  .x(d => d.x).y(d => d.y)
  .radius(12)                         // hex radius in pixels
  .extent([[0, 0], [width, height]]);

const bins = hexbin(projected);       // each bin has .x, .y, .length

const colorScale = d3.scaleSequential(d3.interpolateYlOrRd)
  .domain([0, d3.max(bins, d => d.length)]);

svg.selectAll("path").data(bins).join("path")
  .attr("d", hexbin.hexagon())        // regular hexagon path
  .attr("transform", d => `translate(${d.x},${d.y})`)
  .attr("fill", d => colorScale(d.length))
  .attr("stroke", "#fff").attr("stroke-width", 0.5);
```

**Hex radius choice**: too small → dots again; too large → loses geographic detail. Start at `radius = Math.min(width, height) / 40` and adjust. The hex grid is in screen space, not geographic space — bins near the poles cover more real-world area under Mercator. Use equal-area projections for honest hex binning.

**Encoding choices**: color = count (density), area = count (proportional hexagons), or both. Area encoding requires scaling the hexagon path per bin:

```js
const areaScale = d3.scaleSqrt().domain([0, d3.max(bins, d => d.length)]).range([0, hexbin.radius()]);
svg.selectAll("path").data(bins).join("path")
  .attr("d", d => hexbin.hexagon(areaScale(d.length)))
  .attr("transform", d => `translate(${d.x},${d.y})`);
```

## Cartograms

Cartograms distort geography so that area encodes a data variable rather than land mass.

### Non-Contiguous Cartogram

Scale each feature independently around its centroid. Simple to implement, preserves shape, but gaps appear between features:

```js
features.forEach(f => {
  const val = f.properties.population;
  const area = d3.geoArea(f) * 510e6; // approx km²
  // Scale factor: sqrt(value / area) normalized to reasonable range
  f.properties._scale = Math.sqrt(val / area) / maxRatio;
});

svg.selectAll("path").data(features).join("path")
  .attr("d", f => {
    const centroid = path.centroid(f);
    const s = f.properties._scale;
    // Scale path around its centroid
    return `${path(f)}`;  // see transform approach below
  })
  .attr("transform", f => {
    const [cx, cy] = path.centroid(f);
    const s = f.properties._scale;
    return `translate(${cx * (1 - s)}, ${cy * (1 - s)}) scale(${s})`;
  });
```

The transform approach is simpler but scales strokes. For clean strokes, compute scaled paths with a custom `d3.geoTransform`:

```js
function scaledPath(feature, scaleFactor) {
  const [cx, cy] = path.centroid(feature);
  const transform = d3.geoTransform({
    point(x, y) {
      this.stream.point(
        cx + (x - cx) * scaleFactor,
        cy + (y - cy) * scaleFactor
      );
    }
  });
  return d3.geoPath(transform)(feature);
}
```

### Dorling Cartogram

Replace geographic shapes with circles sized by data value, positioned by force simulation:

```js
const nodes = features.map(f => {
  const [x, y] = path.centroid(f);
  return { feature: f, x, targetX: x, y, targetY: y,
           r: radius(f.properties.population) };
});

const sim = d3.forceSimulation(nodes)
  .force("x", d3.forceX(d => d.targetX).strength(0.05))
  .force("y", d3.forceY(d => d.targetY).strength(0.05))
  .force("collide", d3.forceCollide(d => d.r + 1).iterations(4))
  .stop();

for (let i = 0; i < 300; i++) sim.tick(); // more iterations for stable layout
```

Low position strength (~0.05) allows circles to spread. Higher strength (~0.5) keeps them closer to true position but allows overlap. The trade-off between geographic fidelity and readability is the core design decision.

## Flow Maps

Visualize movement between origins and destinations — migration, trade, commute patterns.

### Great-Circle Arcs

D3 renders `LineString` coordinates as geodesic curves automatically. For origin-destination pairs:

```js
const flows = [
  { origin: [-73.9, 40.7], dest: [2.3, 48.9], volume: 1200 },  // NYC → Paris
  { origin: [-73.9, 40.7], dest: [139.7, 35.7], volume: 800 }, // NYC → Tokyo
];

const strokeScale = d3.scaleSqrt()
  .domain(d3.extent(flows, d => d.volume))
  .range([0.5, 6]);

svg.selectAll(".flow").data(flows).join("path")
  .attr("class", "flow")
  .attr("d", d => path({
    type: "LineString",
    coordinates: [d.origin, d.dest]
  }))
  .attr("fill", "none")
  .attr("stroke", "#e63946")
  .attr("stroke-width", d => strokeScale(d.volume))
  .attr("stroke-opacity", 0.6)
  .attr("stroke-linecap", "round");
```

**Always `scaleSqrt` for stroke width** — same reasoning as circle radius. Linear stroke exaggerates high-volume flows.

### Curved Arcs (Non-Geodesic)

For maps where straight projected lines overlap (e.g., many flows from one hub), add curvature by inserting a control point:

```js
function curvedArc(source, target, projection, curvature = 0.3) {
  const [sx, sy] = projection(source);
  const [tx, ty] = projection(target);
  const mx = (sx + tx) / 2, my = (sy + ty) / 2;
  const dx = tx - sx, dy = ty - sy;
  // Perpendicular offset — curvature controls how far the arc bows
  const cx = mx - dy * curvature, cy = my + dx * curvature;
  return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`;
}
```

Add arrowheads with SVG markers. Scale marker size with stroke width or use a fixed-size marker at the end of the path.

### Flow Direction

Animate flow direction with `stroke-dashoffset`:

```js
svg.selectAll(".flow")
  .attr("stroke-dasharray", "4 4")
  .each(function() {
    d3.select(this).append("animate")
      .attr("attributeName", "stroke-dashoffset")
      .attr("from", "0").attr("to", "-8")
      .attr("dur", "1s").attr("repeatCount", "indefinite");
  });
```

Or use CSS: `animation: dash 1s linear infinite;` with `@keyframes dash { to { stroke-dashoffset: -8; } }`.

### Bundled Flows

When many flows cross the same region, bundle them to reduce visual clutter. See `hierarchy-edge-bundling` skill for the Holten bundling algorithm. For geographic flows, a simpler approach groups flows by destination region and draws them through shared waypoints.

## Geographic Label Placement

### Centroid Labels

Simple but often places labels outside concave features (e.g., label for Florida ends up in the Gulf):

```js
svg.selectAll("text").data(features).join("text")
  .attr("x", d => path.centroid(d)[0])
  .attr("y", d => path.centroid(d)[1])
  .attr("text-anchor", "middle")
  .attr("font-size", "10px")
  .text(d => d.properties.name);
```

### Pole of Inaccessibility

The point farthest from any edge — always inside the polygon. Better than centroid for concave or elongated shapes. Use the `polylabel` library:

```js
import polylabel from "https://cdn.jsdelivr.net/npm/polylabel@2/+esm";

features.forEach(f => {
  if (f.geometry.type === "Polygon") {
    // polylabel works on projected coordinates
    const projected = f.geometry.coordinates.map(ring =>
      ring.map(([lon, lat]) => projection([lon, lat]) ?? [0, 0])
    );
    const [x, y] = polylabel(projected, 1.0); // precision in pixels
    f.properties._labelX = x;
    f.properties._labelY = y;
  } else {
    // MultiPolygon — use largest polygon
    const largest = f.geometry.coordinates
      .map(poly => poly)
      .sort((a, b) => d3.polygonArea(b[0].map(c => projection(c) ?? [0, 0]))
                      - d3.polygonArea(a[0].map(c => projection(c) ?? [0, 0])))[0];
    const projected = largest.map(ring =>
      ring.map(([lon, lat]) => projection([lon, lat]) ?? [0, 0])
    );
    const [x, y] = polylabel(projected, 1.0);
    f.properties._labelX = x;
    f.properties._labelY = y;
  }
});
```

### Collision Avoidance

For dense maps where labels overlap, use force simulation to nudge labels apart:

```js
const labelNodes = features.map(f => ({
  feature: f,
  x: f.properties._labelX,
  y: f.properties._labelY,
  targetX: f.properties._labelX,
  targetY: f.properties._labelY,
}));

const sim = d3.forceSimulation(labelNodes)
  .force("x", d3.forceX(d => d.targetX).strength(0.5))
  .force("y", d3.forceY(d => d.targetY).strength(0.5))
  .force("collide", d3.forceCollide(8)) // approximate text half-height
  .stop();

for (let i = 0; i < 60; i++) sim.tick();
```

This pushes labels apart while keeping them near their geographic anchor. For publication-quality labels, measure text width with `ctx.measureText()` or a hidden SVG element and use rectangular collision.

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

Re-project on every zoom instead of transforming a group — avoids stroke scaling and is the right approach for Canvas:

```js
const [baseScale, baseTranslate] = [projection.scale(), projection.translate()];

function zoomed({ transform }) {
  projection
    .scale(baseScale * transform.k)
    .translate([transform.x + transform.k * baseTranslate[0],
                transform.y + transform.k * baseTranslate[1]]);
  render(); // full re-render with updated projection
}

svg.call(d3.zoom().scaleExtent([1, 12]).on("zoom", zoomed));
```

**Performance at high zoom**: re-projecting 3000+ features on every zoom frame is expensive. Throttle with `requestAnimationFrame` and skip features outside the visible viewport:

```js
function render() {
  context.clearRect(0, 0, width, height);
  const visibleBounds = [projection.invert([0, 0]), projection.invert([width, height])];
  for (const f of features) {
    // Quick centroid check — skip features clearly outside viewport
    const c = d3.geoCentroid(f);
    if (c[0] < visibleBounds[0][0] - 5 || c[0] > visibleBounds[1][0] + 5) continue;
    context.beginPath(); path(f);
    context.fillStyle = color(f.properties.value);
    context.fill();
  }
  // borders, etc.
}
```

## Tile Layers

Use `d3-tile` for raster tile backgrounds (OpenStreetMap, etc.) behind D3 vector overlays:

```js
import { tile as d3tile } from "https://cdn.jsdelivr.net/npm/d3-tile@1/+esm";

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

### Zoomable Tile Map (Canvas)

For smooth tile zooming, render tiles to Canvas and cache loaded images:

```js
const tileCache = new Map();

function loadTile(url) {
  if (tileCache.has(url)) return Promise.resolve(tileCache.get(url));
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => { tileCache.set(url, img); resolve(img); };
    img.onerror = reject;
    img.src = url;
  });
}

async function renderTiles(transform) {
  const tiles = d3tile()
    .size([width, height])
    .scale(transform.k * baseScale * 2 * Math.PI)
    .translate([transform.x + transform.k * baseTx, transform.y + transform.k * baseTy])
    ();

  for (const [x, y, z] of tiles) {
    const url = `https://tile.openstreetmap.org/${z}/${x}/${y}.png`;
    try {
      const img = await loadTile(url);
      const tx = (x + tiles.translate[0]) * tiles.scale;
      const ty = (y + tiles.translate[1]) * tiles.scale;
      context.drawImage(img, tx, ty, tiles.scale, tiles.scale);
    } catch (e) { /* tile unavailable */ }
  }
}
```

Cache eviction: limit cache to ~200 tiles. LRU or just clear when count exceeds threshold.

### Tile Providers

| Provider | URL pattern | Notes |
|----------|------------|-------|
| OpenStreetMap | `tile.openstreetmap.org/{z}/{x}/{y}.png` | Free, attribution required |
| Stamen Toner | `tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png` | Requires API key |
| CartoDB Positron | `basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` | Light minimal style |
| CartoDB Dark | `basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png` | Dark mode maps |

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

// Centroid (geographic center of mass, spherical)
d3.geoCentroid(feature); // [lon, lat]

// Bounding box
d3.geoBounds(feature); // [[west, south], [east, north]]

// Area (steradians — multiply by Earth radius² for km²)
d3.geoArea(feature) * 6371 * 6371; // km²
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

**Performance**: `d3.geoDistance` is O(1) per pair but testing all features is O(n). For 10K+ features, pre-build a spatial index. A simple grid in lon-lat space works:

```js
// Build spatial grid (10° cells)
const grid = new Map();
features.forEach(f => {
  const [lon, lat] = d3.geoCentroid(f);
  const key = `${Math.floor(lon / 10)},${Math.floor(lat / 10)}`;
  if (!grid.has(key)) grid.set(key, []);
  grid.get(key).push(f);
});

// Query: check only nearby cells
function nearbyFeatures(lon, lat, radiusDeg) {
  const cellRadius = Math.ceil(radiusDeg / 10) + 1;
  const cx = Math.floor(lon / 10), cy = Math.floor(lat / 10);
  const candidates = [];
  for (let dx = -cellRadius; dx <= cellRadius; dx++)
    for (let dy = -cellRadius; dy <= cellRadius; dy++) {
      const cell = grid.get(`${cx + dx},${cy + dy}`);
      if (cell) candidates.push(...cell);
    }
  return candidates.filter(f =>
    d3.geoDistance(d3.geoCentroid(f), [lon, lat]) * 180 / Math.PI < radiusDeg);
}
```

For nearest-point queries, use `d3-geo-voronoi`:

```js
import { geoVoronoi } from "https://cdn.jsdelivr.net/npm/d3-geo-voronoi@2/+esm";
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

### Versor Rotation (3-Axis)

For proper globe rotation that feels like dragging a physical sphere (no gimbal lock), use the `versor` library with quaternion math:

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

### Auto-Rotating Globe

```js
const timer = d3.timer(elapsed => {
  projection.rotate([elapsed * 0.01, -15]); // 0.01°/ms ≈ 10°/s
  render();
});
// Stop on interaction: timer.stop() in drag.on("start")
```

### Back-Face Rendering

To show back-hemisphere features with reduced opacity:

```js
// Front face
context.globalAlpha = 1;
context.beginPath(); path(land); context.fill();

// Back face — separate projection with clipAngle(180) and inverted visibility
const backProjection = d3.geoOrthographic()
  .rotate(projection.rotate())
  .scale(projection.scale())
  .translate(projection.translate())
  .clipAngle(180); // show everything
const backPath = d3.geoPath(backProjection, context);

// Draw back-facing features first (underneath), dimmed
context.globalAlpha = 0.15;
context.beginPath(); backPath(land); context.fill();
context.globalAlpha = 1;
// Then draw front-facing on top
context.beginPath(); path(land); context.fill();
```

## Canvas Map Architecture

For production Canvas maps, use a multi-canvas stack. Each layer redraws independently — editing a tooltip doesn't repaint 3000 county fills.

```
┌─────────────────────────┐
│   SVG overlay           │ ← tooltips, hover highlight, legend
│   (position: absolute)  │
├─────────────────────────┤
│   Interaction canvas    │ ← cursor tracking, selection highlight
├─────────────────────────┤
│   Data canvas           │ ← choropleth fills, borders (redraws on zoom)
├─────────────────────────┤
│   Tile canvas           │ ← raster tiles (redraws on pan/zoom)
└─────────────────────────┘
```

```js
function createCanvasStack(container, width, height) {
  const dpr = window.devicePixelRatio || 1;
  const layers = {};
  for (const name of ["tiles", "data", "interaction"]) {
    const canvas = container.append("canvas")
      .attr("width", width * dpr).attr("height", height * dpr)
      .style("width", `${width}px`).style("height", `${height}px`)
      .style("position", "absolute").style("left", "0").style("top", "0");
    const ctx = canvas.node().getContext("2d");
    ctx.scale(dpr, dpr);
    layers[name] = { canvas, ctx };
  }
  // SVG overlay on top
  layers.overlay = container.append("svg")
    .attr("width", width).attr("height", height)
    .style("position", "absolute").style("left", "0").style("top", "0");
  return layers;
}
```

### Hit Detection on Canvas Maps

**Color picking** — the standard approach. Render each feature with a unique encoded color to a hidden canvas, read pixel under cursor:

```js
const hiddenCanvas = document.createElement("canvas");
hiddenCanvas.width = width; hiddenCanvas.height = height;
const hctx = hiddenCanvas.getContext("2d", { willReadFrequently: true });
const hiddenPath = d3.geoPath(projection, hctx);

// Build lookup: encode feature index as RGB
const indexToFeature = new Map();
features.forEach((f, i) => {
  const r = (i + 1) >> 16 & 255;   // +1 so index 0 isn't black (background)
  const g = (i + 1) >> 8 & 255;
  const b = (i + 1) & 255;
  indexToFeature.set((r << 16) | (g << 8) | b, f);
  hctx.beginPath(); hiddenPath(f);
  hctx.fillStyle = `rgb(${r},${g},${b})`;
  hctx.fill();
});

// Lookup on mousemove
canvas.on("mousemove", (event) => {
  const [mx, my] = d3.pointer(event);
  const [r, g, b] = hctx.getImageData(mx, my, 1, 1).data;
  const key = (r << 16) | (g << 8) | b;
  const feature = indexToFeature.get(key);
  // feature is the hovered county/state/country, or undefined
});
```

Supports up to 16.7M features (2²⁴). Anti-aliasing can cause edge artifacts — disable with `hctx.imageSmoothingEnabled = false` and ensure no strokes on the hidden canvas.

**`d3.geoContains` approach** — simpler but O(n) per mousemove:

```js
canvas.on("mousemove", (event) => {
  const lonlat = projection.invert(d3.pointer(event));
  if (!lonlat) return;
  const hit = features.find(f => d3.geoContains(f, lonlat));
});
```

Good for ≤200 features. For 500+, color picking is faster.

### Frame Budgeting for Map Zoom

During continuous zoom/pan, coalesce render calls:

```js
let dirty = false;
function markDirty() {
  if (!dirty) {
    dirty = true;
    requestAnimationFrame(() => { dirty = false; render(); });
  }
}

// Zoom handler calls markDirty instead of render directly
d3.zoom().on("zoom", (event) => {
  currentTransform = event.transform;
  markDirty();
});
```

## Large Geometry

### Simplification

Pre-simplified TopoJSON (lower quantization) is the first line of defense. The `topojson` CLI creates multiple resolutions:

```bash
# Full detail
topojson -q 1e6 -o counties-full.json counties.geojson
# Simplified for overview
topojson -q 1e4 -s 1e-7 -o counties-simple.json counties.geojson
```

Client-side simplification with `topojson-simplify`:

```js
import { presimplify, simplify } from "https://cdn.jsdelivr.net/npm/topojson-simplify@3/+esm";

const presimplified = presimplify(topology);
const simplified = simplify(presimplified, 0.01); // min triangle area threshold
const features = topojson.feature(simplified, simplified.objects.counties);
```

### Level-of-Detail by Zoom

Switch geometry resolution based on zoom level:

```js
const geometries = {
  overview: await d3.json("counties-10m.json"),  // 10m = simplified
  detail: null, // lazy-load
};

async function getGeometry(zoomLevel) {
  if (zoomLevel > 4 && !geometries.detail) {
    geometries.detail = await d3.json("counties-full.json");
  }
  return zoomLevel > 4 ? geometries.detail : geometries.overview;
}
```

| Zoom level | Features visible | Geometry |
|------------|-----------------|----------|
| 1–2 | Whole country | 110m (coarse) |
| 3–5 | State-level | 10m (medium) |
| 6+ | County-level | Full resolution, lazy-loaded |

### Streaming Parse

For very large GeoJSON (50MB+), parse with streaming to avoid blocking the main thread:

```js
// In a Web Worker
const response = await fetch("large-dataset.geojson");
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  // Parse complete features as they arrive
  // (requires a streaming JSON parser like oboe.js or custom feature extraction)
}
```

In practice, prefer TopoJSON (80% smaller) and lazy-loading over streaming raw GeoJSON.

## Projection Transitions

Smoothly morph between projections. See `shape-morphing` skill for the general technique. Geographic-specific approach:

```js
function interpolateProjection(proj0, proj1) {
  // Create interpolator between two projections
  return function(t) {
    return function(point) {
      const p0 = proj0(point), p1 = proj1(point);
      if (!p0 || !p1) return null;
      return [p0[0] * (1 - t) + p1[0] * t, p0[1] * (1 - t) + p1[1] * t];
    };
  };
}

// Usage with d3.transition
const proj0 = d3.geoMercator().fitSize([w, h], geo);
const proj1 = d3.geoEqualEarth().fitSize([w, h], geo);

svg.selectAll("path").transition().duration(2000)
  .attrTween("d", function(d) {
    const interp = interpolateProjection(proj0, proj1);
    return t => d3.geoPath(interp(t))(d);
  });
```

This interpolates in screen space (not spherical). For smoother results on globe transitions, use `d3.geoProjection` with interpolated projection parameters.

## Small Multiples (Faceted Maps)

Show the same geography repeated for different time periods or categories. See `small-multiples` skill for layout math.

```js
const months = d3.groups(data, d => d.month);
const cols = 4, cellW = width / cols, cellH = cellW * 0.7;

months.forEach(([month, values], i) => {
  const col = i % cols, row = Math.floor(i / cols);
  const g = svg.append("g")
    .attr("transform", `translate(${col * cellW}, ${row * cellH})`);

  const proj = d3.geoAlbersUsa().fitSize([cellW - 10, cellH - 30], nation);
  const p = d3.geoPath(proj);
  const valueMap = new Map(values.map(d => [d.fips, d.value]));

  g.selectAll("path").data(counties).join("path")
    .attr("d", p)
    .attr("fill", d => color(valueMap.get(d.id)) ?? "#eee");

  g.append("text").attr("x", cellW / 2).attr("y", 14)
    .attr("text-anchor", "middle").attr("font-size", "11px")
    .text(month);
});
```

Key: create a **new projection per cell** with `fitSize` so each mini-map fills its cell. Share the color scale across all cells for comparison.

## Performance

| Scenario | Features | Approach |
|----------|----------|----------|
| Interactive thematic | <500 | SVG — full DOM events, transitions |
| Choropleth US states | ~50 | SVG — simple, accessible |
| Choropleth US counties | ~3100 | Canvas fill + SVG legend/tooltip overlay |
| Point overlay | <5K | SVG circles |
| Point overlay | 5K–50K | Canvas circles |
| Point overlay | 50K+ | Canvas + `globalCompositeOperation` density |
| Dense tile + vector | Any | Multi-canvas stack |
| Globe with rotation | Any | Canvas — redraws ~60fps |

**Batch by fill color.** Pre-render static layers to offscreen canvas. Simplify geometry at load time for zoomed-out views.

### Performance Checklist

1. **DPR scaling** — set canvas size to `width * dpr`, CSS size to `width`, scale context by `dpr`. See `canvas-rendering` skill.
2. **Batch fills** — group features by color, one `beginPath`/`fill` per color.
3. **Mesh for borders** — one `topojson.mesh()` path instead of per-feature strokes.
4. **Frame budgeting** — coalesce zoom/pan events into single `requestAnimationFrame`.
5. **Viewport culling** — skip features outside visible bounds during zoom.
6. **LOD switching** — simplified geometry for overview, full detail on zoom-in.
7. **Lazy loading** — load detailed geometry only when zoom demands it.

## Common Pitfalls

1. **Coordinate order.** GeoJSON uses `[longitude, latitude]`, not `[lat, lon]`. Most common geographic data bug. Google Maps API, Leaflet, and many databases use `[lat, lon]` — always check.

2. **AlbersUsa gotchas.** No `rotate()`, `center()`, or `clipAngle()`. `invert()` returns `null` outside composite regions (including the gaps between AK/HI/lower 48). Cannot be used with `d3.tile`.

3. **Antimeridian cutting.** Features crossing 180° need proper cutting. D3 handles this in rendering, but raw coordinates may have artifacts. Reputable TopoJSON sources are pre-cut. If you create your own geometry, use `d3.geoProject` in the `d3-geo-projection` CLI.

4. **Winding order.** GeoJSON specifies counterclockwise outer rings (RFC 7946). Reversed winding fills the globe minus your target — a black rectangle that covers everything except your feature. Fix with `@turf/rewind` or check with `d3.geoArea()` (if > 2π steradians, winding is inverted).

5. **`fitSize` with multiple features.** Fits the bounding box of all features passed. To fit one region but render more, call `fitSize` on the region first, then render everything.

6. **Null projections.** `projection([lon, lat])` returns `null` outside the clip region (e.g., back of globe). Always guard: `projection(point) ?? [NaN, NaN]`.

7. **Stroke scaling on zoom.** Transforming a `<g>` scales strokes. Three fixes: divide `stroke-width` by `transform.k`, use `vector-effect: non-scaling-stroke` (SVG only, no transitions), or re-project instead of transforming (Canvas).

8. **FIPS code type mismatch.** TopoJSON stores FIPS as numbers; CSV data often has leading zeros as strings. Normalize before joining. State FIPS: `String(id).padStart(2, "0")`. County FIPS: `String(id).padStart(5, "0")`.

9. **Canvas anti-aliasing on hidden canvas.** Color-picking hit detection breaks when anti-aliasing blends unique colors at feature edges. Set `imageSmoothingEnabled = false` on the hidden context and don't draw strokes.

10. **Re-projecting on every frame.** During zoom animation, computing `d3.geoPath` for 3000+ features 60 times/second is slow. Use geometric zoom (transform a `<g>`) for SVG, or viewport-cull for Canvas. Reserve projection-based zoom for final renders.

11. **`d3.geoArea` units.** Returns steradians (solid angle), not km². Multiply by `R²` (Earth radius squared, 6371² ≈ 40.6M) for km². Small features have very small values — don't confuse with zero.

12. **Forgetting the Sphere.** World maps without a Sphere background path have no water. Draw `{ type: "Sphere" }` first with a light fill. It also serves as the clip boundary for graticules.

13. **`topojson.mesh` with wrong filter.** `(a, b) => a !== b` gives internal borders. `(a, b) => a === b` gives the outer boundary. No filter gives all borders (internal + outer). Getting this backwards doubles stroke weight on some edges.

14. **Mercator scale misleads.** Areas near poles appear much larger. Never use Mercator for choropleth — use an equal-area projection. Greenland is not the size of Africa.

## References

- [D3 Geo](https://d3js.org/d3-geo) — projection and path API
- [D3 Geo Projection (extended)](https://github.com/d3/d3-geo-projection)
- [TopoJSON spec](https://github.com/topojson/topojson-specification) and [client API](https://github.com/topojson/topojson-client)
- [topojson-simplify](https://github.com/topojson/topojson-simplify) — client-side simplification
- [d3-tile](https://github.com/d3/d3-tile) — raster tile rendering
- [d3-hexbin](https://github.com/d3/d3-hexbin) — hexagonal binning
- [d3-geo-voronoi](https://github.com/Fil/d3-geo-voronoi) — spherical Voronoi diagrams
- [polylabel](https://github.com/mapbox/polylabel) — pole of inaccessibility for label placement
- [versor](https://github.com/Fil/versor) — quaternion rotation for globes
- [US Atlas](https://github.com/topojson/us-atlas) / [World Atlas](https://github.com/topojson/world-atlas)
- [Observable: Choropleth](https://observablehq.com/@d3/choropleth)
- [Observable: Bivariate Choropleth](https://observablehq.com/@d3/bivariate-choropleth)
- [Observable: Non-Contiguous Cartogram](https://observablehq.com/@d3/non-contiguous-cartogram)
- [Observable: Zoom to Bounding Box](https://observablehq.com/@d3/zoom-to-bounding-box)
- [Observable: Versor Dragging](https://observablehq.com/@d3/versor-dragging)
- [Observable: Zoomable Map Tiles](https://observablehq.com/@d3/zoomable-map-tiles)
- [Joshua Stevens: Bivariate Choropleth](https://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/)
