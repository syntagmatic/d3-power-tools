---
name: data-table
description: "Build accessible data tables as companions or alternatives to D3.js visualizations. Use this skill when the user needs a table alternative to a chart, sortable/filterable data tables, chart↔table toggle, linked highlighting between table rows and chart elements, virtual scrolling for large datasets, column management, keyboard navigation, conditional formatting, grouping/subtotals, CSV export, or any pattern where tabular data complements or replaces a visualization."
---

# Data Tables for D3 Visualizations

Charts show patterns; tables show values. When the viewer's task is looking up a specific number, comparing exact figures across rows, or exporting data, a table outperforms any chart. Build tables as first-class views alongside D3 visualizations, not as accessibility afterthoughts.

Related: `linked-views` · `brushing` · `canvas-accessibility` · `color` · `responsive` · `sparkcharts`

## Table vs. Chart: When the Table Wins

Use a table — not a chart — when:

- **Exact value lookup** — the viewer needs specific numbers, not trends. Charts encode values as position/length at ~10% precision; tables give the exact figure.
- **Small n** — fewer than ~20 data points with 3+ attributes. A chart of 8 rows wastes space.
- **Mixed units** — dollars, percentages, counts, and dates side-by-side. No single y-axis handles that.
- **Comparison across attributes** — the viewer reads across a row. Charts require multiple encodings or facets.
- **Mobile** — complex charts degrade on small screens; tables scroll naturally.

Offer **both views** (toggle or side-by-side) when different viewers need different tasks.

## When Not to Use This

Don't build a table when the viewer needs **distribution shape**, **trends over time**, or **spatial patterns**. A 500-row table of time-series data is less useful than a line chart. If the task is "which is biggest?", a bar chart communicates faster than scanning a column.

## Number Formatting and Alignment

Poor alignment is the most common table design failure.

```css
td.num { text-align: right; font-variant-numeric: tabular-nums; }
th.num { text-align: right; }
```

- **Consistent precision** — all values in a column get the same decimal places. `d3.format(',.1f')` not a mix of `3.1` and `3.14159`.
- **Units in the header, not every cell** — write `GDP ($M)` in `<th>`, format cells as `1,234`. Exception: currency symbols aid scanning in financial tables.
- **Group separators** — `d3.format(',')` turns `1234567` into `1,234,567`.

## Architecture: Chart ↔ Table Toggle

```
┌──────────────────────────────────┐
│  Toggle bar (chart / table)      │
├──────────────────────────────────┤
│  Chart container  OR  Table view │
│  (canvas/SVG)         (sticky    │
│                        header +  │
│                        scroll    │
│                        body)     │
├──────────────────────────────────┤
│  Status bar (count, filter info) │
└──────────────────────────────────┘
```

Table and chart are sibling containers. Toggle hides one and shows the other via `display`/`aria-hidden`. Both bind the same data array so filter/selection state is shared. Use `aria-pressed` on the toggle button.

## Column Specification

```js
const columns = [
  { key: 'name', label: 'Name', type: 'string' },
  { key: 'population', label: 'Population', type: 'number', format: d3.format(',') },
  { key: 'gdp', label: 'GDP per Capita', type: 'number', format: d3.format('$,.0f') },
  { key: 'continent', label: 'Continent', type: 'string' }
];
```

`type` drives sort comparator (lexicographic vs. numeric) and cell alignment (right for numbers).

## D3 Nested Join Pattern

Two-level join — rows keyed by `d.id`, cells by column index:

```js
const rows = d3.select(tbody).selectAll('tr')
  .data(data, d => d.id)
  .join('tr');

rows.selectAll('td')
  .data(d => columns.map(col => col.format ? col.format(d[col.key]) : d[col.key]))
  .join('td')
    .text(d => d);
```

The **outer join uses a key function** (`d => d.id`) for stable DOM identity during filter/sort — without it, D3 reuses `<tr>` by index, causing flash-of-wrong-content. The **inner cell join must NOT have a key function** — cells map 1:1 to columns by index. A key causes collisions when two cells format to the same string.

## Sortable Columns

Click header to sort ascending, click again for descending:

- Use `d3.ascending`/`d3.descending` as comparators
- Set `aria-sort` on the active `<th>` (`"ascending"`, `"descending"`, `"none"` on others)
- Make headers `tabindex="0"`, handle Enter/Space for keyboard users
- **Sort a copy**: `[...data].sort(...)`. `Array.sort()` mutates in place — if the chart reads the same array, its order silently changes.

### Multi-Sort

Shift-click adds secondary sort keys. Track as an ordered array `[{key, dir}]`:

```js
let sortKeys = []; // first entry is primary

function onHeaderClick(col, event) {
  if (event.shiftKey) {
    const idx = sortKeys.findIndex(s => s.key === col.key);
    if (idx >= 0) sortKeys[idx].dir *= -1;
    else sortKeys.push({ key: col.key, dir: 1 });
  } else {
    const prev = sortKeys.find(s => s.key === col.key);
    sortKeys = [{ key: col.key, dir: prev ? prev.dir * -1 : 1 }];
  }
  renderTable(applyFilters(data));
}

// Chain comparators — fall through when equal
const multiSort = keys => (a, b) => {
  for (const { key, dir } of keys) {
    const cmp = d3.ascending(a[key], b[key]);
    if (cmp !== 0) return cmp * dir;
  }
  return 0;
};
```

Show sort priority with a small numeral badge (1, 2, 3) next to the arrow. Set `aria-sort` only on the primary column.

## Linked Highlighting

Hover/select in chart highlights the table row, and vice versa. See `linked-views` skill for the shared state pattern (`d3.dispatch` or a state object with `hoveredId`/`selectedIds`/`notify()`).

Table-specific details:
- `.classed('hovered', d => d.id === state.hoveredId)` on `<tr>` elements
- **Scroll-to-row**: `row.scrollIntoView({ block: 'nearest' })` on selection only — on hover it fights the user's scrolling

## Filtering

Chain independent filters through a pipeline. Each filter is a predicate; a row passes only if every predicate returns true:

```js
const activeFilters = new Map(); // key → predicate fn

function applyFilters(data) {
  const preds = [...activeFilters.values()];
  const filtered = preds.length ? data.filter(d => preds.every(f => f(d))) : data;
  liveRegion.textContent = `Showing ${filtered.length} of ${data.length} rows`;
  return filtered;
}
```

`liveRegion` is a `div[aria-live="polite"]` — without it, screen reader users filter blindly.

### Global text search

Debounce input, search across all columns:

```js
const searchInput = d3.select('#search').on('input', debounce(e => {
  const q = e.target.value.toLowerCase();
  if (q) activeFilters.set('search', d =>
    columns.some(col => String(d[col.key]).toLowerCase().includes(q)));
  else activeFilters.delete('search');
  renderTable(applyFilters(data));
}, 150));

function debounce(fn, ms) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
```

### Other filter types

**Categorical dropdown**: build `<select>` options from `[...new Set(data.map(d => d[col.key]))]`. On change, set predicate `d => d[col.key] === value` or delete the filter for "All".

**Range slider**: `<input type="range">` with `d3.extent` for min/max. Predicate: `d => d[col.key] >= threshold`.

**Clear all**: `activeFilters.clear()`, reset all filter control DOM state (selects, inputs), re-render.

## Column Management

### Show/hide columns

Checkbox dropdown controlling `col.visible`. Thread `visibleCols = () => columns.filter(c => c.visible)` through both header and body joins — the cell data mapper must reference the same column list as `<th>`.

```js
columns.forEach(c => c.visible = true);

menu.selectAll('label').data(columns).join('label')
  .html(col => `<input type="checkbox" checked> ${col.label}`)
  .select('input')
    .property('checked', col => col.visible)
    .on('change', (e, col) => { col.visible = e.target.checked; renderTable(applyFilters(data)); });
```

### Frozen first column

CSS-only — pin the row label column during horizontal scroll:

```css
th:first-child, td:first-child {
  position: sticky; left: 0; z-index: 1;
  background: var(--bg, white); /* must be opaque or content bleeds through */
}
th:first-child { z-index: 2; }
```

## Keyboard Navigation

See `canvas-accessibility` skill for the full WAI-ARIA grid pattern (roving tabindex, arrow key navigation, Home/End/Ctrl shortcuts).

Table-specific additions:
- Set `role="grid"` on the table, `role="row"`/`role="gridcell"` on rows/cells
- Sortable headers need `tabindex="0"` + Enter/Space handling to trigger `onHeaderClick`
- Live region announces sort/filter changes: `liveRegion.text(\`Sorted by ${col.label}, ascending\`)`
- `.sr-only` class for visually-hidden live region: `position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0)`

## Conditional Formatting

### Heatmap cells

Color-code numeric cells with a luminance check for WCAG contrast:

```js
const color = d3.scaleSequential(d3.interpolateBlues)
  .domain(d3.extent(data, d => d.value));

rows.selectAll('td.heatmap')
  .style('background-color', d => color(d))
  .style('color', d => d3.lab(color(d)).l < 55 ? '#fff' : '#000');
```

### Data bars

A percentage-width `<div>` inside the cell creates an in-cell bar. Scale with `d3.scaleLinear([0, max], [0, 100])`, render a `.bar-fill` div at that width, overlay a `.bar-label` span with the formatted value. Use `position: relative`/`absolute` layering.

### Sparkline cells

Inline SVG sparklines in cells. See `sparkcharts` skill for the full pattern. Key integration: append a small `<svg>` (e.g., 60×16), draw `d3.line()` from `d.series`, add `aria-label` with trend summary ("Trending up 12%") since screen readers can't interpret paths.

## Grouping and Subtotals

Use `d3.group(data, d => d.category)` to partition, then render per-group `<tbody>` with a header row and expand/collapse:

```js
for (const [name, rows] of grouped) {
  const section = container.append('tbody');
  const header = section.append('tr').attr('class', 'group-header');
  header.append('td').attr('colspan', visibleCols().length)
    .html(`<button aria-expanded="true">${name} (${rows.length})</button>`);

  section.selectAll('tr.data-row').data(rows, d => d.id).join('tr')
    .attr('class', 'data-row')
    .selectAll('td')
      .data(d => visibleCols().map(col => col.format ? col.format(d[col.key]) : d[col.key]))
      .join('td').text(d => d);

  header.select('button').on('click', function() {
    const exp = this.getAttribute('aria-expanded') === 'true';
    this.setAttribute('aria-expanded', String(!exp));
    section.selectAll('tr.data-row').style('display', exp ? 'none' : null);
  });
}
```

**Subtotals**: compute per-group aggregates with `d3.sum` over numeric columns, render as a styled row (`bold, border-top, aria-label="Subtotal"`).

## Export

Export the **filtered, sorted** data — not the original array. Both formats share the same column/row mapping:

```js
function exportCSV(data, columns) {
  const escape = v => { const s = String(v); return /[,"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const csv = [columns.map(c => c.label), ...data.map(d => columns.map(c => escape(d[c.key])))].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'data.csv' }).click();
}
```

**Clipboard copy**: same data, tab-separated (`columns.map(c => d[c.key]).join('\t')`), via `navigator.clipboard.writeText()`. Tabs paste cleanly into Excel/Sheets without an import dialog. Announce: `liveRegion.text(\`Copied ${data.length} rows\`)`.

## Virtual Scrolling (10K+ rows)

Without virtualization, 50K+ DOM nodes cause scroll lag. Render only visible rows:

1. Container with `max-height` and `overflow-y: auto`
2. Spacer element (`height: data.length * rowHeight`) to size the scrollbar
3. On scroll, compute `startIdx`/`endIdx` from `scrollTop` and `clientHeight`
4. Buffer 5-10 rows above/below viewport to prevent white flash
5. Slice data, join visible rows, offset `<tbody>` with `translateY(startIdx * rowHeight)`
6. Set `aria-rowcount` on `<table>` and `aria-rowindex` on each `<tr>`

D3's data join handles row recycling: `tbody.selectAll('tr').data(slice, d => d.id).join('tr')`.

**Gotcha**: after sorting, re-call `renderVisible()` — data order changed but scroll position didn't.

**Ctrl+F is broken.** Virtual scrolling removes off-screen rows from DOM. Compensate with a visible search input using the filter pipeline above.

### When to paginate instead

Virtual scrolling suits exploration — free scrolling through sorted/filtered data. Server-side pagination suits datasets exceeding browser memory. Tradeoff: pagination loses scroll momentum but works at any scale. If the full dataset fits in memory (<100K rows), virtual scrolling is simpler.

## Observable Plot Note

Plot's `Plot.table()` produces an HTML table outside the Plot SVG. Fine for basic sortable tables from tidy data. Reach for D3 when you need linked highlighting, virtual scrolling, or chart↔table toggle — Plot's table has no interaction hooks.

## Common Pitfalls

1. **No key on row join** — `d => d.id` on the outer join is critical. Without it, sort/filter causes DOM reuse by index and rows show wrong data momentarily.
2. **Key on cell join** — inner `selectAll('td').data(...)` must use index matching. A key function causes collisions when two cells format to the same string.
3. **Left-aligned numbers** — numbers without `text-align: right` and `tabular-nums` are unreadable for comparison.
4. **Inconsistent decimal places** — mixing `3.1` and `3.14` in one column makes scanning impossible. Set one `d3.format` per column.
5. **`scrollIntoView` on hover** — restrict to click/selection. On hover it fights the user's scrolling.
6. **Sticky + border-collapse** — `position: sticky` breaks with `border-collapse: collapse`. Use `border-collapse: separate; border-spacing: 0`.
7. **Missing `aria-live` on filter results** — screen reader users type a filter query and hear nothing.
8. **Exporting raw data instead of current view** — export must use the filtered/sorted array.
9. **Heatmap cells without contrast check** — dark backgrounds with dark text fail WCAG. Always check luminance.
10. **Frozen column transparent background** — content scrolls behind the frozen column if background isn't opaque.
11. **Tab-trapping in grid navigation** — roving tabindex must allow Tab to leave the table. Only handle arrow keys.

## References

- [Sortable Table — D3 Observable](https://observablehq.com/@d3/sortable-table) — Bostock's canonical sortable table
- [Ten Guidelines for Better Tables](https://www.cambridge.org/core/journals/journal-of-benefit-cost-analysis/article/abs/ten-guidelines-for-better-tables/74C6FD9FEB12038A52A95B9FBCA05A12) — Schwabish on alignment, units, and whitespace
- [WAI-ARIA Grid Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) — interactive tables with cell-level keyboard navigation
- [Web Typography: Tables](https://alistapart.com/article/web-typography-tables/) — Richard Rutter on tabular-nums and alignment
