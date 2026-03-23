---
name: color-and-compositing
description: "Color science and compositing for D3.js data visualization: perceptual color spaces (Lab, HCL, OKLab), Paul Tol colorblind-safe palettes, D3 color scales and interpolation, globalCompositeOperation on Canvas, SVG mix-blend-mode and feColorMatrix, alpha/opacity strategies for overdraw, colorblind simulation, WCAG contrast checking, and color legends (continuous, categorical, bivariate). Use this skill when the user needs colorblind-safe palettes, custom color schemes as D3 scales, canvas compositing modes for density visualization, blending or alpha tuning for overlapping elements, color legends, or needs to evaluate color choices for accessibility."
---

# Color and Compositing

Color in data visualization is an encoding channel, not decoration. This skill covers **choosing** colors (perceptual spaces, palettes), **blending** them (compositing, alpha), and **communicating** them (legends, accessibility).

Related: `canvas-rendering` (batching by color, density heatmaps), `animated-transitions` (color interpolation), `canvas-accessibility` (ARIA for canvas).

```
data values → d3.scale* → color strings → rendering context
                                               ↓
                                      compositing mode
                                               ↓
                                          final pixels
```

---

## Color Spaces and Interpolation

RGB interpolation produces muddy midpoints. Always use Lab or HCL for color scales.

```js
d3.interpolateRgb("steelblue", "orange")(0.5); // grayish — avoid
d3.interpolateLab("steelblue", "orange")(0.5); // clean blend
d3.interpolateHcl("steelblue", "orange")(0.5); // hue rotation
```

| Space | Uniform lightness | Uniform hue | D3 API | Best for |
|-------|:-:|:-:|--------|----------|
| RGB | No | No | `d3.interpolateRgb` | Never for data |
| Lab | Yes | No | `d3.interpolateLab` | Sequential scales, two-stop gradients |
| HCL | Yes | Yes | `d3.interpolateHcl` | Diverging scales, categorical hue rings |
| OKLab | Yes | Yes | Manual / CSS `oklch()` | Wide-gamut displays, CSS-native work |

**Lab**: perceptually uniform lightness. `d3.lab(l, a, b)` — L is lightness (0–100).

**HCL**: explicit hue angle. `d3.interpolateHclLong` goes the full way around the hue wheel.

**OKLab**: better uniformity than Lab in blues. Not in D3 core. Conversion function:
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

### Multi-stop gradients

```js
const ramp = d3.piecewise(d3.interpolateLab, ["#364B9A", "#6EA6CD", "#EAECCC", "#F67E4B", "#A50026"]);
const scale = d3.scaleSequential(ramp).domain([min, max]);
```

---

## Paul Tol Colorblind-Safe Palettes

D3's Category10 and Set1 are not colorblind-safe. Paul Tol's palettes are guaranteed safe for protanopia, deuteranopia, and tritanopia.

Full hex arrays and D3 scale constructors in [`scripts/tol-palettes.js`](scripts/tol-palettes.js).

### Qualitative — never interpolate, use exact colors

```js
const bright    = ["#4477AA","#EE6677","#228833","#CCBB44","#66CCEE","#AA3377","#BBBBBB"]; // 7, general-purpose
const vibrant   = ["#EE7733","#0077BB","#33BBEE","#EE3377","#CC3311","#009988","#BBBBBB"]; // 7, dark backgrounds
const muted     = ["#CC6677","#332288","#DDCC77","#117733","#88CCEE","#882255","#44AA99","#999933","#AA4499"]; // 9, dense plots
const highContr = ["#004488","#DDAA33","#BB5566"]; // 3, max separation
const light     = ["#77AADD","#EE8866","#EEDD88","#FFAABB","#99DDFF","#44BB99","#BBCC33","#AAAA00","#DDDDDD"]; // 9, pastel fills
```

| Situation | Scheme |
|-----------|--------|
| General line chart, ≤7 categories | **Bright** |
| Dark background | **Vibrant** |
| Dense scatter/parallel coords, 6–9 groups | **Muted** |
| Only 2–3 categories | **High-Contrast** |
| Filled areas with labels on top | **Light** |

### Diverging — support interpolation

**Sunset** (11 stops, blue→red): `["#364B9A","#4A7BB7","#6EA6CD","#98CAE1","#C2E4EF","#EAECCC","#FEDA8B","#FDB366","#F67E4B","#DD3D2D","#A50026"]` bad: `"#FFFFFF"`

**BuRd** (9 stops): `["#2166AC","#4393C3","#92C5DE","#D1E5F0","#F7F7F7","#FDDBC7","#F4A582","#D6604D","#B2182B"]` bad: `"#FFEE99"`

**PRGn** (9 stops): `["#762A83","#9970AB","#C2A5CF","#E7D4E8","#F7F7F7","#D9F0D3","#ACD39E","#5AAE61","#1B7837"]` bad: `"#FFEE99"`

### Sequential

**YlOrBr** (9 stops): `["#FFFFE5","#FFF7BC","#FEE391","#FEC44F","#FB9A29","#EC7014","#CC4C02","#993404","#662506"]` bad: `"#888888"`

**Iridescent** (23 stops): `["#FEFBE9","#FCF7D5","#F5F3C1","#EAF0B5","#DDECBF","#D0E7CA","#C2E3D2","#B5DDD8","#A8D8DC","#9BD2E1","#8DCBE4","#81C4E7","#7BBCE7","#7EB2E4","#88A5DD","#9398D2","#9B8AC4","#9D7DB2","#9A709E","#906388","#805770","#684957","#46353A"]` bad: `"#999999"`

### Using as D3 scales

```js
const color = d3.scaleOrdinal(tolBright);                                     // qualitative
const color = d3.scaleSequential(d3.piecewise(d3.interpolateLab, tolIridescent)).domain([0, max]); // sequential
const color = d3.scaleDiverging(d3.piecewise(d3.interpolateLab, tolSunset)).domain([min, mid, max]); // diverging
```

### Bad data color — every Tol scheme specifies one for null/invalid values

```js
const withBad = (scale, bad) => Object.assign(v => v == null || v === "" ? bad : scale(v), scale);
```

Use Tol for scientific publication, guaranteed colorblind safety, print. Use Tableau10 for general dashboards. Avoid Category10 and Set1.

---

## Designing for Color Vision Deficiency

~8% of males have some form. Simulate with Brettel/Viénot transforms in [`scripts/colorblind-sim.js`](scripts/colorblind-sim.js):

```js
import { simulateDichromacy, applySimulationToImageData } from "./scripts/colorblind-sim.js";
const [r, g, b] = simulateDichromacy(68, 119, 170, "deuteranopia");
// Or apply to entire canvas:
applySimulationToImageData(ctx.getImageData(0, 0, w, h), "deuteranopia");
```

### Redundant encoding — color should never be the sole channel

```js
const shape = d3.scaleOrdinal(categories, [d3.symbolCircle, d3.symbolSquare, d3.symbolTriangle, d3.symbolDiamond]);
const color = d3.scaleOrdinal(tolBright).domain(categories);
svg.selectAll("path").data(data).join("path")
  .attr("d", d => d3.symbol(shape(d.category), 64)())
  .attr("fill", d => color(d.category))
  .attr("transform", d => `translate(${x(d.x)},${y(d.y)})`);
```

Other redundant channels: pattern fills, direct labels, dash arrays, size.

### WCAG contrast checking

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

---

## Canvas Compositing

Source (what you draw next) composites onto destination (what's already there).

| Mode | Effect | Data viz use |
|------|--------|-------------|
| `source-over` | Normal (default) | Everything |
| `lighter` | Additive RGB | Density on black — bright = dense |
| `multiply` | Darken overlap | Overlapping regions, Venn diagrams |
| `screen` | Lighten overlap | Glow on dark backgrounds |
| `difference` | Abs difference | Change detection |
| `destination-out` | Eraser | Masking, cutouts |

### Canonical pattern — additive density with `lighter`

```js
ctx.fillStyle = "#000";
ctx.fillRect(0, 0, width, height);
ctx.globalCompositeOperation = "lighter";
ctx.fillStyle = "rgba(70, 130, 180, 0.08)"; // very low alpha

ctx.beginPath();
for (const d of data) {
  ctx.moveTo(d.x + r, d.y);
  ctx.arc(d.x, d.y, r, 0, Math.PI * 2);
}
ctx.fill();
ctx.globalCompositeOperation = "source-over"; // always reset!
```

Alpha tuning: `0.02–0.05` for 10K+, `0.08–0.15` for 1K–10K.

**Multiply variant** — two regions that darken where they overlap:
```js
ctx.globalCompositeOperation = "multiply";
ctx.fillStyle = "rgba(238, 102, 119, 0.6)"; ctx.fill(pathA);
ctx.fillStyle = "rgba(68, 119, 170, 0.6)"; ctx.fill(pathB);
ctx.globalCompositeOperation = "source-over";
```

**Difference variant** — render state A normally, then state B with `"difference"` to highlight changes.

---

## SVG Blending

```js
svg.selectAll("circle").data(groups).join("circle")
  .attr("fill", d => color(d.id)).attr("fill-opacity", 0.7)
  .style("mix-blend-mode", "multiply");

d3.select("svg").style("isolation", "isolate"); // prevent bleed to page background
```

### feColorMatrix desaturation — dim unfocused elements

```html
<filter id="desat"><feColorMatrix type="saturate" values="0.15"/></filter>
```
```js
selection.filter(d => !focused.has(d.id)).attr("filter", "url(#desat)").attr("opacity", 0.4);
selection.filter(d => focused.has(d.id)).attr("filter", null).attr("opacity", 1);
```

Use SVG blending for <500 elements with declarative control. Use Canvas compositing for 1K+ or pixel-level control.

---

## Alpha and Opacity

### The overdraw formula

```
result = 1 - (1 - a)^n     where a = per-element alpha, n = overlap count
```

| Alpha | 10 overlaps | 25 | 50 | 100 |
|-------|:-:|:-:|:-:|:-:|
| 0.01 | 0.10 | 0.22 | 0.40 | 0.63 |
| 0.02 | 0.18 | 0.40 | 0.64 | 0.87 |
| 0.05 | 0.40 | 0.72 | 0.92 | ~1.0 |
| 0.10 | 0.65 | 0.93 | ~1.0 | ~1.0 |

Solve for alpha: `alpha = 1 - (1 - targetOpacity)^(1/n)`

```js
const alpha = 1 - Math.pow(1 - 0.9, 1 / 50); // 50 overlaps, 90% max → ~0.045
```

See [`scripts/alpha-solver.js`](scripts/alpha-solver.js) for utilities.

### Batch by alpha — avoid per-element `globalAlpha` changes

```js
const buckets = d3.group(data, d => Math.round(opacityScale(d.value) * 10) / 10);
for (const [alpha, items] of buckets) {
  ctx.fillStyle = `rgba(70, 130, 180, ${alpha})`;
  ctx.beginPath();
  for (const d of items) ctx.rect(d.x, d.y, d.w, d.h);
  ctx.fill();
}
```

See `canvas-rendering` for full batching patterns.

---

## Performance

- **Batch by color** — every `fillStyle` change flushes canvas state. See `canvas-rendering` skill.
- **Pre-compute RGBA arrays** for 100K+ elements, compute once when scale changes, not per frame.
- **Compositing mode switching** is expensive — draw all content for one mode before switching. Never toggle per element.
- **Cache color strings** — `d3.rgb().toString()` allocates. Pre-compute: `const colors = data.map(d => colorScale(d.category));`

---

## Color Legends

### Continuous — canvas gradient + SVG axis

```js
const [min, max] = colorScale.domain();
const canvas = container.append("canvas").attr("width", 300).attr("height", 14).style("display", "block");
const ctx = canvas.node().getContext("2d");
for (let i = 0; i < 300; i++) { ctx.fillStyle = colorScale(min + (max - min) * i / 300); ctx.fillRect(i, 0, 1, 14); }
const axisScale = d3.scaleLinear([min, max], [0, 300]);
container.append("svg").attr("width", 301).attr("height", 24).style("display", "block")
  .append("g").attr("transform", "translate(0.5,0)").call(d3.axisBottom(axisScale).ticks(5));
```

### Categorical swatches

```js
const items = container.selectAll(".swatch").data(labels).join("div")
  .attr("class", "swatch").style("display", "inline-flex").style("align-items", "center").style("margin-right", "12px");
items.append("span").style("width", "14px").style("height", "14px")
  .style("background", d => colorScale(d)).style("display", "inline-block").style("margin-right", "4px")
  .style("border-radius", "2px");
items.append("span").text(d => d);
```

### Bivariate — 3×3 curated palette

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
| **Green–Blue** | Good | Strong lightness, good for print |
| **Purple–Gold** | Good | Warm/cool contrast, diverging |
| **Blue–Red** | Moderate | Classic choropleth |

Usage — map two quantile scales to grid indices:
```js
const qx = d3.scaleQuantile(data.map(d => d.varX), [0, 1, 2]);
const qy = d3.scaleQuantile(data.map(d => d.varY), [0, 1, 2]);
const bivariateColor = d => palette[qy(d.varY) * 3 + qx(d.varX)];
```

Legend — draw a 3×3 grid with axis labels:
```js
const g = svg.append("g").attr("transform", "translate(50, 10)");
for (let col = 0; col < 3; col++)
  for (let row = 0; row < 3; row++)
    g.append("rect").attr("x", col * size).attr("y", row * size)
      .attr("width", size - 1).attr("height", size - 1).attr("rx", 2)
      .attr("fill", palette[(2 - row) * 3 + col]);
g.append("text").attr("x", size * 1.5).attr("y", size * 3 + 16).attr("text-anchor", "middle").text("X →");
g.append("text").attr("transform", `translate(-8, ${size * 1.5}) rotate(-90)`).attr("text-anchor", "middle").text("Y →");
```

---

## Common Pitfalls

1. **Category10 is not colorblind-safe.** Several pairs are indistinguishable under deuteranopia. Use Tol Bright or Tableau10.

2. **Interpolating in RGB** produces muddy midpoints. Always use Lab or HCL.

3. **Forgetting to reset `globalCompositeOperation`** after `lighter` or `multiply`. Everything drawn afterward uses the wrong mode. Use `save()/restore()` or explicitly reset to `source-over`.

4. **`mix-blend-mode` without `isolation: isolate`** — blending leaks through to the HTML page background.

5. **Alpha compositing math.** `0.5 + 0.5 ≠ 1.0`. Two 50% opaque layers produce 75%: `1 - (1 - 0.5)² = 0.75`. Use the formula or `alpha-solver.js`.

6. **Too many qualitative colors.** More than 7–8 categories become indistinguishable. Group into "top N + other" or switch encoding.

7. **`globalAlpha` stacks with color alpha.** `globalAlpha = 0.5` + `rgba(r,g,b,0.5)` = effective 0.25. Use one mechanism.

8. **Dark mode palette mismatch.** Palettes for white backgrounds (Tol Bright) look washed out on dark. Use Tol Vibrant or adjust lightness in HCL.

## References

- [Paul Tol's Colour Schemes](https://personal.sron.nl/~pault/)
- [ColorBrewer](https://colorbrewer2.org/) — Cynthia Brewer's cartographic color tool
- [D3 Scale Chromatic](https://d3js.org/d3-scale-chromatic) — built-in color schemes
- [D3 Color](https://d3js.org/d3-color) — RGB, HSL, Lab, HCL
- [Canvas Compositing (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation)
- [How to Pick More Beautiful Colors](https://blog.datawrapper.de/beautifulcolors/) — Lisa Charlotte Muth
- [Viz Palette](https://projects.susielu.com/viz-palette) — Susie Lu & Elijah Meeks
