# Scales Research

Research into state-of-the-art scale and axis techniques for the `skills/scales/SKILL.md` skill.

## Current Coverage

The existing skill covers:

- **Log vs Symlog** -- zeros break log, symlog handles them, constant parameter tuning
- **Band vs Point** -- bands have width (bars), points don't (dots)
- **Time Gaps** -- band approach and index approach for removing weekends in financial data
- **Responsive Tick Counts** -- ResizeObserver, pixels-per-tick heuristics (60-150px depending on content)
- **scaleUtc over scaleTime** -- DST distortion avoidance
- **.nice() pitfalls** -- when rounding breaks semantics (percentages, brush extents, zero baselines)
- **Label Collision** -- fewer ticks, truncation, staggering, rotation (in that order)
- **Dual-Y Axes** -- dangers, color-coding rules, zero-inclusion, scatter plot alternative
- **Broken / Discontinuous Axes** -- piecewise scale builder, zigzag break symbol, when not to break
- **Multi-Level Time Ticks** -- conditional formatting by granularity
- **Grid Lines** -- when to use, clutter tradeoffs
- **Axis Transitions** -- domain-first update, deduplication guard
- **Common Pitfalls** -- manual labels, tick count suggestions, unsorted bands, missing zero

**Gaps in coverage:** diverging scales, classification scales (quantile/quantize/threshold), perceptual uniformity guidance, scale inference patterns, expanded decision framework.

## Diverging Scales (midpoint selection, asymmetric data)

### Core Concept

`d3.scaleDiverging` uses a **three-element domain**: `[minimum, midpoint, maximum]`. The midpoint (pivot) maps to the neutral color at interpolator value 0.5. Values below the midpoint map to 0-0.5; values above map to 0.5-1.

### The Asymmetric Problem

Real data is rarely symmetric around the midpoint. Temperature anomalies might range from -2 to +8 degrees. Naive `d3.scaleDiverging([-2, 0, 8], interpolateRdBu)` works correctly -- the scale normalizes each side independently. A value of -2 maps to interpolator 0.0 (full red), 0 maps to 0.5 (white), and +8 maps to 1.0 (full blue). The two sides stretch differently, which is correct behavior -- the alternative (symmetric clamping to [-8, 0, 8]) wastes color resolution on the negative side.

### When to Force Symmetry

Force a symmetric domain when **proportional comparison across the midpoint matters**. If +4 should look as intense as -4, use:

```js
const max = Math.max(Math.abs(d3.min(data, d => d.value)), Math.abs(d3.max(data, d => d.value)));
const color = d3.scaleDiverging([-max, 0, max], d3.interpolateRdBu);
```

This wastes color range but prevents the visual lie where +2 and -2 appear as different intensities.

### Variants for Skewed Data

D3 provides transform-aware diverging scales for data that clusters near zero:

- `d3.scaleDivergingLog` -- log transform on both sides of the midpoint
- `d3.scaleDivergingPow` -- power transform (use `.exponent()`)
- `d3.scaleDivergingSqrt` -- square root transform
- `d3.scaleDivergingSymlog` -- symmetric log (handles zeros)

### Observable Plot's `pivot` Option

Observable Plot uses a `pivot` option on color scales to set the midpoint for diverging schemes. This is cleaner than manually constructing a three-element domain:

```js
Plot.plot({
  color: { type: "diverging", scheme: "RdBu", pivot: 0 },
  marks: [Plot.cell(data, { fill: "change" })]
})
```

### Candidate Code Pattern

```js
// Diverging choropleth: election margin
// Negative = party A, positive = party B, zero = tie
const extent = d3.extent(data, d => d.margin);
const color = d3.scaleDiverging([extent[0], 0, extent[1]], d3.interpolateRdBu);

// Force symmetric when proportional comparison matters
const absMax = Math.max(Math.abs(extent[0]), Math.abs(extent[1]));
const colorSym = d3.scaleDiverging([-absMax, 0, absMax], d3.interpolateRdBu);
```

## Classification Scales (quantile vs quantize vs threshold for choropleths)

Classification is the single most impactful decision in choropleth design. The same data mapped through different classification methods tells different stories.

### The Three D3 Classification Scales

**`d3.scaleQuantize`** -- Divides the domain's *value range* into equal-width bins.
- Domain: `[min, max]` (the extent)
- Each bin spans `(max - min) / n` value units
- **Effect:** Preserves the shape of the value distribution. If data is skewed, most values land in one or two bins.
- **Use when:** The absolute magnitude differences matter. "How far from the mean?"

**`d3.scaleQuantile`** -- Divides the *sorted data* into bins with equal counts.
- Domain: the full array of values (not just extent)
- Each bin contains roughly `values.length / n` observations
- **Effect:** Maximizes visual contrast -- every color appears equally on the map. But it hides the actual distribution; a gap between 10 and 1000 looks the same as between 10 and 11.
- **Use when:** Relative ranking matters more than absolute values. "Which counties are in the top 20%?"

**`d3.scaleThreshold`** -- Manual breakpoints chosen by the analyst.
- Domain: array of threshold values (n-1 thresholds for n bins)
- **Effect:** Full editorial control. Can align with policy thresholds, scientific standards, or natural break points.
- **Use when:** Domain knowledge dictates meaningful boundaries (poverty line, safety limits, legislative thresholds).

### Jenks Natural Breaks

Not built into D3, but widely used in GIS. The Jenks optimization minimizes within-class variance and maximizes between-class variance -- it finds "natural" clusters in the data. Implementations exist in libraries like `simple-statistics`:

```js
import { jenks } from "simple-statistics";
const breaks = jenks(values, 5); // returns 6 boundary values for 5 classes
const color = d3.scaleThreshold(breaks.slice(1, -1), d3.schemeBlues[5]);
```

**Use when:** Data has natural clusters but you don't know where. Jenks finds them. Not recommended for low-variance data (where clusters are artifacts of noise).

### Classification Decision Framework

| Question | Answer | Method |
|----------|--------|--------|
| Are there known meaningful thresholds? | Yes | Threshold |
| Does ranking matter more than magnitude? | Yes | Quantile |
| Is the distribution roughly uniform? | Yes | Quantize |
| Is the distribution clustered? | Yes | Jenks (via threshold) |
| Is the distribution heavily skewed? | -- | Quantile (but warn viewer) |

### Common Trap: Quantile Hides the Distribution

Because quantile always produces equal-count bins, two very different distributions produce identical-looking maps. A bimodal distribution and a uniform distribution are indistinguishable. Always pair a quantile choropleth with a histogram showing the actual distribution and break points.

## Perceptual Uniformity (why interpolateViridis beats interpolateRdYlGn)

### The Problem with Rainbow/Spectral Scales

Rainbow and spectral color maps (including `interpolateRainbow`, `interpolateRdYlGn`) have uneven perceptual steps. Yellow bands appear brighter than blue bands of equal data magnitude. The viewer perceives false boundaries where hue changes rapidly and misses real gradients where hue is locally uniform. This is a well-documented failure mode in visualization research.

### What Perceptual Uniformity Means

A perceptually uniform color scale has equal perceptual distance for equal data distance across its entire range. In CIELAB color space, a step of delta-E = 1 is supposed to be "just noticeable" regardless of where in the color space you are. Viridis was designed to have monotonically increasing lightness and consistent perceptual steps in CIELAB.

### Why Viridis (and Siblings) Win

The viridis family (viridis, magma, inferno, plasma, cividis) were designed with three constraints:

1. **Monotonic lightness** -- works when printed in grayscale
2. **Perceptual uniformity** -- equal data steps produce equal visual steps
3. **Colorblind safety** -- avoids red-green reliance (viridis uses blue-yellow-green arc)

`cividis` goes further: it was mathematically optimized for deuteranopia and protanopia (the most common forms of color vision deficiency), producing near-identical perception for color-blind and normal-vision viewers.

### When Diverging Beats Sequential

Viridis is sequential -- it has a direction. For data with a meaningful midpoint (temperature anomaly, election margin, profit/loss), a diverging scheme is correct even though most diverging schemes (RdBu, PiYG, PuOr) are not perceptually uniform. The tradeoff is worth it: the midpoint semantics matter more than perfect uniformity.

### Practical Guidance for the Skill

- **Sequential data (counts, rates, magnitudes):** Use viridis, magma, or plasma. Avoid rainbow/jet/spectral.
- **Diverging data (deviations from center):** Use PuOr or RdBu. Accept the uniformity tradeoff.
- **Categorical data:** Use Tol's qualitative palette or d3.schemeTableau10.
- **Print/grayscale:** viridis and magma degrade gracefully. RdBu does not.
- Cross-reference with `skills/color/SKILL.md` for full color guidance.

### Key References

- [Viridis introduction (R/matplotlib)](https://cran.r-project.org/web/packages/viridis/vignettes/intro-to-viridis.html)
- [Kenneth Moreland's color map advice](https://www.kennethmoreland.com/color-advice/)
- [Crameri et al. (2020) "The misuse of colour in science communication"](https://www.nature.com/articles/s41467-020-19160-7)
- [PLoS ONE: Optimizing colormaps for color vision deficiency](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0199239)

## Scale Inference (Observable Plot's approach, what D3 could learn)

### How Plot Infers Scale Types

Observable Plot examines the first non-null, non-undefined channel value and applies simple rules:

| Value type | Inferred scale type |
|-----------|-------------------|
| String or boolean | Ordinal (or band for bar marks) |
| Date | UTC |
| Number | Linear |
| Explicit domain with 3+ elements | Ordinal / Point |

Mark declarations can override inference: `barX` forces y to band; `fx`/`fy` are always band.

### Color Scale Inference

Plot's color scale defaults to linear with the turbo scheme, but supports specialized types: `categorical`, `sequential`, `diverging`, `threshold`, `quantile`, `quantize`. The `pivot` option on diverging color scales sets the midpoint -- cleaner than D3's three-element domain.

### What D3 Could Learn (Patterns for the Skill)

D3 is deliberately low-level -- it doesn't infer. But skill users benefit from a decision procedure:

```
1. Is the data categorical?
   - Unordered categories → scaleOrdinal + schemeTableau10
   - Ordered categories → scaleBand (bars) or scalePoint (dots)

2. Is the data temporal?
   - Always → scaleUtc (not scaleTime)
   - Financial with gaps → band or index approach

3. Is the data quantitative?
   - Spans < 1 order of magnitude → scaleLinear
   - Spans 2+ orders, strictly positive → scaleLog
   - Spans 2+ orders, includes zero/negatives → scaleSymlog
   - Has meaningful midpoint → scaleDiverging
   - Needs discrete classes → scaleQuantize/Quantile/Threshold

4. Is this a color encoding?
   - Sequential → d3.interpolateViridis (or magma/plasma)
   - Diverging → d3.interpolateRdBu with explicit midpoint
   - Categorical → d3.schemeTableau10
   - Classification → scaleQuantize/Quantile/Threshold + scheme
```

### Plot's `interval` Option

Plot can snap continuous scales to intervals: `{ x: { interval: "week" } }` forces the x-axis to align to week boundaries. D3 equivalent: `.ticks(d3.utcWeek)`. Worth mentioning in the skill for time-series alignment.

## Scale Breaks and Discontinuities (gap encoding, split axes)

### Current Coverage

The skill already covers broken axes (piecewise scale builder) and time gaps (band/index approaches). What's missing: the d3fc discontinuous scale library and more sophisticated gap-encoding patterns.

### d3fc-discontinuous-scale

The `@d3fc/d3fc-discontinuous-scale` package wraps any D3 scale and removes specified domain regions. It provides discontinuity providers:

- **`discontinuitySkipWeekends()`** -- removes Saturday and Sunday from time scales
- **`discontinuitySkipUtcWeekends()`** -- same, UTC-aware
- **`discontinuityRange(min, max)`** -- removes an arbitrary value range
- **`discontinuityIdentity()`** -- no-op, for toggling

```js
import { scaleDiscontinuous, discontinuitySkipWeekends } from "@d3fc/d3fc-discontinuous-scale";

const x = scaleDiscontinuous(d3.scaleTime())
  .discontinuityProvider(discontinuitySkipWeekends())
  .domain([startDate, endDate])
  .range([marginLeft, width - marginRight]);
```

### Custom Discontinuity Providers

A provider implements four methods:

- `clampUp(value)` -- if value falls in a gap, shift forward to gap boundary
- `clampDown(value)` -- if value falls in a gap, shift backward to gap boundary
- `distance(start, end)` -- distance between two values minus gap regions
- `offset(value, step)` -- advance by step, skipping gaps

This is useful for market hours (skip overnight), holidays, or any domain-specific non-trading periods.

### When to Use Each Approach

| Technique | Best for | Trade-off |
|-----------|----------|-----------|
| Band/index (current skill) | Simple weekend removal | Loses proportional time spacing |
| d3fc discontinuous | Complex gaps (holidays, market hours) | External dependency |
| Piecewise broken scale (current skill) | Value-axis outlier gaps | Visual break symbol needed |
| Annotation markers | Gaps that ARE the story | No scale manipulation needed |

### Gap Encoding Best Practices

- **Always visually mark discontinuities.** A zigzag break symbol, dashed region, or gap annotation prevents the viewer from misreading the chart.
- **Don't remove gaps that carry meaning.** Sensor outages, market halts, and data blackouts are information. Hiding them hides the story.
- **For intraday financial data**, combine weekend skipping with market-hours-only filtering: skip weekends AND skip 8pm-8am.

## Decision Guidance (expanded scale selection framework)

### Position Scale Selection

```
Quantitative position:
  Linear by default
  → Log if strictly positive, 2+ orders of magnitude
  → Symlog if zeros/negatives possible, wide range
  → Pow/Sqrt for area-proportional sizing (sqrt for circle radius)
  → Diverging for deviation-from-center

Categorical position:
  → Band for marks with extent (bars, heatmap cells)
  → Point for marks at a position (dots, line endpoints)

Temporal position:
  → scaleUtc always (not scaleTime)
  → Band/index for gap removal
  → d3fc discontinuous for complex gaps
```

### Color Scale Selection

```
Sequential (magnitude, count, rate):
  → interpolateViridis/magma/plasma for perceptual uniformity
  → interpolateBlues/Greens for single-hue simplicity
  → Avoid: rainbow, jet, spectral

Diverging (deviation from midpoint):
  → interpolateRdBu, interpolatePuOr
  → Set midpoint explicitly via 3-element domain
  → Force symmetric domain only when proportional comparison needed

Categorical (nominal groups):
  → schemeTableau10 (up to 10)
  → Tol qualitative (colorblind-safe)

Classification (choropleth):
  → Quantize for uniform distributions (equal-width bins)
  → Quantile for skewed distributions (equal-count bins)
  → Threshold for domain-specific breakpoints
  → Jenks for clustered data (via simple-statistics + threshold)
```

### The "Should I Transform?" Checklist

1. Plot a histogram of your data values first
2. If the histogram is roughly uniform or normal: linear
3. If the histogram is right-skewed with a long tail: log or symlog
4. If the histogram is bimodal or clustered: consider threshold/Jenks classification
5. If the histogram has a meaningful center: diverging
6. If the histogram has extreme outliers: consider broken axis, but only if the outlier isn't the story

## Code Patterns

### Diverging Choropleth with Asymmetric Domain

```js
// Election margin: negative = Dem, positive = Rep
const margin = data.map(d => d.rep - d.dem);
const extent = d3.extent(margin);

// Asymmetric: let each side use full color range
const color = d3.scaleDiverging([extent[0], 0, extent[1]], d3.interpolateRdBu);

// Symmetric: equal intensity at equal distance from zero
const absMax = Math.max(-extent[0], extent[1]);
const colorSym = d3.scaleDiverging([-absMax, 0, absMax], d3.interpolateRdBu);
```

### Quantile Choropleth with Legend

```js
const values = data.map(d => d.rate);
const color = d3.scaleQuantile(values, d3.schemeBlues[5]);

// Legend showing actual break values
const thresholds = color.quantiles(); // [q1, q2, q3, q4]
const legendData = d3.pairs([d3.min(values), ...thresholds, d3.max(values)]);
// legendData = [[min, q1], [q1, q2], [q2, q3], [q3, q4], [q4, max]]
```

### Jenks Natural Breaks via simple-statistics

```js
import { jenks } from "simple-statistics";

const values = data.map(d => d.value);
const breaks = jenks(values, 5); // [min, b1, b2, b3, b4, max]
const color = d3.scaleThreshold(
  breaks.slice(1, -1),  // inner boundaries only
  d3.schemeYlOrRd[5]
);
```

### Scale Type Inference Helper

```js
// Infer appropriate scale from data (Observable Plot-style heuristic)
function inferScaleType(values) {
  const sample = values.find(v => v != null);
  if (sample instanceof Date) return "utc";
  if (typeof sample === "string" || typeof sample === "boolean") return "ordinal";
  if (typeof sample === "number") {
    const [min, max] = d3.extent(values);
    if (min < 0) return "symlog";  // negatives suggest symlog over log
    if (max / Math.max(min, 1e-10) > 100) return "log";  // 2+ orders of magnitude
    return "linear";
  }
  return "linear";
}
```

### d3fc Discontinuous Scale for Market Hours

```js
import { scaleDiscontinuous, discontinuitySkipWeekends } from "@d3fc/d3fc-discontinuous-scale";

const x = scaleDiscontinuous(d3.scaleUtc())
  .discontinuityProvider(discontinuitySkipWeekends())
  .domain(d3.extent(data, d => d.date))
  .range([marginLeft, width - marginRight]);

// Axis ticks automatically skip weekends
svg.append("g")
  .attr("transform", `translate(0,${height - marginBottom})`)
  .call(d3.axisBottom(x).ticks(d3.utcMonday));
```

### Classification Method Comparison Panel

```js
// Side-by-side choropleths showing how classification changes the story
const values = data.map(d => d.rate);
const methods = {
  quantize: d3.scaleQuantize(d3.extent(values), d3.schemeBlues[5]),
  quantile: d3.scaleQuantile(values, d3.schemeBlues[5]),
  threshold: d3.scaleThreshold([10, 20, 50, 100], d3.schemeBlues[5]),
};
// Render each into a small multiple; the visual difference IS the lesson
```

## Sources

- [D3 Diverging Scales](https://observablehq.com/@d3/diverging-scales)
- [D3 Quantile, Quantize, Threshold](https://observablehq.com/@d3/quantile-quantize-and-threshold-scales)
- [Observable Plot Scales](https://observablehq.com/plot/features/scales)
- [d3fc Discontinuous Scale](https://github.com/d3fc/d3fc/blob/master/packages/d3fc-discontinuous-scale/README.md)
- [Building a Complex Financial Chart with D3 and d3fc](https://blog.scottlogic.com/2018/09/21/d3-financial-chart.html)
- [Kenneth Moreland: Color Map Advice](https://www.kennethmoreland.com/color-advice/)
- [Viridis Introduction](https://cran.r-project.org/web/packages/viridis/vignettes/intro-to-viridis.html)
- [PLoS ONE: Optimizing Colormaps for CVD](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0199239)
- [Classification Methods for Choropleth Maps](https://gisgeography.com/choropleth-maps-data-classification/)
- [Caglar Koylu: Classification Scales](https://observablehq.com/@caglarkoylu/classification-quantile-quantize-and-threshold-scales)
- [Coloring Maps (Adam Pearce)](https://roadtolarissa.com/coloring-maps/)
- [Datawrapper: Broken Y-Axis](https://blog.datawrapper.de/broken-y-axis/)
- [Datawrapper: Dual-Axis Charts](https://blog.datawrapper.de/dualaxis/)
