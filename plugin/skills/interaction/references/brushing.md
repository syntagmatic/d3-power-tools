# Brushing and selection mechanics

Absorbed from the v2 `brushing` skill. Open when the hard part is deciding *which marks are selected*: intersection (strum) brushing on polylines, lasso, fisheye, multi-region brushes, keyboard brushes, or selection over 10K+ rows. Cross-view wiring lives in `coordination.md`.

## Picking a technique by size

| Rows / view | Technique |
|---|---|
| <1K, any view | `d3.brush` / `brushX`, test every mark on each event |
| 1K-50K, scatter or parallel coordinates | lasso or intersection brush; move the geometric test to a Web Worker so drag stays smooth |
| 10K+ polylines | segment grid index (below), query only touched cells |
| 50K+, histograms / aggregates | Falcon-style prefetch: O(1) count lookups during brushing |
| 50K+, item views (scatter) | test a ~2K reservoir sample immediately, full scan on `requestIdleCallback`; run the full scan synchronously on brush `end` |

Observable Plot's brush covers simple linked brushing. Drop to raw D3 for lasso, intersection brushing, fisheye, or custom composition.

## Line intersection brushing (parallel coordinates)

A drawn query line selects every polyline it crosses. Start it with Alt+drag or right-drag so it doesn't collide with axis brushes; `setPointerCapture` so it keeps tracking outside the SVG.

```js
// Orientation test: sign of cross product (pk - pi) x (pj - pi)
const direction = (pi, pj, pk) =>
  (pk[0] - pi[0]) * (pj[1] - pi[1]) - (pj[0] - pi[0]) * (pk[1] - pi[1]);
const onSegment = (pi, pj, pk) =>
  Math.min(pi[0], pj[0]) <= pk[0] && pk[0] <= Math.max(pi[0], pj[0]) &&
  Math.min(pi[1], pj[1]) <= pk[1] && pk[1] <= Math.max(pi[1], pj[1]);

function segmentsIntersect(p1, p2, p3, p4) {
  const d1 = direction(p3, p4, p1), d2 = direction(p3, p4, p2);
  const d3 = direction(p1, p2, p3), d4 = direction(p1, p2, p4);
  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
  return (d1 === 0 && onSegment(p3, p4, p1)) || (d2 === 0 && onSegment(p3, p4, p2)) ||
         (d3 === 0 && onSegment(p1, p2, p3)) || (d4 === 0 && onSegment(p1, p2, p4));
}

function intersectionBrush(q0, q1, data, dimensions, scales, xPositions) {
  return data.filter(d => {
    const pts = dimensions.map((dim, i) => [xPositions[i], scales[dim](d[dim])]);
    return pts.slice(0, -1).some((p, i) => segmentsIntersect(p, pts[i + 1], q0, q1));
  });
}
```

For 10K+ rows, post `{q0, q1, polylines}` to a worker that returns selected indices, and bucket segments into a grid once so a query only tests segments in the cells the query line touches:

```js
function buildSegmentGrid(polylines, cellSize = 50) {
  const grid = new Map(), cell = v => Math.floor(v / cellSize);
  polylines.forEach((pts, pi) => {
    for (let si = 0; si < pts.length - 1; si++) {
      const [x0, y0] = pts[si], [x1, y1] = pts[si + 1];
      for (let c = cell(Math.min(x0, x1)); c <= cell(Math.max(x0, x1)); c++)
        for (let r = cell(Math.min(y0, y1)); r <= cell(Math.max(y0, y1)); r++) {
          const key = `${c},${r}`;
          if (!grid.has(key)) grid.set(key, []);
          grid.get(key).push({ pi, si });
        }
    }
  });
  return { grid, cellSize };
}
```

Collect hit polyline indices in a Set (one polyline crosses many cells).

## Lasso

Shift+drag starts the path. Append points from `event.getCoalescedEvents?.() ?? [event]` for a smooth outline, close on `pointerup`, then test containment. `d3.polygonContains(polygon, point)` is the D3 call; the ray-casting version below has no dependencies and runs in a worker.

```js
function pointInPolygon([x, y], poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
```

Draw the lasso outline on SVG or its own canvas layer. Drawing it on the data canvas forces a full data redraw per pointer event.

## Fisheye

Sarkar-Brown distortion: normalized distance `t = d / radius` maps to `t(k+1) / (tk + 1)`, where `k` is strength (3 is a sane default). Points beyond `radius` don't move.

```js
function cartesianFisheye(positions, focus, k = 3, radius = Math.max(...positions) * 0.4) {
  return positions.map(x => {
    const dx = x - focus, t = Math.abs(dx) / radius;
    if (t >= 1) return x;
    return focus + Math.sign(dx) * radius * t * (k + 1) / (t * k + 1);
  });
}
```

Use it on parallel-coordinate axis positions on `pointermove`, snapping back over 300ms on `pointerleave`. Radial fisheye (scatter, node-link, maps) applies the same map to `Math.hypot(dx, dy)` and scales `dx, dy` by the ratio. Recomputing on every pointermove is expensive, so coalesce to one per frame.

## Multi-region brushes (Shift+drag)

Keep an array of extents on one view. On brush `end`, shift appends and a plain drag replaces; test marks against the union and emit one key set under this view's source id. Cross-view union vs intersect is the selection model's job (`coordination.md`), not the brush's.

```js
let regions = [];
brush.on("end", ({ selection, sourceEvent }) => {
  if (!sourceEvent || !selection) return;
  regions = sourceEvent.shiftKey ? [...regions, selection] : [selection];
  const hit = d => regions.some(([[x0, y0], [x1, y1]]) => {
    const px = x(d.x), py = y(d.y);
    return px >= x0 && px <= x1 && py >= y0 && py <= y1;
  });
  model.update("scatter", data.filter(hit).map(d => d.id));
});
```

## Keyboard brushes

Put `tabindex="0"` and `role="slider"` on the brush group. Arrow keys move the extent, Shift multiplies the step by 5, Escape clears. Read with `d3.brushSelection(node)`, write with `brushG.call(brush.move, [a, b])`. That `brush.move` fires brush events with `sourceEvent` null, so handlers that ignore programmatic moves will ignore keyboard moves too; call the selection update directly after moving.

## Falcon (50K+ rows, aggregate views)

Moritz & Heer, CHI 2019. On `pointerenter` of a view, prefetch a prefix-sum index of the other views' bin counts over the hovered view's dimension. During the brush, each update is a constant-time lookup per bin instead of a scan. `falcon-vis` (github.com/cmudig/falcon-vis) implements it over DuckDB-WASM or Arrow.

## Traps

- Brush extents on a zoomed chart are in screen space. Invert with the rescaled scale (`transform.rescaleX(x).invert(px)`), or `d3.zoomTransform(node).invert([x, y])` for geometric zoom.
- Hover and selection both triggering redraws flickers. Use separate layers or one coalesced render pass.
- Canvas highlight: background layer draws all rows at `globalAlpha` ~0.05, foreground draws selected rows at ~0.8. Cancel any in-flight progressive render when the selection changes, or stale batches paint over the new selection.
- Touch has no hover. Essential information behind mouseover needs a tap or long-press path.
- Use pointer events and `setPointerCapture`, not mouse events.
