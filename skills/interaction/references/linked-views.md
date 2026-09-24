# Linked views: design

Absorbed from the v2 `linked-views` skill. Open when deciding *whether* and *how* to link charts in a dashboard. The wiring is in `coordination.md`; faceted grids of one chart type are in `small-multiples`.

A linked dashboard should read as one instrument, not a cockpit of widgets. N views give N angles on the same selection; each extra view also splits attention.

## When not to link

- **Parsimony.** Working memory holds about 4 chunks (Cowan). Past 3-4 simultaneously active views, viewers lose track of which gesture caused which update. With 6+ views, make one driver panel and group the rest as detail panels.
- **Complementarity.** Link two views only if the second answers "what does this selection look like from that angle?" If it shows the same thing in a different mark, cut the link.
- **Attention.** Render the source chart immediately and let targets follow a frame later (`coordination.md`, render priority), so the chart under the pointer never lags.

## Patterns

| Pattern | Shape | Note |
|---|---|---|
| Overview + detail | small context chart with a brush; the detail chart's domain follows the brush | the brush-drives-zoom loop guard in `navigation.md` applies |
| Cross-filtering | every view is both a filter and a display; each view shows rows passing all *other* views' filters | bitmap masks past ~100K rows (`coordination.md`) |
| Ghost + active | full dataset in light gray behind, filtered subset in accent color in front | ghost is static; only redraw the active layer |

Ghost + active density curves: a small subset's KDE spikes when normalized on its own. Scale the active curve by `subset.length / total.length` so it sits inside the ghost.

## Scale domains under filtering

- **Fixed** (computed once from all data) preserves spatial memory. Default for anything that updates during a drag.
- **Auto-rescale** reveals local structure but moves the ground under the viewer. Only rescale on brush `end`, never during the drag.

## Feedback

- Transitions go on brush `end` (~300ms). During the drag, set attributes directly; a transition per brush event interrupts itself and lags. If you want motion while dragging, keep it under ~80ms with `d3.easeExpOut`, and skip it entirely when the update re-bins.
- One shared tooltip element for the dashboard, not one per chart. Hovering chart A hides anything B was showing.
- Shareable state: serialize filters, selected keys and zoom `{k, x, y}` to the URL with `history.replaceState` (throttled; not per pointermove).
- Beyond browser memory (~10M rows) or when filters are really SQL, Mosaic + DuckDB-WASM turns filters into WHERE clauses and leaves D3 to render.
