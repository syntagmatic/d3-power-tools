# Color Systems Research

Research for expanding the `skills/color/SKILL.md` beyond Paul Tol palettes.

## Current Coverage

The skill already covers:

- **Color perception**: lightness dominance, simultaneous contrast, small-area color, Mach bands
- **Color spaces**: Lab, HCL, OKLab (conversion math, not interpolation)
- **Paul Tol palettes**: Bright, Vibrant, Muted, High-Contrast, Light (qualitative); Sunset, BuRd, PRGn (diverging); YlOrBr, Iridescent (sequential); bad-data colors per scheme
- **Colorblind simulation**: Brettel/Vienot transforms, prevalence stats
- **WCAG 2 contrast**: relativeLuminance + contrastRatio functions, AA/AAA thresholds
- **Overdraw alpha**: formula, lookup table, solver
- **Canvas compositing**: lighter, multiply, screen, difference, masking
- **Dark mode**: HCL lightness inversion, scheme swaps
- **Wide gamut**: P3 detection, Canvas colorSpace option, brief oklch mention
- **Bivariate legends**: Joshua Stevens 9-color grids (4 palettes)
- **Pitfalls**: 10 common mistakes

**Gaps**: No ColorBrewer selection guidance, no Crameri maps, no OKLCH interpolation patterns, no APCA, no d3-scale-chromatic inventory, no decision framework across palette systems.

## New Palette Systems

### ColorBrewer (Cynthia Brewer)

The foundation of d3-scale-chromatic. Three scheme types:

| Type | Purpose | D3 count | Key property |
|------|---------|----------|--------------|
| **Sequential** | Ordered data, low-to-high | 18 multi-hue + 6 single-hue | Lightness steps dominate |
| **Diverging** | Two extremes + neutral midpoint | 9 | Dark endpoints, light center |
| **Qualitative** | Categories, no order | 8 | Hue differences only |

ColorBrewer's edge over Tol: more granularity (3-to-12 class variants per scheme), cartography-tested, built into D3. Tol's edge over ColorBrewer: explicitly designed for colorblind safety with tested bad-data colors. Use ColorBrewer when you need many class counts or specific sequential ramps; use Tol when colorblind safety is the primary concern.

ColorBrewer schemes are interpolated via uniform B-splines in d3-scale-chromatic, so continuous versions exist even though the source is discrete.

### Crameri Scientific Colour Maps

Created by Fabio Crameri for scientific visualization. Key properties:
- **Perceptually uniform** (flat dE curve across the range)
- **Colorblind-safe** (all maps)
- **B&W printable** (monotonic lightness)
- **Citable** (DOI: zenodo.org/records/8409685)

Major maps:

| Map | Type | Character | Use case |
|-----|------|-----------|----------|
| **batlow** | Sequential | Dark blue → yellow-green → bright yellow | General-purpose sequential, jet replacement |
| **roma** | Diverging | Blue → white → red | Temperature anomalies, deviations |
| **vik** | Diverging | Blue → white → red (wider gamut) | Topography, ocean-land |
| **berlin** | Diverging | Blue → yellow | Elevation, signed data |
| **hawaii** | Sequential | White → dark teal | Bathymetry, depth |
| **lajolla** | Sequential | White → dark brown | Terrain, warm sequential |
| **bamako** | Sequential | White → dark violet | Alternative sequential |
| **oslo** | Sequential | White → dark blue | Ice, cold data |
| **romaO** | Cyclic | Cyclic version of roma | Phase, angle, direction |

D3 support: Not built into d3-scale-chromatic. Available via:
1. Observable notebook by @xaquingv (importable, hex arrays)
2. Zenodo download (XML, JSON, CSV, various formats)
3. Manual: extract hex stops and use `d3.scaleSequential` with custom interpolator

### Matplotlib-derived (in d3-scale-chromatic)

These are built into D3 but underused relative to ColorBrewer:

| Scheme | Origin | Why it's good |
|--------|--------|---------------|
| **Viridis** | van der Walt, Smith, Firing | Perceptually uniform, colorblind-safe, prints well |
| **Magma** | Same team | Perceptually uniform, darker range |
| **Inferno** | Same team | High contrast, dark-to-bright |
| **Plasma** | Same team | Purple-to-yellow, avoids green |
| **Cividis** | Nuñez, Anderton, Renslow | Optimized for CVD, blue-to-yellow |
| **Turbo** | Anton Mikhailov (Google) | Rainbow-like but perceptually ordered, NOT perceptually uniform |

## Modern Color Spaces

### OKLCH / OKLab

OKLCH (Lightness, Chroma, Hue) is a cylindrical form of OKLab, created by Bjorn Ottosson (2020). Now native in CSS Color Level 4.

**Why it matters for dataviz**:
- Perceptually uniform: equal L steps = equal perceived lightness changes (unlike HSL)
- Predictable chroma: you can set a chroma ceiling and all hues stay within it
- Gamut-aware: can represent Display P3 colors
- CSS-native: `oklch(70% 0.15 240)` works in all modern browsers

**D3 support**: d3-color does NOT natively support oklch (open issue #87 on GitHub). Workarounds:

1. **Culori library** — modern JS color library, supports oklch natively, ESM, used by Tailwind v4
2. **CSS-side interpolation** — use CSS `color-mix()` or `oklch()` directly in styles, bypass D3 interpolation
3. **Manual conversion** — convert oklch stops to hex at scale-creation time

**When to use oklch over HCL**:
- HCL (CIELCHab) has known hue non-uniformity in blue-purple range
- OKLCH fixes this — hue 270 actually looks like it's between 240 and 300
- Use OKLCH for programmatic palette generation; use HCL when staying within D3 built-ins

### Display P3

~50% larger gamut than sRGB. Relevant for saturated categorical colors that need maximum separation.

```js
// Detection
const hasP3 = matchMedia("(color-gamut: p3)").matches;

// Canvas with P3
const ctx = canvas.getContext("2d", { colorSpace: "display-p3" });

// CSS (works in SVG style attributes too)
element.style.fill = "oklch(65% 0.25 150)"; // P3-level chroma
```

P3 is useful for categorical palettes where you need more than 8-9 distinguishable colors — the wider gamut gives you more room in chroma space. Not useful for sequential/diverging scales where lightness dominates.

## Contrast and Accessibility

### APCA (Advanced Perceptual Contrast Algorithm)

APCA is the candidate contrast method for WCAG 3.0, replacing WCAG 2's contrast ratio.

**Key differences from WCAG 2**:

| WCAG 2 | APCA |
|--------|------|
| Single ratio (e.g. 4.5:1) | Lc value from -108 to +106 |
| Symmetric (swap fg/bg = same ratio) | **Asymmetric** (light-on-dark ≠ dark-on-light) |
| No font size/weight consideration | Lookup table: font size × weight → minimum Lc |
| Binary pass/fail | Graduated levels |

**Lc thresholds** (simplified):

| Lc value | Use |
|----------|-----|
| ≥ 90 | Body text (14px/400 weight) |
| ≥ 75 | Body text (18px/400) or large headings |
| ≥ 60 | Large text (24px+), bold text (18px/700) |
| ≥ 45 | Non-text elements, chart marks |
| ≥ 30 | Large non-text, decorative |
| ≥ 15 | Disabled states, invisible boundaries |

**For data visualization**: Lc 45 is the key threshold — chart labels, axis text, annotation callouts. Data marks themselves can go lower if they have redundant encoding (shape, position).

**JavaScript implementation**:

```js
import { APCAcontrast, sRGBtoY } from "apca-w3";

// Arguments: [R, G, B, A] as 0-255 integers
const textY = sRGBtoY([17, 17, 17, 1.0]);
const bgY = sRGBtoY([232, 230, 221, 1.0]);
const Lc = APCAcontrast(textY, bgY);
// Returns signed float: positive = dark-on-light, negative = light-on-dark
// |Lc| ≥ 45 → acceptable for chart annotations
```

**Status**: WCAG 3.0 is still in draft (as of 2026). Use WCAG 2.2 for compliance. Use APCA proactively for better perceptual accuracy — it handles dark mode much better than WCAG 2's symmetric ratio.

## D3 Built-in Schemes

### Complete inventory of d3-scale-chromatic

**Categorical** (all from ColorBrewer unless noted):

| Scheme | Colors | Origin | Notes |
|--------|--------|--------|-------|
| `schemeCategory10` | 10 | D3 original | NOT colorblind-safe, avoid |
| `schemeAccent` | 8 | ColorBrewer | Pastel, low contrast |
| `schemeDark2` | 8 | ColorBrewer | Good for dark text on light bg |
| `schemePaired` | 12 | ColorBrewer | 6 light/dark pairs, good for paired categories |
| `schemePastel1` | 9 | ColorBrewer | Very light, fill only |
| `schemePastel2` | 8 | ColorBrewer | Very light, fill only |
| `schemeSet1` | 9 | ColorBrewer | Saturated, NOT colorblind-safe |
| `schemeSet2` | 8 | ColorBrewer | Moderate saturation |
| `schemeSet3` | 12 | ColorBrewer | 12 colors, moderate separation |
| `schemeTableau10` | 10 | Tableau | Better than Category10, reasonable CVD safety |
| `schemeObservable10` | 10 | Observable | Contemporary, optimized for modern screens |

**Underused categorical picks**:
- `schemeTableau10` — better default than Category10, tested by Tableau research
- `schemeObservable10` — modern, designed for screen rendering
- `schemePaired` — great when categories have natural pairs (before/after, plan/actual)

**Sequential single-hue** (all ColorBrewer): Blues, Greens, Greys, Oranges, Purples, Reds

**Sequential multi-hue** (ColorBrewer): BuGn, BuPu, GnBu, OrRd, PuBu, PuBuGn, PuRd, RdPu, YlGn, YlGnBu, YlOrBr, YlOrRd

**Sequential multi-hue** (other origins):
- `interpolateViridis` — matplotlib, perceptually uniform, CVD-safe
- `interpolateMagma` — matplotlib, darker
- `interpolateInferno` — matplotlib, high contrast
- `interpolatePlasma` — matplotlib, avoids green
- `interpolateCividis` — CVD-optimized, blue-yellow
- `interpolateTurbo` — Google, rainbow-like but ordered (NOT perceptually uniform)
- `interpolateWarm` — Niccoli, red-yellow
- `interpolateCool` — Niccoli, blue-green
- `interpolateCubehelixDefault` — Green's cubehelix

**Diverging** (all ColorBrewer): BrBG, PRGn, PiYG, PuOr, RdBu, RdGy, RdYlBu, RdYlGn, Spectral

**Cyclical**: Rainbow, Sinebow

**Underused sequential picks**:
- `interpolateCividis` — the best choice when CVD safety is paramount and you want a built-in D3 scheme
- `interpolateViridis` — should be the default sequential, not Blues or YlOrRd
- `interpolateMagma` — excellent for dark backgrounds (dark-to-bright trajectory)
- `interpolateWarm` / `interpolateCool` — useful as a pair for small multiples with two facets

## Decision Guidance

### Which palette system?

```
Need colorblind safety above all else?
├── Yes, qualitative → Tol Bright/Muted or Cividis (if ordinal-ish)
├── Yes, sequential → Viridis, Cividis, or Crameri batlow
├── Yes, diverging → Tol Sunset/BuRd or Crameri roma
└── No special CVD requirement
    ├── Sequential data → Viridis (default), ColorBrewer multi-hue for specific hue
    ├── Diverging data → ColorBrewer RdBu/RdYlBu (classic), Tol for CVD
    ├── Categorical ≤10 → Tableau10 (safe default), Tol Bright (best CVD)
    ├── Categorical >10 → Don't. Group into top-N + "other"
    ├── Scientific publication → Crameri (citable, reviewer-proof)
    ├── Bivariate → Stevens grids (Pink-Blue for CVD)
    └── Custom brand colors → Generate in OKLCH space, test with CVD sim
```

### Which color space for interpolation?

| Scenario | Space | Why |
|----------|-------|-----|
| D3 built-in scheme | Whatever D3 uses (Lab B-spline) | Already handled |
| Custom two-stop gradient | `d3.interpolateLab` | Avoids RGB mud |
| Custom diverging through white | `d3.interpolateLab` | HCL has undefined hue at white |
| Programmatic palette generation | OKLCH (via culori) | Best uniformity, gamut-aware |
| CSS-only color manipulation | `oklch()` natively | No JS needed |
| Categorical with max separation | OKLCH hue ring, fixed L and C | Even spacing guaranteed |

### Which contrast algorithm?

| Situation | Algorithm |
|-----------|-----------|
| Legal/compliance requirement | WCAG 2.2 (4.5:1 AA, 3:1 large text) |
| Dark mode text | APCA (WCAG 2 overestimates light-on-dark contrast) |
| Chart annotation sizing | APCA Lc ≥ 45 for labels, ≥ 60 for axis text |
| Proactive quality check | Both — WCAG 2 for compliance, APCA for perception |

## Code Patterns

### Generate OKLCH palette with culori

```js
import { oklch, formatHex } from "culori";

// Qualitative: evenly spaced hues, fixed L and C
function oklchCategorical(n, L = 0.65, C = 0.15) {
  return Array.from({ length: n }, (_, i) =>
    formatHex(oklch({ l: L, c: C, h: (i * 360) / n + 30 }))
  );
}

// Sequential: ramp L and C at fixed hue
function oklchSequential(n, hue = 250, lRange = [0.95, 0.30], cRange = [0.03, 0.18]) {
  return Array.from({ length: n }, (_, i) => {
    const t = i / (n - 1);
    return formatHex(oklch({
      l: lRange[0] + t * (lRange[1] - lRange[0]),
      c: cRange[0] + t * (cRange[1] - cRange[0]),
      h: hue,
    }));
  });
}
```

### Use culori with D3 scales

```js
import { interpolate, oklch, formatHex } from "culori";
import * as d3 from "d3";

// Create a D3-compatible interpolator in oklch space
const oklchInterpolator = (a, b) => {
  const interp = interpolate([a, b], "oklch");
  return t => formatHex(interp(t));
};

const scale = d3.scaleSequential()
  .domain([0, 100])
  .interpolator(oklchInterpolator("#08306b", "#deebf7"));
```

### APCA contrast check for chart elements

```js
import { APCAcontrast, sRGBtoY } from "apca-w3";

function parseHexToRGBA(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b, 1.0];
}

function checkChartContrast(fgHex, bgHex, role = "label") {
  const Lc = Math.abs(APCAcontrast(
    sRGBtoY(parseHexToRGBA(fgHex)),
    sRGBtoY(parseHexToRGBA(bgHex))
  ));
  const thresholds = { label: 45, axis: 60, body: 75, title: 90 };
  const min = thresholds[role] || 45;
  return { Lc, pass: Lc >= min, required: min };
}

// Usage
checkChartContrast("#666666", "#ffffff", "axis");
// → { Lc: 63.2, pass: true, required: 60 }
```

### Import Crameri batlow for D3

```js
// From Observable notebook (@xaquingv/fabio-crameris-color-schemes)
// or manually extract 256 hex stops from Zenodo download

const batlow = [
  "#011959", "#0b1c5a", "#121f5a", "#17225a", "#1c255a", "#20285b",
  // ... 250 more stops ...
  "#f9fb21"
];

const batlowScale = d3.scaleSequential()
  .domain([0, maxValue])
  .interpolator(d3.interpolateRgbBasis(batlow));

// Or with fewer stops (less smooth but sufficient for most uses):
const batlow9 = ["#011959","#103f60","#1c7a5a","#5da544","#b5b640","#e2c35c","#f5d380","#fae5a8","#f9fb21"];
const batlowScale9 = d3.scaleSequential()
  .domain([0, maxValue])
  .interpolator(d3.interpolateRgbBasis(batlow9));
```

### CSS oklch() for SVG styling (no JS conversion needed)

```js
// Generate a categorical scale using CSS oklch directly
const n = 6;
const categoricalOklch = d3.range(n).map(i =>
  `oklch(65% 0.15 ${(i * 360) / n + 30})`
);

d3.selectAll("rect")
  .data(data)
  .join("rect")
  .attr("fill", d => categoricalOklch[d.category]);
// Browser renders oklch natively — no hex conversion needed
```

### Validate palette with both WCAG 2 and APCA

```js
function auditPalette(colors, background, role = "label") {
  return colors.map(c => {
    const wcag2 = contrastRatio(c, background);  // from existing SKILL.md
    const apca = checkChartContrast(c, background, role);
    return {
      color: c,
      wcag2: { ratio: wcag2, passAA: wcag2 >= 4.5 },
      apca: apca,
      recommendation: apca.pass && wcag2 >= 3 ? "ok" :
        !apca.pass && wcag2 >= 4.5 ? "WCAG2 ok but APCA too low — check dark mode" :
        apca.pass && wcag2 < 3 ? "APCA ok but WCAG2 too low — may fail compliance" :
        "fail both — increase contrast"
    };
  });
}
```

## Sources

- [ColorBrewer](https://colorbrewer2.org/) — Cynthia Brewer's palette selection tool
- [ColorBrewer scheme types](https://colorbrewer2.org/learnmore/schemes_full.html)
- [d3-scale-chromatic](https://d3js.org/d3-scale-chromatic) — D3's built-in color schemes
- [d3-scale-chromatic GitHub](https://github.com/d3/d3-scale-chromatic)
- [Crameri Scientific Colour Maps](https://www.fabiocrameri.ch/colourmaps/)
- [Crameri batlow](https://www.fabiocrameri.ch/batlow/)
- [Crameri on Zenodo](https://zenodo.org/records/8409685)
- [Crameri in Observable](https://observablehq.com/@xaquingv/fabio-crameris-color-schemes)
- [Crameri in R (khroma)](https://cran.r-project.org/web/packages/khroma/vignettes/crameri.html)
- [OKLCH Color Picker](https://oklch.org/)
- [OKLCH on MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color_value/oklch)
- [Chris Henrick: Color experiments with OKLCH](https://clhenrick.io/blog/color-experiments-with-oklch/)
- [d3-color OKLCH issue #87](https://github.com/d3/d3-color/issues/87)
- [Culori — Color functions for JavaScript](https://culorijs.org/)
- [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html)
- [Why APCA](https://git.apcacontrast.com/documentation/WhyAPCA.html)
- [apca-w3 npm](https://www.npmjs.com/package/apca-w3)
- [APCA GitHub (SAPC-APCA)](https://github.com/Myndex/SAPC-APCA)
- [D3 Color Schemes on Observable](https://observablehq.com/@d3/color-schemes)
- [Accessible Colors: From WCAG to APCA](https://capellic.com/insights/accessible-colors)
- [OKLab Color Space](https://bottosson.github.io/posts/oklab/) — Bjorn Ottosson
