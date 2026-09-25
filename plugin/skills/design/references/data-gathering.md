# Data preparation

Absorbed from the v2 `data-gathering` skill. Open when loading or reshaping real data: the decisions and traps are in `SKILL.md`, the code and details are here.

## The faces of missing

| Source | Value | `+x` | global `isFinite(x)` | `Number.isFinite(+x)` |
|---|---|---|---|---|
| empty CSV cell | `""` | `0` (!) | `true` (!) | `true` (!) |
| CSV `NA` | `"NA"` | `NaN` | `false` | `false` |
| autoType empty cell | `null` | `0` (!) | `true` (!) | `true` (!) |
| JSON `null` | `null` | `0` (!) | `true` (!) | `true` (!) |
| JSON missing key | `undefined` | `NaN` | `false` | `false` |

Every `(!)` is a missing value that passes as a number and draws at zero. Test for `""` and `null` before coercing; no finiteness check after `+x` can catch them.

## Rollup

`d3.group`/`d3.rollup` return `InternMap`, which compares keys by value, so two `Date` objects for the same instant match.

```js
const summary = d3.rollup(
  data,
  v => ({ mean: d3.mean(v, d => d.value), n: v.length }),
  d => d.year, d => d.region
);
summary.get(2024)?.get("West");
```

## Reshaping

Spreadsheet exports put months or years in columns. D3 wants one row per observation.

```js
const months = ["jan", "feb", "mar", "apr"];
const long = wide.flatMap(d => months.map(month => ({ name: d.name, month, value: d[month] })));

const wideAgain = Array.from(d3.group(long, d => d.name), ([name, rows]) => {
  const obj = { name };
  for (const r of rows) obj[r.month] = r.value;
  return obj;
});
```

## Joins and orphans

`d3.index` gives O(1) lookup and throws if the key isn't unique; fall back to `d3.group(...).get(key)?.[0]`. Always list orphans: in a choropleth, an unmatched key is an unfilled feature, not an error.

```js
const popByFips = d3.index(populations, d => d.fips);
const joined = counties.map(d => ({ ...d, population: popByFips.get(d.fips)?.population ?? null }));
const orphans = counties.filter(d => !popByFips.has(d.fips));
```

Multi-key: `d3.index(rows, d => d.state, d => d.year)`, then `lookup.get("CA")?.get(2024)`.

## Cleaning one-liners

```js
const byDate = d3.sort(data, d => d.date);                        // new array; use the return
const deduped = d3.groups(data, d => d.id).map(([, v]) => v[0]);
const num = s => s === "" ? null : +String(s).replace(/,/g, "");
const bins = d3.bin().value(d => d.age).domain(d3.extent(data, d => d.age)).thresholds(20)(data);
```

## BOM in headers

Excel's UTF-8 export prepends `﻿`, so the first column key becomes `"﻿date"` and `d.date` is `undefined`. `fetch().text()` (and so `d3.csv`) strips it during decoding; it bites when `d3.csvParse` gets a string read another way (e.g. Node `fs`). Check `Object.keys(rows[0])[0].charCodeAt(0) === 0xFEFF`.

## Date shift

Parse `"2024-03-15"` with `d3.utcParse` and you get UTC midnight. In UTC-5, `getDate()` returns 14. Read date-only values with `getUTC*` methods and format with `d3.utcFormat`, or the labels are a day early.

## Large data

DuckDB-WASM is heavy (multi-MB WASM) but gives SQL and Parquet range requests; use it when the page only needs aggregates. hyparquet is a small pure-JS Parquet reader. apache-arrow reads Arrow IPC into typed arrays without copying. Int64 columns from either arrive as BigInt: convert with `Number()` before any scale. When a build step exists (e.g. Observable Framework data loaders), pre-aggregate there and ship the small derived file.
