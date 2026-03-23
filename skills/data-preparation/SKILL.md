---
name: data-preparation
description: "Data loading, parsing, cleaning, reshaping, and transformation for D3.js visualizations. Use this skill whenever the user needs to load CSV/JSON/TSV data, coerce types, parse dates, handle missing values, reshape data with d3.group/d3.rollup, pivot wide-to-long, aggregate with d3.sum/d3.mean/d3.bin, join datasets, compute derived fields, or prepare data for scales, layouts, and bindable arrays. Also covers d3.csv, d3.json, d3.autoType, d3.group, d3.rollup, d3.flatGroup, d3.flatRollup, d3.index, d3.bin, d3.cumsum, d3.rank, d3.cross, d3.timeParse, missing data, NaN handling, data cleaning, wide-to-long, pivot, normalization, columnar typed arrays, and streaming. Related skills: parallel-coordinates (normalization), canvas-rendering / webgl-rendering (typed arrays), geographic-maps (TopoJSON loading), hierarchy-layouts (d3.stratify), fallback-table (table rendering from prepared data)."
---

# Data Preparation

Everything between raw data and bindable arrays. Loading, type coercion, cleaning, reshaping, aggregation, joining, normalization, and performance patterns — all with idiomatic D3 (d3-fetch, d3-dsv, d3-array, d3-time-format).

**Core principle:** D3 works with plain arrays and objects. The preparation layer delivers arrays whose elements map 1:1 to visual marks, with every field typed and scaled-ready.

```
┌──────────────────────────────────────────────────────────┐
│  Source                                                  │
│  CSV / TSV / JSON / fetch  ──►  raw strings / objects    │
├──────────────────────────────────────────────────────────┤
│  Parse & Coerce                                          │
│  autoType / accessor fn / timeParse  ──►  typed rows     │
├──────────────────────────────────────────────────────────┤
│  Clean                                                   │
│  filter nulls / deduplicate / validate  ──►  clean rows  │
├──────────────────────────────────────────────────────────┤
│  Reshape & Aggregate                                     │
│  group / rollup / bin / pivot  ──►  nested / summary     │
├──────────────────────────────────────────────────────────┤
│  Derive & Join                                           │
│  computed fields / normalize / merge  ──►  enriched      │
├──────────────────────────────────────────────────────────┤
│  Bind                                                    │
│  ──►  scales, layouts, .data() joins, bindable arrays    │
└──────────────────────────────────────────────────────────┘
```

---

## 1. Loading Data

Row accessor coerces types at parse time — never handle raw strings downstream:

```js
const data = await d3.csv("sales.csv", d => ({
  date: parseDate(d.date), region: d.region,
  revenue: +d.revenue, units: +d.units
}));
```

`d3.json` has no row accessor — data is already typed. Use for structured data and GeoJSON/TopoJSON (see `geographic-maps` skill).

### Multiple files

```js
const [sales, regions, geo] = await Promise.all([
  d3.csv("sales.csv", typeSales),
  d3.csv("regions.csv", d => ({ id: d.id, name: d.name, pop: +d.pop })),
  d3.json("boundaries.json")
]);
```

### Inline parsing

```js
const data = d3.csvParse(csvString, d => ({
  name: d.name, value: +d.value || null, date: parseDate(d.date)
}));
```

### Streaming large CSV (>50 MB)

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
  buffer = lines.pop();
  for (const line of lines) {
    if (!header) { header = d3.csvParseRows(line)[0]; continue; }
    processRow(header, d3.csvParseRows(line)[0]);
  }
}
```

---

## 2. Type Coercion

`+d.value` is idiomatic D3 number coercion. Watch the edge cases:

```js
+""        // 0 — silently corrupts! Guard: d.value === "" ? null : +d.value
+"3.14"    // 3.14
+"N/A"     // NaN
+null      // 0
+undefined // NaN
```

### d3.autoType

```js
const data = await d3.csv("data.csv", d3.autoType);
```

Good for prototyping. Surprises: `"true"`→boolean, `"07030"`→`7030` (loses leading zero), numeric-looking IDs become numbers. Prefer explicit row accessors for production.

### Date parsing

```js
const parseDate = d3.timeParse("%Y-%m-%d");
const parseDateUTC = d3.utcParse("%Y-%m-%d");  // avoids timezone shifts
```

| Token | Meaning | Example |
|-------|---------|---------|
| `%Y` | 4-digit year | 2024 |
| `%m` | zero-padded month | 03 |
| `%d` | zero-padded day | 09 |
| `%H`/`%M`/`%S` | hour/min/sec | 14:30:05 |
| `%B`/`%b` | full/abbr month | March/Mar |
| `%I`/`%p` | 12-hour/AM-PM | 02 PM |

`timeParse` returns `null` on mismatch — always validate:

```js
const date = parseDate(d.date);
if (!date) console.warn(`Bad date: "${d.date}"`, d);
```

---

## 3. Cleaning

```js
const clean = data.filter(d => d.date != null && isFinite(d.revenue));
```

Use `isFinite()` over `!isNaN()` — also rejects `Infinity`.

### The many faces of missing

| Source | What you get | `+x` | `isFinite(x)` |
|--------|-------------|------|---------------|
| Empty CSV cell | `""` | `0` (!) | `true` (!) |
| CSV "NA" | `"NA"` | `NaN` | `false` |
| autoType empty | `null` | `0` (!) | `false` |
| JSON null | `null` | `0` (!) | `false` |
| JSON missing key | `undefined` | `NaN` | `false` |

Guard: `const safeNum = s => s === "" ? null : +s;`

### Deduplication

```js
const unique = [...d3.index(data, d => d.id).values()]; // throws on dupes
// If dupes expected, keep last: [...new Map(data.map(d => [d.id, d])).values()]
```

`d3.count(data, d => d.value)` counts only finite numeric values (skips NaN/null/undefined), unlike `.length`.

---

## 4. Reshaping: group, rollup, index

These d3-array functions replace the old `d3.nest` API. All return `InternMap` (value equality for keys — Date/number keys work unlike plain Map).

| Function | Returns | Use case |
|----------|---------|----------|
| `d3.group(data, keyFn)` | `InternMap<key, row[]>` | Split into groups |
| `d3.groups(data, keyFn)` | `[key, row[]][]` | Same, as flat entries for `.data()` joins |
| `d3.rollup(data, reduceFn, keyFn)` | `InternMap<key, value>` | Group then summarize |
| `d3.flatRollup(data, reduceFn, ...keyFns)` | `[key1, key2, ..., value][]` | Multi-level aggregation, flat output |
| `d3.flatGroup(data, ...keyFns)` | `[key1, key2, ..., rows][]` | Multi-level grouping, flat output |
| `d3.index(data, keyFn)` | `InternMap<key, row>` | Unique lookup (throws on dupes) |

All support multi-level nesting via additional key functions.

```js
// group
const byRegion = d3.group(data, d => d.region);
// rollup with multiple aggregates
const stats = d3.rollup(data,
  v => ({ total: d3.sum(v, d => d.revenue), mean: d3.mean(v, d => d.revenue), count: v.length }),
  d => d.region
);
// flatRollup — visualization-ready summary
const summary = d3.flatRollup(data, v => d3.sum(v, d => d.revenue), d => d.year, d => d.region);
// [[2023, "North", 45000], ...] → convert: summary.map(([year, region, revenue]) => ({ year, region, revenue }))

// multi-level nesting
const nested = d3.group(data, d => d.year, d => d.region);
nested.get(2023).get("North");

// InternMap: Date keys work
d3.group(data, d => d.date).get(new Date("2024-03-15")); // works!
```

### Wide-to-long pivot

```js
const quarters = data.columns.filter(c => c.startsWith("q"));
const long = data.flatMap(d => quarters.map(q => ({ name: d.name, quarter: q, value: +d[q] })));
```

### Long-to-wide

```js
const wide = d3.flatGroup(data, d => d.name).map(([name, rows]) => {
  const obj = { name };
  for (const row of rows) obj[row.metric] = row.value;
  return obj;
});
```

For hierarchy layouts, convert flat id/parent tables with `d3.stratify()` — see `hierarchy-layouts` skill.

---

## 5. Aggregation & Binning

All d3-array aggregation functions accept an optional accessor and skip NaN/null/undefined:

```js
d3.min(data, d => d.value)       d3.max(data, d => d.value)
d3.extent(data, d => d.value)    // [min, max] — feed to scale.domain()
d3.sum(data, d => d.value)       d3.mean(data, d => d.value)
d3.median(data, d => d.value)    d3.deviation(data, d => d.value)
d3.quantile(sorted, 0.25)       // array must be pre-sorted
d3.cumsum(data, d => d.revenue)  // Float64Array running total
```

### d3.bin

```js
const bins = d3.bin()
  .domain(d3.extent(data, d => d.age))
  .thresholds(20)
  .value(d => d.age)(data);
// Each bin: array of rows with .x0, .x1 properties
```

| Strategy | Usage | Notes |
|----------|-------|-------|
| Number | `.thresholds(20)` | Target count (actual may differ) |
| d3.thresholdSturges | `.thresholds(d3.thresholdSturges)` | Default, good for normal |
| d3.thresholdScott | `.thresholds(d3.thresholdScott)` | Based on std deviation |
| d3.thresholdFreedmanDiaconis | `.thresholds(d3.thresholdFreedmanDiaconis)` | Based on IQR, good for skewed |
| Array | `.thresholds([10, 20, 30])` | Explicit boundaries |

---

## 6. Sorting & Ranking

```js
d3.sort(data, d => d.revenue)          // ascending, returns new array
d3.sort(data, d => -d.revenue)         // descending
d3.sort(data, d => d.region, d => -d.revenue) // multi-key
d3.rank(data, d => d.score)            // fractional ranking (ties get average)
d3.permute(row, ["name", "region"])    // extract values in order
```

For `Array.prototype.sort`: `data.slice().sort((a, b) => d3.ascending(a.name, b.name))`

---

## 7. Joining & Merging

### Lookup join with d3.index

```js
const lookup = d3.index(metadata, d => d.id);
const enriched = data.map(d => ({ ...d, ...lookup.get(d.id) }));
// Left join: const meta = lookup.get(d.id); return meta ? { ...d, ...meta } : d;
```

For choropleth joins (CSV + TopoJSON by FIPS), see `geographic-maps` skill.

### d3.cross — cartesian product

```js
const grid = d3.cross(years, regions, (year, region) => ({
  year, region, revenue: rollupMap.get(year)?.get(region) ?? 0
}));
```

---

## 8. Derived Fields & Normalization

```js
// Computed columns
const enriched = data.map(d => ({
  ...d, margin: d.revenue - d.cost, perCapita: d.value / d.population * 100000
}));

// Percentage of total
const total = d3.sum(data, d => d.value);
data.map(d => ({ ...d, pct: d.value / total }));

// Min-max normalize to [0, 1]
const [lo, hi] = d3.extent(data, d => d.value);
data.map(d => ({ ...d, valueNorm: (d.value - lo) / (hi - lo) }));

// Z-score
const mean = d3.mean(data, d => d.value), sd = d3.deviation(data, d => d.value);
data.map(d => ({ ...d, zValue: (d.value - mean) / sd }));
```

### Multi-dimensional normalization (parallel coordinates)

```js
const dims = ["income", "education", "health"];
const extents = new Map(dims.map(dim => [dim, d3.extent(data, d => d[dim])]));
const normalized = data.map(d => {
  const row = { ...d };
  for (const dim of dims) {
    const [lo, hi] = extents.get(dim);
    row[dim] = hi === lo ? 0.5 : (d[dim] - lo) / (hi - lo);
  }
  return row;
});
```

---

## 9. Performance: Large Datasets

### Columnar typed arrays (>50K rows)

See `canvas-rendering` and `webgl-rendering` skills for rendering pipelines.

```js
const n = data.length;
const x = new Float64Array(n), y = new Float64Array(n), cat = new Uint8Array(n);
const categoryIndex = new Map([...new Set(data.map(d => d.type))].map((c, i) => [c, i]));
data.forEach((d, i) => { x[i] = d.longitude; y[i] = d.latitude; cat[i] = categoryIndex.get(d.type); });
```

### Pre-computed sort indices

```js
const order = d3.range(n);
order.sort((a, b) => x[a] - x[b]);
for (const i of order) drawPoint(x[i], y[i], cat[i]);
```

### Sampling

```js
const sample = d3.shuffle(data.slice()).slice(0, 1000);
```

`d3.bin` works directly with typed arrays: `d3.bin().thresholds(40)(new Float64Array(values))`.

---

## 10. Streaming & Incremental Data

### Circular buffer for time-windowed data

```js
class CircularBuffer {
  constructor(cap) { this.data = new Array(cap); this.head = 0; this.size = 0; this.cap = cap; }
  push(item) { this.data[this.head] = item; this.head = (this.head + 1) % this.cap; if (this.size < this.cap) this.size++; }
  toArray() { return this.size < this.cap ? this.data.slice(0, this.size) : [...this.data.slice(this.head), ...this.data.slice(0, this.head)]; }
}
```

### Appending to selections

```js
let allData = [];
function update(newRows) {
  allData = allData.concat(newRows);
  svg.selectAll("circle").data(allData, d => d.id).join(
    enter => enter.append("circle").attr("r", 0).attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).transition().attr("r", 3),
    update => update.attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
  );
}
```

---

## Common Pitfalls

1. **CSV values are always strings.** `"3" + "5" === "35"`. Always coerce numeric columns in the row accessor. This is the single most common D3 data bug.

2. **`+""` is `0`, not `NaN`.** Empty CSV cells become empty strings. `+"" === 0` silently corrupts aggregation. Guard with: `d.value === "" ? null : +d.value`.

3. **`d3.autoType` converts ZIP codes and IDs to numbers.** `"07030"` becomes `7030`. Use explicit row accessors for production data with leading zeros or numeric-looking identifiers.

4. **`d3.timeParse` returns `null` on mismatch — silently.** No error, no warning. Always check: `if (!date) console.warn(...)`.

5. **InternMap ≠ Map.** `d3.group` returns InternMap with value equality (Date/number keys work). Don't spread to a plain `Map` — you lose this behavior. But InternMap is iterable and has `.get()`, `.has()`, `.keys()`, `.values()`, `.entries()` — use it directly.

6. **`d3.sort` returns a new array.** Unlike `Array.sort()`, the original is unchanged. Forgetting the return value is a silent bug: `d3.sort(data, d => d.x)` does nothing if you don't capture the result.

7. **`d3.extent` on an empty array returns `[undefined, undefined]`.** This propagates to scales as `domain([undefined, undefined])`, producing NaN positions. Guard: `if (!data.length) return;`

8. **`d3.bin().domain()` must match the value accessor's domain.** If your values range 0–100 but you set `.domain([0, 1])`, most values land outside all bins. Always derive domain from the same accessor: `.domain(d3.extent(data, accessor))`.

9. **Missing values propagate through scales.** `scaleLinear()(undefined)` returns `NaN`. Elements positioned at `NaN` are invisible, not errored. Clean data before binding to scales or the missing marks will be silently lost.

---

## References

- [d3-array](https://d3js.org/d3-array) — group, rollup, bin, sort, rank, extent, sum, mean, quantile, cumsum, cross
- [d3-fetch](https://d3js.org/d3-fetch) — csv, tsv, json, text, xml, html, svg, image, blob
- [d3-dsv](https://d3js.org/d3-dsv) — csvParse, csvParseRows, csvFormat, tsvParse, autoType
- [d3-time-format](https://d3js.org/d3-time-format) — timeParse, timeFormat, utcParse, utcFormat
- [Observable: d3.group, d3.rollup](https://observablehq.com/@d3/d3-group)
- [Observable: d3.bin](https://observablehq.com/@d3/d3-bin)
- [Tidy Data — Hadley Wickham (2014)](https://doi.org/10.18637/jss.v059.i10) — the conceptual framework for long/tidy data transformations
