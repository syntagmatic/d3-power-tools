---
name: data-table
description: "Build accessible data tables as fallback views for D3.js visualizations. Use this skill when the user needs a table alternative to a chart, sortable/filterable data tables, chart↔table toggle, linked highlighting between table rows and chart elements, virtual scrolling for large datasets, CSV export, sticky headers, or any pattern where tabular data complements or replaces a visualization."
---

# Fallback Data Table for D3 Visualizations

Build data tables that serve as accessible alternatives to D3 visualizations — sortable, filterable, linkable to charts, and scalable to large datasets. Tables aren't a lesser view; for many tasks (lookup, comparison, export) they're superior to charts.

## When to Use

- **Accessibility** — screen reader users may prefer structured tabular data over spatial visualization
- **Data lookup** — users need specific values, not patterns
- **Export** — users want to download or copy the data
- **Mobile** — complex charts degrade on small screens; tables scroll naturally
- **Complementary view** — table and chart side-by-side, linked by hover/selection

## Architecture

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

`type` drives sort comparators and text alignment (right-align numbers, use `font-variant-numeric: tabular-nums`). `format` is optional.

## D3 Nested Join Pattern

The table body uses a two-level join — rows keyed by `d.id`, cells by column index:

```js
const rows = d3.select(tbody).selectAll('tr')
  .data(data, d => d.id)
  .join('tr');

rows.selectAll('td')
  .data(d => columns.map(col => col.format ? col.format(d[col.key]) : d[col.key]))
  .join('td')
    .text(d => d);
```

The **outer join uses a key function** (`d => d.id`) for stable identity during filter/sort. The **inner cell join must NOT have a key function** — cells always map 1:1 to columns by index. Adding a key to the cell join causes bugs when formatted values collide.

## Sortable Columns

Click header → sort ascending, click again → descending. Key details:

- Use `d3.ascending`/`d3.descending` as comparators
- Set `aria-sort` attribute on the active `<th>` (`"ascending"`, `"descending"`, or `"none"` on inactive headers)
- Make headers `tabindex="0"` and handle Enter/Space for keyboard activation
- Show indicators via CSS pseudo-elements: `th.sort-asc::after { content: ' ▲'; }`

**Gotcha**: `Array.sort()` mutates in place. If the chart reads the same array, sort order will change there too. Either sort a copy (`[...data].sort(...)`) or accept shared sort order.

## Linked Highlighting

Hover/select in chart → highlight table row, and vice versa. Use a shared state object:

```js
const state = {
  hoveredId: null,
  selectedIds: new Set(),
  listeners: [],
  onHover(id) { this.hoveredId = id; this.notify(); },
  onSelect(id) {
    this.selectedIds.has(id) ? this.selectedIds.delete(id) : this.selectedIds.add(id);
    this.notify();
  },
  onChange(fn) { this.listeners.push(fn); },
  notify() { for (const fn of this.listeners) fn(); }
};
```

Both views wire events to `state.onHover()`/`state.onSelect()` and subscribe via `state.onChange()` to update their rendering.

Table side: `.classed('hovered', d => d.id === state.hoveredId)` on `<tr>` elements.

Chart side: re-render with highlight/fade based on state.

**Scroll-to-row**: when the chart highlights a point, call `row.scrollIntoView({ block: 'nearest' })` on the corresponding `<tr>`. Only do this on click/selection — doing it on hover fights the user's own scrolling.

## Filtering

Global text search: filter across all columns with `String(val).toLowerCase().includes(query)`. Show a status `div[aria-live="polite"]` with "Showing N of M rows". For per-column filters, add a second `<tr>` in `<thead>` with `<input>` or `<select>` per column.

## Virtual Scrolling (10K+ rows)

Render only visible rows + buffer. Key pattern:

1. Wrap table in a container with `max-height` and `overflow-y: auto`
2. Use a spacer element (`height: data.length * rowHeight`) to size the scrollbar
3. On scroll, compute `startIdx`/`endIdx` from `scrollTop` and `clientHeight`
4. Slice data, join visible rows, offset `<tbody>` with `translateY(startIdx * rowHeight)`
5. Set `aria-rowcount` on `<table>` and `aria-rowindex` on each visible `<tr>`
6. Debounced live region announces scroll position for screen readers

**Gotcha**: after sorting, re-call `renderVisible()` — data order changed but scroll position didn't.

## Sticky Headers

Pure CSS — no JS needed:

```css
.table-container { max-height: 500px; overflow-y: auto; }
thead th { position: sticky; top: 0; background: #fff; z-index: 1; }
```

**Gotcha**: `position: sticky` breaks with `border-collapse: collapse` in some browsers. Use `border-collapse: separate; border-spacing: 0;` instead, with `border-bottom` on cells.

## CSV Export

Create a Blob from column headers + formatted rows, generate an Object URL, trigger download via a temporary `<a>` element. Quote strings containing commas/quotes with RFC 4180 escaping (`"` → `""`).

## Responsive Patterns

- **Horizontal scroll**: wrap in `overflow-x: auto` container. Freeze first column with `position: sticky; left: 0`.
- **Column priority**: tag columns with `data-priority` attributes, hide low-priority columns via `@media` queries.

## Common Pitfalls

1. **Sorting mutates shared array** — sort a copy if chart shouldn't reorder.
2. **No key on cell join** — inner `selectAll('td').data(...)` uses index matching. Adding a key causes bugs when formatted values collide.
3. **Format functions must be pure** — called every re-render. No side effects.
4. **Virtual scroll + sort** — must re-render visible rows after sorting.
5. **`scrollIntoView` on hover** — debounce or restrict to click/selection only.
6. **Missing key on row join** — `d => d.id` on the outer row join is critical for stable DOM during filter/sort.
7. **10K+ rows without virtualization** — 50K+ DOM nodes will lag. Virtualize or paginate above ~5K rows.
8. **Sticky + border-collapse** — use `border-collapse: separate; border-spacing: 0` instead.

## References

- [Sortable Table — D3 Observable](https://observablehq.com/@d3/sortable-table) — Mike Bostock's canonical sortable table in D3
- [WAI-ARIA Table Role](https://www.w3.org/TR/wai-aria-1.2/#table) — ARIA semantics for data tables
- [WAI-ARIA Grid Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) — interactive tables with cell-level keyboard navigation
- [Show the Data](https://apreshill.github.io/data-vis-labs-2018/slides/06-slides_tables.html) — Alison Hill on when tables beat charts
- [Clustergrammer](https://maayanlab.github.io/clustergrammer/) — Avi Ma'ayan Lab's interactive heatmap/table hybrid for exploring high-dimensional data
- [Ten Guidelines for Better Tables](https://www.darkhorseanalytics.com/blog/clear-off-the-table) — Jon Schwabish's widely cited design guidelines for data tables
