# Parallel coordinates

Absorbed from the v2 `parallel-coordinates` skill. Open when plotting 5+ numeric dimensions as polylines, with axis brushing, reordering, or Canvas rendering at scale.

## When to use it

| Situation | Parallel coordinates? | Otherwise |
|---|---|---|
| 5+ numeric dimensions, see all at once; compare items across them | yes | |
| clusters in high-dimensional data | yes, with brushing | scatterplot matrix below 5 dims |
| 2-3 dimensions | no | scatterplot, small multiples |
| mostly categorical | no | parallel sets, alluvial |
| time series across dimensions | rarely | small multiples |
| 50+ dimensions | yes, with fisheye and column management | t-SNE/UMAP for the overview |

The payoff is brushing as analysis: interactively stacking range filters across dimensions and seeing which items survive.

## Reading crossings (point-line duality)

A 2D point becomes a line between two adjacent axes, so patterns between axes Xi and Xi+1 encode their relationship:

| Between two axes | Means |
|---|---|
| near-parallel segments | strong positive correlation |
| X / hourglass crossing | negative correlation |
| all segments through one point between the axes | perfect negative linear relationship |
| hyperbolic "bowtie" envelope | an elliptical cluster; waist width = tightness |
| uniform tangle | independence |

Only adjacent pairs are readable, which is why axis order is the main design decision.

## Axis order

| Strategy | When |
|---|---|
| correlation (greedy by \|r\|) | default for numeric exploration |
| domain grouping, outcome axis at far right | dimensions fall into natural groups |
| variance first (leftmost) | screening many dimensions |
| manual drag | testing a specific adjacency |

```js
function correlationOrder(data, dims) {
  const corr = (a, b) => {
    const ma = d3.mean(data, d => d[a]), mb = d3.mean(data, d => d[b]);
    let num = 0, sa = 0, sb = 0;
    for (const d of data) { const da = d[a] - ma, db = d[b] - mb; num += da * db; sa += da * da; sb += db * db; }
    return sa && sb ? num / Math.sqrt(sa * sb) : 0;
  };
  const ordered = [dims[0]], remaining = new Set(dims.slice(1));
  while (remaining.size) {
    const last = ordered.at(-1);
    const next = d3.greatest(remaining, d => Math.abs(corr(last, d)));
    ordered.push(next);
    remaining.delete(next);
  }
  return ordered;
}
```

Start from the highest-variance dimension (pass it first in `dims`).

## Architecture

Canvas below for polylines (`pointer-events: none`), SVG on top for axes, labels, and brushes, with identical size and margins. Draw all lines dimmed, then selected lines on top. Always `clearRect` before a redraw.

| Rows | Technique |
|---|---|
| < 500, < 20 dims | SVG paths |
| 500-5K | Canvas, one frame |
| 5K-50K | Canvas + progressive render queue (rAF chunks) |
| 50K+ | OffscreenCanvas in a worker (`transferControlToOffscreen`) |
| 50-200 dims | fisheye on axis x-positions + column search/removal |

- Progressive rendering must **shuffle** row order, or the first frames show only the first N rows of a sorted file, which misrepresents the data.
- Opacity by count: `alpha = clamp(100 / n, 0.01, 0.8)`.
- Straight segments read values at axes best. Béziers with control points at 1/3 and 2/3 between axes show flow; make it a toggle.
- Color by one dimension: sequential (viridis) for numeric, a CVD-safe categorical palette (`legibility`) up to ~7 categories. Beyond that, highlight on hover instead.

## Brushing

- `d3.brushY()` per axis, extent `[[-10, 0], [10, height]]`. Store filters as pixel or value ranges per dimension, and a row passes when every active filter passes. Clearing a brush deletes its filter.
- Multi-brush: an array of ranges per dimension for disjoint selections.
- Brushes live in the axis group's local coordinates, so they stay valid when axes are dragged.
- Strum (angular) brushing: the user draws a segment between two adjacent axes, and rows whose segment crosses it are selected. This selects by *relationship* (a wedge in the dual scatterplot), which axis brushes can't. Combine both.

```js
// Proper segment intersection: data segment (x1,ya)-(x2,yb) vs strum segment s.
function crossesStrum(x1, x2, ya, yb, s) {
  const cross = (ux, uy, vx, vy) => ux * vy - uy * vx;
  const c1 = cross(s.x2 - s.x1, s.y2 - s.y1, x1 - s.x1, ya - s.y1);
  const c2 = cross(s.x2 - s.x1, s.y2 - s.y1, x2 - s.x1, yb - s.y1);
  const c3 = cross(x2 - x1, yb - ya, s.x1 - x1, s.y1 - ya);
  const c4 = cross(x2 - x1, yb - ya, s.x2 - x1, s.y2 - ya);
  return c1 * c2 < 0 && c3 * c4 < 0;
}
```

## Axis interactions

- Reorder by drag: on drag, move the axis and re-sort `dimensions` by current x, then redraw; on end, transition it to its slot.
- Remove by dragging off the left edge. Filter axis names with a text input past ~50 columns.
- Invert on label click: keep the inverted set in a `Set` and apply it when (re)building scales. Mutating the range directly is lost the next time scales rebuild.
- Export the brushed rows: `d3.csvFormat(selected, dimensions)` into a Blob.

## Data types

- Numeric: `scaleLinear(extent).nice()`. Offer log per axis for skew, symlog if zeros exist.
- Categorical: `scalePoint` with padding, ordered by frequency or meaning, not alphabet.
- Missing values: route lines to a "null zone" below the axis, dashed or dimmed. Dropping rows hides the missingness pattern.

## Hover picking on Canvas

Draw every line to a hidden canvas with its index packed into RGB (`(i>>16)&255, (i>>8)&255, i&255`, 16M rows), lineWidth ~3 for easier targeting, `getContext("2d", { willReadFrequently: true })`. On pointermove read one pixel and only accept `alpha === 255`: lower alpha is background or an anti-aliased edge, which would decode to a wrong index. Size the hit canvas with the same DPR as the visible one. Redraw it on reorder, brush, and resize.

## Traps

- Blurry lines: canvas backing store at `width * dpr`, `ctx.scale(dpr, dpr)`, CSS size unchanged.
- Ghosting: forgot `clearRect`.
- Unshuffled progressive draw shows a biased first frame.
- Dense axis labels: rotate them or use fisheye.
