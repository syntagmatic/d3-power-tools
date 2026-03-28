---
name: hierarchy-layouts
description: "D3.js hierarchy layout computation and rendering: treemaps, sunburst, icicle, circle packing, dendrograms, radial trees, cluster layouts, and partition. Use this skill whenever the user wants to visualize tree-structured or nested data, convert tabular data to a hierarchy, choose a tiling strategy, render node-link diagrams, create space-filling layouts, place labels in hierarchy cells, or work with d3.hierarchy, d3.treemap, d3.pack, d3.tree, d3.cluster, d3.partition, or d3.stratify."
---

# Hierarchy Layouts

Every dataset with a parent column is a tree, but not every tree needs the same picture. The layout you choose determines which question the viewer can answer at a glance — leaf sizes, nesting depth, grouping, or topology. For interactive patterns (expand/collapse, zoomable drill-down), see `hierarchy-interaction`.

## Choosing a Layout

| Layout | Emphasizes | Viewer question | Perceptual channel |
|--------|-----------|-----------------|-------------------|
| **Treemap** | Leaf sizes | "Where is the budget going?" | Rectangle area |
| **Sunburst** | Depth + proportion | "How does this break down level by level?" | Arc angle |
| **Icicle** | Depth + proportion | Same, but easier to compare than arcs | Rectangle width |
| **Flame graph** | Aggregated call frequency | "Which code paths consume the most CPU?" | Merged partition rectangles |
| **Pack** | Grouping + containment | "Which cluster does this belong to?" | Enclosure — wastes ~30% space |
| **Tree** | Topology + paths | "How is A connected to B?" | Position — only layout showing edges |
| **Cluster** | Topology, leaves aligned | "How do endpoints compare?" | Same as tree, leaves at one depth |

**Decision shortcuts:**
- Compare sizes → **treemap**. Rectangles beat arcs and circles for area judgment.
- See all levels → **sunburst** or **icicle**. Treemaps crush inner nodes as depth increases.
- Trace parent-child paths → **tree** or **cluster**. Space-filling layouts hide topology.
- Grouping over exact sizes → **pack**. Circles communicate containment instantly.
- Wide and shallow (2-3 levels) → **treemap**. Nearly perfect data-ink ratio.
- Narrow and deep (5+ levels) → **sunburst** or **icicle**. Treemap cells become unreadably thin.

## When Not to Use Hierarchy Layouts

- **Flat data with no nesting.** A bar chart is simpler and more accurate.
- **Comparing exact values.** Position along a common scale beats area beats angle. Use a bar chart.
- **Too many leaves (>500) without interaction.** Add zoom/drill-down (see `hierarchy-interaction`) or aggregate into "Other."
- **No meaningful size variable.** Treemap/sunburst degenerate into uniform grids. Use `.count()` deliberately, or switch to tree/cluster.

## d3.stratify End-to-End

Flat CSV with id/parentId columns to hierarchy:

```js
const csv = await d3.csv("departments.csv", d3.autoType);
const stratify = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parentId || null);  // empty string → null for root

const root = stratify(csv);
root.sum(d => d.budget || 0).sort((a, b) => b.value - a.value);
```

For path-based data (file paths), use `/` delimiter: `d3.stratify().path(d => d.filepath)` — creates intermediate nodes automatically.

### Validation

`d3.stratify()` throws unhelpful errors on bad input. Validate before calling: check for duplicate IDs, orphaned nodes (parent not in dataset), and multiple/missing roots. Common causes: trailing whitespace in CSV ids, null vs empty string for root's parentId.

See [`scripts/validate-hierarchy.js`](scripts/validate-hierarchy.js) for the full `validateHierarchy()` / `cleanHierarchy()` with cycle detection.

## `.sum()` vs `.count()`

Space-filling layouts require `.value` on every node:

- **`.sum(accessor)`** — rolls up leaf values. Internal nodes get sum of descendants. If accessor returns a value for internal nodes, it's *added* to children's sum. To size only by leaves: `root.sum(d => d.children ? 0 : d.value)`.
- **`.count()`** — sets value to number of leaves. Equal-area cells.

**Always `.sum()` before `.sort()`** — sort uses `.value`, which isn't set until `.sum()` runs.

## Tiling Strategy Tradeoffs

```js
treemap.tile(d3.treemapSquarify);      // default — best aspect ratios, unstable order
treemap.tile(d3.treemapResquarify);    // stable on data updates — essential for animation
treemap.tile(d3.treemapBinary);        // balanced binary split — moderate ratios, deterministic
treemap.tile(d3.treemapSliceDice);     // alternates by depth — preserves ordering/adjacency
```

**Decision shortcut:** Animated? → resquarify. Position encodes meaning? → sliceDice. Otherwise → squarify. SliceDice is also the basis of Marimekko charts (2-level hierarchy: variable-width columns + segments).

## Coordinate System Semantics

Each layout uses `.x`/`.y` differently — major source of bugs:

**`d3.tree()` / `d3.cluster()`**: `.size([crossAxis, mainAxis])`. For horizontal tree: `.size([height, width])`, then `d.y` = horizontal, `d.x` = vertical. Counterintuitive but intentional.

**Radial tree/cluster**: `.size([2 * Math.PI, radius])`. `d.x` = angle (radians), `d.y` = radius. Convert: `x = d.y * Math.cos(d.x - π/2)`, `y = d.y * Math.sin(d.x - π/2)`.

**Space-filling** (treemap, partition): `d.x0, d.y0, d.x1, d.y1` — rectangle bounds.

**Pack**: `d.x, d.y, d.r` — center and radius.

**Partition for sunburst**: `x` maps to angle, `y` to radius. Apply `d3.scaleSqrt` to the radial dimension — without it, outer rings dominate because area grows with r².

## Partition Orientation Variants

Icicle, flame graph, and sunburst are the same `d3.partition()` with different coordinate mappings:

```js
const partition = d3.partition().size([width, height]).padding(1);

// Top-down icicle (default): rect at (d.x0, d.y0)
// Bottom-up flame graph: flip y → rect at (d.x0, height - d.y1)
// Left-to-right: partition.size([height, width]), swap x/y in rendering
```

**Icicle vs sunburst:** icicles win for labels (horizontal text), size comparison (common baseline), deep hierarchies (no r² distortion). Sunbursts win for compactness in wide-but-shallow trees and provide a natural center target for zoom-out.

**Flame graphs** (Brendan Gregg, 2011): inverted partition where x-axis is alphabetically sorted — identical stack frames merge so width = total sampled time. Flame *charts* (Chrome DevTools) are time-ordered and don't merge. See [d3-flame-graph](https://github.com/spiermar/d3-flame-graph). For zoomable icicle, see `hierarchy-interaction`.

## Treemap Label Placement

Measure text against cell size, truncate or hide when it won't fit:

```js
cell.append("text")
  .attr("x", 4).attr("y", 14)
  .text(d => d.data.name)
  .each(function(d) {
    const cellWidth = d.x1 - d.x0 - 8, cellHeight = d.y1 - d.y0;
    if (cellHeight < 16) { d3.select(this).remove(); return; }
    let text = d.data.name;
    while (this.getComputedTextLength() > cellWidth && text.length > 0) {
      text = text.slice(0, -1);
      d3.select(this).text(text + "...");
    }
    if (text.length === 0) d3.select(this).remove();
  });
```

**Multi-line labels** for larger cells: split name on whitespace, append `<tspan>` elements with `dy="1.1em"`. Track available lines from cell height (`Math.floor((d.y1 - d.y0 - 4) / 14)`), stop appending when full.

## Radial Labels

Labels in radial layouts need rotation and flipping — without flipping, left-half labels render upside-down:

```js
// Sunburst arc label — x is angle, y is radius (after partition)
label.attr("transform", d => {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
  const y = (d.y0 + d.y1) / 2;
  return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
}).attr("text-anchor", d => {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
  return x < 180 ? "start" : "end";
});
```

**Tree/cluster radial labels:** same flip logic but position by `d.x` (angle) and `d.y` (radius): `rotate(angle - 90) translate(radius + 6, 0)`, flip with `rotate(180)` when angle > π.

Hide labels when arc is too short: `label.attr("opacity", arcLength > 40 ? 1 : 0)` where `arcLength = (d.x1 - d.x0) * (d.y0 + d.y1) / 2`.

## Drilldown: Layout-Side Setup

When the viewer clicks a node, rescale to map the clicked node's bounds to the full viewport:

```js
function zoomTo(d) {
  focus = d;
  const x = d3.scaleLinear([d.x0, d.x1], [0, width]);
  const y = d3.scaleLinear([d.y0, d.y1], [0, height]);

  cell.transition().duration(750)
    .attr("transform", n => `translate(${x(n.x0)},${y(n.y0)})`)
    .select("rect")
      .attr("width", n => Math.max(0, x(n.x1) - x(n.x0)))
      .attr("height", n => Math.max(0, y(n.y1) - y(n.y0)));

  // Breadcrumb: d.ancestors().reverse() → spans with click-to-zoom
  // Filter visible: root.descendants().filter(n => n.x0 >= d.x0 && n.x1 <= d.x1 && ...)
}
```

For the full zoomable treemap/sunburst/pack interaction pattern with animated transitions, see `hierarchy-interaction`.

## Link Generators

For node-link layouts, swap `.x`/`.y` accessors: `d3.linkHorizontal().x(d => d.y).y(d => d.x)` for horizontal trees. Use `d3.linkRadial().angle(d => d.x).radius(d => d.y)` for radial layouts.

## Color Mapping Strategies

Three patterns, each answering a different question:

**Categorical by top-level ancestor** — "which branch?" Most common treemap coloring:

```js
const topLevel = root.children || [root];
const color = d3.scaleOrdinal(topLevel.map(d => d.data.name), d3.schemeTableau10);
const branch = d => d.ancestors().find(a => a.depth === 1)?.data.name;
cell.attr("fill", d => color(branch(d)))
    .attr("fill-opacity", d => 0.4 + 0.6 * (1 - d.depth / root.height));
```

**Sequential by depth** — "how deep?" `d3.scaleSequential([0, root.height], d3.interpolateBlues)`, fill by `d.depth`.

**Diverging by change** — "what grew or shrank?" `d3.scaleDiverging([-0.5, 0, 0.5], d3.interpolateRdBu)`, fill by `d.data.change` (relative change between periods).

## Performance

SVG treemaps work up to ~500 nodes. Beyond that, switch to Canvas for the data layer (`ctx.fillRect` for each leaf), SVG for labels/overlays. Hit detection: point-in-rectangle on `root.leaves()`.

**Tiling for animation:** always use `treemapResquarify` — it caches topology so cells resize without reordering.

**Pack is expensive.** Circle packing solves a non-trivial optimization. For >5K nodes, pre-compute once and cache. For interactive filtering, recompute only affected subtrees.

## Common Pitfalls

1. **Treemap `paddingTop` without labels.** Reserves space that goes unused — visual gap the viewer tries to interpret.

2. **Pack and treemap labels overlapping.** Four strategies from simplest to most robust: (a) *Measure and hide* — approximate text width vs container, hide if it won't fit. (b) *Focus-level only* — show labels only for focused node + direct children. (c) *Constraint relaxation* — force simulation on label positions with rectangular collision + anchor force + containment. Pre-compute synchronously. Densest correct labeling. Uses `rectCollideForce` from `annotation` skill. (d) *Hover labels* — show on hover/focus. Most scalable but loses overview.

3. **Sunburst root fills center.** Filter with `.filter(d => d.depth > 0)`, or render as a small zoom-out target.

4. **Squarify for animated data.** Reorders cells on each update → jump. Use `treemapResquarify`.

5. **`.sum()` vs `.count()` confusion.** All cells same size? Probably `.count()` when you meant `.sum()`. Totals wrong? Accessor returns values for internal nodes (added to children's sum, not replaced).

6. **Negative values silently ignored.** `.sum(d => d.profit)` turns negatives to 0 — no warning. Encode sign as color, use `Math.abs()` for area.

7. **Stratify with missing parents.** Throws `"missing: X"` or `"ambiguous: X"`. Always validate first. Common causes: trailing whitespace, null vs empty string for root parent, header row in data.

## Observable Plot

Plot's `Plot.tree()` handles stratify, links, and labels declaratively for simple node-link trees. D3's value is in space-filling layouts, Canvas rendering, custom interactions, and coordinate-system control.

## References

- [D3 Hierarchy](https://d3js.org/d3-hierarchy)
- [Squarified Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — Bruls, Huizing & van Wijk (EuroVis 2000)
- [Treemaps for space-constrained visualization](http://www.cs.umd.edu/hcil/treemap-history/) — Shneiderman (1991)
- [Visualization of large hierarchical data by circle packing](https://dl.acm.org/doi/10.1145/1124772.1124851) — Wang et al. (CHI 2006)
- [Flame Graphs](https://www.brendangregg.com/flamegraphs.html) — Brendan Gregg
- [Perceptual Guidelines for Treemaps](https://doi.org/10.1109/TVCG.2010.186) — Kong et al.
