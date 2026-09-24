# Sparkcharts

Absorbed from the v2 `sparkcharts` skill. Open for word-sized charts: sparklines in text, table cells, KPI cards.

A sparkline puts the shape (trend, volatility, distribution) next to the number it explains, so the reader never looks away. No axes, legends, or chrome, which also removes the safeguards against misreading. Most of this page is about putting those back cheaply.

## Which spark

| Data | Form | Notes |
|---|---|---|
| a trend | line, endpoint dot | the canonical form |
| a trend where volume matters | area under a line | fill ~0.1 opacity, line on top |
| discrete counts, signed values | spark bar | domain `[min(0, min), max]`, 1px gaps, negatives in a second hue |
| binary outcomes | win/loss strip | fixed-height bars above/below a midline, ties as a 1px tick |
| value vs target vs qualitative bands | bullet chart (Few) | bands largest first, measure bar 40% height, target line 70% |
| value inside an interval | band + line | `area` lo→hi in light gray, line on top |
| a distribution | dot strip | x = value, dots at ~0.6 opacity |

Under ~5 data points, print the numbers instead. For precise reads ("what was March?"), use a real chart or a table.

## Curves

- `curveMonotoneX` default: smooth with no overshoot, since at this size one overshoot pixel reads as a real peak.
- `curveLinear` for discrete data where interpolation would imply values in between.
- `curveStep` for values that hold until the next change (quarters, on/off).
- Avoid `curveBasis`: it doesn't pass through the points, so it shaves peaks and troughs. Cardinal and Catmull-Rom overshoot.

## Scales are the honesty problem

- **Same metric across rows or cards → one shared y-domain**, computed once from all rows. Per-row `d3.extent` makes a 1% wobble and a 40% swing look identical, and with no axis nothing betrays it.
- Spark bars: `[0, globalMax]` so heights are proportional across rows.
- Zero baseline vs extent: zero when zero means something (counts, revenue). Extent when relative change matters (temperature, price), but then never compare heights across sparklines. Data in 98-102 on a zero baseline is a flat line.
- Always pair with a number (latest, range, or summary) in the adjacent cell. It supplies the magnitude the shape can't.
- Don't mix units in one column of sparklines.
- Operational dashboards: a fixed time window (last 1h/24h) so viewers learn the normal shape and spikes stand out. Auto-scaled x is fine for editorial sparklines read once.
- Green/red by endpoint change can contradict the shape (crashed and recovered reads "green"), and color wins.

## Sizes and embedding

- Inline in text: ~4:1 to 6:1 width:height, `vertical-align: middle; margin: 0 2px`. Keep data in `data-values` attributes and render every `.spark` span.
- Table cells: ~60×16, `white-space: nowrap`, padding `2px 6px`. An inline SVG adds line-height whitespace below: `display: block` on the SVG or `line-height: 0` on the `td`.
- KPI cards: 40-60px tall leaves room for a dashed reference line (target, zero), min/max dots, and an endpoint label. The usual layout is big number, then delta (▲/▼ %), then sparkline.
- Fill width with `viewBox` + `preserveAspectRatio="none"` + `width: 100%`. The stretch is acceptable because shape is the message, but slopes change with container width, so check narrow and wide.
- Stroke `currentColor` so it follows text color and dark mode.
- `role="img"` and an `aria-label` stating trend, min, max, latest.

## Traps

- All values equal: extent is `[v, v]` and the line sits at mid-height. Pad to `[v - 1, v + 1]`.
- Gaps drawn as continuity: `.defined(d => d != null)`. A broken line is the honest signal.
- More points than pixels (1000 in 80px): downsample with LTTB, which keeps the point in each bucket forming the largest triangle with its neighbors' picks. It preserves shape better than averaging.
- Hover: nearest index is `Math.round(x.invert(px))` on an index scale.

## Scale-out

| Sparklines on page | Technique |
|---|---|
| < 200 | SVG |
| 200-1000 | Canvas per sparkline (mind DPR) |
| 1000+ | Canvas + virtual scroll |
