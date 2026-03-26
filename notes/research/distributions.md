# Distribution Visualization Research

Research notes for expanding the distributions skill beyond its current coverage.

## Current Coverage

The `skills/distributions/SKILL.md` covers:

- **Histogram** -- bin-based counts
- **Box plot** -- median, quartiles, whiskers, outliers (including notched variant, whisker variants)
- **Violin plot** -- KDE-based density shape (including half/split violin)
- **Ridgeline / Joy plot** -- stacked density curves with overlap tuning
- **Bee swarm** -- dodge algorithm, force-based placement
- **Strip / Jitter** -- seeded jitter, sinusoidal jitter, constrained jitter within violins
- **Density plot** -- overlapping KDE curves with blend modes
- **QQ plot** -- normal comparison with confidence bands
- **KDE** -- Silverman bandwidth, Gaussian kernel, edge truncation fix

Mentioned but not developed: raincloud plots (one sentence noting they exist as "half-violin + strip + box"). Not mentioned at all: letter-value plots, HOPs, 2D density (hexbin/contour), gradient density strips.

---

## Raincloud Plots

**Source:** Allen et al. 2019, "Raincloud plots: a multi-platform tool for robust data visualization" (Wellcome Open Research, 4:63). [PMC6480976](https://pmc.ncbi.nlm.nih.gov/articles/PMC6480976/)

### What it is

Three components stacked asymmetrically on one side of a shared axis:

1. **Half-violin (the "cloud")** -- un-mirrored density curve, showing distribution shape
2. **Jittered strip (the "rain")** -- every individual observation
3. **Box plot (the "umbrella")** -- median, IQR, whiskers for anchoring familiar summary stats

The key insight: by using a *half*-violin instead of a full violin, you free up horizontal space for the raw data points. No redundant mirroring.

### When it beats existing options

- **vs. box plot alone:** reveals bimodality, skew, and gaps that box plots hide
- **vs. violin alone:** shows individual observations, so you see clusters and outliers directly
- **vs. bee swarm:** works at any n (bee swarm degrades past ~500)
- **vs. strip + box:** the density curve adds shape context that jitter alone doesn't convey
- Best for **small-to-medium n (20-2000)** where both individual points and shape matter

### When NOT to use

- Very small n (<10): density curve is unreliable, just show points + median
- Very large n (>5000): jittered points become an overplotted mess; switch to violin + box
- Many groups (>8): use ridgelines instead; rainclouds consume too much horizontal space per group

### D3 implementation approach

A raincloud is three existing D3 patterns composed together:

```js
// Layout: each group gets a band. Within the band:
//   top third: half-violin (area, one side only)
//   middle: box plot (rect + lines)
//   bottom third: jittered strip (circles)

const groupY = d3.scaleBand().domain(groups).range([0, height]).padding(0.1);
const bandH = groupY.bandwidth();

// 1. Half-violin (cloud) -- area going upward only
const violinArea = d3.area()
  .x0(d => xScale(d[0]))
  .x1(d => xScale(d[0]))
  .y0(bandH * 0.5)                          // baseline at midpoint
  .y1(d => bandH * 0.5 - densityScale(d[1])) // density goes up
  .curve(d3.curveBasis);

// 2. Box plot -- narrow rect centered below the violin
// Use computeStats() from the existing skill

// 3. Jittered strip -- circles below the box
// Constrain jitter to a narrow vertical band below the box
```

Horizontal orientation (groups on y-axis, values on x-axis) is most common for rainclouds because group labels read naturally.

### Observable Plot status

No built-in raincloud mark. You'd compose it from `Plot.areaY`, `Plot.boxX`/`Plot.boxY`, and `Plot.dot` with jitter. The lack of a dedicated mark suggests it hasn't reached "primitive" status in the community yet -- it's a composite pattern.

### Defensive design (Waskom 2023)

Waskom's "Designing Defensive Raincloud Plots" (arXiv:2303.17709) notes that naive rainclouds can mislead when KDE bandwidth is wrong or when the density curve extends beyond plausible data range. Recommendations:
- Clip the density curve to the data range (don't show density at impossible values)
- Use a bounded kernel near data boundaries
- Consider a histogram-based half instead of KDE for discrete or small-n data

---

## Letter-Value Plots (Extended Box Plots for Large n)

**Source:** Hofmann, Wickham, Kafadar 2017, "Letter-Value Plots: Boxplots for Large Data" (JCGS 26:3, 469-477). [Paper](https://vita.had.co.nz/papers/letter-value-plot.pdf)

### What it is

A box plot that shows progressively more quantiles as nested, shrinking boxes -- as many levels as the data supports reliably. Standard box plots show only median + quartiles regardless of n. With 10,000 points, you can estimate the 1/128th quantiles reliably, but a box plot throws that information away and flags hundreds of "outliers" that are actually expected tail behavior.

### Letter values (Tukey's naming)

| Letter | Quantile | Depth formula |
|--------|----------|---------------|
| M (median) | 0.500 | d_1 = (1+n)/2 |
| F (fourths) | 0.250, 0.750 | d_2 = (1+floor(d_1))/2 |
| E (eighths) | 0.125, 0.875 | d_3 = (1+floor(d_2))/2 |
| D (sixteenths) | 0.0625, 0.9375 | d_4 = (1+floor(d_3))/2 |
| C | 1/32, 31/32 | d_5 = ... |
| B | 1/64, 63/64 | ... |
| A | 1/128, 127/128 | ... |

General: depth d_i = (1 + floor(d_{i-1})) / 2, recursively. Lower letter value L_i = y_(floor(d_i)), upper U_i = y_(n - floor(d_i) + 1). When depth is half-integer, average the two adjacent order statistics.

### Stopping rule

Show boxes up to level k where the estimate is statistically reliable. The "trustworthy" rule: stop when 0.5 * sqrt(2 * d_k) * z_{1-alpha/2} > d_{k+1}. Practically, for alpha = 0.05, this means:
- n = 100: show ~4 levels (through eighths)
- n = 1000: show ~6 levels (through 1/64)
- n = 10000: show ~8 levels (through 1/256)
- Rule of thumb: k = floor(log2(n)) - 2

### Width encoding

Three options for box widths at each level:
- **linear**: width decreases by constant factor per level. Simple, readable.
- **exponential**: width proportional to proportion of data covered (50%, 25%, 12.5%...). Encodes coverage.
- **area**: area proportional to coverage. Most theoretically sound but harder to read.

### When it beats box plots

- **Large n (>200)**: box plots flag too many "outliers" that are just expected tail behavior
- **Comparing tail behavior**: letter-value plots reveal whether tails are heavier or lighter than expected
- **Detecting skew in tails**: asymmetric nesting is immediately visible

### D3 implementation approach

```js
function letterValues(sorted) {
  const n = sorted.length;
  const levels = [];
  let depth = (1 + n) / 2;

  // Level 0: median
  levels.push({ letter: "M", lower: quantileAtDepth(sorted, depth), upper: quantileAtDepth(sorted, depth) });

  const letters = ["F", "E", "D", "C", "B", "A", "Z", "Y", "X", "W"];
  let k = 0;

  while (k < letters.length) {
    depth = (1 + Math.floor(depth)) / 2;
    if (depth < 1) break;

    // Trustworthy stopping rule: stop when estimate is unreliable
    // Roughly: stop at k = floor(log2(n)) - 2
    if (k > Math.floor(Math.log2(n)) - 2) break;

    const lower = quantileAtDepth(sorted, depth);
    const upper = sorted[n - Math.floor(depth)]; // symmetric from top
    levels.push({ letter: letters[k], lower, upper, depth });
    k++;
  }
  return levels;
}

function quantileAtDepth(sorted, depth) {
  const i = Math.floor(depth) - 1; // 0-indexed
  if (depth === Math.floor(depth)) return sorted[i];
  return (sorted[i] + sorted[i + 1]) / 2;
}

// Render: nested rects, widest at center (median), narrowing outward
const boxWidth = d3.scaleLinear()
  .domain([0, levels.length - 1])
  .range([bandWidth * 0.8, bandWidth * 0.15]);

levels.forEach((lv, i) => {
  g.append("rect")
    .attr("x", -boxWidth(i) / 2)
    .attr("y", yScale(lv.upper))
    .attr("width", boxWidth(i))
    .attr("height", yScale(lv.lower) - yScale(lv.upper))
    .attr("fill", colorScale(i));  // sequential palette encodes depth
});
```

### Observable Plot status

Not built in. Seaborn has `boxenplot()` as a first-class chart type. The absence from Observable Plot suggests it remains a specialist tool, mainly used in EDA with large datasets.

---

## Distribution Comparison Research

### Which charts do readers understand best?

Summary of findings across multiple studies:

**Box plots** -- high familiarity, fast median comparison, but readers routinely misinterpret whiskers (many think they show min/max or standard deviation). Completely hide distribution shape. (Wilke, "Fundamentals of Data Visualization")

**Violin plots** -- less familiar to general audiences. Readers often don't understand that width = density. However, when explained, they allow correct identification of bimodality and skew that box plots miss. (Wikipedia/Violin plot overview)

**Strip/dot plots** -- surprisingly effective for small n. Readers can directly perceive individual values, gaps, and clusters. Performance degrades with overplotting. Best for n < 200.

**Raincloud plots** -- the MARC (Meta-Analytic Rain Cloud) study found 0.43-0.76 SD improvement in correct interpretation vs other chart types for evidence communication tasks. But they require more visual real estate and explanation for unfamiliar audiences. (Meta-Analytic Rain Cloud study, JREE 2022)

**Hypothetical Outcome Plots (HOPs)** -- animated samples from a distribution. Hullman et al. (IEEE VIS 2018) found viewers were **35-41 percentage points more accurate** on multivariate probability judgments vs error bars and violin plots. The visual system processes ensemble statistics from animated samples naturally, requiring less statistical literacy. Animation speed: ~400ms per frame works well.

Key paper: Hullman et al., "Hypothetical Outcome Plots Help Untrained Observers Judge Trends in Ambiguous Data" (IEEE TVCG 2018). Also: Kale et al., "Hypothetical Outcome Plots Outperform Error Bars and Violin Plots for Inferences about Reliability of Variable Ordering" (PLOS ONE 2015).

### Practical guidance from the research

1. **For statistical audiences**: violin + box overlay or letter-value plots
2. **For general audiences**: raincloud (if space permits) or strip + median line
3. **For uncertainty communication**: HOPs (animated) dramatically outperform static charts
4. **For comparing many groups (6+)**: ridgelines or small-multiple histograms
5. **For large n (>1000)**: letter-value plots or violin; never bee swarm or strip
6. **For detecting distribution differences**: HOPs > raincloud > violin > box (in order of reader accuracy)

---

## Observable Plot Patterns

Observable Plot provides distribution visualization through composable marks rather than monolithic chart types:

### Built-in marks for distributions

| Mark | What it does | Distribution use |
|------|-------------|-----------------|
| `Plot.boxX` / `Plot.boxY` | Composite box plot (rule + bar + tick + dot) | One-dimensional summaries. Computes quartiles, whiskers, outliers internally via group transform. |
| `Plot.density` | 2D Gaussian KDE with contour output | Two-dimensional density estimation. Bandwidth in pixels (default 20), configurable thresholds. Uses marching squares. |
| `Plot.dot` | Scatter/strip | Individual observations with jitter via transforms |
| `Plot.areaY` / `Plot.areaX` | Filled curves | KDE output rendered as half-violin or density area |
| `Plot.rectY` / `Plot.rectX` | Rectangles | Histograms via `Plot.binX` transform |
| `Plot.ruleY` / `Plot.ruleX` | Lines | Reference lines, median markers |
| `Plot.tickX` / `Plot.tickY` | Tick marks | Strip plots |

### What's NOT in Observable Plot

- No violin mark (compose from area + KDE)
- No raincloud mark (compose from area + box + dot)
- No letter-value plot mark
- No ridgeline mark (compose from area + faceting)
- No bee swarm mark (no built-in dodge/force)

### Design philosophy

Observable Plot treats distribution charts as compositions of simpler marks + transforms, not as monolithic chart types. This is the right model for D3 skills too -- teach the components and composition patterns rather than single-purpose functions.

### Key density mark details

```js
// Observable Plot 2D density
Plot.plot({
  marks: [
    Plot.density(data, {x: "x", y: "y", bandwidth: 20, fill: "density"}),
    Plot.dot(data, {x: "x", y: "y", r: 1, fill: "black", fillOpacity: 0.1})
  ]
})
```

The `fill: "density"` keyword maps density threshold values to a sequential color scale -- a pattern worth adopting in D3 implementations.

---

## Gradient/Heatmap Density (2D Density Alternatives)

When two quantitative variables need distribution visualization, 1D charts fail. Options:

### Hexbin

D3 has `d3-hexbin` for hexagonal binning. Hexagons tessellate with less visual bias than squares (no alignment artifacts on diagonal patterns). Each hex encodes point count via color or size.

```js
import {hexbin as d3Hexbin} from "d3-hexbin";

const hexbin = d3Hexbin()
  .x(d => xScale(d.x))
  .y(d => yScale(d.y))
  .radius(10)
  .extent([[0, 0], [width, height]]);

const bins = hexbin(data);
const color = d3.scaleSequential(d3.interpolateYlOrRd)
  .domain([0, d3.max(bins, d => d.length)]);
```

### Contour density (d3-contour)

`d3.contourDensity()` computes 2D KDE and returns GeoJSON contours. Equivalent to Observable Plot's density mark but lower-level.

```js
const contours = d3.contourDensity()
  .x(d => xScale(d.x))
  .y(d => yScale(d.y))
  .bandwidth(15)
  .thresholds(20)
  (data);

svg.selectAll("path")
  .data(contours)
  .join("path")
    .attr("d", d3.geoPath())
    .attr("fill", d => color(d.value));
```

### When to use which

| Method | Best for | Watch out for |
|--------|----------|--------------|
| **Scatter** | n < 500 | Overplotting |
| **Scatter + alpha** | n < 2000 | Still hides density shape |
| **Hexbin** | n > 500, want counts | Bin size choice matters; discrete feel |
| **Contour density** | n > 500, want smooth shape | Bandwidth choice; edge effects |
| **Heatmap (raster)** | Regular grid data | Not for irregular point clouds |

### Gradient density strips (1D)

An alternative to violins for small-multiples: encode density as a color gradient along a line. Each strip is a single row of pixels colored by KDE value. Very compact -- useful in tables or sparkline contexts. Not widely adopted but seen in genomics visualizations.

---

## Decision Guidance (Expanded Selection Table)

| Chart | n range | Groups | Shows | Hides | Reader familiarity |
|-------|---------|--------|-------|-------|--------------------|
| **Histogram** | Any | 1-2 | Counts, gaps, discreteness | Smoothness illusion from bins | High |
| **Box plot** | 10+ | 3-20+ | Median, IQR, outliers | Shape (bimodal = unimodal) | High |
| **Letter-value plot** | 200+ | 3-20+ | Tail behavior, nested quantiles | Shape (less than box plot) | Low |
| **Violin** | 30+ | 2-12 | Full density shape | Individual points | Medium |
| **Half/split violin** | 30+ | 2 subgroups per category | Shape comparison within category | Individual points | Low |
| **Raincloud** | 20-2000 | 2-8 | Shape + individuals + summary | Nothing (but space-intensive) | Low |
| **Ridgeline** | 30+ | 6-30+ | Trend across ordered groups | Precise comparison (no shared baseline) | Medium |
| **Bee swarm** | 10-500 | 2-8 | Every point, clusters, gaps | Nothing (but slow past 500) | Medium |
| **Strip/jitter** | Any | 2-12 | Raw data distribution | Density (overplots past 200) | High |
| **Density plot** | 50+ | 2-4 overlapping | Smooth shape, overlap | Individual values | Medium |
| **QQ plot** | 20+ | 1-2 | Departure from theoretical dist | Distribution shape directly | Low (specialist) |
| **HOPs (animated)** | Any | 2-4 | Uncertainty, probability | Static comparison | Low |
| **2D density (contour)** | 500+ | 1-4 | Joint distribution of 2 vars | Individual points | Medium |
| **Hexbin** | 500+ | 1-2 | Joint distribution, counts | Smooth shape | Medium |

### Selection flowchart (text form)

1. **How many variables?**
   - Two quantitative: hexbin or contour density
   - One quantitative, one categorical: continue below

2. **How many groups?**
   - 1-2: density plot or raincloud
   - 3-8: violin, raincloud, or box plot
   - 8-30+: ridgeline or box plot
   - 30+: small-multiple histograms

3. **How many points per group?**
   - <10: strip + median line (no summary stats -- too few points)
   - 10-30: strip + box or bee swarm (no KDE -- too few for reliable density)
   - 30-500: raincloud, violin, or bee swarm
   - 500-5000: violin + box or letter-value plot
   - 5000+: letter-value plot or violin (no individual points)

4. **What does the reader need?**
   - Compare medians: box plot or letter-value plot
   - See shape: violin or ridgeline
   - See individuals + shape: raincloud or bee swarm
   - Judge probability/uncertainty: HOPs
   - Compare tails: letter-value plot or QQ

---

## Code Patterns

### Raincloud plot (horizontal, D3 v7)

```js
function raincloud(svg, data, { x, y, width, height, margin, color = "#4682b4" }) {
  const groups = [...new Set(data.map(d => d[y]))];
  const values = data.map(d => d[x]);

  const xScale = d3.scaleLinear()
    .domain(d3.extent(values)).nice()
    .range([margin.left, width - margin.right]);

  const yBand = d3.scaleBand()
    .domain(groups)
    .range([margin.top, height - margin.bottom])
    .padding(0.2);

  const bw = yBand.bandwidth();

  for (const group of groups) {
    const gData = data.filter(d => d[y] === group);
    const gValues = gData.map(d => d[x]).sort(d3.ascending);
    const stats = computeStats(gValues);
    const g = svg.append("g")
      .attr("transform", `translate(0, ${yBand(group)})`);

    // 1. Half-violin (top portion of band)
    const bandwidth = 0.9 * Math.min(
      d3.deviation(gValues),
      (stats.q3 - stats.q1) / 1.34
    ) * Math.pow(gValues.length, -0.2);
    const ticks = d3.ticks(xScale.domain()[0], xScale.domain()[1], 200);
    const density = kde(gaussian, bandwidth, gValues)(ticks);
    const maxDensity = d3.max(density, d => d[1]);
    const densityScale = d3.scaleLinear()
      .domain([0, maxDensity])
      .range([bw * 0.45, 0]); // top half of band

    g.append("path")
      .datum(density)
      .attr("d", d3.area()
        .x(d => xScale(d[0]))
        .y0(bw * 0.45)
        .y1(d => densityScale(d[1]))
        .curve(d3.curveBasis))
      .attr("fill", color)
      .attr("fill-opacity", 0.6);

    // 2. Box plot (middle strip)
    const boxY = bw * 0.5;
    const boxH = bw * 0.15;
    g.append("line") // whisker
      .attr("x1", xScale(stats.whiskerLow)).attr("x2", xScale(stats.whiskerHigh))
      .attr("y1", boxY + boxH / 2).attr("y2", boxY + boxH / 2)
      .attr("stroke", "black");
    g.append("rect") // IQR box
      .attr("x", xScale(stats.q1)).attr("width", xScale(stats.q3) - xScale(stats.q1))
      .attr("y", boxY).attr("height", boxH)
      .attr("fill", color).attr("stroke", "black");
    g.append("line") // median
      .attr("x1", xScale(stats.median)).attr("x2", xScale(stats.median))
      .attr("y1", boxY).attr("y2", boxY + boxH)
      .attr("stroke", "white").attr("stroke-width", 2);

    // 3. Jittered strip (bottom portion of band)
    const jitterBand = [bw * 0.7, bw * 0.95];
    const random = d3.randomLcg(42);
    g.selectAll("circle")
      .data(gData)
      .join("circle")
        .attr("cx", d => xScale(d[x]))
        .attr("cy", () => jitterBand[0] + random() * (jitterBand[1] - jitterBand[0]))
        .attr("r", Math.min(2.5, bw * 0.03))
        .attr("fill", color)
        .attr("fill-opacity", 0.5);
  }
}
```

### Letter-value plot (D3 v7)

```js
function letterValuePlot(svg, data, { x, y, width, height, margin }) {
  const groups = [...new Set(data.map(d => d[x]))];

  const xBand = d3.scaleBand()
    .domain(groups)
    .range([margin.left, width - margin.right])
    .padding(0.2);

  const yScale = d3.scaleLinear()
    .domain(d3.extent(data, d => d[y])).nice()
    .range([height - margin.bottom, margin.top]);

  // Sequential color: deeper levels get lighter
  const colorScale = d3.scaleSequential(d3.interpolateBlues)
    .domain([-1, 10]); // invert so median is darkest

  for (const group of groups) {
    const sorted = Float64Array.from(
      data.filter(d => d[x] === group).map(d => d[y])
    ).sort();
    const n = sorted.length;

    const levels = computeLetterValues(sorted);
    const bw = xBand.bandwidth();

    // Width decreases linearly per level
    const widthScale = d3.scaleLinear()
      .domain([0, levels.length])
      .range([bw, bw * 0.15]);

    const g = svg.append("g")
      .attr("transform", `translate(${xBand(group)}, 0)`);

    levels.forEach((lv, i) => {
      if (i === 0) return; // skip median-only level
      const w = widthScale(i);
      g.append("rect")
        .attr("x", (bw - w) / 2)
        .attr("y", yScale(lv.upper))
        .attr("width", w)
        .attr("height", Math.max(1, yScale(lv.lower) - yScale(lv.upper)))
        .attr("fill", colorScale(levels.length - i))
        .attr("stroke", "white")
        .attr("stroke-width", 0.5);
    });

    // Median line
    g.append("line")
      .attr("x1", 0).attr("x2", bw)
      .attr("y1", yScale(levels[0].value)).attr("y2", yScale(levels[0].value))
      .attr("stroke", "black").attr("stroke-width", 2);
  }
}

function computeLetterValues(sorted) {
  const n = sorted.length;
  const levels = [];
  let depth = (1 + n) / 2;

  // Median
  const medianVal = atDepth(sorted, depth);
  levels.push({ letter: "M", value: medianVal, lower: medianVal, upper: medianVal });

  const letters = ["F", "E", "D", "C", "B", "A", "Z", "Y", "X", "W"];
  const maxLevels = Math.max(0, Math.floor(Math.log2(n)) - 2);

  for (let k = 0; k < Math.min(maxLevels, letters.length); k++) {
    depth = (1 + Math.floor(depth)) / 2;
    if (depth < 1) break;
    const lower = atDepth(sorted, depth);
    const upper = atDepth(sorted, n + 1 - depth);
    levels.push({ letter: letters[k], lower, upper, depth });
  }
  return levels;
}

function atDepth(sorted, depth) {
  const i = Math.floor(depth) - 1; // 0-indexed
  if (depth === Math.floor(depth)) return sorted[i];
  return (sorted[i] + sorted[i + 1]) / 2;
}
```

### HOPs (Hypothetical Outcome Plots) -- animated distribution sampling

```js
function hops(svg, data, { x, y, width, height, margin, interval = 400 }) {
  // Pre-draw the base chart (e.g., bar chart of means)
  // On each frame, draw one bootstrap sample's statistic

  const groups = [...new Set(data.map(d => d[x]))];
  const xBand = d3.scaleBand().domain(groups).range([margin.left, width - margin.right]).padding(0.2);
  const yScale = d3.scaleLinear()
    .domain(d3.extent(data, d => d[y])).nice()
    .range([height - margin.bottom, margin.top]);

  const bars = svg.selectAll(".hop-bar")
    .data(groups)
    .join("rect")
      .attr("class", "hop-bar")
      .attr("x", d => xBand(d))
      .attr("width", xBand.bandwidth());

  function animate() {
    // Bootstrap sample: draw n values with replacement per group
    const sampled = groups.map(group => {
      const vals = data.filter(d => d[x] === group).map(d => d[y]);
      const boot = Array.from({length: vals.length}, () =>
        vals[Math.floor(Math.random() * vals.length)]
      );
      return { group, mean: d3.mean(boot) };
    });

    bars.data(sampled, d => d.group)
      .transition().duration(interval * 0.6)
        .attr("y", d => yScale(d.mean))
        .attr("height", d => yScale(0) - yScale(d.mean));
  }

  const timer = d3.interval(animate, interval);
  return timer; // caller can stop with timer.stop()
}
```

### 2D contour density

```js
const contours = d3.contourDensity()
  .x(d => xScale(d.x))
  .y(d => yScale(d.y))
  .size([width, height])
  .bandwidth(20)
  .thresholds(15)
  (data);

const color = d3.scaleSequential(d3.interpolateViridis)
  .domain([0, d3.max(contours, d => d.value)]);

svg.selectAll("path.contour")
  .data(contours)
  .join("path")
    .attr("class", "contour")
    .attr("d", d3.geoPath())
    .attr("fill", d => color(d.value))
    .attr("stroke", "none");

// Overlay individual points at low opacity
svg.selectAll("circle")
  .data(data)
  .join("circle")
    .attr("cx", d => xScale(d.x))
    .attr("cy", d => yScale(d.y))
    .attr("r", 1.5)
    .attr("fill", "black")
    .attr("opacity", 0.15);
```

---

## Sources

- Allen et al. 2019, [Raincloud plots: a multi-platform tool for robust data visualization](https://pmc.ncbi.nlm.nih.gov/articles/PMC6480976/)
- Hofmann, Wickham, Kafadar 2017, [Letter-Value Plots: Boxplots for Large Data](https://vita.had.co.nz/papers/letter-value-plot.pdf)
- Waskom 2023, [Designing Defensive Raincloud Plots](https://arxiv.org/pdf/2303.17709)
- Hullman et al. 2018, [Hypothetical Outcome Plots Help Untrained Observers Judge Trends](https://ieeexplore.ieee.org/document/8440816/)
- Kale et al. 2015, [HOPs Outperform Error Bars and Violin Plots](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0142444)
- Wilke, [Fundamentals of Data Visualization: Boxplots and Violins](https://clauswilke.com/dataviz/boxplots-violins.html)
- Scherer 2021, [Visualizing Distributions with Raincloud Plots](https://www.cedricscherer.com/2021/06/06/visualizing-distributions-with-raincloud-plots-and-how-to-create-them-with-ggplot2/)
- [Observable Plot Density Mark](https://observablehq.com/plot/marks/density)
- [Observable Plot Box Mark](https://observablehq.com/plot/marks/box)
- [D3 Graph Gallery: 2D Density](https://d3-graph-gallery.com/density2d)
- [D3 Raincloud Plot Gist (vijithassar)](https://gist.github.com/vijithassar/c60dafea4431f292660d6f5e0487e470)
- Gimond, [Beyond the Boxplot: Tukey's Letter-Value Summaries](http://mgimond.github.io/ES218/letter_values.html)
