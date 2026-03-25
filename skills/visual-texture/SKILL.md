---
name: visual-texture
description: "Visual texture for D3.js data visualization: SVG pattern fills (hatching, cross-hatch, dots, stipple, diamonds, triangles, zigzag), perceptual distinctiveness ranking, SVG filter textures (feTurbulence, halftone), stroke dash patterns, Canvas pattern equivalents and atlases, pattern+color compositing, markers, color+pattern dual encoding for accessibility. Use this skill when the user needs texture, pattern fills, hatching, stippling, accessible redundant encoding beyond color, print-friendly charts, black-and-white visualizations, textured areas (bars, maps, regions), accessible choropleth maps, custom dash patterns, decorated strokes, procedural textures, or any fill/stroke styling beyond solid color. Also covers dynamic pattern generation, pattern legends, animated patterns, and pattern performance."
---

# Patterned Fills and Stroke Styles

Pattern fills add a second visual channel beyond color — essential for accessibility (colorblind-safe redundant encoding), print reproduction, and visual richness.

Related: `color` (color palettes, bivariate legends), `canvas` (batched drawing, DPR), `cartography` (choropleth with pattern fills).

**Always use `patternUnits="userSpaceOnUse"`** — pattern density stays constant regardless of shape size. `objectBoundingBox` stretches to fit each shape, so a large rectangle has sparse hatching while a small one has dense hatching.

## Pattern Library

All patterns: append `<pattern>` to defs, draw marks inside, return id. Canonical form — diagonal hatch:

```js
function patternHatch(defs, { id = "hatch", size = 8, strokeWidth = 1.5, stroke = "#333", angle = 45 } = {}) {
  defs.append("pattern")
    .attr("id", id).attr("width", size).attr("height", size)
    .attr("patternUnits", "userSpaceOnUse")
    .attr("patternTransform", `rotate(${angle})`)
    .append("line")
      .attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", size)
      .attr("stroke", stroke).attr("stroke-width", strokeWidth);
  return id;
}
```

### Geometric Variants — tile contents differ

| Pattern | Tile contents | Density | Best for |
|---------|---------------|:---:|----------|
| **Diagonal hatch** | Line + `rotate(45)` | Medium | Default categorical |
| **Cross-hatch** | Two perpendicular lines + `rotate(45)` | High | Emphasis |
| **Horizontal/Vertical** | Single line at `y=size/2` or `x=size/2` | Low | Neutral |
| **Dot grid** | Circle at `(size/2, size/2)` | Low–med | Scatter-like fill |
| **Checkerboard** | Two rects at `(0,0)` and `(half,half)` | High | Strong contrast |
| **Stipple** | `n` circles at seeded-random positions | Variable | Organic |
| **Diamond** | Rotated square path | Medium | Alt categorical |
| **Triangle** | Equilateral tessellation, height = `size * √3/2` | Medium | Alt categorical |

### Perceptual Distinctiveness Ranking

From most to least distinct:

1. **Solid fill vs any pattern** — always clearly different
2. **Diagonal hatch (/) vs dots (·)** — orientation vs shape
3. **Diagonal (/) vs backslash (\\)** — mirror orientation
4. **Hatch vs cross-hatch** — density difference
5. **Horizontal vs vertical** — subtle, especially at small sizes

For maximum accessibility, choose patterns that differ in **type** (lines vs dots vs shapes), not just **angle**. A palette of (diagonal hatch, dots, cross-hatch, horizontal, diamonds, stipple) gives 6 clearly distinct patterns.

## Combining Patterns with Color

Dual encoding: layer colored background behind pattern marks. Screen: color reinforces. Print: pattern alone carries information.

### Mark color vs background lightness

| Background L (Lab) | Mark color | Rationale |
|---|---|---|
| L > 70 | `rgba(0,0,0,0.2)` | Subtle dark marks |
| 55 < L ≤ 70 | `rgba(0,0,0,0.3)` | Stronger dark |
| 40 < L ≤ 55 | `rgba(255,255,255,0.35)` | White marks |
| L ≤ 40 | `rgba(255,255,255,0.45)` | Stronger white |

### Accessible choropleth

Combine sequential color with varying pattern density:

```js
const bins = [
  { color: "#eff3ff", pattern: "dots",  spacing: 10 },  // lightest, sparse
  { color: "#bdd7e7", pattern: "hatch", spacing: 8 },
  { color: "#6baed6", pattern: "hatch", spacing: 5 },
  { color: "#3182bd", pattern: "cross", spacing: 5 },
  { color: "#08519c", pattern: "cross", spacing: 3 },   // darkest, dense
];
```

Each bin differs in both color and pattern. Colorblind readers use pattern alone; sighted readers get color reinforcement.

## SVG Filter-Based Textures

Procedural textures without tile repetition artifacts. Heavier than `<pattern>` but organic-looking.

```html
<filter id="noise-texture" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" seed="42" result="noise"/>
  <feColorMatrix type="saturate" values="0" in="noise" result="gray"/>
  <feComponentTransfer in="gray" result="pattern">
    <feFuncA type="linear" slope="0.15" intercept="0"/>
  </feComponentTransfer>
  <feComposite in="SourceGraphic" in2="pattern" operator="atop"/>
</filter>
```

**Halftone** — `feTurbulence` + `feComponentTransfer` with `type="discrete" tableValues="0 1"` to threshold into dots.

| Criterion | `<pattern>` | `<filter>` |
|---|---|---|
| Performance | Fast (tile reuse) | Slow (per-element raster) |
| Tile seams | Sometimes | Never |
| Organic texture | No | Yes |

Use `<pattern>` for geometric fills. Use `<filter>` for organic textures on a few large areas, not hundreds of elements. `numOctaves` > 4 is visually indistinguishable but costs more.

## Canvas Pattern Atlas

Pre-render all patterns into `CanvasPattern` objects at initialization — avoid creating them per frame:

```js
function buildPatternAtlas(dpr = 1) {
  const patterns = {};
  const configs = [
    { name: "hatch45",  fn: (t) => drawHatchTile(t, 45) },
    { name: "dots",     fn: (t) => drawDotTile(t) },
    { name: "cross",    fn: (t) => drawCrossHatchTile(t) },
    // ...
  ];
  for (const { name, fn } of configs) {
    const tile = document.createElement("canvas");
    tile.width = 8 * dpr; tile.height = 8 * dpr;
    const tctx = tile.getContext("2d");
    tctx.scale(dpr, dpr);
    fn(tctx);
    patterns[name] = ctx.createPattern(tile, "repeat");
  }
  return patterns;
}
```

`CanvasPattern` objects are GPU-resident in most browsers. Creating = expensive; using = cheap. **Batch by pattern** — changing `fillStyle` to a different pattern flushes the draw buffer.

### Canvas color + pattern compositing

```js
ctx.fillStyle = colorScale(category);
ctx.fill(region);
ctx.globalCompositeOperation = "multiply";
ctx.fillStyle = atlas["hatch45"];
ctx.fill(region);
ctx.globalCompositeOperation = "source-over";
```

Multiply blend darkens where pattern marks fall — combined fill without pre-rendering combined tiles.

## Print Considerations

- `stroke-width` ≥ 1px — thinner lines may disappear in print
- Avoid `rgba` transparency — printers handle inconsistently. Use opaque marks.
- Tile size 6–10px works across screen and print
- Test with browser print preview at 100% and 50% — some patterns moiré at certain print scales
- `@media print` CSS to increase pattern contrast or switch to pattern-only mode

## Common Pitfalls

1. **`objectBoundingBox` patterns stretch** — every shape gets different-density hatching. Use `userSpaceOnUse`.

2. **Pattern ID collisions** — two charts on same page with `id="hatch"` silently conflict. Namespace: `id="chart1-hatch"` or `crypto.randomUUID()`.

3. **Pattern fills ignore `fill-opacity`** — `fill-opacity: 0.5` makes entire tile (including background) semi-transparent. Set opacity on marks *within* the `<pattern>` instead.

4. **Canvas pattern DPR mismatch** — tile canvas must be sized for `devicePixelRatio` or patterns look blurry on retina. Always: `tile.width = size * dpr; tctx.scale(dpr, dpr)`.

5. **`stroke-dasharray` CSS vs attribute** — CSS uses commas (`6, 3`), SVG attribute uses spaces (`6 3`).

6. **Markers don't inherit stroke color** — `<marker>` has its own paint context. Use `fill="context-stroke"` (SVG2) or per-color markers.

7. **Animated `stroke-dashoffset` via D3 transitions** is NOT GPU-accelerated — triggers repaint per frame. Prefer CSS `@keyframes` for smooth marching ants.

8. **Too many unique patterns** — more than 5-6 distinct patterns become hard to differentiate.

9. **`getTotalLength()` on hidden elements** returns 0 with `display: none`. Use `visibility: hidden` or `opacity: 0`.

10. **Pattern rotation seams** — angles other than 0/45/90 can create visible seams at tile boundaries. At 45°, tiles repeat seamlessly. At arbitrary angles, increase tile size or use overlapping marks.

11. **SVG filter on `<pattern>` elements** — expensive and inconsistent across browsers. Apply filters to the shape, not inside the pattern.

12. **Pattern URL with `<base>` tag** — `url(#id)` resolves against base URL, not page. Fix: `url(${window.location.pathname}#id)`.

## References

- [SVG Patterns spec](https://www.w3.org/TR/SVG2/pservers.html#Patterns)
- [textures.js](https://riccardoscalco.it/textures/) — Riccardo Scalco's D3 pattern fill plugin
- [Hero Patterns](https://www.heropatterns.com/) — Steve Schoger's SVG pattern gallery
- [Accessible Visualization Design](https://www.perceptualedge.com/articles/visual_business_intelligence/best_practices_in_color_design.pdf) — Stephen Few
