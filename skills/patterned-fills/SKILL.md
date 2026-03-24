---
name: patterned-fills
description: "SVG pattern fills and stroke styles for D3.js data visualization: hatching (diagonal, cross-hatch, horizontal, vertical), dot grids, stippling, diamonds, triangles, texture fills, SVG filter-based textures (feTurbulence, feDisplacementMap), dashed and dotted strokes, stroke-dasharray patterns, marker-based line decorations, Canvas pattern equivalents, Canvas pattern atlases, and combining patterns with color. Use this skill when the user needs pattern fills for accessibility (redundant encoding beyond color), print-friendly charts, black-and-white visualizations, textured areas (bars, maps, regions), accessible choropleth maps, custom dash patterns, decorated strokes, procedural textures, or any fill/stroke styling beyond solid color. Also covers dynamic pattern generation, pattern legends, and pattern performance."
---

# Patterned Fills and Stroke Styles

Pattern fills add a second visual channel beyond color — essential for accessibility (colorblind-safe redundant encoding), print reproduction, and visual richness. Patterns make the difference between a chart that requires color vision and one that doesn't.

Related skills: `color-and-compositing` (color palettes, blending, bivariate legends), `canvas-rendering` (batched Canvas drawing, DPR), `canvas-accessibility` (redundant encoding for screen readers), `geographic-maps` (choropleth with pattern fills).

```
data values → d3.scaleOrdinal → pattern ID → fill: url(#pattern-id)
                               → stroke dash → stroke-dasharray: "6 3"
                               → combined    → color + pattern + dash
```

## SVG Pattern Fills

A `<pattern>` defines a rectangular tile that repeats. Defined once in `<defs>`, referenced via `fill="url(#id)"`.

```js
defs.append("pattern")
  .attr("id", "dots")
  .attr("width", 8).attr("height", 8)
  .attr("patternUnits", "userSpaceOnUse")
  .append("circle")
    .attr("cx", 4).attr("cy", 4).attr("r", 1.5).attr("fill", "#333");

rect.attr("fill", "url(#dots)");
```

**Always use `userSpaceOnUse`** — pattern density stays constant regardless of shape size. `objectBoundingBox` stretches/compresses to fit each shape, so a large rectangle has sparse hatching while a small one has dense hatching. This is almost never what you want.

Use `patternTransform` to rotate or scale the tile without changing the element it fills:

```js
pattern.attr("patternTransform", "rotate(45)");      // diagonal
pattern.attr("patternTransform", "rotate(45) scale(1.5)"); // combined
```

## Pattern Library

All patterns follow the same structure: append a `<pattern>` to defs, draw marks inside, return the id. Here's the canonical form — a diagonal hatch:

```js
function patternHatch(defs, { id = "hatch", size = 8, strokeWidth = 1.5, stroke = "#333", angle = 45 } = {}) {
  defs.append("pattern")
    .attr("id", id)
    .attr("width", size).attr("height", size)
    .attr("patternUnits", "userSpaceOnUse")
    .attr("patternTransform", `rotate(${angle})`)
    .append("line")
      .attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", size)
      .attr("stroke", stroke).attr("stroke-width", strokeWidth);
  return id;
}
```

### Geometric Variants

Each variant changes only what's inside the tile:

| Pattern | Tile contents | Visual density | Best for |
|---------|---------------|:---:|----------|
| **Diagonal hatch** | Single line + `rotate(45)` | Medium | Default categorical |
| **Backslash hatch** | Single line + `rotate(-45)` | Medium | Second category |
| **Cross-hatch** | Two perpendicular lines + `rotate(45)` | High | Emphasis |
| **Horizontal lines** | One horizontal line at `y = size/2` | Low | Calm/neutral |
| **Vertical lines** | One vertical line at `x = size/2` | Low | Alternative neutral |
| **Dot grid** | Circle at `(size/2, size/2)` | Low–medium | Scatter-like fill |
| **Checkerboard** | Two rects at `(0,0)` and `(half,half)` | High | Strong contrast |
| **Stipple** | `n` circles at seeded-random positions | Variable | Organic/statistical |
| **Wavy lines** | Quadratic Bézier curve | Medium | Water/flow |

### Additional Variants

**Diamond grid** — rotate a square grid 45° with small squares:

```js
function patternDiamonds(defs, { id = "diamonds", size = 12, strokeWidth = 1, stroke = "#333" } = {}) {
  const p = defs.append("pattern")
    .attr("id", id).attr("width", size).attr("height", size)
    .attr("patternUnits", "userSpaceOnUse");
  const half = size / 2;
  p.append("path")
    .attr("d", `M${half},0 L${size},${half} L${half},${size} L0,${half} Z`)
    .attr("fill", "none").attr("stroke", stroke).attr("stroke-width", strokeWidth);
  return id;
}
```

**Triangle grid** — equilateral triangles tessellation:

```js
function patternTriangles(defs, { id = "triangles", size = 12, strokeWidth = 1, stroke = "#333" } = {}) {
  const p = defs.append("pattern")
    .attr("id", id).attr("width", size).attr("height", size * Math.sqrt(3) / 2)
    .attr("patternUnits", "userSpaceOnUse");
  const h = size * Math.sqrt(3) / 2;
  p.append("path")
    .attr("d", `M0,${h} L${size / 2},0 L${size},${h} Z M${size / 2},0 L${size},${h} L${size * 1.5},0`)
    .attr("fill", "none").attr("stroke", stroke).attr("stroke-width", strokeWidth);
  return id;
}
```

**Zigzag** — continuous zigzag line:

```js
function patternZigzag(defs, { id = "zigzag", size = 12, strokeWidth = 1.5, stroke = "#333" } = {}) {
  const p = defs.append("pattern")
    .attr("id", id).attr("width", size).attr("height", size)
    .attr("patternUnits", "userSpaceOnUse");
  const q = size / 4;
  p.append("path")
    .attr("d", `M0,${q*3} L${q},${q} L${q*2},${q*3} L${q*3},${q} L${size},${q*3}`)
    .attr("fill", "none").attr("stroke", stroke).attr("stroke-width", strokeWidth);
  return id;
}
```

### Perceptual Distinctiveness

Not all patterns are equally distinguishable. From most to least distinct:

1. **Solid fill vs any pattern** — always clearly different
2. **Diagonal hatch (/) vs dots (·)** — orientation vs shape
3. **Diagonal (/) vs backslash (\\)** — mirror orientation
4. **Hatch vs cross-hatch** — density difference
5. **Horizontal vs vertical** — subtle, especially at small sizes

For maximum accessibility, choose patterns that differ in **type** (lines vs dots vs shapes), not just **angle**. A palette of (diagonal hatch, dots, cross-hatch, horizontal lines, diamonds, stipple) gives 6 clearly distinct patterns.

## Categorical Pattern Scale

Map categories to distinct patterns, analogous to `d3.scaleOrdinal` for color:

```js
// Create one pattern per category
const patternTypes = [
  { fn: "hatch", angle: 45 },
  { fn: "dots" },
  { fn: "crosshatch" },
  { fn: "hatch", angle: -45 },
  { fn: "horizontal" },
  { fn: "diamonds" },
];

categories.forEach((cat, i) => {
  const type = patternTypes[i % patternTypes.length];
  createPattern(defs, { id: `pat-${i}`, type: type.fn, angle: type.angle ?? 0 });
});

const patternFill = d3.scaleOrdinal(categories, categories.map((_, i) => `url(#pat-${i})`));
bars.attr("fill", d => patternFill(d.category));
```

## Combining Patterns with Color

The power of patterns: dual encoding makes charts readable in both color and grayscale. For screen: layer a colored background behind the pattern. For print: the pattern alone carries the information.

```js
// Inside each pattern tile, add a colored background rect before the hatch marks:
const p = defs.append("pattern").attr("id", `pat-${i}`)
  .attr("width", size).attr("height", size).attr("patternUnits", "userSpaceOnUse")
  .attr("patternTransform", `rotate(${angle})`);
p.append("rect").attr("width", size).attr("height", size).attr("fill", colorScale(cat));

// Adapt mark color to background lightness
const isDark = d3.lab(colorScale(cat)).l < 55;
const markColor = isDark ? "rgba(255,255,255,0.45)" : "rgba(0,0,0,0.2)";
p.append("line").attr("y2", size).attr("stroke", markColor).attr("stroke-width", 1.5);
```

### Mark color selection

The pattern marks must be visible against the background color. This table gives the right mark opacity:

| Background lightness (Lab L) | Mark color | Rationale |
|---|---|---|
| L > 70 (light) | `rgba(0,0,0,0.2)` | Subtle dark marks |
| 55 < L ≤ 70 (medium) | `rgba(0,0,0,0.3)` | Slightly stronger |
| 40 < L ≤ 55 (dark-medium) | `rgba(255,255,255,0.35)` | White marks |
| L ≤ 40 (dark) | `rgba(255,255,255,0.45)` | Stronger white marks |

### Accessible choropleth with patterns

For maps where colorblind users must distinguish regions, combine sequential color with varying pattern density:

```js
// 5 choropleth bins — color + pattern
const bins = [
  { color: "#eff3ff", pattern: "dots",    spacing: 10 },  // lightest, sparse dots
  { color: "#bdd7e7", pattern: "hatch",   spacing: 8 },   // light, wide hatch
  { color: "#6baed6", pattern: "hatch",   spacing: 5 },   // medium, medium hatch
  { color: "#3182bd", pattern: "cross",   spacing: 5 },   // dark, cross-hatch
  { color: "#08519c", pattern: "cross",   spacing: 3 },   // darkest, dense cross-hatch
];
```

Each bin differs in both color (lightness) and pattern (type and density). A colorblind reader can distinguish bins by pattern alone; a sighted reader gets color reinforcement.

## Stroke Dash Patterns

### `stroke-dasharray`

Alternating dash and gap lengths. The pattern repeats.

```js
"6 3"              // dashed
"2 3"              // dotted
"12 4 4 4"         // dash-dot
"12 4 2 4 2 4"     // dash-dot-dot
"0.1 6"            // round dots (with stroke-linecap: round)
```

### Categorical Dash Scale

```js
const dashScale = d3.scaleOrdinal(categories, [
  null, "6 3", "2 3", "12 4 4 4", "8 3 2 3 2 3", "1 4"
]);
lines.attr("stroke-dasharray", d => dashScale(d.category));
```

### Dash + Color + Width — Triple Encoding for Lines

For maximum accessibility, encode category in three channels:

```js
const dashScale  = d3.scaleOrdinal(categories, [null, "6 3", "2 4", "12 4 4 4"]);
const colorScale = d3.scaleOrdinal(categories, tolBright);
const widthScale = d3.scaleOrdinal(categories, [2, 2, 1.5, 1.5]);

lines.attr("stroke", d => colorScale(d.category))
     .attr("stroke-dasharray", d => dashScale(d.category))
     .attr("stroke-width", d => widthScale(d.category));
```

### Dash Animation

```js
// Draw-on effect
const totalLength = path.node().getTotalLength();
path.attr("stroke-dasharray", totalLength).attr("stroke-dashoffset", totalLength)
  .transition().duration(1500).attr("stroke-dashoffset", 0);

// Marching ants (prefer CSS animation for GPU acceleration)
// @keyframes march { to { stroke-dashoffset: -16; } }
// .marching { stroke-dasharray: 4 4; animation: march 0.4s linear infinite; }
```

### Linecap and Linejoin

| `stroke-linecap` | Effect |
|---|---|
| `butt` (default) | Square-cut ends |
| `round` | Rounded — turns "0.1" dashes into circles |
| `square` | Extended square ends |

| `stroke-linejoin` | Effect |
|---|---|
| `miter` (default) | Sharp corners |
| `round` | Rounded corners |
| `bevel` | Flattened corners |

## SVG Filter-Based Textures

SVG filters generate procedural textures without tile repetition artifacts. Heavier than `<pattern>` but organic-looking.

### feTurbulence — noise texture

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

Apply to shapes: `selection.attr("filter", "url(#noise-texture)")`. The `seed` parameter makes it deterministic.

### Paper/grain texture

```html
<filter id="paper">
  <feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="5" seed="7"/>
  <feColorMatrix type="saturate" values="0"/>
  <feComponentTransfer>
    <feFuncA type="linear" slope="0.08"/>
  </feComponentTransfer>
  <feComposite in="SourceGraphic" in2="BackgroundImage" operator="atop"/>
</filter>
```

### Halftone effect

Simulate print halftone dots with feTurbulence + feConvolveMatrix:

```html
<filter id="halftone">
  <feTurbulence type="turbulence" baseFrequency="0.15" numOctaves="1" seed="1" result="dots"/>
  <feColorMatrix in="dots" type="saturate" values="0" result="bw"/>
  <feComponentTransfer in="bw">
    <feFuncA type="discrete" tableValues="0 1"/>
  </feComponentTransfer>
  <feComposite in="SourceGraphic" operator="in"/>
</filter>
```

### When to use filters vs patterns

| Criterion | `<pattern>` | `<filter>` |
|---|---|---|
| Performance | Fast (tile reuse) | Slow (per-element raster) |
| Tile seams visible | Sometimes | Never |
| Organic texture | No | Yes |
| Print quality | Excellent | Good |
| Complex elements | Works | Can cause clipping |

Use `<pattern>` for geometric fills (hatch, dots). Use `<filter>` for organic textures (paper, noise, grain) applied to a few large areas, not hundreds of elements.

## Canvas Equivalents

### Canvas Pattern Fills

Same tile concept — draw to an offscreen canvas, then `ctx.createPattern(tile, "repeat")`:

```js
function createCanvasHatch(size, strokeWidth, color, angle, dpr = 1) {
  const tile = document.createElement("canvas");
  tile.width = size * dpr; tile.height = size * dpr;
  const tctx = tile.getContext("2d");
  tctx.scale(dpr, dpr);
  // Rotate the drawing context for diagonal
  tctx.translate(size / 2, size / 2);
  tctx.rotate(angle * Math.PI / 180);
  tctx.translate(-size / 2, -size / 2);
  tctx.strokeStyle = color;
  tctx.lineWidth = strokeWidth;
  tctx.beginPath();
  // Draw three lines to cover tile under rotation
  for (let offset = -size; offset <= size * 2; offset += size) {
    tctx.moveTo(offset, -size);
    tctx.lineTo(offset, size * 2);
  }
  tctx.stroke();
  return tile;
}

const hatchTile = createCanvasHatch(8, 1.5, "#333", 45);
ctx.fillStyle = ctx.createPattern(hatchTile, "repeat");
ctx.fill(path);
```

For color + pattern: fill the tile background first, then draw pattern marks on top.

### Canvas Pattern Atlas

For charts with many pattern types, pre-render all patterns into a single set of `CanvasPattern` objects at initialization:

```js
function buildPatternAtlas(dpr = 1) {
  const patterns = {};
  const configs = [
    { name: "hatch45",  fn: (t) => drawHatchTile(t, 45) },
    { name: "hatch-45", fn: (t) => drawHatchTile(t, -45) },
    { name: "dots",     fn: (t) => drawDotTile(t) },
    { name: "cross",    fn: (t) => drawCrossHatchTile(t) },
    { name: "horiz",    fn: (t) => drawHorizontalTile(t) },
    { name: "vert",     fn: (t) => drawVerticalTile(t) },
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

const atlas = buildPatternAtlas(devicePixelRatio);
// Usage: ctx.fillStyle = atlas["hatch45"]; ctx.fill();
```

Pre-building avoids creating pattern objects during render. `CanvasPattern` objects can be reused across frames.

### Canvas Dashes

```js
ctx.setLineDash([6, 3]);     // same numbers as SVG
ctx.lineDashOffset = offset; // for animation
ctx.setLineDash([]);         // reset to solid
```

### Canvas Pattern + Color Compositing

Layer a solid color fill with a pattern fill for dual encoding:

```js
// First pass: solid color fill
ctx.fillStyle = colorScale(category);
ctx.fill(region);

// Second pass: pattern overlay with multiply blend
ctx.globalCompositeOperation = "multiply";
ctx.fillStyle = atlas["hatch45"];
ctx.fill(region);
ctx.globalCompositeOperation = "source-over";
```

The multiply blend darkens the color where pattern marks fall, creating a combined color+pattern fill without needing to pre-render combined tiles.

## SVG Markers (Arrows and Decorations)

```js
defs.append("marker")
  .attr("id", "arrow")
  .attr("viewBox", "0 0 10 10")
  .attr("refX", 10).attr("refY", 5)
  .attr("markerWidth", 8).attr("markerHeight", 8)
  .attr("orient", "auto-start-reverse")
  .append("path").attr("d", "M0,0 L10,5 L0,10 Z").attr("fill", "#333");

line.attr("marker-end", "url(#arrow)");
```

- `orient="auto-start-reverse"` flips `marker-start` 180° automatically — one definition for bidirectional arrows
- `markerUnits="userSpaceOnUse"` makes size independent of stroke width
- `marker-mid` places markers at every vertex of a polyline
- Markers don't inherit stroke color by default — use `fill="context-stroke"` (SVG2) or create per-color markers

### Marker library

| Marker | Path data | Use |
|---|---|---|
| Filled arrow | `M0,0 L10,5 L0,10 Z` | Flow direction |
| Open arrow | `M0,0 L10,5 L0,10` (no Z, fill none) | Softer direction |
| Circle dot | `circle cx=5 cy=5 r=3` | Data points on paths |
| Diamond | `M5,0 L10,5 L5,10 L0,5 Z` | Alternative to arrow |
| Bar/tick | `M0,0 L0,10` (stroke only) | Scale ticks on curves |

## Pattern Legends

### Swatch legend (fill patterns)

Rect with pattern fill + text label, arranged vertically or horizontally:

```js
const legendG = svg.append("g").attr("transform", `translate(${width + 16}, 0)`);
categories.forEach((cat, i) => {
  const g = legendG.append("g").attr("transform", `translate(0, ${i * 22})`);
  g.append("rect").attr("width", 16).attr("height", 16)
    .attr("fill", `url(#pat-${i})`).attr("stroke", "#999").attr("stroke-width", 0.5)
    .attr("rx", 2);
  g.append("text").attr("x", 22).attr("y", 12).attr("font-size", "11px").text(cat);
});
```

### Dash legend (line patterns)

Short line with dash pattern + text label:

```js
dashPatterns.forEach((dp, i) => {
  const g = legendG.append("g").attr("transform", `translate(0, ${i * 22})`);
  g.append("line").attr("x1", 0).attr("y1", 8).attr("x2", 30).attr("y2", 8)
    .attr("stroke", colorScale(dp.category))
    .attr("stroke-width", 2)
    .attr("stroke-dasharray", dp.dash);
  g.append("text").attr("x", 36).attr("y", 12).attr("font-size", "11px").text(dp.category);
});
```

### Combined legend (color + pattern)

When using dual encoding, the legend swatch should show both color and pattern:

```js
g.append("rect").attr("width", 16).attr("height", 16)
  .attr("fill", `url(#cp-${i})`);  // combined color+pattern pattern ID
```

## Dynamic Patterns

### Density-Varying Patterns

Vary pattern tile spacing to encode a quantitative value — denser hatching = higher value:

```js
const spacing = 12 - (value / maxValue) * 9; // 12 (sparse) → 3 (dense)
```

Create a unique pattern per element. Note: many unique `<pattern>` definitions have a rendering cost — keep to 5-6 visually distinguishable levels.

### Animated Patterns

Animating pattern properties creates subtle motion effects:

```js
// Flowing pattern — shift pattern position over time
function animatePattern(patternEl) {
  const size = +patternEl.getAttribute("width");
  let offset = 0;
  function tick() {
    offset = (offset + 0.3) % size;
    patternEl.setAttribute("patternTransform", `translate(${offset}, 0) rotate(45)`);
    requestAnimationFrame(tick);
  }
  tick();
}
```

For Canvas, animate `ctx.translate()` before `ctx.fill()` with the pattern, or recreate pattern tiles with shifted marks.

### Patterns Under Zoom

SVG patterns in `userSpaceOnUse` move with zoom but don't scale — usually desirable (constant visual density). To scale with zoom, update `patternTransform` with `scale(1/transform.k)`:

```js
zoom.on("zoom", ({ transform }) => {
  // Keep pattern density constant relative to screen
  defs.selectAll("pattern")
    .attr("patternTransform", `rotate(45) scale(${1 / transform.k})`);
});
```

## Performance

### SVG Pattern Performance

| Element count | Impact |
|---|---|
| <100 with patterns | No concern |
| 100–500 | Ensure patterns are defined once in `<defs>`, not duplicated per element |
| 500+ | Consider Canvas — SVG pattern rendering scales with element count × pattern complexity |

Each unique `<pattern>` element is a small render tree. Having 500 unique patterns (e.g., one per feature with unique density) is expensive. Instead, quantize to 5–6 levels and share pattern definitions.

### Canvas Pattern Performance

`CanvasPattern` objects are GPU-resident in most browsers. Creating them is expensive; using them is cheap:

- **Create once** at initialization, not per frame
- **Batch by pattern** — changing `fillStyle` to a different `CanvasPattern` flushes the draw buffer, same as changing color
- **DPR matters** — pattern tiles must be rendered at `devicePixelRatio` or they look blurry on retina
- `createPattern()` from an `<img>` element must wait for `onload`

### Filter Performance

SVG filters with feTurbulence are expensive — they rasterize each filtered element:

- Apply to `<g>` groups, not individual elements
- Use `filterUnits="userSpaceOnUse"` with explicit dimensions to avoid oversized filter regions
- `numOctaves` > 4 is visually indistinguishable but costs more
- Cache filtered results with `will-change: filter` CSS

## Print Considerations

- `stroke-width` ≥ 1px — thinner lines may disappear in print
- Avoid `rgba` transparency — printers handle it inconsistently. Use opaque marks.
- Tile size 6–10px works across screen and print
- Ensure patterns are visible in grayscale even with color backgrounds
- Use `@media print` CSS to increase pattern contrast or switch to pattern-only mode
- Test with browser print preview at 100% and 50% zoom — some patterns moiré at certain print scales

```css
@media print {
  .bar { stroke: #333 !important; stroke-width: 0.5px; }
  /* Force pattern-only fills for print */
  .bar[data-pattern] { fill: var(--print-pattern) !important; }
}
```

## Common Pitfalls

1. **`objectBoundingBox` patterns stretch** — every shape gets different-density hatching. Use `userSpaceOnUse`.

2. **Pattern ID collisions** — two charts on the same page with `id="hatch"` silently conflict. Namespace IDs: `id="chart1-hatch"`. For multiple instances of the same component, generate unique IDs with `crypto.randomUUID()` or a counter.

3. **Pattern fills ignore `fill-opacity`** — `fill-opacity: 0.5` on the shape makes the entire tile (including background) semi-transparent. Set opacity on marks within the `<pattern>` instead.

4. **Canvas pattern DPR mismatch** — tile canvas must be sized for `devicePixelRatio` or patterns look blurry on retina. Always: `tile.width = size * dpr; tctx.scale(dpr, dpr)`.

5. **`stroke-dasharray` CSS vs attribute** — CSS uses commas (`6, 3`), SVG attribute uses spaces (`6 3`). D3 `.attr()` sets the attribute.

6. **Markers don't inherit stroke color** — `<marker>` has its own paint context. Use `fill="context-stroke"` (SVG2) or per-color marker definitions.

7. **Animated `stroke-dashoffset` via D3 transitions** is not GPU-accelerated — triggers repaint per frame. Prefer CSS `@keyframes` for smooth marching ants.

8. **Too many unique patterns** — more than 5-6 distinct patterns become hard to differentiate. Group into fewer categories.

9. **`getTotalLength()` on hidden elements** returns 0 with `display: none`. Use `visibility: hidden` or `opacity: 0` to measure before showing.

10. **Pattern rotation seams** — rotating a pattern tile by angles other than 0/45/90 can create visible seams at tile boundaries. At 45°, the tile repeats seamlessly because the diagonal equals the tile size. At arbitrary angles, increase the tile size or use overlapping marks.

11. **SVG filter on `<pattern>` elements** — filters inside `<pattern>` are expensive and may not render consistently across browsers. Apply filters to the shape using the pattern, not inside the pattern definition.

12. **Pattern URL with base tag** — if the page has `<base href="...">`, pattern references `url(#id)` resolve against the base URL, not the page. Fix: use `url(${window.location.pathname}#id)` or avoid `<base>`.

## References

- [SVG Patterns spec](https://www.w3.org/TR/SVG2/pservers.html#Patterns) — W3C reference
- [SVG Filter Effects spec](https://www.w3.org/TR/SVG2/filters.html) — feTurbulence, feColorMatrix
- [textures.js](https://riccardoscalco.it/textures/) — Riccardo Scalco's D3 pattern fill plugin
- [Hero Patterns](https://www.heropatterns.com/) — Steve Schoger's SVG pattern gallery
- [Canvas createPattern](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/createPattern) — MDN
- [stroke-dasharray](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/stroke-dasharray) — MDN
- [Accessible Visualization Design](https://www.perceptualedge.com/articles/visual_business_intelligence/best_practices_in_color_design.pdf) — Stephen Few
