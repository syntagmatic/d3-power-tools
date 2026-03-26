# Parallel Coordinates Research

Research date: 2026-03-25

## Current Coverage

The `skills/parallel-coordinates/SKILL.md` is Tier 1 (strongest). It covers:

- **Canvas+SVG hybrid architecture** with layered rendering
- **Progressive rendering** via render queue with shuffle for representative partial frames
- **Opacity scaling** (`alpha = max(0.01, min(0.8, 100/n))`)
- **Axis brushing** with multi-brush support (disjoint selections per axis)
- **Manual axis reordering** via drag
- **Axis inversion** with Set-based state tracking
- **Fisheye distortion** for 30+ dimensions
- **Column deletion** and **text search** for dimension management
- **Mixed scale inference** (linear, log, point/ordinal)
- **Null zone** rendering for missing data
- **Color-picking hit detection** on hidden canvas for hover-to-highlight
- **OffscreenCanvas in Web Worker** for 50K+ rows
- **CSV export** of brushed selections
- **Bezier curves** vs straight lines toggle

**Gaps identified**: No automated axis ordering, no aggregation/density rendering, no edge bundling, no guidance on when to use dimension reduction instead.

---

## Automated Axis Reordering (Pargnostics, correlation-based, clutter reduction)

The current skill covers manual drag reordering but has no automated reordering. This is a significant gap -- users shouldn't have to discover correlations by trial and error with 20+ axes.

### Pargnostics (Dasgupta & Kosara, 2010)

"Parallel coordinates diagnostics" -- screen-space metrics computed per axis pair:

| Metric | What it measures |
|--------|-----------------|
| **Crossing count** | Number of line intersections between two axes |
| **Crossing angle** | Distribution of intersection angles (closer to 90 = more readable) |
| **Convergence** | Lines from spread positions on left axis converging to narrow range on right |
| **Overplotting** | Fraction of pixels drawn more than once |
| **Parallelism** | Lines running nearly parallel (indicates positive correlation) |
| **Mutual information** | Statistical dependency between axis pair |

These metrics enable automated optimization: the system can rank all axis-pair arrangements and select orderings that maximize a user-chosen criterion (e.g., minimize crossings, maximize convergence).

**Key insight**: Axis ordering is NP-complete for optimal global arrangement, but greedy approaches work well in practice -- start with the pair having highest metric score, then greedily append the next best neighbor.

### Correlation-based ordering

Simpler than Pargnostics but effective: order axes so that highly correlated dimensions are adjacent. Adjacent positively-correlated axes produce parallel line bundles; negatively-correlated axes produce X-shaped crossings (which axis inversion can resolve).

```
Algorithm: Greedy correlation ordering
1. Compute |correlation| matrix for all dimension pairs
2. Pick the pair with highest |correlation| as the first two axes
3. For remaining dimensions, find the one most correlated with either end
4. Append to whichever end has higher correlation
5. For negative correlations, auto-invert the appended axis
```

### Clutter reduction ordering

Minimize visual clutter by ordering axes to reduce total line crossings. Equivalent to the minimum linear arrangement problem. Approximations:

- **Greedy neighbor**: Place adjacent axes that minimize pairwise crossings
- **Simulated annealing**: Random swaps, accept if clutter decreases (or with cooling probability)
- **Optimal for small n**: For <12 dimensions, brute-force all permutations is feasible

### Implementation sketch (D3 context)

```js
// Correlation-based auto-order
function autoOrderByCorrelation(data, dimensions) {
  const corr = (a, b) => {
    const va = data.map(d => +d[a]), vb = data.map(d => +d[b]);
    const ma = d3.mean(va), mb = d3.mean(vb);
    const num = d3.sum(va.map((v, i) => (v - ma) * (vb[i] - mb)));
    const den = Math.sqrt(
      d3.sum(va.map(v => (v - ma) ** 2)) *
      d3.sum(vb.map(v => (v - mb) ** 2))
    );
    return den === 0 ? 0 : num / den;
  };

  // Build correlation matrix
  const pairs = [];
  for (let i = 0; i < dimensions.length; i++)
    for (let j = i + 1; j < dimensions.length; j++)
      pairs.push({ a: dimensions[i], b: dimensions[j], r: corr(dimensions[i], dimensions[j]) });
  pairs.sort((a, b) => Math.abs(b.r) - Math.abs(a.r));

  // Greedy chain from strongest pair
  const ordered = [pairs[0].a, pairs[0].b];
  const used = new Set(ordered);
  while (ordered.length < dimensions.length) {
    let bestDim = null, bestR = -1, bestEnd = 'right';
    for (const dim of dimensions) {
      if (used.has(dim)) continue;
      const rLeft = Math.abs(corr(ordered[0], dim));
      const rRight = Math.abs(corr(ordered[ordered.length - 1], dim));
      if (rLeft > bestR) { bestR = rLeft; bestDim = dim; bestEnd = 'left'; }
      if (rRight > bestR) { bestR = rRight; bestDim = dim; bestEnd = 'right'; }
    }
    if (bestEnd === 'left') ordered.unshift(bestDim);
    else ordered.push(bestDim);
    used.add(bestDim);
  }
  return ordered;
}
```

### Sources

- [Pargnostics paper (PDF)](https://kosara.net/papers/2010/Dasgupta-InfoVis-2010.pdf)
- [Pargnostics on eagereyes](https://eagereyes.org/blog/2010/pargnostics)
- [Efficient Reordering of Parallel Coordinates (SpringerLink)](https://link.springer.com/chapter/10.1007/978-3-319-24523-2_14)
- [Parallel Coordinate Order for High-Dimensional Data](https://arxiv.org/pdf/1905.10035)

---

## Dimension Reduction Alternatives (PCA biplot, UMAP, when to reduce vs show all)

Parallel coordinates show all original dimensions. Dimension reduction (PCA, UMAP, t-SNE) projects to 2-3 dimensions. These are complements, not substitutes.

### When to use parallel coordinates

- **Fewer than ~50 dimensions** (with fisheye/search for 50-200)
- When users need to **read individual variable values** and set filters
- When the **identity of each dimension matters** (named features, not abstract components)
- For **interactive exploration** with brushing and filtering
- When **individual data points** need to be traceable

### When to switch to dimension reduction

- **Hundreds to thousands of dimensions** (genomics, NLP embeddings) -- parallel coordinates become unreadable
- When the goal is **cluster discovery** rather than per-variable analysis
- When **global structure** (manifold shape) matters more than individual feature values
- For **communication** to non-expert audiences (scatter plot is more intuitive)

### Method comparison

| Method | Preserves | Loses | Best for |
|--------|-----------|-------|----------|
| **PCA biplot** | Linear variance, variable loadings | Nonlinear structure | Understanding which variables drive variance; interpretable axes |
| **t-SNE** | Local neighborhoods | Global distances, density | Cluster visualization; publication figures |
| **UMAP** | Local + some global structure | Exact distances | Large datasets; faster than t-SNE; streaming |
| **Parallel coordinates** | All original dimensions | Spatial proximity | Interactive filtering; reading values; domain expert analysis |

### Hybrid approach: PCA-ordered parallel coordinates

Use PCA to inform axis ordering rather than replacing the visualization:

1. Run PCA on the data
2. Order axes by their loading on PC1 (the direction of maximum variance)
3. Dimensions that load similarly on PC1 end up adjacent, revealing the primary pattern

This gives the interpretability of parallel coordinates with the structural insight of PCA.

### Sources

- [PCA vs t-SNE vs UMAP comparison](https://medium.com/@laakhanbukkawar/pca-vs-t-sne-vs-umap-visualizing-the-invisible-in-your-data-92cb2baebdbb)
- [Understanding UMAP (Google PAIR)](https://pair-code.github.io/understanding-umap/)
- [Techniques for Visualizing High Dimensional Data](https://www.geeksforgeeks.org/data-visualization/techniques-for-visualizing-high-dimensional-data/)
- [Seeing data as t-SNE and UMAP do (Nature Methods)](https://www.nature.com/articles/s41592-024-02301-x)

---

## Curved and Bundled Parallel Coordinates (edge bundling between axes)

The current skill mentions Bezier curves as a styling option. The research literature goes further with systematic edge bundling.

### Angular-based Edge Bundled Parallel Coordinates (APCP)

From Hazarika et al. (IEEE VIS 2022):

- Replace individual polylines with **bundled Bezier curves** that aggregate similar trajectories
- Between each axis pair, compute an **angular distribution** of line segment inclinations
- Represent bundles using curves that encode mean angle and variance
- Result: simplified overview that preserves correlation structure while eliminating clutter

**Key benefit**: Shows cluster structure between axes without drawing every line. Particularly effective for ensemble simulation data (meteorology, climate).

### Bundling techniques

1. **Cluster-based bundling**: K-means cluster data points between each axis pair. Draw one thick curve per cluster with width proportional to membership count.

2. **Density-based bundling**: Compute 2D density between axis pairs. Route curves through high-density regions using control point attraction.

3. **Hierarchical bundling**: Use hierarchical clustering to create multi-level bundles. Coarse bundles at overview, split into finer bundles on zoom.

### Implementation approach

```js
// Cluster-based curve bundling between adjacent axes
function bundledPaths(data, dimA, dimB, k = 5) {
  // 1. Extract (valueA, valueB) pairs
  const points = data.map(d => [scales[dimA](d[dimA]), scales[dimB](d[dimB])]);

  // 2. K-means cluster on the 2D points
  const clusters = kMeans(points, k);

  // 3. For each cluster, compute centroid path with Bezier control points
  return clusters.map(cluster => {
    const yA = d3.mean(cluster.points, p => p[0]);
    const yB = d3.mean(cluster.points, p => p[1]);
    const spread = d3.deviation(cluster.points, p => p[0]);
    return { yA, yB, count: cluster.points.length, spread };
  });
}

// Draw bundled curves with width ~ count
function drawBundles(ctx, bundles, xA, xB) {
  const xMid = (xA + xB) / 2;
  for (const { yA, yB, count } of bundles) {
    ctx.lineWidth = Math.sqrt(count) * 0.5;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(xA, yA);
    ctx.bezierCurveTo(xMid, yA, xMid, yB, xB, yB);
    ctx.stroke();
  }
}
```

### C1-continuous piecewise Bezier curves

Heinrich & Weiskopf showed that replacing polygonal lines with C1 continuous Bezier curves makes it easier to visually trace data points across axes. Control points at 1/3 and 2/3 between axes ensure smooth transitions. Bundling these curves then provides visual separation between clusters.

### Sources

- [Angular-based Edge Bundled PCP (arXiv)](https://arxiv.org/abs/2209.10874)
- [Evaluation of a Bundling Technique for Parallel Coordinates (PDF)](https://joules.de/files/heinrich_evaluation_2012.pdf)
- [An Edge-Bundling Layout for Interactive Parallel Coordinates](https://www.researchgate.net/publication/261958582_An_Edge-Bundling_Layout_for_Interactive_Parallel_Coordinates)
- [Parallel Coordinates for Multidimensional Data Visualization (Heinrich & Weiskopf)](https://www.joules.de/files/heinrich_parallel_2015.pdf)

---

## Scalability Techniques (aggregation, density, sampling beyond 100K)

The current skill covers progressive rendering and OffscreenCanvas workers for 50K+ rows. Beyond 100K, drawing every line -- even progressively -- hits fundamental limits: screen resolution, overdraw, and memory.

### Density-based rendering (replace lines with heatmap)

Instead of drawing N individual lines, rasterize line density into a 2D grid between each axis pair:

1. For each axis pair, create a 2D histogram (bins on each axis)
2. For each data row, increment the bin at (binA, binB)
3. Render bins as colored rectangles with color mapped to count
4. Result: O(bins^2) rendering cost regardless of N

```js
// Density rendering between two axes
function renderDensity(ctx, data, dimA, dimB, xA, xB, binsPerAxis = 50) {
  const grid = Array.from({ length: binsPerAxis }, () => new Float32Array(binsPerAxis));
  const scA = scales[dimA], scB = scales[dimB];
  const h = height / binsPerAxis;

  // Bin the data
  for (const d of data) {
    const yA = Math.floor(scA(d[dimA]) / h);
    const yB = Math.floor(scB(d[dimB]) / h);
    if (yA >= 0 && yA < binsPerAxis && yB >= 0 && yB < binsPerAxis)
      grid[yA][yB]++;
  }

  // Find max for color scale
  let maxCount = 0;
  for (const row of grid) for (const v of row) if (v > maxCount) maxCount = v;
  const color = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, maxCount]);

  // Draw density bands (simplified -- full version draws trapezoids)
  const w = xB - xA;
  for (let a = 0; a < binsPerAxis; a++) {
    for (let b = 0; b < binsPerAxis; b++) {
      if (grid[a][b] === 0) continue;
      ctx.fillStyle = color(grid[a][b]);
      ctx.globalAlpha = 0.7;
      // Draw a quad from (xA, a*h) to (xB, b*h)
      ctx.beginPath();
      ctx.moveTo(xA, a * h);
      ctx.lineTo(xA, (a + 1) * h);
      ctx.lineTo(xB, (b + 1) * h);
      ctx.lineTo(xB, b * h);
      ctx.closePath();
      ctx.fill();
    }
  }
}
```

### Frequency-based parallel coordinates

From the R `freqparcoord` package concept: plot only the top-density lines, color-coded by density value. Works by:

1. Estimate multivariate density at each data point (KDE or k-nearest-neighbor density)
2. Rank points by density
3. Draw only the top N% (e.g., top 10%)
4. Color-code by density: dark = high density, light = low density

This shows the dominant patterns without clutter from outliers.

### Hierarchical aggregation

From Fua et al. -- hierarchical clustering creates a multi-resolution view:

1. Cluster data hierarchically (agglomerative or divisive)
2. At each level, represent clusters as bands (min-max range) or single representative lines
3. User drills down by clicking a cluster to expand it
4. Band width encodes cluster size

### Confluent drawing

From Luo et al. (2019) -- data binning per dimension creates a node-link structure:

1. Bin each dimension independently
2. Count lines connecting each bin-pair between adjacent axes
3. Draw edges with width proportional to count
4. Result looks like a Sankey/alluvial diagram

### GPU-accelerated binning

For 1M+ rows, use WebGL/GPU compute:

1. Scatter data into 2D bins using vertex shaders with atomic counters
2. Render density texture directly on GPU
3. Avoids CPU bottleneck entirely
4. See the `webgl-rendering` skill for shader patterns

### Performance tiers (extended)

| Rows | Technique | Notes |
|------|-----------|-------|
| <50K | Progressive rendering + opacity | Current skill coverage |
| 50K-200K | OffscreenCanvas worker + aggressive opacity | Current skill coverage |
| 200K-1M | Frequency-based (top 5-10% by density) | New: density estimation + sampling |
| 200K-1M | Density rendering (bin-based) | New: heatmap between axis pairs |
| 1M+ | GPU binning + density texture | New: WebGL compute pipeline |
| Any large | Hierarchical aggregation | New: drill-down exploration |

### Sources

- [Visual Exploration of Large Multidimensional Data Using Parallel Coordinates on Big Data Infrastructure](https://www.mdpi.com/2227-9709/4/3/21)
- [Hierarchical Parallel Coordinates for Exploration of Large Datasets](https://www.researchgate.net/publication/220943999_Hierarchical_Parallel_Coordinates_for_Exploration_of_Large_Datasets)
- [Confluent-Drawing Parallel Coordinates (arXiv)](https://arxiv.org/pdf/1906.10017)
- [Blending aggregation and selection for parallel coordinates](http://openaccess.city.ac.uk/2840/)
- [freqparcoord R package](https://search.r-project.org/CRAN/refmans/freqparcoord/html/freqparcoord.html)
- [Visualizing High-Dimensional Data Using Parallel Coordinates (2025 blog)](https://markusthill.github.io/blog/2025/visualizing-high-dimensional-data-with-parallel-coordinates/)

---

## Decision Guidance

### When to add automated axis ordering

**Do it when**: Dataset has >10 dimensions and the user hasn't expressed a preferred order. Offer as a toolbar button ("Auto-order by correlation" / "Auto-order by clutter").

**Don't force it**: Domain experts often have a natural dimension ordering (e.g., process stages, anatomical regions). Default to data column order; auto-order on request.

### When to switch from lines to density

**Do it when**: n > 200K or when opacity-scaled lines become a solid block of color. If `alpha < 0.02`, individual lines are invisible -- switch to density rendering.

**Hybrid approach**: Draw density background + overlay the brushed selection as individual lines. This gives overview + detail in one view.

### When to use edge bundling

**Do it when**: You want to show cluster structure between axes without requiring the user to brush. Works well for presentation/communication mode (less interactive, more "here's what the data shows").

**Don't use for**: Precise value reading or interactive brushing -- bundles obscure individual line positions.

### When to suggest dimension reduction instead

**Suggest PCA/UMAP when**:
- Dimensions > 100 (parallel coordinates can't show them all meaningfully)
- User asks "are there clusters?" (scatter plot of UMAP embedding answers this faster)
- Variables are not individually meaningful (e.g., pixel values, embedding dimensions)

**Suggest the hybrid** (PCA-ordered parallel coordinates) when:
- User wants both cluster overview and per-variable detail
- Dimensions are 10-50 named features

### Observable Plot note

Observable Plot does not have a built-in parallel coordinates mark as of early 2026. The canonical approach remains D3 with Canvas+SVG hybrid. Observable notebooks have multiple community examples but no Plot-native API.

---

## Code Patterns

### Pattern 1: Auto-order toolbar button

```js
// Add to toolbar
const orderSelect = toolbar.append("select")
  .on("change", function() {
    const method = this.value;
    if (method === "correlation") {
      dimensions = autoOrderByCorrelation(data, dimensions);
    } else if (method === "clutter") {
      dimensions = autoOrderByClutter(data, dimensions);
    } else {
      dimensions = [...originalDimensions]; // reset
    }
    updateLayout();
    updateCanvas();
  });

orderSelect.selectAll("option")
  .data(["original", "correlation", "clutter"])
  .join("option")
  .attr("value", d => d)
  .text(d => `Order: ${d}`);
```

### Pattern 2: Density rendering toggle

```js
let renderMode = "lines"; // or "density"

function render() {
  ctx.clearRect(0, 0, width, height);
  if (renderMode === "density") {
    for (let i = 0; i < dimensions.length - 1; i++) {
      renderDensity(ctx, data, dimensions[i], dimensions[i + 1],
        xScale(dimensions[i]), xScale(dimensions[i + 1]));
    }
  } else {
    // existing line rendering with opacity scaling
    renderLines(ctx, data, dimensions, scales);
  }
  // Always draw brushed selection as lines on top
  if (selected.length > 0 && selected.length < data.length) {
    renderLines(ctx, selected, dimensions, scales, { alpha: 0.8, color: "steelblue" });
  }
}
```

### Pattern 3: Frequency-based top-density rendering

```js
function renderTopDensity(ctx, data, dimensions, percentile = 0.1) {
  // Estimate density per point using k-nearest neighbors
  const k = Math.max(5, Math.floor(Math.sqrt(data.length)));
  const densities = estimateKNNDensity(data, dimensions, k);

  // Sort by density, take top percentile
  const indexed = data.map((d, i) => ({ d, density: densities[i] }));
  indexed.sort((a, b) => b.density - a.density);
  const cutoff = Math.floor(data.length * percentile);
  const topPoints = indexed.slice(0, cutoff);

  // Color scale for density
  const colorScale = d3.scaleSequential(d3.interpolateInferno)
    .domain(d3.extent(topPoints, d => d.density));

  // Draw lines colored by density
  for (const { d, density } of topPoints) {
    ctx.strokeStyle = colorScale(density);
    ctx.globalAlpha = 0.5;
    drawPolyline(ctx, d, dimensions, scales);
  }
}
```

### Pattern 4: Cluster-based edge bundling

```js
function renderBundled(ctx, data, dimensions, k = 8) {
  for (let i = 0; i < dimensions.length - 1; i++) {
    const dimA = dimensions[i], dimB = dimensions[i + 1];
    const xA = xScale(dimA), xB = xScale(dimB);

    // Extract normalized axis values for clustering
    const points = data.map(d => [scales[dimA](d[dimA]), scales[dimB](d[dimB])]);
    const clusters = kMeans(points, k);

    // Draw bundles
    for (const cluster of clusters) {
      const yA = d3.mean(cluster, p => p[0]);
      const yB = d3.mean(cluster, p => p[1]);
      const count = cluster.length;

      ctx.lineWidth = Math.max(1, Math.sqrt(count / data.length) * 20);
      ctx.globalAlpha = Math.min(0.8, count / data.length * 5);
      ctx.strokeStyle = "#4682b4";

      const xMid = (xA + xB) / 2;
      ctx.beginPath();
      ctx.moveTo(xA, yA);
      ctx.bezierCurveTo(xMid, yA, xMid, yB, xB, yB);
      ctx.stroke();
    }
  }
}
```
