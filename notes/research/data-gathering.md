# Data Gathering: Beyond d3.csv

Research for expanding the data-gathering skill with modern browser-based data loading and processing techniques.

## Current Coverage

The existing SKILL.md covers:
- **d3.autoType** pitfalls (ZIP codes, booleans, inconsistent nulls) and explicit row accessors
- **Missing data** taxonomy (`""` vs `null` vs `undefined` vs `NaN`) with the `+"" === 0` bug
- **Data smells**: unsorted time data, duplicates, inconsistent categories, sentinel values, BOM, mixed numeric formats, single-row groups, empty `d3.extent`
- **d3.bin domain mismatch** and InternMap value equality for Date keys
- **Columnar typed arrays** for Canvas/WebGL (Float64Array, pre-computed sort indices)
- **Streaming large CSV** via `fetch` + `ReadableStream` + manual line splitting

Not covered: DuckDB-WASM, Parquet/Arrow in browser, Papa Parse, Observable patterns, AbortController, progressive rendering, or decision guidance for when to reach beyond `d3.csv`.

---

## DuckDB-WASM (Client-Side SQL)

### What problem it solves
`d3.group` and `d3.rollup` work on in-memory arrays and can't push predicates or projections down to the data source. When a 200 MB Parquet file sits on a CDN and you need a grouped bar chart of 50 rows, you'd normally download the whole file. DuckDB-WASM runs full SQL in the browser with predicate/projection pushdown -- it fetches only the columns and row groups it needs via HTTP range requests.

### Scale
- **Not worth it below ~100K rows.** `d3.csv` + `d3.group` is simpler and fast enough.
- **Sweet spot: 100K--10M rows**, especially when the visualization only needs aggregated results (sums, means, histograms).
- **Upper bound: limited by browser memory** (typically 1--4 GB usable). DuckDB-WASM can query Parquet files larger than memory if the query is selective enough.

### Bundle cost
The WASM binary is ~4 MB compressed. Initialization takes 1--3 seconds on first load (cached afterward). Cold query: ~40ms; warm query: ~6ms. Not appropriate for lightweight pages or small datasets.

### D3 integration
Query results come back as Apache Arrow tables. Convert to row arrays for D3:

```js
import * as duckdb from "@duckdb/duckdb-wasm";

// Initialize (one-time)
const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
const worker = new Worker(bundle.mainWorker);
const logger = new duckdb.ConsoleLogger();
const db = new duckdb.AsyncDuckDB(logger, worker);
await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
const conn = await db.connect();

// Query a remote Parquet file -- only fetches needed columns/rows
const result = await conn.query(`
  SELECT region, SUM(sales) as total
  FROM 'https://example.com/data.parquet'
  WHERE year >= 2020
  GROUP BY region
  ORDER BY total DESC
`);

// Arrow table -> JS array for D3
const rows = result.toArray().map(row => ({...row}));
// Now use rows with d3.scaleBand, d3.scaleLinear, etc.
```

### When to use vs d3.group/rollup
| Scenario | Tool |
|---|---|
| CSV < 50K rows, full dataset needed | `d3.csv` + row accessor |
| In-memory array, simple grouping | `d3.group` / `d3.rollup` |
| Remote Parquet, need aggregation only | DuckDB-WASM SQL |
| Multiple ad-hoc queries on same dataset | DuckDB-WASM (register table once) |
| Joins across multiple files | DuckDB-WASM SQL |
| User-driven filtering on large data | DuckDB-WASM (parameterized queries) |

### Production readiness
Mature. Used in Observable, MotherDuck, and numerous production dashboards. Active development. As of late 2025, supports Iceberg tables and S3 access from the browser.

---

## Arrow and Parquet in Browser (Columnar Data, Zero-Copy)

### Three libraries, different tradeoffs

| Library | Approach | Bundle size | Key feature |
|---|---|---|---|
| **apache-arrow** (JS) | Pure JS Arrow reader | ~150 KB | Zero-copy vectors from typed arrays via `makeVector` |
| **parquet-wasm** | Rust/WASM Parquet reader | 456 KB--1.2 MB | Full Parquet codec support, async partial reads |
| **hyparquet** | Pure JS Parquet reader | **9.2 KB** min.gz | Zero dependencies, HTTP range requests, column/row selection |

### hyparquet: lightweight Parquet for viz

Designed specifically for reading Parquet over HTTP in the browser. Key capabilities:
- **HTTP range requests**: fetches only needed row groups and columns. Optimistically fetches 512 KB of footer metadata (covers 99% of files).
- **Column selection**: read only the columns your chart needs.
- **Row group filtering**: skip row groups that don't match your filter.
- **Zero dependencies**, pure JavaScript.

```js
import { parquetRead } from "hyparquet";
import { asyncBufferFromUrl } from "hyparquet";

// Read specific columns from a remote Parquet file
const buffer = await asyncBufferFromUrl("https://example.com/data.parquet");
const rows = [];
await parquetRead({
  file: buffer,
  columns: ["date", "value"],  // only fetch these columns
  rowEnd: 10000,               // limit rows
  onComplete: data => rows.push(...data)
});
// rows is now an array D3 can consume directly
```

### apache-arrow: when DuckDB is overkill

For pre-aggregated Arrow files (e.g., from Observable data loaders), Arrow JS reads them with zero-copy into typed arrays:

```js
import { tableFromIPC } from "apache-arrow";

const response = await fetch("/data/summary.arrow");
const table = await tableFromIPC(response);

// Column access -- returns typed arrays, no copying
const dates = table.getChild("date").toArray();
const values = table.getChild("value").toArray();   // Float64Array

// Row access for D3
const rows = [...table];  // iterates row proxies
```

### When to use each
- **hyparquet**: You have Parquet files on a CDN and want to read them without a WASM runtime. Best for read-only viz of specific columns. Tiny bundle.
- **parquet-wasm**: You need full Parquet codec support (Zstd, LZ4, Brotli) or write support. Heavier but comprehensive.
- **apache-arrow**: You already have Arrow IPC files (e.g., from a data loader build step). Zero-copy typed array access.
- **DuckDB-WASM**: You need SQL queries, joins, or aggregations on Parquet. Heaviest but most capable.

### Production readiness
All three are production-ready. hyparquet is the most pragmatic for visualization use cases due to tiny bundle size. parquet-wasm and apache-arrow are Apache Foundation projects with broad ecosystem support.

---

## Streaming and Progressive Loading (Large Files, Chunked Parsing)

### The problem
`d3.csv` loads the entire response as text, then parses all rows. For a 100 MB CSV, the browser holds the raw text (~100 MB) plus the parsed array (~200+ MB of objects) simultaneously. The UI freezes during parsing.

### Papa Parse: production-grade streaming CSV

Papa Parse adds three things the existing SKILL.md streaming pattern lacks:
1. **Web Worker mode** (`worker: true`): parsing happens off the main thread entirely.
2. **Chunk callbacks**: receive batches of rows instead of one-at-a-time, reducing callback overhead.
3. **Auto-detection**: handles delimiters, quotes, newlines within fields, BOM.

```js
Papa.parse("https://example.com/huge.csv", {
  download: true,
  worker: true,
  header: true,
  chunk(results, parser) {
    // results.data is an array of row objects (one chunk)
    // Process incrementally: update bins, append to typed arrays, etc.
    for (const row of results.data) {
      updateHistogram(+row.value);
    }
  },
  complete() {
    renderChart();  // final render after all chunks
  }
});
```

**Limitation**: When using `worker: true`, you cannot pause/resume -- the entire file is read into the worker's memory. For true backpressure-aware streaming, use the manual `fetch` + `ReadableStream` approach already in the SKILL.md.

### Progressive rendering pattern

For very large files, render intermediate results so the user sees data immediately:

```js
let bins = d3.bin().domain([0, 100]).thresholds(50)([]); // empty bins
let rowCount = 0;

Papa.parse(file, {
  header: true,
  chunk(results) {
    for (const row of results.data) {
      const v = +row.value;
      if (isFinite(v)) {
        const bin = bins.find(b => v >= b.x0 && v < b.x1);
        if (bin) bin.push(row);
      }
    }
    rowCount += results.data.length;
    if (rowCount % 50000 === 0) renderHistogram(bins); // progressive update
  },
  complete() {
    renderHistogram(bins); // final render
  }
});
```

### Web Worker + manual streaming (maximum control)

For backpressure-aware streaming without Papa Parse:

```js
// worker.js
self.onmessage = async ({ data: url }) => {
  const response = await fetch(url);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", header = null, batch = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) {
      if (!header) { header = line.split(","); continue; }
      batch.push(line);
      if (batch.length >= 10000) {
        self.postMessage({ batch, header });
        batch = [];
      }
    }
  }
  if (batch.length) self.postMessage({ batch, header });
  self.postMessage({ done: true });
};
```

### Scale guidance
| Rows | Approach |
|---|---|
| < 50K | `d3.csv` with row accessor |
| 50K--500K | `d3.csv` is fine, but consider typed arrays for Canvas |
| 500K--5M | Papa Parse with `worker: true` and chunk callback |
| 5M--50M | Web Worker + manual ReadableStream + progressive rendering |
| > 50M | Use Parquet format instead of CSV |

---

## Observable Patterns (FileAttachment, Data Loaders, Data Flow)

### Build-time data loaders

Observable Framework's key insight: **move heavy processing to build time**. A data loader is any script (JS, Python, R, shell) that writes to stdout. Framework runs it at build time and caches the output as a static file.

```
docs/
  data/
    summary.csv.py    # data loader: runs at build, outputs CSV
    summary.csv       # generated output (cached, served as static file)
  index.md            # loads via FileAttachment("data/summary.csv").csv()
```

This pattern is relevant for d3-power-tools even outside Observable:
- **Pre-aggregate at build time** using DuckDB CLI, Python, or Node scripts.
- **Ship small derived files** (aggregated CSV, Arrow IPC) instead of raw data.
- **Cache invalidation** by checking source file modification times.

### FileAttachment lazy loading

`FileAttachment("file.csv")` doesn't load the file -- it returns an object with async methods (`.csv()`, `.json()`, `.arrow()`, `.stream()`). The actual fetch happens only when you call a method. This is a good pattern for any data loading API: declare the source, defer the fetch.

### What to adopt outside Observable
1. **Build-time preprocessing**: Use a build script to convert large CSVs to Parquet or pre-aggregated Arrow files. Ship the small derived file.
2. **Lazy loading pattern**: Don't fetch data until the chart that needs it is about to render (e.g., IntersectionObserver + data fetch).
3. **Format-appropriate methods**: `.csv()` returns parsed rows, `.arrow()` returns an Arrow table, `.json()` returns parsed JSON. Match the loading method to the visualization's needs.

---

## Modern Fetch Patterns (AbortController, Streaming JSON, Response.body)

### AbortController for cancellable loads

Essential for dashboards where users change filters before data finishes loading:

```js
let controller = null;

async function loadData(url) {
  // Cancel any in-flight request
  if (controller) controller.abort();
  controller = new AbortController();

  try {
    const response = await fetch(url, { signal: controller.signal });
    const data = await response.json();
    renderChart(data);
  } catch (e) {
    if (e.name === "AbortError") return;  // expected, ignore
    throw e;
  }
}
```

### Streaming JSON (NDJSON)

For APIs that return newline-delimited JSON, process rows as they arrive:

```js
async function* streamNDJSON(url) {
  const response = await fetch(url);
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line);
    }
  }
  if (buffer.trim()) yield JSON.parse(buffer);
}

// Usage with D3
const points = [];
for await (const row of streamNDJSON("/api/data.ndjson")) {
  points.push(row);
  if (points.length % 1000 === 0) updateScatterplot(points);
}
```

### Progress tracking

```js
async function fetchWithProgress(url, onProgress) {
  const response = await fetch(url);
  const total = +response.headers.get("Content-Length") || 0;
  const reader = response.body.getReader();
  let received = 0;
  const chunks = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    if (total) onProgress(received / total);
  }

  const blob = new Blob(chunks);
  return blob.text();
}
```

---

## Decision Guidance (When to Use Which Strategy)

### By dataset size

| Dataset size | Format | Loading strategy | Processing |
|---|---|---|---|
| < 1K rows | CSV/JSON | `d3.csv` / `d3.json` | Row accessor, `d3.group` |
| 1K--50K rows | CSV/JSON | `d3.csv` / `d3.json` | Row accessor, typed arrays if Canvas |
| 50K--500K rows | CSV or Parquet | `d3.csv` or hyparquet | Pre-aggregate if possible |
| 500K--5M rows | Parquet | DuckDB-WASM or hyparquet | SQL aggregation, typed arrays |
| 5M--50M rows | Parquet | DuckDB-WASM | SQL with pushdown, progressive render |
| > 50M rows | Parquet (partitioned) | DuckDB-WASM or server-side | Pre-aggregate at build time |

### By interaction pattern

| Pattern | Strategy |
|---|---|
| Static chart, data changes rarely | Build-time preprocessing, ship small derived file |
| Dashboard with filter controls | DuckDB-WASM: parameterized queries on user interaction |
| Real-time streaming data | NDJSON + async generator + progressive rendering |
| User uploads a file | Papa Parse with Web Worker for CSV; hyparquet for Parquet |
| Multiple linked views, same data | Load once into DuckDB, query per view |
| Lazy-loaded chart (below fold) | IntersectionObserver + deferred fetch |

### Bundle budget guidance

| Library | Compressed size | Justification threshold |
|---|---|---|
| d3-dsv (included in D3) | 0 KB extra | Default choice |
| hyparquet | ~9 KB | Any Parquet file, even small ones |
| Papa Parse | ~15 KB | Streaming/worker CSV parsing needed |
| apache-arrow | ~150 KB | Arrow IPC files from build pipeline |
| parquet-wasm | 456 KB--1.2 MB | Need Parquet write or exotic codecs |
| DuckDB-WASM | ~4 MB | SQL queries, joins, aggregations on large data |

---

## Code Patterns

### Pattern 1: Tiered loading with fallback

```js
async function loadData(url) {
  if (url.endsWith(".parquet")) {
    // Try hyparquet for small Parquet files
    const { parquetRead, asyncBufferFromUrl } = await import("hyparquet");
    const buffer = await asyncBufferFromUrl(url);
    const rows = [];
    await parquetRead({ file: buffer, onComplete: data => rows.push(...data) });
    return rows;
  }
  // Default: d3.csv with explicit types
  return d3.csv(url, d => ({
    date: new Date(d.date),
    value: d.value === "" ? null : +d.value,
    category: d.category
  }));
}
```

### Pattern 2: DuckDB-WASM singleton

```js
let _db = null;

async function getDB() {
  if (_db) return _db;
  const duckdb = await import("@duckdb/duckdb-wasm");
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const worker = new Worker(bundle.mainWorker);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  _db = db;
  return db;
}

async function queryParquet(sql) {
  const db = await getDB();
  const conn = await db.connect();
  try {
    const result = await conn.query(sql);
    return result.toArray().map(row => ({...row}));
  } finally {
    await conn.close();
  }
}

// Usage
const data = await queryParquet(`
  SELECT month, SUM(revenue) as revenue
  FROM 'https://cdn.example.com/sales.parquet'
  GROUP BY month ORDER BY month
`);
const x = d3.scaleBand().domain(data.map(d => d.month));
```

### Pattern 3: Progressive CSV with typed array accumulation

```js
async function loadLargeCSV(url, { onProgress, xCol, yCol }) {
  const response = await fetch(url);
  const total = +response.headers.get("Content-Length") || 0;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", header = null, received = 0;

  // Growable typed arrays (pre-allocate, resize as needed)
  let capacity = 65536;
  let xArr = new Float64Array(capacity);
  let yArr = new Float64Array(capacity);
  let n = 0;

  function grow() {
    capacity *= 2;
    const newX = new Float64Array(capacity);
    const newY = new Float64Array(capacity);
    newX.set(xArr); newY.set(yArr);
    xArr = newX; yArr = newY;
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    received += value.length;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      if (!header) {
        header = d3.csvParseRows(line)[0];
        continue;
      }
      const cols = d3.csvParseRows(line)[0];
      if (n >= capacity) grow();
      xArr[n] = +cols[header.indexOf(xCol)];
      yArr[n] = +cols[header.indexOf(yCol)];
      n++;
    }

    if (total && onProgress) onProgress(received / total);
  }

  return {
    x: xArr.subarray(0, n),
    y: yArr.subarray(0, n),
    length: n
  };
}
```

### Pattern 4: Cancellable data loading for filter-driven dashboards

```js
function createDataLoader(baseUrl) {
  let controller = null;

  return async function load(filters) {
    if (controller) controller.abort();
    controller = new AbortController();

    const params = new URLSearchParams(filters);
    try {
      const res = await fetch(`${baseUrl}?${params}`, {
        signal: controller.signal
      });
      return await res.json();
    } catch (e) {
      if (e.name === "AbortError") return null; // cancelled, caller ignores
      throw e;
    }
  };
}

// Usage
const loadSales = createDataLoader("/api/sales");
filterDropdown.on("change", async function() {
  const data = await loadSales({ region: this.value });
  if (data) updateChart(data); // null means request was superseded
});
```

---

## Sources

- [DuckDB-WASM documentation](https://duckdb.org/docs/stable/clients/wasm/overview)
- [DuckDB-WASM query API](https://duckdb.org/docs/stable/clients/wasm/query)
- [DuckDB WASM + D3 visualization](https://travishorn.com/high-performance-data-visualization-in-the-browser-with-duckdb-and-parquet/)
- [DuckDB Iceberg in Browser (Dec 2025)](https://duckdb.org/2025/12/16/iceberg-in-the-browser)
- [hyparquet - Parquet parser for JS](https://github.com/hyparam/hyparquet)
- [hyparquet: Quest for Instant Data](https://blog.hyperparam.app/2025/07/24/quest-for-instant-data/)
- [parquet-wasm](https://github.com/kylebarron/parquet-wasm)
- [Apache Arrow JS](https://arrow.apache.org/docs/js/)
- [Papa Parse](https://www.papaparse.com/)
- [Observable Framework data loaders](https://observablehq.observablehq.cloud/framework/data-loaders)
- [Observable FileAttachment docs](https://observablehq.com/documentation/data/files/file-attachments)
- [Processing 13M rows in browser](https://dev.to/wesleymreng7/processing-13-million-rows-from-a-csv-file-in-the-browser-without-freezing-the-screen-1nih)
- [MDN ReadableStream](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams)
- [DuckDB-WASM performance benchmarks](https://shell.duckdb.org/versus)
- [Mosaic (DuckDB + visualization)](https://idl.uw.edu/mosaic/duckdb/)
