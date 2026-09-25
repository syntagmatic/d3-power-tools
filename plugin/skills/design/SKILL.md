---
name: design
description: "Read first before building any D3 visualization. Exploratory design process (see the data, define the viewer's task, find the natural form) plus data preparation: loading CSV/JSON/TSV, d3.csv, d3.autoType, type coercion, missing values and NaN, date parsing and timezones, d3.group/rollup/flatGroup/index, d3.bin, reshaping wide/long, joins, outliers, data smells, and large data (DuckDB-WASM, Parquet, Arrow). Routes to the other skills by need."
---

# Design

Two things happen before any mark is drawn: deciding what the chart is for, and getting the data into a shape that won't lie. Models skip the first and trust the second. Bad data doesn't throw errors; it draws wrong charts. The viewer of an exploratory chart is a detective, not a reader, so open a thinking space instead of steering to one answer.

## Before code

1. **See the data.** Profile it before picking a form: dimensions, distributions, clusters, gaps. Is it hierarchical, relational, temporal, spatial, or high-dimensional?
2. **Define the task.** What does the viewer *do*: discover, compare, relate? Exploration comes before explanation.
3. **Find the natural form.** Match the form to the data's structure and don't flatten what's naturally complex. Interaction is part of the form, not bolted on: each one answers a question the viewer might ask. Coordinate views when one can't hold the whole structure.

Complexity should match the data. Keep responses under 100ms so the viewer is thinking with the tool, and use animation only for object constancy.

## Where to go next

| If the need is... | Read |
|---|---|
| Scales, axes, color, texture, annotation, labels, tooltips | `legibility` |
| Distributions, parallel coordinates, small multiples, sparklines | `patterns` |
| Trees, treemaps, sunburst, circle packing, edge bundling | `hierarchy` |
| Node-link, force layouts, adjacency matrix, chord, Sankey | `networks` |
| Maps, projections, choropleths, TopoJSON | `maps` |
| Time series, time axes, horizon charts, streaming | `time` |
| Brushing, linked views, coordination, zoom and navigation | `interaction` |
| Transitions, choreography, scrollytelling, shape morphing | `motion` |
| Canvas, WebGL, responsive sizing, code structure and idioms | `rendering` |
| Keyboard, screen readers, data-table fallbacks | `accessibility` |

## Loading decisions

| If... | Do | Not |
|---|---|---|
| prototyping a throwaway | `d3.autoType` | autoType in production |
| the data has IDs with leading zeros (ZIP, FIPS) | explicit row accessor, keep as string | autoType: `"07030"` → `7030`, choropleth joins drop silently |
| dates are date-only | `d3.utcParse` + `scaleUtc` | `d3.timeParse`: a local-time midnight shifts a day in UTC-negative zones |
| times are local wall-clock without offset | `d3.timeParse` + `scaleTime`, bin with `d3.timeDay` | `d3.utcDay` bins, which shift boundaries |
| you need uniform 24h bins | `d3.utcDay` | `d3.timeDay` (23/25h around DST) |
| over ~500K rows, only aggregates needed | DuckDB-WASM (SQL in the browser, Parquet range requests) | loading raw rows |
| over ~500K rows, every row drawn on Canvas | `fetch` + `ReadableStream` into typed arrays | `d3.csv` |
| large Parquet on a lightweight page | hyparquet (pure JS, no WASM) | DuckDB-WASM |
| pre-aggregated Arrow IPC | apache-arrow `tableFromIPC` | re-parsing to objects |

Coerce in the row accessor, not after. CSV values are always strings: `"3" + "5" === "35"`.

```js
const data = await d3.csv("data.csv", d => ({
  fips: d.fips,
  date: d3.utcParse("%Y-%m-%d")(d.date),
  value: d.value === "" ? null : +d.value
}));
```

## Grouping decisions

| Need | Use | Returns |
|---|---|---|
| rows by key, for lookup | `d3.group` | nested `InternMap<K, row[]>` |
| aggregate by key, for lookup | `d3.rollup` | nested `InternMap<K, V>` |
| rows by key, as a bindable array | `d3.flatGroup` | `[k1, ..., rows][]` |
| aggregate by key, as a bindable array | `d3.flatRollup` | `[k1, ..., V][]` |
| one row per unique key (joins) | `d3.index` | `InternMap<K, row>`, throws on duplicate keys |

## Outliers

Detect with IQR fences (1.5 × IQR beyond Q1/Q3). Then pick one: **filter** from the domain and say so in an annotation; **clamp** (`.clamp(true)`) with an arrow glyph at the edge; **transform** heavy tails with log or sqrt; or a **broken axis** (see `legibility`) when the outlier isn't the point.

## Traps

- **`+"" === 0`.** Empty CSV cells become `""`, which coerces to 0, so a missing value draws as a real bar at zero. Guard: `s === "" ? null : +s`.
- **Global `isFinite` coerces:** `isFinite("")` and `isFinite(null)` are both `true`. After the `""`/`null` guard, check with `Number.isFinite`; it also rejects `Infinity`, which blows out domains.
- **autoType mixes missing forms:** `""` becomes `null`, `"NA"` stays the string `"NA"`, `"true"` becomes a boolean.
- **Scales pass missing through.** `scaleLinear()(undefined)` returns the `.unknown()` value (undefined), the attribute is dropped, and the mark vanishes with no error.
- **`d3.timeParse` returns `null` on a format mismatch**, silently. A column of nulls is an empty chart. Warn on null.
- **`new Date("2024-03-15")` is UTC midnight; `new Date("2024-03-15T00:00:00")` is local midnight.** Always parse with an explicit format.
- **Unsorted dates zigzag the line.** `d3.line` follows array order. Sort by date first.
- **`d3.sort` returns a new array** and leaves the original alone. Ignoring the return is a no-op.
- **Converting an InternMap to `Map` or `Object.fromEntries`** loses value equality; every `.get(date)` returns `undefined`.
- **`d3.group` keeps first-seen order.** Sort the keys when order means something (months).
- **Sentinel values** (`-999`, `9999`) blow out the domain. Filter before `d3.extent`.
- **`d3.extent([])` is `[undefined, undefined]`** and becomes NaN positions. Return early on empty data.
- **`d3.bin().domain()` must cover the accessor's values.** Values outside are dropped, so derive it from the same accessor.
- **Inconsistent categories** (`"US"`, `"U.S."`) make separate bars. Normalize in the row accessor.
- **Duplicate rows** inflate sums and double-stack marks. Dedup by id.
- **Comma-formatted numbers** (`"1,234"`) become NaN. Strip commas first.
- **Arrow/DuckDB Int64 columns come back as BigInt**, which D3 scales can't use. Convert with `Number()`.
- **Single-row groups** are a dot, not a distribution. Filter by group size.

## References

- `references/exploratory-design.md`: the original design-process text (fully summarized above).
- `references/data-gathering.md`: missing-value table, rollup/reshape/join code, orphan detection, BOM and date-shift details.
- `examples/data-gathering.html`: messy CSV through cleaning, grouping, and binning. Tested by `tests/test.config.json`.
