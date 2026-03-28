---
name: time-series
description: "Build time-series visualizations with D3.js. Use this skill when the user wants line charts over time, horizon charts, swimlane/event timelines, cycle plots, real-time streaming charts, brushed time selection, or multi-series spaghetti plots. Covers d3.scaleTime/scaleUtc, DST handling, gap detection, downsampling (LTTB), Canvas rendering for large time series, overview+detail, and crosshair tooltips."
---

# Temporal Time Series

Time is the one axis viewers think they understand — until DST eats an hour, a weekend gap implies a crash, or 100K points turn a line chart into a solid rectangle. These patterns handle the cases where naive date-to-pixel mapping breaks.

For axis customization and tick formatting, see `scales`. For brush mechanics, see `brushing`. For zoom integration, see `navigation`. For Canvas performance patterns, see `canvas`. For animated transitions, see `motion`. For callout annotations on time series, see `annotation`.

## Choosing a Time-Series Chart

| Viewer question | Best chart | Why |
|---|---|---|
| What's the trend? | Line chart | Simplest encoding for temporal continuity |
| How do 10+ series compare? | Horizon chart (2-3 bands) | Line spaghetti is unreadable beyond 5 series |
| Is this value normal? | Line + prediction band | Shows expected range; deviations pop visually |
| When did A exceed B? | Difference area (two-clip) | Line chart requires mental subtraction |
| Is Tuesday always slow? | Cycle plot | Line charts bury weekly seasonality in trend |
| What day-of-week patterns exist across a year? | Calendar heatmap | Encodes 2D temporal structure that lines can't show |
| What happened during this deployment? | Line + annotation bands | Without annotations, viewers guess at causation |
| How does this year compare to last? | Shift + difference area | Overlaid lines are hard to compare precisely |
| What's the distribution at each time point? | Fan chart (nested CI bands) | Line shows only central tendency |

Common pairings: line + prediction band + annotation markers (monitoring dashboard), overview+detail + LTTB (large dataset exploration), horizon chart + state timeline below (multi-metric with shared events).

## scaleTime vs scaleUtc

`d3.scaleUtc` is the safe default. Use `d3.scaleTime` only when you need local-timezone axis labels (e.g., "9 AM" for a work-hours dashboard).

Why it matters: DST creates days with 23 or 25 hours. With `scaleTime`, the visual gap between 1 AM and 3 AM on spring-forward is half the normal span — the chart lies about duration. On fall-back, 1:00-1:59 AM occurs twice and timestamps plot on top of each other. For sub-hourly data near DST boundaries, `scaleUtc` is the only correct choice.

When computing durations, use millisecond math (`(end - start) / 3.6e6` for hours) which is DST-safe.

## Gap Detection and Handling

Insert null sentinels at gaps so `.defined()` breaks the line:

```js
function insertGapSentinels(data, maxGapMs) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    if (i > 0 && (data[i].date - data[i - 1].date) > maxGapMs)
      result.push({ date: data[i - 1].date, value: null });
    result.push(data[i]);
  }
  return result;
}
```

Without `.defined(d => d.value != null)`, the line generator draws to (0, 0) for null values, creating spikes to the origin — a bug that looks like a real data crash.

**Weekend/holiday gaps in financial data:** A continuous time axis shows weekends as flat gaps. Two fixes: `d3.scaleBand` on trading days only (more honest — doesn't imply data exists where it doesn't), or `scaleTime` with `.defined(isWeekday)` to break the line.

## Horizon Charts

Horizon charts fold an area chart into colored bands: magnitude maps to color intensity, sign maps to hue. They fit 10-50 series into the vertical space of one line chart.

```js
function horizonChart(svg, data, { x, bands = 4, height, colorPos = "steelblue", colorNeg = "tomato" }) {
  const maxAbs = d3.max(data, d => Math.abs(d.value)),
        step = maxAbs / bands,
        y = d3.scaleLinear([0, step], [height, 0]),
        area = d3.area().defined(d => d.value != null)
          .x(d => x(d.date)).y0(height)
          .y1(d => y(Math.min(step, Math.abs(d.value))));

  for (let band = 0; band < bands; band++) {
    const bandData = data.map((d, i) => ({
      date: d.date,
      value: Math.max(0, Math.abs(d.value) - band * step),
    }));
    for (const sign of [1, -1]) {
      svg.append("path")
        .datum(bandData.map((d, i) => ({
          ...d, value: (sign > 0 ? data[i].value >= 0 : data[i].value < 0) ? d.value : 0,
        })))
        .attr("d", area)
        .attr("fill", sign > 0 ? colorPos : colorNeg)
        .attr("fill-opacity", (band + 1) / bands);
    }
  }
}
```

**Band count matters:** Heer, Kong, and Agrawala (CHI 2009) found 2-band horizon charts match standard line chart accuracy once viewers learn them, but accuracy degrades beyond 4 bands. Stick to 2 bands for general audiences, 3-4 for expert dashboards.

**When not to use:** Horizon charts require learning — untrained viewers misread band boundaries as data features. If fewer than 5 series, small multiples of standard line charts are clearer.

## Cycle Plots

Cycle plots decompose a time series by recurring period (day-of-week, month, hour) to answer: "Is Tuesday always slow, or was last Tuesday unusual?" Each panel shows all observations for one cycle position, with a mean line for the seasonal norm.

```js
const byDay = d3.group(data, d => d.date.getDay()),
      dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
      panelW = width / 7,
      y = d3.scaleLinear(d3.extent(data, d => d.value), [panelH, 0]);

dayNames.forEach((name, dayIdx) => {
  const panel = svg.append("g").attr("transform", `translate(${dayIdx * panelW}, 0)`),
        dayData = (byDay.get(dayIdx) || []).sort((a, b) => a.date - b.date),
        xLocal = d3.scaleLinear([0, dayData.length - 1], [4, panelW - 4]);

  panel.append("path").datum(dayData)
    .attr("d", d3.line().x((d, i) => xLocal(i)).y(d => y(d.value)))
    .attr("fill", "none").attr("stroke", "steelblue").attr("stroke-width", 1.5);

  const mean = d3.mean(dayData, d => d.value);
  panel.append("line")
    .attr("x1", 0).attr("x2", panelW)
    .attr("y1", y(mean)).attr("y2", y(mean))
    .attr("stroke", "#e15759").attr("stroke-dasharray", "4,2");
});
```

Cycle plots assume a meaningful recurring period exists. If `d3.mean` per cycle position shows no variance across positions, a cycle plot adds nothing.

## Overlapping Event Stacking (Swimlanes)

When events overlap, stack into sub-rows. Sort by start time, greedily assign each event to the first sub-row whose last event ends before this one starts. Track per-row end times in an array; if no row fits, create a new one. Set `event.row` for y-offset within the lane.

## Real-Time / Streaming

**Circular buffer** — avoid `Array.shift()` (O(n)) for high-frequency data. Write to `buffer[head % capacity]`, advance head, yield in order via iterator. Unbounded `push()` in a streaming chart is a memory leak on a timer.

**rAF gating** — when data arrives faster than screen refresh, batch updates:

```js
let pendingData = [], rafId = null;
function onData(point) {
  pendingData.push(point);
  if (!rafId) rafId = requestAnimationFrame(flush);
}
function flush() {
  rafId = null;
  for (const point of pendingData) buffer.push(point);
  pendingData = [];
  redraw();
}
```

**Teardown** — `cancelAnimationFrame(rafId)`, `ws.close()`, `ro.disconnect()`. A streaming chart that outlives its DOM element keeps rendering to nowhere. Don't capture growing arrays in stale closures; reference the buffer directly.

If data arrives slower than 1 Hz, skip streaming architecture entirely. Just re-render on each point.

## Voronoi-Based Nearest-Series Detection

For dense multi-series charts, a 1.5px stroke is nearly impossible to hover. Use Delaunay to find the nearest point across all series:

```js
const allPoints = series.flatMap(([key, values]) =>
  values.map(d => ({ ...d, series: key }))
);
const delaunay = d3.Delaunay.from(allPoints, d => x(d.date), d => y(d.value));

svg.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event);
  const nearest = allPoints[delaunay.find(mx, my)];
  // Highlight nearest.series, show tooltip at nearest point
});
```

## LTTB Downsampling (Largest Triangle Three Buckets)

LTTB reduces point count while preserving visual shape by maximizing triangle area between consecutive selected points.

**The core tradeoff:** LTTB preserves what the chart looks like but not what the data says. It distorts frequency content and shifts peak locations slightly. This is fine — LTTB is a rendering optimization, not a data transformation.

```js
function lttb(data, threshold) {
  if (threshold >= data.length || threshold < 3) return data;
  const sampled = [data[0]], bSize = (data.length - 2) / (threshold - 2);
  let prevIdx = 0;
  for (let i = 0; i < threshold - 2; i++) {
    const bStart = Math.floor(i * bSize) + 1, bEnd = Math.floor((i + 1) * bSize) + 1,
          nEnd = Math.min(Math.floor((i + 2) * bSize) + 1, data.length);
    let avgX = 0, avgY = 0; // Average of next bucket = triangle target
    for (let j = bEnd; j < nEnd; j++) { avgX += +data[j].date; avgY += data[j].value; }
    avgX /= (nEnd - bEnd); avgY /= (nEnd - bEnd);
    let maxArea = -1, maxIdx = bStart;
    const prev = data[prevIdx];
    for (let j = bStart; j < bEnd; j++) {
      const area = Math.abs(
        (+prev.date - avgX) * (data[j].value - prev.value) -
        (+prev.date - +data[j].date) * (avgY - prev.value));
      if (area > maxArea) { maxArea = area; maxIdx = j; }
    }
    sampled.push(data[maxIdx]); prevIdx = maxIdx;
  }
  sampled.push(data[data.length - 1]);
  return sampled;
}
const downsampled = lttb(data, Math.min(data.length, width * 2));
```

Downsample each series independently — using shared indices distorts individual shapes because peaks occur at different times.

**Min-max bucketing:** Simpler and faster — keep min and max per pixel column. Use for 10M-point overviews; use LTTB when the downsampled line needs to look like the original.

**Virtual windowing:** Only render the visible range. `d3.bisector(d => d.date)` finds start/end indices in sorted data; slice, then `lttb(visible, width * 2)`. Makes zoom-to-detail instant on million-point datasets.

**TypedArrays:** Store timestamps and values in parallel `Float64Array`s. At 100K+ points, typed arrays iterate 3-5x faster than object arrays due to memory layout.

## Overview + Detail

The canonical time-series interaction: a small overview shows the full range, a brush selects a window, the main chart zooms to that window.

```
┌─────────────────────────────────────┐
│           Main Chart (detail)       │  ← xMain domain from brush
│                                     │
├─────────────────────────────────────┤
│  ▓▓▓▓▓░░░░░░░░░░░░░░░  Overview   │  ← brushX selects time range
└─────────────────────────────────────┘
```

```js
// Assumes: width, mainHeight, overviewHeight, data, mainG, overviewG, mainXAxisG, mainLine, lineGen
const xOverview = d3.scaleUtc(d3.extent(data, d => d.date), [0, width]),
      xMain = xOverview.copy(),
      yOverview = d3.scaleLinear(d3.extent(data, d => d.value), [overviewHeight, 0]);

overviewG.append("path").datum(data)
  .attr("d", d3.area().x(d => xOverview(d.date)).y0(overviewHeight).y1(d => yOverview(d.value)))
  .attr("fill", "steelblue").attr("fill-opacity", 0.15);

const brush = d3.brushX().extent([[0, 0], [width, overviewHeight]]).on("brush end", brushed);
overviewG.append("g").call(brush);

function brushed(event) {
  if (!event.selection) return;
  const [x0, x1] = event.selection.map(xOverview.invert);
  xMain.domain([x0, x1]);
  mainXAxisG.call(d3.axisBottom(xMain));
  mainLine.attr("d", lineGen);
}
```

Use `scaleUtc` for the overview even if main uses `scaleTime` — UTC avoids spring-forward glitches. Re-run LTTB on the visible slice after each brush to keep point count near `2 * width`. For programmatic brush ("Last 6 months" buttons), call `brushG.transition().call(brush.move, [x0, x1])` — don't also call the update function manually or you double-render. Snap to intervals in the `end` event with `interval.floor(start)` / `interval.ceil(end)`.

## Prediction Bands and Anomaly Detection

Layer `d3.area()` bands behind the data line. Draw widest band first (lowest opacity), narrowest last:

```js
// Data shape: { date, value, p5, p95, p20, p80 }
const levels = [
  { lower: "p5", upper: "p95", opacity: 0.1 },
  { lower: "p20", upper: "p80", opacity: 0.2 },
];
levels.forEach(({ lower, upper, opacity }) => {
  g.append("path").datum(data)
    .attr("d", d3.area().x(d => x(d.date))
      .y0(d => y(d[lower])).y1(d => y(d[upper])).curve(d3.curveMonotoneX))
    .attr("fill", "steelblue").attr("fill-opacity", opacity);
});

// Anomaly markers — points outside the outer band
g.selectAll(".anomaly")
  .data(data.filter(d => d.value < d.p5 || d.value > d.p95))
  .join("circle")
    .attr("cx", d => x(d.date)).attr("cy", d => y(d.value))
    .attr("r", 4).attr("fill", "red").attr("stroke", "white").attr("stroke-width", 1.5);
```

This is a "fan chart" (Bank of England popularized this form). Don't fabricate confidence intervals; if no statistical model provides bounds, use threshold lines instead.

## Semantic Temporal Zoom

Standard zoom stretches the axis. Semantic zoom changes what marks *represent* — yearly view shows monthly bars, daily view shows hourly lines:

```js
function getTemporalLevel(domain) {
  const spanMs = domain[1] - domain[0];
  if (spanMs > 365 * 86400000) return { interval: d3.utcMonth, format: "%b %Y" };
  if (spanMs > 30 * 86400000)  return { interval: d3.utcWeek, format: "%b %d" };
  if (spanMs > 7 * 86400000)   return { interval: d3.utcDay, format: "%a %d" };
  if (spanMs > 86400000)       return { interval: d3.utcHour, format: "%H:%M" };
  return { interval: d3.utcMinute, format: "%H:%M:%S" };
}
```

On each zoom event, re-aggregate with `d3.rollups` using that interval, update the axis with `.ticks(interval).tickFormat(d3.utcFormat(format))`. Pre-compute aggregates per level to avoid re-rolling on every frame. If the viewer needs both macro and micro simultaneously, use overview+detail instead.

## Annotation Bands and Event Markers

For marking deployments, incidents, or regime changes, see `annotation`. Key patterns: point annotations (vertical dashed line + label), range annotations (shaded band), state timelines (categorical swimlane below chart). Draw bands behind data but in front of grid lines.

## Difference Area (Period Comparison)

Show when A exceeds B with two clipped area paths — green (A > B), red (B > A). Create a `clipPath` from each series line, apply to the opposing fill. For year-over-year, join each point with its value from one year ago:

```js
const byDate = new Map(data.map(d => [+d.date, d.value]));
const yoy = data
  .map(d => ({ date: d.date, current: d.value, previous: byDate.get(+d.date - 365.25 * 86400000) ?? null }))
  .filter(d => d.previous != null);
```

Observable Plot's `differenceY` mark handles this declaratively. Use D3 directly when you need custom interaction, zoom, or Canvas performance.

## Common Pitfalls

**scaleTime domain must be Date objects.** Passing strings or epoch numbers to `scaleTime.domain()` silently produces wrong results — the scale treats them as generic continuous values and the axis renders nonsense labels.

**Brush coordinates in zoomed space.** When combining brush and zoom, the brush operates in pixel coordinates but the scale may be transformed. Use `transform.rescaleX(x).invert()` to convert brush pixels to data coordinates, not `x.invert()`.

## References

- [Sizing the Horizon (Heer et al., CHI 2009)](https://idl.cs.washington.edu/files/2009-TimeSeries-CHI.pdf) — perceptual study of horizon chart band count and chart size
- [LTTB Algorithm](https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf) — Steinarsson's downsampling thesis
- [Focus + Context via Brushing](https://observablehq.com/@d3/focus-context) — canonical overview+detail pattern
- [Observable Plot: Difference Mark](https://observablehq.github.io/plot/marks/difference) — declarative two-series comparison
- [Semantic Zoom for Time Series (IEEE VIS 2024)](https://ieeexplore.ieee.org/document/10714315/) — qualitative abstraction at each zoom level
- [D3 Graph Gallery: Confidence Interval](https://d3-graph-gallery.com/graph/line_confidence_interval.html) — area-based prediction bands
