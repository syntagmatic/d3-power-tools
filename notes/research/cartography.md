# Cartography Research: State of the Art (March 2026)

Research for extending `skills/cartography/SKILL.md` beyond its current 395 lines.

## Current Coverage

The existing skill covers the core D3 geo stack thoroughly:

- **Projection selection** — 9-projection table (EqualEarth, Mercator, AlbersUsa, Albers, Orthographic, NaturalEarth1, Gnomonic, Winkel3, AzimuthalEqualArea, TransverseMercator) with when-to-use guidance
- **TopoJSON topology** — merge/dissolve, mesh filters, neighbors/four-color, FIPS joining
- **Bivariate choropleth** — 3x3 color matrix with Joshua Stevens palette
- **Bubble maps** — force-collision layout, Dorling cartogram
- **Hex binning** — d3Hexbin in screen space, area encoding, radius heuristics
- **Cartograms** — non-contiguous (scaled around centroid), Dorling
- **Flow maps** — great-circle rendering, curved arc control points
- **Labels** — polylabel pole-of-inaccessibility, force-based collision
- **Globe** — versor quaternion rotation, back-face rendering
- **Canvas multi-layer** — tile/data/interaction/SVG stack, color-pick hit detection, batch-by-fill
- **Zoom** — projection-based re-projection, viewport culling
- **Projection transitions** — screen-space interpolation
- **LOD** — pre-simplified TopoJSON, zoom-level switching
- **13 common pitfalls** — coordinate order, winding, antimeridian, FIPS types, stroke scaling, etc.

**Not covered**: vector tiles, PMTiles, MapLibre/Mapbox integration, dark mode, Snyder-based projection decision framework, Observable Plot geo marks, adaptive composite projections.

## Vector Tiles and PMTiles

### What PMTiles Is

[PMTiles](https://github.com/protomaps/PMTiles) is a single-file archive format for map tiles (vector or raster) that serves directly from static storage (S3, R2, GCS, any CDN) via HTTP range requests. No tile server needed. A full planet basemap is ~120 GB; regional extracts are practical for most projects.

### When to Add a Tile Basemap

Add tiles when your map needs **geographic context** (streets, water, terrain) that your data doesn't provide. Pure D3 maps excel at thematic visualization but struggle when users need wayfinding context or when the data covers a small region where country outlines aren't enough.

**Use tiles when**:
- Users need street-level context (city maps, facility locations)
- The map is a slippy/pannable map with 15+ zoom levels
- You need terrain, satellite, or pre-rendered labels as background
- The audience expects a "Google Maps-like" interaction model

**Skip tiles when**:
- It's a thematic map (choropleth, cartogram, bubble) at country/state level
- You control the exact projection (tiles lock you to Web Mercator mostly)
- The visualization IS the map (not data overlaid on a map)
- Self-contained HTML matters (tiles require network)

### D3 + d3-tile for Raster Tiles

The existing d3-tile approach renders raster tiles behind D3 vector layers. Pattern from Observable:

```js
const tile = d3.tile()
  .size([width, height])
  .scale(projection.scale() * 2 * Math.PI)
  .translate(projection([0, 0]));

// Fetch and render tiles
const tiles = tile();
const image = svg.selectAll("image")
  .data(tiles, d => d)
  .join("image")
    .attr("xlink:href", d => `https://tile.openstreetmap.org/${d[2]}/${d[0]}/${d[1]}.png`)
    .attr("x", d => (d[0] + tiles.translate[0]) * tiles.scale)
    .attr("y", d => (d[1] + tiles.translate[1]) * tiles.scale)
    .attr("width", tiles.scale)
    .attr("height", tiles.scale);
```

### D3 + Vector Tiles (GeoJSON)

D3 can render vector tiles directly as SVG/Canvas paths. The Observable vector tiles notebook fetches GeoJSON tiles and renders with `d3.geoPath`:

```js
const projection = d3.geoMercator()
  .center([-122.4183, 37.7750])
  .scale(Math.pow(2, 21) / (2 * Math.PI))
  .translate([width / 2, height / 2]);

const tile = d3.tile()
  .size([width, height])
  .scale(projection.scale() * 2 * Math.PI)
  .translate(projection([0, 0]));

const tiles = await Promise.all(tile().map(async d => {
  d.data = await fetch(`https://tile.nextzen.org/.../${d[2]}/${d[0]}/${d[1]}.json`)
    .then(r => r.json());
  return d;
}));
```

This gives full D3 styling control over every road, building, and water feature — but at the cost of performance at high zoom levels.

### PMTiles in the Browser

PMTiles serves tiles without a tile server. The typical integration path is PMTiles + MapLibre GL JS (see next section). For D3-only projects, you'd use the `pmtiles` JS library to read tile data and decode MVT (Mapbox Vector Tile) format, then render with Canvas or SVG. This is complex — most projects use MapLibre as the rendering layer.

```
PMTiles file (S3/R2/CDN)
    ↓ HTTP range requests
pmtiles.js (browser)
    ↓ decoded MVT → GeoJSON
MapLibre GL JS (WebGL rendering)
    ↓ or
d3.geoPath (Canvas/SVG, custom but slower)
```

### Deployment

- **Static hosting**: Upload `.pmtiles` to S3/R2/GCS, serve with CORS headers. No server.
- **Cost**: Pennies per month for storage; bandwidth is the main cost.
- **Regional extracts**: Use `pmtiles extract` to create city/country subsets from planet file.
- **Serverless decoding**: Google Cloud Run and Azure Container Apps support scale-to-zero with `go-pmtiles`.

## MapLibre/Mapbox Integration

### When to Use MapLibre GL JS vs Pure D3

| Factor | Pure D3 | MapLibre GL JS |
|--------|---------|----------------|
| Projection freedom | Any of 100+ projections | Web Mercator (+ globe in v5) |
| Tile basemaps | Manual with d3-tile | Built-in, performant |
| WebGL rendering | Manual (WebGL skill) | Built-in |
| Data bindings | Native D3 selections | Separate layer API |
| Self-contained HTML | Yes | Requires MapLibre JS (~300KB) + tile source |
| Max features (interactive) | ~5K SVG, ~100K Canvas | ~500K WebGL |
| Zoom levels | Typically 1-3 levels | 0-22 continuous |
| Label placement | Manual | Built-in collision detection |
| 3D terrain | No | Yes (v4+) |
| Globe view | d3.geoOrthographic | MapLibre v5 globe mode |

### D3 + MapLibre Integration Pattern

The proven pattern: MapLibre renders the basemap, D3 renders data in a synchronized SVG overlay. The key is a custom `d3.geoTransform` that delegates to MapLibre's projection:

```js
// Create MapLibre map
const map = new maplibregl.Map({
  container, style, center: [-122.4, 37.8], zoom: 12
});

// D3 SVG overlay
const svg = d3.select(map.getCanvasContainer())
  .append("svg")
  .style("position", "absolute")
  .style("pointer-events", "none");

// Bridge projection: MapLibre handles coordinates → pixels
function projectPoint(lon, lat) {
  const point = map.project(new maplibregl.LngLat(lon, lat));
  this.stream.point(point.x, point.y);
}
const transform = d3.geoTransform({ point: projectPoint });
const path = d3.geoPath().projection(transform);

// Sync on every map movement
function update() {
  svg.selectAll("path").attr("d", path);
  svg.selectAll("circle")
    .attr("cx", d => map.project(d.lngLat).x)
    .attr("cy", d => map.project(d.lngLat).y);
}
map.on("viewreset", update);
map.on("move", update);
map.on("moveend", update);
```

This gives you D3's data joins and transitions on top of MapLibre's tile rendering. The SVG overlay has `pointer-events: none` so map interaction passes through; add `pointer-events: all` to specific D3 elements that need clicks.

### When Each Approach Wins

**Pure D3 wins for**:
- Thematic maps (choropleth, cartogram, flow) where the data IS the map
- Non-Mercator projections (equal-area choropleth, globe, conic)
- Self-contained visualizations (single HTML file, no network dependency)
- Publication-quality static maps
- Small multiples of maps
- Observable notebooks and embeds

**MapLibre wins for**:
- Street-level context needed behind data
- Continuous zoom from world to building level
- Large point datasets (100K+) with WebGL rendering
- Users expect pan/zoom "slippy map" interaction
- 3D terrain visualization
- Tile-based basemaps (OSM, satellite, custom styles)

**Hybrid (MapLibre + D3 overlay) wins for**:
- Data-dense overlays on geographic context
- D3 transitions/animations over a basemap
- Complex interaction patterns (brushing, linking) on map data

## Projection Selection Depth

### Snyder's Decision Framework

The [Projection Wizard](https://projectionwizard.org/) implements John P. Snyder's systematic selection guideline. The hierarchy:

```
1. What distortion property matters?
   ├── Equal-area → preserves area (choropleth, density)
   ├── Conformal → preserves angles/shapes (navigation, weather)
   ├── Equidistant → preserves distance from center (range rings)
   └── Compromise → minimizes all distortions (reference maps)

2. What geographic extent?
   ├── World → cylindrical or pseudocylindrical
   ├── Hemisphere → azimuthal
   └── Continent or smaller
       ├── Round extent → azimuthal
       ├── E-W elongated → conic or cylindrical (normal)
       └── N-S elongated → cylindrical (transverse)
```

### Equal-Area vs Conformal: The Key Decision

**Equal-area is mandatory for**:
- Choropleth maps (area distortion directly misleads about magnitude)
- Density maps, dot density, hex bins
- Any map where the reader compares region sizes
- Cartograms (the distortion IS the data)

**Conformal is preferred for**:
- Navigation and wayfinding
- Weather maps (wind direction/pressure patterns)
- Large-scale (zoomed-in) maps where local shape matters
- Web Mercator tile basemaps (historical/practical reasons)

**Compromise projections for**:
- Reference/general-purpose world maps
- When neither area nor angle is critical
- Natural Earth 1, Robinson, Winkel Tripel

### Modern Projection Recommendations (Beyond Current Skill)

| Use case | Projection | Why |
|----------|-----------|-----|
| World thematic (default) | Equal Earth | Equal-area, modern (2018), pleasing shape, adopted by UN/EU |
| World reference | Natural Earth 1 | Compromise, familiar, no polar pinching |
| USA (50 states) | AlbersUsa | Composite with AK/HI insets, equal-area |
| USA (contiguous 48) | Albers `.rotate([96, 0]).center([0, 38]).parallels([29.5, 45.5])` | Standard USGS parameters |
| Europe | Conic Equal Area `.rotate([-15, 0]).center([0, 52]).parallels([35, 65])` | ETRS89/LAEA standard |
| Single country | Transverse Mercator or national projection | Minimal distortion in narrow extent |
| Globe/3D | Orthographic | Perspective view, clip to hemisphere |
| Polar | Azimuthal Equal Area, centered on pole | Standard for Arctic/Antarctic |
| Small multiples | Same projection for all panels | Comparability > optimality |

### Tissot's Indicatrix as Quality Check

Draw Tissot circles to visually verify distortion. If circles vary wildly in size on a choropleth, the projection is wrong:

```js
const graticule = d3.geoGraticule().step([30, 30]);
// Generate circles at graticule intersections
const tissot = graticule.lines()
  .filter((_, i) => i % 2 === 0)
  .flatMap(line => line.coordinates.filter((_, i) => i % 3 === 0))
  .map(([lon, lat]) => d3.geoCircle().center([lon, lat]).radius(5)());
```

## Dark Mode Cartography

### The Dark-is-More Problem

On light backgrounds, dark colors intuitively mean "more" — this is the **dark-is-more bias**. A 2024 study (Schiewe, KN Journal of Cartography) with 214 participants found:

- The dark-is-more bias **persists even on dark backgrounds** — people still read dark as "more" even when dark colors have low contrast against the background
- The bias is slightly weaker in dark mode, and varies by color scheme
- Expert cartographers are somewhat less susceptible
- Simply inverting a light-mode sequential scheme produces poor results

**Implication**: Don't just invert your color ramps. Design separate schemes for dark mode.

### Design Guidelines for Dark Mode Maps

**Background**: Use dark gray (`#1a1a2e`, `#0d1117`, `#1e1e1e`), not pure black. Pure black creates excessive contrast with any color.

**Sequential schemes for dark mode**:
- Start from a dark color close to the background (low = blends in)
- End at a saturated, light color (high = pops out)
- The "high value" color should have the highest luminance contrast against background
- Multi-hue schemes (e.g., viridis, inferno, plasma) work better than single-hue in dark mode because hue variation provides a second channel beyond lightness

**Borders and boundaries**:
- Use subtle mid-gray (`#333`, `#444`), not white
- Reduce stroke width compared to light mode
- State/country borders at 0.3-0.5px, not 1px

**Labels**:
- Off-white (`#e0e0e0`), not pure white
- Add text shadow or halo: `text-shadow: 0 0 3px rgba(0,0,0,0.8)`
- Reduce label density compared to light mode
- Use `font-weight: 300-400`, not bold

**Water and land**:
- Water slightly lighter than background: `#1a1a2e` bg, `#12203a` water
- Or water slightly more blue: `#0d2137`

**Implementation pattern** — CSS custom properties for theme switching:

```js
const themes = {
  light: {
    bg: "#f5f5f5", water: "#c6dbef", border: "#999",
    label: "#333", halo: "rgba(255,255,255,0.8)",
    sequential: d3.interpolateBlues,
  },
  dark: {
    bg: "#1a1a2e", water: "#0d2137", border: "#444",
    label: "#e0e0e0", halo: "rgba(0,0,0,0.8)",
    sequential: d3.interpolatePlasma, // multi-hue works better on dark
  }
};

// Respond to system preference
const prefersDark = matchMedia("(prefers-color-scheme: dark)").matches;
const theme = themes[prefersDark ? "dark" : "light"];
```

**Canvas-specific dark mode**:
```js
// Canvas doesn't inherit CSS — set explicitly
ctx.fillStyle = theme.bg;
ctx.fillRect(0, 0, width, height);
// Use compositing for glowing effects on dark backgrounds
ctx.globalCompositeOperation = "screen"; // additive blending for points
```

### Tile Basemaps in Dark Mode

MapTiler, Mapbox, and Protomaps all offer dark tile styles. The OSM Dark style (MapTiler, January 2026) is purpose-built rather than color-inverted. When using PMTiles + MapLibre, switch style JSON for dark mode. When using d3-tile with raster tiles, use a dark tile provider URL.

## Modern Projection Innovations

### Observable Plot's Geo Mark

Observable Plot's `geo` mark wraps D3's geo stack with a declarative API. Key features relevant to the skill:

- **Projection-aware marks**: Any mark (dot, text, arrow) can use projection coordinates directly, not just the geo mark
- **Clip to GeoJSON**: `clip` option accepts arbitrary GeoJSON polygons, not just `"sphere"` or `"frame"`
- **Automatic fitSize**: Plot auto-fits the projection to the data extent

This is relevant as a simpler API for quick maps, but the D3 skill should teach the underlying mechanics that Plot abstracts away.

### Globe Mode in MapLibre v5

MapLibre GL JS v5 (2024-2025) added globe rendering — an orthographic-like view at low zoom that transitions to Mercator as you zoom in. This is similar to what Google Maps and Apple Maps do. It's WebGL-rendered, performant, and handles the transition automatically.

For D3 projects that need globe interaction, the choice is now:
- **D3 geoOrthographic + versor**: Full control, self-contained, Canvas/SVG, but you handle everything
- **MapLibre v5 globe**: WebGL, performant, automatic Mercator transition at zoom, but locked into MapLibre ecosystem

### Adaptive Composite Projections

The AlbersUsa pattern (inset AK/HI) can be generalized. D3 doesn't have a built-in API for arbitrary composite projections, but `d3.geoTransform` + manual clip regions can compose any set of projections:

```js
// Conceptual pattern for custom composite
function compositeProjection(regions) {
  // regions: [{projection, clipPolygon, translate, scale}, ...]
  return function(point) {
    for (const r of regions) {
      if (d3.geoContains(r.clipPolygon, point)) {
        const [x, y] = r.projection(point);
        return [x * r.scale + r.translate[0], y * r.scale + r.translate[1]];
      }
    }
    return null;
  };
}
```

### d3-geo-polygon

The [d3-geo-polygon](https://github.com/Fil/d3-geo-polygon) package provides polyhedral projections (Waterman butterfly, Cox conformal) and proper polygon clipping on the sphere. These are niche but produce striking visualizations for data stories.

## Decision Guidance

### Pure D3 vs Tile Library Decision Tree

```
START: Do you need a basemap with streets/terrain/satellite?
  │
  ├── NO → Pure D3
  │   ├── Thematic map (choropleth, cartogram)? → Pure D3, equal-area projection
  │   ├── Globe with drag rotation? → D3 geoOrthographic + versor + Canvas
  │   ├── Small multiples? → Pure D3, shared projection
  │   └── Self-contained HTML? → Pure D3 with inline TopoJSON
  │
  └── YES → Need basemap
      │
      ├── How many data features overlaid?
      │   ├── < 5K → MapLibre + D3 SVG overlay
      │   ├── 5K-100K → MapLibre + D3 Canvas overlay (or deck.gl)
      │   └── 100K+ → MapLibre + deck.gl (WebGL)
      │
      ├── Need non-Mercator projection?
      │   ├── YES → Pure D3 (tiles are mostly Mercator)
      │   └── NO → MapLibre
      │
      ├── Deployment constraints?
      │   ├── Single HTML file, no network → Pure D3 with embedded TopoJSON
      │   ├── Static hosting only → PMTiles on S3/R2 + MapLibre
      │   └── Tile server available → MapLibre with any tile source
      │
      └── Interaction model?
          ├── Slippy map (pan/zoom 0-22) → MapLibre
          ├── Fixed view with hover/click → Pure D3
          └── Brush/link to other charts → Pure D3 (or hybrid)
```

### Performance Boundaries

| Approach | Max interactive features | Zoom levels | Bundle size |
|----------|------------------------|-------------|-------------|
| D3 SVG | ~5,000 paths | 1-3 | ~50KB (d3-geo) |
| D3 Canvas | ~100,000 points | 1-5 | ~50KB |
| D3 Canvas + quadtree | ~500,000 points | 1-5 | ~55KB |
| MapLibre GL JS | ~500,000 (WebGL) | 0-22 | ~300KB |
| MapLibre + deck.gl | 1M-10M | 0-22 | ~600KB |
| d3-tile + raster | unlimited (pre-rendered) | 0-19 | ~55KB |

## Code Patterns

### Pattern 1: PMTiles + MapLibre + D3 Overlay

The full stack for data visualization over a basemap, no tile server needed.

```html
<script type="module">
import maplibregl from "https://cdn.jsdelivr.net/npm/maplibre-gl@4/+esm";
import { Protocol } from "https://cdn.jsdelivr.net/npm/pmtiles@3/+esm";
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

// Register PMTiles protocol
const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      basemap: {
        type: "vector",
        url: "pmtiles://https://your-bucket.s3.amazonaws.com/basemap.pmtiles",
      }
    },
    layers: [/* style layers */]
  },
  center: [-98, 39], zoom: 4
});

// D3 overlay
const container = map.getCanvasContainer();
const svg = d3.select(container).append("svg")
  .attr("width", "100%").attr("height", "100%")
  .style("position", "absolute").style("top", 0).style("left", 0);

function projectPoint(lon, lat) {
  const p = map.project([lon, lat]);
  this.stream.point(p.x, p.y);
}
const path = d3.geoPath().projection(d3.geoTransform({ point: projectPoint }));

map.on("load", async () => {
  const data = await d3.json("data.geojson");
  const features = svg.selectAll("path")
    .data(data.features)
    .join("path")
      .attr("d", path)
      .attr("fill", d => color(d.properties.value))
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.5);

  function update() { features.attr("d", path); }
  map.on("move", update);
});
</script>
```

### Pattern 2: Dark Mode Choropleth (Pure D3)

```js
const darkTheme = {
  bg: "#1a1a2e",
  water: "#0d2137",
  land: "#2a2a3e",
  border: "rgba(255,255,255,0.15)",
  label: "#ccc",
  halo: "rgba(0,0,0,0.7)",
  // Sequential: light = more on dark background
  scale: d3.scaleSequential(d3.interpolatePlasma),
};

const lightTheme = {
  bg: "#fafafa",
  water: "#c6dbef",
  land: "#eee",
  border: "rgba(0,0,0,0.2)",
  label: "#333",
  halo: "rgba(255,255,255,0.7)",
  scale: d3.scaleSequential(d3.interpolateBlues),
};

function render(theme) {
  const { bg, water, land, border, label, halo, scale } = theme;

  // Canvas background
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, width, height);

  // Water (sphere)
  ctx.beginPath(); path({ type: "Sphere" });
  ctx.fillStyle = water; ctx.fill();

  // Choropleth fills — batch by color
  scale.domain(d3.extent(features, d => d.properties.value));
  const byColor = d3.group(features, f => scale(f.properties.value) ?? land);
  for (const [c, group] of byColor) {
    ctx.beginPath();
    for (const f of group) path(f);
    ctx.fillStyle = c; ctx.fill();
  }

  // Borders
  ctx.beginPath(); path(borders);
  ctx.strokeStyle = border; ctx.lineWidth = 0.5; ctx.stroke();
}

// Auto-detect and respond to theme changes
const mq = matchMedia("(prefers-color-scheme: dark)");
render(mq.matches ? darkTheme : lightTheme);
mq.addEventListener("change", e => render(e.matches ? darkTheme : lightTheme));
```

### Pattern 3: Projection Selection Helper

```js
// Systematic projection selection based on Snyder's framework
function selectProjection(extent, property = "equal-area") {
  const [[w, s], [e, n]] = extent; // [[minLon, minLat], [maxLon, maxLat]]
  const dLon = e - w, dLat = n - s;
  const centerLon = (w + e) / 2, centerLat = (n + s) / 2;
  const isWorld = dLon > 300;
  const isHemisphere = dLon > 150;

  if (isWorld) {
    // World maps
    if (property === "equal-area") return d3.geoEqualEarth();
    if (property === "compromise") return d3.geoNaturalEarth1();
    return d3.geoEqualEarth(); // default
  }

  if (isHemisphere) {
    return d3.geoAzimuthalEqualArea()
      .rotate([-centerLon, -centerLat]);
  }

  // Continent or smaller
  const aspectRatio = dLon / dLat;

  if (aspectRatio < 0.7) {
    // N-S elongated → transverse cylindrical
    return d3.geoTransverseMercator()
      .rotate([-centerLon, 0]);
  }

  if (Math.abs(centerLat) > 60) {
    // Polar → azimuthal
    return d3.geoAzimuthalEqualArea()
      .rotate([-centerLon, -centerLat]);
  }

  // Default: conic equal-area (good for mid-latitude E-W extent)
  return d3.geoConicEqualArea()
    .rotate([-centerLon, 0])
    .center([0, centerLat])
    .parallels([s + dLat / 6, n - dLat / 6]);
}
```

## Sources

- [PMTiles (GitHub)](https://github.com/protomaps/PMTiles)
- [PMTiles Cloud-Optimized Geo Formats Guide](https://guide.cloudnativegeo.org/pmtiles/intro.html)
- [PMTiles on More Platforms (2024)](https://protomaps.com/blog/pmtiles-more-platforms/)
- [Protomaps Basemaps](https://github.com/protomaps/basemaps)
- [MapLibre GL JS](https://maplibre.org/projects/gl-js/)
- [MapLibre + D3 Integration (Observable)](https://observablehq.com/@philipmathieu/maplibre-d3)
- [D3 Vector Tiles (Observable)](https://observablehq.com/@d3/vector-tiles)
- [Projection Wizard](https://projectionwizard.org/)
- [Projection Wizard Paper (Savric et al.)](https://berniejenny.info/pdf/2016_Savric_etal_ProjectionWizard.pdf)
- [Observable Plot Geo Mark](https://observablehq.com/plot/marks/geo)
- [Observable Plot Projections](https://observablehq.com/plot/features/projections)
- [Dark-is-More Bias in Dark Mode (Schiewe, 2024)](https://link.springer.com/article/10.1007/s42489-024-00171-z)
- [Perceiving Dark Mode Colour Schemes in Choropleth Maps](https://www.researchgate.net/publication/383718943_Perceiving_Dark_Mode_Colour_Schemes_in_Choropleth_Maps)
- [OpenStreetMap Dark Style (MapTiler, 2026)](https://www.maptiler.com/news/2026/01/openstreetmap-dark-the-community-favorite-now-optimized-for-the-night/)
- [Esri Light and Dark Color Schemes](https://www.esri.com/arcgis-blog/products/arcgis-online/mapping/light-and-dark-color-schemes)
- [D3 Projection Comparison (Observable)](https://observablehq.com/@d3/projection-comparison)
- [Simon Willison: PMTiles + MapLibre](https://til.simonwillison.net/gis/pmtiles)
- [deck.gl + MapLibre](https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre)
- [d3-geo-polygon (Fil)](https://github.com/Fil/d3-geo-polygon)
