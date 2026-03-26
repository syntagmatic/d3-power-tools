---
name: data-gathering
description: "Data loading, parsing, cleaning, reshaping, and transformation for D3.js visualizations. Use this skill whenever the user needs to load CSV/JSON/TSV data, coerce types, parse dates, handle missing values, reshape data with d3.group/d3.rollup, aggregate with d3.sum/d3.mean/d3.bin, join datasets, compute derived fields, or prepare data for scales, layouts, and bindable arrays. Also covers d3.csv, d3.json, d3.autoType, d3.group, d3.rollup, d3.flatGroup, d3.flatRollup, d3.index, d3.bin, d3.timeParse, missing data, NaN handling, data cleaning, columnar typed arrays, and streaming. Related skills: parallel-coordinates (normalization), canvas / webgl (typed arrays), cartography (TopoJSON loading), hierarchy-layouts (d3.stratify), data-table (table rendering from prepared data)."
---

# Data Preparation

Bad data doesn't throw errors — it draws wrong charts. A bar at zero that should be missing, a line that zigzags because dates aren't sorted, a scale that blows out because one row has a sentinel value. Every section here is a visual bug you'll never find by reading code.

## autoType: Convenient Until It Isn't

```js
const data = await d3.csv("data.csv", d3.autoType);
```

Good for prototyping. Three traps in production:
- `"07030"` becomes `7030` — ZIP codes, FIPS codes, and any leading-zero identifier lose meaning. Your choropleth join silently drops counties.
- `"true"` becomes `true` — breaks string comparisons and scale domains.
- `"NA"` stays `"NA"` but `""` becomes `null` — two different representations of missing in one dataset.

**Prefer explicit row accessors.** You choose what's a number, what's a string, what's missing:

```js
const data = await d3.csv("data.csv", d => ({
  fips: d.fips,                          // keep as string
  date: d3.timeParse("%Y-%m-%d")(d.date),
  value: d.value === "" ? null : +d.value // explicit missing handling
}));
```

## The Many Faces of Missing

| Source | What you get | `+x` | `isFinite(x)` |
|--------|-------------|------|---------------|
| Empty CSV cell | `""` | `0` (!) | `true` (!) |
| CSV "NA" | `"NA"` | `NaN` | `false` |
| autoType empty | `null` | `0` (!) | `false` |
| JSON null | `null` | `0` (!) | `false` |
| JSON missing key | `undefined` | `NaN` | `false` |

The `+"" === 0` row is the single most common D3 data bug. Empty CSV cells become empty strings, `+""` coerces to `0`, and your bar chart shows a data point at zero that should be absent. **Guard**: `const safeNum = s => s === "" ? null : +s;`

Use `isFinite()` over `!isNaN()` — it also rejects `Infinity`, which blows out scale domains.

Missing values propagate silently through scales: `scaleLinear()(undefined)` returns `NaN`. The element renders at an invisible position — no error, no warning, just a missing mark.

## Data Smells

Symptoms in your data that show up as visual bugs. Check these before bindng to marks.

**Unsorted time data.** `d3.line()` connects points in array order. If your dates aren't sorted, the line zigzags backward. Always sort after parsing: `data.sort((a, b) => a.date - b.date)`.

**Duplicate rows.** Duplicates inflate aggregations (a summed bar is too tall) and create stacked marks that look like single marks but have double opacity. Dedup by key before bindin: `d3.groups(data, d => d.id).map(([, v]) => v[0])`.

**Inconsistent categories.** `"US"`, `"U.S."`, and `"United States"` produce three separate bars/slices/groups instead of one. `d3.group` treats them as distinct keys. Normalize in the row accessor.

**Sentinel values.** `-999`, `9999`, or `99.99` for missing blow out your scale domain. One sentinel at `-999` makes all real data cluster in a tiny band at the right of the axis. Filter before computing `d3.extent`.

**BOM in CSV headers.** Files saved from Excel often have a UTF-8 BOM (`\uFEFF`) prepended to the first column name. `d.date` returns `undefined` because the actual key is `"\uFEFFdate"`. Check with: `Object.keys(data[0])[0].charCodeAt(0) === 65279`.

**Mixed numeric formats.** `"1,234"` and `"1234"` in the same column — the comma-formatted value becomes `NaN` under `+x`. Strip before coercing: `+d.value.replace(/,/g, "")`.

**Single-row groups.** A category with one data point still gets a "trend line" or a box plot. One observation is a dot, not a distribution. Filter or flag groups where `v.length < n`.

**`d3.extent` on empty arrays** returns `[undefined, undefined]`, which propagates to `domain([undefined, undefined])` and NaN positions for every element. Guard: `if (!data.length) return;`

## d3.bin Domain Mismatch

`d3.bin().domain()` **must match** the value accessor's range. If values span 0--100 but you set `.domain([0, 1])`, most values fall outside all bins -- silently lost, histogram looks nearly empty. Always derive domain from the same accessor:

```js
const bins = d3.bin()
  .domain(d3.extent(data, d => d.age))
  .thresholds(20)
  .value(d => d.age)(data);
```

## InternMap: Why Date Keys Work

`d3.group` and `d3.rollup` return `InternMap`, which uses **value equality** -- two `new Date("2024-03-15")` instances match. Plain `Map` uses reference equality, so the same lookup fails. Don't spread to a plain `Map` or convert with `Object.fromEntries` -- you lose this behavior and every `.get()` with a Date key returns `undefined`.

## Columnar Typed Arrays (>50K rows)

For Canvas/WebGL pipelines, columnar layout avoids per-object GC pressure and enables direct GPU upload:

```js
const n = data.length;
const x = new Float64Array(n), y = new Float64Array(n), cat = new Uint8Array(n);
const categoryIndex = new Map([...new Set(data.map(d => d.type))].map((c, i) => [c, i]));
data.forEach((d, i) => { x[i] = d.longitude; y[i] = d.latitude; cat[i] = categoryIndex.get(d.type); });
```

**Pre-computed sort indices** let you draw back-to-front without re-sorting the typed arrays:

```js
const order = d3.range(n);
order.sort((a, b) => x[a] - x[b]);
for (const i of order) drawPoint(x[i], y[i], cat[i]);
```

## Streaming Large CSV (>50 MB)

Parse incrementally to avoid loading the entire file into memory. Process rows as they arrive:

```js
const response = await fetch("huge.csv");
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "", header = null;

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop(); // incomplete line stays in buffer
  for (const line of lines) {
    if (!header) { header = d3.csvParseRows(line)[0]; continue; }
    processRow(header, d3.csvParseRows(line)[0]);
  }
}
```

## When to Escalate Beyond d3.csv

`d3.csv` with a row accessor handles most visualization data. Escalate when it doesn't:

| Signal | Tool | Why |
|--------|------|-----|
| >500K rows, need aggregation only | DuckDB-WASM (SQL in browser) | Queries remote Parquet via HTTP range requests -- fetches only needed columns/row groups. ~4 MB WASM bundle; not worth it below ~100K rows. |
| >500K rows, need all rows for Canvas | Manual `fetch` + `ReadableStream` | Stream-parse into typed arrays without holding the full CSV string + parsed objects simultaneously. |
| Large Parquet file, lightweight page | hyparquet (9 KB) | Pure JS Parquet reader with column selection and HTTP range requests. No WASM runtime. |
| Dashboard with rapid filter changes | AbortController | Cancel in-flight requests when the user changes filters before data arrives. |
| Pre-aggregated Arrow IPC files | apache-arrow JS | Zero-copy typed array access via `tableFromIPC`. ~150 KB. Use when a build step already produces Arrow files. |
| Multiple ad-hoc queries, joins | DuckDB-WASM | Register a table once, run SQL per view. Shared state across linked views. |

**Observable Plot** uses the same `d3.csv`/`d3.autoType` pipeline. For large data in Observable Framework, data loaders pre-aggregate at build time -- a pattern worth adopting even outside Observable: run a build script to produce small derived CSV/Parquet, ship that instead of raw data.

## Cancellable Data Loading

Essential for filter-driven dashboards where users change selections faster than data loads:

```js
let controller = null;

async function loadData(url) {
  if (controller) controller.abort();
  controller = new AbortController();
  try {
    const res = await fetch(url, { signal: controller.signal });
    return await res.json();
  } catch (e) {
    if (e.name === "AbortError") return null; // superseded, caller ignores
    throw e;
  }
}
```

Without cancellation, stale responses arrive after fresh ones and silently overwrite the chart with outdated data. The visual bug: the chart flickers between states, sometimes settling on the wrong one.

## Common Pitfalls

1. **CSV values are always strings.** `"3" + "5" === "35"`. Always coerce in the row accessor, not after.

2. **`d3.timeParse` returns `null` on format mismatch -- silently.** No error, no warning. A column of nulls produces an empty chart. Always validate: `if (!date) console.warn("Bad date:", raw)`.

3. **`d3.sort` returns a new array.** Unlike `Array.sort()`, the original is unchanged. Forgetting the return value is a silent no-op -- your data stays unsorted and the line still zigzags.

4. **Parquet/Arrow type mismatches.** Arrow BigInt columns (Int64) don't work with D3 scales. Convert: `Number(bigintValue)`. As of March 2026, DuckDB-WASM returns BigInt for integer columns by default.

## References

- [d3-array](https://d3js.org/d3-array) -- group, rollup, bin, sort, extent, sum, mean
- [d3-dsv](https://d3js.org/d3-dsv) -- csvParse, autoType
- [d3-time-format](https://d3js.org/d3-time-format) -- timeParse, utcParse
- [DuckDB-WASM](https://duckdb.org/docs/stable/clients/wasm/overview) -- SQL queries on client-side data
- [hyparquet](https://github.com/hyparam/hyparquet) -- lightweight Parquet reader (9 KB)
