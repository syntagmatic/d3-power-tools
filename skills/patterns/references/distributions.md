# Distributions

Absorbed from the v2 `distributions` skill. Open when building a box, violin, raincloud, ridgeline, beeswarm, letter-value, or QQ plot, or when choosing a KDE bandwidth.

## What each form hides

| Chart | Best when | Hides |
|---|---|---|
| Histogram | small n, bin structure matters | smoothness is an artifact of bin width |
| Box plot | comparing medians across 5+ groups | shape: bimodal and unimodal look identical |
| Letter-value | n > 200, tails matter | shape (less than a box does) |
| Violin | shape matters (bimodal, skew) | individuals; KDE invents shape below n ≈ 30 |
| Raincloud | shape + points + summary, n 20-2000, 2-8 groups | nothing, but costs space |
| Ridgeline | 6+ *ordered* groups, trend across them | precise comparison (no shared baseline) |
| Beeswarm | individuals matter, n < ~500/group | nothing, but layout cost grows fast |
| Strip/jitter | quick look, any n | overplots past ~200/group without alpha |
| Overlaid density | 2-4 groups | individuals; bandwidth shapes what you see |

Box plot trap: a normal and a bimodal sample with the same median and IQR draw the same box. Until unimodality is confirmed, overlay points or use a violin. Discrete data (children per family) should never be smoothed: KDE puts density at 3.5.

## KDE

```js
const gaussian = x => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
const kde = (kernel, bw, data) => xs => xs.map(x => [x, d3.mean(data, v => kernel((x - v) / bw)) / bw]);

// Silverman. IQR is 0 for heavily tied data, so fall back to the std or bandwidth is 0 (NaN density).
function silverman(values) {
  const s = Float64Array.from(values).sort();
  const std = d3.deviation(s), iqr = d3.quantileSorted(s, 0.75) - d3.quantileSorted(s, 0.25);
  const spread = iqr > 0 ? Math.min(std, iqr / 1.34) : std;
  return 0.9 * spread * s.length ** -0.2;
}
```

- Evaluate over `extent ± 3·bw` (~200 points) so tails aren't truncated, then clip to the possible range for bounded data (durations ≥ 0, scores ≤ 100). Waskom's "defensive" rule.
- Silverman over-smooths multimodal data: halve it when you suspect two modes. Log-transform very skewed data before KDE. For n < 30, widen 20-50% or use a histogram.
- Bandwidth is editorial. Too small fabricates modes; too large merges real ones.

## Box plot details

- `d3.quantile` works on unsorted input (quickselect). If you've already sorted for fences and whiskers, use `d3.quantileSorted`.
- Tukey fences: `q1 - 1.5·IQR`, `q3 + 1.5·IQR`. Whiskers end at the most extreme data point *inside* the fences, not at the fence.
- Other whiskers: min/max (no outlier flagging), 5th/95th percentile (same definition across groups), ±1-2 SD only when the audience thinks in SDs (misleading for skew). Say which one in the caption.
- Notch half-width `1.57 · IQR / √n` (McGill et al.): non-overlapping notches ≈ medians differ at ~95%. Draw it as a polygon pinched ~15% of box width at the median. If the notch exceeds a hinge, the box "folds," which means n is too small for notches.
- Box + points: outliers get drawn twice. Skip the outlier markers or filter them from the overlay.

## Violins and density scaling

- Width normalization is a hidden claim. Per-group max width compares shape but makes n=10 look as confident as n=10,000. A shared density scale makes width mean data volume. Width ∝ √n is a good default when group sizes differ by more than 3×.
- Split violin: group A as `area().x0(0).x1(d => -w(d[1]))`, group B mirrored positive.
- Brushed subsets: recomputing KDE on 5 of 200 points with the same bandwidth spikes 10× taller. Multiply density by `subset.length / group.length` so height means proportion.
- Overlaid densities: widest first, or `fill-opacity: .3` with `mix-blend-mode: multiply`. More than 4 groups: ridgeline.

## Raincloud

Per group band (horizontal reads best): half-violin above a baseline at ~45% of the band, box in the middle, seeded-jitter strip below. Allen et al. 2019. For discrete or small-n data, use a histogram half instead of KDE. Not below n = 10, not above ~5000 (use violin + box), not beyond 8 groups (use ridgelines).

## Ridgeline

`ridgeHeight = band.step() * (1 + overlap)`; area baseline at `band(key) + band.bandwidth()`, density drawn upward (`y1 = -h(d)`). Overlap 0 is small multiples, 0.3-0.5 readable, 0.7-1 dramatic. Each ridge reaches into the row above, so **draw the top row first and the bottom row last** so lower ridges sit in front; semi-opaque fills help. Only for ordered categories: vertical stacking implies order.

## Beeswarm and jitter

- Dodge layout (no simulation): sort by value, place each point at `x(value)`, and search outward from the baseline (0, +δ, −δ, +2δ, ...) for the first y that clears every placed circle by `2r`. Only neighbors within `2r` in x can collide, so keep placed points in x order and scan just that window.
- Force layout: run it headless. The default schedule cools to `alphaMin` (0.001) in ~300 ticks: `n = Math.ceil(Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay()))`. Stopping at 120 ticks (alpha ≈ 0.06) leaves overlaps.
- Jitter with `d3.randomLcg(seed)` so points don't jump on re-render. Width ~60% of the band.
- Violin-constrained jitter: jitter half-width = `scale(density at the point's value)`, so the strip takes the violin's shape.
- Random jitter hides clustering; if density matters use a swarm or violin. Past ~500 points per group, switch to density or Canvas with alpha.

## Letter-value plot

Box plots flag hundreds of expected tail points as "outliers" at large n. Letter values (Hofmann, Wickham, Kafadar 2017) nest boxes at depths M, F (fourths), E (eighths), D, C, B, A, Z, Y, X... Tukey's stopping rule keeps `floor(log2 n) - 3` levels beyond the median, leaving ~5-8 points in each tail as outliers.

```js
function letterValues(sorted) {
  const n = sorted.length;
  const at = d => { const i = Math.floor(d) - 1; return d === Math.floor(d) ? sorted[i] : (sorted[i] + sorted[i + 1]) / 2; };
  let depth = (1 + n) / 2;
  const levels = [{ letter: "M", lower: at(depth), upper: at(depth) }];
  const letters = "FEDCBAZYXW";
  const k = Math.min(Math.max(0, Math.floor(Math.log2(n)) - 3), letters.length);
  for (let i = 0; i < k; i++) {
    depth = (1 + Math.floor(depth)) / 2;
    if (depth < 1) break;
    levels.push({ letter: letters[i], lower: at(depth), upper: at(n + 1 - depth) });
  }
  return levels;
}
```

Render as nested rects, widest at the center, sequential color by depth. Below n ≈ 100 use a plain box.

## QQ plot

- Theoretical quantiles on x, sample on y (swapping is the common mistake). Plotting position `p = (i + 0.5) / n` (Hazen, i from 0); standardize the sample.
- `normalQuantile(p)` isn't in D3: use the Beasley-Springer-Moro or Acklam rational approximation.
- Reading: on the diagonal means the reference fits. Heavy tails bend down at left and up at right. Skew bends one way throughout.
- 95% pointwise band at theoretical quantile z: `se = √(p(1-p)/n) / φ(z)`, band `z ± 1.96·se`, with φ the standard normal density.

## Transitions between views

Precompute positions for every view (strip, swarm, box), then interpolate `cx`/`cy`. The `motion` skill covers staging.
