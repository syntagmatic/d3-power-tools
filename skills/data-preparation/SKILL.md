---
name: data-preparation
description: "Data loading, parsing, cleaning, reshaping, and transformation for D3.js visualizations. Use this skill whenever the user needs to load CSV/JSON/TSV data, coerce types, parse dates, handle missing values, reshape data with d3.group/d3.rollup, pivot wide-to-long, aggregate with d3.sum/d3.mean/d3.bin, join datasets, compute derived fields, or prepare data for scales, layouts, and bindable arrays. Also covers d3.csv, d3.json, d3.autoType, d3.group, d3.rollup, d3.flatGroup, d3.flatRollup, d3.index, d3.bin, d3.cumsum, d3.rank, d3.cross, d3.timeParse, missing data, NaN handling, data cleaning, wide-to-long, pivot, normalization, columnar typed arrays, and streaming. Related skills: parallel-coordinates (normalization), canvas-rendering / webgl-rendering (typed arrays), geographic-maps (TopoJSON loading), hierarchy-layouts (d3.stratify), fallback-table (table rendering from prepared data)."
---

# Data Preparation

Everything between raw data and bindable arrays. D3 works with plain arrays and objects — the preparation layer delivers arrays whose elements map 1:1 to visual marks, with every field typed and scale-ready.

## autoType Pitfalls

```js
const data = await d3.csv("data.csv", d3.autoType);
```

Good for prototyping. Surprises: `"true"`→boolean, `"07030"`→`7030` (loses leading zero), numeric-looking IDs become numbers. **Prefer explicit row accessors for production** — especially data with FIPS codes, ZIP codes, or ID columns.

## The Many Faces of Missing

| Source | What you get | `+x` | `isFinite(x)` |
|--------|-------------|------|---------------|
| Empty CSV cell | `""` | `0` (!) | `true` (!) |
| CSV "NA" | `"NA"` | `NaN` | `false` |
| autoType empty | `null` | `0` (!) | `false` |
| JSON null | `null` | `0` (!) | `false` |
| JSON missing key | `undefined` | `NaN` | `false` |

**Guard**: `const safeNum = s => s === "" ? null : +s;`

Use `isFinite()` over `!isNaN()` — also rejects `Infinity`.

`d3.count(data, d => d.value)` counts only finite numeric values (skips NaN/null/undefined), unlike `.length`.

## InternMap vs Map

`d3.group`, `d3.rollup`, `d3.index` return `InternMap` with **value equality** — Date and number keys work unlike plain Map. Don't spread to a plain Map — you lose this behavior. InternMap is iterable with `.get()`, `.has()`, `.keys()`, `.values()`, `.entries()`.

```js
d3.group(data, d => d.date).get(new Date("2024-03-15")); // works!
```

## d3.bin Domain Mismatch

`d3.bin().domain()` **must match** the value accessor's domain. If values range 0–100 but you set `.domain([0, 1])`, most values land outside all bins. Always derive domain from the same accessor:

```js
const bins = d3.bin()
  .domain(d3.extent(data, d => d.age))
  .thresholds(20)
  .value(d => d.age)(data);
```

`d3.bin` works directly with typed arrays: `d3.bin().thresholds(40)(new Float64Array(values))`.

## Streaming: Circular Buffer

```js
class CircularBuffer {
  constructor(cap) { this.data = new Array(cap); this.head = 0; this.size = 0; this.cap = cap; }
  push(item) { this.data[this.head] = item; this.head = (this.head + 1) % this.cap; if (this.size < this.cap) this.size++; }
  toArray() { return this.size < this.cap ? this.data.slice(0, this.size) : [...this.data.slice(this.head), ...this.data.slice(0, this.head)]; }
}
```

## Columnar Typed Arrays (>50K rows)

For Canvas/WebGL rendering pipelines:

```js
const n = data.length;
const x = new Float64Array(n), y = new Float64Array(n), cat = new Uint8Array(n);
const categoryIndex = new Map([...new Set(data.map(d => d.type))].map((c, i) => [c, i]));
data.forEach((d, i) => { x[i] = d.longitude; y[i] = d.latitude; cat[i] = categoryIndex.get(d.type); });
```

### Pre-Computed Sort Indices

```js
const order = d3.range(n);
order.sort((a, b) => x[a] - x[b]);
for (const i of order) drawPoint(x[i], y[i], cat[i]);
```

## Streaming Large CSV (>50 MB)

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

## Common Pitfalls

1. **CSV values are always strings.** `"3" + "5" === "35"`. Always coerce in the row accessor. Single most common D3 data bug.

2. **`+""` is `0`, not `NaN`.** Empty cells → empty strings. `+"" === 0` silently corrupts aggregation. Guard: `d.value === "" ? null : +d.value`.

3. **`d3.autoType` converts ZIP/FIPS/IDs to numbers.** `"07030"` → `7030`. Use explicit row accessors for leading-zero data.

4. **`d3.timeParse` returns `null` on mismatch — silently.** No error, no warning. Always check: `if (!date) console.warn(...)`.

5. **InternMap ≠ Map.** Don't spread `d3.group` results to plain Map — loses value equality for Date/number keys.

6. **`d3.sort` returns a new array.** Unlike `Array.sort()`, original unchanged. Forgetting the return value is a silent no-op.

7. **`d3.extent` on empty array returns `[undefined, undefined]`.** Propagates to `domain([undefined, undefined])` → NaN positions. Guard: `if (!data.length) return;`.

8. **`d3.bin().domain()` mismatched.** Values outside domain land in no bin — silently lost.

9. **Missing values propagate through scales.** `scaleLinear()(undefined)` → `NaN`. Elements at NaN are invisible, not errored. Clean before binding.

## References

- [d3-array](https://d3js.org/d3-array) — group, rollup, bin, sort, rank, extent, sum, mean, quantile, cumsum, cross
- [d3-fetch](https://d3js.org/d3-fetch) — csv, tsv, json
- [d3-dsv](https://d3js.org/d3-dsv) — csvParse, autoType
- [d3-time-format](https://d3js.org/d3-time-format) — timeParse, utcParse
- [Tidy Data](https://doi.org/10.18637/jss.v059.i10) — Hadley Wickham (2014)
