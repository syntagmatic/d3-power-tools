---
name: data-gathering
description: "Data loading, parsing, cleaning, reshaping, and transformation for D3.js visualizations. Use this skill whenever the user needs to load CSV/JSON/TSV data, coerce types, parse dates, handle missing values, reshape data with d3.group/d3.rollup, aggregate with d3.sum/d3.mean/d3.bin, join datasets, compute derived fields, or prepare data for scales, layouts, and bindable arrays. Also covers d3.csv, d3.json, d3.autoType, d3.group, d3.rollup, d3.flatGroup, d3.flatRollup, d3.index, d3.bin, d3.timeParse, missing data, NaN handling, data cleaning, columnar typed arrays, and streaming. Related skills: parallel-coordinates (normalization), canvas / webgl (typed arrays), cartography (TopoJSON loading), hierarchy-layouts (d3.stratify), data-table (table rendering from prepared data)."
---

# Data Preparation

Bad data doesn't throw errors — it draws wrong charts. A bar at zero that should be missing, a line that zigzags because dates aren't sorted, a scale that blows out because one row has a sentinel value. Every section here is a visual bug you'll never find by reading code.

## autoType: Convenient Until It Isn't

Good for prototyping. Three traps in production:
- `"07030"` becomes `7030` — ZIP codes, FIPS codes, leading-zero identifiers lose meaning. Choropleth joins silently drop counties.
- `"true"` becomes `true` — breaks string comparisons and scale domains.
- `"NA"` stays `"NA"` but `""` becomes `null` — two different missing representations in one dataset.

**Prefer explicit row accessors:**

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

`d3.group` and `d3.rollup` return `InternMap` (value equality on keys — two `new Date("2024-03-15")` instances match).

Rollup example — aggregate each group:

```js
const summary = d3.rollup(
  data,
  v => ({ mean: d3.mean(v, d => d.value), n: v.length }),
  d => d.year, d => d.region
);
summary.get(2024).get("West"); // { mean: 55.3, n: 12 }
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
const wide = await d3.csv("monthly.csv", d3.autoType);
const months = ["jan", "feb", "mar", "apr"];
const long = wide.flatMap(d =>
  months.map(month => ({ name: d.name, month, value: d[month] }))
);
```

## Long-to-Wide Reshaping

```js
const byName = d3.group(long, d => d.name);
const wideData = Array.from(byName, ([name, rows]) => {
  const obj = { name }; for (const r of rows) obj[r.month] = r.value; return obj;
});
```

## Joining Datasets

Merge by key using `d3.index` for O(1) lookup:

```js
const popByFips = d3.index(populations, d => d.fips);
const joined = counties.map(d => ({
  ...d, population: popByFips.get(d.fips)?.population ?? null
}));
```

**Detect orphans** — keys in one dataset but not the other. Critical for choropleths where missing joins leave features unfilled:

```js
const dataFips = new Set(populations.map(d => d.fips));
const missing = counties.filter(d => !dataFips.has(d.fips));
```

Multi-key join: `d3.index(dataB, d => d.state, d => d.year)` then `lookup.get("CA")?.get(2024)?.metric`.

## Data Smells

Symptoms in your data that show up as visual bugs. Check before binding to marks.

**Unsorted time data.** `d3.line()` connects points in array order. Unsorted dates make the line zigzag. Always: `data.sort((a, b) => a.date - b.date)`.

**Duplicate rows.** Inflate aggregations; create stacked marks with double opacity. Dedup: `d3.groups(data, d => d.id).map(([, v]) => v[0])`.

**Inconsistent categories.** `"US"`, `"U.S."`, `"United States"` produce three bars instead of one. Normalize in the row accessor.

**Sentinel values.** `-999` or `9999` for missing blow out your scale domain. Filter before `d3.extent`.

**BOM in CSV headers.** Excel UTF-8 BOM (`\uFEFF`) prepended to first column name. `d.date` returns `undefined` because key is `"\uFEFFdate"`. Check: `Object.keys(data[0])[0].charCodeAt(0) === 65279`.

**Mixed numeric formats.** `"1,234"` and `"1234"` — comma-formatted becomes `NaN` under `+x`. Strip: `+d.value.replace(/,/g, "")`.

**Single-row groups.** One observation is a dot, not a distribution. Filter groups where `v.length < n`.

**`d3.extent` on empty arrays** returns `[undefined, undefined]` — propagates to NaN positions. Guard: `if (!data.length) return;`

## Date and Timezone Handling

**The midnight shift bug.** Parse "March 15th" with `d3.utcParse` — midnight UTC. In UTC-5, `utc.getDate()` returns `14`. Off by one day.

**Rule of thumb:** Date-only data: `d3.utcParse` + `d3.scaleUtc`. Times with timezone offset: `d3.utcParse`. Local times without offset: `d3.timeParse` + `d3.scaleTime`.

**Timezone-aware aggregation.** Grouping by `d3.utcDay` when data is local time shifts bin boundaries. Use `d3.timeDay` for local-time data.

**`Date` constructor inconsistency.** `new Date("2024-03-15")` is UTC midnight, but `new Date("2024-03-15T00:00:00")` is local midnight. Always parse explicitly.

**DST gaps.** Around transitions, `d3.timeDay` bins are 23 or 25 hours. Use `d3.utcDay` for uniform 24-hour bins.

## d3.bin Domain Mismatch

`d3.bin().domain()` **must match** the value accessor's range. Values spanning 0--100 with `.domain([0, 1])` silently loses most data. Always derive domain from the same accessor:

```js
const bins = d3.bin()
  .domain(d3.extent(data, d => d.age))
  .thresholds(20)
  .value(d => d.age)(data);
```

## Outlier Detection Before Visualization

Outliers blow out scale domains, making 99% of data an unreadable cluster. Use IQR fences (1.5 * IQR above Q3 / below Q1) to detect them.

**What to do with outliers:**

1. **Filter.** Remove from domain calculation, note in annotation.
2. **Clamp.** `scaleLinear().domain([lower, upper]).clamp(true)` — outliers stack at edge. Add arrow glyph at boundary.
3. **Transform.** `d3.scaleLog()` or `d3.scaleSqrt()` compresses heavy tails naturally (income, city populations).
4. **Broken axis** (see `skills/scales/`) — split the axis. Use sparingly; misleads if viewer misses the break.

## When to Escalate Beyond d3.csv

| Signal | Tool | Why |
|--------|------|-----|
| >500K rows, aggregation only | DuckDB-WASM | SQL in browser, Parquet range requests. ~4 MB WASM. |
| >500K rows, all rows for Canvas | `fetch` + `ReadableStream` | Stream-parse into typed arrays. |
| Large Parquet, lightweight page | hyparquet (9 KB) | Pure JS Parquet reader, no WASM. |
| Pre-aggregated Arrow IPC | apache-arrow JS (~150 KB) | Zero-copy typed array access via `tableFromIPC`. |

For large data in Observable Framework, data loaders pre-aggregate at build time — ship small derived CSV/Parquet, not raw data.

## Common Pitfalls

1. **CSV values are always strings.** `"3" + "5" === "35"`. Always coerce in the row accessor, not after.

2. **`d3.timeParse` returns `null` on format mismatch -- silently.** No error, no warning. A column of nulls produces an empty chart. Always validate: `if (!date) console.warn("Bad date:", raw)`.

3. **`d3.sort` returns a new array.** Unlike `Array.sort()`, the original is unchanged. Forgetting the return value is a silent no-op -- your data stays unsorted and the line still zigzags.

4. **Parquet/Arrow type mismatches.** Arrow BigInt columns (Int64) don't work with D3 scales. Convert: `Number(bigintValue)`. As of March 2026, DuckDB-WASM returns BigInt for integer columns by default.

5. **Grouping doesn't preserve order.** `d3.group` iterates in first-seen order, which is usually fine. But if you need sorted groups (e.g., months in calendar order), sort the keys explicitly: `[...byMonth.keys()].sort((a, b) => a - b)`.

6. **`d3.index` throws on duplicate keys.** If your "unique" key isn't unique, `d3.index` throws. Use `d3.group` instead and take the first: `d3.group(data, d => d.id)` then `.get(key)?.[0]`.

## References

- [d3-array](https://d3js.org/d3-array) -- group, rollup, bin, sort, extent, cross
- [d3-time-format](https://d3js.org/d3-time-format) -- timeParse, utcParse
- [DuckDB-WASM](https://duckdb.org/docs/stable/clients/wasm/overview) -- SQL queries on client-side data
- [hyparquet](https://github.com/hyparam/hyparquet) -- lightweight Parquet reader (9 KB)
