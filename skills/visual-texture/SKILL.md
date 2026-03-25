---
name: visual-texture
description: "Visual texture for D3.js data visualization: SVG pattern fills (hatching, cross-hatch, dots, stipple, diamonds, triangles, zigzag), perceptual distinctiveness ranking, SVG filter textures (feTurbulence, halftone), stroke dash patterns, Canvas pattern equivalents and atlases, pattern+color compositing, markers, color+pattern dual encoding for accessibility. Use this skill when the user needs texture, pattern fills, hatching, stippling, accessible redundant encoding beyond color, print-friendly charts, black-and-white visualizations, textured areas (bars, maps, regions), accessible choropleth maps, custom dash patterns, decorated strokes, procedural textures, or any fill/stroke styling beyond solid color. Also covers dynamic pattern generation, pattern legends, animated patterns, and pattern performance."
---

# Patterned Fills and Stroke Styles

Texture gives a chart a second voice when color alone can't speak — for the 8% of men who are colorblind, for the printer that flattens everything to grayscale, for the reader who needs to tell "Group A" from "Group B" without relying on hue.

Related: `color` (palettes, bivariate legends), `canvas` (batched drawing, DPR), `cartography` (choropleth with pattern fills).

## When Not to Use Texture

Texture adds visual noise. Every hatched region competes for attention with the data it represents. Use it only when it carries information the viewer can't get otherwise:

- **Don't texture for decoration.** If color already distinguishes categories and the chart won't be printed or used by colorblind readers, patterns add clutter without signal.
- **Don't texture small marks.** Bars narrower than ~20px or areas smaller than ~15x15px can't resolve a pattern — the viewer sees visual static, not "diagonal hatch." Use shape or position instead.
- **Don't use more than 5-6 patterns.** Beyond that, viewers can't reliably match legend to mark. If you need more categories, re-examine whether texture is the right channel.
- **Watch for photosensitivity.** High-contrast regular patterns (especially >5 alternating light-dark stripes) can cause discomfort. Keep pattern marks subtle — `rgba(0,0,0,0.2)` on light backgrounds, not solid black.

## Perceptual Ordering — Which Patterns Read as "More"

Bertin classified texture (grain) as an **ordered** visual variable: denser patterns read as "more" or "heavier." This matters when encoding sequential data.

**Density is the ordered dimension.** Viewers naturally rank patterns by how much ink covers the tile. Sparse dots read as "less"; dense cross-hatch reads as "more." Orientation and shape are categorical — diagonal hatch and horizontal lines feel different, not greater or lesser.

For sequential/ordinal data, vary **spacing** within a single pattern type (e.g., all diagonal hatch, spacing from 12px down to 3px). Mixing pattern types (dots for low, hatch for high) confuses the ordering because the viewer sees a categorical difference, not a ranked one.

For categorical data, vary **pattern type** (lines vs dots vs shapes) to maximize distinctiveness. Angle alone is too subtle — diagonal (/) vs backslash (\\) is barely distinguishable at small sizes.

## Pattern Library

All patterns: append `<pattern>` to defs, draw marks inside, return id. **Always use `patternUnits="userSpaceOnUse"`** — otherwise pattern density varies with shape size, and the viewer reads density as data when it's actually an artifact of geometry.

Canonical form — diagonal hatch:

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

### Geometric Variants

| Pattern | Key difference | Use |
|---------|---------------|----------|
| **Diagonal hatch** | Line + `rotate(45)` | Default categorical; vary spacing for ordinal |
| **Cross-hatch** | Two perpendicular lines | Reads as denser/heavier — use for emphasis or high-value bins |
| **Horizontal/Vertical** | Axis-aligned | Neutral, but horizontal vs vertical is hard to tell at small sizes |
| **Dot grid** | Circle at tile center | Clearly distinct from line-based patterns |
| **Stipple** | Random dot positions (seeded) | Organic feel; density is continuously variable |
| **Diamond / Triangle** | Shape tessellation | Alternative categorical; differ by type from line patterns |

### Distinctiveness Ranking

From most to least distinct:

1. **Solid fill vs any pattern** — always clearly different
2. **Lines vs dots vs shapes** — different pattern type (strongest categorical separator)
3. **Diagonal (/) vs backslash (\\)** — mirror orientation (weaker)
4. **Hatch vs cross-hatch** — density difference (reads as ordinal, not categorical)
5. **Horizontal vs vertical** — subtle, especially below 20px

For a 6-category palette, maximize type variety: (diagonal hatch, dots, cross-hatch, horizontal lines, diamonds, stipple).

## Combining Patterns with Color

Dual encoding: color carries the information on screen; pattern carries it in print and for colorblind readers. Layer a colored background behind semi-transparent pattern marks.

### Mark color vs background lightness

Choose mark opacity based on background L* (Lab) so patterns are visible without overwhelming the color:

| Background L* | Mark color | Why |
|---|---|---|
| > 70 | `rgba(0,0,0,0.2)` | Light background — subtle dark marks avoid visual noise |
| 55–70 | `rgba(0,0,0,0.3)` | Mid-light — needs stronger contrast |
| 40–55 | `rgba(255,255,255,0.35)` | Dark enough that dark marks disappear; switch to white |
| ≤ 40 | `rgba(255,255,255,0.45)` | Deep background — white marks need more opacity |

### Accessible choropleth

Combine sequential color with varying pattern density. Each bin differs in both channels:

```js
const bins = [
  { color: "#eff3ff", pattern: "dots",  spacing: 10 },  // lightest, sparse
  { color: "#bdd7e7", pattern: "hatch", spacing: 8 },
  { color: "#6baed6", pattern: "hatch", spacing: 5 },
  { color: "#3182bd", pattern: "cross", spacing: 5 },
  { color: "#08519c", pattern: "cross", spacing: 3 },   // darkest, dense
];
```

Pattern density increases with color darkness — both channels reinforce the same ordering.

## SVG Filter Textures

Procedural textures via `<filter>` avoid tile seam artifacts but are expensive (per-element rasterization). Use for organic texture on a few large areas, not hundreds of elements.

| | `<pattern>` | `<filter>` |
|---|---|---|
| Performance | Fast (tile reuse) | Slow (per-element raster) |
| Tile seams | Possible at non-45° angles | Never |
| Organic look | No | Yes |

Key parameters: `feTurbulence baseFrequency` controls grain size. `numOctaves` > 4 is visually indistinguishable but costs more. Threshold with `feComponentTransfer type="discrete" tableValues="0 1"` for halftone dots.

## Canvas Patterns

Pre-render all patterns into `CanvasPattern` objects at initialization. `CanvasPattern` is GPU-resident in most browsers — creating is expensive, using is cheap.

```js
const tile = document.createElement("canvas");
tile.width = size * dpr; tile.height = size * dpr;  // DPR-aware or patterns blur on retina
const tctx = tile.getContext("2d");
tctx.scale(dpr, dpr);
drawHatchTile(tctx, size, 45);
const pattern = ctx.createPattern(tile, "repeat");
```

**Batch by pattern** — changing `fillStyle` to a different `CanvasPattern` flushes the GPU draw buffer. Sort draw calls by pattern to minimize flushes.

Color + pattern compositing without pre-rendering combined tiles:

```js
ctx.fillStyle = colorScale(category);
ctx.fill(region);
ctx.globalCompositeOperation = "multiply";
ctx.fillStyle = atlas["hatch45"];
ctx.fill(region);
ctx.globalCompositeOperation = "source-over";
```

## Print Considerations

- `stroke-width` >= 1px — thinner lines disappear in print
- Avoid `rgba` transparency — printers handle it inconsistently. Use opaque marks for print targets.
- Tile size 6-10px works across screen and 300dpi print
- Test at 100% and 50% print scale — some spacings cause moire
- `@media print` CSS to boost pattern contrast or switch to pattern-only mode

## Common Pitfalls

1. **`objectBoundingBox` stretches patterns** — density varies per shape. The viewer reads density as data. Use `userSpaceOnUse`.

2. **Pattern ID collisions** — two charts sharing `id="hatch"` silently conflict. Namespace with chart prefix or `crypto.randomUUID()`.

3. **`fill-opacity` affects the entire tile** — including the pattern's transparent background. Set opacity on marks *within* `<pattern>`, not on the filled shape.

4. **Canvas pattern DPR mismatch** — tile canvas must match `devicePixelRatio` or patterns blur on retina. Always `tile.width = size * dpr; tctx.scale(dpr, dpr)`.

5. **Pattern rotation seams** — angles other than 0/45/90 create visible seams at tile boundaries. Increase tile size or use overlapping marks for arbitrary angles.

6. **Animated `stroke-dashoffset` via D3 transitions** triggers repaint per frame (not GPU-accelerated). Use CSS `@keyframes` for marching ants.

7. **Pattern URL with `<base>` tag** — `url(#id)` resolves against the base URL, not the page. Fix: `url(${window.location.pathname}#id)`.
