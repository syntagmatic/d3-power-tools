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

## Grouping and Aggregation

`d3.group` and `d3.rollup` are the primary reshaping tools in D3 v7+. They return `InternMap` (value equality on keys — two `new Date("2024-03-15")` instances match).

Group by one key — returns `InternMap<key, row[]>`:

```js
// data: [{region: "West", sales: 100}, {region: "East", sales: 200}, ...]
const byRegion = d3.group(data, d => d.region);
byRegion.get("West"); // all rows where region === "West"
```

Multi-level grouping — nested maps:

```js
const nested = d3.group(data, d => d.year, d => d.region);
nested.get(2023).get("West"); // rows for West in 2023
```

Rollup — aggregate each group to a single value:

```js
const avgByCategory = d3.rollup(data, v => d3.mean(v, d => d.value), d => d.category);
// InternMap { "A" => 42.5, "B" => 31.2 }
```

Multi-key rollup for pivot-table-style summaries:

```js
const summary = d3.rollup(
  data,
  v => ({ mean: d3.mean(v, d => d.value), n: v.length }),
  d => d.year, d => d.region
);
summary.get(2024).get("West"); // { mean: 55.3, n: 12 }
```

**flatGroup / flatRollup** — flat arrays instead of nested maps. Use when you need bindable arrays:

```js
const rows = d3.flatRollup(data, v => d3.sum(v, d => d.sales), d => d.year, d => d.region);
// [[2023, "West", 5400], [2023, "East", 3200], ...]
const tabular = rows.map(([year, region, sales]) => ({ year, region, sales }));

const flat = d3.flatGroup(data, d => d.year, d => d.region);
// [[2023, "West", [{...}, {...}]], [2023, "East", [{...}]], ...]
```

**Choosing the right function:**

| Need | Function | Returns |
|------|----------|---------|
| Rows by key, for lookup | `d3.group` | nested `InternMap<K, row[]>` |
| Aggregate by key, for lookup | `d3.rollup` | nested `InternMap<K, V>` |
| Rows by key, for bindable array | `d3.flatGroup` | `[key, ..., row[]][]` |
| Aggregate by key, for bindable array | `d3.flatRollup` | `[key, ..., V][]` |
| Unique rows by key | `d3.index` | `InternMap<K, row>` (throws on duplicates) |

**InternMap gotcha.** Don't spread to a plain `Map` or convert with `Object.fromEntries` — you lose value equality and every `.get()` with a Date key returns `undefined`.

## Wide-to-Long Reshaping

CSV files from spreadsheets often have months/years as columns. D3 needs one row per observation.

```js
// Wide CSV columns: name, jan, feb, mar, apr
const wide = await d3.csv("monthly.csv", d3.autoType);
const months = ["jan", "feb", "mar", "apr"];
const long = wide.flatMap(d =>
  months.map(month => ({ name: d.name, month, value: d[month] }))
);
```

When column names are dates, parse them:

```js
// Columns: country, 2020-01, 2020-02, 2020-03, ...
const raw = await d3.csv("timeseries.csv");
const dateCols = raw.columns.slice(1);
const parseMonth = d3.timeParse("%Y-%m");
const long = raw.flatMap(d =>
  dateCols.map(col => ({
    country: d.country, date: parseMonth(col),
    value: d[col] === "" ? null : +d[col]
  }))
);
```

For >100K resulting rows, build columnar typed arrays directly instead of objects (see below).

## Long-to-Wide Reshaping

The reverse — for heatmaps, matrices, or table displays where you need a row per entity and columns per category.

```js
// Long: [{name: "Alice", month: "jan", value: 10}, ...]
// Goal: [{name: "Alice", jan: 10, feb: 20, ...}, ...]
const byName = d3.group(long, d => d.name);
const wideData = Array.from(byName, ([name, rows]) => {
  const obj = { name };
  for (const r of rows) obj[r.month] = r.value;
  return obj;
});
```

For a dense matrix (e.g., correlation heatmap), `d3.cross(vars, vars, (a, b) => ({x: a, y: b, value: fn(a, b)}))` generates all cells as a flat bindable array.

## Joining Datasets

Merge two datasets by key using `d3.index` for O(1) lookup:

```js
// Primary: [{fips: "06037", name: "Los Angeles"}, ...]
// Values:  [{fips: "06037", population: 10014009}, ...]
const popByFips = d3.index(populations, d => d.fips);

const joined = counties.map(d => ({
  ...d,
  population: popByFips.get(d.fips)?.population ?? null
}));
```

**Detect orphans** — keys in one dataset but not the other. Critical for choropleths where missing joins leave features unfilled:

```js
const countyFips = new Set(counties.map(d => d.fips));
const dataFips = new Set(populations.map(d => d.fips));
const missing = counties.filter(d => !dataFips.has(d.fips));   // no data for these features
const orphans = populations.filter(d => !countyFips.has(d.fips)); // data with no feature
```

**Multi-key join** — when the key is composite (e.g., state + year):

```js
const lookup = d3.index(dataB, d => d.state, d => d.year);
// lookup.get("CA")?.get(2024) => row or undefined

const joined = dataA.map(d => ({
  ...d,
  metric: lookup.get(d.state)?.get(d.year)?.metric ?? null
}));
```

## Data Smells

Symptoms in your data that show up as visual bugs. Check these before binding to marks.

**Unsorted time data.** `d3.line()` connects points in array order. If your dates aren't sorted, the line zigzags backward. Always sort after parsing: `data.sort((a, b) => a.date - b.date)`.

**Duplicate rows.** Duplicates inflate aggregations (a summed bar is too tall) and create stacked marks that look like single marks but have double opacity. Dedup by key before binding: `d3.groups(data, d => d.id).map(([, v]) => v[0])`.

**Inconsistent categories.** `"US"`, `"U.S."`, and `"United States"` produce three separate bars/slices/groups instead of one. `d3.group` treats them as distinct keys. Normalize in the row accessor.

**Sentinel values.** `-999`, `9999`, or `99.99` for missing blow out your scale domain. One sentinel at `-999` makes all real data cluster in a tiny band at the right of the axis. Filter before computing `d3.extent`.

**BOM in CSV headers.** Files saved from Excel often have a UTF-8 BOM (`\uFEFF`) prepended to the first column name. `d.date` returns `undefined` because the actual key is `"\uFEFFdate"`. Check with: `Object.keys(data[0])[0].charCodeAt(0) === 65279`.

**Mixed numeric formats.** `"1,234"` and `"1234"` in the same column — the comma-formatted value becomes `NaN` under `+x`. Strip before coercing: `+d.value.replace(/,/g, "")`.

**Single-row groups.** A category with one data point still gets a "trend line" or a box plot. One observation is a dot, not a distribution. Filter or flag groups where `v.length < n`.

**`d3.extent` on empty arrays** returns `[undefined, undefined]`, which propagates to `domain([undefined, undefined])` and NaN positions for every element. Guard: `if (!data.length) return;`

## Date and Timezone Handling

```js
const utc   = d3.utcParse("%Y-%m-%d")("2024-03-15");  // midnight UTC
const local = d3.timeParse("%Y-%m-%d")("2024-03-15");  // midnight local time
```

**The midnight shift bug.** Parse "March 15th" with `d3.utcParse` and you get midnight UTC. In UTC-5, `utc.getDate()` returns `14` — your axis labels say March 14. Off by one day, unnoticed for months.

**Rule of thumb:** Date-only data: `d3.utcParse` + `d3.scaleUtc`. Times with timezone offset: `d3.utcParse`. Local times without offset: `d3.timeParse` + `d3.scaleTime`.

**Timezone-aware aggregation.** Grouping by day in UTC when your data is local time shifts bin boundaries:

```js
// Wrong: groups by UTC day, splitting local-day events across two bins
const byDayUTC = d3.group(data, d => d3.utcDay(d.date));

// Right: group by local day when dates represent local time
const byDayLocal = d3.group(data, d => d3.timeDay(d.date));
```

**`Date` constructor inconsistency.** `new Date("2024-03-15")` is UTC midnight, but `new Date("2024-03-15T00:00:00")` is local midnight. Always parse explicitly with `d3.utcParse` or `d3.timeParse`.

**DST gaps.** Around DST transitions, `d3.timeDay` bins are 23 or 25 hours. Use `d3.utcDay` for uniform 24-hour bins in aggregation.

## d3.bin Domain Mismatch

`d3.bin().domain()` **must match** the value accessor's range. If values span 0--100 but you set `.domain([0, 1])`, most values fall outside all bins -- silently lost, histogram looks nearly empty. Always derive domain from the same accessor:

```js
const bins = d3.bin()
  .domain(d3.extent(data, d => d.age))
  .thresholds(20)
  .value(d => d.age)(data);
```

## Outlier Detection Before Visualization

Outliers blow out scale domains, making 99% of your data an unreadable cluster. Detect them before setting domains.

**IQR method** — standard statistical fence:

```js
const values = data.map(d => d.value).filter(isFinite).sort(d3.ascending);
const q1 = d3.quantile(values, 0.25);
const q3 = d3.quantile(values, 0.75);
const iqr = q3 - q1;
const lower = q1 - 1.5 * iqr;
const upper = q3 + 1.5 * iqr;

const outliers = data.filter(d => isFinite(d.value) && (d.value < lower || d.value > upper));
const inliers = data.filter(d => isFinite(d.value) && d.value >= lower && d.value <= upper);
```

**What to do with outliers:**

1. **Filter.** Remove from domain calculation, note in annotation: `d3.extent(inliers, d => d.value)`.
2. **Clamp.** `d3.scaleLinear().domain([lower, upper]).clamp(true)` — outliers stack at the edge. Add an arrow glyph at the clamp boundary.
3. **Transform.** `d3.scaleLog()` or `d3.scaleSqrt()` compresses heavy tails naturally (income, city populations).
4. **Broken axis** (see `skills/scales/`) — split the axis. Use sparingly; misleads if the viewer misses the break.

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

Parse incrementally — process rows as they arrive without holding the full file:

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

**Streaming aggregation** — replace `processRow` with accumulators to compute summaries without storing rows:

```js
const counts = new Map(), sums = new Map();
function processRow(header, values) {
  const row = Object.fromEntries(header.map((h, i) => [h, values[i]]));
  const key = row.region, val = +row.sales;
  if (!isFinite(val)) return;
  counts.set(key, (counts.get(key) ?? 0) + 1);
  sums.set(key, (sums.get(key) ?? 0) + val);
}
// After loop: new Map(Array.from(sums, ([k, s]) => [k, s / counts.get(k)]))
```

**Streaming histogram** — pre-define bins, count into them per row:

```js
const thresholds = d3.range(0, 101, 5);
const binCounts = new Uint32Array(thresholds.length + 1);
function addToBins(value) {
  if (!isFinite(value)) return;
  binCounts[d3.bisectRight(thresholds, value)]++;
}
```

## When to Escalate Beyond d3.csv

`d3.csv` with a row accessor handles most visualization data. Escalate when it doesn't:

| Signal | Tool | Why |
|--------|------|-----|
| >500K rows, aggregation only | DuckDB-WASM | SQL in browser, Parquet range requests. ~4 MB WASM. |
| >500K rows, all rows for Canvas | `fetch` + `ReadableStream` | Stream-parse into typed arrays. |
| Large Parquet, lightweight page | hyparquet (9 KB) | Pure JS Parquet reader, no WASM. |
| Rapid filter changes | AbortController | Cancel stale in-flight requests. |
| Pre-aggregated Arrow IPC | apache-arrow JS (~150 KB) | Zero-copy typed array access via `tableFromIPC`. |

For large data in Observable Framework, data loaders pre-aggregate at build time — a pattern worth adopting anywhere: ship small derived CSV/Parquet, not raw data.

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

Without cancellation, stale responses arrive after fresh ones and overwrite the chart with outdated data — the chart flickers between states, sometimes settling on the wrong one.

## Common Pitfalls

1. **CSV values are always strings.** `"3" + "5" === "35"`. Always coerce in the row accessor, not after.

2. **`d3.timeParse` returns `null` on format mismatch -- silently.** No error, no warning. A column of nulls produces an empty chart. Always validate: `if (!date) console.warn("Bad date:", raw)`.

3. **`d3.sort` returns a new array.** Unlike `Array.sort()`, the original is unchanged. Forgetting the return value is a silent no-op -- your data stays unsorted and the line still zigzags.

4. **Parquet/Arrow type mismatches.** Arrow BigInt columns (Int64) don't work with D3 scales. Convert: `Number(bigintValue)`. As of March 2026, DuckDB-WASM returns BigInt for integer columns by default.

5. **Grouping doesn't preserve order.** `d3.group` iterates in first-seen order, which is usually fine. But if you need sorted groups (e.g., months in calendar order), sort the keys explicitly: `[...byMonth.keys()].sort((a, b) => a - b)`.

6. **`d3.index` throws on duplicate keys.** If your "unique" key isn't unique, `d3.index` throws. Use `d3.group` instead and take the first: `d3.group(data, d => d.id)` then `.get(key)?.[0]`.

## References

- [d3-array](https://d3js.org/d3-array) -- group, rollup, flatGroup, flatRollup, index, bin, sort, extent, sum, mean, cross
- [d3-dsv](https://d3js.org/d3-dsv) -- csvParse, autoType
- [d3-time-format](https://d3js.org/d3-time-format) -- timeParse, utcParse
- [d3-time](https://d3js.org/d3-time) -- timeDay, utcDay, interval arithmetic
- [DuckDB-WASM](https://duckdb.org/docs/stable/clients/wasm/overview) -- SQL queries on client-side data
- [hyparquet](https://github.com/hyparam/hyparquet) -- lightweight Parquet reader (9 KB)
