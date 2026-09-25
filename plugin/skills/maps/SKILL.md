---
name: maps
description: "Geographic maps in D3: projection choice (geoEqualEarth, geoAlbersUsa, geoMercator, geoOrthographic, conic), fitSize/fitExtent, TopoJSON feature/mesh/merge/neighbors, us-atlas and world-atlas, pre-projected geoIdentity data, winding order, choropleth, bivariate choropleth, bubble maps, Dorling and non-contiguous cartograms, hexbin maps, flow maps, globes with versor drag, zoom-to-feature, canvas map layers and color-pick hit detection, projection transitions, geometry LOD, tile layers and MapLibre overlays."
---

# Maps

A map makes two choices before any data shows up: how the sphere goes flat (projection) and what mark carries the value (map form). Get either wrong and the map lies about area or hides the pattern. Most other map bugs come from geometry plumbing: winding order, mesh versus feature, and projecting data that's already projected.

Pipeline: TopoJSON → `topojson.feature/mesh/merge` → projection → `d3.geoPath` → SVG/Canvas. Layer order: tiles → fills → borders → points → labels → legend.

## Which projection

| If the map... | Use | Not |
|---|---|---|
| encodes magnitude by area (choropleth, density, hex bins, cartograms) | equal-area: `geoEqualEarth` (world), `geoAlbers`/`geoConicEqualArea` (continent), `geoAzimuthalEqualArea` (polar) | Mercator: Greenland reads as big as Africa |
| is the US with Alaska and Hawaii | `geoAlbersUsa` (composite, equal-area) | anything that needs `rotate`, `center`, `clipAngle` or tiles; AlbersUsa has none of them |
| is a general reference world map | compromise: `geoNaturalEarth1` (Robinson, Winkel Tripel via d3-geo-projection) | equal-area when shapes matter more than areas |
| sits on raster/vector tiles, or needs local angles (navigation, weather) | `geoMercator` | Mercator for anything else: it's conformal, which is why tiles use it, not because it's good |
| is a region wider E-W than N-S | conic (`geoConicEqualArea`, standard parallels inside the region) | |
| is a region taller N-S | transverse cylindrical (`geoTransverseMercator`) | |
| is a roundish region or a pole | azimuthal | |
| is a draggable globe | `geoOrthographic`, versor drag | 2-axis lon/lat drag (locks at the poles) |

Center on `[lon, lat]` with `.rotate([-lon, -lat])`: rotation angles are negated. Unsure about a region: projectionwizard.org.

## Which map form

| If the data is... | Form | Rule |
|---|---|---|
| a rate or ratio per region (per capita, %) | choropleth | never raw counts: big regions dominate. Classify with quantile/quantize/threshold (see legibility) |
| two rates per region | bivariate choropleth, 3×3 Stevens grid | legend must be the 3×3 grid with axis labels, or it's unreadable |
| a count or total per region or point | bubble map, `scaleSqrt` radius | never linear radius (area grows with r²) |
| counts where bubbles overlap badly | Dorling cartogram (collide force, weak anchor) | |
| a magnitude that should reshape regions | non-contiguous cartogram (scale each region around its centroid) | |
| thousands of points | hex bins in screen space on an equal-area projection | Mercator hexes cover more real area near the poles |
| origin-destination volumes | flow map, `scaleSqrt` stroke width | LineStrings draw as great circles on their own; use curved screen arcs for many flows from one hub |
| global with a focus region | orthographic globe | |

Details and code: `references/map-forms.md`.

## Data

**Never synthesize geometry.** Load `us-atlas@3` or `world-atlas@2`: pre-cut at the antimeridian, correctly wound, topologically shared borders.

- `topojson.feature(topo, obj)` → polygons to **fill**. `topojson.mesh(topo, obj, (a, b) => a !== b)` → internal borders to **stroke**, each drawn once. `a === b` gives the outer boundary. `topojson.merge` dissolves regions into one outline.
- us-atlas FIPS ids are strings in the TopoJSON, but joins against CSVs that parsed them as numbers drop leading zeros: normalize with `String(id).padStart(5, "0")` (counties) or `2` (states).
- World maps need `{type: "Sphere"}`: drawn for the ocean, and it's what you fit to.

## Traps

- **Whole-sphere fill.** d3-geo wants **clockwise** exterior rings, the opposite of GeoJSON RFC 7946. A reversed ring means "everything except this shape" and fills the globe. Detect: `d3.geoArea(f) > 2 * Math.PI`. Fix: `@turf/rewind` with `{reverse: true}`, or use the atlases, which are already wound for d3.
- **Stroking features instead of the mesh.** Stroking every feature draws shared borders twice (darker, aliased) and strokes the coastline too. Fill features, stroke `mesh(…, (a, b) => a !== b)`, then stroke the outer boundary separately.
- **Hand-tuned `scale`/`translate`.** Use `projection.fitSize([w, h], geo)` or `fitExtent([[m, m], [w - m, h - m]], geo)`. Fit to the merged outline or the Sphere, not a features array (pass a FeatureCollection). Refit on resize.
- **Projecting pre-projected data.** us-atlas `*-albers-10m.json` files are already projected with AlbersUsa into a 975×610 frame. Render with `d3.geoPath()` (null projection) or `d3.geoIdentity().fitSize(...)` to rescale. Feeding them to `geoAlbersUsa` projects them twice and draws garbage or nothing.
- **Upside-down maps.** `geoIdentity().reflectY(true)` is only for planar data whose y grows northward (state-plane or UTM coordinates from a shapefile). The albers atlas files already have y growing downward: reflecting flips the map. Raw lon/lat through an identity is also upside-down: give it a real projection instead.
- **`projection(p)` doesn't clip.** Only `geoPath` streams clip. Points on the back of a globe still get coordinates: test `d3.geoDistance(p, center) < Math.PI / 2`. `geoAlbersUsa` returns `null` outside its insets, so guard with `?? [NaN, NaN]` or filter.
- **Stroke scaling on zoom.** A transformed `<g>` scales strokes: set `vector-effect: non-scaling-stroke`, divide width by `k`, or re-project.
- **Re-projecting every frame.** `geoPath` over 3000+ features at 60fps is slow. SVG: transform a `<g>` (geometric zoom). Canvas: re-project but cull features outside the viewport.
- **Label at the centroid.** Concave shapes put it outside (Florida's lands in the Gulf). Use polylabel on projected coordinates, largest polygon of a MultiPolygon.
- **`d3.geoArea` is in steradians.** Multiply by 6371² for km².

## Rendering decisions

| Situation | Do |
|---|---|
| <5K features, hover/click | SVG |
| 5K-100K features | Canvas data layer + SVG overlay for legend and tooltips |
| 100K+ features, continuous 0-22 zoom, streets/terrain basemap | escalate: MapLibre GL with a D3 overlay |
| Canvas hit-testing ≤200 features | `d3.geoContains` per feature |
| Canvas hit-testing more | color-pick on a hidden canvas (no strokes; unmatched colors are misses) |
| Canvas choropleth | batch by fill color: one `beginPath`/`fill` per class, not per feature |
| Click to zoom to a region | `path.bounds(d)` → `k = 0.9 / max(dx / w, dy / h)` clamped to the scale extent → `zoom.transform` with `zoomIdentity.translate(w / 2, h / 2).scale(k).translate(-cx, -cy)` |
| Canvas zoom | re-project: `scale(s0 * k)`, `translate([x + k * t0[0], y + k * t0[1]])` |
| Detail at depth | 110m → 50m → 10m world-atlas by zoom level, or `topojson-simplify` |
| Dark mode | separate scheme, not inverted: dark gray ground, mid-gray borders, multi-hue sequential ramp |

Canvas stack, bottom to top: tile canvas → data canvas → interaction canvas (highlight) → SVG (legend, tooltips).

## References

- `references/projections.md`: regional parameters, rotation, fitting, pre-projected data, AlbersUsa limits, projection transitions, versor globe drag.
- `references/map-forms.md`: choropleth draw order, selective mesh, dissolve, greedy map coloring, bivariate palette, Dorling and non-contiguous cartograms, hexbin, flow arcs, polylabel.
- `references/rendering.md`: canvas layers, color-pick hit detection, fill batching, zoom-to-feature, projection zoom, LOD, MapLibre overlay.
- `examples/geographic-maps.html`: canvas choropleth with color-pick hover, Dorling bubbles, world flow map with zoom-to-feature, globe with back-face rendering.
