---
name: sparkcharts
description: "Build inline sparklines and spark charts with D3.js. Use this skill when the user wants small, word-sized charts embedded in text, tables, dashboards, or KPI cards. Covers sparklines (line), spark bars, spark area, win/loss strips, bullet charts, dot-strip distributions, and band/range charts. Also use when the user mentions Tufte sparklines, inline charts, micro charts, or small multiples of tiny charts."
---

# Sparkcharts

Compact, word-sized visualizations that embed in text, table cells, and dashboard cards. Edward Tufte's sparkline: "intense, simple, word-sized graphics." Every pixel carries data — no axes, no legends.

```
<span class="spark">
  <svg width="80" height="16" viewBox="…">
    <path d="…" />       ← the sparkline
    <circle />           ← endpoint dot
  </svg>
</span>
```

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

- `curveMonotoneX` — smooth, preserves monotonicity, best default
- `curveLinear` — point-to-point, best for discrete/step data
- `curveStep` — step function, categorical time periods
- `curveBasis` — very smooth but overshoots, use when trend > individual values

## Variants

Each variant replaces the line generator / drawing step above. Scales and SVG setup remain the same.

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

### Shared scales across rows

When sparkcharts in different rows represent the same metric, they **must share a common y-domain** so heights are visually comparable. Without this, a flat distribution filling its own range looks identical to a steep one.

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

```html
<p>Revenue trending upward
  <span class="spark" data-values="3,5,4,7,6,8,9,11,10,12"></span>
  reaching $12M.</p>
```

```js
d3.selectAll(".spark").each(function() {
  const data = this.dataset.values.split(",").map(Number);
  const svg = d3.select(this).append("svg").attr("width", 80).attr("height", 16);
  // draw sparkline in svg using scales + line generator from above
});
```

```css
.spark svg { vertical-align: middle; margin: 0 2px; }
```

## Dashboard Cards

Larger sparklines (40–60px tall) in metric cards. Consider adding:
- A dashed reference line at a meaningful value (budget, target, zero)
- Min/max dots
- Endpoint value label

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

Use `viewBox` and let CSS control size. `preserveAspectRatio: "none"` stretches to fill container width — fine for sparklines where horizontal trend is the point.

```js
svg.attr("viewBox", `0 0 ${w} ${h}`)
  .attr("preserveAspectRatio", "none")
  .style("width", "100%").style("height", `${h}px`);
```

## Canvas Sparklines

For 200+ sparklines on a page, Canvas is lighter than 200 SVGs. Same scale/line logic, but draw with `ctx.beginPath()` + manual `moveTo`/`lineTo` loop + `ctx.stroke()`. Remember DPR setup (see `canvas-rendering` skill).

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

## Common Pitfalls

1. **Flat-line when all values identical** — `d3.extent` returns `[v, v]`. Fix: pad domain `[v - 1, v + 1]`.
2. **Blurry Canvas on retina** — multiply canvas dimensions by `devicePixelRatio`, CSS-size to logical pixels.
3. **SVG in table cells adds height** — `display: block` on SVG or `line-height: 0` on `<td>`.
4. **Missing null handling** — use `.defined(d => d != null)` on the line generator to break gaps.
5. **Too many data points** — 1000 points in 80px means <0.1px each. Downsample with LTTB.

## References

- [Sparkline — Edward Tufte](https://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=0001OR) — original concept
- [Bullet Graph Design Spec](https://www.perceptualedge.com/articles/misc/Bullet_Graph_Design_Spec.pdf) — Stephen Few
- [D3 Sparkline — Observable](https://observablehq.com/@d3/sparkline) — Mike Bostock
- [LTTB downsampling](https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf) — Sveinn Steinarsson
