# Map forms

From the v2 `cartography` skill. Open when building a choropleth, bivariate choropleth, bubble map, cartogram, hexbin, flow map, or placing region labels.

## Loading and topology

```js
import * as topojson from "https://cdn.jsdelivr.net/npm/topojson-client@3/+esm";
const us = await d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json");
const counties  = topojson.feature(us, us.objects.counties).features;
const stateMesh = topojson.mesh(us, us.objects.states, (a, b) => a !== b); // internal borders
const nation    = topojson.merge(us, us.objects.states.geometries);        // dissolved outline
const world     = await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json");
const land      = topojson.feature(world, world.objects.land);
```

- Dissolve groups (Census divisions from states): `topojson.merge(us, geometries.filter(...))`.
- Borders between groups only: `topojson.mesh(us, us.objects.states, (a, b) => a !== b && regionOf.get(a.id) !== regionOf.get(b.id))`.
- Ids are zero-padded strings (`"06037"`). Pad the other side of the join, not the atlas.

## Choropleth draw order

Fills, then internal mesh, then the outer boundary:

```js
function drawChoropleth(ctx, path, features, value, color, stateMesh, nation) {
  for (const f of features) {
    ctx.beginPath(); path(f);
    ctx.fillStyle = color(value.get(f.id)) ?? "#ccc"; ctx.fill();
  }
  ctx.beginPath(); path(stateMesh);
  ctx.strokeStyle = "#fff"; ctx.lineWidth = 0.5; ctx.stroke();
  ctx.beginPath(); path(nation);
  ctx.strokeStyle = "#333"; ctx.lineWidth = 1; ctx.stroke();
}
```

Missing data gets its own color outside the ramp.

## Map coloring (categorical regions)

Greedy coloring over `topojson.neighbors`. It isn't guaranteed to finish in four colors, so supply five or six:

```js
const neighbors = topojson.neighbors(us.objects.states.geometries);
const assigned = [];
neighbors.forEach((nbrs, i) => {
  const used = new Set(nbrs.map(j => assigned[j]));
  assigned[i] = palette.find(c => !used.has(c));
});
```

## Bivariate choropleth

Each variable goes through `scaleQuantile(values, [0, 1, 2])`, and the pair indexes a 3×3 grid. Joshua Stevens palette (rows = y low→high, columns = x low→high):

```js
const biColors = [
  ["#e8e8e8", "#ace4e4", "#5ac8c8"],
  ["#dfb0d6", "#a5add3", "#5698b9"],
  ["#be64ac", "#8c62aa", "#3b4994"],
];
const biColor = d => biColors[qy(d.y)]?.[qx(d.x)] ?? "#ccc";
```

The legend is the 3×3 grid with both axes labeled. Without it the map can't be read.

## Bubbles and Dorling cartograms

Radius with `scaleSqrt`. Nudge overlapping circles apart while anchoring them to their projected location:

```js
function settle(nodes) { // nodes: {x, y, r} in screen space
  for (const n of nodes) { n.tx = n.x; n.ty = n.y; }
  const sim = d3.forceSimulation(nodes)
    .force("x", d3.forceX(d => d.tx).strength(0.8))
    .force("y", d3.forceY(d => d.ty).strength(0.8))
    .force("collide", d3.forceCollide(d => d.r + 1).iterations(3))
    .stop();
  for (let i = 0; i < 120; i++) sim.tick();
  return nodes;
}
```

Anchor strength 0.8 keeps bubbles near their true location. ~0.3 gives a Dorling cartogram. At ~0.05 collision dominates and geography dissolves.

## Non-contiguous cartogram

Project, then scale each region around its projected centroid (factor from `scaleSqrt` of the value so area tracks value):

```js
function scaledPath(feature, projection, factor) {
  const [cx, cy] = d3.geoPath(projection).centroid(feature);
  const t = d3.geoTransform({
    point(x, y) { this.stream.point(cx + (x - cx) * factor, cy + (y - cy) * factor); }
  });
  return d3.geoPath({ stream: s => projection.stream(t.stream(s)) })(feature);
}
```

## Hex bins

```js
import { hexbin as d3Hexbin } from "https://cdn.jsdelivr.net/npm/d3-hexbin@0.2/+esm";
const hexbin = d3Hexbin().x(d => d.x).y(d => d.y)
  .radius(Math.min(width, height) / 40).extent([[0, 0], [width, height]]);
const bins = hexbin(projectedPoints);
const r = d3.scaleSqrt([0, d3.max(bins, b => b.length)], [0, hexbin.radius()]);
```

Bins live in screen space, so the projection must be equal-area or hexes near the poles cover more ground.

## Flow maps

A `LineString` through `geoPath` draws as a great circle, so long flows curve correctly on their own. Stroke width by `scaleSqrt`. For many flows fanning from one hub, bend screen-space arcs so they separate:

```js
function curvedArc(source, target, projection, curvature = 0.3) {
  const [sx, sy] = projection(source), [tx, ty] = projection(target);
  const mx = (sx + tx) / 2, my = (sy + ty) / 2, dx = tx - sx, dy = ty - sy;
  return `M${sx},${sy} Q${mx - dy * curvature},${my + dx * curvature} ${tx},${ty}`;
}
```

## Region labels

Centroids fall outside concave shapes. Use polylabel (`https://cdn.jsdelivr.net/npm/polylabel@2/+esm`), the point farthest from any edge: project the coordinates first, then `polylabel(projectedRings, 1.0)`. For a MultiPolygon, label the largest polygon by projected area.
