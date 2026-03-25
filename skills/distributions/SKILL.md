---
name: distributions
description: "Build statistical distribution charts with D3.js. Use this skill when the user wants box plots, violin plots, ridgeline/joy plots, density plots, bee swarm plots, strip/jitter plots, or QQ plots. Covers kernel density estimation, quartile calculation, outlier detection, grouped/faceted statistical comparisons, and animated transitions between distribution views."
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
| **Violin plot** | Distribution shape matters (bimodal, skewed) | Full density shape, symmetry | Individual points; KDE fabricates shape from < 30 points |
| **Ridgeline** | Comparing many (6+) ordered distributions | Trend across groups, density overlap | Precise comparison (rows lack shared y baseline) |
| **Bee swarm** | Individual observations matter, n < 500/group | Every point, gaps, clusters | Nothing — but force simulation degrades past ~500 pts |
| **Strip/jitter** | Quick overview, any n | Raw data distribution | Overplots past ~200 pts/group without opacity |
| **Density plot** | Comparing 2–4 overlapping distributions | Smooth shape, overlap regions | Individual values; bandwidth choice shapes what you see |

**The box plot trap.** Two datasets — one normal, one bimodal with the same median and IQR — produce identical box plots. If you haven't already confirmed unimodality, a box plot will hide the most important feature of your data. Use a violin or overlay raw points to check before committing to box plots.

**Combining charts** improves insight: violin + inner box shows shape and summary; bee swarm + median line shows individuals and center. Raincloud plots (half-violin + strip + box) give all three.

**When NOT to use:**
- **Box plots with n < 10** — quartiles from tiny samples are noise; just show the raw points
- **Violin plots with n < 30** — KDE invents smooth curves from sparse data, showing peaks and valleys that don't exist
- **Density plots for small samples** — use a histogram instead; it shows what you actually observed rather than a smoothed fantasy
- **Bee swarm with n > 500/group** — force simulation becomes slow; switch to jitter or violin
- **Ridgeline for unordered categories** — the vertical stacking implies order; use faceted violins instead
- **Any smoothed chart when the data is discrete** — KDE smears probability across impossible values (e.g., showing density at 3.5 children); use a histogram or bar chart

## Kernel Density Estimation (KDE)

KDE smooths raw data into a continuous density curve. The bandwidth parameter is the single most consequential choice — it determines what the viewer sees as "signal" vs "noise."

```js
const gaussian = (x) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

function kde(kernel, bandwidth, data) {
  return (points) => points.map(x => [
    x,
    d3.mean(data, v => kernel((x - v) / bandwidth)) / bandwidth
  ]);
}

// Extend 3 bandwidths past data extent to avoid edge truncation
const ticks = d3.ticks(extent[0] - 3 * bandwidth, extent[1] + 3 * bandwidth, 200);
const density = kde(gaussian, bandwidth, values)(ticks);
```

### Bandwidth: A Judgment Call

Bandwidth is not a technical parameter — it's an editorial decision about what features to show the viewer.

**Too small:** every data point becomes its own peak, fabricating modes that don't exist. The viewer sees structure that is pure noise.

**Too large:** real features merge into a single smooth hump. A bimodal distribution becomes unimodal. The viewer misses the story.

**Silverman's rule** — good default for roughly normal data, robust to outliers:

```js
const std = d3.deviation(values);
const iqr = d3.quantile(sorted, 0.75) - d3.quantile(sorted, 0.25);
// Use smaller of std and IQR/1.34 to handle outlier-inflated std
const bandwidth = 0.9 * Math.min(std, iqr / 1.34) * Math.pow(values.length, -0.2);
```

**When to override the rule:**
- **Bimodal data:** Silverman assumes one peak, so it over-smooths and merges two modes into one. Halve the bandwidth and check visually.
- **Very skewed data:** log-transform before KDE, then back-transform the density curve.
- **Small samples (n < 30):** the rule produces tiny bandwidths that create spiky, misleading curves. Increase by 20-50%, or just use a histogram — it honestly shows what you observed.

## Descriptive Statistics Helper

Compute everything once per group — avoids repeated sorting and quantile calculation:

```js
function computeStats(values) {
  const sorted = Float64Array.from(values).sort();
  const q1 = d3.quantile(sorted, 0.25);
  const q3 = d3.quantile(sorted, 0.75);
  const iqr = q3 - q1;
  const lowerFence = q1 - 1.5 * iqr;
  const upperFence = q3 + 1.5 * iqr;
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

Notches indicate confidence interval around the median. If notches of two boxes don't overlap, their medians differ significantly (~95% confidence).

```js
// Notch extent: median +/- 1.57 * IQR / sqrt(n)
const notchHalf = 1.57 * stats.iqr / Math.sqrt(stats.n);
const notchLow = stats.median - notchHalf;
const notchHigh = stats.median + notchHalf;
const notchIndent = boxWidth * 0.15; // visual pinch at the median

// Draw as polygon instead of rect
const points = [
  [0, yScale(stats.q3)],
  [boxWidth, yScale(stats.q3)],
  [boxWidth, yScale(notchHigh)],
  [boxWidth - notchIndent, yScale(stats.median)],
  [boxWidth, yScale(notchLow)],
  [boxWidth, yScale(stats.q1)],
  [0, yScale(stats.q1)],
  [0, yScale(notchLow)],
  [notchIndent, yScale(stats.median)],
  [0, yScale(notchHigh)],
].map(p => p.join(",")).join(" ");

boxes.append("polygon").attr("points", points);
```

## Whisker Variants

Pick whiskers based on what question the viewer is asking:

- **1.5xIQR (Tukey)** — default choice. Points beyond are flagged as outliers, which is what most audiences expect.
- **Min/Max** — use when there are no true outliers, or when the audience cares about the full range (e.g., manufacturing tolerances). Hides nothing but also flags nothing.
- **Percentile (5th/95th)** — use when outlier counts are unreliable (small n) or when you want a consistent definition across groups with different distributions.
- **1 SD / 2 SD** — use only when the audience thinks in standard deviations (scientific, engineering). Misleading for skewed data since SD is symmetric around the mean.

## Ridgeline (Joy) Plots

### Overlap Tuning

- `overlap = 0` — no overlap, standard small multiples
- `overlap = 0.3-0.5` — mild overlap, most readable
- `overlap = 0.7-1.0` — dramatic overlap, Joy Division effect

Render from bottom to top (reverse data order) so lower rows appear in front.

```js
const overlap = 0.7;
const ridgeHeight = yBand.step() * (1 + overlap);
const densityYScale = d3.scaleLinear().domain([0, maxDensity]).range([0, ridgeHeight]);

const area = d3.area()
  .x(d => xScale(d[0]))
  .y0(0)
  .y1(d => -densityYScale(d[1]))
  .curve(d3.curveBasis);

ridges.attr("transform", d => `translate(0, ${yBand(d.key) + yBand.bandwidth()})`);
```

## Bee Swarm: Dodge Algorithm

Faster alternative to force simulation. Place points in sorted order, nudging to avoid overlap:

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

For force-based bee swarm, pre-compute: `simulation.stop(); for (let i = 0; i < 120; i++) simulation.tick();`

## Seeded Jitter

Use `d3.randomLcg` for reproducible jitter (strip plots won't shift on re-render):

```js
const random = d3.randomLcg(42);
const jitter = () => (random() - 0.5) * groupScale.bandwidth() * 0.6;
```

### Sinusoidal jitter — uniform spread without randomness

```js
sortedData.forEach((d, i, arr) => {
  d.jitterX = Math.sin(i * Math.PI / arr.length) * (bandwidth * 0.3);
});
```

## Violin + Strip: Constrained Jitter

Constrain jitter width to the violin width at each y-position:

```js
const jitterScale = d3.scaleLinear().domain([0, maxDensity]).range([0, groupScale.bandwidth() / 2]);
circles.attr("cx", d => {
  const densityAtValue = interpolateDensity(d.value, d.group);
  return (Math.random() - 0.5) * 2 * jitterScale(densityAtValue);
});
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
// Right half: group B density
violin.append("path")
  .attr("d", d3.area()
    .x0(0).x1(d => violinScale(d[1]))
    .y(d => yScale(d[0]))
    .curve(d3.curveCatmullRom)(densityB))
  .attr("fill", colorB);
```

## QQ Plot

QQ plots answer "does my data follow this distribution?" — points on the diagonal mean yes, curvature means no. Heavy tails curve up at right and down at left; skew curves one way throughout.

Use the Beasley-Springer-Moro rational approximation for `normalQuantile(p)` (the inverse normal CDF) — it's a ~25-line pure math function with no D3 dependency. See any standard implementation.

Plotting position: `p = (i + 0.5) / n` (Hazen formula). Standardize data before comparing: `(v - mean) / sd`.

### QQ Confidence Bands

95% pointwise envelope under the null (data is normal):

```js
// se of order statistic i: sqrt(p(1-p) / n) / f(z_p)
// f = standard normal density at the theoretical quantile
const confBands = theoreticalQuantiles.map((z, i) => {
  const p = (i + 0.5) / n;
  const f = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
  const se = Math.sqrt(p * (1 - p) / n) / f;
  return { z, lower: z - 1.96 * se, upper: z + 1.96 * se };
});
```

## Multiple Overlapping Densities

Draw widest distribution first, or use `mix-blend-mode: multiply` for better overlap visibility:

```js
svg.selectAll(".density-area")
  .data(densities)
  .join("path")
    .attr("d", d => area(d.density))
    .attr("fill", d => colorScale(d.key))
    .attr("fill-opacity", 0.3)
    .attr("stroke", d => colorScale(d.key))
    .attr("stroke-width", 1.5);
```

## Transitions Between Chart Types

Pre-compute positions for each view, then interpolate:

```js
data.forEach(d => {
  d.boxX = groupScale(d.group) + groupScale.bandwidth() / 2;
  d.boxY = yScale(d.value);
  d.swarmX = d.simulatedX;
  d.swarmY = d.simulatedY;
  d.stripX = groupScale(d.group) + jitter();
  d.stripY = yScale(d.value);
});
// Transition by interpolating cx/cy between view positions
```

## Density Scale Normalization

This is a hidden editorial choice that changes what the viewer concludes:

- **Per-group normalization** (each violin same max width): lets the viewer compare shape, but a group with n=10 looks as confident as n=10,000. Use when shape comparison is the point and sample sizes are similar.
- **Shared density scale**: wider violins mean more data. Use when relative group sizes matter.
- **Width scaled by sqrt(n)**: `violinScale.range([0, Math.sqrt(d.stats.n) * scaleFactor])` — a compromise that encodes sample size without letting large groups dominate. Good default when group sizes vary by more than 3x.

## Common Pitfalls

**Sorted input for d3.quantile.** `d3.quantile` requires sorted input. Unsorted data gives wrong quartiles with no error. Always sort first.

**KDE bandwidth too small.** With small samples (n < 30), Silverman's rule can produce very small bandwidths that create spiky, misleading density curves. Set a minimum bandwidth or increase by 20-50%.

**Violin width normalization.** If violins are normalized to the same max width, groups with very different sample sizes look identical in spread.

**Jitter hides density.** Random jitter in strip plots obscures where points cluster. When density matters, use bee swarm or violin instead.

**Outlier double-counting.** When combining box plot with strip/swarm, outliers appear both as box plot markers and as regular points. Either skip outlier markers on the box or filter them from the point overlay.

**QQ plot axis confusion.** Convention: theoretical quantiles on x-axis, sample quantiles on y-axis. Swapping them is a common mistake.

**Ridgeline occlusion.** Later (lower) rows occlude earlier ones. Render from bottom to top and use semi-transparent fills.

**Force simulation not converged.** Bee swarm points overlap if the simulation hasn't run enough ticks. Check `simulation.alpha()` — should be < 0.001. Increase tick count or reduce collision radius.

**Overplotting in large datasets.** Beyond ~500 points, individual dots become useless. Switch to density representations (violin, density plot) or use canvas with alpha blending.

## References

- Wilke, [Visualizing Distributions](https://clauswilke.com/dataviz/boxplots-violins.html) — when box plots lie and violins help
- Akin, [KDE Bandwidth Importance](https://aakinshin.net/posts/kde-bw/) — visual consequences of bandwidth choice
