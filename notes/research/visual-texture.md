# Visual Texture Research

Research date: 2026-03-25

## Current Coverage

The `visual-texture` skill covers:

- **SVG pattern fills**: hatching, cross-hatch, dots, stipple, diamonds, triangles, zigzag
- **Perceptual ordering**: Bertin's texture-as-ordered-variable, density as the ranked dimension, spacing variation for sequential data, pattern-type variation for categorical
- **SVG filter textures**: feTurbulence procedural noise, halftone via feComponentTransfer
- **Canvas pattern equivalents**: pattern atlas approach, OffscreenCanvas tile generation
- **Pattern + color dual encoding**: redundant encoding for colorblind accessibility and print
- **Stroke dash patterns**: custom dash arrays as categorical encoding
- **Pattern legends**: matching legend swatches to fill patterns

Key design rules already captured: `patternUnits="userSpaceOnUse"` always, minimum mark size ~20px for pattern legibility, 5-6 pattern limit, photosensitivity warnings for high-contrast regular patterns.

## CSS Paint API / Houdini Worklets

### What it is

The CSS Paint API (part of Houdini) lets you register a paint worklet -- a lightweight JS class with a `paint(ctx, size, properties)` method that draws to a canvas-like context. The result is usable anywhere CSS accepts `<image>`: `background-image`, `border-image`, `mask-image`. Patterns are generated programmatically at render time, not from static tiles.

### Why it matters for visualization

- **Parameterized patterns via CSS custom properties.** A single worklet can produce hatching at any angle, spacing, and color, driven by `--hatch-angle`, `--hatch-spacing` etc. Data-driven pattern parameters become CSS property updates -- no SVG defs management.
- **Off-main-thread rendering.** Worklets run in an isolated execution environment, avoiding jank when generating many patterns simultaneously.
- **Resolution-independent.** The worklet receives the element's actual pixel dimensions, so patterns render crisply at any DPR without the `patternUnits` pitfalls of SVG.

### Browser support (as of early 2026)

| Browser | Status |
|---------|--------|
| Chrome 65+ | Full support |
| Edge (Chromium) | Full support |
| Safari | Partial support |
| Firefox | Not supported, under consideration |

A [polyfill from Google Chrome Labs](https://github.com/GoogleChromeLabs/css-paint-polyfill) covers Firefox and Safari with acceptable performance for static patterns. Not viable for animation-heavy use.

### Practical assessment

**Not yet recommended as a primary technique** for cross-browser visualization work. The Firefox gap is significant. However, for Chromium-targeted dashboards or progressive enhancement (CSS paint with SVG `<pattern>` fallback), it's a viable approach.

The worklet registration pattern:

```js
// pattern-hatch.worklet.js
class HatchPainter {
  static get inputProperties() {
    return ['--hatch-spacing', '--hatch-angle', '--hatch-color', '--hatch-width'];
  }
  paint(ctx, size, props) {
    const spacing = parseInt(props.get('--hatch-spacing')) || 8;
    const angle = parseInt(props.get('--hatch-angle')) || 45;
    const color = props.get('--hatch-color').toString().trim() || '#333';
    const width = parseFloat(props.get('--hatch-width')) || 1.5;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.save();
    ctx.rotate(angle * Math.PI / 180);
    const diag = Math.hypot(size.width, size.height) * 2;
    for (let i = -diag; i < diag; i += spacing) {
      ctx.beginPath();
      ctx.moveTo(i, -diag);
      ctx.lineTo(i, diag);
      ctx.stroke();
    }
    ctx.restore();
  }
}
registerPaint('hatch', HatchPainter);
```

Sources:
- [CSS Painting API | Can I use](https://caniuse.com/css-paint-api)
- [Houdini APIs - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Houdini_APIs)
- [CSS Paint API polyfill](https://github.com/GoogleChromeLabs/css-paint-polyfill)
- [CSS Houdini Paint API generative patterns](https://codepen.io/georgedoescode/pen/eYvjOMN)

## Texture Perception Research

### Julesz texton theory

Bela Julesz (1981, 1983) established that texture discrimination is preattentive -- it happens instantly, without focused attention. He identified three classes of **textons** (fundamental texture elements):

1. **Elongated blobs** -- line segments with specific orientation, width, and length
2. **Color** -- hue/lightness differences
3. **Terminators** -- endpoints of line segments, crossings

Key finding: **only first-order statistics (density) of textons drive preattentive discrimination.** The spatial arrangement of textons is not detected preattentively -- only whether one region has more/fewer/different textons than another. This directly validates using pattern density as an ordered visual variable.

### Ware's framework (Information Visualization, 4th ed.)

Colin Ware synthesizes texton theory into a three-stage model of visual processing relevant to visualization design:

1. **Stage 1 (parallel, preattentive)**: Orientation, size, color, motion, and texture density are extracted simultaneously across the visual field. Texture differences that vary along these dimensions "pop out."
2. **Stage 2 (pattern aggregation)**: Texture and color are used to group regions -- contiguous areas of similar texture are perceived as a single object.
3. **Stage 3 (sequential, attentive)**: Visual working memory processes individual objects for recognition.

**Design implications from Ware:**

- **Orientation is the strongest texture discriminator.** Horizontal vs. 45-degree hatching is detected preattentively; 40-degree vs. 50-degree is not. Use at least 30-degree separation between orientations.
- **Density (spacing) is ordered; orientation and shape are categorical.** This matches Bertin. Don't mix pattern types for sequential data.
- **Texture interacts with color.** A texture overlaid on color reduces the effective number of distinguishable colors. Budget for this: if using 6 colors + 6 patterns, test that the combinations remain discriminable, not just the individual channels.
- **5-6 discriminable textures is the practical ceiling** before viewers must consult the legend for every mark.

### Bertin's retinal variables (Semiology of Graphics, 1967)

Bertin ranked texture (grain) as an ordered variable alongside size and value (lightness). His taxonomy:

| Variable | Selective? | Ordered? | Quantitative? |
|----------|-----------|----------|---------------|
| Size | Yes | Yes | Yes |
| Value (lightness) | Yes | Yes | No |
| Texture (grain) | Yes | Yes | No |
| Color (hue) | Yes | No | No |
| Orientation | Yes | No | No |
| Shape | Sometimes | No | No |

Texture is selective (you can isolate "all hatched regions") and ordered (denser = more) but not quantitative (you can't read a ratio from pattern density).

Sources:
- [Julesz 1981 - Texton theory, Nature](https://www.nature.com/articles/290091a0)
- [Julesz 1983 - Textons in preattentive vision, Bell System Technical Journal](https://onlinelibrary.wiley.com/doi/abs/10.1002/j.1538-7305.1983.tb03502.x)
- [Colin Ware - Information Visualization, 4th ed.](https://shop.elsevier.com/books/information-visualization/ware/978-0-12-812875-6)
- [Healey - Perception in Visualization](https://www.csc2.ncsu.edu/faculty/healey/PP/)

## SVG 2 Hatch Element

### What it is

SVG 2 introduced a native `<hatch>` element as a new paint server alongside `<pattern>`, `<linearGradient>`, and `<radialGradient>`. Unlike `<pattern>` (which tiles a rectangular region), `<hatch>` draws continuous parallel lines that extend across the filled shape, supporting the kind of hatching needed for cartography and technical illustration.

```xml
<hatch id="myHatch" hatchUnits="userSpaceOnUse"
       pitch="8" rotate="45">
  <hatchpath stroke="#333" stroke-width="1.5"/>
</hatch>
<rect fill="url(#myHatch)" width="200" height="100"/>
```

Key attributes: `pitch` (line spacing), `rotate` (angle), `hatchUnits`, `hatchContentUnits`. Child `<hatchpath>` elements define the stroke appearance.

### Advantages over `<pattern>`

- No tile-seam artifacts at certain angles/sizes
- Continuous lines across shape boundaries (important for cartographic hatching)
- Simpler API for the common case of parallel-line fills
- No need for `patternTransform` rotation hacks

### Implementation status (early 2026)

**No browser implements `<hatch>`.** The spec is stable in the W3C SVG 2 CR, but:

- Chrome: No implementation, no public intent-to-implement
- Firefox: [Bug 1239147](https://bugzilla.mozilla.org/show_bug.cgi?id=1239147) filed 2016, no progress
- Safari: No implementation

**Practical verdict: Do not use.** Continue using `<pattern>` with `patternTransform="rotate(...)"` for hatching. The `<pattern>` approach works in all browsers and the visual result is identical for visualization purposes. If `<hatch>` ships in the future, it would simplify the code but not change the visual output.

Sources:
- [W3C SVG 2 Paint Servers spec (hatch section)](https://www.w3.org/TR/2016/CR-SVG2-20160915/pservers.html)
- [SVG 2 new features wiki](https://github.com/w3c/svgwg/wiki/SVG-2-new-features)
- [Firefox bug 1239147 - Add support for hatches](https://bugzilla.mozilla.org/show_bug.cgi?id=1239147)
- [SVG 2 draft - Paint Servers](https://svgwg.org/svg2-draft/pservers.html)

## Weighted Voronoi Stippling

### The technique

Adrian Secord's 2002 paper introduced weighted Voronoi stippling: an iterative algorithm that places dots such that their density approximates a grayscale tone field. The algorithm:

1. Seed points randomly (or via rejection sampling from the density field)
2. Compute Voronoi diagram of the points
3. Move each point to the **weighted centroid** of its Voronoi cell, where weights come from the underlying density/data field
4. Repeat until convergence (Lloyd's relaxation with density weighting)

Darker/denser regions accumulate more points; lighter regions have fewer. The result looks like a hand-drawn stipple illustration.

### As a data encoding

Stippling encodes a continuous scalar field through dot density -- the same principle as dot-density maps in cartography, but with algorithmically optimized placement that avoids clumping and gaps. Compared to regular grids or random placement:

- **More perceptually uniform**: weighted Voronoi produces blue-noise distributions where dots are roughly equidistant, avoiding the Moire patterns of grids and the clumpy appearance of random placement
- **More organic/aesthetic**: the result resembles hand-drawn illustration, useful for editorial and narrative visualization
- **Inherently accessible**: works in grayscale and for colorblind viewers since density is the only channel

### D3 implementation

Mike Bostock's [Observable notebook](https://observablehq.com/@mbostock/voronoi-stippling) demonstrates the technique using `d3.Delaunay`:

```js
const delaunay = d3.Delaunay.from(points);
const voronoi = delaunay.voronoi([0, 0, width, height]);

for (let k = 0; k < iterations; k++) {
  for (let i = 0; i < n; i++) {
    const cell = voronoi.cellPolygon(i);
    if (cell === null) continue;
    const [cx, cy] = weightedCentroid(cell, densityField);
    points[i * 2] = cx;
    points[i * 2 + 1] = cy;
  }
  delaunay = d3.Delaunay.from(points);
  voronoi = delaunay.voronoi([0, 0, width, height]);
}
```

The [d3-weighted-voronoi](https://github.com/Kcnarf/d3-weighted-voronoi) plugin extends this with per-site weights affecting cell sizes.

### Applications in data visualization

- **Dot-density choropleth**: Instead of coloring map regions, fill them with stipple dots where density encodes the data value. Accessible by default.
- **Scalar field visualization**: Show continuous data (temperature, population density) as stipple density rather than color ramps.
- **Artistic/editorial visualization**: The hand-drawn quality suits narrative contexts where a clean, illustrative style is preferred.
- **Hybrid encoding**: Combine stipple density with dot color for bivariate maps.

### Performance considerations

Voronoi stippling is computationally expensive -- each iteration recomputes the full Voronoi diagram. For interactive use:
- Pre-compute the stipple layout offline, render the static dots
- Use Canvas, not SVG, for >1000 dots
- 20-50 Lloyd iterations is typically sufficient for visual convergence

Sources:
- [Bostock - Voronoi Stippling (Observable)](https://observablehq.com/@mbostock/voronoi-stippling)
- [Secord 2002 - Weighted Voronoi Stippling (paper)](https://www.cs.ubc.ca/labs/imager/tr/2002/secord2002b/secord.2002b.pdf)
- [Rougier 2017 - ReScience replication](https://github.com/ReScience-Archives/Rougier-2017)
- [d3-weighted-voronoi plugin](https://github.com/Kcnarf/d3-weighted-voronoi)

## Accessible Patterns Beyond Hatching

### The problem

Color-only choropleth maps and bar charts fail ~8% of male viewers (deuteranopia/protanopia). Standard advice is "add texture," but most implementations only use diagonal hatching at varying angles, which exhausts its discriminability at 3-4 categories.

### Pattern vocabulary for accessibility

A robust accessible pattern set uses multiple texton dimensions (per Julesz), not just orientation:

| Pattern | Texton dimension | Notes |
|---------|-----------------|-------|
| Diagonal hatch (/) | Orientation | Most common, ~45 degree |
| Horizontal lines | Orientation | Clearly distinct from diagonal |
| Vertical lines | Orientation | Distinct from horizontal, less so from diagonal at small sizes |
| Dots (regular grid) | Shape (blob vs line) | Very distinct from any line pattern |
| Cross-hatch (+) | Density / crossing | Reads as "denser" than single-direction hatch |
| Stipple (random dots) | Regularity | Distinct from grid dots; reads as "textured" |
| Waves / zigzag | Curvature | Distinct from straight-line patterns |
| Chevrons (>>>) | Shape + orientation | Adds directional reading |

### Design guidance for accessible maps

1. **Pair every color with a unique pattern.** The pattern must be identifiable even in grayscale printout.
2. **Use blue-orange as the base palette** (distinguishable across all CVD types), then add patterns for redundancy.
3. **Test at the minimum region size** your map will render. If small island nations can't resolve the pattern, use a different encoding (labels, hatched borders instead of fills).
4. **Order patterns by density for sequential data.** Sparse dots -> single hatch -> cross-hatch -> dense stipple.
5. **Provide a data table alternative** (see `data-table` skill) as the ultimate fallback.

### Tools

- ColorBrewer 2.0 for colorblind-safe palettes
- Color Oracle or Coblis for CVD simulation
- WCAG contrast checker for pattern-on-background contrast (pattern stroke vs. fill background must meet 3:1 for non-text content)

Sources:
- [Jenny & Kelso - Designing Maps for the Colour-Vision Impaired (PDF)](https://colororacle.org/resources/2007_JennyKelso_DesigningMapsForTheColourVisionImpaired.pdf)
- [ESRI - Designing Maps for Colorblind Readability](https://www.esri.com/arcgis-blog/products/arcgis-pro/mapping/designing-maps-for-colorblind-readability)
- [Carbon Design - Color Palettes and Accessibility](https://medium.com/carbondesign/color-palettes-and-accessibility-features-for-data-visualization-7869f4874fca)
- [Map Library - Color Contrast Strategies for Map Accessibility](https://www.maplibrary.org/9529/7-color-contrast-strategies-for-map-accessibility/)

## Decision Guidance

### When to add texture to the existing skill

| Technique | Add to SKILL.md? | Rationale |
|-----------|-------------------|-----------|
| CSS Paint API worklets | No, not yet | Firefox doesn't support it; polyfill adds complexity. Revisit when Firefox ships support. Mention as a "future" note. |
| SVG 2 `<hatch>` | No | Zero browser implementations. Dead letter for now. |
| Weighted Voronoi stippling | Yes | Mature technique, D3 ecosystem support, directly relevant as a data-encoding pattern method. Add as an advanced recipe. |
| Expanded accessible pattern set | Yes | Current skill covers dual encoding but could add a concrete 6-pattern canonical set with texton-theory justification. |
| Perception research (Ware, Julesz, Bertin) | Partially | The skill already cites Bertin on density ordering. Add Julesz texton theory as the scientific basis for the 5-6 pattern limit and orientation-separation guidance (minimum 30 degrees). |

### What NOT to add

- **WebGL procedural textures** -- overkill for pattern fills; the `webgl-rendering` skill is the right home.
- **Animated texture transitions** -- already partially covered; the `motion` skill handles animation mechanics.
- **Pattern generation libraries** (e.g., textures.js) -- the skill should teach the underlying technique, not wrap a library.

## Code Patterns

### Weighted Voronoi stipple fill for a D3 shape

```js
function stippleFill(ctx, path, densityFn, { n = 2000, iterations = 30 } = {}) {
  // 1. Sample initial points inside the path using rejection sampling
  const bounds = path.bounds();
  const points = new Float64Array(n * 2);
  let i = 0;
  while (i < n) {
    const x = bounds[0][0] + Math.random() * (bounds[1][0] - bounds[0][0]);
    const y = bounds[0][1] + Math.random() * (bounds[1][1] - bounds[0][1]);
    if (ctx.isPointInPath(path, x, y)) {
      // Weight acceptance by density
      if (Math.random() < densityFn(x, y)) {
        points[i * 2] = x;
        points[i * 2 + 1] = y;
        i++;
      }
    }
  }

  // 2. Lloyd relaxation with density weighting
  for (let k = 0; k < iterations; k++) {
    const delaunay = d3.Delaunay.from(points);
    const voronoi = delaunay.voronoi([bounds[0][0], bounds[0][1], bounds[1][0], bounds[1][1]]);
    for (let j = 0; j < n; j++) {
      const cell = voronoi.cellPolygon(j);
      if (!cell) continue;
      // Weighted centroid
      let wx = 0, wy = 0, wt = 0;
      for (const [cx, cy] of cell) {
        const w = densityFn(cx, cy);
        wx += cx * w;
        wy += cy * w;
        wt += w;
      }
      if (wt > 0) {
        points[j * 2] = wx / wt;
        points[j * 2 + 1] = wy / wt;
      }
    }
  }

  // 3. Draw stipple dots
  ctx.fillStyle = "#333";
  for (let j = 0; j < n; j++) {
    ctx.beginPath();
    ctx.arc(points[j * 2], points[j * 2 + 1], 1.2, 0, Math.PI * 2);
    ctx.fill();
  }
}
```

### Canonical 6-pattern accessible set

```js
const accessiblePatterns = [
  { id: "pat-diag",   type: "hatch",  angle: 45,  spacing: 6 },
  { id: "pat-horiz",  type: "hatch",  angle: 0,   spacing: 6 },
  { id: "pat-dots",   type: "dots",   radius: 1.5, spacing: 8 },
  { id: "pat-cross",  type: "cross",  spacing: 6 },
  { id: "pat-wave",   type: "wave",   amplitude: 3, wavelength: 10 },
  { id: "pat-vert",   type: "hatch",  angle: 90,  spacing: 6 },
];

// Each pattern uses a different texton class:
// Orientation (diag vs horiz vs vert), shape (dots), density (cross), curvature (wave)
// Maximizes preattentive discriminability per Julesz texton theory.
```

### Progressive enhancement: CSS Paint API with SVG fallback

```js
// Feature-detect and register worklet if available
if ('paintWorklet' in CSS) {
  CSS.paintWorklet.addModule('hatch-worklet.js');
  // Apply via CSS custom properties
  element.style.background = 'paint(hatch)';
  element.style.setProperty('--hatch-spacing', '8');
  element.style.setProperty('--hatch-angle', '45');
} else {
  // Fallback: apply SVG pattern fill
  element.style.background = 'url(#svg-hatch-pattern)';
}
```
