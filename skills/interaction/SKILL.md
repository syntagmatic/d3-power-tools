---
name: interaction
description: "Interactive D3 charts that stay correct under fast input: brushing (1D/2D, multi-region, keyboard), lasso, click and hover selection, intersection brushing on parallel coordinates, fisheye, linked views and cross-filtering, coordinated highlighting, d3.dispatch, shared state stores, crossfilter bitmaps, focus+context, overview+detail, zoom and pan, semantic vs geometric zoom, rescaleX, zoom constraints, zoom-to-fit, minimap, pinch-to-zoom, level of detail, and robustness: throttling, rAF coalescing, stale closures, feedback loops."
---

# Interaction

The API for brushes and zoom is easy; what breaks is everything around it. A brush that's correct at 1Hz stutters at 120Hz, a linked view triggers itself, a zoom handler keeps an old scale after resize. Pick the gesture, the wiring, and the zoom model from the tables below, then check every handler against the robustness traps. Audits rate those traps as the weakest part of generated interactive charts.

## Which selection gesture

| If the viewer wants to... | Use | Not |
|---|---|---|
| pick a range on one quantitative or time axis | `d3.brushX` / `brushY` | a 2D brush that forces a meaningless y extent |
| pick a rectangular region of a scatter | `d3.brush` | lasso (overkill for axis-aligned clusters) |
| pick an irregular cluster | lasso: Shift+drag path, `d3.polygonContains` | many rectangles |
| pick several disjoint regions in one view | Shift+drag appends extents; union them | separate brushes per region |
| pick lines that cross a region on parallel coordinates | per-axis `brushY` (AND across axes), or intersection "strum" line for "lines passing between A and B" | testing only vertices |
| pick one item or category | click on mark or legend; toggle; Escape or background click clears | a brush |
| inspect without committing | hover + tooltip, found with `d3.Delaunay.find` on one overlay | per-mark listeners on 10K marks |
| see local detail without losing context | fisheye on axis positions (parcoords) or radially (scatter, network) | zoom, when global context must stay visible |

Brushes need a keyboard path (`tabindex`, arrow keys, Escape) and touch needs a non-hover path. Selection over >1K rows: technique by size in `references/brushing.md`.

## Which linking architecture

| Situation | Wiring |
|---|---|
| 2 views, one direction (overview drives detail) | direct call |
| 3-8 views exchanging events | `d3.dispatch`, one namespace per listener (`"brush.scatter"`); an un-namespaced `.on("brush", f)` replaces the previous listener |
| filter + zoom + sort + undo/URL | one store; views render from state, never from event payloads |
| any cross-view selection | keyed `SelectionModel` (per-source key sets, `intersect` or `union`); never array indices |
| cross-filtering 100K+ rows | bitmap masks, `Uint32Array`, AND per dimension; each view skips its own filter |
| 50K+ rows into histograms | Falcon-style prefetched counts |
| past browser memory, SQL filters | Mosaic + DuckDB-WASM, D3 only renders |

Before wiring, ask whether to link at all: past 3-4 active views, viewers lose track of cause and effect. Link only views that show the selection from a different angle. Show filtered data as **ghost + active**: full data in gray behind, subset in accent color in front. Keep scale domains fixed while dragging; rescale on `end` if at all.

## Which zoom

| If the chart... | Use |
|---|---|
| reads fine at default scale, or the task is comparing all values | no zoom (filter or small multiples instead) |
| is spatial: map, floor plan, node-link | geometric: transform a `<g>`, counter-scale `r` and font-size by `1/k` |
| has data axes | semantic: `transform.rescaleX(x)` from the **original** scale, redraw axes and marks |
| has 10K+ marks | Canvas under an SVG overlay that owns the zoom and the axes; cull to the visible domain |
| needs overview + detail on time | context `brushX` driving focus zoom, both directions guarded |
| allows zoom > ~5× | add a minimap |
| changes representation with zoom | LOD states with separate enter/exit thresholds (hysteresis) |
| sits in a scrolling page | wheel only with Ctrl/⌘ (`zoom.filter`), or enable on click |

Always set `scaleExtent`, `extent` (the plot area inside margins) and `translateExtent`. Programmatic zoom animates (`selection.transition().call(zoom.transform, t)`), and `zoom.transform` doesn't clamp k to `scaleExtent`, so clamp it yourself.

## Robustness traps

Each of these looks fine in a slow manual test and breaks under a real mouse.

| Trap | Symptom | Fix |
|---|---|---|
| Unthrottled handler | brush/pointermove/zoom runs filter + redraw per event; jank at 10K rows | handler stores latest input; `requestAnimationFrame` does compute and draw, once per frame |
| Compute outside the frame | rAF gates the paint but the O(n) mask rebuild still runs per event | move the computation into the frame callback too |
| Transition per drag event | 150ms transitions restart every event, marks lag and never settle | set attributes directly while dragging; transition on `end` only |
| Transition conflicts | a direct `.attr()` set mid-transition is overwritten by the running tween on its next tick | `selection.interrupt()` before setting or restarting; a new unnamed transition cancels the old one, so name transitions that animate independent properties |
| Stale closure over scales | after resize or data reload, brush inversion and hit-testing use old scales | read `x`, `y`, data from a mutable chart/store object inside the handler, not captured `const`s from setup |
| Compounded rescale | zoom accelerates, then flips | `transform.rescaleX(originalX)`, never a rescaled copy |
| `brush.move` inside a brush handler | infinite recursion or a brush that won't let go | guard: `if (!event.sourceEvent) return;` (programmatic moves have a null `sourceEvent`) |
| Brush drives zoom drives brush | infinite loop, or a focus that never redraws | a `syncing` flag around each cross-call; redraw before the guard return (`references/navigation.md`) |
| Linked view re-triggers itself | A → B → A ping-pong, or A's brush cleared by its own echo | tag emits with a `source` id; each view skips events from itself |
| Keyboard moves ignored | `brush.move` from arrow keys has null `sourceEvent`, so the guard drops it | call the selection update directly after the keyboard move |
| Duplicate listeners | remount adds a second handler; everything fires twice | namespaced `.on("x.view", null)` on teardown |
| Selection by index | linked view highlights wrong rows after sort/filter | select by key |
| Zoom state desync | setting `g.attr("transform")` by hand; next gesture jumps back | always go through `zoom.transform` |
| Hover + selection redraws | flicker from two render paths | one coalesced render, or separate layers |
| Touch | hover-only info unreachable; page scrolls instead of panning | tap path for essentials; `touch-action: none` on zoomed elements |

The coalescing pattern, in full:

```js
let latest, queued = false;             // not `latest === null`: a cleared brush IS null
function onInput(value) {               // brush, pointermove, zoom
  latest = value;
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => { queued = false; update(latest); });
}
```

The guard pattern for two behaviors that drive each other:

```js
let syncing = false;
function sync(fn) { if (syncing) return; syncing = true; try { fn(); } finally { syncing = false; } }
```

## Feedback timing

- Source chart updates immediately; linked targets can follow a frame later.
- During drag: no transitions. On `end`: ~300ms transitions, auto-rescale if wanted, URL `replaceState`.
- One shared tooltip for the dashboard, anchored to the data point for dense marks.
- Programmatic zoom: 500-750ms.

## References

- `references/brushing.md`: technique by row count, segment-intersection brushing and grid index, lasso, fisheye formula, multi-region brushes, keyboard brushes, Falcon, canvas highlight layers.
- `references/linked-views.md`: when not to link, overview+detail / cross-filter / ghost+active, fixed vs auto-rescaled domains, feedback and tooltips.
- `references/coordination.md`: dispatch vs store vs selection model, keyed `SelectionModel` (intersect/union), rAF render scheduling and priority, bitmap cross-filter code, React/Vue/Angular bridges.
- `references/navigation.md`: geometric vs semantic code, Canvas zoom, constraints, zoom-to-fit, minimap, guarded brush-to-zoom, linked zoom, LOD hysteresis, touch and wheel.
- `examples/`: `brushing-and-selection.html` (brush, lasso, linked highlight), `linked-views.html` (scatter, histogram, table, bars via `d3.dispatch`), `navigation.html` (semantic zoom, geometric Canvas zoom with minimap, focus+context, LOD, SVG-over-Canvas zoom).
