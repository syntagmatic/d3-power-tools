# Time-Series Visualization Research

Research into techniques beyond current d3-power-tools coverage.

## Current Coverage

The existing `skills/time-series/SKILL.md` covers:

- **scaleTime vs scaleUtc** -- DST pitfalls, when to use each
- **Gap detection** -- sentinel insertion, `.defined()`, weekend/holiday gaps in financial data
- **Horizon charts** -- band folding, color encoding, band count guidance (Heer et al.)
- **Cycle plots** -- seasonal decomposition by recurring period
- **Swimlanes** -- overlapping event stacking with greedy row assignment
- **Real-time streaming** -- circular buffer, rAF gating, memory leak prevention
- **Voronoi nearest-series** -- Delaunay-based hit detection for dense multi-series
- **LTTB downsampling** -- shape-preserving reduction, min-max bucketing, virtual windowing
- **TypedArray optimization** -- Float64Array for cache-friendly iteration at 100K+
- **Overview + detail** -- brush-linked zoom with programmatic snap-to-interval

**Not covered:** multi-scale temporal drill-down, anomaly/prediction bands, calendar heatmaps, annotation bands/event markers, Observable Plot's difference mark and shift transform patterns.

## Multi-Scale Time (temporal drill-down, year->day->hour)

### What question it answers

"What does this annual pattern look like at the hourly level?" -- letting viewers start from a high-level overview and drill into progressively finer temporal resolution without losing context. Standard zoom just stretches the same axis; semantic temporal zoom changes the *representation* at each level.

### Approach

Semantic zoom on the time axis: as the user zooms, switch between temporal aggregation levels (year -> month -> week -> day -> hour -> minute). Each level uses a different data resolution and axis tick format.

**Key insight from research (TU Wien SemTimeZoom, IEEE VIS 2024):** At each zoom level, use a *qualitative abstraction* -- don't just show more points, change what the marks represent. Yearly view shows monthly aggregates as bars; daily view shows hourly line; minute view shows raw samples.

### D3 implementation

```js
// Determine aggregation level from visible domain span
function getTemporalLevel(domain) {
  const spanMs = domain[1] - domain[0];
  if (spanMs > 365 * 86400000) return { interval: d3.utcMonth, format: "%b %Y" };
  if (spanMs > 30 * 86400000) return { interval: d3.utcWeek, format: "%b %d" };
  if (spanMs > 7 * 86400000) return { interval: d3.utcDay, format: "%a %d" };
  if (spanMs > 86400000) return { interval: d3.utcHour, format: "%H:%M" };
  return { interval: d3.utcMinute, format: "%H:%M:%S" };
}

// On zoom, re-aggregate and re-render
function onZoom(transform) {
  const newX = transform.rescaleX(xBase);
  const domain = newX.domain();
  const { interval, format } = getTemporalLevel(domain);

  // Re-aggregate data to current level
  const binned = d3.rollups(
    data.filter(d => d.date >= domain[0] && d.date <= domain[1]),
    v => d3.mean(v, d => d.value),
    d => interval.floor(d.date)
  ).map(([date, value]) => ({ date, value }));

  // Switch mark type based on level
  if (interval === d3.utcMonth || interval === d3.utcWeek) {
    renderBars(binned, newX);  // aggregates as bars
  } else {
    renderLine(binned, newX);  // fine resolution as line
  }

  xAxisG.call(d3.axisBottom(newX).ticks(interval).tickFormat(d3.utcFormat(format)));
}
```

### When to use

- Datasets spanning years but with sub-hourly granularity available
- Exploratory dashboards where users need both "big picture" and "what happened at 3 PM"
- Alternative to overview+detail when vertical space is limited (single chart vs two)

### When NOT to use

- If only one temporal resolution exists in the data
- If the viewer needs to see both macro and micro simultaneously (use overview+detail instead)
- Narrative/presentation contexts where the author controls the view

### Performance

- Pre-compute aggregates per level to avoid re-rolling on every zoom frame
- Use `d3.bisector` to slice visible range before aggregating
- At fine zoom levels, apply LTTB on the visible slice

## Anomaly Bands and Prediction Intervals (confidence regions, threshold alerts)

### What question it answers

"Is this value normal?" -- showing expected ranges so deviations are immediately visible without mental comparison to past values. Standard line charts show what happened but not whether it's surprising.

### Approach

Layer an `d3.area()` band behind the data line, where y0/y1 map to the prediction interval bounds. Anomalous points that fall outside the band get highlighted with distinct marks.

### D3 implementation

```js
// Data shape: { date, value, lower95, upper95, lower50, upper50 }

// Outer band (95% CI) -- light fill
const band95 = d3.area()
  .x(d => x(d.date))
  .y0(d => y(d.lower95))
  .y1(d => y(d.upper95))
  .curve(d3.curveMonotoneX);

// Inner band (50% CI) -- darker fill
const band50 = d3.area()
  .x(d => x(d.date))
  .y0(d => y(d.lower50))
  .y1(d => y(d.upper50))
  .curve(d3.curveMonotoneX);

// Draw bands back-to-front
g.append("path").datum(data).attr("d", band95)
  .attr("fill", "steelblue").attr("fill-opacity", 0.1);
g.append("path").datum(data).attr("d", band50)
  .attr("fill", "steelblue").attr("fill-opacity", 0.2);

// Actual line on top
g.append("path").datum(data).attr("d", line)
  .attr("fill", "none").attr("stroke", "steelblue").attr("stroke-width", 1.5);

// Anomaly markers -- points outside 95% band
const anomalies = data.filter(d => d.value < d.lower95 || d.value > d.upper95);
g.selectAll(".anomaly")
  .data(anomalies)
  .join("circle")
    .attr("cx", d => x(d.date))
    .attr("cy", d => y(d.value))
    .attr("r", 4)
    .attr("fill", "red")
    .attr("stroke", "white")
    .attr("stroke-width", 1.5);
```

**D3-Foresight** (reichlab.io) is a purpose-built library for forecast visualization with confidence intervals, but the pattern above is simple enough to implement directly.

### Nested confidence bands

Use graduated opacity for multiple confidence levels (50%, 80%, 95%). This is a "fan chart" -- the Bank of England's inflation forecasts popularized this form. Key: draw widest band first (lowest opacity), narrowest last.

### Threshold lines with alert zones

```js
// Static threshold with shaded alert zone
const threshold = 100;
g.append("rect")
  .attr("x", 0).attr("width", width)
  .attr("y", 0).attr("height", y(threshold))
  .attr("fill", "red").attr("fill-opacity", 0.05);

g.append("line")
  .attr("x1", 0).attr("x2", width)
  .attr("y1", y(threshold)).attr("y2", y(threshold))
  .attr("stroke", "red").attr("stroke-dasharray", "6,3");
```

### When to use

- Monitoring dashboards where "out of bounds" is the primary signal
- Forecast visualization (weather, finance, capacity planning)
- Any time the viewer needs to judge whether a value is normal vs unusual

### When NOT to use

- If no statistical model provides bounds (don't fabricate confidence intervals)
- If the data is already aggregated -- bands on aggregated data can mislead about underlying variance

### Performance

- Bands are just area paths -- same cost as a line, no performance concern
- Anomaly markers: if hundreds of anomalies, use Canvas circles instead of SVG

## Calendar Heatmaps (temporal patterns across days/weeks)

### What question it answers

"Are there day-of-week or seasonal patterns?" -- a calendar layout makes weekly rhythms visible that line charts hide. GitHub's contribution chart is the canonical example.

### Approach

Map each day to a cell in a weeks-by-days grid. X = week number (or column within year), Y = day of week (0-6). Fill color encodes the value. Multiple years stack vertically.

### D3 implementation

```js
const cellSize = 17;
const year = d3.groups(data, d => d.date.getUTCFullYear());

// For each year
year.forEach(([yr, values]) => {
  const yearG = svg.append("g")
    .attr("transform", `translate(40, ${yearIndex * (cellSize * 7 + 40)})`);

  const countDay = d => d.date.getUTCDay();
  const timeWeek = d3.utcSunday;
  const countWeek = d => timeWeek.count(d3.utcYear(d.date), d.date);

  const color = d3.scaleSequential(d3.interpolateGreens)
    .domain([0, d3.max(values, d => d.value)]);

  yearG.selectAll("rect")
    .data(values)
    .join("rect")
      .attr("width", cellSize - 1)
      .attr("height", cellSize - 1)
      .attr("x", d => countWeek(d) * cellSize)
      .attr("y", d => countDay(d) * cellSize)
      .attr("fill", d => d.value ? color(d.value) : "#eee")
    .append("title")
      .text(d => `${d3.utcFormat("%Y-%m-%d")(d.date)}: ${d.value}`);

  // Month boundaries
  yearG.selectAll(".month")
    .data(d3.utcMonths(new Date(yr, 0, 1), new Date(yr + 1, 0, 1)))
    .join("path")
      .attr("d", monthPath)  // stepped path around month boundary cells
      .attr("fill", "none")
      .attr("stroke", "#000")
      .attr("stroke-width", 1);
});

function monthPath(t) {
  // Path that traces the boundary of a month in the calendar grid
  const d = t.getUTCDay();
  const w = d3.utcSunday.count(d3.utcYear(t), t);
  return `M${(w + 1) * cellSize},${d * cellSize}` +
    `H${w * cellSize}V${7 * cellSize}` +
    `H${(d3.utcSunday.count(d3.utcYear(t), d3.utcMonth.offset(t, 1)) + 1) * cellSize}` +
    `V0H${(w + 1) * cellSize}Z`;
}
```

### Variants

- **Month-level heatmap**: rows = days of month (1-31), columns = months. Good for multi-year patterns.
- **Hour-of-day x day-of-week**: 7x24 grid. Answers "when do errors happen?" for operational data.
- **Cal-HeatMap library**: configurable temporal granularity (year/month/week/day/hour), with drill-down by click.

### When to use

- Daily data spanning months to years where weekly/seasonal rhythm matters
- Activity/contribution tracking (commits, workouts, sensor readings)
- When the viewer's question is about *when* something happens, not *how much*

### When NOT to use

- Sub-daily data (use hour-of-day x day-of-week heatmap instead)
- If trend matters more than periodicity (line chart is better)
- Sparse data -- empty cells dominate and the pattern is unreadable

### Performance

- 365 rects per year is trivial for SVG
- For decade-scale views (3,650+ rects), still fine in SVG; Canvas unnecessary

## Annotation Bands (event markers, regime changes, Grafana-style)

### What question it answers

"What was happening externally when this metric changed?" -- connecting data patterns to real-world events (deployments, incidents, policy changes, holidays). Without annotations, viewers guess at causation.

### Grafana patterns worth adopting

Grafana's annotation system distinguishes:
1. **Point annotations**: vertical lines at specific times (deployment, incident start)
2. **Range annotations**: shaded bands spanning a time period (maintenance window, feature rollout)
3. **State timelines**: a swimlane showing categorical state over time (healthy/degraded/down)
4. **Cross-panel annotations**: one annotation source visible across all charts in a dashboard

### D3 implementation

```js
// Point annotation -- vertical line + label
function annotatePoint(g, x, date, label, color = "#e15759") {
  const xPos = x(date);
  g.append("line")
    .attr("x1", xPos).attr("x2", xPos)
    .attr("y1", 0).attr("y2", height)
    .attr("stroke", color).attr("stroke-dasharray", "4,2").attr("stroke-width", 1);
  g.append("text")
    .attr("x", xPos + 4).attr("y", 12)
    .attr("fill", color).attr("font-size", 10)
    .text(label);
}

// Range annotation -- shaded band
function annotateRange(g, x, start, end, label, color = "#e15759") {
  const x0 = x(start), x1 = x(end);
  g.append("rect")
    .attr("x", x0).attr("width", x1 - x0)
    .attr("y", 0).attr("height", height)
    .attr("fill", color).attr("fill-opacity", 0.08);
  g.append("text")
    .attr("x", (x0 + x1) / 2).attr("y", 12)
    .attr("text-anchor", "middle")
    .attr("fill", color).attr("font-size", 10)
    .text(label);
}

// State timeline -- horizontal swimlane below chart
function stateTimeline(g, x, states, { laneHeight = 20, y: yOffset = 0 }) {
  const stateColor = d3.scaleOrdinal()
    .domain(["healthy", "degraded", "down"])
    .range(["#59a14f", "#f28e2c", "#e15759"]);

  g.selectAll(".state")
    .data(states)
    .join("rect")
      .attr("x", d => x(d.start))
      .attr("width", d => x(d.end) - x(d.start))
      .attr("y", yOffset)
      .attr("height", laneHeight)
      .attr("fill", d => stateColor(d.state))
      .attr("rx", 2);
}
```

### Rendering order

Draw annotation bands *behind* the data line but *in front of* the grid. Layer order: background -> grid lines -> annotation bands -> data paths -> annotation point lines -> labels. This prevents bands from obscuring data while still being clearly visible.

### When to use

- Ops/monitoring dashboards (deployments, incidents, maintenance windows)
- Any time-series where external events drive changes (policy dates, product launches)
- Combining with linked views -- click an annotation to filter other panels

### When NOT to use

- If there are too many annotations (>10 visible at once), they become noise. Aggregate or filter.
- Static/print contexts where hover tooltips aren't available for annotation detail.

## Observable Plot Time Patterns (what Plot does differently)

### Difference mark

Plot's `differenceY` mark fills the area between two lines with alternating colors based on which is larger. This directly answers "when did metric A exceed metric B?" without requiring the viewer to mentally compare two lines.

D3 equivalent: two clipped area paths.

```js
// Clip path approach: two areas, each clipped to where it's dominant
const areaAbove = d3.area()
  .x(d => x(d.date))
  .y0(d => y(d.valueB))
  .y1(d => y(d.valueA));

// Clip to region where A > B
const clipAbove = svg.append("clipPath").attr("id", "clip-above")
  .append("path").datum(data)
  .attr("d", d3.area()
    .x(d => x(d.date))
    .y0(0)
    .y1(d => y(d.valueA)));

svg.append("path").datum(data)
  .attr("d", areaAbove)
  .attr("clip-path", "url(#clip-above)")
  .attr("fill", "green").attr("fill-opacity", 0.3);

// Mirror for B > A
```

### Shift transform

Plot's `shift` transform derives a time-shifted copy of a series, enabling year-over-year or period-over-period comparison in a single view. Combined with the difference mark, it shows when the current period outperforms or underperforms the comparison period.

D3 equivalent: manually join the series to its shifted self.

```js
// Year-over-year: pair each point with the value from 1 year ago
const shiftMs = 365.25 * 86400000;
const shifted = data.map(d => {
  const pastDate = new Date(+d.date - shiftMs);
  const pastPoint = bisector(data, pastDate);  // find nearest
  return { date: d.date, current: d.value, previous: pastPoint?.value ?? null };
}).filter(d => d.previous != null);
```

### Interval transform

Plot's `interval` transform bins temporal data to regular intervals, which is useful for ensuring uniform spacing even when raw data has irregular timestamps.

### What Plot does differently (philosophy)

- **Marks as question-answerers**: each mark type is designed around a specific analytical question, not a geometric primitive. The difference mark exists because "when does A exceed B?" is a common question.
- **Transforms as data verbs**: shift, window, normalize, bin -- these compose with marks declaratively.
- **Faceting built in**: `fx` and `fy` channels give small multiples for free, replacing manual grid layout.

### Takeaway for D3 skill

These are compositional patterns worth documenting as D3 recipes:
- Difference area (two-clip approach)
- Period-over-period shift-and-join
- Temporal binning with `d3.utcInterval.every(n)`

## Decision Guidance (which time-series chart for which question)

| Viewer question | Best chart | Why not the others |
|---|---|---|
| "What's the trend?" | Line chart | Simplest encoding for temporal continuity |
| "How do 10+ series compare?" | Horizon chart (2-3 bands) | Line spaghetti is unreadable beyond 5 series |
| "Is this value normal?" | Line + prediction band | Horizon charts can't show prediction intervals |
| "When did A exceed B?" | Difference area | Line chart requires mental subtraction |
| "Is Tuesday always slow?" | Cycle plot | Line charts bury weekly seasonality in trend |
| "What day-of-week patterns exist across the year?" | Calendar heatmap | Line charts can't show 2D temporal structure |
| "What happened during this deployment?" | Line + annotation bands | Without annotations, viewers guess at causation |
| "What does the yearly pattern look like hourly?" | Multi-scale drill-down | Overview+detail uses space; drill-down uses time |
| "When were we in a degraded state?" | State timeline | Point annotations can't show duration |
| "How does this year compare to last year?" | Shift + difference area | Overlaid lines are hard to compare precisely |
| "What's the distribution at each time point?" | Fan chart (nested CI bands) | Line shows only central tendency |

### Combining techniques

Common pairings:
- **Line + prediction band + annotation markers**: monitoring dashboard (Grafana-style)
- **Overview+detail + multi-scale ticks**: exploration of large datasets
- **Calendar heatmap + linked line chart**: click a day to see its hourly detail
- **Horizon chart + state timeline below**: compare many metrics with shared event context

## Code Patterns

### Pattern: graduated confidence fan chart

```js
// Confidence levels from widest to narrowest
const levels = [
  { lower: "p5", upper: "p95", opacity: 0.1 },
  { lower: "p20", upper: "p80", opacity: 0.2 },
  { lower: "p35", upper: "p65", opacity: 0.3 },
];

levels.forEach(({ lower, upper, opacity }) => {
  g.append("path")
    .datum(data)
    .attr("d", d3.area()
      .x(d => x(d.date))
      .y0(d => y(d[lower]))
      .y1(d => y(d[upper]))
      .curve(d3.curveMonotoneX))
    .attr("fill", "steelblue")
    .attr("fill-opacity", opacity);
});
```

### Pattern: year-over-year difference

```js
// Join current data with same date last year
function yearOverYear(data) {
  const byDate = new Map(data.map(d => [+d.date, d.value]));
  const oneYear = 365.25 * 86400000;
  return data
    .map(d => ({
      date: d.date,
      current: d.value,
      previous: byDate.get(+d.date - oneYear) ?? null,
    }))
    .filter(d => d.previous != null);
}
```

### Pattern: temporal aggregation for drill-down

```js
// Pre-compute aggregates at each temporal level for instant zoom
function preAggregate(data, levels) {
  const result = {};
  for (const { key, interval, agg } of levels) {
    result[key] = d3.rollups(
      data,
      v => ({
        mean: d3.mean(v, agg),
        min: d3.min(v, agg),
        max: d3.max(v, agg),
        count: v.length,
      }),
      d => interval.floor(d.date)
    ).map(([date, stats]) => ({ date, ...stats }));
  }
  return result;
}

const aggregates = preAggregate(data, [
  { key: "month", interval: d3.utcMonth, agg: d => d.value },
  { key: "week", interval: d3.utcWeek, agg: d => d.value },
  { key: "day", interval: d3.utcDay, agg: d => d.value },
  { key: "hour", interval: d3.utcHour, agg: d => d.value },
]);
```

### Pattern: annotation layer (Grafana-style)

```js
// Annotation data: { date, end?, label, type: "deploy"|"incident"|"maintenance" }
function renderAnnotations(g, annotations, x, height) {
  const colors = { deploy: "#4e79a7", incident: "#e15759", maintenance: "#f28e2c" };

  annotations.forEach(a => {
    const color = colors[a.type] || "#999";
    if (a.end) {
      // Range annotation
      g.append("rect")
        .attr("x", x(a.date)).attr("width", Math.max(1, x(a.end) - x(a.date)))
        .attr("y", 0).attr("height", height)
        .attr("fill", color).attr("fill-opacity", 0.07)
        .attr("pointer-events", "none");
    }
    // Point marker (or range start line)
    g.append("line")
      .attr("x1", x(a.date)).attr("x2", x(a.date))
      .attr("y1", 0).attr("y2", height)
      .attr("stroke", color).attr("stroke-width", 1)
      .attr("stroke-dasharray", a.end ? "none" : "4,2");

    g.append("text")
      .attr("x", x(a.date) + 3).attr("y", -4)
      .attr("fill", color).attr("font-size", 9).attr("font-weight", 500)
      .text(a.label);
  });
}
```

## Sources

- [D3 Time Scales](https://d3js.org/d3-scale/time)
- [D3 Time Intervals](https://d3js.org/d3-time)
- [PatternFly Timeline](https://github.com/patternfly/patternfly-timeline) -- drag and zoom time navigation
- [D3 Graph Gallery: Confidence Interval](https://d3-graph-gallery.com/graph/line_confidence_interval.html)
- [D3-Foresight](http://reichlab.io/d3-foresight/) -- forecast visualization library
- [Observable Plot: Difference Mark](https://observablehq.github.io/plot/marks/difference)
- [Observable Plot: Shift Transform](https://observablehq.com/plot/transforms/shift)
- [Observable Plot: Interval Transform](https://observablehq.com/plot/transforms/interval)
- [Cal-HeatMap](https://cal-heatmap.com/v2/) -- calendar heatmap library
- [Calendar Heatmap (DKirwan)](https://github.com/DKirwan/calendar-heatmap) -- GitHub-style contribution chart
- [Grafana: Annotate Visualizations](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/annotate-visualizations/)
- [Grafana: State Timeline](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/state-timeline/)
- [Semantic Zoom for Cyclic Time Series (IEEE VIS 2024)](https://ieeexplore.ieee.org/document/10714315/)
- [SemTimeZoom (TU Wien)](https://www.cvast.tuwien.ac.at/projects/semtimezoom) -- visualization technique for time-oriented data with semantic zoom
- [Analyzing Time Series with Observable Plot](https://observablehq.com/@ee2dev/analyzing-time-series-data-with-plot)
