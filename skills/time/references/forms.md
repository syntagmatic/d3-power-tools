# Temporal forms

Absorbed from the v2 `time-series` skill. Open when building a horizon chart, cycle plot, swimlane, fan chart, difference area, or annotation layer.

## Horizon chart

Fold each series into `bands` layers of height `step = maxAbs / bands`; layer `b` shows `clamp(|v| - b*step, 0, step)` at opacity `(b+1)/bands`, positive and negative in separate hues. Negative values are drawn in the same upward orientation (or mirrored), not below the baseline.

```js
function horizon(g, data, { x, height, bands = 2, pos = "#4477AA", neg = "#EE6677" }) {
  const step = d3.max(data, d => Math.abs(d.value ?? 0)) / bands;
  const y = d3.scaleLinear([0, step], [height, 0]);
  const area = d3.area().defined(d => d.v != null).x(d => x(d.date)).y0(height).y1(d => y(d.v));
  for (let b = 0; b < bands; b++) for (const sign of [1, -1]) {
    const layer = data.map(d => ({
      date: d.date,
      v: d.value == null ? null
        : Math.sign(d.value) === sign ? Math.min(step, Math.max(0, Math.abs(d.value) - b * step)) : 0,
    }));
    g.append("path").datum(layer).attr("d", area)
      .attr("fill", sign > 0 ? pos : neg).attr("fill-opacity", (b + 1) / bands);
  }
}
```

- Heer, Kong & Agrawala, "Sizing the Horizon" (CHI 2009): estimation error and time rise as band count goes up; 2 bands is the recommendation. Layered bands help most when rows are very short.
- Untrained viewers read band edges as data features. Under ~5 series, small-multiple line charts are clearer.
- Share `step` across rows when rows are compared; per-row `step` makes every row look equally volatile.

## Cycle plot

One panel per cycle position (weekday, month, hour). Inside each panel, that position's observations in time order, plus a mean line for the seasonal norm. Shared y across panels.

- Group with `d.date.getUTCDay()` (or `getDay()` only if the whole chart is local time). Mixing UTC dates with local grouping shifts Sunday-night data into Monday.
- If per-position means barely differ, there's no cycle. Use a plain line.

## Swimlanes and Gantt

Overlapping events in one lane: sort by start, assign each to the first sub-row whose last end ≤ this start, else open a new row. Greedy is optimal here (interval partitioning). Lane height = sub-rows × row height.

## Fan chart (prediction bands)

Nested `d3.area()` bands behind the line, widest and faintest first (e.g. p5-p95 at 0.1, p20-p80 at 0.2). Mark points outside the outer band as anomalies. Only draw bands a model actually produced; with no model, use threshold lines instead.

## Difference area (A vs B, this year vs last)

Draw the area between A and B twice: once clipped to the region above line B (from the top edge down to B), which shows where A > B, and once clipped to the region below B, which shows where A < B. Two colors. For year-over-year, join each point with its value one year earlier:

```js
const byDate = new Map(data.map(d => [+d.date, d.value]));
const yoy = data
  .map(d => ({ date: d.date, current: d.value, previous: byDate.get(+d3.utcYear.offset(d.date, -1)) ?? null }))
  .filter(d => d.previous != null);
```

Observable Plot's `differenceY` does this declaratively; use D3 when you need custom interaction, zoom, or Canvas.

## Event markers

Point events: vertical dashed rule + label. Ranges (deploys, incidents, recessions): shaded band behind the data and in front of the grid. Many categorical states: a state swimlane under the chart sharing its x-scale. Callout mechanics live in `legibility` (`references/annotation.md`).

## Nearest-series hover

A 1.5px stroke can't be hovered. Flatten all series to `{date, value, series}`, build `d3.Delaunay.from(points, d => x(d.date), d => y(d.value))`, and `find(mx, my)` on one overlay. Rebuild the Delaunay whenever scales or data change, or hover lands on stale positions.
