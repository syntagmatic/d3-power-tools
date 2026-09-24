---
name: time
description: "Time-series charts in D3: choosing line, area, horizon, swimlane/Gantt, cycle plot, calendar heatmap, fan chart or difference area; gap handling with line.defined; LTTB and M4 downsampling for large series; real-time streaming (fixed window, ring buffer, rAF batching); brushed overview+detail (focus+context) and semantic temporal zoom; nearest-series crosshair hover, multi-series spaghetti plots, event markers, and DST-safe binning."
---

# Time

Time is the axis viewers think they understand, and the one that lies most quietly: a line drawn across an outage reads as data, 100K points become a solid band, a streaming chart whose domain follows the data extent jitters. This skill is about picking the temporal form, then keeping the line honest about gaps, density, and motion.

Axis mechanics (UTC vs local, trading-day gaps, multi-level ticks) live in `legibility` (`references/scales.md`). Default to `scaleUtc` and `d3.utc*` intervals everywhere here.

## Which temporal form

| If the viewer asks... | Use | Not |
|---|---|---|
| What's the trend? (≤5 series) | line | area, unless the zero baseline and filled magnitude mean something |
| How does a total split over time? | stacked area | stacked lines (upper series read as totals) |
| How do 10-50 series compare? | horizon chart, 2 bands, shared band step | spaghetti lines beyond ~5 series; horizon under 5 series (small multiples read easier) |
| When was each thing active / what overlapped? | swimlane (events) or Gantt (planned spans), sub-rows for overlaps | points on a line |
| Is Tuesday always slow? | cycle plot: one panel per weekday/month, mean line each | one long line that buries seasonality in trend |
| Which days of the year were busy? | calendar heatmap (week columns, weekday rows) | a line of 365 daily points |
| Is this value normal? | line + fan chart (nested model bands), anomalies marked | bands nobody computed; use threshold lines instead |
| When did A exceed B? / this year vs last? | difference area (two clips) | two overlaid lines and mental subtraction |
| What happened during the deploy? | line + event bands or rules, state swimlane below | unannotated line, viewers guess at cause |
| What's happening now? | streaming line on a fixed window | an extent-following domain |
| Too long to read at one zoom? | overview+detail brush, or semantic zoom | one chart with 100K points squashed into it |

Pairings that work: line + fan band + event markers (monitoring); overview+detail + LTTB (exploration); horizon rows + state swimlane on a shared x-scale (multi-metric incident review).

## Gaps

A line through missing data is a claim that data exists. Break the line; don't interpolate across outages.

- `d3.line().defined(d => d.value != null)` and the same on `d3.area()`. Without it, `y(null)` coerces to `y(0)` and the line dives to zero, which looks like a real crash. `undefined` gives `NaN` and a broken path.
- Irregular sampling has no nulls to catch, so insert a sentinel wherever the step exceeds the expected cadence:

```js
const withGaps = (data, maxGapMs) => data.flatMap((d, i) =>
  i > 0 && d.date - data[i - 1].date > maxGapMs ? [{ date: d.date, value: null }, d] : [d]);
```

- Pick `maxGapMs` as a multiple of the median step, not a guess.
- Isolated points between two gaps vanish with `.defined()` because a one-point segment has no length. Draw a dot layer for points whose neighbors are both undefined.
- To show the gap is known, draw a dashed line under the real one from only the defined points: `line(data.filter(line.defined()))`. Dashes say "missing"; solid says "measured".
- `curveBasis` flattens spikes and `curveCardinal`/`curveCatmullRom` overshoot. Use `curveLinear`, `curveMonotoneX`, or `curveStepAfter` for sampled states.
- Weekends in trading data are expected gaps, not outages: remove them with a band or index scale (`legibility`), don't break the line at every Friday.

## Density

At more than ~2 points per pixel column, the line is a solid band and SVG slows. Reduce before rendering, per series, per visible window.

| Points per series | Do |
|---|---|
| < ~2× width | draw everything |
| 2× width to ~1M | LTTB to ~`2 * width` on the visible slice |
| extremes must survive (alerting) | M4: first/last/min/max per pixel column |
| 10M+ overview | min-max per pixel column, Canvas, typed arrays |

- LTTB keeps shape, not values: it can skip a bucket's real peak. Never compute stats or show tooltips from downsampled data; look up the raw point.
- Re-downsample after every brush or zoom; slice with `d3.bisector` first.
- Downsample each run between gaps separately; nulls coerce to 0 inside the algorithm.

## Streaming

- Below ~1 Hz, just re-render on each point. Above that: ring buffer, coalesce arrivals to one redraw per `requestAnimationFrame`.
- **Fixed window**: x domain `[now - W, now]` from the clock, not `d3.extent(buffer)`, which jumps on late points and while the buffer fills. Hold y steady or the line rescales every frame.
- **Redraw vs transform shift**: redrawing the path each frame against a moving domain is the default and tolerates jittered arrival. Transform shift (append the point, then transition `translate(-dx)` with linear easing over the arrival interval) is cheaper in SVG but stutters unless arrival is regular. Clip the plot area either way.
- Evict by time (keep one point past the left edge so the line enters from the frame).
- Teardown: `cancelAnimationFrame`, close the socket, disconnect observers. Background tabs pause rAF but not sockets, so cap the pending queue.

## Brushed focus+context

Overview (full range, faint area) with `d3.brushX`; detail x domain = `selection.map(xOverview.invert)`.

- Cleared brush restores the full domain.
- Preset buttons call `brush.move`; it fires brush events, so don't render twice.
- Brush + zoom that update each other loop unless both handlers bail on the other's `sourceEvent`.
- `brush` fires on every pointermove: re-downsample the visible slice and coalesce to one render per frame.
- If the viewer needs coarse and fine at once, keep overview+detail. If one level at a time is fine, semantic zoom (re-aggregate by `d3.utcMonth`/`utcDay`/`utcHour` as the span shrinks) is lighter.

## Traps

- `scaleTime`/`scaleUtc` domain from strings: `+"2024-03-01"` is `NaN`, every mark vanishes. Parse to `Date` (epoch numbers are fine).
- Local-time daily bins on DST days hold 23 or 25 hours; daily totals jump. Bin with `d3.utcDay` or say so.
- Cycle plots grouped with `getDay()` on UTC dates shift late-evening data a day in the Americas. Use `getUTCDay()`.
- Brushing on a zoomed chart: invert with `transform.rescaleX(x)`, not the base `x`.
- Hovering a 1.5px line is impossible: hit-test with `d3.Delaunay` over all series points, rebuilt when scales change.
- Horizon rows with per-row band steps make every row look equally volatile. Share the step when rows are compared.
- Fan bands need a model. Don't draw a ±10% band and call it confidence.

## References

- `references/forms.md`: horizon code and band-count study, cycle plot, swimlane packing, fan chart, difference area and YoY join, event markers, nearest-series hover.
- `references/density.md`: reducer choice, LTTB implementation, M4, virtual windowing, typed arrays.
- `references/streaming.md`: rate tiers, fixed window, shift vs redraw, ring buffer, rAF batching, teardown.
- `references/focus-context.md`: overview+detail brush code, presets, snapping, brush/zoom sync, semantic zoom levels.
- `examples/time-series.html`: multi-series line, overview brush, 2-band horizon. Tested by `tests/test.config.json`.
