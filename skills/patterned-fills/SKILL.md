---
name: patterned-fills
description: "SVG pattern fills and stroke styles for D3.js data visualization: hatching (diagonal, cross-hatch, horizontal, vertical), dot grids, stippling, texture fills, dashed and dotted strokes, stroke-dasharray patterns, marker-based line decorations, and Canvas equivalents. Use this skill when the user needs pattern fills for accessibility (redundant encoding beyond color), print-friendly charts, black-and-white visualizations, textured areas (bars, maps, regions), custom dash patterns, decorated strokes, or any fill/stroke styling beyond solid color. Also covers combining patterns with color, dynamic pattern generation, and pattern legends."
---

# Patterned Fills and Stroke Styles

Pattern fills add a second visual channel beyond color — essential for accessibility (colorblind-safe redundant encoding), print reproduction, and visual richness.

Related skills: `color-and-compositing` (color palettes, blending), `canvas-rendering` (batched Canvas drawing), `canvas-accessibility` (redundant encoding for screen readers).

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

**Always use `userSpaceOnUse`** — pattern density stays constant regardless of shape size. `objectBoundingBox` stretches/compresses to fit each shape.

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

### Variants

Each variant changes only what's inside the tile:

| Pattern | Tile contents |
|---------|---------------|
| **Cross-hatch** | Two perpendicular lines + `rotate(45)` |
| **Horizontal lines** | One horizontal line at `y = size/2` |
| **Vertical lines** | One vertical line at `x = size/2` |
| **Dot grid** | Circle at `(size/2, size/2)` |
| **Checkerboard** | Two rects at `(0,0)` and `(half,half)`, each `half × half` |
| **Stipple** | `n` circles at seeded-random positions (use mulberry32 PRNG for determinism) |
| **Wavy lines** | Quadratic Bézier `M0,mid Q quarter,mid±amp size/2,mid Q 3quarter,mid∓amp size,mid` |

## Categorical Pattern Scale

Map categories to distinct patterns, analogous to `d3.scaleOrdinal` for color:

```js
// Create one pattern per category
const patternTypes = [
  { angle: 45 }, { fn: "dots" }, { fn: "crosshatch" },
  { angle: -45 }, { fn: "horizontal" }, { fn: "vertical" },
];

categories.forEach((cat, i) => {
  const type = patternTypes[i % patternTypes.length];
  patternHatch(defs, { id: `pat-${i}`, angle: type.angle ?? 45 });
});

const patternFill = d3.scaleOrdinal(categories, categories.map((_, i) => `url(#pat-${i})`));
bars.attr("fill", d => patternFill(d.category));
```

## Combining Patterns with Color

For screen: layer a colored background behind the pattern for double encoding. For print: the pattern alone carries the information.

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

## Canvas Equivalents

### Canvas Pattern Fills

Same tile concept — draw to an offscreen canvas, then `ctx.createPattern(tile, "repeat")`:

```js
const tile = document.createElement("canvas");
tile.width = size * dpr; tile.height = size * dpr;
const tctx = tile.getContext("2d");
tctx.scale(dpr, dpr);
// Draw pattern marks on tctx...
ctx.fillStyle = ctx.createPattern(tile, "repeat");
```

For color + pattern: fill the tile background first, then draw pattern marks on top.

### Canvas Dashes

```js
ctx.setLineDash([6, 3]);     // same numbers as SVG
ctx.lineDashOffset = offset; // for animation
ctx.setLineDash([]);         // reset to solid
```

Batch by pattern — `fillStyle` changes with CanvasPattern objects are expensive. See `canvas-rendering` skill.

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

## Pattern Legends

Swatch legend: rect with pattern fill + text label, arranged vertically. Dash legend: short line with dash pattern + text label. Same structure as color swatch legends.

## Dynamic Patterns

### Density-Varying Patterns

Vary pattern tile spacing to encode a quantitative value — denser hatching = higher value:

```js
const spacing = 12 - (value / maxValue) * 9; // 12 (sparse) → 3 (dense)
```

Create a unique pattern per element. Note: many unique `<pattern>` definitions have a rendering cost — keep to 5-6 visually distinguishable levels.

### Patterns Under Zoom

SVG patterns in `userSpaceOnUse` move with zoom but don't scale — usually desirable (constant visual density). To scale with zoom, update `patternTransform` with `scale(1/transform.k)`.

## Print Considerations

- `stroke-width` ≥ 1px — thinner lines may disappear in print
- Avoid `rgba` transparency — printers handle it inconsistently. Use opaque marks.
- Tile size 6–10px works across screen and print
- Ensure patterns are visible in grayscale even with color backgrounds
- Use `@media print` CSS to increase pattern contrast

## Common Pitfalls

1. **`objectBoundingBox` patterns stretch** — every shape gets different-density hatching. Use `userSpaceOnUse`.

2. **Pattern ID collisions** — two charts on the same page with `id="hatch"` silently conflict. Namespace IDs: `id="chart1-hatch"`.

3. **Pattern fills ignore `fill-opacity`** — `fill-opacity: 0.5` on the shape makes the entire tile (including background) semi-transparent. Set opacity on marks within the `<pattern>` instead.

4. **Canvas pattern DPR mismatch** — tile canvas must be sized for `devicePixelRatio` or patterns look blurry on retina.

5. **`stroke-dasharray` CSS vs attribute** — CSS uses commas (`6, 3`), SVG attribute uses spaces (`6 3`). D3 `.attr()` sets the attribute.

6. **Markers don't inherit stroke color** — `<marker>` has its own paint context. Use `fill="context-stroke"` (SVG2) or per-color marker definitions.

7. **Animated `stroke-dashoffset` via D3 transitions** is not GPU-accelerated — triggers repaint per frame. Prefer CSS `@keyframes` for smooth marching ants.

8. **Too many unique patterns** — more than 5-6 distinct patterns become hard to differentiate. Group into fewer categories.

9. **`getTotalLength()` on hidden elements** returns 0 with `display: none`. Use `visibility: hidden` or `opacity: 0` to measure before showing.

## References

- [SVG Patterns spec](https://www.w3.org/TR/SVG2/pservers.html#Patterns) — W3C reference
- [textures.js](https://riccardoscalco.it/textures/) — Riccardo Scalco's D3 pattern fill plugin
- [Hero Patterns](https://www.heropatterns.com/) — Steve Schoger's SVG pattern gallery
- [Canvas createPattern](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/createPattern) — MDN
- [stroke-dasharray](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/stroke-dasharray) — MDN
