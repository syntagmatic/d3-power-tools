---
name: sparkcharts
description: "Build inline sparklines and spark charts with D3.js. Use this skill when the user wants small, word-sized charts embedded in text, tables, dashboards, or KPI cards. Covers sparklines (line), spark bars, spark area, win/loss strips, bullet charts, dot-strip distributions, and band/range charts. Also use when the user mentions Tufte sparklines, inline charts, micro charts, or small multiples of tiny charts."
---

# Sparkcharts

Readers lose context when they have to look away from a number to find its trend. Sparkcharts solve this by embedding the shape of the data — trend, volatility, distribution — right next to the value, inside the text flow. Tufte's "intense, simple, word-sized graphics" with a data-pixel ratio of 1.0: no axes, no legends, no chrome.

## Sparkline (Line)

The canonical form. All other spark types are variations on this structure.

```js
const x = d3.scaleLinear([0, data.length - 1], [1, w - 1]);
const y = d3.scaleLinear(d3.extent(data), [h - 1, 1]);
const line = d3.line((d, i) => x(i), d => y(d))
  .curve(d3.curveMonotoneX);

svg.append("path").datum(data)
  .attr("d", line)
  .attr("fill", "none")
  .attr("stroke", "currentColor")
  .attr("stroke-width", 1.5);

// Endpoint dot
svg.append("circle")
  .attr("cx", x(data.length - 1))
  .attr("cy", y(data.at(-1)))
  .attr("r", 1.5)
  .attr("fill", "#e41a1c");
```

### Curve choice

- `curveMonotoneX` — default. Smooth without overshooting: a monotone segment never creates false peaks, critical at sparkline scale where a single overshoot pixel reads as a real data feature
- `curveLinear` — point-to-point, best for discrete/step data where interpolation would imply nonexistent intermediate values
- `curveStep` — categorical time periods (quarters, on/off states) where the value holds until the next change
- `curveBasis` — very smooth but overshoots extrema. Only when the overall trend matters more than individual values

## Variants

### Spark Area

Fill below the line. Use low opacity to avoid overwhelming the stroke.

```js
const area = d3.area()
  .x((d, i) => x(i)).y0(h).y1(d => y(d))
  .curve(d3.curveMonotoneX);

svg.append("path").datum(data)
  .attr("d", area).attr("fill", "currentColor").attr("opacity", 0.1);
// Draw line path on top
```

### Spark Bar

Tiny bar chart for discrete counts or distributions.

```js
const n = data.length, gap = 1;
const barW = Math.max(1, (w - gap * (n - 1)) / n);
const y = d3.scaleLinear([Math.min(0, d3.min(data)), d3.max(data)], [h, 0]);
const zero = y(0);

svg.selectAll("rect").data(data).join("rect")
  .attr("x", (d, i) => i * (barW + gap))
  .attr("y", d => d >= 0 ? y(d) : zero)
  .attr("width", barW)
  .attr("height", d => Math.abs(y(d) - zero))
  .attr("fill", d => d >= 0 ? "#3182bd" : "#e6550d");
```

### Win/Loss Strip

Binary outcome strip — wins above midline, losses below. Tufte's "bandwidth sparkline."

```js
const mid = h / 2, barH = mid - 1;
svg.selectAll("rect").data(data).join("rect")
  .attr("x", (d, i) => i * (barW + gap))
  .attr("y", d => d > 0 ? mid - barH : d < 0 ? mid + 1 : mid - 0.5)
  .attr("width", barW)
  .attr("height", d => d === 0 ? 1 : barH)
  .attr("fill", d => d > 0 ? "#2ca02c" : d < 0 ? "#d62728" : "#999");
```

### Bullet Chart

Stephen Few's bullet chart — compact alternative to gauges. A quantitative measure against a qualitative range and a comparative marker.

```js
const x = d3.scaleLinear([0, d3.max(ranges)], [0, w]);

// Qualitative ranges (background bands, largest first)
svg.selectAll(".range").data([...ranges].sort((a, b) => b - a)).join("rect")
  .attr("width", d => x(d)).attr("height", h)
  .attr("fill", (d, i) => ["#ddd", "#ccc", "#bbb"][i]);

// Measure bar (foreground, 40% height centered)
svg.append("rect")
  .attr("y", h * 0.3).attr("width", x(value)).attr("height", h * 0.4)
  .attr("fill", "#333");

// Target marker line (70% height centered)
svg.append("line")
  .attr("x1", x(target)).attr("x2", x(target))
  .attr("y1", h * 0.15).attr("y2", h * 0.85)
  .attr("stroke", "#000").attr("stroke-width", 2);
```

### Band / Range Chart

Value within a confidence interval or min–max range. Data: `[{value, lo, hi}, ...]`.

```js
const area = d3.area()
  .x((d, i) => x(i)).y0(d => y(d.lo)).y1(d => y(d.hi))
  .curve(d3.curveMonotoneX);
const line = d3.line()
  .x((d, i) => x(i)).y(d => y(d.value))
  .curve(d3.curveMonotoneX);

svg.append("path").datum(data).attr("d", area).attr("fill", "#e0e0e0");
svg.append("path").datum(data).attr("d", line)
  .attr("fill", "none").attr("stroke", "currentColor").attr("stroke-width", 1.5);
```

### Dot Strip (Distribution)

Individual values as dots along a single axis — one-dimensional scatter.

```js
const r = 1.5;
const x = d3.scaleLinear(d3.extent(data), [r, w - r]);
svg.selectAll("circle").data(data).join("circle")
  .attr("cx", d => x(d)).attr("cy", h / 2)
  .attr("r", r).attr("fill", "#3182bd").attr("opacity", 0.6);
```

## Embedding in Tables

The most common use case: sparklines inside `<td>` cells.

```js
rows.selectAll("td")
  .data(d => columns.map(col => ({ col, row: d })))
  .join("td")
    .each(function({ col, row }) {
      if (col.type === "sparkline") {
        const svg = d3.select(this).append("svg").attr("width", 60).attr("height", 16);
        // draw sparkline in svg using scales + line generator from above
      } else {
        d3.select(this).text(col.format ? col.format(row[col.key]) : row[col.key]);
      }
    });
```

Cell sizing: `white-space: nowrap`, tight padding (`2px 6px`), `line-height: 1`.

This is also how Grafana's table visualization works (as of March 2026): a "sparkline" cell type renders a tiny line/bar chart from time series data directly in the table cell. The pattern validates the design — sparklines are most effective when adjacent to the number they contextualize, not isolated in a separate panel.

### Shared scales across rows

When sparkcharts in different rows represent the same metric, they **must share a common y-domain** so heights are visually comparable. Without this, every sparkline auto-scales to its own `d3.extent`, and a 1% fluctuation filling its range looks identical to a 40% swing — Tufte's lie factor made invisible by the absence of axes.

```js
// Compute shared domain ONCE from all rows before rendering
const mpgDomain = d3.extent(allData, d => d.mpg);
const hpDomain = [0, d3.max(allData, d => d.hp)];

// Pass to each sparkline builder
function sparkline(container, values, { domain, ...opts } = {}) {
  const ext = domain || d3.extent(values);           // ← shared if given
  const y = d3.scaleLinear()
    .domain(ext[0] === ext[1] ? [ext[0]-1, ext[1]+1] : ext)
    .range([h - pad, pad]);
  // ... draw as usual
}
```

For spark bars showing distributions, use `[0, globalMax]` as the domain so bar heights are proportional across rows.

### Pair sparkcharts with numbers

A sparkline shows shape; numbers give magnitude. Always place a range, summary stat, or latest value next to the spark cell. Common patterns:

| MPG Range | MPG Distribution |
|-----------|-----------------|
| 10–28     | `~sparkline~`   |
| 22–38     | `~sparkline~`   |

The number column anchors the visual. Without it, readers can't tell whether a line at the top of a spark means 30 or 300.

## Embedding Inline in Text

Store data in `data-values` attributes, select all `.spark` spans, parse and render. The critical CSS: `vertical-align: middle` aligns the spark with surrounding text, and `margin: 0 2px` gives breathing room without breaking the reading flow.

```css
.spark svg { vertical-align: middle; margin: 0 2px; }
```

## Dashboard Cards

Larger sparklines (40–60px tall) in metric cards. At this size you have pixels to spare, so add context that word-sized sparklines omit:
- A dashed reference line at a meaningful value (budget, target, zero) — gives the shape a baseline the reader can judge against
- Min/max dots — anchors the range without adding an axis
- Endpoint value label — lets the reader skip the mental lookup to the KPI number

The dominant real-world layout (used by Grafana stat panels, Datadog metric cards, every monitoring dashboard): large number + delta arrow + sparkline, stacked vertically in a fixed-width card.

```js
// KPI card structure
const card = d3.select(container).append("div")
  .style("padding", "12px 16px").style("min-width", "160px");

card.append("div").style("font-size", "28px").style("font-weight", "600")
  .text(d3.format(",.0f")(latest));

const delta = latest - previous;
card.append("div")
  .style("font-size", "13px")
  .style("color", delta >= 0 ? "#2ca02c" : "#d62728")
  .text(`${delta >= 0 ? "▲" : "▼"} ${d3.format("+.1%")(delta / previous)}`);

const svg = card.append("svg").attr("width", 140).attr("height", 40);
// Draw sparkline with shared domain across all cards
```

### Fixed-window vs auto-scaled sparklines

For monitoring dashboards, use a **fixed time window** (last 1h, 6h, 24h) rather than auto-scaling the x-axis. When the window is consistent, the viewer learns the "normal shape" — a spike or dip stands out because the baseline shape is familiar. Auto-scaled sparklines shift shape as the data extent changes, destroying this learned recognition.

```js
// Fixed 24h window: always show the same time range
const now = Date.now();
const x = d3.scaleTime([now - 24 * 60 * 60 * 1000, now], [0, w]);
// Data outside the window is simply not plotted
```

Auto-scaling is fine for editorial sparklines (in articles, reports) where each chart is read once. Fixed-window is better for operational sparklines that the same person monitors repeatedly.

## Small Multiples Grid

Use CSS grid and shared y-domain for comparable heights across charts:

```js
const globalExtent = d3.extent(datasets.flatMap(d => d.values));

const grid = d3.select(container).append("div")
  .style("display", "grid")
  .style("grid-template-columns", `repeat(${cols}, 1fr)`);

datasets.forEach(({ label, values }) => {
  const cell = grid.append("div");
  cell.append("div").style("font-size", "11px").text(label);
  // Draw sparkline with y.domain(globalExtent) for comparability
});
```

**Shared vs independent scales**: shared makes heights comparable ("which grew most?"). Independent maximizes each chart's dynamic range ("what shape is each trend?"). Default to shared.

## Responsive

Use `viewBox` and let CSS control size. `preserveAspectRatio: "none"` stretches to fill container width. This is safe for sparklines (unlike most charts) because the reader cares about trend shape, not precise slope — stretching horizontally changes aspect ratio but preserves the up/down pattern that carries the message.

```js
svg.attr("viewBox", `0 0 ${w} ${h}`)
  .attr("preserveAspectRatio", "none")
  .style("width", "100%").style("height", `${h}px`);
```

## Canvas Sparklines

For 200+ sparklines on a page, Canvas is lighter than 200 SVGs. Same scale/line logic, but draw with `ctx.beginPath()` + manual `moveTo`/`lineTo` loop + `ctx.stroke()`. Remember DPR setup (see `canvas` skill).

## Interaction

Sparklines are typically non-interactive. When needed:

- **Hover tooltip**: find nearest point by index — `const i = Math.round(x.invert(pointerX))`, show `data[i]`
- **Click to expand**: `svg.style("cursor", "pointer").on("click", () => showExpanded(data))`

## Accessibility

Always set `role="img"` and `aria-label` describing the trend, min, max, latest value. See `canvas-accessibility` skill for canvas-based sparklines.

Use `currentColor` as default stroke so sparklines inherit text color and adapt to dark themes.

## Downsampling (LTTB)

When data exceeds pixel width (e.g., 1000 points in 80px), downsample first. Largest-triangle-three-buckets preserves visual shape better than averaging. Pick the point in each bucket that forms the largest triangle with the selected points in adjacent buckets.

## Performance

| Sparklines on page | Technique |
|---|---|
| < 200 | SVG |
| 200–1000 | Canvas, one per sparkline |
| 1000+ | Canvas + virtual scroll (only render visible rows) |

## When Sparkcharts Mislead

Sparklines strip away axes and labels, which makes them powerful — and dangerous. The same design that maximizes data density also removes the safeguards that prevent misreading.

1. **Auto-scaled y-axis hides magnitude.** `d3.extent` maps min-to-max into the full pixel height. A stock that moved 1% and one that moved 40% look identical if each fills its own range. Fix: use shared y-domains when sparklines sit side-by-side (see "Shared scales across rows"), or always pair with a number column that anchors magnitude.

2. **Zero-baseline suppresses signal.** The opposite problem: forcing `y.domain([0, max])` on data that varies between 98 and 102 produces a flat line at the top. Tufte noted this tension explicitly — there is no universal answer. Rule of thumb: use zero baseline for quantities where zero is meaningful (counts, revenue). Use `d3.extent` for quantities where relative change matters (temperature, stock price), but then *never* compare heights across sparklines visually.

3. **Aspect ratio distortion.** A sparkline stretched too wide flattens slopes; too narrow exaggerates them. At word-size (roughly 4:1 to 6:1 width:height), most trends read naturally. `preserveAspectRatio: "none"` with CSS width is convenient but can distort perception if the container width varies dramatically — test at both narrow and wide breakpoints.

4. **Missing data reads as continuity.** Without `.defined(d => d != null)`, the line generator connects across gaps, implying data exists where it does not. At sparkline scale, a broken line segment is a stronger and more honest signal than interpolation.

5. **Color without context.** Coloring a sparkline green or red based on endpoint change tells only part of the story — a line that crashed and recovered looks "green." If the shape tells a different story than the color, the color wins (readers process it first).

## When Not to Use Sparkcharts

- **When the reader needs to read precise values.** Sparklines encode trend and shape, not magnitude. If the task is "what was the value in March?", use a proper chart with axes, or a data table.
- **When you have fewer than ~5 data points.** Below this, a sparkline carries less information than just listing the numbers. The visual overhead is not justified.
- **When comparing across different units.** Sparklines in a table column work when every row measures the same thing. Mixing temperature, revenue, and percentages in one column of sparklines invites false visual comparisons.

## Common Pitfalls

1. **Flat-line when all values identical** — `d3.extent` returns `[v, v]`, mapping everything to mid-height. Fix: pad domain `[v - 1, v + 1]`.
2. **Blurry Canvas on retina** — multiply canvas dimensions by `devicePixelRatio`, CSS-size to logical pixels.
3. **SVG in table cells adds height** — the SVG's default `display: inline` respects line-height and adds whitespace below. Fix: `display: block` on SVG or `line-height: 0` on `<td>`.
4. **Missing null handling** — use `.defined(d => d != null)` on the line generator to break gaps instead of connecting across missing data.
5. **Too many data points** — 1000 points in 80px means <0.1px each, wasting CPU with no visual benefit. Downsample with LTTB.

## Observable Plot

Observable Plot has no dedicated sparkline mark, but you can approximate one with `Plot.line` in a small fixed-size plot with `axis: null` on both scales. For spark-in-table, D3 gives you more control over cell-level rendering and shared scales across rows.

## References

- [Sparkline — Edward Tufte](https://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=0001OR) — original concept
- [Bullet Graph Design Spec](https://www.perceptualedge.com/articles/misc/Bullet_Graph_Design_Spec.pdf) — Stephen Few
- [D3 Sparkline — Observable](https://observablehq.com/@d3/sparkline) — Mike Bostock
- [LTTB downsampling](https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf) — Sveinn Steinarsson
