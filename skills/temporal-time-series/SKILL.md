---
name: temporal-time-series
description: "Build time-series visualizations with D3.js. Use this skill when the user wants line charts over time, horizon charts, swimlane/event timelines, Gantt charts, cycle plots, real-time streaming charts, brushed time selection, or multi-series spaghetti plots. Covers d3.scaleTime/scaleUtc, time parsing/formatting, DST handling, gap detection, downsampling (LTTB), Canvas rendering for large time series, overview+detail, and crosshair tooltips."
---

# Temporal Time Series

Patterns for building time-series visualizations with D3.js v7+.

For axis customization and tick formatting, see `axes-and-scales`. For brush mechanics, see `brushing-and-selection`. For zoom integration, see `zoom-and-pan`. For Canvas performance patterns, see `canvas-rendering`. For animated transitions, see `animated-transitions`. For callout annotations on time series, see `annotations-and-labels`.

## DST and Timezone Pitfalls

### scaleTime vs scaleUtc

`d3.scaleTime` interprets domain values in the browser's local timezone. `d3.scaleUtc` interprets them in UTC. Use `scaleUtc` when the data has explicit UTC timestamps or when DST jumps would distort the axis.

DST creates days with 23 or 25 hours. `d3.scaleTime` handles this via the Date API — the visual gap between 1 AM and 3 AM on a spring-forward day is half the normal two-hour span. On fall-back days, 1:00-1:59 AM occurs twice — timestamps in this range plot on top of each other with `scaleTime`. Use `scaleUtc` for sub-hourly data near DST boundaries.

When computing durations, use millisecond math (`(end - start) / 3.6e6`) which is DST-safe.

### Date Constructor Timezone Trap

```js
new Date("2024-03-15");          // UTC midnight (date-only = UTC)
new Date("2024-03-15T00:00");    // LOCAL midnight (datetime without Z = local)
new Date("2024-03-15T00:00:00Z"); // UTC midnight (explicit Z)
```

This inconsistency is the #1 source of off-by-one-day bugs. Always use `d3.timeParse` or `d3.utcParse` for data loading.

## Gap Detection and Handling

### Detecting Gaps in Irregular Data

```js
function detectGaps(data, maxGapMs) {
  const gaps = [];
  for (let i = 1; i < data.length; i++) {
    const dt = data[i].date - data[i - 1].date;
    if (dt > maxGapMs) {
      gaps.push({ start: data[i - 1].date, end: data[i].date, index: i });
    }
  }
  return gaps;
}
```

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

Without `.defined(d => d.value != null)`, the line generator draws to (0, 0) for null values, creating spikes to the origin.

### Weekend/Holiday Gaps in Financial Data

Use `d3.scaleBand` on trading days only for evenly spaced axes, or `scaleTime` with `.defined(isWeekday)` to break the line at weekends.

## Horizon Charts

Layer a time-series area chart into colored bands, encoding magnitude by color intensity and sign by hue. Fits many series into small vertical space.

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

Beyond 4 bands, differences between adjacent bands become hard to distinguish. Stick to 3-4 bands for most use cases.

## Overlapping Event Stacking (Swimlanes)

When events in the same lane overlap, stack them into sub-rows. Sort by start time, then greedily assign each event to the first sub-row whose last event ends before this one starts. Track per-row end times in an array; if no row fits, create a new one. Set `event.row` for y-offset within the lane.

## Cycle Plots

Decompose a time series by recurring period (day-of-week, hour-of-day, month) to reveal seasonality. Each panel shows all observations for one cycle position.

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

  // Mean line for this day-of-week
  const mean = d3.mean(dayData, d => d.value);
  panel.append("line")
    .attr("x1", 0).attr("x2", panelWidth)
    .attr("y1", y(mean)).attr("y2", y(mean))
    .attr("stroke", "#e15759").attr("stroke-dasharray", "4,2");
});
```

## Real-Time / Streaming

### Circular Buffer

Avoid `Array.shift()` (O(n)) for high-frequency data:

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

When data arrives faster than the screen refreshes, batch updates:

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

1. **Bound your data** — use `CircularBuffer` or trim after each append, never unbounded `push()`
2. **Cancel on teardown** — `cancelAnimationFrame(rafId)`, `ws.close()`, `ro.disconnect()`
3. **Avoid stale closures** — don't capture growing arrays in long-lived callbacks; reference the buffer directly

## Voronoi-Based Nearest-Series Detection

For dense multi-series charts, hit-testing individual lines is unreliable. Use a Delaunay overlay to find the nearest point across all series:

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

Reduce point count while preserving visual shape. LTTB keeps perceptually important peaks and valleys:

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

Downsample each series independently — using the same sample indices across series distorts individual series shapes.

### Min-Max Bucketing

Simpler than LTTB: for each pixel column, keep min and max values. Loop over data, bucket by `Math.floor(x(d.date))`, track min/max per bucket, then flatten to `[min, max, min, max, ...]`. Produces at most `2 * pixelWidth` points.

### Virtual Windowing

Only render the visible time range. Use `d3.bisector(d => d.date)` to find start/end indices within sorted data, slice, then downsample. Combine with zoom: on each `zoom` event, call `getVisibleData` with the rescaled domain, then `lttb(visible, width * 2)` before drawing.

### TypedArray for Time-Series Data

Store timestamps and values in parallel `Float64Array`s for cache-friendly access. Convert dates with `+d.date` (ms since epoch).

## Overview + Detail

The canonical time-series interaction: a small overview shows the full range, a brush selects a window, and the main chart zooms to that window.

### Architecture

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

// Overview: simplified area or line
const overviewArea = d3.area()
    .x(d => xOverview(d.date))
    .y0(overviewHeight)
    .y1(d => yOverview(d.value));

overviewG.append("path")
  .datum(data)
    .attr("d", overviewArea)
    .attr("fill", "steelblue")
    .attr("fill-opacity", 0.15);

// Brush on overview
const brush = d3.brushX()
    .extent([[0, 0], [width, overviewHeight]])
    .on("brush end", brushed);

overviewG.append("g").call(brush);

function brushed(event) {
  if (!event.selection) return;
  const [x0, x1] = event.selection.map(xOverview.invert);
  xMain.domain([x0, x1]);

  // Update main chart axes and paths
  mainXAxisG.call(d3.axisBottom(xMain));
  mainLine.attr("d", lineGen);
}
```

### Key details

- **Use `scaleUtc` for the overview** even if the main chart uses `scaleTime` — the overview rarely needs DST precision and UTC avoids spring-forward glitches at full-year zoom.
- **Downsample on brush** — when the user zooms into a narrow window, re-run LTTB on the visible slice to keep point count ≈ `2 × width`.
- **Animate domain changes** — `xMain.domain(newDomain)` is instant; wrap axis and path updates in a shared transition for smooth zooming.
- **Programmatic brush.move** — to set the brush from buttons (e.g., "Last 6 months"), call `brushG.transition().call(brush.move, [x0, x1])`. This triggers the `brushed` handler via the transition, so don't also call the update function manually (double render).
- **Snap to intervals** — in the `end` event, snap the selection to day/week/month boundaries with `interval.floor(start)` and `interval.ceil(end)`, then call `brush.move` with the snapped pixels.

## Common Pitfalls

**scaleTime domain must be Date objects.** Passing strings or epoch numbers to `scaleTime.domain()` silently produces wrong results.

**Brush coordinates in zoomed space.** When combining brush and zoom, the brush operates in pixel coordinates but the scale may be transformed. Use `transform.rescaleX(x).invert()` to convert brush pixels to data coordinates, not `x.invert()`.

**rAF scheduling in real-time charts.** Calling `requestAnimationFrame(redraw)` inside every WebSocket `onmessage` creates redundant frames. Gate with a flag: schedule one rAF, process all pending data in that frame.

## References

- [LTTB Algorithm](https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf) — Steinarsson's downsampling thesis
- [Horizon Chart](https://observablehq.com/@d3/horizon-chart) — D3 horizon chart example
- [Focus + Context via Brushing](https://observablehq.com/@d3/focus-context) — canonical overview+detail pattern
