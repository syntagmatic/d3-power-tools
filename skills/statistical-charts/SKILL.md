---
name: statistical-charts
description: "Build statistical distribution charts with D3.js. Use this skill when the user wants box plots, violin plots, ridgeline/joy plots, density plots, bee swarm plots, strip/jitter plots, or QQ plots. Covers kernel density estimation, quartile calculation, outlier detection, grouped/faceted statistical comparisons, and animated transitions between distribution views."
---

# Statistical Charts

Patterns for building distribution-visualization charts with D3.js: box plots, violin plots, ridgeline (joy) plots, density plots, bee swarm plots, strip/jitter plots, and QQ plots.

For axis patterns, see `axes-and-scales`. For animated transitions, see `animated-transitions`. For force-based layouts (bee swarm), see `force-simulation`. For color palettes, see `color-and-compositing`.

## Choosing a Distribution Chart

Pick based on what you need to show:

| Chart | Best When | Shows | Hides |
|-------|-----------|-------|-------|
| **Box plot** | Comparing medians and spread across 5+ groups | Median, quartiles, outliers | Shape (bimodal data looks same as unimodal) |
| **Violin plot** | Distribution shape matters (bimodal, skewed) | Full density shape, symmetry | Individual points, exact values |
| **Ridgeline** | Comparing many (6+) distributions at a glance | Trend across ordered groups, density overlap | Precise comparison (no shared x baseline within rows) |
| **Bee swarm** | Individual observations matter, n < 500/group | Every point, gaps, clusters | Performance degrades past ~500 pts/group |
| **Strip/jitter** | Quick overview, any n | Raw data distribution | Overplots badly past ~200 pts/group without opacity |
| **Density plot** | Comparing 2–4 overlapping distributions | Smooth shape, overlap regions | Individual values, small-sample artifacts |

**Combining charts** improves insight: violin + inner box shows shape and summary; bee swarm + median line shows individuals and center. Raincloud plots (half-violin + strip + box) give all three.

**When NOT to use:**
- **Box plots with n < 10** — quartiles are meaningless with tiny samples; show the raw points
- **Violin plots with n < 30** — KDE smoothing fabricates shape from too few points
- **Bee swarm with n > 500/group** — force simulation becomes slow; switch to jitter or violin
- **Ridgeline for unordered categories** — the vertical stacking implies order; use faceted violins instead

## Kernel Density Estimation (KDE)

KDE smooths raw data into a continuous density curve. Each data point contributes a kernel (usually Gaussian); the density at any point is the sum of all kernels.

```js
const gaussian = (x) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

function kde(kernel, bandwidth, data) {
  return (points) => points.map(x => [
    x,
    d3.mean(data, v => kernel((x - v) / bandwidth)) / bandwidth
  ]);
}

// Evaluate density at evenly-spaced points, extending 3 bandwidths past data extent
const ticks = d3.ticks(extent[0] - 3 * bandwidth, extent[1] + 3 * bandwidth, 200);
const density = kde(gaussian, bandwidth, values)(ticks);
```

### Bandwidth Selection

Bandwidth controls smoothness. Too small = noisy spikes. Too large = over-smoothed, hides features.

**Silverman's rule of thumb** — good default for roughly normal data:

```js
const std = d3.deviation(values);
const iqr = d3.quantile(sorted, 0.75) - d3.quantile(sorted, 0.25);
// Use smaller of std and IQR/1.34 to be robust to outliers
const bandwidth = 0.9 * Math.min(std, iqr / 1.34) * Math.pow(values.length, -0.2);
```

**Scott's rule** — simpler, assumes normality:
```js
const bandwidth = 1.06 * d3.deviation(values) * Math.pow(values.length, -0.2);
```

**Manual override guidance:**
- Bimodal data: use smaller bandwidth to reveal both peaks
- Very skewed data: consider log-transform before KDE
- Small samples (n < 30): Silverman produces spiky results, increase by 20-50%

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

- **1.5xIQR** (Tukey) — most common
- **Min/Max** — whiskers to data extremes, no outliers shown
- **Percentile (5th/95th or 2nd/98th)** — fixed percentile endpoints
- **1 SD / 2 SD** — whiskers at mean +/- standard deviations

Use `Float64Array.from(values).sort()` for large datasets to avoid GC pressure. `d3.quantile` requires sorted input — passing unsorted data gives wrong results with no error.

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

## QQ Plot: Normal Quantile Approximation

No external library needed — Beasley-Springer-Moro algorithm for the normal inverse CDF:

```js
function normalQuantile(p) {
  const a = [-3.969683028665376e1, 2.209460984245205e2,
    -2.759285104469687e2, 1.383577518672690e2,
    -3.066479806614716e1, 2.506628277459239e0];
  const b = [-5.447609879822406e1, 1.615858368580409e2,
    -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
  const c = [-7.784894002430293e-3, -3.223964580411365e-1,
    -2.400758277161838e0, -2.549732539343734e0,
    4.374664141464968e0, 2.938163982698783e0];
  const d = [7.784695709041462e-3, 3.224671290700398e-1,
    2.445134137142996e0, 3.754408661907416e0];
  const pLow = 0.02425, pHigh = 1 - pLow;
  let q;
  if (p < pLow) {
    q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
           ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  } else if (p <= pHigh) {
    q = p - 0.5; const r = q * q;
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
  } else {
    q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  }
}
```

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

Different density scales per group are acceptable (each violin normalized to same max width), but **document the choice**. Shared density scales enable comparison of group sizes. Consider scaling violin width by sample size: `violinScale.range([0, Math.sqrt(d.stats.n) * scaleFactor])`.

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

- [Kernel Density Estimation](https://en.wikipedia.org/wiki/Kernel_density_estimation) — theory and bandwidth selection
- [Silverman's Rule of Thumb](https://en.wikipedia.org/wiki/Kernel_density_estimation#A_rule-of-thumb_bandwidth_estimator)
- [Bee Swarm Plot](https://observablehq.com/@d3/beeswarm) — force-based bee swarm
- [Ridgeline Plot](https://observablehq.com/@d3/ridgeline-plot) — joy plot example
- [QQ Plot Theory](https://en.wikipedia.org/wiki/Q%E2%80%93Q_plot)
- [Tukey Box Plot](https://en.wikipedia.org/wiki/Box_plot) — whisker rules and outlier definitions
