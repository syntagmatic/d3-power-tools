---
name: temporal-time-series
description: "Build time-series visualizations with D3.js. Use this skill when the user wants line charts over time, horizon charts, swimlane/event timelines, Gantt charts, cycle plots, real-time streaming charts, brushed time selection, or multi-series spaghetti plots. Covers d3.scaleTime/scaleUtc, time parsing/formatting, DST handling, gap detection, downsampling (LTTB), Canvas rendering for large time series, overview+detail, and crosshair tooltips."
---

# Temporal Time Series

Patterns for building time-series visualizations with D3.js v7+. Covers time scales, time-aware axes, gap handling, horizon charts, swimlane timelines, Gantt charts, cycle plots, real-time streaming, brushed time selection, and multi-series line charts.

For axis customization and tick formatting, see `axes-and-scales`. For brush mechanics, see `brushing-and-selection`. For zoom integration, see `zoom-and-pan`. For Canvas performance patterns, see `canvas-rendering`. For animated transitions, see `animated-transitions`. For callout annotations on time series, see `annotations-and-labels`.

## Time Scales

### scaleTime vs scaleUtc

`d3.scaleTime` interprets domain values in the browser's local timezone. `d3.scaleUtc` interprets them in UTC. Choose based on your audience:

```js
// Local time — good for dashboards where users expect their timezone
const x = d3.scaleTime()
  .domain([new Date("2024-01-01"), new Date("2024-12-31")])
  .range([0, width]);

// UTC — good for multi-timezone data, server logs, scientific data
const x = d3.scaleUtc()
  .domain([new Date("2024-01-01T00:00:00Z"), new Date("2024-12-31T23:59:59Z")])
  .range([0, width]);
```

Use `scaleUtc` when the data has explicit UTC timestamps or when DST jumps would distort the axis. Use `scaleTime` when displaying data in the user's local context (weather, commute times, local events).

### Date Parsing

D3's `d3.timeParse` is explicit about format. The native `Date` constructor has timezone traps.

```js
// d3.timeParse — explicit, predictable
const parseDate = d3.timeParse("%Y-%m-%d");
parseDate("2024-03-15"); // local midnight, always

// d3.utcParse — explicit UTC
const parseUTC = d3.utcParse("%Y-%m-%dT%H:%M:%SZ");
parseUTC("2024-03-15T08:30:00Z"); // UTC, always

// Native Date constructor — DANGER: inconsistent timezone behavior
new Date("2024-03-15");          // UTC midnight (date-only = UTC)
new Date("2024-03-15T00:00");    // LOCAL midnight (datetime without Z = local)
new Date("2024-03-15T00:00:00Z"); // UTC midnight (explicit Z)
```

Always use `d3.timeParse` or `d3.utcParse` for data loading. Reserve the `Date` constructor for programmatic dates where you control the format.

### Date Formatting

```js
const formatMonth = d3.timeFormat("%B %Y");       // "March 2024"
const formatDay = d3.timeFormat("%b %d");          // "Mar 15"
const formatTime = d3.timeFormat("%H:%M");         // "08:30"
const formatISO = d3.utcFormat("%Y-%m-%dT%H:%MZ"); // "2024-03-15T08:30Z"
```

### DST Handling

Daylight Saving Time creates days with 23 or 25 hours. `d3.scaleTime` handles this correctly via the Date API — the visual gap between 1 AM and 3 AM on a spring-forward day is half the normal two-hour span.

When computing durations, use millisecond math (`(end - start) / 3.6e6`) which is DST-safe. When showing intraday data that crosses DST boundaries, prefer `scaleUtc` with formatted local-time tick labels to avoid visual compression/expansion at the transition.

## Time-Aware Axes

### Automatic Multi-Resolution Ticks

`d3.scaleTime` and `d3.scaleUtc` automatically choose tick intervals based on the domain extent. A 1-year domain gets monthly ticks; a 1-day domain gets hourly ticks.

```js
const xAxis = d3.axisBottom(x)
  .ticks(width / 80);  // roughly one tick per 80px — D3 picks the interval

svg.append("g")
  .attr("transform", `translate(0,${height})`)
  .call(xAxis);
```

### Custom Multi-Level Tick Format

Show different formats at different zoom levels — hours when zoomed in, months when zoomed out:

```js
const multiFormat = (date) => {
  if (d3.timeSecond(date) < date) return d3.timeFormat(".%L")(date);
  if (d3.timeMinute(date) < date) return d3.timeFormat(":%S")(date);
  if (d3.timeHour(date) < date) return d3.timeFormat("%H:%M")(date);
  if (d3.timeDay(date) < date) return d3.timeFormat("%H:%M")(date);
  if (d3.timeMonth(date) < date) return d3.timeFormat("%b %d")(date);
  if (d3.timeYear(date) < date) return d3.timeFormat("%B")(date);
  return d3.timeFormat("%Y")(date);
};

const xAxis = d3.axisBottom(x).tickFormat(multiFormat);
```

### Two-Level Axis (Year Below, Month Above)

```js
// Primary axis: months
const monthAxis = d3.axisBottom(x)
  .ticks(d3.timeMonth.every(1))
  .tickFormat(d3.timeFormat("%b"));

svg.append("g")
  .attr("transform", `translate(0,${height})`)
  .call(monthAxis);

// Secondary axis: years — tick at Jan 1 of each year
const yearAxis = d3.axisBottom(x)
  .ticks(d3.timeYear.every(1))
  .tickFormat(d3.timeFormat("%Y"))
  .tickSize(-height)
  .tickPadding(20);

svg.append("g")
  .attr("transform", `translate(0,${height + 22})`)
  .call(yearAxis)
  .call(g => g.select(".domain").remove())
  .call(g => g.selectAll(".tick line")
    .attr("stroke", "#ddd")
    .attr("stroke-dasharray", "2,2"));
```

### Responsive Tick Count

Adjust tick density based on width to prevent label collisions. Use `d3.axisBottom(x).ticks(width / 80)` as a baseline. For finer control, choose the interval explicitly based on domain span:

```js
function responsiveTimeTicks(scale, width) {
  const spanDays = (scale.domain()[1] - scale.domain()[0]) / 8.64e7;
  const maxTicks = Math.floor(width / 80);
  if (spanDays > 365 * 5) return scale.ticks(d3.timeYear.every(Math.ceil(spanDays / 365 / maxTicks)));
  if (spanDays > 365) return scale.ticks(d3.timeMonth.every(Math.ceil(12 / maxTicks)));
  if (spanDays > 60) return scale.ticks(d3.timeWeek.every(Math.ceil(spanDays / 7 / maxTicks)));
  return scale.ticks(maxTicks);
}
```

## Gap Handling

### Detecting Gaps in Irregular Data

Time-series data often has gaps — missing readings, weekends in financial data, outages. Detect gaps by comparing consecutive timestamps to a threshold:

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

// For daily data, flag gaps > 1.5 days
const gaps = detectGaps(data, 1.5 * 8.64e7);
```

### Breaking Lines at Gaps

Use the line generator's `.defined()` to break lines at gaps or null values:

```js
// Break at null/undefined values
const line = d3.line()
  .x(d => x(d.date))
  .y(d => y(d.value))
  .defined(d => d.value != null);

// Break at time gaps — insert null sentinels
function insertGapSentinels(data, maxGapMs) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    if (i > 0 && (data[i].date - data[i - 1].date) > maxGapMs) {
      result.push({ date: data[i - 1].date, value: null }); // sentinel
    }
    result.push(data[i]);
  }
  return result;
}

const dataWithGaps = insertGapSentinels(data, 2 * 8.64e7);
svg.append("path")
  .datum(dataWithGaps)
  .attr("d", line)
  .attr("fill", "none")
  .attr("stroke", "steelblue");
```

### Weekend/Holiday Gaps in Financial Data

For stock data, skip non-trading days on the axis. Use `d3.scaleBand` or a custom ordinal approach instead of `scaleTime`:

```js
// Option 1: Band scale on trading days only — evenly spaced
const tradingDays = data.map(d => d.date);
const x = d3.scaleBand()
  .domain(tradingDays)
  .range([0, width])
  .padding(0.1);

// Option 2: scaleTime but break the line at weekends
const isWeekday = d => d.date.getDay() !== 0 && d.date.getDay() !== 6;
const line = d3.line()
  .defined(isWeekday)
  .x(d => x(d.date))
  .y(d => y(d.close));
```

## Horizon Charts

Horizon charts layer a time-series area chart into colored bands, encoding magnitude by color intensity and sign by hue. They fit many series into a small vertical space.

### Basic Horizon Chart

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

For Canvas rendering with many horizon rows, use the same band/sign loop but draw with `ctx.beginPath()` / `ctx.fill()` and `ctx.globalAlpha = (band + 1) / bands`. See `canvas-rendering` for retina scaling and double-buffering.

## Swimlanes / Event Timelines

Categorical y-axis with temporal x-axis. Each lane shows events as bars or spans.

### Basic Swimlane

```js
const lanes = [...new Set(events.map(d => d.category))];
const laneScale = d3.scaleBand()
  .domain(lanes)
  .range([0, height])
  .padding(0.15);

const x = d3.scaleTime()
  .domain(d3.extent(events.flatMap(d => [d.start, d.end])))
  .range([0, width]);

svg.selectAll(".event")
  .data(events)
  .join("rect")
    .attr("class", "event")
    .attr("x", d => x(d.start))
    .attr("y", d => laneScale(d.category))
    .attr("width", d => Math.max(2, x(d.end) - x(d.start)))
    .attr("height", laneScale.bandwidth())
    .attr("rx", 3)
    .attr("fill", d => colorScale(d.category));

// Lane labels
svg.selectAll(".lane-label")
  .data(lanes)
  .join("text")
    .attr("x", -8)
    .attr("y", d => laneScale(d) + laneScale.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", "end")
    .attr("font-size", "12px")
    .text(d => d);
```

### Overlapping Event Stacking

When events in the same lane overlap, stack them into sub-rows. Sort by start time, then greedily assign each event to the first sub-row whose last event ends before this one starts. Track per-row end times in an array; if no row fits, create a new one. Set `event.row` for y-offset within the lane.

## Gantt Charts

Task bars with time extent, dependencies, progress, and hierarchy.

### Basic Gantt

```js
const taskScale = d3.scaleBand()
  .domain(tasks.map(d => d.name))
  .range([0, height])
  .padding(0.2);

const x = d3.scaleTime()
  .domain([d3.min(tasks, d => d.start), d3.max(tasks, d => d.end)])
  .range([0, width]);

// Task bars
svg.selectAll(".task")
  .data(tasks)
  .join("rect")
    .attr("class", "task")
    .attr("x", d => x(d.start))
    .attr("y", d => taskScale(d.name))
    .attr("width", d => x(d.end) - x(d.start))
    .attr("height", taskScale.bandwidth())
    .attr("rx", 3)
    .attr("fill", "#4e79a7");

// Progress fill overlay
svg.selectAll(".progress")
  .data(tasks)
  .join("rect")
    .attr("class", "progress")
    .attr("x", d => x(d.start))
    .attr("y", d => taskScale(d.name))
    .attr("width", d => (x(d.end) - x(d.start)) * d.progress)
    .attr("height", taskScale.bandwidth())
    .attr("rx", 3)
    .attr("fill", "#59a14f");

// Milestone markers (diamond)
svg.selectAll(".milestone")
  .data(tasks.filter(d => d.milestone))
  .join("path")
    .attr("d", d3.symbol().type(d3.symbolDiamond).size(120))
    .attr("transform", d => `translate(${x(d.start)},${taskScale(d.name) + taskScale.bandwidth() / 2})`)
    .attr("fill", "#e15759");
```

### Dependency Arrows

```js
function drawDependencies(svg, tasks, deps, x, taskScale) {
  const taskMap = new Map(tasks.map(d => [d.id, d]));

  // Arrow marker
  svg.append("defs").append("marker")
    .attr("id", "arrow").attr("viewBox", "0 0 10 10")
    .attr("refX", 10).attr("refY", 5)
    .attr("markerWidth", 8).attr("markerHeight", 8).attr("orient", "auto")
    .append("path").attr("d", "M0,0 L10,5 L0,10 Z").attr("fill", "#999");

  svg.selectAll(".dependency")
    .data(deps)
    .join("path")
      .attr("d", d => {
        const from = taskMap.get(d.from), to = taskMap.get(d.to);
        const x1 = x(from.end), y1 = taskScale(from.name) + taskScale.bandwidth() / 2;
        const x2 = x(to.start), y2 = taskScale(to.name) + taskScale.bandwidth() / 2;
        return `M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}`;
      })
      .attr("fill", "none").attr("stroke", "#999")
      .attr("stroke-width", 1.5).attr("marker-end", "url(#arrow)");
}
```

For critical path highlighting, compute slack via forward/backward pass on the dependency DAG, then stroke tasks with zero slack in a contrasting color.

## Cycle Plots

Decompose a time series by recurring period (day-of-week, hour-of-day, month) to reveal seasonality. Each panel shows all observations for one cycle position.

### Day-of-Week Cycle Plot

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

  panel.append("text")
    .attr("x", panelWidth / 2).attr("y", panelHeight + 16)
    .attr("text-anchor", "middle").attr("font-size", "11px").text(name);
});
```

## Real-Time / Streaming

### Sliding Window with Domain Shift

Append new data and shift the time domain instead of rebuilding everything:

```js
const windowMs = 60_000; // 60-second window
const data = [];

function appendPoint(point) {
  data.push(point);
  const now = point.date;

  // Trim old data outside the window
  while (data.length > 0 && data[0].date < now - windowMs) {
    data.shift();
  }

  // Shift the domain — no scale rebuild
  x.domain([now - windowMs, now]);

  // Update axis with short transition for smooth scrolling
  xAxisGroup.transition().duration(100).ease(d3.easeLinear).call(xAxis);

  // Redraw line
  path.datum(data).attr("d", line);
}
```

### Circular Buffer Pattern

Avoid `Array.shift()` (O(n)) for high-frequency data. Use a circular buffer:

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

  // Iterate from oldest to newest
  *[Symbol.iterator]() {
    const start = this.size < this.capacity ? 0 : this.head;
    for (let i = 0; i < this.size; i++) {
      yield this.buffer[(start + i) % this.capacity];
    }
  }

  toArray() { return [...this]; }
}

const buffer = new CircularBuffer(2000); // keep last 2000 points
```

### requestAnimationFrame Gating

When data arrives faster than the screen refreshes, batch updates to avoid redundant draws:

```js
let pendingData = [];
let rafId = null;

function onData(point) {
  pendingData.push(point);
  if (!rafId) {
    rafId = requestAnimationFrame(flush);
  }
}

function flush() {
  rafId = null;
  // Process all pending points in one batch
  for (const point of pendingData) {
    buffer.push(point);
  }
  pendingData = [];
  redraw();
}
```

### WebSocket Integration

```js
const ws = new WebSocket("wss://data-feed.example.com/stream");
ws.onmessage = (event) => {
  const point = JSON.parse(event.data);
  point.date = new Date(point.timestamp);
  onData(point); // funnels through rAF gate above
};
ws.onclose = () => setTimeout(() => connectWebSocket(), Math.min(30000, retryDelay *= 2));
```

### Canvas Double-Buffering

Prevent flicker by drawing to an offscreen canvas, then copying in one operation:

```js
const offscreen = document.createElement("canvas");
offscreen.width = canvas.width; offscreen.height = canvas.height;
const offCtx = offscreen.getContext("2d");

function redraw() {
  offCtx.clearRect(0, 0, offscreen.width, offscreen.height);
  drawAxes(offCtx);
  drawLine(offCtx, buffer.toArray());
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(offscreen, 0, 0);
}
```

### Memory Leak Prevention

1. **Bound your data** — use `CircularBuffer` or trim after each append, never unbounded `push()`
2. **Remove old DOM** — use proper enter/update/exit joins with a key function
3. **Cancel on teardown** — `cancelAnimationFrame(rafId)`, `ws.close()`, `ro.disconnect()`
4. **Avoid stale closures** — don't capture growing arrays in long-lived callbacks; reference the buffer directly

## Brushed Time Selection

### Overview + Detail Pattern

A small overview chart controls the time range of a larger detail chart via brushing:

```js
// Detail chart (main)
const xDetail = d3.scaleTime().domain(x.domain()).range([0, width]);
const yDetail = d3.scaleLinear().domain(y.domain()).range([detailHeight, 0]);

// Overview chart (small, below)
const xOverview = d3.scaleTime().domain(x.domain()).range([0, width]);
const yOverview = d3.scaleLinear().domain(y.domain()).range([overviewHeight, 0]);

// Brush on overview
const brush = d3.brushX()
  .extent([[0, 0], [width, overviewHeight]])
  .on("brush end", brushed);

overviewSvg.append("g").call(brush);

function brushed({ selection }) {
  if (!selection) {
    xDetail.domain(xOverview.domain());
  } else {
    xDetail.domain(selection.map(xOverview.invert));
  }
  // Update detail chart
  detailPath.attr("d", detailLine);
  detailAxisGroup.call(d3.axisBottom(xDetail));
}
```

### Snap-to-Interval

Snap brush extents to the nearest day, week, or month by converting pixel selection to dates via `xOverview.invert`, applying `interval.floor(start)` and `interval.ceil(end)`, then calling `brush.move` with the snapped pixel positions in the `end` event.

### Formatted Brush Handles

Show date labels at brush edges by appending `<text>` elements positioned at each handle's x-coordinate, updated in the `brush` event with `d3.timeFormat("%b %d, %Y")(xOverview.invert(selection[i]))`.

### Brush-to-Zoom with Animated Transition

```js
const brush = d3.brushX()
  .extent([[0, 0], [width, height]])
  .on("end", ({ selection }) => {
    if (!selection) return;
    const [x0, x1] = selection.map(x.invert);
    svg.select(".brush").call(brush.move, null); // clear the brush

    // Animate zoom to selected range
    x.domain([x0, x1]);
    svg.select(".line")
      .transition().duration(750)
      .attr("d", line);
    svg.select(".x-axis")
      .transition().duration(750)
      .call(d3.axisBottom(x));
  });
```

## Multi-Series

### Spaghetti Plot with Highlight

```js
const series = d3.groups(data, d => d.series);
const color = d3.scaleOrdinal(d3.schemeTableau10).domain(series.map(([key]) => key));

const line = d3.line()
  .x(d => x(d.date))
  .y(d => y(d.value));

const paths = svg.selectAll(".series")
  .data(series)
  .join("path")
    .attr("class", "series")
    .attr("d", ([, values]) => line(values))
    .attr("fill", "none")
    .attr("stroke", ([key]) => color(key))
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.7);

// Highlight on hover: dim all others
paths.on("pointerenter", function () {
  paths.attr("stroke-opacity", 0.1);
  d3.select(this).attr("stroke-opacity", 1).attr("stroke-width", 2.5).raise();
}).on("pointerleave", () => {
  paths.attr("stroke-opacity", 0.7).attr("stroke-width", 1.5);
});
```

### Voronoi-Based Nearest-Series Detection

For dense multi-series charts, hit-testing individual lines is unreliable. Use a Voronoi overlay to find the nearest point across all series:

```js
const allPoints = series.flatMap(([key, values]) =>
  values.map(d => ({ ...d, series: key }))
);

const delaunay = d3.Delaunay.from(allPoints, d => x(d.date), d => y(d.value));

svg.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event);
  const idx = delaunay.find(mx, my);
  const nearest = allPoints[idx];

  // Highlight the nearest series
  paths.attr("stroke-opacity", ([key]) => key === nearest.series ? 1 : 0.1)
       .attr("stroke-width", ([key]) => key === nearest.series ? 2.5 : 1);

  // Show tooltip at the nearest point
  tooltip
    .style("opacity", 1)
    .style("left", `${event.pageX + 12}px`)
    .style("top", `${event.pageY - 12}px`)
    .html(`<strong>${nearest.series}</strong><br>${d3.timeFormat("%b %d")(nearest.date)}: ${nearest.value}`);
});
```

### Interactive Legend

Toggle series visibility on legend click. Track hidden series in a `Set`, then set `display: none` on hidden paths and reduce legend swatch opacity to 0.2 for hidden items.

## Interaction Recipes

### Crosshair with Vertical Rule

Show a vertical rule at the cursor position with tooltip listing all series values at that time:

```js
const rule = svg.append("line")
  .attr("class", "crosshair")
  .attr("y1", 0).attr("y2", height)
  .attr("stroke", "#999")
  .attr("stroke-width", 1)
  .attr("stroke-dasharray", "3,3")
  .style("display", "none");

const bisect = d3.bisector(d => d.date).left;

svg.on("pointermove", (event) => {
  const [mx] = d3.pointer(event);
  const date = x.invert(mx);

  rule.attr("x1", mx).attr("x2", mx).style("display", null);

  // Find value at this date for each series
  const rows = series.map(([key, values]) => {
    const i = bisect(values, date);
    const d = i > 0 && (i >= values.length || date - values[i - 1].date < values[i].date - date)
      ? values[i - 1] : values[i];
    return d ? `<span style="color:${color(key)}">${key}</span>: ${d.value.toFixed(1)}` : null;
  }).filter(Boolean);

  tooltip
    .style("opacity", 1)
    .html(`<strong>${d3.timeFormat("%b %d, %Y")(date)}</strong><br>${rows.join("<br>")}`)
    .style("left", `${event.pageX + 15}px`)
    .style("top", `${event.pageY - 10}px`);
});

svg.on("pointerleave", () => {
  rule.style("display", "none");
  tooltip.style("opacity", 0);
});
```

### Zoom with Time Axis

Use `transform.rescaleX(x)` to get a zoomed time scale, then update axis and line with the new scale. See `zoom-and-pan` for the full pattern including `scaleExtent`, `translateExtent`, minimap, and programmatic zoom-to-fit.

### Play/Pause Time Scrubber

Animate a vertical marker through time using `requestAnimationFrame`. Each frame advances `currentTime` by `speed * 16` ms (one frame at 60fps), repositions the marker line, and clips the data path to `data.filter(d => d.date <= currentTime)`. A play/pause button toggles the `playing` flag; an `<input type="range">` scrubber maps 0-1 to the time domain for manual seeking. See `animated-transitions` for easing and stagger patterns.

## Performance

### Canvas Rendering for Large Time Series

For 10K+ data points, Canvas outperforms SVG:

```js
function drawLineCanvas(ctx, data, x, y, color = "steelblue") {
  ctx.beginPath();
  let started = false;
  for (const d of data) {
    if (d.value == null) { started = false; continue; }
    const px = x(d.date), py = y(d.value);
    if (!started) { ctx.moveTo(px, py); started = true; }
    else ctx.lineTo(px, py);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
```

### LTTB Downsampling (Largest Triangle Three Buckets)

Reduce point count while preserving visual shape. LTTB keeps perceptually important peaks and valleys:

```js
function lttb(data, threshold) {
  if (threshold >= data.length || threshold < 3) return data;

  const sampled = [data[0]]; // always keep first point
  const bucketSize = (data.length - 2) / (threshold - 2);

  let prevIdx = 0;
  for (let i = 0; i < threshold - 2; i++) {
    const bucketStart = Math.floor((i + 0) * bucketSize) + 1;
    const bucketEnd = Math.floor((i + 1) * bucketSize) + 1;

    // Average of next bucket (used as target for triangle area)
    const nextStart = Math.floor((i + 1) * bucketSize) + 1;
    const nextEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length);
    let avgX = 0, avgY = 0;
    for (let j = nextStart; j < nextEnd; j++) {
      avgX += +data[j].date;
      avgY += data[j].value;
    }
    avgX /= (nextEnd - nextStart);
    avgY /= (nextEnd - nextStart);

    // Find the point in this bucket that forms the largest triangle
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

  sampled.push(data[data.length - 1]); // always keep last point
  return sampled;
}

// Usage: reduce 100K points to 1000 for rendering
const downsampled = lttb(data, Math.min(data.length, width * 2));
```

### Min-Max Bucketing

Simpler than LTTB: for each pixel column, keep min and max values. Loop over data, bucket by `Math.floor(x(d.date))`, track min/max per bucket, then flatten to `[min, max, min, max, ...]`. Produces at most `2 * pixelWidth` points.

### Virtual Windowing

Only render the visible time range. Use `d3.bisector(d => d.date)` to find the start/end indices within the sorted data array, slice, then downsample:

```js
function getVisibleData(data, domain) {
  const bisect = d3.bisector(d => d.date);
  const i0 = Math.max(0, bisect.left(data, domain[0]) - 1);
  const i1 = Math.min(data.length, bisect.right(data, domain[1]) + 1);
  return data.slice(i0, i1);
}
```

Combine with zoom: on each `zoom` event, call `getVisibleData` with the rescaled domain, then `lttb(visible, width * 2)` before drawing.

### TypedArray for Time-Series Data

Store timestamps and values in parallel `Float64Array`s for cache-friendly access. Convert dates with `+d.date` (ms since epoch). Binary search on typed arrays is fast — use `d3.bisector` or a manual bisect loop for windowing.

## Common Pitfalls

**Date constructor timezone trap.** `new Date("2024-01-15")` parses as UTC midnight. `new Date("2024-01-15T00:00")` parses as local midnight. This inconsistency is the #1 source of off-by-one-day bugs. Always use `d3.timeParse` or `d3.utcParse` for data loading.

**scaleTime domain must be Date objects.** Passing strings or epoch numbers to `scaleTime.domain()` silently produces wrong results. Always ensure domain values are `Date` instances: `x.domain([new Date(start), new Date(end)])`.

**Line generator with missing data.** Without `.defined(d => d.value != null)`, the line generator draws to (0, 0) for null values, creating spikes to the origin. Always set `.defined()` when data may have gaps.

**requestAnimationFrame scheduling in real-time charts.** Calling `requestAnimationFrame(redraw)` inside every WebSocket `onmessage` creates redundant frames. Gate with a flag: schedule one rAF, process all pending data in that frame.

**Memory leaks in real-time charts.** Unbounded `data.push()` without trimming old data causes memory growth. Use a circular buffer or trim after each append. Also clean up event listeners and cancel animation frames on teardown.

**Array.shift() is O(n).** In sliding-window patterns, `data.shift()` copies the entire array on every call. For high-frequency data (>10 updates/sec), use a circular buffer instead.

**Brush coordinates in zoomed space.** When combining brush and zoom, the brush operates in pixel coordinates but the scale may be transformed. Use `transform.rescaleX(x).invert()` to convert brush pixels to data coordinates, not `x.invert()`.

**DST double-hour in scaleTime.** On fall-back days, 1:00-1:59 AM occurs twice. If your data has timestamps in this range, they may plot on top of each other with `scaleTime`. Use `scaleUtc` for sub-hourly data near DST boundaries.

**Horizon chart color mapping.** Increasing band count increases information density but requires careful color ramp design. Beyond 4 bands, differences between adjacent bands become hard to distinguish. Stick to 3-4 bands for most use cases.

**LTTB on multi-series data.** Downsample each series independently. Downsampling all series together or using the same sample indices across series distorts individual series shapes.

## References

- [D3 Time Scales](https://d3js.org/d3-scale/time) — scaleTime and scaleUtc API
- [D3 Time Formats](https://d3js.org/d3-time-format) — d3.timeParse, d3.timeFormat
- [D3 Time Intervals](https://d3js.org/d3-time) — d3.timeDay, d3.timeWeek, d3.timeMonth
- [Focus + Context via Brushing](https://observablehq.com/@d3/focus-context) — canonical overview+detail pattern
- [Horizon Chart](https://observablehq.com/@d3/horizon-chart) — D3 horizon chart example
- [LTTB Algorithm](https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf) — Steinarsson's downsampling thesis
- [Gantt Chart](https://observablehq.com/@d3/gantt-chart) — D3 Gantt chart example
- [D3 Zoom](https://d3js.org/d3-zoom) — zoom API for time axis integration
- [D3 Brush](https://d3js.org/d3-brush) — brush API for time selection
