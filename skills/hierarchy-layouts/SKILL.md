---
name: hierarchy-layouts
description: "D3.js hierarchy layout computation and rendering: treemaps, sunburst, icicle, circle packing, dendrograms, radial trees, cluster layouts, and partition. Use this skill whenever the user wants to visualize tree-structured or nested data, convert tabular data to a hierarchy, choose a tiling strategy, render node-link diagrams, create space-filling layouts, place labels in hierarchy cells, or work with d3.hierarchy, d3.treemap, d3.pack, d3.tree, d3.cluster, d3.partition, or d3.stratify."
---

# Hierarchy Layouts

Patterns for computing and rendering D3 hierarchy layouts. For interactive patterns (expand/collapse, zoomable drill-down), see `hierarchy-interaction`.

## Data Validation

`d3.stratify()` throws unhelpful errors on bad input. Common issues: duplicate IDs, orphaned nodes (parent references nonexistent ID), cycles, multiple roots, no root.

**Strategy:** Validate before `d3.stratify()`. Index all IDs in a Set, check parent references. Detect cycles with DFS (gray/black coloring). Recover: deduplicate (keep first), break cycles by detaching back-edge node, graft orphans and extra roots onto synthetic `__root__`.

See [`scripts/validate-hierarchy.js`](scripts/validate-hierarchy.js) for `validateHierarchy()` / `cleanHierarchy()`.

## `.sum()` vs `.count()` — Critical Distinction

Space-filling layouts (treemap, pack, partition) need `.value` on every node.

- **`.sum(accessor)`** — rolls up leaf values. Accessor gets `.data`, not the node. Internal nodes get sum of descendants.
- **`.count()`** — sets value to number of leaves. Equal-area leaves regardless of data.

**Gotcha:** `.sum()` visits bottom-up. If accessor returns value for internal nodes, those values are *added* to children's sum — they don't replace it. To size only by leaves: `root.sum(d => d.children ? 0 : d.value)`.

**Gotcha:** Sort after `.sum()` since sort callbacks often use `.value`.

## Tiling Strategy Tradeoffs

```js
treemap.tile(d3.treemapSquarify);      // default
treemap.tile(d3.treemapResquarify);    // stable on data updates
treemap.tile(d3.treemapBinary);        // balanced binary split
treemap.tile(d3.treemapSliceDice);     // alternates by depth
```

The WHY:
- **Squarify**: best for static — minimizes aspect ratios, cells are readable. But node order is NOT preserved across data updates (jumpy animations).
- **Resquarify**: same aspect ratios as squarify but preserves node order — **essential for animated treemaps**. Use whenever you transition between data states.
- **Binary**: balanced splits, moderate aspect ratios, stable ordering. Good middle ground.
- **SliceDice**: preserves ordering and adjacency — use when spatial position has meaning (e.g., timeline).

## Coordinate System Semantics

Each layout uses `.x`/`.y` differently — this is a major source of confusion:

**`d3.tree()` / `d3.cluster()`**: `.size([crossAxis, mainAxis])`. For horizontal tree: `.size([height, width])`, then `d.y` = horizontal, `d.x` = vertical. Confusing but intentional — mathematical convention.

**Radial tree/cluster**: `.size([2 * Math.PI, radius])`. `d.x` = angle (radians), `d.y` = radius. Convert: `x = d.y * Math.cos(d.x - π/2)`, `y = d.y * Math.sin(d.x - π/2)`. The `-π/2` rotates so angle 0 points up.

**Space-filling layouts** (treemap, partition): `d.x0, d.y0, d.x1, d.y1` — rectangle bounds.

**Pack**: `d.x, d.y, d.r` — center and radius.

**Partition for sunburst**: `x` maps to angle, `y` to radius. Apply `d3.scaleSqrt` to radial dimension so outer rings don't dominate visually.

## Radial Label Transform

Labels in radial layouts need rotation and flipping to stay readable:

```js
node.append("text")
  .attr("transform", d => {
    const angle = d.x * 180 / Math.PI;
    return d.x < Math.PI
      ? `rotate(${angle - 90}) translate(${d.y + 6},0)`
      : `rotate(${angle + 90}) translate(${-d.y - 6},0)`;
  })
  .attr("text-anchor", d => d.x < Math.PI ? "start" : "end");
```

### Sunburst Arc Label Visibility

Calculate based on available arc length:
```js
const arcLength = (d.x1 - d.x0) * (d.y0 + d.y1) / 2;
label.attr("opacity", arcLength > 40 ? 1 : 0);
```

## Jump-Free Layout Transitions

When transitioning between radial (sunburst) and Cartesian (treemap/icicle), the `<g>` position jumps because arcs draw relative to center while rectangles draw from origin.

**Fix:** Interpolate `<g>` to new centroid, use compensating transform on `<path>` during arc phase:

```js
node.transition(t).attr("transform", d => `translate(${d.target_x},${d.target_y})`);
path.transition(t).attrTween("transform", (d) => (time) => {
  if (inArcPhase) {
    const curX = interpolateX(time), curY = interpolateY(time);
    return `translate(${cx - curX}, ${cy - curY})`;
  }
  return "translate(0,0)";
});
```

## Link Generators

| Generator | Use | Accessors |
|-----------|-----|-----------|
| `d3.linkHorizontal()` | Horizontal tree | `.x(d => d.y).y(d => d.x)` |
| `d3.linkVertical()` | Vertical tree | `.x(d => d.x).y(d => d.y)` |
| `d3.linkRadial()` | Radial tree/cluster | `.angle(d => d.x).radius(d => d.y)` |

## Common Pitfalls

1. **Forgetting `.sum()` or `.count()`.** Treemap, pack, partition require `.value`. Without it, all cells have zero area — layout runs but nothing visible.

2. **`.sum()` accessor gets `.data`, not the node.** Write `d => d.value`, not `d => d.data.value`.

3. **Sorting before `.sum()`.** Sort callbacks use `node.value`, not set until `.sum()`. Always `.sum()` first.

4. **Tree/cluster `size` convention.** `[crossAxis, mainAxis]` — `.size([height, width])` for horizontal. Then `d.y` = horizontal, `d.x` = vertical.

5. **Radial `-π/2` rotation.** Without it, angle 0 points right instead of up.

6. **Treemap `paddingTop` without labels.** Reserves space for group labels. Wasted if not rendering labels there.

7. **Pack labels overlapping.** Pack doesn't guarantee label space. Show only for certain depth ranges, clip to circle, or label on hover.

8. **Partition root fills center.** In sunburst, filter out root: `.filter(d => d.depth > 0)`, or render as small center circle for zoom-out nav.

9. **`d3.stratify` root parent ID.** Root must have null/empty parent. If CSV root has empty string: `.parentId(d => d.parent || null)`.

## References

- [D3 Hierarchy](https://d3js.org/d3-hierarchy)
- [Squarified Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — Bruls, Huizing & van Wijk (EuroVis 2000)
- [Treemaps for space-constrained visualization](http://www.cs.umd.edu/hcil/treemap-history/) — Shneiderman (1991)
