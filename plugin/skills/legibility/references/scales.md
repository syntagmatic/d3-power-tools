# Scales and axes

Absorbed from the v2 `scales` skill. Open when a chart needs a nonlinear scale, a time axis with gaps, a broken axis, or classification breaks.

## Log vs symlog

`scaleLog` returns NaN for 0 and negatives, and the marks just vanish without an error. `scaleSymlog` computes `sign(x) * log1p(|x| / c)`: linear near zero, logarithmic beyond `c`. Raise `constant` when data clusters near zero.

Neither belongs on a bar chart: bar length stops being proportional to value.

## Time gaps (trading days, shifts)

Band approach: each observed date is a category. Equal spacing, no dead weekends.

```js
const x = d3.scaleBand(data.map(d => d.date), [marginLeft, width - marginRight]).padding(0.1);
const xAxis = d3.axisBottom(x)
  .tickValues(x.domain().filter(d => d.getUTCDay() === 1))
  .tickFormat(d3.utcFormat("%b %-d"));
```

Index approach, for lines where bars don't need width:

```js
const xi = d3.scaleLinear([0, data.length - 1], [marginLeft, width - marginRight]);
const xiAxis = d3.axisBottom(xi).ticks(8).tickFormat(i => {
  const d = data[Math.round(i)];
  return d ? d3.utcFormat("%b %-d")(d.date) : "";
});
```

Both lose proportional time: a 3-day holiday looks like a weekend. Keep `scaleUtc` and mark the gaps when duration matters (accrual, outages).

## UTC vs local

`scaleTime` uses local time, so DST days are 23 or 25 hours and uniform hourly data looks uneven. Use `scaleUtc` with `d3.utcParse`/`d3.utcFormat` unless the viewer needs wall-clock local time. The classic off-by-one: `new Date("2024-03-01")` parses as UTC midnight, which is the previous evening in the Americas under a local `timeFormat`.

## Multi-level time ticks

```js
const multiFormat = date =>
  d3.utcMonth(date) < date ? d3.utcFormat("%-d")(date)
  : d3.utcYear(date) < date ? d3.utcFormat("%b")(date)
  : d3.utcFormat("%Y")(date);
```

## Broken axis

Piecewise scale. Draw a zigzag between the segments so the break can't be missed.

```js
function brokenScale(domains, ranges) {
  const parts = domains.map((dom, i) => d3.scaleLinear(dom, ranges[i]));
  const scale = v => {
    const i = domains.findIndex(([lo, hi]) => v >= lo && v <= hi);
    return i >= 0 ? parts[i](v) : v < domains[0][0] ? parts[0](v) : parts.at(-1)(v);
  };
  scale.parts = parts;
  return scale;
}
```

## Axis transitions

Set the new domain first, then transition axis and marks off the same transition, so nothing renders with a stale scale. `.call(axis)` is idempotent. Hand-appended axis titles aren't, so join them: `g.selectAll(".title").data([label]).join("text")`.

## Diverging variants

`scaleDivergingLog`, `scaleDivergingSymlog`, `scaleDivergingPow`, `scaleDivergingSqrt` apply the transform to each side of the midpoint, for skewed data clustered near the center.

Default to a symmetric domain `[-m, 0, m]` with `m = max(|min|, |max|)`. `[min, 0, max]` normalizes each side separately, so -2 and +8 both reach full saturation, which misstates magnitude.

## Classification

```js
const q = d3.scaleQuantile(values, d3.schemeBlues[5]);
const legendBreaks = q.quantiles();           // show these, and a histogram
const z = d3.scaleQuantize(d3.extent(values), d3.schemeBlues[5]);
```

Jenks natural breaks aren't in D3. Use `ss.jenks(values, k)` from simple-statistics, which returns `[min, b1, ..., max]`, and pass the interior breaks to `scaleThreshold`.

## Pitfalls

- A bar domain not including zero turns 50→80 into "almost double."
- An unsorted band domain reads as noise. Sort by value unless the order means something.
- `.ticks(5)` can return 4-6 ticks.
- Hand-appended axis titles duplicate on every resize without a join.
