# Hierarchy layouts

Absorbed from the v2 `hierarchy-layouts` skill. Open when building a static treemap, sunburst, icicle, pack, tree, or cluster: data prep, coordinate conventions, labels, and color.

## Getting to a hierarchy

`d3.stratify()` for flat id/parentId rows, `stratify().path(d => d.filepath)` for slash-delimited paths (intermediate nodes are created for you). Normalize the root's parent first: `.parentId(d => d.parentId || null)`, since an empty string is not a root.

Stratify throws terse errors: `missing: X` (parent not in data), `ambiguous: X` (duplicate id), plus no-root / multiple-roots / cycle. Usual causes: trailing whitespace in ids, `""` vs `null` for the root's parent, a header row parsed as data. Run `scripts/validate-hierarchy.js` (`validateHierarchy()` reports duplicates, orphans, cycles, root count; `cleanHierarchy()` repairs) before stratifying user data.

## `.sum()` vs `.count()`

- `.sum(f)` sets each node's value to `f(node.data)` **plus** its children's values. If internal rows carry a value too, it's added, not replaced. Leaf-only sizing: `root.sum(d => d.children ? 0 : d.value)`.
- `.count()` makes every leaf equal. All cells the same size usually means `.count()` where `.sum()` was meant.
- `.sum()` before `.sort()`: sort reads `.value`.
- Negative values are **not** clamped: they subtract from ancestors' totals and produce negative or zero-size cells. Size by `Math.abs()` and encode sign with color.

## Tiling

| Situation | Tile |
|---|---|
| Static, sizes are the point | `treemapSquarify` (default, best aspect ratios, order not preserved) |
| Values change and cells animate | `treemapResquarify` (keeps the previous arrangement, so cells resize instead of jumping) |
| Position/order carries meaning, or Marimekko | `treemapSliceDice` (alternates direction by depth) |
| Deterministic balanced splits | `treemapBinary` |

## Coordinate conventions

| Layout | Fields | Note |
|---|---|---|
| tree / cluster | `d.x` cross-axis, `d.y` depth axis | horizontal tree: `.size([height, width])`, then draw at `(d.y, d.x)` |
| radial tree / cluster | `d.x` angle (rad), `d.y` radius | `.size([2 * Math.PI, radius])` |
| treemap / partition | `x0, y0, x1, y1` | |
| pack | `x, y, r` | |
| partition as sunburst | x → angle, y → radius | map radius through `scaleSqrt` or outer rings get too much area |

Radial to Cartesian (angle 0 at 12 o'clock): `[d.y * Math.cos(d.x - Math.PI / 2), d.y * Math.sin(d.x - Math.PI / 2)]`.

Link generators swap accessors to match: `d3.linkHorizontal().x(d => d.y).y(d => d.x)`; `d3.linkRadial().angle(d => d.x).radius(d => d.y)`.

## Partition variants

Icicle, flame graph and sunburst are one `d3.partition()` drawn differently. Flame graph: flip y (`height - d.y1`). Left-to-right icicle: `.size([height, width])` and swap x/y when drawing.

Flame graph (Gregg) vs flame chart: a flame graph sorts frames alphabetically so identical stacks merge and width is total time. A flame chart (DevTools) is time-ordered and doesn't merge. Don't call one the other.

## Labels

Treemap: measure and truncate, hide below ~16px cell height. `getComputedTextLength()` only works once the text is in the DOM.

```js
function fitLabel(textEl, d) {
  const maxW = d.x1 - d.x0 - 8;
  if (d.y1 - d.y0 < 16) return textEl.remove();
  let s = d.data.name;
  while (textEl.getComputedTextLength() > maxW && s.length) {
    s = s.slice(0, -1);
    textEl.textContent = s + "…";
  }
  if (!s.length) textEl.remove();
}
```

Multi-line: split on whitespace into `<tspan dy="1.1em">`, stop at `Math.floor((d.y1 - d.y0 - 4) / 14)` lines.

Radial labels must flip on the left half or they read upside down:

```js
const radialLabel = d => {
  const a = (d.x0 + d.x1) / 2 * 180 / Math.PI, r = (d.y0 + d.y1) / 2;
  return `rotate(${a - 90}) translate(${r},0) rotate(${a < 180 ? 0 : 180})`;
};
// text-anchor: a < 180 ? "start" : "end"; hide when (d.x1 - d.x0) * r < ~40px of arc
```

For tree/cluster nodes use `d.x`/`d.y` directly: `rotate(angle - 90) translate(radius + 6, 0)`, flip when angle > π.

Pack and treemap labels crowd. Cheapest to most robust: measure and hide; label only the focused node and its children; rectangular-collision force run offline (see the `legibility` skill's annotation reference); labels on hover only.

## Color

| Question | Encoding |
|---|---|
| Which branch? | ordinal by depth-1 ancestor, opacity fading with depth |
| How deep? | `scaleSequential([0, root.height], ...)` by `d.depth` |
| What grew or shrank? | symmetric `scaleDiverging` on relative change |

```js
const branch = d => d.ancestors().find(a => a.depth === 1)?.data.name;
```

## Performance

- SVG treemaps are fine to a few hundred cells. Beyond that, fill leaves on Canvas and keep labels in SVG; hit-test by point-in-rect over `root.leaves()`.
- Pack is the expensive layout. Compute once and cache for large trees.

## Pitfalls

- `paddingTop` reserved for labels you then don't draw leaves an unexplained gap.
- Sunburst root disc fills the center: filter `d.depth > 0`, or keep it small as the zoom-out target.
- Squarify on animated data reorders cells every update.
- Observable Plot's `tree` mark covers a simple static node-link tree. Reach for D3 for space-filling layouts, Canvas, and custom interaction.
