# Small multiples

Absorbed from the v2 `small-multiples` skill. Open when the same chart repeats across categories: facet wrap, facet grid, trellis, synchronized panels.

## When panels beat one chart

Use them when a combined chart makes the viewer decode instead of perceive:

- more than 4-5 overlapping series (lines can't be tracked through crossings)
- the question is shape ("same trend?"), not intersection ("where do they cross?")
- the facets are real groups the viewer already knows (cities, products, cohorts)

Stay with one chart for 2-3 series, exact crossover points, exact value comparison at a point (superimposed lines let the eye measure the gap), or a story about the aggregate.

## How many panels

| Panels | Approach |
|---|---|
| up to ~16-20 | full panels, 4×4 or 4×5 |
| 20-50 | strip each panel to its shape: no axes, gridlines, or labels. The grid is the chart |
| 50-200 | viewers look up rather than compare: add sort and search; Canvas |
| 200+ | scrolling kills comparison: aggregate, filter, or drill down |

Below ~120px wide, line panels lose their shape. If a panel needs axes and annotation to be readable and gets under ~150px, don't facet.

## Ordering

- By a summary statistic (mean, max, slope): the grid becomes a gradient that shows ranking.
- By similarity (correlation, DTW): puts similar shapes together so clusters show.
- By inherent order (months, age bands, geography): respect it.
- Alphabetical: only for lookup with no data-driven logic.

## Scales

| Question | Scales |
|---|---|
| "which is highest?" (magnitude across facets) | shared x and y |
| "does each have a seasonal pattern?" (shape within a facet) | independent y |
| different units or magnitudes over time | shared x, independent y |

- Independent y silently misleads: viewers assume panels are comparable. Label it ("y scales differ"), style the axes distinctly, or add a shared-scale summary panel.
- Compute shared domains from the full dataset **before** the per-facet loop. `d3.extent(facetData, ...)` inside the loop is the common bug that makes scales independent by accident.
- Share the domain, set the range per panel: `x.copy().range([0, plotWidth])`.
- `plotWidth = cellWidth - margin.left - margin.right`; clip marks to the plot area or they bleed into neighbors.

## Grid math

Facet wrap: `cols = Math.ceil(Math.sqrt(n * aspectRatio))`, then `col = i % cols`, `row = Math.floor(i / cols)`, origin `(col * (cellW + gap), row * (cellH + gap))`.

Facet grid: `d3.group(data, rowVar, colVar)`, and look up `nested.get(r)?.get(c) ?? []` for every row×column pair so empty cells still render. Row labels left, column labels top.

Axes: y only on the leftmost column, x only on the bottom row, one shared axis title for the grid.

CSS grid: `repeat(auto-fill, minmax(...))` keeps cell size constant with few facets. `auto-fit` collapses empty tracks and stretches the cells.

## Synchronized interaction

- Crosshair: one overlay rect per panel; on pointermove broadcast the local x to every panel's crosshair and `x.invert(mx)` to the tooltips. This only works because every panel's x has the same range.
- Linked brush and zoom: guard with `if (!event.sourceEvent) return;`, then `.call(brush.move, sel)` (or `zoom.transform`) on the *other* panels. Inside a brush listener `this` is the `<g>`; `event.target` is the brush behavior. Without the guard, programmatic moves re-fire and loop.

## Canvas

| Facets | Rendering | Hit detection |
|---|---|---|
| < 50 | SVG per facet | built in |
| 50-200 | canvas per facet | per canvas |
| 200+ | one shared canvas | cell index from pointer, then local test |

Shared canvas: per facet `save`, `rect` + `clip` to the plot area, `translate`, draw, `restore`. For hit testing, compute the column and row from the pointer and bounds-check **both** before combining them (`col` past the last column otherwise wraps into the next row's index):

```js
function cellAt(mx, my, { padLeft, padTop, cellW, cellH, gap, cols, n }) {
  const col = Math.floor((mx - padLeft) / (cellW + gap));
  const row = Math.floor((my - padTop) / (cellH + gap));
  if (col < 0 || col >= cols || row < 0) return null;
  const i = row * cols + col;
  return i < n ? { i, lx: mx - padLeft - col * (cellW + gap), ly: my - padTop - row * (cellH + gap) } : null;
}
```

Then reject points in the gap or margin (`lx`, `ly` outside the plot area).

## Scale-out and resize

- 50+ panels in a scroller: `IntersectionObserver` with `rootMargin: "200px"` to render just before they appear. 1000+: virtual scroll with a pool of visible-rows + 1 and a spacer at full grid height.
- Resize: debounce 100-150ms, and only re-layout when the column count changes.
- Canvas DPR: backing store at `w * devicePixelRatio`, `ctx.scale(dpr, dpr)`.

## Traps

- Every panel identical: each panel got a reference to the same array, not its own slice.
- Crosshair misaligns across panels: panels built their own x with different ranges.
