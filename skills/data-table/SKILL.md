---
name: data-table
description: "Build accessible data tables as companions or alternatives to D3.js visualizations. Use this skill when the user needs a table alternative to a chart, sortable/filterable data tables, chart↔table toggle, linked highlighting between table rows and chart elements, virtual scrolling for large datasets, column management, keyboard navigation, conditional formatting, grouping/subtotals, CSV export, or any pattern where tabular data complements or replaces a visualization."
---

# Data Tables for D3 Visualizations

Charts show patterns; tables show values. When the viewer's task is looking up a specific number, comparing exact figures across rows, or exporting data, a table outperforms any chart. Build tables as first-class views alongside D3 visualizations, not as accessibility afterthoughts.

Related: `linked-views` · `brushing` · `canvas-accessibility` · `color` · `responsive` · `sparkcharts`

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

## Multi-Sort

Shift-click a header to add secondary sort keys. Track sort state as an ordered array:

```js
let sortKeys = []; // [{key, dir}] — first entry is primary

function onHeaderClick(col, event) {
  if (event.shiftKey) {
    const idx = sortKeys.findIndex(s => s.key === col.key);
    if (idx >= 0) sortKeys[idx].dir *= -1;      // toggle direction
    else sortKeys.push({ key: col.key, dir: 1 }); // add secondary
  } else {
    const prev = sortKeys.find(s => s.key === col.key);
    sortKeys = [{ key: col.key, dir: prev ? prev.dir * -1 : 1 }];
  }
  updateAriaSort();
  renderTable(applyFilters(data));
}
```

Chain comparators — fall through to the next key when values are equal:

```js
function multiComparator(sortKeys) {
  return (a, b) => {
    for (const { key, dir } of sortKeys) {
      const cmp = d3.ascending(a[key], b[key]);
      if (cmp !== 0) return cmp * dir;
    }
    return 0;
  };
}

// Usage: [...filtered].sort(multiComparator(sortKeys))
```

Show sort priority in the header — a small numeral badge (1, 2, 3) next to the arrow icon for multi-sort columns. Set `aria-sort` only on the primary sort column; secondary sort columns get a visual indicator but no `aria-sort` (the spec only supports one sorted column).

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

### Filter pipeline

Chain independent filters through a single pipeline. Each filter is a predicate function; a row passes only if every predicate returns true:

```js
const activeFilters = new Map(); // key → predicate fn

function applyFilters(data) {
  const preds = [...activeFilters.values()];
  const filtered = preds.length ? data.filter(d => preds.every(f => f(d))) : data;
  announceCount(filtered.length, data.length);
  return filtered;
}

function announceCount(shown, total) {
  liveRegion.textContent = `Showing ${shown} of ${total} rows`;
}
```

`liveRegion` is a `div[aria-live="polite"]` — without it, screen reader users filter blindly and don't know if anything matched.

### Global text search

Filters across all columns. Debounce the input to avoid re-rendering on every keystroke:

```js
const searchInput = d3.select('#search').on('input', debounce(e => {
  const q = e.target.value.toLowerCase();
  if (q) {
    activeFilters.set('search', d =>
      columns.some(col => String(d[col.key]).toLowerCase().includes(q))
    );
  } else {
    activeFilters.delete('search');
  }
  renderTable(applyFilters(data));
}, 150));

function debounce(fn, ms) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
```

### Categorical dropdown filter

Build options from distinct values in the column:

```js
function addCategoryFilter(col, container) {
  const values = [...new Set(data.map(d => d[col.key]))].sort();
  const select = container.append('select')
    .attr('aria-label', `Filter by ${col.label}`)
    .on('change', e => {
      const v = e.target.value;
      if (v === '') activeFilters.delete(col.key);
      else activeFilters.set(col.key, d => d[col.key] === v);
      renderTable(applyFilters(data));
    });
  select.append('option').attr('value', '').text(`All ${col.label}`);
  select.selectAll('option.v').data(values).join('option').attr('class', 'v')
    .attr('value', d => d).text(d => d);
}
```

### Range slider filter

For numeric columns, a two-handle range input. Use two `<input type="range">` layered with CSS, or a single native `<input>` for a minimum threshold:

```js
function addRangeFilter(col, container) {
  const extent = d3.extent(data, d => d[col.key]);
  const slider = container.append('input')
    .attr('type', 'range')
    .attr('min', extent[0]).attr('max', extent[1]).attr('value', extent[0])
    .attr('step', (extent[1] - extent[0]) / 100)
    .attr('aria-label', `Minimum ${col.label}`)
    .on('input', e => {
      const min = +e.target.value;
      activeFilters.set(col.key, d => d[col.key] >= min);
      renderTable(applyFilters(data));
    });
}
```

### Clearing filters

A "Clear all" button resets the pipeline. Update every filter control's DOM state too — a common miss:

```js
clearBtn.on('click', () => {
  activeFilters.clear();
  d3.selectAll('select.filter').property('value', '');
  d3.select('#search').property('value', '');
  renderTable(applyFilters(data));
});
```

## Column Management

### Show/hide columns

A checkbox dropdown lets the viewer control which columns are visible. Store visibility in the column spec:

```js
columns.forEach(c => c.visible = true); // default all visible

function buildColumnMenu(container) {
  const menu = container.append('div').attr('class', 'col-menu');
  menu.selectAll('label').data(columns).join('label')
    .html(col => `<input type="checkbox" checked> ${col.label}`)
    .select('input')
      .property('checked', col => col.visible)
      .on('change', (e, col) => {
        col.visible = e.target.checked;
        renderTable(applyFilters(data));
      });
}

// Filter columns in the render path
const visibleCols = () => columns.filter(c => c.visible);
```

Thread `visibleCols()` through both the header and body join — the cell data mapper must reference the same column list used to render `<th>` elements.

### Frozen first column

Pin the row label column so it stays visible during horizontal scroll. CSS-only — no JS needed:

```css
/* First column header and cells freeze on horizontal scroll */
th:first-child, td:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--bg, white); /* must be opaque or content bleeds through */
}
th:first-child { z-index: 2; } /* above both frozen cells and scrolling headers */
```

**Gotcha**: the frozen column needs an opaque background. If you use a transparent or semi-transparent background, scrolled content shows through.

## Keyboard Navigation

### Roving tabindex on grid cells

The WAI-ARIA grid pattern: only one cell in the table is in the tab order at a time. Arrow keys move focus between cells. This means the user can Tab into the table, arrow around, then Tab out — instead of tabbing through every cell.

```js
function initGridNavigation(table) {
  let focusRow = 0, focusCol = 0;
  const getCell = (r, c) => table.querySelector(
    `tr:nth-child(${r + 1}) > :nth-child(${c + 1})`
  );

  // Set initial roving tabindex
  table.querySelectorAll('td, th').forEach(el => el.setAttribute('tabindex', '-1'));
  const first = getCell(0, 0);
  if (first) first.setAttribute('tabindex', '0');

  table.addEventListener('keydown', e => {
    const rows = table.querySelectorAll('tr');
    const maxRow = rows.length - 1;
    const maxCol = rows[0]?.children.length - 1 ?? 0;
    let nr = focusRow, nc = focusCol;

    switch (e.key) {
      case 'ArrowRight': nc = Math.min(nc + 1, maxCol); break;
      case 'ArrowLeft':  nc = Math.max(nc - 1, 0); break;
      case 'ArrowDown':  nr = Math.min(nr + 1, maxRow); break;
      case 'ArrowUp':    nr = Math.max(nr - 1, 0); break;
      case 'Home': nc = 0; if (e.ctrlKey) nr = 0; break;
      case 'End':  nc = maxCol; if (e.ctrlKey) nr = maxRow; break;
      default: return; // don't preventDefault for other keys
    }
    e.preventDefault();
    const prev = getCell(focusRow, focusCol);
    const next = getCell(nr, nc);
    if (prev) prev.setAttribute('tabindex', '-1');
    if (next) { next.setAttribute('tabindex', '0'); next.focus(); }
    focusRow = nr; focusCol = nc;
  });
}
```

Set `role="grid"` on the table and `role="row"` / `role="gridcell"` on rows and cells so screen readers enter grid navigation mode.

### Live regions for state changes

When sort or filter changes, screen reader users need an announcement. A single shared live region handles all updates:

```js
const liveRegion = d3.select('body').append('div')
  .attr('aria-live', 'polite')
  .attr('class', 'sr-only'); // visually hidden

// After sort:
liveRegion.text(`Sorted by ${col.label}, ${dir === 1 ? 'ascending' : 'descending'}`);

// After filter — already handled by announceCount() in the filter pipeline
```

```css
.sr-only {
  position: absolute; width: 1px; height: 1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap;
}
```

### Header activation

Make sortable headers operable by keyboard — `tabindex="0"` plus Enter/Space handling:

```js
d3.selectAll('th[data-sortable]')
  .attr('tabindex', '0')
  .attr('role', 'columnheader')
  .on('keydown', (e, col) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onHeaderClick(col, e);
    }
  });
```

## Conditional Formatting

### Heatmap cells

Color-code numeric cells by value. Use a sequential scale and ensure WCAG contrast for the text:

```js
const color = d3.scaleSequential(d3.interpolateBlues)
  .domain(d3.extent(data, d => d.value));

// In the cell join:
rows.selectAll('td.heatmap')
  .style('background-color', d => color(d))
  .style('color', d => d3.lab(color(d)).l < 55 ? '#fff' : '#000');
```

The luminance check (`d3.lab().l < 55`) flips text to white on dark backgrounds. Without it, dark blue cells with black text fail WCAG contrast.

### Data bars in cells

A percentage-width `<div>` inside the cell creates an in-cell bar chart:

```js
const barScale = d3.scaleLinear()
  .domain([0, d3.max(data, d => d.value)])
  .range([0, 100]);

rows.selectAll('td.bar-cell').each(function(d) {
  const cell = d3.select(this);
  cell.html(''); // clear previous
  cell.append('div').attr('class', 'bar-bg')
    .append('div').attr('class', 'bar-fill')
      .style('width', `${barScale(d)}%`);
  cell.append('span').attr('class', 'bar-label').text(d3.format(',')(d));
});
```

```css
td.bar-cell { position: relative; padding: 0; }
.bar-bg { position: absolute; inset: 2px; background: #f0f0f0; }
.bar-fill { height: 100%; background: steelblue; }
.bar-label { position: relative; padding: 4px 8px; } /* sits above the bar */
```

### Sparkline cells

Embed tiny line charts in cells using inline SVG. See the `sparkcharts` skill for the full pattern — here's the integration point:

```js
rows.selectAll('td.spark').each(function(d) {
  const cell = d3.select(this);
  cell.html('');
  const w = 60, h = 16;
  const svg = cell.append('svg').attr('width', w).attr('height', h);
  const x = d3.scaleLinear().domain([0, d.series.length - 1]).range([0, w]);
  const y = d3.scaleLinear().domain(d3.extent(d.series)).range([h - 1, 1]);
  svg.append('path')
    .attr('d', d3.line().x((v,i) => x(i)).y(v => y(v))(d.series))
    .attr('fill', 'none').attr('stroke', 'steelblue').attr('stroke-width', 1.5);
});
```

Provide an `aria-label` on each sparkline SVG with the trend summary (e.g., "Trending up 12%") — screen readers can't interpret the path.

## Grouping and Subtotals

### Collapsible row groups

Use `d3.group` to partition data, then render group headers with expand/collapse:

```js
const grouped = d3.group(data, d => d.continent);

function renderGrouped(container, grouped) {
  for (const [groupName, rows] of grouped) {
    const section = container.append('tbody').attr('class', 'group');
    // Group header row
    const header = section.append('tr').attr('class', 'group-header')
      .attr('aria-expanded', 'true');
    header.append('td')
      .attr('colspan', visibleCols().length)
      .html(`<button aria-expanded="true">${groupName} (${rows.length})</button>`);

    // Data rows
    const dataRows = section.selectAll('tr.data-row')
      .data(rows, d => d.id).join('tr').attr('class', 'data-row');
    dataRows.selectAll('td')
      .data(d => visibleCols().map(col => col.format ? col.format(d[col.key]) : d[col.key]))
      .join('td').text(d => d);

    // Toggle visibility
    header.select('button').on('click', function() {
      const expanded = this.getAttribute('aria-expanded') === 'true';
      this.setAttribute('aria-expanded', String(!expanded));
      section.selectAll('tr.data-row').style('display', expanded ? 'none' : null);
    });
  }
}
```

### Aggregate rows

Add subtotal rows at the bottom of each group. Compute aggregates per group:

```js
function groupSubtotals(grouped, numericCols) {
  const subtotals = new Map();
  for (const [name, rows] of grouped) {
    const agg = {};
    for (const col of numericCols) {
      agg[col.key] = d3.sum(rows, d => d[col.key]);
    }
    agg._isSubtotal = true;
    subtotals.set(name, agg);
  }
  return subtotals;
}
```

Style subtotal rows distinctly — bold text, top border, no hover highlight. Mark them with `aria-label="Subtotal"` so screen readers distinguish them from data rows.

## Export

### CSV download from current view

Export the filtered, sorted data — not the original array. Build CSV from the visible columns:

```js
function exportCSV(data, columns) {
  const header = columns.map(c => c.label).join(',');
  const rows = data.map(d =>
    columns.map(c => {
      const v = String(d[c.key]);
      return v.includes(',') || v.includes('"') || v.includes('\n')
        ? `"${v.replace(/"/g, '""')}"` : v;
    }).join(',')
  );
  const csv = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'data.csv';
  a.click();
  URL.revokeObjectURL(url);
}
```

Bind to a button: `d3.select('#export').on('click', () => exportCSV(currentData, visibleCols()))`. Use `currentData` (the filtered/sorted array), not the raw `data`.

### Clipboard copy

Copy the current view as tab-separated text for pasting into spreadsheets:

```js
async function copyToClipboard(data, columns) {
  const header = columns.map(c => c.label).join('\t');
  const rows = data.map(d => columns.map(c => d[c.key]).join('\t'));
  const tsv = [header, ...rows].join('\n');
  await navigator.clipboard.writeText(tsv);
  liveRegion.text(`Copied ${data.length} rows to clipboard`);
}
```

Tab-separated is better than CSV for clipboard — Excel and Google Sheets parse tabs on paste without an import dialog.

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
8. **Exporting raw data instead of current view** — the export button must use the filtered/sorted array. Exporting the original `data` confuses users who applied filters expecting to download only what they see.
9. **Heatmap cells without contrast check** — dark backgrounds with dark text fail WCAG. Always check luminance and flip text color.
10. **Frozen column transparent background** — content scrolls behind the frozen column if its background isn't opaque. Set an explicit `background` on sticky cells.
11. **Tab-trapping in grid navigation** — the roving tabindex pattern must allow Tab to leave the table. Don't intercept Tab/Shift+Tab in the keydown handler — only handle arrow keys.

## References

- [Sortable Table — D3 Observable](https://observablehq.com/@d3/sortable-table) — Bostock's canonical sortable table
- [Ten Guidelines for Better Tables](https://www.cambridge.org/core/journals/journal-of-benefit-cost-analysis/article/abs/ten-guidelines-for-better-tables/74C6FD9FEB12038A52A95B9FBCA05A12) — Schwabish on alignment, units, and whitespace
- [WAI-ARIA Grid Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) — interactive tables with cell-level keyboard navigation
- [Web Typography: Tables](https://alistapart.com/article/web-typography-tables/) — Richard Rutter on tabular-nums and alignment
