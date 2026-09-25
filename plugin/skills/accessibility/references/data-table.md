# Data tables

Absorbed from the v2 `data-table` skill. Open when building a table view: alongside a chart, as its accessible alternative, or on its own.

## Table or chart

Table: exact lookup, fewer than ~20 items with 3+ attributes, mixed units in one row, reading across attributes, small screens. Chart: distribution shape, trend, spatial pattern, "which is biggest". A 500-row time-series table is worse than a line chart. When viewers have different tasks, offer both behind a toggle.

## Layout and formatting

```
toggle bar (chart | table)
chart container  OR  table (sticky header, scrolling body)
status bar (row count, active filters; doubles as live region)
```

- Numbers: `text-align: right; font-variant-numeric: tabular-nums` on `td` and `th`.
- One `d3.format` per column (`",.1f"`), never mixed precision. Units in the header (`GDP ($M)`), not every cell; currency symbols in cells are fine for financial tables.
- Column spec `{ key, label, type, format, visible }`: `type` picks the comparator and alignment.

## Nested join

```js
const rows = d3.select(tbody).selectAll('tr')
  .data(data, d => d.id)          // key: stable rows across sort/filter
  .join('tr');
rows.selectAll('td')
  .data(d => visibleCols().map(c => c.format ? c.format(d[c.key]) : d[c.key]))  // no key: cells match columns by index
  .join('td')
  .text(d => d);
```

Header and body must read the same `visibleCols()` list, or cells shift under the wrong headers after a column is hidden.

## Sorting

- Header content is a `<button>` (focusable, Enter/Space for free). Put `aria-sort` on the active `<th>` only.
- Sort a copy. `Array.prototype.sort` mutates, and the chart reading the same array reorders silently.
- Shift-click adds secondary keys. Show priority badges (1, 2, 3); `aria-sort` stays on the primary.

```js
let sortKeys = [];                                  // [{ key, dir }], primary first
function onHeaderClick(col, event) {
  const prev = sortKeys.find(s => s.key === col.key);
  if (event.shiftKey) prev ? (prev.dir *= -1) : sortKeys.push({ key: col.key, dir: 1 });
  else sortKeys = [{ key: col.key, dir: prev ? -prev.dir : 1 }];
}
const multiSort = keys => (a, b) => {
  for (const { key, dir } of keys) {
    const c = d3.ascending(a[key], b[key]);
    if (c) return c * dir;
  }
  return 0;
};
```

## Filtering

Each filter is a predicate in a Map; a row passes if every predicate does. Announce the count every time, or screen reader users filter blind.

```js
const activeFilters = new Map();
function applyFilters(data, liveRegion) {
  const preds = [...activeFilters.values()];
  const out = preds.length ? data.filter(d => preds.every(f => f(d))) : data;
  liveRegion.textContent = `Showing ${out.length} of ${data.length} rows`;
  return out;
}
const searchPredicate = (q, columns) => d =>
  columns.some(c => String(d[c.key]).toLowerCase().includes(q.toLowerCase()));
```

- Search: debounce input ~150ms; set `'search'` → `searchPredicate`, delete it when empty.
- Category `<select>` from `new Set(values)`; "All" deletes the filter. Range input bounded by `d3.extent`.
- Clear all resets the Map **and** the controls' DOM state.

## Linked highlighting

Shared state (`hoveredId`, `selectedIds`, notify) drives both views; see `linked-views`. Rows: `.classed('hovered', d => d.id === state.hoveredId)`. `row.scrollIntoView({ block: 'nearest' })` on selection only.

## Sticky and frozen

```css
thead th { position: sticky; top: 0; z-index: 1; }
th:first-child, td:first-child { position: sticky; left: 0; z-index: 1; background: var(--bg); }
thead th:first-child { z-index: 2; }
table { border-collapse: separate; border-spacing: 0; }
```

Sticky cells need an opaque background or content shows through. With `border-collapse: collapse`, cell borders scroll away from sticky cells.

## Conditional formatting

- Heatmap cells: text color from background lightness, `d3.lab(bg).l < 55 ? '#fff' : '#000'`.
- Data bars: a `.bar-fill` div at `scaleLinear([0, max], [0, 100])` percent width, value label layered on top.
- Sparklines (~60×16 SVG, see `sparkcharts`) need an `aria-label` with the trend ("Trending up 12%").

## Grouping

`d3.group` → one `<tbody>` per group with a header row holding `<button aria-expanded>` and a `colspan` cell; toggle hides that tbody's data rows. Subtotal rows: `d3.sum` per numeric column, styled bold with a top border.

## Export

Export the current filtered, sorted view.

```js
function exportCSV(data, columns) {
  const esc = v => { const s = String(v ?? ''); return /[,"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const csv = [columns.map(c => esc(c.label)), ...data.map(d => columns.map(c => esc(d[c.key])))]
    .map(r => r.join(',')).join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  Object.assign(document.createElement('a'), { href: url, download: 'data.csv' }).click();
  URL.revokeObjectURL(url);
}
```

Clipboard: same rows tab-separated via `navigator.clipboard.writeText()` (pastes into spreadsheets without an import dialog); announce "Copied N rows".

## Virtual scrolling (10K+ rows)

1. Scroll container with `max-height`, `overflow-y: auto`; a spacer `data.length * rowHeight` tall.
2. On scroll, `start = floor(scrollTop / rowHeight) - buffer`, `end` from `clientHeight`; buffer 5-10 rows.
3. Join the slice keyed by id; offset the tbody with `translateY(start * rowHeight)`.
4. `aria-rowcount` on the table, `aria-rowindex` on each row.
5. Re-render the window after sorting: order changed, scroll position didn't.

Ctrl+F only finds rendered rows, so a visible search box is required. If the data doesn't fit in browser memory, paginate server-side instead.

## Pitfalls

- `role="grid"` on a read-only table: replaces native table navigation with a widget contract you then have to implement. Keep the native `<table>`.
- Roving tabindex that captures Tab: only arrows move within; Tab leaves.
- Exporting the original array instead of the current view.
- Hover triggering `scrollIntoView`.

Sources: Bostock, Sortable Table (Observable); Schwabish, "Ten Guidelines for Better Tables"; WAI-ARIA APG Grid and Sortable Table; Rutter, "Web Typography: Tables".
