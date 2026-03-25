---
name: color-and-compositing
description: "Color science and compositing for D3.js data visualization: perceptual color spaces (Lab, HCL, OKLab), Paul Tol colorblind-safe palettes, D3 color scales and interpolation, globalCompositeOperation on Canvas, SVG mix-blend-mode and feColorMatrix, alpha/opacity strategies for overdraw, colorblind simulation, WCAG contrast checking, color perception pitfalls, scale design principles, dark mode adaptation, wide gamut, and color legends (continuous, categorical, bivariate). Use this skill when the user needs colorblind-safe palettes, custom color schemes as D3 scales, canvas compositing modes for density visualization, blending or alpha tuning for overlapping elements, color legends, sequential/diverging/categorical scale design, dark mode color adaptation, or needs to evaluate color choices for accessibility."
---

# Color and Compositing

Color in data visualization is an encoding channel, not decoration. Covers **choosing** colors (perceptual spaces, palettes, scale design), **blending** them (compositing, alpha), **communicating** them (legends, accessibility), and **adapting** them (dark mode, wide gamut).

Related: `canvas-rendering` (batching by color), `visual-texture` (redundant encoding).

## Color Perception

### Lightness dominates

The visual system processes lightness ~10× faster than chromatic differences. A sequential scale that only varies hue (constant lightness) looks flat — data disappears. **Test**: convert to grayscale. If ordering is still clear, it works.

### Simultaneous contrast

A color looks different depending on surroundings. A medium gray on white looks darker than on black. Affects choropleths — a county's perceived color shifts based on neighbors. Mitigate with borders between regions and lightness-varying (not just chroma-varying) scales.

### Small-area color

Small marks (dots, thin lines) appear less saturated and lighter than large areas. A carefully designed palette loses distinctiveness on scatter plots. Mitigate: boost chroma ~20% in HCL, darken slightly, add dark outlines.

```js
function boostedColor(hex, chromaBoost = 20) {
  const c = d3.hcl(hex);
  c.c = Math.min(130, (c.c || 0) + chromaBoost);
  c.l = Math.max(20, c.l - 5);
  return c.toString();
}
```

### Mach bands

The visual system exaggerates lightness differences at boundaries. Continuous color legends show illusory gradients within uniform bins — an optical illusion, not a rendering bug. Discrete legends avoid this.

## Color Space Selection

RGB interpolation produces muddy midpoints. Always use Lab or HCL.

| Space | Uniform lightness | Uniform hue | Best for |
|-------|:-:|:-:|----------|
| Lab | Yes | No | Sequential scales, two-stop gradients |
| HCL | Yes | Yes | Diverging scales, categorical hue rings |
| OKLab | Yes | Yes | Wide-gamut, CSS-native (`oklch()`) |

### HCL hue interpolation pitfall

HCL through white/black hits undefined hue — midpoint jumps unpredictably. Matters for diverging scales through neutral midpoint. Use Lab for the neutral zone, or use D3's built-in diverging interpolators which handle this.

### OKLab conversion

```js
function srgbToOklab(r, g, b) {
  const l_ = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b;
  const m_ = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b;
  const s_ = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b;
  const l = Math.cbrt(l_), m = Math.cbrt(m_), s = Math.cbrt(s_);
  return [
    0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
    1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
    0.0259040371*l + 0.7827717662*m - 0.8086757660*s
  ];
}
```

## Paul Tol Colorblind-Safe Palettes

D3's Category10 and Set1 are not colorblind-safe. Full hex arrays in [`scripts/tol-palettes.js`](scripts/tol-palettes.js).

### Qualitative — never interpolate, use exact colors

```js
const bright    = ["#4477AA","#EE6677","#228833","#CCBB44","#66CCEE","#AA3377","#BBBBBB"]; // 7, general
const vibrant   = ["#EE7733","#0077BB","#33BBEE","#EE3377","#CC3311","#009988","#BBBBBB"]; // 7, dark bg
const muted     = ["#CC6677","#332288","#DDCC77","#117733","#88CCEE","#882255","#44AA99","#999933","#AA4499"]; // 9, dense
const highContr = ["#004488","#DDAA33","#BB5566"]; // 3, max separation
const light     = ["#77AADD","#EE8866","#EEDD88","#FFAABB","#99DDFF","#44BB99","#BBCC33","#AAAA00","#DDDDDD"]; // 9, pastel
```

| Situation | Scheme |
|-----------|--------|
| General line chart, ≤7 categories | **Bright** |
| Dark background | **Vibrant** |
| Dense scatter/parallel coords, 6–9 groups | **Muted** |
| Only 2–3 categories | **High-Contrast** |
| Filled areas with labels on top | **Light** |

### Diverging — with bad-data color per scheme

**Sunset** (11 stops): `["#364B9A","#4A7BB7","#6EA6CD","#98CAE1","#C2E4EF","#EAECCC","#FEDA8B","#FDB366","#F67E4B","#DD3D2D","#A50026"]` bad: `"#FFFFFF"`

**BuRd** (9 stops): `["#2166AC","#4393C3","#92C5DE","#D1E5F0","#F7F7F7","#FDDBC7","#F4A582","#D6604D","#B2182B"]` bad: `"#FFEE99"`

**PRGn** (9 stops): `["#762A83","#9970AB","#C2A5CF","#E7D4E8","#F7F7F7","#D9F0D3","#ACD39E","#5AAE61","#1B7837"]` bad: `"#FFEE99"`

### Sequential

**YlOrBr** (9 stops): `["#FFFFE5","#FFF7BC","#FEE391","#FEC44F","#FB9A29","#EC7014","#CC4C02","#993404","#662506"]` bad: `"#888888"`

**Iridescent** (23 stops): `["#FEFBE9","#FCF7D5","#F5F3C1","#EAF0B5","#DDECBF","#D0E7CA","#C2E3D2","#B5DDD8","#A8D8DC","#9BD2E1","#8DCBE4","#81C4E7","#7BBCE7","#7EB2E4","#88A5DD","#9398D2","#9B8AC4","#9D7DB2","#9A709E","#906388","#805770","#684957","#46353A"]` bad: `"#999999"`

### Bad data color — every Tol scheme specifies one

```js
const withBad = (scale, bad) => Object.assign(v => v == null || v === "" ? bad : scale(v), scale);
```

## Colorblind Simulation

~8% of males have some form. Simulate with Brettel/Viénot transforms in [`scripts/colorblind-sim.js`](scripts/colorblind-sim.js):

```js
import { simulateDichromacy, applySimulationToImageData } from "./scripts/colorblind-sim.js";
const [r, g, b] = simulateDichromacy(68, 119, 170, "deuteranopia");
applySimulationToImageData(ctx.getImageData(0, 0, w, h), "deuteranopia");
```

| Type | Prevalence | What merges |
|---|---|---|
| Deuteranopia | ~6% males | Red/green/brown indistinguishable |
| Protanopia | ~2% males | Similar, red appears darker |
| Tritanopia | ~0.01% | Blue/green merge, yellow/pink merge |

### WCAG Contrast

```js
function relativeLuminance(hex) {
  const [r, g, b] = [1, 3, 5].map(i => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrastRatio(a, b) {
  const l1 = relativeLuminance(a), l2 = relativeLuminance(b);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}
// WCAG AA: ≥4.5:1 normal text, ≥3:1 large. AAA: ≥7:1.
```

## Overdraw Alpha Formula

```
result = 1 - (1 - a)^n     where a = per-element alpha, n = overlap count
```

| Alpha | 10 overlaps | 25 | 50 | 100 |
|-------|:-:|:-:|:-:|:-:|
| 0.01 | 0.10 | 0.22 | 0.40 | 0.63 |
| 0.02 | 0.18 | 0.40 | 0.64 | 0.87 |
| 0.05 | 0.40 | 0.72 | 0.92 | ~1.0 |
| 0.10 | 0.65 | 0.93 | ~1.0 | ~1.0 |

**Solve for alpha**: `alpha = 1 - Math.pow(1 - targetOpacity, 1 / n)`

```js
const alpha = 1 - Math.pow(1 - 0.9, 1 / 50); // 50 overlaps, 90% max → ~0.045
// Simpler heuristic: alpha = clamp(100 / data.length, 0.01, 0.8)
```

See [`scripts/alpha-solver.js`](scripts/alpha-solver.js).

## Canvas Compositing

| Mode | Effect | Data viz use |
|------|--------|-------------|
| `source-over` | Normal (default) | Everything |
| `lighter` | Additive RGB | Density on black — bright = dense |
| `multiply` | Darken overlap | Overlapping regions, Venn diagrams |
| `screen` | Lighten overlap | Glow on dark backgrounds |
| `difference` | Abs difference | Change detection |
| `destination-out` | Eraser | Masking, cutouts |
| `source-in` | Keep only overlap | Clipping to existing content |

### Additive density with `lighter`

```js
ctx.fillStyle = "#000";
ctx.fillRect(0, 0, width, height);
ctx.globalCompositeOperation = "lighter";
ctx.fillStyle = "rgba(70, 130, 180, 0.08)"; // very low alpha
ctx.beginPath();
for (const d of data) { ctx.moveTo(d.x + r, d.y); ctx.arc(d.x, d.y, r, 0, Math.PI * 2); }
ctx.fill();
ctx.globalCompositeOperation = "source-over"; // always reset!
```

Alpha tuning: `0.02–0.05` for 10K+, `0.08–0.15` for 1K–10K.

### Multi-group density

Use different color channel emphasis per group — overlapping regions blend to white/yellow/cyan/magenta, revealing overlap.

### Masking with `source-in`

Draw mask shape first, switch to `source-in`, then draw — subsequent content clipped to mask.

## Dark Mode HCL Adaptation

```js
function adaptForDarkMode(hex) {
  const c = d3.hcl(hex);
  c.l = 100 - c.l;  // invert lightness around 50
  c.c = Math.min(130, (c.c || 0) * 1.1);  // boost chroma slightly
  return c.toString();
}
```

Works for qualitative palettes. Sequential scales: on dark backgrounds, reverse lightness direction so high values are bright (far from background), not dark (merging with background).

| Light mode | Dark mode |
|---|---|
| Tol Bright | Tol Vibrant (designed for dark) |
| `d3.schemeBlues` | Reverse, or use `d3.schemeYlGnBu` |

## Wide Gamut P3 / oklch

Display P3 covers ~50% more colors than sRGB.

```js
const hasP3 = window.matchMedia("(color-gamut: p3)").matches;
// Canvas: canvas.getContext("2d", { colorSpace: "display-p3" }) — affects entire canvas
```

CSS `oklch()` is the best perceptual space for designing scales. For D3, convert to hex at scale-creation time — D3 doesn't natively interpolate oklch.

## Bivariate Legends

Don't blend two arbitrary scales — use Joshua Stevens' hand-tuned 9-color grids:

```js
const bivariate = {
  pinkBlue:   ["#e8e8e8","#ace4e4","#5ac8c8","#dfb0d6","#a5add3","#5698b9","#be64ac","#8c62aa","#3b4994"],
  greenBlue:  ["#e8e8e8","#b5c0da","#6c83b5","#b8d6be","#90b2b3","#567994","#73ae80","#5a9178","#2a5a5b"],
  purpleGold: ["#e8e8e8","#e4d9ac","#c8b35a","#cbb8d7","#c8ada0","#af8e53","#9972af","#976b82","#804d36"],
  blueRed:    ["#e8e8e8","#e4acac","#c85a5a","#b0d5df","#ad9ea5","#985356","#64acbe","#627f8c","#574249"],
};
```

| Palette | Colorblind safety | Best for |
|---------|:-:|----------|
| **Pink–Blue** | Best | General bivariate |
| **Green–Blue** | Good | Strong lightness, print |
| **Purple–Gold** | Good | Warm/cool contrast |
| **Blue–Red** | Moderate | Classic choropleth |

Index: `palette[qy(d.varY) * 3 + qx(d.varX)]`

## Common Pitfalls

1. **Category10 is not colorblind-safe.** Several pairs merge under deuteranopia. Use Tol Bright or Tableau10.

2. **Interpolating in RGB** produces muddy midpoints. Use Lab or HCL.

3. **Forgetting to reset `globalCompositeOperation`** — everything drawn afterward uses the wrong mode. Use `save()/restore()` or reset to `source-over`.

4. **`mix-blend-mode` without `isolation: isolate`** — blending leaks to page background.

5. **Alpha compositing math.** `0.5 + 0.5 ≠ 1.0`. Two 50% layers = 75%: `1 - (1-0.5)² = 0.75`.

6. **Too many qualitative colors.** >7–8 categories become indistinguishable. Group into "top N + other".

7. **`globalAlpha` stacks with color alpha.** `globalAlpha=0.5` + `rgba(r,g,b,0.5)` = effective 0.25.

8. **Dark mode palette mismatch.** Palettes for white backgrounds look washed out on dark. Use Vibrant or adjust lightness in HCL.

9. **Printing transparency.** `rgba()` alpha renders inconsistently across printers. Use opaque colors + pattern fills.

10. **`d3.color()` in tight loops.** Parsing hex strings allocates objects. Cache outside render loop.

## References

- [Paul Tol's Colour Schemes](https://personal.sron.nl/~pault/)
- [ColorBrewer](https://colorbrewer2.org/)
- [D3 Scale Chromatic](https://d3js.org/d3-scale-chromatic)
- [Canvas Compositing (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation)
- [Joshua Stevens: Bivariate Choropleth](https://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/)
- [OKLab Color Space](https://bottosson.github.io/posts/oklab/) — Björn Ottosson
- [WCAG Contrast (Understanding SC 1.4.3)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
