---
name: patterns
description: "Choose the chart form that makes a dataset's shape visible: distributions (box, violin, raincloud, ridgeline/joy, beeswarm, strip/jitter, density/KDE bandwidth, letter-value, QQ), multivariate parallel coordinates (parcoords, axis order, axis brushing, strum, Canvas at scale), small multiples (trellis, facet wrap/grid, shared vs independent scales, synchronized panels), and word-sized sparkcharts (sparklines, spark bars, win/loss, bullet charts, KPI cards, sparklines in tables)."
---

# Patterns

The data has a shape: two modes, a heavy tail, a cluster in 8 dimensions, one series out of twenty that breaks trend. The job is to pick the form that makes that shape visible rather than one that summarizes it away. Every form hides something. Know what, and check it isn't the thing that matters.

Start with the table, then read the section for the form you picked.

## Which form

| If the question is... | Use | Not |
|---|---|---|
| what does one variable look like, n < 10 | strip + median line | any summary stat (quartiles of 8 points are noise) |
| same, n 10-30 | strip + box, or beeswarm | KDE (invents shape) |
| same, n 30-500 | raincloud, violin + box, or beeswarm | a bare box (hides bimodality) |
| same, n 500-5000 | violin + box, or letter-value | beeswarm/strip (overplots) |
| same, n 5000+ | letter-value or violin | points of any kind |
| is it discrete (counts, ratings) | histogram or dot/bar per value | KDE: it puts density at 3.5 children |
| compare medians across 5+ groups | box plots, sorted by median | a box alone if shape is unchecked (overlay points) |
| compare 6+ ordered groups' shapes | ridgeline | ridgeline for *unordered* categories (stacking implies order), so use faceted violins |
| compare 2-4 overlapping shapes | overlaid densities with alpha | >4 overlaid (use ridgeline) |
| does it follow a normal (or other) distribution | QQ plot with a confidence band | eyeballing a histogram |
| tails, at large n | letter-value | box plot (flags hundreds of expected points as outliers) |
| relationships across 5+ numeric dimensions | parallel coordinates + brushing | scatterplot matrix beyond 5 dims; PC for 2-3 dims (use a scatter) |
| mostly categorical dimensions | parallel sets / alluvial | parallel coordinates |
| same chart across 5+ groups, question is shape | small multiples | one chart with 6+ overlapping lines |
| where exactly do series cross, or 2-3 series | one chart | small multiples |
| trend next to a number, in text/table/card | sparkline (or spark bar, win/loss, bullet) | a full chart with axes |
| a precise value at a point | a chart with axes, or a table | a sparkline |

## Distributions

- **The box plot trap.** Normal and bimodal samples with equal median and IQR draw identical boxes. Until you've seen the shape, overlay the points or use a violin.
- **Bandwidth is editorial.** Default to Silverman (`0.9 · min(σ, IQR/1.34) · n^-0.2`). It over-smooths multimodal data, so halve it if you suspect two modes. Log-transform skewed data first. If IQR = 0 (tied data), fall back to σ, or the bandwidth is 0 and every density is NaN.
- Evaluate KDE over `extent ± 3·bw`, then clip to the possible range: no density at negative durations or scores over 100.
- **Violin width is a claim.** Equal max width makes n=10 look as sure as n=10,000. Use a shared density scale when group sizes matter, width ∝ √n when they differ by more than 3×.
- Tukey whiskers end at the last data point *inside* `1.5·IQR`, not at the fence. Name the whisker rule in the caption if it isn't Tukey's.
- Notches: `median ± 1.57·IQR/√n`. Non-overlap ≈ different medians at ~95%.
- Ridgelines: each ridge reaches into the row above, so draw the top row first and the bottom row last, so lower ridges are in front. Overlap 0.3-0.5 stays readable.
- Force beeswarm: the default schedule needs ~300 ticks to reach `alphaMin`. Stopping at 120 leaves overlaps. Or skip the simulation and use a sorted dodge placement.
- Jitter with `d3.randomLcg(seed)`, never `Math.random`, so points don't jump on re-render.
- Brushed subset KDE: multiply by `subset.length / group.length` or 5 selected points spike 10× taller than the full group.
- `d3.quantile` accepts unsorted input. `d3.quantileSorted` assumes sorted input and is wrong without an error if it isn't.

## Parallel coordinates

- **Axis order is the design.** Only adjacent pairs are readable. Default: start from the highest-variance dimension and greedily chain by |r|. Put the outcome axis at far right when there is one.
- Reading pairs: near-parallel segments = positive correlation; X/hourglass = negative; all lines through one point between the axes = perfect negative linear; bowtie envelope = an elliptical cluster.
- Canvas for lines, SVG for axes and brushes above it. SVG only below ~500 rows. Past ~5K, render progressively, **shuffling** rows so the first frame isn't just the head of a sorted file. Past ~50K, a worker with OffscreenCanvas.
- Line alpha `clamp(100/n, 0.01, 0.8)`. Color by one dimension, and past ~7 categories switch to highlight-on-hover.
- `brushY` per axis, and rows pass when every active filter passes. Strum brushes between axes select by relationship, which axis brushes can't.
- Axis inversion lives in state (a `Set`) applied when building scales. Mutating the range is lost on rebuild.
- Missing values go to a styled null zone below the axis. Don't drop the rows.
- Canvas picking via an RGB-indexed hidden canvas: accept only `alpha === 255`. Anti-aliased edges decode to the wrong row.

## Small multiples

- **Shared vs independent y is the decision.** Magnitude questions ("which is highest?") need shared. Shape questions ("is each seasonal?") can use independent, but label it, because viewers assume panels compare.
- Compute shared domains from the full data **before** the facet loop. `d3.extent(facet)` inside it is the classic accidental-independent-scale bug.
- Order panels by a statistic or similarity, not the alphabet, unless people will look panels up by name.
- Up to ~20 panels at full detail. At 20-50, strip to shape only. At 200+, don't: aggregate or filter. Below ~120px wide, line panels lose their shape.
- Facet wrap: `cols = ceil(sqrt(n · aspect))`. Y axis on the left column only, x on the bottom row only.
- Linked brush/zoom across panels: `if (!event.sourceEvent) return;` before moving the others, or it loops.
- Shared-canvas hit test: bounds-check the column as well as the index, or the right margin wraps into the next row.
- Resize: debounce, and re-layout only when the column count changes.

## Sparkcharts

- **Same metric across rows → one shared y-domain.** Per-row extents make 1% and 40% look the same, and with no axis nothing gives it away.
- Always put a number (latest, range) beside the spark. Zero baseline for counts and money, extent for relative change, and then never compare heights.
- `curveMonotoneX` by default: no overshoot. `curveBasis` flattens peaks; cardinal and Catmull-Rom overshoot.
- `.defined(d => d != null)`: a gap should look like a gap.
- Flat data: pad `[v-1, v+1]`. More points than pixels: LTTB.
- Inline SVG in a table cell adds a line-height gap below: `display: block`.
- Monitoring: fixed time windows, so the normal shape becomes familiar.
- `stroke: currentColor`, `role="img"`, and an `aria-label` with trend, min, max, latest.

## Traps across all four

- Auto-scaling per panel/row/sparkline when the reader will compare them. It's the same lie in three forms.
- Canvas without DPR scaling looks blurry: backing store `w·dpr`, `ctx.scale(dpr, dpr)`.
- Categorical palettes past ~7 hues. Use highlight or direct labels instead (`legibility`).

## References

- `references/distributions.md`: what each form hides, KDE + Silverman code, box/notch/whisker rules, violin scaling, raincloud and ridgeline layout, beeswarm dodge and tick count, letter-value code, QQ bands.
- `references/parallel-coordinates.md`: duality table, correlation ordering code, strum intersection test, render tiers, brushing and axis interactions, hit-canvas picking.
- `references/small-multiples.md`: panel counts, ordering, scale strategy, wrap/grid math, synchronized crosshair/brush/zoom, shared-canvas hit test, lazy rendering.
- `references/sparkcharts.md`: which spark form, curve choice, scale honesty, table/text/card embedding, LTTB, scale-out.
- `examples/`: `statistical-charts.html`, `parallel-coordinates.html`, `small-multiples.html`, `sparkcharts.html`. Tested by `tests/test.config.json`.
- Related: `interaction` (brushing, linked views), `rendering` (Canvas, workers, resize), `motion` (transitions between distribution views), `legibility` (palettes, axes).
