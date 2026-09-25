# Visual texture

Absorbed from the v2 `visual-texture` skill. Open when building pattern fills for categorical or ordinal encoding, print or CVD-safe charts, or stippled scalar fields.

## Why six patterns, and which six

Texture discrimination is preattentive only when patterns differ in a texton dimension: orientation (≥30° apart), shape (line vs blob), terminators or crossings, or density (Julesz; Ware). Differences in arrangement alone (grid dots vs random dots at equal density) take focused attention.

A set with one texton class each:

| Pattern | Dimension |
|---|---|
| diagonal hatch 45° | orientation |
| horizontal lines | orientation (45° from diagonal) |
| dot grid | shape: blob vs line |
| cross-hatch | crossings; also reads "denser" |
| waves / zigzag | curvature |
| vertical lines | orientation (45° from diagonal) |

A seventh reuses a dimension, and readers start consulting the legend. Horizontal vs vertical alone is weak below ~20px.

Ordinal data: one pattern type, vary spacing. Density reads as ordered; pattern type reads as categorical.

## Pattern function

```js
function patternHatch(defs, { id, size = 8, strokeWidth = 1.5, stroke = "rgba(0,0,0,.25)", angle = 45 }) {
  defs.append("pattern")
      .attr("id", id)
      .attr("width", size).attr("height", size)
      .attr("patternUnits", "userSpaceOnUse")
      .attr("patternTransform", `rotate(${angle})`)
    .append("line")
      .attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", size)
      .attr("stroke", stroke).attr("stroke-width", strokeWidth);
  return `url(#${id})`;
}
```

Dots: one `<circle>` at the tile center. Cross: two perpendicular lines. Stipple: seeded random circles (`d3.randomLcg(seed)`), so tiles match across renders.

## Color plus pattern

Fill the shape with color, then overlay a second shape filled with the pattern. Or put a background `<rect>` inside the pattern itself. Choose mark color by background L\*:

| Background L\* | Pattern marks |
|---|---|
| > 70 | `rgba(0,0,0,0.2)` |
| 55-70 | `rgba(0,0,0,0.3)` |
| 40-55 | `rgba(255,255,255,0.35)` |
| ≤ 40 | `rgba(255,255,255,0.45)` |

Accessible choropleth: both channels increase together.

```js
const bins = [
  { color: "#eff3ff", pattern: "dots",  spacing: 10 },
  { color: "#bdd7e7", pattern: "hatch", spacing: 8 },
  { color: "#6baed6", pattern: "hatch", spacing: 5 },
  { color: "#3182bd", pattern: "cross", spacing: 5 },
  { color: "#08519c", pattern: "cross", spacing: 3 },
];
```

## SVG filters vs patterns

`<pattern>` tiles are cheap and can seam at odd angles. `<filter>` textures (`feTurbulence`, then `feComponentTransfer type="discrete"` for halftone) have no seams but rasterize per element, so use them only on a few large areas. `numOctaves` above ~4 adds cost and no visible detail.

## Canvas

Build every tile once at startup. At DPR:

```js
function makePattern(ctx, size, drawTile, dpr = devicePixelRatio) {
  const tile = document.createElement("canvas");
  tile.width = tile.height = Math.ceil(size * dpr);
  const t = tile.getContext("2d");
  t.scale(dpr, dpr);
  drawTile(t, size);
  const p = ctx.createPattern(tile, "repeat");
  p.setTransform(new DOMMatrix().scale(1 / dpr));
  return p;
}
```

Sort draws by pattern to avoid constant `fillStyle` switches. Tinting without pre-combined tiles: fill with the color, then `multiply` the pattern over it, then reset to `source-over`.

## Print

Strokes ≥1px. Opaque marks rather than rgba. Tiles 6-10px work from screen to 300dpi. Check at 50% scale for moiré. Use `@media print` to raise pattern contrast.

## Weighted Voronoi stippling

Encodes a scalar field as dot density with blue-noise spacing. Seed by rejection sampling against the density, then run 20-50 Lloyd iterations moving each point to its density-weighted Voronoi centroid (`d3.Delaunay.from(points).voronoi(bounds)`). Precompute, then draw to Canvas past ~1000 dots. Reference: Bostock's "Voronoi Stippling" notebook.

## Pitfalls

- `objectBoundingBox` scales the pattern per shape, which readers take for data.
- Duplicate pattern ids across charts collide silently.
- `fill-opacity` on the shape fades the whole pattern paint. Set opacity on the marks inside the pattern.
- Angles other than 0/45/90 seam at tile edges. Use a bigger tile.
- With a `<base>` element, `url(#id)` resolves against the base URL.
- High-contrast stripe fields can be uncomfortable for photosensitive readers, so keep marks subtle.
