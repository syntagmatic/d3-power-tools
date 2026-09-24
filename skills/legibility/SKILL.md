---
name: legibility
description: "Make a D3 chart readable and honest: scale choice (log/symlog, band/point, UTC, diverging, quantile/quantize/threshold/Jenks), axes and ticks, broken and dual-y axes, color palettes (Tol, Viridis, ColorBrewer, bivariate), colorblind safety and contrast, alpha/overdraw, canvas compositing, dark mode, pattern fills and hatching for redundant encoding, annotations, callouts, leader lines, label collision, and tooltips."
---

# Legibility

Every chart makes three editorial choices before anyone reads it: how value maps to position (scale), how category or magnitude maps to color (and texture), and what the chart tells you to look at (annotation). Models get the API right and the defaults wrong. This skill is about the defaults.

Work through it in order: pick the scale, pick the color, then decide what to say.

## Scale decisions

| If the data... | Use | Not |
|---|---|---|
| is strictly positive and spans 2+ orders of magnitude | `scaleLog`, ticks `.ticks(5, ".0s")` | log on anything with zeros (renders at NaN, silently) |
| spans orders of magnitude and has zeros or negatives | `scaleSymlog().constant(c)`, c ≈ typical small value | log with a fudge `+1` |
| spans less than one order of magnitude | `scaleLinear` | log for "looks fancier" |
| is dates | `scaleUtc` + `d3.utcParse` | mixing `new Date("2024-03-01")` (UTC) with `d3.timeParse` (local): labels shift a day |
| is trading days / event sequence with meaningless gaps | `scaleBand` over the dates, or an index scale with date tick labels | `scaleUtc` showing empty weekends |
| has gaps that *are* the story (outages, halts) | `scaleUtc` + visible gap marks | gap removal |
| is categories on bars or cells | `scaleBand`, domain sorted by value or name | unsorted domain (reads as noise) |
| is categories on dots or line ends | `scalePoint` | band |
| has a meaningful center (anomaly, margin, profit) | `scaleDiverging([-m, 0, m])`, symmetric | `[min, 0, max]` unless the two sides really are different quantities: asymmetric domains saturate the short side and exaggerate it |
| must be binned for a choropleth | see the classification table below | continuous color without a legend showing breaks |

### Classification (choropleths, binned color)

| Method | Scale | Say it when |
|---|---|---|
| Equal interval | `scaleQuantize(extent, colors)` | "how far above/below" matters |
| Equal count | `scaleQuantile(allValues, colors)` | "which quintile" matters. **Always pair with a histogram**: bimodal and uniform data produce identical quantile maps |
| Manual breaks | `scaleThreshold(breaks, colors)` | domain has meaningful cutoffs (poverty line, AQI bands) |
| Natural breaks | Jenks (simple-statistics) → `scaleThreshold` | clusters exist but you don't know where |

### Axis rules

- Bars start at zero. Always. A bar is a length.
- `.nice()` for scatter and line domains; skip it for fixed-meaning domains (0-100%), brush extents, and bar charts whose lower bound could get pushed negative.
- Ticks by pixel budget, not a constant: numeric ~70px/tick, dates ~120px/tick, categorical bands need ≥20px or the labels go. `.ticks(n)` is a hint, so use `.tickValues()` when exact.
- Every axis gets a title with units. D3 never draws one.
- Label collision: fewer ticks → truncate with `<title>` → stagger → rotate 45° (last resort).
- Grid lines: y-only for line charts, both for scatter, none for bars. Lighter than the data.

### Dual-y and broken axes: only with guards

- **Dual-y** only for different units. Color each axis like its series. Both domains include zero. If you're tuning one range to make the lines "line up," you're fabricating a correlation, so plot x-vs-y instead.
- **Broken axis** only when an outlier crushes the rest *and* the outlier isn't the point. Draw an explicit break mark. If the outlier is the story, use log or an annotation instead.

## Color decisions

Color is a channel with limited bandwidth. Lightness carries order; hue carries identity. **Test every palette in grayscale**: if order disappears, the scale is broken.

| Need | Default | Why |
|---|---|---|
| Sequential magnitude | `interpolateViridis` (light bg), `interpolateMagma` (dark bg) | lightness-monotonic, CVD-safe |
| Sequential, max CVD safety | `interpolateCividis` | blue-yellow only |
| Diverging | Tol BuRd / Sunset, or `interpolateRdBu` | neutral midpoint, tested |
| Categorical ≤7, CVD-safe | **Tol Bright** | `schemeCategory10` and `Set1` merge under deuteranopia |
| Categorical 8-9, dense marks | Tol Muted | |
| 2-3 categories | Tol High-Contrast | |
| >9 categories | Don't. Top N + "other", or direct labels | nobody can match 12 hues to a legend |
| Two variables in one color | Stevens 3×3 bivariate grid | blended scales produce mud |

Exact hex arrays: `references/color.md` and `scripts/tol-palettes.js`. Don't approximate Tol colors from memory.

- Interpolate in Lab or HCL, never RGB (muddy midpoints). HCL through a white/black midpoint has undefined hue, so use the built-in diverging interpolators or Lab there.
- Small marks look paler than the legend swatch: boost HCL chroma ~20 and drop L ~5 for dots and thin lines.
- Anything that goes through a d3 scale or interpolator must be a resolved color, never `var(--x)`.
- **Dark backgrounds**: sequential ramps run dark→bright (magma, inferno, viridis work natively). Categorical colors keep hue, raise L to ~60-75, and drop chroma slightly. Don't invert lightness.
- Text contrast: WCAG 2 ≥4.5:1 for labels (≥3:1 large). On dark themes the WCAG ratio overstates contrast, so check APCA (Lc ≥60 axis text, ≥45 large callouts).
- Unknown/missing data gets its own color outside the ramp (Tol specifies one per scheme), not the ramp's first stop.

### Overdraw and alpha

Stacked alpha compounds: `result = 1 - (1 - a)^n`. To hit target opacity T at n overlaps: `a = 1 - (1 - T)^(1/n)`. Rough defaults: 0.02-0.05 for 10K+ marks, 0.08-0.15 for 1K-10K. `globalAlpha` multiplies with rgba alpha. Additive density (`globalCompositeOperation = "lighter"`) needs a dark background, and always reset to `source-over` (or `save/restore`). SVG `mix-blend-mode` needs `isolation: isolate` on the parent or it blends with the page.

## Texture (redundant encoding)

Use pattern fills when color alone can't carry it: CVD readers, print, grayscale. Otherwise they're noise.

- Only on areas ≥ ~15×15px (bars ≥20px wide). Max 5-6 patterns.
- Categorical: vary pattern *type* (lines / dots / cross / waves), with orientations ≥30° apart. `/` vs `\` is too subtle.
- Ordinal: one pattern type, vary *spacing* (12px → 3px). Denser reads as more. Pair with lightness so both channels agree.
- `patternUnits="userSpaceOnUse"` always. `objectBoundingBox` scales density with shape size, which readers take as data.
- Mark color by background lightness: dark marks `rgba(0,0,0,.2-.3)` above L*55, white marks `rgba(255,255,255,.35-.45)` below.
- Namespace pattern ids per chart. With a `<base>` tag, `url(#id)` breaks, so use `url(${location.pathname}#id)`.
- Canvas: build tiles at `size*dpr`, then `pattern.setTransform(new DOMMatrix().scale(1/dpr))`, or they blur.

## Annotation decisions

A chart without annotation has no argument. A chart with ten has no focus.

1. **Headline states the finding**, not the topic. Subtitle gives scope. Source line last.
2. **1-3 callouts**, on what's surprising: inflections, crossovers, outliers, first/last. More than 3 is a list.
3. **Reference lines** for "compared to what" (target, average, threshold), labeled in place.
4. **Direct labels** instead of a legend when there are ≤ ~6 series and room at the line ends.
5. **Tooltips** for everything else. Never repeat a callout in a tooltip.

- **Highlight by quieting**: desaturate and fade non-focus marks (`#ccc`, opacity .3) instead of making the focus louder.
- Leader lines are thinner and lighter than data (0.7-1px, muted), with no arrowheads unless direction means something.
- Store annotations as data in data coordinates (`{x, y, dx, dy, title, priority}`) and recompute pixels on resize. Drop `priority > 1` on narrow screens. Flip `dx/dy` when a note would overflow.
- Labels over varied backgrounds need a halo (`paint-order: stroke` with a background-colored stroke) or a backing rect.
- `getComputedTextLength()`/`getBBox()` return 0 before the node is in the DOM.
- Exploratory dashboards and small-multiples grids: skip callouts and let tooltips and brushing do it.

### Label collision

| Density | Method |
|---|---|
| Few labels, sparse | greedy: try 8 offsets, keep the first free slot |
| Moderate, need neat result | rectangular-collision force, run ~120 ticks offline (`forceCollide` is circular and wrong for text) |
| Many points, only some labeled | label the Voronoi-cell-largest points, tooltip the rest |

Code for both is in `references/annotation.md`.

### Tooltips

HTML div, `pointer-events: none`, clamped to the viewport. For small or dense marks, hit-test with `d3.Delaunay.find` on a single overlay and anchor the tooltip to the *data point*, not the cursor. Coalesce `pointermove` work to one update per animation frame.

## References

- `references/scales.md`: log/symlog, time gaps (band and index code), piecewise broken scale, multi-level time ticks, axis transitions, diverging variants, Jenks.
- `references/color.md`: Tol hex arrays with bad-data colors, Stevens bivariate grids, CVD types, WCAG/APCA, compositing modes, OKLCH generation.
- `references/visual-texture.md`: texton-based pattern set, pattern function, color+pattern choropleth bins, Canvas atlases, print rules, Voronoi stippling.
- `references/annotation.md`: connector geometry, rect-collision force, greedy placer, text wrapping, Canvas callouts, step-sequenced annotations.
- `scripts/`: `tol-palettes.js`, `colorblind-sim.js` (Brettel/Viénot), `alpha-solver.js`.
- `examples/`: color legend, compositing gallery, texture gallery, annotations and labels, axes and scales. Tested by `tests/test.config.json`.
