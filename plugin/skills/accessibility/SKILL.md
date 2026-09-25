---
name: accessibility
description: "Make D3 charts usable without sight or a mouse: screen reader summaries, ARIA roles (img, listbox, grid, tree, application), keyboard navigation, roving tabindex, focus rings drawn on canvas, hidden DOM mirror, live region announcements, reduced motion, prefers-contrast, forced-colors, chart/table toggle, accessible data tables (sortable, filterable, sticky header, virtual scrolling, CSV export), linked highlighting between table rows and chart marks."
---

# Accessibility

A chart is one encoding of a dataset. People who can't see it, or can't point at it, need a different encoding of the same data, not a description of the pixels. The judgment here is which alternative the chart owes: a sentence, a table, or navigation point by point. Then build that one well.

SVG under ~500 marks gives you DOM nodes to label and make focusable (`tabindex`), and it responds to forced colors. Canvas gives you none of that, so everything below is on you.

## What a screen-reader user needs

| If the chart... | Provide | Because |
|---|---|---|
| makes one point (static, editorial) | `role="img"` + `aria-label` stating the finding, not the chart type | "Unemployment peaked at 14.7% in April 2020" beats "Line chart of unemployment" |
| is for looking up or comparing values | a real `<table>` behind a chart/table toggle | tables are the native, fully supported structure: headers, row/column navigation, Ctrl+F |
| is explored (hover, select, drill) | keyboard navigation + live region, and the table too | exploration is the task; a summary can't substitute |
| updates live | a polite live region announcing a summary ("Data updated, 42 items") | per-point announcements are noise |

Offer the table even when you build navigation. Sighted keyboard users, low-vision users, and anyone wanting exact numbers use it too.

## ARIA roles that work

| Viz | Role on the focusable container | Notes |
|---|---|---|
| Static chart | `img` + `aria-label` | children become presentational, so nothing inside can be interactive |
| Bar chart, ranked list | `listbox`, items `option` | linear order, Up/Down (or Left/Right) |
| Heatmap, matrix | `grid` | row/column movement |
| Tree, hierarchy | `tree`, items `treeitem` with `aria-expanded`, `aria-level` | screen readers announce APG tree keys, so implement those keys |
| Scatter, force, map | `application` | disables browse mode so arrow keys reach you. Last resort: users lose their normal reading commands, and VoiceOver treats it differently |
| Data table | native `<table>`, no role | `role="grid"` only if individual cells are interactive |

- `role="graphics-document"` / `graphics-*` (ARIA Graphics module) have inconsistent screen reader support. `role="img"` with `aria-label` is the reliable static option.
- An ARIA role promises a keyboard contract. `role="tree"` with non-tree keys is worse than no role.
- `aria-description` gives per-item detail without a separate `aria-describedby` element.

## Keyboard model

- **One tab stop** for the chart. Tab enters, Tab leaves. Never trap Tab. Only arrow keys, Home/End, Enter/Space, Escape are handled; call `e.preventDefault()` for exactly those, or arrows scroll the page.
- **Roving focus**: either move real focus among DOM elements (`tabindex="0"` on the current one, `-1` on the rest), or keep focus on the container and point `aria-activedescendant` at the current item's id. Canvas uses the second.
- **Arrows follow the data's natural order**, not screen geometry, unless the data is spatial:

| Data shape | Arrows mean |
|---|---|
| ordered series (bars, time) | previous / next in data order |
| matrix | row/column; Home/End = row start/end; Ctrl+Home/End = first/last cell |
| hierarchy (APG tree) | Up/Down = previous/next visible node; Right = expand, then first child; Left = collapse, then parent |
| 2-D scatter / network | nearest neighbor inside a 90° cone in the arrow's direction (quadtree) |

- Shared keys: Home = first, End = last, Enter/Space = select, Escape = clear selection (and blur, for dense canvases).
- On blur, keep `focusedId` and hide the ring, so Tab-back resumes where the user left off. Clear it only for standalone charts where re-entry should start fresh.
- Click must also set focus: `pointerdown` → `canvas.focus()`, hit-test, set `focusedId`, announce, render.
- Offer a skip link past dense visualizations.

## Focus ring on canvas

- Draw it **last** in the render loop, or data paints over it.
- Two-tone so it shows on any background: blue stroke (~2.5px, dashed) over a white halo (shadow or a wider white stroke under it). Pad ~4px outside the shape.
- Match the mark's shape: circle ring, padded rect, padded annular sector for arcs, fixed 8px circle for tiny points.
- Animated dash offset only when `prefers-reduced-motion` isn't set.

## Live regions

- Create the region (`role="status"` or `aria-live="polite"`, visually hidden) **at page load**. Regions inserted along with their text are often not announced.
- Announce identity, value, context: "California, value 39.5M, selected". Build it from a field config (key, label, format) so every mark reads the same way.
- Debounce 100-200ms: held arrow keys otherwise queue dozens of announcements. Skip the debounce for trees with short labels.

| Event | Say |
|---|---|
| focus moves | identity + value + context |
| Enter / Escape | "selected" / "Selection cleared" |
| expand / collapse | node + state + child count |
| filter, sort, data update | "Showing 12 of 50 rows", "Sorted by GDP, descending" |
| layout switch | "Switched to table view" |

## System preferences

Canvas ignores CSS, so query `matchMedia` at init and re-render on `change`.

| Query | Do |
|---|---|
| `prefers-reduced-motion: reduce` | skip transitions, jump to final state, stop animated focus rings |
| `prefers-contrast: more` | +1px strokes, higher-contrast palette, +2px text |
| `forced-colors: active` | canvas is a bitmap and ignores forced colors. A visually hidden mirror doesn't help sighted high-contrast users. Switch to (or offer) the visible table |

Contrast ratios and pattern fills for non-color encoding live in `legibility`, not here.

## Chart ↔ table toggle

- Sibling containers, one visible. `display: none` already hides from assistive tech; no extra `aria-hidden` needed.
- Toggle is a `<button aria-pressed>`. Announce the switch.
- Both views bind the **same data and the same state** (filter, sort, `hoveredId`, `selectedIds`). Filtering the table filters the chart.
- Linked highlighting: hover in either view sets `hoveredId`; both re-render. `scrollIntoView({ block: "nearest" })` on the row only on **selection**, never hover (it fights the user's scroll).
- Sort a copy (`[...data].sort()`): in-place sort silently reorders the chart too.

## Table decisions

| Situation | Do |
|---|---|
| exact lookup, <~20 items with 3+ attributes, mixed units, reading across rows | table wins; chart optional |
| task is shape, trend, or spatial pattern | chart wins; table is the alternative, not the lead |
| sortable columns | `<button>` inside `<th>`; `aria-sort` on the active header only |
| numbers | right-aligned, `font-variant-numeric: tabular-nums`, one `d3.format` per column, units in the header |
| 10K+ rows | virtual scroll with `aria-rowcount` / `aria-rowindex`, plus a visible search box (Ctrl+F can't see unrendered rows) |
| export | the filtered, sorted view, not the raw array |

## Traps

- Row join without a key (`d => d.id`): sort/filter reuses rows by index and flashes wrong values. Cell join **with** a key: two cells formatting to the same string collide.
- Sticky header with `border-collapse: collapse`: the borders don't stick. Use `separate` with `border-spacing: 0`. Sticky cells need an opaque background.
- DOM mirror built once, never updated after brush/filter: screen readers browse data that isn't shown.
- Heatmap cells with fixed text color: pick black/white by background lightness (`d3.lab(c).l < 55 ? "#fff" : "#000"`).
- Sparkline or icon in a cell without `aria-label` ("Trending up 12%"): screen readers can't read a path.
- Keyboard-only testing. Test with VoiceOver and NVDA; `application` and `grid` behave differently in each.

## References

- `references/canvas-accessibility.md`: when to use a DOM mirror, APG tree and grid key handlers, quadtree cone navigation, focus ring drawing, announce builder, mirror as canvas fallback content.
- `references/data-table.md`: nested join, multi-sort, filter pipeline and search, column show/hide, frozen column, conditional formatting, grouping, CSV/clipboard export, virtual scrolling.
- `examples/canvas-accessibility.html`: keyboard-navigable canvas scatter with live region and table fallback.
- `examples/data-table.html`: sortable, filterable table with chart toggle and linked highlighting. Tested by `tests/test.config.json`.
