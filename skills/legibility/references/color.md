# Color

Absorbed from the v2 `color` skill. Open for exact palette values, CVD or contrast checks, compositing modes, or generating a custom palette.

## Perception, briefly

- **Lightness dominates.** A hue-only ramp at constant lightness looks flat. Grayscale test: order must survive.
- **Simultaneous contrast.** A choropleth region's apparent color shifts with its neighbors. Thin borders and lightness-varying ramps reduce it.
- **Small-area effect.** Dots and thin lines read paler than swatches, so boost chroma:

```js
const boosted = hex => { const c = d3.hcl(hex); c.c = Math.min(130, (c.c || 0) + 20); c.l = Math.max(20, c.l - 5); return c.formatHex(); };
```

- **Mach bands.** Continuous legends show illusory stripes at bin edges. Discrete legends avoid it.

## Color spaces

| Space | Use |
|---|---|
| Lab | two-stop sequential gradients, neutral zones of diverging ramps |
| HCL | D3's `interpolateHcl`, fine for most gradients; hue is undefined near white/black |
| OKLCH | generating N evenly spaced hues (fixes HCL's blue-purple unevenness), CSS-native `oklch(65% 0.15 240)`. d3-color has no OKLCH, so use CSS strings or culori |

Evenly spaced categorical hues at fixed lightness and chroma:

```js
const oklchPalette = n => d3.range(n).map(i => `oklch(65% 0.15 ${(i * 360) / n + 30})`);
```

CSS color strings work as SVG/Canvas fills. They can't go through d3 interpolators; resolve them to hex first.

## Paul Tol palettes (exact)

Source: personal.sron.nl/~pault. Full set with more schemes in `../scripts/tol-palettes.js`.

Qualitative (never interpolate):

```js
const tol = {
  bright:       ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"],
  vibrant:      ["#EE7733", "#0077BB", "#33BBEE", "#EE3377", "#CC3311", "#009988", "#BBBBBB"],
  muted:        ["#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE", "#882255", "#44AA99", "#999933", "#AA4499"],
  highContrast: ["#004488", "#DDAA33", "#BB5566"],
  light:        ["#77AADD", "#EE8866", "#EEDD88", "#FFAABB", "#99DDFF", "#44BB99", "#BBCC33", "#AAAA00", "#DDDDDD"],
};
```

Use: bright for general ≤7, vibrant as an alternative to bright, muted for 6-9 in dense plots, highContrast for 2-3, light behind text labels.

Diverging and sequential, with each scheme's bad-data color:

```js
const tolRamps = {
  sunset:  { bad: "#FFFFFF", stops: ["#364B9A", "#4A7BB7", "#6EA6CD", "#98CAE1", "#C2E4EF", "#EAECCC", "#FEDA8B", "#FDB366", "#F67E4B", "#DD3D2D", "#A50026"] },
  buRd:    { bad: "#FFEE99", stops: ["#2166AC", "#4393C3", "#92C5DE", "#D1E5F0", "#F7F7F7", "#FDDBC7", "#F4A582", "#D6604D", "#B2182B"] },
  prGn:    { bad: "#FFEE99", stops: ["#762A83", "#9970AB", "#C2A5CF", "#E7D4E8", "#F7F7F7", "#D9F0D3", "#ACD39E", "#5AAE61", "#1B7837"] },
  ylOrBr:  { bad: "#888888", stops: ["#FFFFE5", "#FFF7BC", "#FEE391", "#FEC44F", "#FB9A29", "#EC7014", "#CC4C02", "#993404", "#662506"] },
};
const ramp = name => d3.interpolateRgbBasis(tolRamps[name].stops);
const withBad = (scale, bad) => Object.assign(v => (v == null || Number.isNaN(v) ? bad : scale(v)), scale);
```

## Bivariate (Joshua Stevens 3×3)

Index with `grid[yBin * 3 + xBin]`, bins 0-2 from two `scaleQuantile`s.

```js
const bivariate = {
  pinkBlue:   ["#e8e8e8", "#ace4e4", "#5ac8c8", "#dfb0d6", "#a5add3", "#5698b9", "#be64ac", "#8c62aa", "#3b4994"],
  greenBlue:  ["#e8e8e8", "#b5c0da", "#6c83b5", "#b8d6be", "#90b2b3", "#567994", "#73ae80", "#5a9178", "#2a5a5b"],
  purpleGold: ["#e8e8e8", "#e4d9ac", "#c8b35a", "#cbb8d7", "#c8ada0", "#af8e53", "#9972af", "#976b82", "#804d36"],
  blueRed:    ["#e8e8e8", "#e4acac", "#c85a5a", "#b0d5df", "#ad9ea5", "#985356", "#64acbe", "#627f8c", "#574249"],
};
```

Pink-blue is the safest for CVD, and blue-red the least.

## Color vision deficiency

| Type | Prevalence | Merges |
|---|---|---|
| Deuteranomaly/-opia | ~6% of males | red / green / brown |
| Protanomaly/-opia | ~2% of males | red / green, reds darken |
| Tritanopia | very rare | blue / green, yellow / pink |

Simulate with `../scripts/colorblind-sim.js` (Brettel/Viénot). Canvas: run it on `getImageData`.

## Contrast

- WCAG 2.x relative-luminance ratio: ≥4.5:1 text, ≥3:1 large text and meaningful graphics (SC 1.4.11). Still the compliance bar.
- APCA (WCAG 3 draft) is polarity-aware and more accurate on dark backgrounds. Rough targets: Lc 75 body text, 60 axis labels, 45 large callouts. Package `apca-w3`.

## Compositing (Canvas)

| `globalCompositeOperation` | Use |
|---|---|
| `lighter` | additive density on dark backgrounds |
| `multiply` | overlap darkening on light backgrounds; tinting a pattern over a fill |
| `screen` | glow on dark |
| `difference` | change detection between two layers |
| `destination-out` | cutouts, erasing |
| `source-in` | clip new drawing to existing pixels |

Always restore `source-over`. Multi-group additive density: give each group a different dominant channel so overlaps blend to recognizable mixes.

## Wide gamut

`matchMedia("(color-gamut: p3)")`. Canvas: `getContext("2d", { colorSpace: "display-p3" })`. This helps categorical separation. It doesn't matter for lightness ramps.

## Pitfalls

- `schemeCategory10` and `schemeSet1` are not CVD-safe.
- `globalAlpha` × rgba alpha multiply.
- Two 50% layers make 75%, not 100%.
- rgba transparency prints unreliably, so use opaque colors plus patterns for print.
- Don't parse `d3.color()` inside render loops. Precompute.
