---
name: hierarchy-layouts
description: "D3.js hierarchy layout computation and rendering: treemaps, sunburst, icicle, circle packing, dendrograms, radial trees, cluster layouts, and partition. Use this skill whenever the user wants to visualize tree-structured or nested data, convert tabular data to a hierarchy, choose a tiling strategy, render node-link diagrams, create space-filling layouts, place labels in hierarchy cells, or work with d3.hierarchy, d3.treemap, d3.pack, d3.tree, d3.cluster, d3.partition, or d3.stratify."
---

# Hierarchy Layouts

Every dataset with a parent column is a tree, but not every tree needs the same picture. The layout you choose determines which question the viewer can answer at a glance — leaf sizes, nesting depth, grouping, or topology — and these are not interchangeable. For interactive patterns (expand/collapse, zoomable drill-down), see `hierarchy-interaction`.

## Choosing a Layout

Pick the layout that answers the viewer's actual question:

| Layout | Emphasizes | Viewer question | Perceptual channel |
|--------|-----------|-----------------|-------------------|
| **Treemap** | Leaf sizes | "Where is the budget going?" | Rectangle area — accurate size comparison |
| **Sunburst** | Depth + proportion | "How does this break down level by level?" | Arc angle — outer rings get *more* space at deeper levels |
| **Icicle** | Depth + proportion | Same as sunburst, but comparison-friendly | Rectangle width — easier to compare than arc angle |
| **Pack** | Grouping + containment | "Which cluster does this belong to?" | Enclosure — Gestalt makes groups pop, but wastes ~30% of space |
| **Tree** | Topology + paths | "How is A connected to B?" | Position — the only layout that shows edges |
| **Cluster** | Topology, leaves aligned | "How do endpoints compare?" | Same as tree, but all leaves at one depth |

**Decision shortcuts:**
- If the viewer needs to compare sizes: **treemap**. Rectangles beat arcs and circles for area judgment.
- If the viewer needs to see all levels at once: **sunburst** or **icicle**. Treemaps crush inner nodes as depth increases.
- If the viewer needs to trace parent-child paths: **tree** or **cluster**. Space-filling layouts hide topology.
- If grouping matters more than exact sizes: **pack**. The circles-within-circles metaphor communicates containment instantly, even though circle area is harder to compare than rectangle area.
- If the hierarchy is wide and shallow (2-3 levels): **treemap**. Nearly perfect data-ink ratio.
- If the hierarchy is narrow and deep (5+ levels): **sunburst** or **icicle**, because treemap cells for deep leaves become unreadably thin.

## When Not to Use Hierarchy Layouts

- **Flat data with no nesting.** A bar chart or dot plot is simpler and more accurate. Adding hierarchy for decoration wastes the viewer's effort.
- **Comparing exact values.** Position along a common scale (bar chart) beats area judgment (treemap) beats angle judgment (sunburst). If the question is "is A bigger than B by 10%?", use a bar chart.
- **Too many leaves (>500) without interaction.** A static treemap with 500 unlabeled slivers is a texture, not a visualization. Either add zoom/drill-down (see `hierarchy-interaction`) or aggregate small nodes into "Other."
- **No meaningful size variable.** If all leaves are the same size, treemap and sunburst degenerate into uniform grids. Use `.count()` deliberately, or switch to tree/cluster where equal leaves are expected.

## Data Validation

`d3.stratify()` throws unhelpful errors on bad input (duplicate IDs, orphaned nodes, cycles, multiple roots). Validate before calling it: index all IDs in a Set, check parent references, detect cycles with DFS (gray/black coloring). See [`scripts/validate-hierarchy.js`](scripts/validate-hierarchy.js) for `validateHierarchy()` / `cleanHierarchy()`.

## `.sum()` vs `.count()`

Space-filling layouts (treemap, pack, partition) require `.value` on every node. Two ways to set it:

- **`.sum(accessor)`** — rolls up leaf values. Accessor receives `.data`, not the node. Internal nodes get sum of descendants. If accessor returns a value for internal nodes, it gets *added* to the children's sum — it doesn't replace it. To size only by leaves: `root.sum(d => d.children ? 0 : d.value)`.
- **`.count()`** — sets value to number of leaves. Equal-area cells regardless of data.

**Always `.sum()` before `.sort()`** — sort callbacks use `.value`, which isn't set until `.sum()` runs.

## Tiling Strategy Tradeoffs

```js
treemap.tile(d3.treemapSquarify);      // default
treemap.tile(d3.treemapResquarify);    // stable on data updates
treemap.tile(d3.treemapBinary);        // balanced binary split
treemap.tile(d3.treemapSliceDice);     // alternates by depth
```

- **Squarify**: best for static — minimizes aspect ratios, cells are readable. But node order is NOT preserved across data updates (jumpy animations).
- **Resquarify**: same aspect ratios as squarify but preserves node order — **essential for animated treemaps**. Use whenever you transition between data states.
- **Binary**: balanced splits, moderate aspect ratios, stable ordering. Good middle ground.
- **SliceDice**: preserves ordering and adjacency — use when spatial position has meaning (e.g., timeline).

## Coordinate System Semantics

Each layout uses `.x`/`.y` differently — this is a major source of bugs:

**`d3.tree()` / `d3.cluster()`**: `.size([crossAxis, mainAxis])`. For horizontal tree: `.size([height, width])`, then `d.y` = horizontal position, `d.x` = vertical. Counterintuitive but intentional — mathematical convention where x is the "breadth" axis.

**Radial tree/cluster**: `.size([2 * Math.PI, radius])`. `d.x` = angle (radians), `d.y` = radius. Convert: `x = d.y * Math.cos(d.x - π/2)`, `y = d.y * Math.sin(d.x - π/2)`. The `-π/2` rotates so angle 0 points up instead of right.

**Space-filling layouts** (treemap, partition): `d.x0, d.y0, d.x1, d.y1` — rectangle bounds.

**Pack**: `d.x, d.y, d.r` — center and radius.

**Partition for sunburst**: `x` maps to angle, `y` to radius. Apply `d3.scaleSqrt` to the radial dimension — without it, outer rings dominate visually because area grows with r-squared.

## Radial Labels

Labels in radial layouts need rotation and flipping. Without flipping, labels on the left half render upside-down:

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

For sunburst arcs, hide labels when the arc is too short to read — otherwise they pile up at the center:
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

For node-link layouts, swap `.x`/`.y` accessors to match coordinate semantics: `d3.linkHorizontal().x(d => d.y).y(d => d.x)` for horizontal trees (because `d.y` is the horizontal axis). Use `d3.linkRadial().angle(d => d.x).radius(d => d.y)` for radial layouts.

## Common Pitfalls

1. **Treemap `paddingTop` without labels.** Reserves space for group labels at the top of each cell. If you're not rendering labels there, it wastes space and creates a visual gap the viewer will try to interpret.

2. **Pack and treemap labels overlapping.** These layouts don't guarantee label space — cells and circles can be any size, and parent labels compete with children. Three strategies, from simplest to most robust:

   - **Constraint relaxation:** Run a force simulation on label positions after layout. Each label starts at its circle/cell center, a rectangular collision force pushes overlapping labels apart, an anchor force pulls them back, and a containment constraint keeps them inside their circle. Pre-compute synchronously (`sim.stop(); for 100 ticks`) — the viewer never sees labels jiggle. This produces the densest correct labeling because it finds positions that fit rather than hiding labels that don't. Uses `rectCollideForce` from the `annotation` skill. See `blocks/19-circle-packing-zoom.html`.
   - **Focus-level only:** Show labels only for the focused node and its direct children. At overview depth-0, only show depth-1 labels. When zoomed into a depth-1 node, show depth-2 labels. Eliminates overlap entirely but shows fewer labels. Best combined with constraint relaxation: focus-level selects *which* labels to show, relaxation decides *where* to place them.
   - **Measure and hide:** Approximate text width (`name.length * fontSize * 0.55`) and compare to container width (circle diameter or treemap cell width). Hide labels that don't fit. Simplest approach but still overlaps when siblings are close together.
   - **Hover labels:** Show labels only on hover/focus. Most scalable but loses the overview — the viewer must probe to discover what things are called. Best as a fallback for labels too small to place.

3. **Sunburst root fills center.** Partition allocates the full innermost ring to root, which carries no information. Filter it out: `.filter(d => d.depth > 0)`, or render as a small center circle for zoom-out navigation.

4. **Squarify for animated data.** Squarify reorders nodes to minimize aspect ratios, so cells jump to new positions when data changes. Switch to `treemapResquarify` for any treemap that transitions between data states.

## References

- [D3 Hierarchy](https://d3js.org/d3-hierarchy)
- [Squarified Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — Bruls, Huizing & van Wijk (EuroVis 2000)
- [Treemaps for space-constrained visualization](http://www.cs.umd.edu/hcil/treemap-history/) — Shneiderman (1991)
- [Visualization of large hierarchical data by circle packing](https://dl.acm.org/doi/10.1145/1124772.1124851) — Wang et al. (CHI 2006)
