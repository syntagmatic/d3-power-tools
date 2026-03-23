---
name: statistical-charts
description: "Build statistical distribution charts with D3.js. Use this skill when the user wants box plots, violin plots, ridgeline/joy plots, density plots, bee swarm plots, strip/jitter plots, or QQ plots. Covers kernel density estimation, quartile calculation, outlier detection, grouped/faceted statistical comparisons, and animated transitions between distribution views."
---

# Statistical Charts

Patterns for building distribution-visualization charts with D3.js. Covers box plots, violin plots, ridgeline (joy) plots, density plots, bee swarm plots, strip/jitter plots, and QQ plots. These charts answer questions about spread, skew, modality, and outliers in continuous data.

For axis patterns and scale selection, see `axes-and-scales`. For animated transitions between chart types, see `animated-transitions`. For force-based layouts (bee swarm), see `force-simulation`. For color palettes and accessibility, see `color-and-compositing`.

## Core Statistical Functions

Most distribution charts share the same underlying calculations. Compute these once, then feed them into whichever visual encoding you need.

### Quartiles and IQR

```js
const sorted = Float64Array.from(values).sort();
const q1 = d3.quantile(sorted, 0.25);
const median = d3.quantile(sorted, 0.5);
const q3 = d3.quantile(sorted, 0.75);
const iqr = q3 - q1;
```

`d3.quantile` uses linear interpolation (R-7 method). Input must be sorted. Use `Float64Array` for large datasets to avoid GC pressure.

### Whiskers (Tukey Fences)

The standard 1.5xIQR rule: whiskers extend to the most extreme data point within 1.5xIQR of the box edges.

```js
const lowerFence = q1 - 1.5 * iqr;
const upperFence = q3 + 1.5 * iqr;
const whiskerLow = d3.min(values.filter(v => v >= lowerFence));
const whiskerHigh = d3.max(values.filter(v => v <= upperFence));
const outliers = values.filter(v => v < lowerFence || v > upperFence);
```

Whisker variants:
- **1.5xIQR** (Tukey) — most common, shown above
- **Min/Max** — whiskers to data extremes, no outliers shown
- **Percentile (5th/95th or 2nd/98th)** — fixed percentile endpoints
- **1 SD / 2 SD** — whiskers at mean +/- standard deviations

### Kernel Density Estimation (KDE)

KDE smooths raw data into a continuous density curve. Each data point contributes a kernel (usually Gaussian); the density at any point is the sum of all kernels.

```js
// Gaussian kernel
const gaussian = (x) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

// KDE function: returns array of [x, density] pairs
function kde(kernel, bandwidth, data) {
  return (points) => points.map(x => [
    x,
    d3.mean(data, v => kernel((x - v) / bandwidth)) / bandwidth
  ]);
}

// Usage: evaluate density at evenly-spaced points across the domain
const extent = d3.extent(values);
const ticks = d3.ticks(extent[0] - 3 * bandwidth, extent[1] + 3 * bandwidth, 200);
const density = kde(gaussian, bandwidth, values)(ticks);
```

### Bandwidth Selection

Bandwidth controls smoothness. Too small = noisy spikes. Too large = over-smoothed, hides features.

**Silverman's rule of thumb** — good default for roughly normal data:

```js
const n = values.length;
const std = d3.deviation(values);
const iqr = d3.quantile(sorted, 0.75) - d3.quantile(sorted, 0.25);
// Use the smaller of std and IQR/1.34 to be robust to outliers
const bandwidth = 0.9 * Math.min(std, iqr / 1.34) * Math.pow(n, -0.2);
```

**Scott's rule** — simpler, assumes normality:
```js
const bandwidth = 1.06 * d3.deviation(values) * Math.pow(values.length, -0.2);
```

**Manual override** — when you know the data:
- Bimodal data: use smaller bandwidth to reveal both peaks
- Very skewed data: consider log-transform before KDE

### Descriptive Statistics Helper

Compute everything once per group:

```js
function computeStats(values) {
  const sorted = Float64Array.from(values).sort();
  const q1 = d3.quantile(sorted, 0.25);
  const q3 = d3.quantile(sorted, 0.75);
  const iqr = q3 - q1;
  const lowerFence = q1 - 1.5 * iqr;
  const upperFence = q3 + 1.5 * iqr;
  return {
    min: sorted[0],
    max: sorted[sorted.length - 1],
    q1,
    median: d3.quantile(sorted, 0.5),
    q3,
    iqr,
    mean: d3.mean(sorted),
    std: d3.deviation(sorted),
    whiskerLow: d3.min(sorted.filter(v => v >= lowerFence)),
    whiskerHigh: d3.max(sorted.filter(v => v <= upperFence)),
    outliers: sorted.filter(v => v < lowerFence || v > upperFence),
    n: sorted.length,
  };
}
```

## Box Plots

### Basic Vertical Box Plot

```js
const groupScale = d3.scaleBand()
  .domain(groups.map(d => d.key))
  .range([0, width])
  .padding(0.3);

const yScale = d3.scaleLinear()
  .domain([globalMin, globalMax]).nice()
  .range([height, 0]);

const boxWidth = groupScale.bandwidth();

// One group per box
const boxes = svg.selectAll(".box")
  .data(groups)
  .join("g")
    .attr("class", "box")
    .attr("transform", d => `translate(${groupScale(d.key)}, 0)`);

// Box (IQR)
boxes.append("rect")
  .attr("x", 0)
  .attr("y", d => yScale(d.stats.q3))
  .attr("width", boxWidth)
  .attr("height", d => yScale(d.stats.q1) - yScale(d.stats.q3))
  .attr("fill", d => colorScale(d.key))
  .attr("stroke", "currentColor");

// Median line
boxes.append("line")
  .attr("x1", 0).attr("x2", boxWidth)
  .attr("y1", d => yScale(d.stats.median))
  .attr("y2", d => yScale(d.stats.median))
  .attr("stroke", "currentColor")
  .attr("stroke-width", 2);

// Whiskers — vertical lines from box edges to fence values
boxes.append("line")
  .attr("x1", boxWidth / 2).attr("x2", boxWidth / 2)
  .attr("y1", d => yScale(d.stats.whiskerLow))
  .attr("y2", d => yScale(d.stats.q1))
  .attr("stroke", "currentColor");

boxes.append("line")
  .attr("x1", boxWidth / 2).attr("x2", boxWidth / 2)
  .attr("y1", d => yScale(d.stats.q3))
  .attr("y2", d => yScale(d.stats.whiskerHigh))
  .attr("stroke", "currentColor");

// Whisker caps
const capWidth = boxWidth * 0.5;
boxes.append("line")
  .attr("x1", (boxWidth - capWidth) / 2).attr("x2", (boxWidth + capWidth) / 2)
  .attr("y1", d => yScale(d.stats.whiskerLow))
  .attr("y2", d => yScale(d.stats.whiskerLow))
  .attr("stroke", "currentColor");

boxes.append("line")
  .attr("x1", (boxWidth - capWidth) / 2).attr("x2", (boxWidth + capWidth) / 2)
  .attr("y1", d => yScale(d.stats.whiskerHigh))
  .attr("y2", d => yScale(d.stats.whiskerHigh))
  .attr("stroke", "currentColor");

// Outliers
boxes.selectAll(".outlier")
  .data(d => d.stats.outliers.map(v => ({ value: v, key: d.key })))
  .join("circle")
    .attr("class", "outlier")
    .attr("cx", boxWidth / 2)
    .attr("cy", d => yScale(d.value))
    .attr("r", 3)
    .attr("fill", "none")
    .attr("stroke", d => colorScale(d.key));
```

### Notched Box Plot

Notches indicate confidence interval around the median. If notches of two boxes don't overlap, their medians differ significantly (roughly 95% confidence).

```js
// Notch extent: median +/- 1.57 * IQR / sqrt(n)
const notchHalf = 1.57 * stats.iqr / Math.sqrt(stats.n);
const notchLow = stats.median - notchHalf;
const notchHigh = stats.median + notchHalf;
const notchIndent = boxWidth * 0.15; // visual pinch at the median

// Draw as a polygon instead of rect
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

boxes.append("polygon")
  .attr("points", points)
  .attr("fill", d => colorScale(d.key))
  .attr("stroke", "currentColor");
```

### Horizontal Box Plot

Swap x/y scales and draw rects/lines along the horizontal axis:

```js
const xScale = d3.scaleLinear().domain([globalMin, globalMax]).nice().range([0, width]);
const groupScale = d3.scaleBand().domain(groups.map(d => d.key)).range([0, height]).padding(0.3);
const boxHeight = groupScale.bandwidth();

// Box
boxes.append("rect")
  .attr("x", d => xScale(d.stats.q1))
  .attr("y", 0)
  .attr("width", d => xScale(d.stats.q3) - xScale(d.stats.q1))
  .attr("height", boxHeight);

// Median — vertical line
boxes.append("line")
  .attr("x1", d => xScale(d.stats.median)).attr("x2", d => xScale(d.stats.median))
  .attr("y1", 0).attr("y2", boxHeight)
  .attr("stroke", "currentColor").attr("stroke-width", 2);
```

### Grouped / Side-by-Side Box Plots

Use a nested band scale for sub-groups:

```js
const x0 = d3.scaleBand().domain(categories).range([0, width]).padding(0.2);
const x1 = d3.scaleBand().domain(subgroups).range([0, x0.bandwidth()]).padding(0.05);

// Position each box at x0(category) + x1(subgroup)
boxes.attr("transform", d => `translate(${x0(d.category) + x1(d.subgroup)}, 0)`);
```

## Violin Plots

A violin is a mirrored density plot. The KDE curve is reflected around a central axis, showing shape and density of the distribution.

### Basic Violin

```js
const areaGenerator = d3.area()
  .x0(d => -violinScale(d[1]))  // left half (mirrored)
  .x1(d => violinScale(d[1]))   // right half
  .y(d => yScale(d[0]))
  .curve(d3.curveCatmullRom);

// violinScale maps density values to half-width
const maxDensity = d3.max(allDensities, group => d3.max(group, d => d[1]));
const violinScale = d3.scaleLinear()
  .domain([0, maxDensity])
  .range([0, groupScale.bandwidth() / 2]);

const violins = svg.selectAll(".violin")
  .data(groups)
  .join("g")
    .attr("class", "violin")
    .attr("transform", d => `translate(${groupScale(d.key) + groupScale.bandwidth() / 2}, 0)`);

violins.append("path")
  .attr("d", d => areaGenerator(d.density))
  .attr("fill", d => colorScale(d.key))
  .attr("fill-opacity", 0.7)
  .attr("stroke", d => colorScale(d.key));
```

### Hybrid Violin + Box

Overlay a thin box plot inside the violin:

```js
const innerBoxWidth = 6;

// Mini box inside violin
violins.append("rect")
  .attr("x", -innerBoxWidth / 2)
  .attr("y", d => yScale(d.stats.q3))
  .attr("width", innerBoxWidth)
  .attr("height", d => yScale(d.stats.q1) - yScale(d.stats.q3))
  .attr("fill", "#333");

// Median dot
violins.append("circle")
  .attr("cx", 0)
  .attr("cy", d => yScale(d.stats.median))
  .attr("r", 3)
  .attr("fill", "white");
```

### Grouped Violins

Same nested-band approach as grouped box plots. Place each violin at `x0(category) + x1(subgroup) + x1.bandwidth()/2`.

### Half Violins (Split Violin)

Show two subgroups as left/right halves of the same violin:

```js
// Left half: group A density, mirrored left only
violin.append("path")
  .attr("d", d3.area()
    .x0(0)
    .x1(d => -violinScale(d[1]))
    .y(d => yScale(d[0]))
    .curve(d3.curveCatmullRom)(densityA))
  .attr("fill", colorA);

// Right half: group B density, right only
violin.append("path")
  .attr("d", d3.area()
    .x0(0)
    .x1(d => violinScale(d[1]))
    .y(d => yScale(d[0]))
    .curve(d3.curveCatmullRom)(densityB))
  .attr("fill", colorB);
```

## Ridgeline (Joy) Plots

Overlapping density curves stacked vertically — named after Joy Division's "Unknown Pleasures" album cover. Excellent for comparing distributions across many categories.

### Basic Ridgeline

```js
const yBand = d3.scaleBand()
  .domain(groups.map(d => d.key))
  .range([0, height])
  .padding(0.1);

const xScale = d3.scaleLinear()
  .domain(d3.extent(allValues))
  .range([0, width]);

// Each row gets its own y-scale for the density height
const overlap = 0.7; // 0 = no overlap, 1 = rows fully overlap
const ridgeHeight = yBand.step() * (1 + overlap);

const densityYScale = d3.scaleLinear()
  .domain([0, maxDensity])
  .range([0, ridgeHeight]);

const area = d3.area()
  .x(d => xScale(d[0]))
  .y0(0)
  .y1(d => -densityYScale(d[1]))
  .curve(d3.curveBasis);

const line = d3.line()
  .x(d => xScale(d[0]))
  .y(d => -densityYScale(d[1]))
  .curve(d3.curveBasis);

const ridges = svg.selectAll(".ridge")
  .data(groups)
  .join("g")
    .attr("class", "ridge")
    .attr("transform", d => `translate(0, ${yBand(d.key) + yBand.bandwidth()})`);

ridges.append("path")
  .attr("d", d => area(d.density))
  .attr("fill", d => colorScale(d.key))
  .attr("fill-opacity", 0.6);

ridges.append("path")
  .attr("d", d => line(d.density))
  .attr("fill", "none")
  .attr("stroke", d => colorScale(d.key))
  .attr("stroke-width", 1.5);
```

### Gradient Fills

Use `linearGradient` per ridge to encode a second variable (e.g., mean value) along the x-axis:

```js
const gradient = defs.selectAll("linearGradient")
  .data(groups)
  .join("linearGradient")
    .attr("id", d => `grad-${d.key}`)
    .attr("x1", "0%").attr("x2", "100%");

gradient.append("stop").attr("offset", "0%").attr("stop-color", d => coolColor);
gradient.append("stop").attr("offset", "100%").attr("stop-color", d => warmColor);

ridges.select("path.area").attr("fill", d => `url(#grad-${d.key})`);
```

### Overlap Tuning

- `overlap = 0` — no overlap, standard small multiples
- `overlap = 0.3–0.5` — mild overlap, most readable
- `overlap = 0.7–1.0` — dramatic overlap, Joy Division effect

Render from bottom to top (reverse data order) so lower rows appear in front.

## Bee Swarm Plots

Individual points jittered to avoid overlap, preserving exact values on one axis. Uses force simulation for positioning.

### Force-Based Bee Swarm

```js
const xScale = d3.scaleLinear()
  .domain(d3.extent(values)).nice()
  .range([0, width]);

const simulation = d3.forceSimulation(data)
  .force("x", d3.forceX(d => xScale(d.value)).strength(1))
  .force("y", d3.forceY(height / 2).strength(0.05))
  .force("collide", d3.forceCollide(radius + 0.5).iterations(3))
  .stop();

// Pre-compute positions — ~120 ticks is usually enough
for (let i = 0; i < 120; i++) simulation.tick();

svg.selectAll("circle")
  .data(data)
  .join("circle")
    .attr("cx", d => d.x)
    .attr("cy", d => d.y)
    .attr("r", radius)
    .attr("fill", d => colorScale(d.group));
```

### Grouped Bee Swarm (Vertical)

For grouped data, use `forceY` to pull points toward group centers:

```js
const groupScale = d3.scaleBand()
  .domain(groupNames)
  .range([0, width])
  .padding(0.1);

const simulation = d3.forceSimulation(data)
  .force("y", d3.forceY(d => yScale(d.value)).strength(1))
  .force("x", d3.forceX(d => groupScale(d.group) + groupScale.bandwidth() / 2).strength(0.5))
  .force("collide", d3.forceCollide(radius + 0.5).iterations(3))
  .stop();

for (let i = 0; i < 120; i++) simulation.tick();
```

### Dodge Algorithm (Non-Force)

Faster alternative to force simulation. Place points in order, nudging horizontally to avoid overlap:

```js
// Sort by value, then stack horizontally at each position
function dodgeBeeswarm(data, xScale, radius) {
  const sorted = [...data].sort((a, b) => a.value - b.value);
  const placed = [];
  for (const d of sorted) {
    const targetX = xScale(d.value);
    let offsetY = 0;
    let direction = 1;
    while (placed.some(p =>
      Math.hypot(targetX - p.x, offsetY - p.y) < radius * 2
    )) {
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

### Combined Box + Bee Swarm

Overlay individual points on top of a box plot. Use reduced opacity and smaller radius:

```js
// Draw box plot first (see Box Plots section)
// Then overlay points
boxes.selectAll(".point")
  .data(d => d.values.map(v => ({ value: v, key: d.key })))
  .join("circle")
    .attr("cx", () => boxWidth / 2 + (Math.random() - 0.5) * boxWidth * 0.6)
    .attr("cy", d => yScale(d.value))
    .attr("r", 2)
    .attr("fill", d => colorScale(d.key))
    .attr("fill-opacity", 0.4);
```

## Strip / Jitter Plots

Simpler than bee swarm: randomly offset points along the non-data axis. Fast and works well for smaller datasets.

### Random Jitter

```js
svg.selectAll("circle")
  .data(data)
  .join("circle")
    .attr("cx", d => groupScale(d.group) + groupScale.bandwidth() / 2
      + (Math.random() - 0.5) * groupScale.bandwidth() * 0.6)
    .attr("cy", d => yScale(d.value))
    .attr("r", 3)
    .attr("fill", d => colorScale(d.group))
    .attr("fill-opacity", 0.5);
```

### Seeded Random for Consistency

Use `d3.randomLcg` for reproducible jitter:

```js
const random = d3.randomLcg(42);
const jitter = () => (random() - 0.5) * groupScale.bandwidth() * 0.6;
```

### Sinusoidal Jitter (Uniform Spread)

Instead of random, space points evenly across the strip width:

```js
groupData.sort((a, b) => a.value - b.value).forEach((d, i, arr) => {
  d.jitterX = Math.sin(i * Math.PI / arr.length) * (groupScale.bandwidth() * 0.3);
});
```

### Combined Violin + Strip

Draw the violin shape first, then overlay jittered points inside the violin outline. Constrain jitter width to the violin width at each y-position:

```js
// For each point, find density at its value, scale jitter to violin width
const jitterScale = d3.scaleLinear().domain([0, maxDensity]).range([0, groupScale.bandwidth() / 2]);
circles.attr("cx", d => {
  const densityAtValue = interpolateDensity(d.value, d.group);
  const maxJitter = jitterScale(densityAtValue);
  return (Math.random() - 0.5) * 2 * maxJitter;
});
```

## Density Plots

### 1D Density (Area)

```js
const density = kde(gaussian, bandwidth, values)(ticks);

const area = d3.area()
  .x(d => xScale(d[0]))
  .y0(height)
  .y1(d => yScale(d[1]))
  .curve(d3.curveBasis);

svg.append("path")
  .datum(density)
  .attr("d", area)
  .attr("fill", "steelblue")
  .attr("fill-opacity", 0.5)
  .attr("stroke", "steelblue")
  .attr("stroke-width", 1.5);
```

### Multiple Overlapping Densities

```js
const densities = groups.map(g => ({
  key: g.key,
  density: kde(gaussian, bandwidth, g.values)(ticks),
}));

svg.selectAll(".density-area")
  .data(densities)
  .join("path")
    .attr("d", d => area(d.density))
    .attr("fill", d => colorScale(d.key))
    .attr("fill-opacity", 0.3)
    .attr("stroke", d => colorScale(d.key))
    .attr("stroke-width", 1.5);
```

Order matters: draw the widest distribution first, or use `mix-blend-mode: multiply` for better overlap visibility.

### Bandwidth Control UI

```js
const slider = d3.select("#bandwidth-slider");
slider.on("input", function() {
  const bw = +this.value;
  const newDensity = kde(gaussian, bw, values)(ticks);
  densityPath.datum(newDensity)
    .transition().duration(300)
    .attr("d", area);
});
```

## QQ Plots

Quantile-quantile plots compare a data distribution against a theoretical distribution (usually normal). Points on the diagonal = data matches the theory.

### Normal QQ Plot

```js
// Compute theoretical quantiles from standard normal
const sorted = [...values].sort(d3.ascending);
const n = sorted.length;
const theoreticalQuantiles = sorted.map((_, i) => {
  const p = (i + 0.5) / n; // plotting position (Hazen)
  return jstat.normal.inv(p, 0, 1); // or use a manual approximation
});

// Without jstat — rational approximation of the normal inverse CDF
function normalQuantile(p) {
  // Beasley-Springer-Moro algorithm
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
    q = p - 0.5;
    const r = q * q;
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
  } else {
    q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  }
}

// Standardize data to compare against standard normal
const mean = d3.mean(sorted);
const sd = d3.deviation(sorted);
const standardized = sorted.map(v => (v - mean) / sd);

// Plot
const qqData = theoreticalQuantiles.map((tq, i) => ({
  theoretical: tq,
  sample: standardized[i],
}));

svg.selectAll("circle")
  .data(qqData)
  .join("circle")
    .attr("cx", d => xScale(d.theoretical))
    .attr("cy", d => yScale(d.sample))
    .attr("r", 3)
    .attr("fill", "steelblue")
    .attr("fill-opacity", 0.6);

// Reference line (y = x for standardized data)
const lineExtent = d3.extent(theoreticalQuantiles);
svg.append("line")
  .attr("x1", xScale(lineExtent[0])).attr("y1", yScale(lineExtent[0]))
  .attr("x2", xScale(lineExtent[1])).attr("y2", yScale(lineExtent[1]))
  .attr("stroke", "red")
  .attr("stroke-dasharray", "4,4");
```

### Confidence Bands

95% pointwise confidence envelope under the null (data is normal):

```js
// Approximate confidence band: +/- 1.96 * se
// se of order statistic i: sqrt(p(1-p) / n) / f(z_p)
// f = standard normal density, z_p = normal quantile at p
const confBands = theoreticalQuantiles.map((z, i) => {
  const p = (i + 0.5) / n;
  const f = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI); // normal density
  const se = Math.sqrt(p * (1 - p) / n) / f;
  return { z, lower: z - 1.96 * se, upper: z + 1.96 * se };
});

const bandArea = d3.area()
  .x(d => xScale(d.z))
  .y0(d => yScale(d.lower))
  .y1(d => yScale(d.upper))
  .curve(d3.curveLinear);

svg.append("path")
  .datum(confBands)
  .attr("d", bandArea)
  .attr("fill", "red")
  .attr("fill-opacity", 0.1);
```

## Common Patterns

### Shared Scales for Comparison

When comparing distributions side by side, always share the value scale:

```js
const globalExtent = d3.extent(allData, d => d.value);
const yScale = d3.scaleLinear().domain(globalExtent).nice().range([height, 0]);
```

Different density scales per group are acceptable (each violin normalized to same max width), but document the choice. Shared density scales enable comparison of group sizes.

### Color Encoding by Group

Use `d3.scaleOrdinal` with a colorblind-safe palette:

```js
const colorScale = d3.scaleOrdinal()
  .domain(groupNames)
  .range(d3.schemeTableau10); // or Paul Tol qualitative
```

See `color-and-compositing` for palette selection guidance.

### Transitions Between Chart Types

Morph between box plot, violin, and bee swarm using D3 transitions. Key: map elements between views.

```js
// Box -> Violin: transition rect to path via intermediate representation
// Simple approach: fade out old, fade in new
function transitionTo(chartType) {
  svg.selectAll(".box-elements")
    .transition().duration(500)
    .attr("opacity", chartType === "box" ? 1 : 0);

  svg.selectAll(".violin-elements")
    .transition().duration(500)
    .attr("opacity", chartType === "violin" ? 1 : 0);

  // For bee swarm: transition circle positions
  svg.selectAll(".point")
    .transition().duration(800)
    .attr("cx", d => chartType === "swarm" ? d.swarmX : groupCenter)
    .attr("cy", d => chartType === "swarm" ? d.swarmY : yScale(d.value))
    .attr("opacity", chartType === "swarm" ? 0.7 : 0);
}
```

Better approach for points: pre-compute positions for each view, then interpolate:

```js
data.forEach(d => {
  d.boxX = groupScale(d.group) + groupScale.bandwidth() / 2;
  d.boxY = yScale(d.value);
  d.swarmX = d.simulatedX;
  d.swarmY = d.simulatedY;
  d.stripX = groupScale(d.group) + jitter();
  d.stripY = yScale(d.value);
});
```

### Responsive Sizing

```js
const container = d3.select("#chart");
const ro = new ResizeObserver(([entry]) => {
  const { width: w, height: h } = entry.contentRect;
  // Rebuild scales and redraw
  updateChart(w, h);
});
ro.observe(container.node());
```

### Tooltip Pattern

```js
const tooltip = d3.select("body").append("div")
  .attr("class", "tooltip")
  .style("position", "absolute")
  .style("pointer-events", "none")
  .style("opacity", 0);

selection.on("pointerenter", (event, d) => {
  tooltip.style("opacity", 1)
    .html(`<strong>${d.group}</strong><br>
           Median: ${d.stats.median.toFixed(1)}<br>
           IQR: ${d.stats.q1.toFixed(1)}–${d.stats.q3.toFixed(1)}<br>
           n = ${d.stats.n}`)
    .style("left", (event.pageX + 10) + "px")
    .style("top", (event.pageY - 10) + "px");
})
.on("pointerleave", () => tooltip.style("opacity", 0));
```

## Common Pitfalls

**Sorted input for d3.quantile.** `d3.quantile` requires sorted input. If you pass unsorted data, you get wrong quartiles with no error. Always sort first.

**KDE bandwidth too small.** With small samples (n < 30), Silverman's rule can produce very small bandwidths that create spiky, misleading density curves. Set a minimum bandwidth or increase it by 20-50%.

**Violin width normalization.** If violins are normalized to the same max width, groups with very different sample sizes look identical in spread. Consider scaling violin width by sample size: `violinScale.range([0, Math.sqrt(d.stats.n) * scaleFactor])`.

**Jitter hides density.** Random jitter in strip plots obscures where points cluster. When density matters, use bee swarm or violin instead.

**Outlier double-counting.** When combining box plot with strip/swarm, outliers appear both as box plot markers and as regular points. Either skip outlier markers on the box or filter them from the point overlay.

**QQ plot axis confusion.** Convention: theoretical quantiles on x-axis, sample quantiles on y-axis. Swapping them is a common mistake that makes interpretation harder.

**Ridgeline occlusion.** Later (lower) rows occlude earlier ones. Render from bottom to top and use semi-transparent fills or white backgrounds for each ridge.

**Force simulation not converged.** Bee swarm points overlap if the simulation hasn't run enough ticks. Check with `simulation.alpha()` — should be < 0.001. Increase tick count or reduce collision radius.

**Transitions with changing data length.** When switching chart types, the number of SVG elements may change (e.g., outlier circles vs density path). Use proper enter/update/exit joins, not just attribute transitions.

**Overplotting in large datasets.** Beyond ~500 points, individual dots become useless. Switch to density representations (violin, density plot) or use canvas with alpha blending. See `canvas-rendering`.

## References

- [D3 Statistics Functions](https://d3js.org/d3-array/summarize) — d3.quantile, d3.mean, d3.deviation, d3.variance
- [Box Plot](https://observablehq.com/@d3/box-plot) — canonical D3 box plot example
- [Violin Plot](https://observablehq.com/@d3/violin-plot) — D3 violin plot
- [Kernel Density Estimation](https://en.wikipedia.org/wiki/Kernel_density_estimation) — theory and bandwidth selection
- [Silverman's Rule of Thumb](https://en.wikipedia.org/wiki/Kernel_density_estimation#A_rule-of-thumb_bandwidth_estimator)
- [Bee Swarm Plot](https://observablehq.com/@d3/beeswarm) — force-based bee swarm
- [Ridgeline Plot](https://observablehq.com/@d3/ridgeline-plot) — joy plot example
- [QQ Plot Theory](https://en.wikipedia.org/wiki/Q%E2%80%93Q_plot)
- [Tukey Box Plot](https://en.wikipedia.org/wiki/Box_plot) — whisker rules and outlier definitions
