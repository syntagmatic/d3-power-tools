---
name: axes-and-scales
description: "D3.js axes and scales for production charts: scale selection (linear, log, symlog, pow, time, band, point), axis generation and customization, custom tick formats, responsive tick counts with ResizeObserver, label collision avoidance (rotation, staggering, ellipsis), broken/discontinuous axes, dual-y axes with independent scales, time scales with gaps (weekends, holidays), ordinal grouping and nested axes, axis transitions, grid lines, and Canvas axis rendering. Use this skill when the user needs axes, scales, tick formatting, label layout, dual-y charts, log scale gotchas, broken axes, time axis gaps, responsive axes, or any scale-to-visual-encoding pipeline."
---

# Axes and Scales

The scale→axis pipeline is the backbone of quantitative charts. A scale maps data to visual properties; an axis makes that mapping legible.

Related skills: `data-preparation` (type coercion before scaling), `brushing-and-selection` (brush extents map through scales), `animated-transitions` (scale domain transitions), `canvas-rendering` (drawing axes on Canvas).

```
raw data → d3.scale*() → pixel coordinates
                ↓
           d3.axis*() → tick marks, labels, grid lines
                ↓
           collision avoidance → readable labels
```

## Scale Selection Guide

| Data type | Scale | When to use |
|-----------|-------|------------|
| Continuous numeric | `scaleLinear` | Default for most quantitative data |
| Wide range (2+ orders) | `scaleLog` | Domain must be > 0 |
| Includes zero + wide range | `scaleSymlog` | Like log but handles zero and negatives |
| Emphasize extremes | `scalePow` / `scaleSqrt` | Area encoding (sqrt), perceptual correction |
| Time | `scaleUtc` | Prefer over `scaleTime` — avoids DST surprises |
| Categorical | `scaleBand` | Bar charts — discrete bands with padding |
| Categorical, no width | `scalePoint` | Dot plots, parallel coordinates |
| Categorical → continuous | `scaleOrdinal` | Categories to colors/shapes |
| Binned continuous | `scaleQuantize` | Equal-width bins |
| Rank-based | `scaleQuantile` | Equal-count bins |

### scaleLinear

```js
const x = d3.scaleLinear([0, d3.max(data, d => d.value)], [marginLeft, width - marginRight]);

// .nice() pads domain to round numbers — good for scatter, skip for bar charts
x.domain(d3.extent(data, d => d.value)).nice();
```

Always include zero for bar charts (lengths must be proportional).

### scaleLog

```js
const y = d3.scaleLog([1, d3.max(data, d => d.value)], [height - marginBottom, marginTop]);
```

Domain must be > 0. If data has zeros: filter them, clamp to 1, or use `scaleSymlog`. Default ticks are powers of 10 — for SI labels: `.ticks(5, ".0s")`.

### scaleSymlog

Symmetric log: handles zero and negatives via `sign(x) * log(1 + |x/c|)`. The `constant` parameter controls the linear region around zero.

```js
const y = d3.scaleSymlog(d3.extent(data, d => d.value), [height - marginBottom, marginTop])
  .constant(1); // increase for wider linear region
```

### scaleUtc / scaleTime

```js
const x = d3.scaleUtc(d3.extent(data, d => d.date), [marginLeft, width - marginRight]);
```

Always use `scaleUtc` unless you need local time display. `scaleTime` makes DST transitions create 23/25-hour days, distorting uniform data.

### scaleBand / scalePoint

```js
const x = d3.scaleBand(data.map(d => d.category), [marginLeft, width - marginRight])
  .padding(0.2);
// x(d.category) → left edge, x.bandwidth() → bar width, x.step() → bandwidth + padding

const x = d3.scalePoint(data.map(d => d.category), [marginLeft, width - marginRight])
  .padding(0.5);
```

## Axis Generation

```js
svg.append("g")
  .attr("transform", `translate(0,${height - marginBottom})`)
  .call(d3.axisBottom(x));

svg.append("g")
  .attr("transform", `translate(${marginLeft},0)`)
  .call(d3.axisLeft(y));
```

### Controlling Ticks

```js
d3.axisBottom(x)
  .ticks(5)                          // suggest ~5 ticks (D3 may adjust)
  .tickValues([0, 25, 50, 75, 100])  // exact tick positions
  .tickFormat(d3.format(",.0f"))     // thousands separator, no decimals
  .tickSize(6)                       // tick length
  .tickSizeOuter(0)                  // suppress end ticks
  .tickPadding(8);                   // gap between tick and label
```

### Grid Lines

Extend ticks across the chart area — use a second axis call with no labels:

```js
svg.append("g")
  .attr("transform", `translate(${marginLeft},0)`)
  .call(d3.axisLeft(y)
    .tickSize(-(width - marginLeft - marginRight))
    .tickFormat("")
  )
  .call(g => g.select(".domain").remove())
  .call(g => g.selectAll("line").attr("stroke", "#e0e0e0").attr("stroke-dasharray", "2,2"));
```

### Removing the Domain Line

```js
.call(g => g.select(".domain").remove())
// or CSS: .y-axis .domain { display: none; }
```

## d3.format Cheat Sheet

| Pattern | Example | Use for |
|---------|---------|---------|
| `","` | 1,234,567 | General integers |
| `",.2f"` | 1,234.50 | Currency, precise values |
| `".2s"` | 1.2M | SI abbreviation |
| `".0%"` | 46% | Percentages (input 0–1) |
| `"+.1f"` | +3.1 | Signed/diverging data |
| `"~s"` | 1.5k | SI, trim trailing zeros |
| `"$,.0f"` | $1,234 | US dollars |

### Multi-Level Time Ticks

Different formats at different granularities:

```js
const multiFormat = (date) => {
  if (d3.utcMonth(date) < date) return d3.utcFormat("%-d")(date);
  if (d3.utcYear(date) < date)  return d3.utcFormat("%b")(date);
  return d3.utcFormat("%Y")(date);
};
d3.axisBottom(x).tickFormat(multiFormat);
```

## Label Collision Avoidance

Strategies in order of preference:

### Rotate Labels

```js
axisGroup.selectAll("text")
  .attr("transform", "rotate(-45)")
  .attr("text-anchor", "end")
  .attr("dx", "-0.5em").attr("dy", "0.3em");
```

### Stagger on Alternating Lines

```js
axisGroup.selectAll("text")
  .attr("dy", (d, i) => i % 2 === 0 ? "1em" : "2.2em");
axisGroup.selectAll(".tick line")
  .attr("y2", (d, i) => i % 2 === 0 ? 6 : 18);
```

### Truncate with Ellipsis

```js
axisGroup.selectAll("text")
  .text(d => d.length > 12 ? d.slice(0, 11) + "\u2026" : d)
  .append("title").text(d => d);
```

### Adaptive: Measure and Decide

Measure label bounding boxes after rendering, check for overlap, then apply lightest-touch fix — try truncation first, then rotation if still overlapping.

## Responsive Tick Counts

```js
const ro = new ResizeObserver(([entry]) => {
  const innerWidth = entry.contentRect.width - marginLeft - marginRight;
  const tickCount = Math.max(2, Math.floor(innerWidth / 80)); // ~80px per tick
  x.range([marginLeft, entry.contentRect.width - marginRight]);
  xAxisGroup.call(d3.axisBottom(x).ticks(tickCount));
});
ro.observe(container.node());
```

| Axis type | Pixels per tick |
|-----------|:-:|
| Numeric | 60–100 |
| Time | 100–150 |
| Categorical | band width ≥ 20px |

## Broken / Discontinuous Axes

For data with gaps or focusing on two separate ranges. Build piecewise scales for each segment and draw a zigzag break symbol between them:

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

// Usage:
const broken = brokenScale([[0, 50], [900, 1000]], [[marginLeft, 200], [220, width - marginRight]]);

// Render one axis per sub-range, break symbol in the gap
broken.scales.forEach(sub => {
  svg.append("g").attr("transform", `translate(0,${height - marginBottom})`).call(d3.axisBottom(sub));
});
```

## Dual-Y Axes

Two y-axes for datasets with different units. Use sparingly — can mislead if scales are chosen to create false correlations.

```js
const yLeft = d3.scaleLinear([0, d3.max(data, d => d.temperature)], [height - marginBottom, marginTop]).nice();
const yRight = d3.scaleLinear([0, d3.max(data, d => d.precipitation)], [height - marginBottom, marginTop]).nice();

svg.append("g").attr("transform", `translate(${marginLeft},0)`)
  .call(d3.axisLeft(yLeft))
  .call(g => g.selectAll("text, .tick line").attr("fill", "#e15759"));

svg.append("g").attr("transform", `translate(${width - marginRight},0)`)
  .call(d3.axisRight(yRight))
  .call(g => g.selectAll("text, .tick line").attr("fill", "#4e79a7"));
```

Color-code axes to match their data series. Force both domains to include zero to prevent misleading gaps. Don't use dual-y when both variables share the same unit or when a scatter plot would be more honest.

## Time Scales with Gaps

Financial/business data has weekends, holidays. A standard `scaleUtc` allocates pixels to empty periods.

### Band-Based Approach (Recommended)

Treat each trading day as a categorical position:

```js
const tradingDays = data.map(d => d.date);
const x = d3.scaleBand(tradingDays, [marginLeft, width - marginRight]).padding(0.1);

d3.axisBottom(x)
  .tickValues(tradingDays.filter((d, i) => i % Math.ceil(tradingDays.length / 10) === 0))
  .tickFormat(d3.utcFormat("%b %-d"));
```

### Linear Index Approach

Map data index to pixels, format ticks as dates:

```js
const x = d3.scaleLinear([0, data.length - 1], [marginLeft, width - marginRight]);
d3.axisBottom(x).ticks(8)
  .tickFormat(i => {
    const idx = Math.round(i);
    return idx >= 0 && idx < data.length ? d3.utcFormat("%b %-d")(data[idx].date) : "";
  });
```

## Ordinal Grouping and Nested Axes

For grouped bar charts with hierarchical categories (e.g., quarters within years):

```js
const x0 = d3.scaleBand(groups, [marginLeft, width - marginRight]).paddingInner(0.1);
const x1 = d3.scaleBand(subgroups, [0, x0.bandwidth()]).padding(0.05);
```

Render the inner axis (quarter labels) inside each outer tick group, the outer axis (year labels) below with heavier font weight. Add dashed separator lines between groups.

## Axis Transitions

```js
y.domain(newDomain).nice();
const t = svg.transition().duration(500);
t.select(".y-axis").call(d3.axisLeft(y));        // ticks enter/exit/slide automatically
t.selectAll(".bar")
  .attr("y", d => y(d.value))
  .attr("height", d => y(0) - y(d.value));       // update data elements in same transition
```

Update the scale first, then transition axis and data elements together so nothing uses a stale scale.

## Canvas Axis Rendering

For Canvas-only charts, draw axes manually — iterate `scale.ticks()`, draw tick lines with `ctx.moveTo`/`ctx.lineTo`, labels with `ctx.fillText`. Set `ctx.textAlign` and `ctx.textBaseline` based on orientation. See `canvas-rendering` skill for full setup.

## .nice() — When and When Not

**Use** for scatter/line where exact domain endpoints don't matter — gives clean tick values.

**Skip** when domain has semantic meaning (0–100%), when using band/point scales, when the user selected a specific date range, or when bar charts already start at zero.

```js
y.domain(d3.extent(data, d => d.value)).nice(5); // align to 5-tick interval
```

## Common Pitfalls

1. **Zero on log scales.** `scaleLog` domain must not include zero. Use `scaleSymlog` or clamp minimum to 1.

2. **DST jumps on `scaleTime`.** DST transitions create 23/25-hour days — uniform intervals become visually uneven. Use `scaleUtc`.

3. **`.nice()` expanding a zero-anchored domain.** For bar charts with `[0, max]`, `.nice()` might make the lower bound negative. It won't when zero is already round — `[0, d3.max(...)].nice()` keeps zero.

4. **`scaleBand` with unsorted domain.** Band order matches the domain array order. Sort explicitly if you want alphabetical: `.domain(data.map(d => d.name).sort())`.

5. **Tick count is a suggestion.** `.ticks(5)` may produce 4–6 ticks — D3 picks "nice" intervals. Use `.tickValues([...])` for exact control.

6. **Axis labels are manual.** D3 doesn't generate axis titles — append a `<text>` element yourself.

7. **Band scale `.bandwidth()` is zero without `.range()`.** Always set range before using.

8. **Axis group transform off by 0.5px.** For crisp 1px lines on non-retina: `translate(${marginLeft + 0.5}, 0)`. Not needed on retina.

9. **`tickFormat("")` vs `tickFormat(() => "")`.** Both hide labels. The string form is simpler.

10. **Responsive axes without cleanup.** D3's axis component uses a data join internally so `.call(axis)` is safe to repeat. But manually appended label text will duplicate — guard against it.

## References

- [D3 Scales](https://d3js.org/d3-scale) — scale API reference
- [D3 Axes](https://d3js.org/d3-axis) — axis generation and customization
- [D3 Format](https://d3js.org/d3-format) — number formatting specifiers
- [D3 Time Format](https://d3js.org/d3-time-format) — date/time formatting
- [Dual-Axis Charts](https://blog.datawrapper.de/dualaxis/) — Lisa Charlotte Muth on when dual-y is appropriate
- [Broken Y-Axis](https://blog.datawrapper.de/broken-y-axis/) — Datawrapper's axis break design analysis
