---
name: data-table
description: "Build accessible data tables as companions or alternatives to D3.js visualizations. Use this skill when the user needs a table alternative to a chart, sortable/filterable data tables, chart↔table toggle, linked highlighting between table rows and chart elements, virtual scrolling for large datasets, or any pattern where tabular data complements or replaces a visualization."
---

# Data Tables for D3 Visualizations

Charts show patterns; tables show values. When the viewer's task is looking up a specific number, comparing exact figures across rows, or exporting data, a table outperforms any chart. Build tables as first-class views alongside D3 visualizations, not as accessibility afterthoughts.

Related: `linked-views` · `brushing` · `canvas-accessibility` · `color` · `responsive`

## Table vs. Chart: When the Table Wins

Use a table — not a chart — when:

- **Exact value lookup** — the viewer needs specific numbers (revenue for Q3, a patient's lab result), not trends. Charts encode values as position/length, which the eye decodes at ~10% precision; tables give the exact figure.
- **Small n** — fewer than ~20 data points with 3+ attributes. A chart of 8 rows wastes space; a table is denser and scannable.
- **Mixed units** — columns show dollars, percentages, counts, and dates side-by-side. No single y-axis can handle that; a table handles it naturally.
- **Comparison across attributes** — the viewer reads across a row to compare one entity's properties. Charts require multiple encodings or facets for this.
- **Mobile** — complex charts degrade on small screens; tables scroll naturally and work at any width with horizontal scroll.

Offer **both views** (toggle or side-by-side) when different viewers need different tasks — analysts want the numbers, executives want the shape.

## When Not to Use This

Don't build a table when the viewer needs to see **distribution shape**, **trends over time**, or **spatial patterns** — those tasks require visual encoding. A 500-row table of time-series data is less useful than a line chart. If the dataset has one or two numeric columns and the task is "which is biggest?", a bar chart communicates faster than scanning a column of numbers.

## Number Formatting and Alignment

Poor alignment is the most common table design failure. Numbers that aren't right-aligned are impossible to compare by scanning.

```css
/* Right-align numeric columns; tabular-nums makes digits equal-width so decimals line up */
td.num { text-align: right; font-variant-numeric: tabular-nums; }
/* Align headers with their data */
th.num { text-align: right; }
```

Formatting rules driven by `d3.format`:
- **Consistent precision** — all values in a column get the same decimal places. `d3.format(',.1f')` not a mix of `3.1` and `3.14159`.
- **Units in the header, not every cell** — write `GDP ($M)` in `<th>`, format cells as `1,234` not `$1,234M` repeated 50 times. Exception: currency symbols aid scanning in financial tables.
- **Group separators for large numbers** — `d3.format(',')` turns `1234567` into `1,234,567`. Without separators, the eye can't distinguish thousands from millions at a glance.

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

Table and chart are sibling containers. Toggle hides one and shows the other via `display`/`aria-hidden`. Both bind the same data array so filter/selection state is shared. Use `aria-pressed` on the toggle button so screen readers announce the active view.

## Column Specification

```js
const columns = [
  { key: 'name', label: 'Name', type: 'string' },
  { key: 'population', label: 'Population', type: 'number', format: d3.format(',') },
  { key: 'gdp', label: 'GDP per Capita', type: 'number', format: d3.format('$,.0f') },
  { key: 'continent', label: 'Continent', type: 'string' }
];
```

`type` drives two things: sort comparator (lexicographic vs. numeric) and cell alignment (right for numbers). Keep format functions pure — they're called every re-render.

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

The **outer join uses a key function** (`d => d.id`) for stable DOM identity during filter/sort — without it, D3 reuses `<tr>` elements by index, causing flash-of-wrong-content during transitions. The **inner cell join must NOT have a key function** — cells always map 1:1 to columns by index. Adding a key to the cell join causes bugs when formatted values collide (e.g., two cells both showing "1,234").

## Sortable Columns

Click header to sort ascending, click again for descending. Key details:

- Use `d3.ascending`/`d3.descending` as comparators
- Set `aria-sort` on the active `<th>` (`"ascending"`, `"descending"`, `"none"` on others) — screen readers announce sort state
- Make headers `tabindex="0"`, handle Enter/Space — keyboard users can't click
- **Sort a copy**: `[...data].sort(...)`. `Array.sort()` mutates in place — if the chart reads the same array, its order silently changes too.

## Linked Highlighting

Hover/select in chart highlights the table row, and vice versa. Use a shared state object:

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

Table side: `.classed('hovered', d => d.id === state.hoveredId)` on `<tr>` elements.

**Scroll-to-row**: call `row.scrollIntoView({ block: 'nearest' })` on selection only — doing it on hover fights the user's own scrolling and creates a jarring experience.

## Filtering

Global text search filters across all columns with `String(val).toLowerCase().includes(query)`. Announce results via `div[aria-live="polite"]` showing "Showing N of M rows" — without this, screen reader users filter blindly and don't know if anything matched.

## Virtual Scrolling (10K+ rows)

Without virtualization, 50K+ DOM nodes cause visible scroll lag. Render only visible rows:

1. Container with `max-height` and `overflow-y: auto`
2. Spacer element (`height: data.length * rowHeight`) to size the scrollbar correctly
3. On scroll, compute `startIdx`/`endIdx` from `scrollTop` and `clientHeight`
4. Add a buffer (5-10 rows above and below viewport) to prevent white flash during fast scrolling
5. Slice data, join visible rows, offset `<tbody>` with `translateY(startIdx * rowHeight)`
6. Set `aria-rowcount` on `<table>` and `aria-rowindex` on each visible `<tr>` — screen readers need the logical row position, not the DOM position

This is framework-agnostic — no React/TanStack needed. D3's data join handles the row recycling: `tbody.selectAll('tr').data(slice, d => d.id).join('tr')` reuses existing `<tr>` elements when the slice shifts by a few rows during scrolling.

**Gotcha**: after sorting, re-call `renderVisible()`. Data order changed but scroll position didn't — the user sees stale rows until the next scroll event.

**Ctrl+F is broken.** Virtual scrolling removes off-screen rows from the DOM, so the browser's native find (Ctrl+F) can't search them. Compensate with a visible search input that filters the data array — the same filtering pattern described above. Users expect search to work; a table that swallows Ctrl+F with no alternative is a support ticket.

### When to paginate instead

Virtual scrolling suits exploration — the user scrolls freely through sorted/filtered data. Server-side pagination suits datasets that exceed browser memory: request only the visible page from the server, fetch the next page on demand. The tradeoff: pagination loses scroll momentum and makes "scan all rows" impossible, but it works at any scale. If the full dataset fits in memory (<100K rows of simple objects), virtual scrolling is simpler and feels faster.

## Observable Plot Note

Observable Plot's `Plot.table()` (as of March 2026) is not a first-class mark — it produces an HTML table outside the Plot SVG. For basic sortable tables from tidy data, it's faster than hand-rolling D3 joins. Reach for D3 when you need linked highlighting, virtual scrolling, or chart↔table toggle — Plot's table has no interaction hooks.

## Common Pitfalls

1. **No key on row join** — `d => d.id` on the outer join is critical. Without it, sort/filter causes DOM reuse by index and rows show wrong data momentarily.
2. **Key on cell join** — inner `selectAll('td').data(...)` must use index matching. A key function causes collisions when two cells format to the same string.
3. **Left-aligned numbers** — numbers without `text-align: right` and `tabular-nums` are unreadable for comparison. The eye needs the ones/tens/hundreds columns to line up vertically.
4. **Inconsistent decimal places** — mixing `3.1` and `3.14` in one column makes scanning impossible. Set one `d3.format` per column.
5. **`scrollIntoView` on hover** — restrict to click/selection. On hover it fights the user's scrolling.
6. **Sticky + border-collapse** — `position: sticky` breaks with `border-collapse: collapse`. Use `border-collapse: separate; border-spacing: 0` with `border-bottom` on cells.
7. **Missing `aria-live` on filter results** — screen reader users type a filter query and hear nothing. The polite live region must announce the count.

## References

- [Sortable Table — D3 Observable](https://observablehq.com/@d3/sortable-table) — Bostock's canonical sortable table
- [Ten Guidelines for Better Tables](https://www.cambridge.org/core/journals/journal-of-benefit-cost-analysis/article/abs/ten-guidelines-for-better-tables/74C6FD9FEB12038A52A95B9FBCA05A12) — Schwabish on alignment, units, and whitespace
- [WAI-ARIA Grid Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) — interactive tables with cell-level keyboard navigation
- [Web Typography: Tables](https://alistapart.com/article/web-typography-tables/) — Richard Rutter on tabular-nums and alignment
