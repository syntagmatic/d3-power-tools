---
name: scales
description: "D3.js axes and scales: log vs symlog tradeoffs, band vs point, time gaps in financial data, responsive tick counts, label collision, broken axes, dual-y, .nice() pitfalls, and axis transitions."
---

# Axes and Scales

A reader's first question is "how much?" Scales answer it — but the wrong scale lies. Log scales hide zeros. Linear scales bury orders of magnitude. Time scales allocate pixels to weekends nobody traded on. Every scale choice is an editorial decision about what the viewer can see.

Related skills: `data-gathering` (type coercion before scaling), `brushing` (brush extents map through scales), `motion` (scale domain transitions), `canvas` (drawing axes on Canvas), `responsive` (container sizing and DPI).

## Log vs Symlog: Zeros Kill Log

The most common scale mistake: using `scaleLog` on data that contains zeros. Log(0) is undefined, so D3 silently returns `NaN` — your points vanish without an error.

```js
// BROKEN: data has zero values, dots silently disappear
const y = d3.scaleLog([1, d3.max(data, d => d.value)], [height - marginBottom, marginTop]);
// → data points where value === 0 render at NaN

// FIX: scaleSymlog handles zero and negatives via sign(x) * log(1 + |x/c|)
const y = d3.scaleSymlog(d3.extent(data, d => d.value), [height - marginBottom, marginTop])
  .constant(1); // increase for wider linear region around zero
```

**When to use log:** Data is strictly positive, spans 2+ orders of magnitude, and you want to reveal structure in the small values that linear would crush. Default ticks are powers of 10 — for SI labels: `.ticks(5, ".0s")`.

**When to use symlog:** Data includes zeros or negatives, or you can't guarantee strictly positive values. The `constant` parameter controls where the scale transitions from linear (near zero) to logarithmic — increase it if your data clusters near zero and the log region compresses them.

**When to use neither:** If your range spans less than one order of magnitude, linear is clearer. Log and symlog distort proportional comparisons — a bar chart on a log scale is a lie because bar length no longer maps to quantity.

## Band vs Point

Both are for categorical data. The difference: bands have width, points don't.

```js
// Band: rectangles — bar charts, heatmap cells
const x = d3.scaleBand(categories, [marginLeft, width - marginRight])
  .padding(0.2);
// x(category) → left edge, x.bandwidth() → bar width

// Point: dots — dot plots, parallel coordinates, lollipops
const x = d3.scalePoint(categories, [marginLeft, width - marginRight])
  .padding(0.5);
// x(category) → center point, no bandwidth
```

Use `scaleBand` when the mark has extent (bars, cells). Use `scalePoint` when the mark is positioned at a single coordinate (dots, line endpoints). Band order matches the domain array — sort explicitly if you want alphabetical: `.domain([...categories].sort())`.

## Time Gaps: Weekends in Financial Data

A `scaleUtc` maps time uniformly — every hour gets equal pixels. For financial data, that means weekends and holidays consume 28% of the x-axis showing nothing. The viewer sees cliffs where Friday meets Monday.

### Band approach (recommended)

Treat each trading day as a categorical position. No gaps, equal spacing:

```js
const tradingDays = data.map(d => d.date);
const x = d3.scaleBand(tradingDays, [marginLeft, width - marginRight]).padding(0.1);

// Show only Mondays (or every Nth day) as tick labels
d3.axisBottom(x)
  .tickValues(tradingDays.filter(d => d.getUTCDay() === 1))
  .tickFormat(d3.utcFormat("%b %-d"));
```

### Index approach

Map data index to pixels. Simpler for line charts where you don't need band width:

```js
const x = d3.scaleLinear([0, data.length - 1], [marginLeft, width - marginRight]);
d3.axisBottom(x).ticks(8)
  .tickFormat(i => {
    const idx = Math.round(i);
    return idx >= 0 && idx < data.length ? d3.utcFormat("%b %-d")(data[idx].date) : "";
  });
```

Both approaches eliminate visual gaps but sacrifice proportional time spacing — a 3-day holiday looks the same as a weekend. If that matters (e.g., interest accrual), use `scaleUtc` with visual markers for non-trading periods.

**When not to use gap removal:** Event-based data where the gaps themselves are meaningful (sensor outages, market halts). Hiding the gap hides the story.

## Responsive Tick Counts

Tick count isn't a formatting detail — it's a design decision. Too many ticks and labels overlap; too few and the reader can't decode values. The right count depends on available pixels.

```js
const ro = new ResizeObserver(([entry]) => {
  const innerWidth = entry.contentRect.width - marginLeft - marginRight;
  const tickCount = Math.max(2, Math.floor(innerWidth / 80));
  x.range([marginLeft, entry.contentRect.width - marginRight]);
  xAxisGroup.call(d3.axisBottom(x).ticks(tickCount));
});
ro.observe(container.node());
```

The 80px divisor is a starting point. Adjust per content:

| Axis type | Pixels per tick | Why |
|-----------|:-:|---|
| Numeric | 60–100 | Short labels ("1.2M") need less room |
| Time | 100–150 | Date labels ("Jan 15") are wider |
| Categorical | band ≥ 20px | Below this, labels are unreadable even rotated |

`d3.axis.ticks(n)` is a *suggestion* — D3 picks "nice" intervals and may return 4–6 ticks when you asked for 5. Use `.tickValues([...])` when you need exact control.

## scaleUtc over scaleTime

Always use `scaleUtc` unless you need local-time display. `scaleTime` makes DST transitions create 23- or 25-hour days — uniform hourly data becomes visually uneven, and the viewer has no way to know the axis itself is distorted.

## .nice() — When and When Not

`.nice()` rounds the domain to clean tick values. Use it for scatter/line charts where exact endpoints don't matter. Skip it when:

- **Bar charts at zero:** `.nice()` can push the lower bound negative, breaking the baseline. (In practice `[0, max].nice()` keeps zero — but `[-2, max].nice()` might round to -10.)
- **Domain has semantic meaning:** 0–100% should stay 0–100%.
- **User-selected range:** A brush extent of [23.4, 87.1] should stay exact.

## Label Collision Avoidance

When labels overlap, try fixes in this order (lightest touch first):

1. **Fewer ticks** — reduce count via `.ticks(n)` or responsive calculation
2. **Truncate with tooltip** — `d.length > 12 ? d.slice(0, 11) + "…" : d` with a `<title>` for the full text
3. **Stagger on alternating lines** — `dy` offset by parity: `i % 2 === 0 ? "1em" : "2.2em"`
4. **Rotate 45°** — last resort; rotated text is slower to read than horizontal

```js
// Rotation pattern
axisGroup.selectAll("text")
  .attr("transform", "rotate(-45)")
  .attr("text-anchor", "end")
  .attr("dx", "-0.5em").attr("dy", "0.3em");
```

## Dual-Y Axes

Two y-axes for datasets with different units. Dangerous — the viewer assumes the two series are comparable, and you control the illusion by choosing where each scale starts. Use sparingly and honestly.

```js
const yLeft = d3.scaleLinear([0, d3.max(data, d => d.temp)], [height - marginBottom, marginTop]).nice();
const yRight = d3.scaleLinear([0, d3.max(data, d => d.precip)], [height - marginBottom, marginTop]).nice();
```

Rules that prevent misleading dual-y charts:
- **Color-code** each axis to match its data series — otherwise the reader can't tell which line maps to which scale.
- **Force both domains to include zero** — prevents manufacturing false correlations by shifting baselines.
- **Don't use dual-y when both variables share the same unit** — use a single scale.
- **Consider a scatter plot instead** — if the point is correlation between two variables, plot one against the other directly.

**When not to use dual-y:** When you find yourself adjusting one scale's range to "line up" with the other. That's fabricating a visual correlation.

## Broken / Discontinuous Axes

When one outlier forces a scale that crushes all other values. Build piecewise scales for each segment, draw a zigzag break symbol between them:

```js
function brokenScale(ranges, pixelRanges) {
  const scales = ranges.map((domain, i) =>
    d3.scaleLinear(domain, pixelRanges[i])
  );
  const scale = (value) => {
    for (let i = 0; i < ranges.length; i++) {
      const [lo, hi] = ranges[i];
      if (value >= lo && value <= hi) return scales[i](value);
    }
    return value < ranges[0][1] ? scales[0](value) : scales.at(-1)(value);
  };
  scale.scales = scales;
  return scale;
}
```

**When not to break the axis:** When the outlier *is* the story. A broken axis makes 900 look close to 50 — if the point is that 900 is extreme, a log scale or annotation preserves the shock.

## Multi-Level Time Ticks

Show different formats at different granularities — days get "15", months get "Mar", years get "2024":

```js
const multiFormat = (date) => {
  if (d3.utcMonth(date) < date) return d3.utcFormat("%-d")(date);
  if (d3.utcYear(date) < date)  return d3.utcFormat("%b")(date);
  return d3.utcFormat("%Y")(date);
};
d3.axisBottom(x).tickFormat(multiFormat);
```

## Grid Lines

Extend ticks across the chart area — use a second axis call with no labels:

```js
svg.append("g")
  .attr("transform", `translate(${marginLeft},0)`)
  .call(d3.axisLeft(y).tickSize(-(width - marginLeft - marginRight)).tickFormat(""))
  .call(g => g.select(".domain").remove())
  .call(g => g.selectAll("line").attr("stroke", "#e0e0e0").attr("stroke-dasharray", "2,2"));
```

Grid lines help the reader trace values but add clutter. Use them for scatter plots (both axes) and line charts (y-axis only). Skip them for bar charts where the bars themselves encode position.

## Axis Transitions

Update the scale domain first, then transition axis and data elements together so nothing uses a stale scale:

```js
y.domain(newDomain).nice();
const t = svg.transition().duration(500);
t.select(".y-axis").call(d3.axisLeft(y));        // ticks slide automatically
t.selectAll(".bar")
  .attr("y", d => y(d.value))
  .attr("height", d => y(0) - y(d.value));
```

D3's axis component uses a data join internally, so `.call(axis)` is safe to repeat. But manually appended label text will duplicate — guard with `.selectAll(".axis-label").data([0]).join("text")`.

## Common Pitfalls

1. **Axis labels are manual.** D3 doesn't generate axis titles — append a `<text>` element yourself. Every axis without a label forces the reader to guess units.

2. **Tick count is a suggestion.** `.ticks(5)` may produce 4–6 ticks. Use `.tickValues([...])` for exact control.

3. **Band scale with unsorted domain.** Band order matches the domain array. The viewer expects alphabetical or value-sorted — unsorted categories look like noise.

4. **Responsive axes without deduplication.** `.call(axis)` is safe to repeat, but manually appended axis labels will duplicate each resize. Use a data join or `.selectAll().data([0]).join()`.

5. **scaleLinear with bar charts not including zero.** Bar length must be proportional to value. A bar from 50 to 80 looks like 80 is almost double 50 if the baseline is at 50. Always include zero.

## References

- [D3 Scales](https://d3js.org/d3-scale) — scale API
- [D3 Axes](https://d3js.org/d3-axis) — axis generation
- [Dual-Axis Charts](https://blog.datawrapper.de/dualaxis/) — Lisa Charlotte Muth on when dual-y is appropriate
- [Broken Y-Axis](https://blog.datawrapper.de/broken-y-axis/) — Datawrapper's axis break design analysis
- [d3fc Discontinuous Scale](https://d3fc.io/api/scale/discontinuous-scale.html) — library for financial time gaps
