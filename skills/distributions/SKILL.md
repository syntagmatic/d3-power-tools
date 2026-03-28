---
name: distributions
description: "Build statistical distribution charts with D3.js. Use this skill when the user wants box plots, violin plots, ridgeline/joy plots, density plots, bee swarm plots, strip/jitter plots, QQ plots, raincloud plots, or letter-value plots. Covers kernel density estimation, quartile calculation, outlier detection, grouped/faceted statistical comparisons, and animated transitions between distribution views."
---

# Distribution Charts

Every distribution chart answers one question: what does the data look like? The danger is that some charts answer confidently even when they're lying — a box plot will show clean quartiles for bimodal data that has two peaks and no center.

For axis patterns, see `scales`. For animated transitions, see `motion`. For force-based layouts (bee swarm), see `force`. For color palettes, see `color`.

## Choosing a Distribution Chart

The choice is analytical, not aesthetic. Each chart type conceals something:

| Chart | Best When | Shows | Hides |
|-------|-----------|-------|-------|
| **Histogram** | Small n (< 50), exploring bin structure | Actual counts, gaps, discreteness | Smoothness is an illusion of bin width |
| **Box plot** | Comparing medians across 5+ groups | Median, quartiles, outliers | Shape — bimodal data looks identical to unimodal |
| **Letter-value plot** | Large n (200+), tail behavior matters | Nested quantiles, tail asymmetry | Shape (less than box plot, but shows more of the tail) |
| **Violin plot** | Distribution shape matters (bimodal, skewed) | Full density shape, symmetry | Individual points; KDE fabricates shape from < 30 points |
| **Raincloud** | Shape + individuals + summary, n 20–2000 | All three: density, points, quartiles | Nothing — but space-intensive (limit to 2–8 groups) |
| **Ridgeline** | Comparing many (6+) ordered distributions | Trend across groups, density overlap | Precise comparison (rows lack shared y baseline) |
| **Bee swarm** | Individual observations matter, n < 500/group | Every point, gaps, clusters | Nothing — but force simulation degrades past ~500 pts |
| **Strip/jitter** | Quick overview, any n | Raw data distribution | Overplots past ~200 pts/group without opacity |
| **Density plot** | Comparing 2–4 overlapping distributions | Smooth shape, overlap regions | Individual values; bandwidth choice shapes what you see |

**The box plot trap.** Two datasets — one normal, one bimodal with the same median and IQR — produce identical box plots. If you haven't confirmed unimodality, a box plot hides the most important feature. Use a violin or overlay raw points to check.

**Combining charts** improves insight: violin + inner box shows shape and summary; bee swarm + median line shows individuals and center. Raincloud plots (half-violin + strip + box) give all three.

### Quick Selection by Sample Size

- **n < 10:** strip + median line. No summary stats — too few for reliable estimates.
- **n 10–30:** strip + box or bee swarm. No KDE — too few for reliable density.
- **n 30–500:** raincloud, violin, or bee swarm. Choose by number of groups.
- **n 500–5000:** violin + box or letter-value plot. Individual points overplot; use density.
- **n 5000+:** letter-value plot or violin. Never bee swarm or strip.

**When NOT to use:**
- **Box plots with n < 10** — quartiles from tiny samples are noise; just show raw points
- **Violin plots with n < 30** — KDE invents smooth curves from sparse data
- **Density plots for small samples** — use a histogram; it shows what you actually observed
- **Bee swarm with n > 500/group** — force simulation becomes slow; switch to jitter or violin
- **Ridgeline for unordered categories** — vertical stacking implies order; use faceted violins
- **Any smoothed chart when data is discrete** — KDE smears probability across impossible values (e.g., density at 3.5 children)

## Kernel Density Estimation (KDE)

KDE smooths raw data into a continuous density curve. Bandwidth is the single most consequential choice — it determines what the viewer sees as "signal" vs "noise."

```js
const gaussian = (x) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

function kde(kernel, bandwidth, data) {
  return (points) => points.map(x => [
    x,
    d3.mean(data, v => kernel((x - v) / bandwidth)) / bandwidth
  ]);
}

// Usage: extend 3 bandwidths past data extent to avoid edge truncation
const extent = d3.extent(values);
const ticks = d3.ticks(extent[0] - 3 * bandwidth, extent[1] + 3 * bandwidth, 200);
const density = kde(gaussian, bandwidth, values)(ticks);
```

### Bandwidth: A Judgment Call

Bandwidth is not a technical parameter — it's an editorial decision about what features to show.

**Too small:** every data point becomes its own peak, fabricating modes. **Too large:** real features merge; a bimodal distribution becomes unimodal.

**Silverman's rule** — good default for roughly normal data:

```js
const sorted = Float64Array.from(values).sort();
const std = d3.deviation(values), iqr = d3.quantile(sorted, 0.75) - d3.quantile(sorted, 0.25);
// Use smaller of std and IQR/1.34 to handle outlier-inflated std
const bandwidth = 0.9 * Math.min(std, iqr / 1.34) * Math.pow(values.length, -0.2);
```

**When to override:** Bimodal data — halve bandwidth (Silverman over-smooths). Very skewed — log-transform before KDE. Small samples (n < 30) — increase 20-50% or use histogram.

**Defensive KDE.** Clip density to the observed data range for bounded data (negative durations, scores above 100). The 3-bandwidth extension above prevents edge truncation but can show density at impossible values.

## Descriptive Statistics Helper

Compute everything once per group — avoids repeated sorting and quantile calculation:

```js
function computeStats(values) {
  const sorted = Float64Array.from(values).sort();
  const q1 = d3.quantile(sorted, 0.25), q3 = d3.quantile(sorted, 0.75), iqr = q3 - q1;
  const lowerFence = q1 - 1.5 * iqr, upperFence = q3 + 1.5 * iqr;
  return {
    min: sorted[0], max: sorted[sorted.length - 1],
    q1, median: d3.quantile(sorted, 0.5), q3, iqr,
    mean: d3.mean(sorted), std: d3.deviation(sorted),
    whiskerLow: d3.min(sorted.filter(v => v >= lowerFence)),
    whiskerHigh: d3.max(sorted.filter(v => v <= upperFence)),
    outliers: sorted.filter(v => v < lowerFence || v > upperFence),
    n: sorted.length,
  };
}
```

## Notched Box Plot

Notches indicate confidence interval around the median. Non-overlapping notches between two boxes suggest significantly different medians (~95% confidence).

```js
const notchHalf = 1.57 * stats.iqr / Math.sqrt(stats.n);
const notchLow = stats.median - notchHalf, notchHigh = stats.median + notchHalf;
const notchIndent = boxWidth * 0.15; // visual pinch at the median

// Draw as polygon: pinch inward at median height
const points = [
  [0, yScale(stats.q3)], [boxWidth, yScale(stats.q3)],
  [boxWidth, yScale(notchHigh)], [boxWidth - notchIndent, yScale(stats.median)],
  [boxWidth, yScale(notchLow)], [boxWidth, yScale(stats.q1)],
  [0, yScale(stats.q1)], [0, yScale(notchLow)],
  [notchIndent, yScale(stats.median)], [0, yScale(notchHigh)],
].map(p => p.join(",")).join(" ");

boxes.append("polygon").attr("points", points);
```

## Whisker Variants

- **1.5xIQR (Tukey)** — default. Points beyond flagged as outliers.
- **Min/Max** — full range, no outlier flagging. Use when there are no true outliers.
- **Percentile (5th/95th)** — consistent definition across groups regardless of distribution.
- **1 SD / 2 SD** — only when audience thinks in standard deviations. Misleading for skewed data.

## Ridgeline (Joy) Plots

`overlap` controls density: 0 = small multiples, 0.3-0.5 = readable, 0.7-1.0 = dramatic. Render bottom-to-top so lower rows appear in front.

```js
const overlap = 0.7;
const ridgeHeight = yBand.step() * (1 + overlap);
const densityYScale = d3.scaleLinear([0, maxDensity], [0, ridgeHeight]);

const area = d3.area()
  .x(d => xScale(d[0])).y0(0).y1(d => -densityYScale(d[1]))
  .curve(d3.curveBasis);

ridges.attr("transform", d => `translate(0, ${yBand(d.key) + yBand.bandwidth()})`);
```

## Bee Swarm: Dodge Algorithm

Faster alternative to force simulation — place points sorted, nudging to avoid overlap:

```js
function dodgeBeeswarm(data, xScale, radius) {
  const sorted = [...data].sort((a, b) => a.value - b.value);
  const placed = [];
  for (const d of sorted) {
    const targetX = xScale(d.value);
    let offsetY = 0, direction = 1;
    while (placed.some(p => Math.hypot(targetX - p.x, offsetY - p.y) < radius * 2)) {
      offsetY += direction * radius * 0.5;
      direction = direction > 0 ? -direction - 0.5 : -direction + 0.5;
    }
    d.x = targetX;
    d.y = offsetY;
    placed.push(d);
  }
  return sorted;
}
```

For force-based bee swarm, pre-compute: `simulation.stop(); for (let i = 0; i < 120; i++) simulation.tick();` See `force` skill for simulation setup.

## Jitter Strategies

**Seeded random** — reproducible, won't shift on re-render:
```js
const random = d3.randomLcg(42);
const jitter = () => (random() - 0.5) * groupBandwidth * 0.6;
```

**Sinusoidal** — uniform spread without randomness:
```js
sortedData.forEach((d, i, arr) => { d.jitterX = Math.sin(i * Math.PI / arr.length) * bandwidth * 0.3; });
```

**Violin-constrained** — jitter width matches violin density at each y-position:
```js
// densityAt(value, group) returns KDE density for a given value in a given group
const jitterScale = d3.scaleLinear([0, maxDensity], [0, groupBandwidth / 2]);
circles.attr("cx", d => (Math.random() - 0.5) * 2 * jitterScale(densityAt(d.value, d.group)));
```

## Half (Split) Violin

Show two subgroups as left/right halves of the same violin:

```js
// Left half: group A density, mirrored left only
violin.append("path")
  .attr("d", d3.area()
    .x0(0).x1(d => -violinScale(d[1]))
    .y(d => yScale(d[0]))
    .curve(d3.curveCatmullRom)(densityA))
  .attr("fill", colorA);
// Right half: group B — same but positive x1
```

## Raincloud Plot

Half-violin + box plot + jittered strip, stacked asymmetrically (Allen et al. 2019; 0.43-0.76 SD improvement in interpretation vs single-view). Horizontal orientation (groups on y-axis) reads most naturally.

```js
// Layout: each group gets a band. Within the band:
//   top: half-violin (area, one side only) using kde() + d3.area()
//   middle: box plot (rect + lines) using computeStats()
//   bottom: jittered strip (circles) using seeded jitter
const bw = yBand.bandwidth();
const violinArea = d3.area()
  .x(d => xScale(d[0]))
  .y0(bw * 0.45)                          // baseline at midpoint
  .y1(d => bw * 0.45 - densityScale(d[1])) // density goes up
  .curve(d3.curveBasis);
```

**Defensive design** (Waskom 2023): clip density to observed data range — naive KDE extends into impossible values. For discrete or small-n data, consider a histogram-based half instead of KDE.

**When NOT to use:** n < 10 (density unreliable), n > 5000 (points overplot — use violin + box), more than 8 groups (use ridgelines).

## Letter-Value Plot (Large-n Box Plot)

Standard box plots show only median + quartiles regardless of n — with 10,000 points you can estimate 1/128th quantiles, but a box plot flags hundreds of expected tail values as "outliers." Letter-value plots (Hofmann, Wickham, Kafadar 2017) show progressively more quantile levels as nested, shrinking boxes. Letter values: M (median), F (fourths), E (eighths), D, C, B, A... Stop when unreliable: `k = floor(log2(n)) - 2` levels.

```js
function computeLetterValues(sorted) {
  const n = sorted.length, levels = [];
  let depth = (1 + n) / 2;
  levels.push({ letter: "M", lower: atDepth(sorted, depth), upper: atDepth(sorted, depth) });
  const letters = ["F", "E", "D", "C", "B", "A", "Z", "Y", "X", "W"];
  const maxLevels = Math.max(0, Math.floor(Math.log2(n)) - 2);
  for (let k = 0; k < Math.min(maxLevels, letters.length); k++) {
    depth = (1 + Math.floor(depth)) / 2;
    if (depth < 1) break;
    levels.push({ letter: letters[k], lower: atDepth(sorted, depth), upper: atDepth(sorted, n + 1 - depth) });
  }
  return levels;
}

function atDepth(sorted, depth) {
  const i = Math.floor(depth) - 1;
  return depth === Math.floor(depth) ? sorted[i] : (sorted[i] + sorted[i + 1]) / 2;
}

// Render: nested rects, widest at center, sequential color encodes depth
const widthScale = d3.scaleLinear([0, levels.length], [bandWidth, bandWidth * 0.15]);
const colorScale = d3.scaleSequential(d3.interpolateBlues).domain([-1, levels.length]);
```

**When it beats box plots:** large n (>200) where box plots flag too many "outliers," tail comparison, tail asymmetry. **When NOT to use:** small n (<100) — just use a box plot; or when shape matters more than tail quantiles — use violin.

## QQ Plot

Points on the diagonal mean data follows the reference distribution; curvature means no. Heavy tails curve up at right and down at left; skew curves one way throughout.

Plotting position: `p = (i + 0.5) / n` (Hazen). Standardize data: `(v - mean) / sd`. Use the Beasley-Springer-Moro rational approximation for `normalQuantile(p)` (inverse normal CDF) — a ~25-line pure math function with no D3 dependency.

### QQ Confidence Bands

95% pointwise envelope under the null (data is normal):

```js
const confBands = theoreticalQuantiles.map((z, i) => {
  const p = (i + 0.5) / n;
  const f = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI); // normal density at z
  const se = Math.sqrt(p * (1 - p) / n) / f;
  return { z, lower: z - 1.96 * se, upper: z + 1.96 * se };
});
```

## Overlapping Densities and Transitions

**Multiple densities:** draw widest first, or use `mix-blend-mode: multiply` with `fill-opacity: 0.3`. Limit to 2-4 groups; beyond that, use ridgeline.

**Chart type transitions:** pre-compute positions for each view (box, swarm, strip), then interpolate `cx`/`cy`. See `motion` skill.

## Density Scale Normalization

A hidden editorial choice that changes what the viewer concludes:

- **Per-group** (each violin same max width): compare shape, but n=10 looks as confident as n=10,000.
- **Shared density scale**: wider violins mean more data. Use when relative group sizes matter.
- **Width ~ sqrt(n)**: `violinScale.range([0, Math.sqrt(n) * scaleFactor])` — good default when group sizes vary >3x.

## Common Pitfalls

**Sorted input for d3.quantile.** `d3.quantile` requires sorted input. Unsorted data gives wrong quartiles with no error. Always sort first.

**KDE bandwidth too small.** With small samples (n < 30), Silverman's rule can produce very small bandwidths that create spiky, misleading density curves. Set a minimum bandwidth or increase by 20-50%.

**Violin width normalization.** If violins are normalized to the same max width, groups with very different sample sizes look identical in spread.

**Jitter hides density.** Random jitter in strip plots obscures where points cluster. When density matters, use bee swarm or violin instead.

**Outlier double-counting.** When combining box plot with strip/swarm, outliers appear both as box plot markers and as regular points. Either skip outlier markers on the box or filter them from the point overlay.

**QQ plot axis confusion.** Convention: theoretical quantiles on x-axis, sample quantiles on y-axis. Swapping them is a common mistake.

**Ridgeline occlusion.** Later (lower) rows occlude earlier ones. Render from bottom to top and use semi-transparent fills.

**Force simulation not converged.** Bee swarm points overlap if the simulation hasn't run enough ticks. Check `simulation.alpha()` — should be < 0.001.

**Overplotting in large datasets.** Beyond ~500 points, individual dots become useless. Switch to density representations or use canvas with alpha blending.

**Filtered KDE spikes outside chart bounds.** When recomputing KDE on a brushed subset with the same bandwidth, fewer points produce taller peaks — selecting 5 of 200 points can spike 10x higher. Scale density by `subset.length / fullGroup.length` so height represents proportion. See ghost/active pattern in `linked-views`.

## References

- Wilke, [Visualizing Distributions](https://clauswilke.com/dataviz/boxplots-violins.html) — when box plots lie and violins help
- Akin, [KDE Bandwidth Importance](https://aakinshin.net/posts/kde-bw/) — visual consequences of bandwidth choice
- Allen et al. 2019, [Raincloud plots](https://pmc.ncbi.nlm.nih.gov/articles/PMC6480976/) — the composite pattern formalized
- Hofmann, Wickham, Kafadar 2017, [Letter-Value Plots](https://vita.had.co.nz/papers/letter-value-plot.pdf) — box plots for large data
- Waskom 2023, [Defensive Raincloud Plots](https://arxiv.org/pdf/2303.17709) — KDE pitfalls in rainclouds
