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

`d3.scaleUtc` is the safe default. Use `d3.scaleTime` only when you need local-timezone axis labels (e.g., "9 AM" in the user's timezone for a work-hours dashboard).

Why it matters: DST creates days with 23 or 25 hours. With `scaleTime`, the visual gap between 1 AM and 3 AM on a spring-forward day is half the normal two-hour span — the chart lies about duration. On fall-back days, 1:00-1:59 AM occurs twice and timestamps in that range plot on top of each other. For sub-hourly data near DST boundaries, `scaleUtc` is the only correct choice.

When computing durations, use millisecond math (`(end - start) / 3.6e6`) which is DST-safe.

## Gap Detection and Handling

### Breaking Lines at Gaps

Insert null sentinels at gaps so `.defined()` breaks the line:

```js
function insertGapSentinels(data, maxGapMs) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    if (i > 0 && (data[i].date - data[i - 1].date) > maxGapMs) {
      result.push({ date: data[i - 1].date, value: null });
    }
    result.push(data[i]);
  }
  return result;
}
```

Without `.defined(d => d.value != null)`, the line generator draws to (0, 0) for null values, creating spikes to the origin — a bug that looks like a real data crash.

### Weekend/Holiday Gaps in Financial Data

A continuous time axis shows weekends as flat gaps, making every Monday look like a plateau. Two fixes: `d3.scaleBand` on trading days only for evenly spaced axes, or `scaleTime` with `.defined(isWeekday)` to break the line at weekends. Band scales are more honest — they don't imply data exists where it doesn't.

## Horizon Charts

Horizon charts fold an area chart into colored bands: magnitude maps to color intensity, sign maps to hue. They fit 10-50 series into the vertical space of one line chart while preserving trend comparison.

```js
function horizonChart(svg, data, { x, bands = 4, height, colorPos = "steelblue", colorNeg = "tomato" }) {
  const maxAbs = d3.max(data, d => Math.abs(d.value));
  const step = maxAbs / bands;
  const y = d3.scaleLinear().domain([0, step]).range([height, 0]);
  const area = d3.area()
    .defined(d => d.value != null)
    .x(d => x(d.date))
    .y0(height)
    .y1(d => y(Math.min(step, Math.abs(d.value))));

  for (let band = 0; band < bands; band++) {
    const bandData = data.map(d => ({
      date: d.date,
      value: Math.max(0, Math.abs(d.value) - band * step),
    }));
    for (const sign of [1, -1]) {
      svg.append("path")
        .datum(bandData.map(d => {
          const orig = data.find(o => o.date === d.date);
          return { ...d, value: (sign > 0 ? orig.value >= 0 : orig.value < 0) ? d.value : 0 };
        }))
        .attr("d", area)
        .attr("fill", sign > 0 ? colorPos : colorNeg)
        .attr("fill-opacity", (band + 1) / bands);
    }
  }
}
```

### Band count matters

Heer, Kong, and Agrawala (CHI 2009) found that 2-band horizon charts match standard line chart accuracy once viewers learn to read them, but accuracy degrades beyond 4 bands because adjacent color-intensity steps become indistinguishable. Stick to 2 bands for general audiences, 3-4 for expert dashboards with trained users.

### When not to use horizon charts

Horizon charts require learning — untrained viewers misread band boundaries as data features. Don't use them for one-off presentations to general audiences. If you have fewer than 5 series, small multiples of standard line charts are clearer. If precise value reading matters more than trend comparison, use a standard chart with a tooltip.

## Cycle Plots

Cycle plots decompose a time series by recurring period (day-of-week, month, hour) to answer: "Is Tuesday always slow, or was last Tuesday unusual?" Each panel shows all observations for one cycle position, with a mean line for the seasonal norm. Standard line charts bury this signal in the overall trend.

```js
const byDay = d3.group(data, d => d.date.getDay());
const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const panelWidth = width / 7;
const y = d3.scaleLinear().domain(d3.extent(data, d => d.value)).range([panelHeight, 0]);

dayNames.forEach((name, dayIdx) => {
  const panel = svg.append("g").attr("transform", `translate(${dayIdx * panelWidth}, 0)`);
  const dayData = (byDay.get(dayIdx) || []).sort((a, b) => a.date - b.date);
  const xLocal = d3.scaleLinear().domain([0, dayData.length - 1]).range([4, panelWidth - 4]);

  panel.append("path")
    .datum(dayData)
    .attr("d", d3.line().x((d, i) => xLocal(i)).y(d => y(d.value)))
    .attr("fill", "none").attr("stroke", "steelblue").attr("stroke-width", 1.5);

  // Mean line highlights the seasonal norm
  const mean = d3.mean(dayData, d => d.value);
  panel.append("line")
    .attr("x1", 0).attr("x2", panelWidth)
    .attr("y1", y(mean)).attr("y2", y(mean))
    .attr("stroke", "#e15759").attr("stroke-dasharray", "4,2");
});
```

### When not to use cycle plots

Cycle plots assume a meaningful recurring period exists. If there's no seasonality, the panels show noise and the mean lines mislead. Test for seasonality first — if `d3.mean` per cycle position shows no variance across positions, a cycle plot adds nothing.

## Overlapping Event Stacking (Swimlanes)

When events in the same lane overlap, stack them into sub-rows. Sort by start time, then greedily assign each event to the first sub-row whose last event ends before this one starts. Track per-row end times in an array; if no row fits, create a new one. Set `event.row` for y-offset within the lane.

## Real-Time / Streaming

### Circular Buffer

Avoid `Array.shift()` (O(n)) for high-frequency data — it copies the entire array on every tick:

```js
class CircularBuffer {
  constructor(capacity) {
    this.capacity = capacity;
    this.buffer = new Array(capacity);
    this.head = 0;
    this.size = 0;
  }
  push(item) {
    this.buffer[this.head] = item;
    this.head = (this.head + 1) % this.capacity;
    if (this.size < this.capacity) this.size++;
  }
  *[Symbol.iterator]() {
    const start = this.size < this.capacity ? 0 : this.head;
    for (let i = 0; i < this.size; i++) {
      yield this.buffer[(start + i) % this.capacity];
    }
  }
  toArray() { return [...this]; }
}
```

### requestAnimationFrame Gating

When data arrives faster than the screen refreshes (e.g., 100 Hz sensor data), batch updates. Without gating, each WebSocket `onmessage` schedules a redundant `requestAnimationFrame`, and you render the same frame dozens of times:

```js
let pendingData = [];
let rafId = null;

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

### Memory Leak Prevention

1. **Bound your data** — use `CircularBuffer` or trim after each append. Unbounded `push()` in a streaming chart is a memory leak on a timer.
2. **Cancel on teardown** — `cancelAnimationFrame(rafId)`, `ws.close()`, `ro.disconnect()`. A streaming chart that outlives its DOM element keeps rendering to nowhere.
3. **Avoid stale closures** — don't capture growing arrays in long-lived callbacks; reference the buffer directly.

### When not to use real-time rendering

If data arrives slower than 1 Hz, skip the streaming architecture entirely. Just re-render on each data point — the complexity of circular buffers and rAF gating buys nothing at human-readable update rates.

## Voronoi-Based Nearest-Series Detection

For dense multi-series charts, hit-testing individual lines is unreliable — a 1.5px stroke is nearly impossible to hover. Use a Delaunay overlay to find the nearest point across all series:

```js
const allPoints = series.flatMap(([key, values]) =>
  values.map(d => ({ ...d, series: key }))
);
const delaunay = d3.Delaunay.from(allPoints, d => x(d.date), d => y(d.value));

svg.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event);
  const idx = delaunay.find(mx, my);
  const nearest = allPoints[idx];
  // Highlight nearest.series, show tooltip at nearest point
});
```

## LTTB Downsampling (Largest Triangle Three Buckets)

LTTB solves a specific problem: reducing point count while preserving visual shape. It keeps perceptually important peaks and valleys by maximizing triangle area between consecutive selected points.

**The core tradeoff:** LTTB preserves what the chart looks like but not what the data says. It distorts frequency content, shifts peak locations slightly, and can't be used for statistical analysis on the downsampled result. This is fine — LTTB is a rendering optimization, not a data transformation.

```js
function lttb(data, threshold) {
  if (threshold >= data.length || threshold < 3) return data;
  const sampled = [data[0]];
  const bucketSize = (data.length - 2) / (threshold - 2);

  let prevIdx = 0;
  for (let i = 0; i < threshold - 2; i++) {
    const bucketStart = Math.floor((i + 0) * bucketSize) + 1;
    const bucketEnd = Math.floor((i + 1) * bucketSize) + 1;

    // Average of next bucket (target for triangle area)
    const nextStart = Math.floor((i + 1) * bucketSize) + 1;
    const nextEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length);
    let avgX = 0, avgY = 0;
    for (let j = nextStart; j < nextEnd; j++) {
      avgX += +data[j].date;
      avgY += data[j].value;
    }
    avgX /= (nextEnd - nextStart);
    avgY /= (nextEnd - nextStart);

    // Find the point in this bucket forming the largest triangle
    let maxArea = -1, maxIdx = bucketStart;
    const prevPoint = data[prevIdx];
    for (let j = bucketStart; j < bucketEnd; j++) {
      const area = Math.abs(
        (+prevPoint.date - avgX) * (data[j].value - prevPoint.value) -
        (+prevPoint.date - +data[j].date) * (avgY - prevPoint.value)
      );
      if (area > maxArea) { maxArea = area; maxIdx = j; }
    }
    sampled.push(data[maxIdx]);
    prevIdx = maxIdx;
  }
  sampled.push(data[data.length - 1]);
  return sampled;
}

// Usage: reduce 100K points to ~2x pixel width
const downsampled = lttb(data, Math.min(data.length, width * 2));
```

Downsample each series independently — using the same sample indices across series distorts individual series shapes because peaks in different series occur at different times.

### Min-Max Bucketing

Simpler and faster than LTTB: for each pixel column, keep min and max values. Produces at most `2 * pixelWidth` points. Use min-max when you need speed over shape fidelity (e.g., a 10M-point overview pane), and LTTB when the downsampled line needs to look like the original (e.g., the detail view).

### Virtual Windowing

Only render the visible time range. Use `d3.bisector(d => d.date)` to find start/end indices within sorted data, slice, then downsample. On each `zoom` event, call `getVisibleData` with the rescaled domain, then `lttb(visible, width * 2)` before drawing. This makes zoom-to-detail feel instant even on million-point datasets.

### TypedArray for Time-Series Data

Store timestamps and values in parallel `Float64Array`s for cache-friendly access. Convert dates with `+d.date` (ms since epoch). This matters at 100K+ points — typed arrays iterate 3-5x faster than arrays of objects due to memory layout.

## Overview + Detail

The canonical time-series interaction: a small overview shows the full range, a brush selects a window, and the main chart zooms to that window.

```
┌─────────────────────────────────────┐
│           Main Chart (detail)       │  ← xMain domain from brush
│                                     │
├─────────────────────────────────────┤
│  ▓▓▓▓▓░░░░░░░░░░░░░░░  Overview   │  ← brushX selects time range
└─────────────────────────────────────┘
```

### Implementation

```js
const xOverview = d3.scaleUtc(fullExtent, [0, width]);
const xMain = d3.scaleUtc(fullExtent, [0, width]);
const yMain = d3.scaleLinear().range([mainHeight, 0]);

const overviewArea = d3.area()
    .x(d => xOverview(d.date))
    .y0(overviewHeight)
    .y1(d => yOverview(d.value));

overviewG.append("path")
  .datum(data)
    .attr("d", overviewArea)
    .attr("fill", "steelblue")
    .attr("fill-opacity", 0.15);

const brush = d3.brushX()
    .extent([[0, 0], [width, overviewHeight]])
    .on("brush end", brushed);

overviewG.append("g").call(brush);

function brushed(event) {
  if (!event.selection) return;
  const [x0, x1] = event.selection.map(xOverview.invert);
  xMain.domain([x0, x1]);
  mainXAxisG.call(d3.axisBottom(xMain));
  mainLine.attr("d", lineGen);
}
```

### Key details

- **Use `scaleUtc` for the overview** even if the main chart uses `scaleTime` — the overview rarely needs DST precision and UTC avoids spring-forward glitches at full-year zoom.
- **Downsample on brush** — when the user zooms into a narrow window, re-run LTTB on the visible slice to keep point count near `2 * width`.
- **Animate domain changes** — `xMain.domain(newDomain)` is instant; wrap axis and path updates in a shared transition for smooth zooming.
- **Programmatic brush.move** — to set the brush from buttons (e.g., "Last 6 months"), call `brushG.transition().call(brush.move, [x0, x1])`. This triggers the `brushed` handler via the transition, so don't also call the update function manually or you get a double render.
- **Snap to intervals** — in the `end` event, snap the selection to day/week/month boundaries with `interval.floor(start)` and `interval.ceil(end)`, then call `brush.move` with the snapped pixels.

## Prediction Bands and Anomaly Detection

Layer `d3.area()` bands behind the data line to answer "is this value normal?" The key is graduated opacity — draw widest band first (lowest opacity), narrowest last:

```js
// Data shape: { date, value, p5, p95, p20, p80 }
const levels = [
  { lower: "p5", upper: "p95", opacity: 0.1 },
  { lower: "p20", upper: "p80", opacity: 0.2 },
];

levels.forEach(({ lower, upper, opacity }) => {
  g.append("path").datum(data)
    .attr("d", d3.area()
      .x(d => x(d.date))
      .y0(d => y(d[lower]))
      .y1(d => y(d[upper]))
      .curve(d3.curveMonotoneX))
    .attr("fill", "steelblue").attr("fill-opacity", opacity);
});

// Anomaly markers — points outside the outer band
g.selectAll(".anomaly")
  .data(data.filter(d => d.value < d.p5 || d.value > d.p95))
  .join("circle")
    .attr("cx", d => x(d.date)).attr("cy", d => y(d.value))
    .attr("r", 4).attr("fill", "red").attr("stroke", "white").attr("stroke-width", 1.5);
```

This is a "fan chart" — the Bank of England's inflation forecasts popularized this form. Don't fabricate confidence intervals; if no statistical model provides bounds, use threshold lines instead (a dashed `line` at a known limit + a shaded `rect` for the alert zone above it).

Bands are just area paths — same rendering cost as a line. If hundreds of anomaly markers accumulate, switch to Canvas circles.

## Semantic Temporal Zoom

Standard zoom stretches the same axis. Semantic zoom changes what the marks *represent* at each level — yearly view shows monthly aggregates as bars, daily view shows hourly lines.

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

On each zoom event, call `getTemporalLevel` on the visible domain, re-aggregate with `d3.rollups` using that interval, and update the axis with `.ticks(interval).tickFormat(d3.utcFormat(format))`. Pre-compute aggregates per level to avoid re-rolling on every zoom frame (see LTTB virtual windowing pattern above).

Use semantic zoom when the dataset spans years with sub-hourly granularity available. If the viewer needs both macro and micro simultaneously, use overview+detail instead — it costs vertical space but shows both at once.

## Annotation Bands and Event Markers

For marking deployments, incidents, or regime changes on a time-series chart, see the `annotation` skill. The key Grafana-inspired patterns: point annotations (vertical dashed line + label), range annotations (shaded band spanning a time window), and state timelines (a categorical swimlane below the chart showing healthy/degraded/down). Draw annotation bands behind the data line but in front of grid lines.

## Difference Area (Period Comparison)

To show when metric A exceeds metric B (or this year vs last year), use two clipped area paths — one green (A > B), one red (B > A). This is what Observable Plot's `differenceY` mark does declaratively; in D3, create a `clipPath` from each series line and apply it to the opposing fill area.

For year-over-year comparison, join each point with its value from one year ago:

```js
const byDate = new Map(data.map(d => [+d.date, d.value]));
const oneYear = 365.25 * 86400000;
const yoy = data
  .map(d => ({ date: d.date, current: d.value, previous: byDate.get(+d.date - oneYear) ?? null }))
  .filter(d => d.previous != null);
```

**Observable Plot note:** Plot's `differenceY` mark and `shift` transform handle these patterns declaratively and are worth considering for quick exploratory views (as of March 2026). When you need custom interaction, zoom integration, or Canvas performance, build in D3 directly.

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
