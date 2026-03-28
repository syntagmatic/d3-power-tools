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
| **Icicle** | Depth + proportion | "How does this break down, and which parts are biggest?" | Rectangle width — easier to compare than arc angle |
| **Flame graph** | Aggregated call frequency | "Which code paths consume the most CPU?" | Merged partition rectangles — root at bottom |
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

## d3.stratify End-to-End

Flat CSV with id/parentId columns to hierarchy:

```js
const csv = await d3.csv("departments.csv", d3.autoType);
// csv: [{id: "CEO", parentId: ""}, {id: "Engineering", parentId: "CEO"}, ...]

const stratify = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parentId || null);  // empty string → null for root

const root = stratify(csv);
root.sum(d => d.budget || 0).sort((a, b) => b.value - a.value);
```

For path-based data (e.g., file paths), use `/` delimiter:

```js
const stratify = d3.stratify().path(d => d.filepath);
// input: [{filepath: "/src/index.js"}, {filepath: "/src/utils/math.js"}, ...]
// creates intermediate nodes for /src, /src/utils automatically
```

### Validation

`d3.stratify()` throws unhelpful errors on bad input (duplicate IDs, orphaned nodes, cycles, multiple roots). Validate before calling it:

```js
function validateFlat(rows, idField = "id", parentField = "parentId") {
  const ids = new Set(rows.map(d => d[idField]));
  const errors = [];

  // Duplicate IDs
  if (ids.size < rows.length) {
    const seen = new Set();
    for (const d of rows) {
      if (seen.has(d[idField])) errors.push(`Duplicate: "${d[idField]}"`);
      seen.add(d[idField]);
    }
  }

  // Orphaned nodes — parent not in dataset and not null/empty
  for (const d of rows) {
    const pid = d[parentField];
    if (pid && pid !== "" && !ids.has(pid)) {
      errors.push(`Orphan: "${d[idField]}" references missing parent "${pid}"`);
    }
  }

  // Multiple roots
  const roots = rows.filter(d => !d[parentField] || d[parentField] === "");
  if (roots.length === 0) errors.push("No root node (every row has a parent)");
  if (roots.length > 1) errors.push(`Multiple roots: ${roots.map(d => d[idField]).join(", ")}`);

  return errors;  // empty array = valid
}
```

See [`scripts/validate-hierarchy.js`](scripts/validate-hierarchy.js) for the full `validateHierarchy()` / `cleanHierarchy()` with cycle detection (DFS gray/black coloring).

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

- **Squarify**: best for static — minimizes aspect ratios (targets golden ratio ~1.618), cells are readable. But node order is NOT preserved across data updates (jumpy animations). Custom target: `d3.treemapSquarify.ratio(2)` — rarely needed, the default is perceptually optimal.
- **Resquarify**: same as squarify on first layout, then caches topology. Sizes change but positions stay — **essential for animated treemaps**. Aspect ratios degrade over many updates as the cached topology drifts from what squarify would choose fresh.
- **Binary**: recursive median-split, alternates H/V by container shape. Moderate aspect ratios, deterministic ordering. Good middle ground when stability matters more than aspect ratio quality.
- **SliceDice**: preserves ordering and adjacency — use when spatial position has meaning (e.g., timeline). Also the basis of Marimekko charts: `treemapSliceDice` on a 2-level hierarchy (depth-1 = variable-width columns, depth-2 = segments).
- **Slice / Dice** (primitives): `treemapSlice` = top-to-bottom strips, `treemapDice` = left-to-right strips. Rarely used directly.

**Decision shortcut:** Is it animated? Use resquarify. Does position encode meaning? Use sliceDice. Otherwise squarify. Consider binary only if you need stability without the sliceDice aspect-ratio penalty.

## Coordinate System Semantics

Each layout uses `.x`/`.y` differently — this is a major source of bugs:

**`d3.tree()` / `d3.cluster()`**: `.size([crossAxis, mainAxis])`. For horizontal tree: `.size([height, width])`, then `d.y` = horizontal position, `d.x` = vertical. Counterintuitive but intentional — mathematical convention where x is the "breadth" axis.

**Radial tree/cluster**: `.size([2 * Math.PI, radius])`. `d.x` = angle (radians), `d.y` = radius. Convert: `x = d.y * Math.cos(d.x - π/2)`, `y = d.y * Math.sin(d.x - π/2)`. The `-π/2` rotates so angle 0 points up instead of right.

**Space-filling layouts** (treemap, partition): `d.x0, d.y0, d.x1, d.y1` — rectangle bounds.

**Pack**: `d.x, d.y, d.r` — center and radius.

**Partition for sunburst**: `x` maps to angle, `y` to radius. Apply `d3.scaleSqrt` to the radial dimension — without it, outer rings dominate visually because area grows with r-squared.

## Partition Orientation Variants

Icicle, flame graph, and sunburst are the same `d3.partition()` layout with different coordinate mappings. Choose the orientation that matches your viewer's mental model:

```js
const partition = d3.partition().size([width, height]).padding(1);
const root = partition(hierarchy);

// Top-down icicle (root at top) — default mapping
rect.attr("x", d => d.x0).attr("y", d => d.y0);

// Bottom-up "flame graph" (root at bottom) — flip y
rect.attr("x", d => d.x0).attr("y", d => height - d.y1);

// Left-to-right icicle — swap size dimensions, swap x/y in rendering
// partition.size([height, width])
rect.attr("x", d => d.y0).attr("y", d => d.x0)
    .attr("width", d => d.y1 - d.y0).attr("height", d => d.x1 - d.x0);
```

**Icicle vs sunburst:** icicles win for label placement (horizontal text), size comparison (common baseline), deep hierarchies (no r-squared area distortion), and static output (no rotation). Sunbursts win for compactness in wide-but-shallow trees and provide a natural center target for zoom-out navigation.

**Flame graphs** (Brendan Gregg, 2011) are inverted partition layouts where the x-axis is alphabetically sorted — identical stack frames are merged so width = total sampled time. Flame *charts* (Chrome DevTools) are time-ordered on x and don't merge frames. Both are partition layouts, but flame charts typically require custom x-positioning rather than `d3.partition()`. For the canonical D3 implementation, see [d3-flame-graph](https://github.com/spiermar/d3-flame-graph). For zoomable icicle interaction, see `hierarchy-interaction`.

## Treemap Label Placement

Measure text against cell size, truncate or hide when it won't fit:

```js
cell.append("text")
  .attr("x", 4).attr("y", 14)
  .text(d => d.data.name)
  .each(function(d) {
    const cellWidth = d.x1 - d.x0 - 8;  // 4px padding each side
    const cellHeight = d.y1 - d.y0;
    if (cellHeight < 16) {               // too short for text
      d3.select(this).remove();
      return;
    }
    // measure rendered width, truncate with ellipsis
    let text = d.data.name;
    while (this.getComputedTextLength() > cellWidth && text.length > 0) {
      text = text.slice(0, -1);
      d3.select(this).text(text + "...");
    }
    if (text.length === 0) d3.select(this).remove();
  });
```

For multi-line labels in larger cells, use `<tspan>` word-wrapping:

```js
cell.append("text").each(function(d) {
  const cellW = d.x1 - d.x0 - 8;
  const words = d.data.name.split(/\s+/);
  let line = [], lineNum = 0;
  const maxLines = Math.floor((d.y1 - d.y0 - 4) / 14);  // 14px line height
  for (const word of words) {
    line.push(word);
    const tspan = d3.select(this).append("tspan")
      .attr("x", 4).attr("dy", lineNum ? "1.1em" : "1em")
      .text(line.join(" "));
    if (tspan.node().getComputedTextLength() > cellW) {
      line.pop();
      tspan.text(line.join(" "));
      line = [word];
      lineNum++;
      if (lineNum >= maxLines) break;
      d3.select(this).append("tspan")
        .attr("x", 4).attr("dy", "1.1em").text(word);
    }
  }
});
```

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

For sunburst arcs, rotate labels along the arc midpoint and flip so text always reads left-to-right:

```js
// Sunburst label transform — x is angle, y is radius (after partition)
label.attr("transform", d => {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;  // midpoint angle in degrees
  const y = (d.y0 + d.y1) / 2;                     // midpoint radius
  // Flip text on left half so it reads L→R
  return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
}).attr("text-anchor", d => {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
  return x < 180 ? "start" : "end";
});
```

Hide labels when the arc is too short to read — otherwise they pile up at the center:
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

## Drilldown: Layout-Side Setup

When the viewer clicks a node to zoom in, the layout doesn't change — only the scales do. Recompute scales to map the clicked node's bounds to the full viewport:

```js
// Treemap drilldown — rescale to show clicked node's subtree
function zoomTo(d) {
  const x = d3.scaleLinear().domain([d.x0, d.x1]).range([0, width]);
  const y = d3.scaleLinear().domain([d.y0, d.y1]).range([0, height]);

  cell.transition().duration(750)
    .attr("transform", n => `translate(${x(n.x0)},${y(n.y0)})`)
    .select("rect")
      .attr("width", n => Math.max(0, x(n.x1) - x(n.x0)))
      .attr("height", n => Math.max(0, y(n.y1) - y(n.y0)));
}
```

Breadcrumb trail for navigation back — track the zoom path:

```js
let focus = root;
const breadcrumb = d3.select("#breadcrumb");

function zoomTo(d) {
  focus = d;
  // rebuild breadcrumb from ancestors
  const ancestors = d.ancestors().reverse();
  breadcrumb.selectAll("span").data(ancestors, d => d.data.name)
    .join("span")
      .text(d => d.data.name)
      .on("click", (event, d) => zoomTo(d));

  // ... rescale layout as above
}
```

Filter visible nodes to the focused subtree to avoid rendering thousands of off-screen cells:

```js
const visible = root.descendants().filter(n =>
  n.x0 >= focus.x0 && n.x1 <= focus.x1 &&
  n.y0 >= focus.y0 && n.y1 <= focus.y1
);
```

For the full zoomable treemap/sunburst/pack interaction pattern with animated transitions, see `hierarchy-interaction`.

## Link Generators

For node-link layouts, swap `.x`/`.y` accessors to match coordinate semantics: `d3.linkHorizontal().x(d => d.y).y(d => d.x)` for horizontal trees (because `d.y` is the horizontal axis). Use `d3.linkRadial().angle(d => d.x).radius(d => d.y)` for radial layouts.

## Color Mapping Strategies

Three common patterns, each answering a different question:

**Sequential by depth** — "how deep is this node?" Useful for showing hierarchy structure in treemaps where nesting is otherwise invisible:

```js
const color = d3.scaleSequential([0, root.height], d3.interpolateBlues);
cell.attr("fill", d => color(d.depth));
```

**Categorical by top-level ancestor** — "which branch does this belong to?" The most common treemap coloring. Use `.ancestors()` to find each leaf's top-level group:

```js
const topLevel = root.children || [root];
const color = d3.scaleOrdinal(topLevel.map(d => d.data.name), d3.schemeTableau10);
// For any node, walk up to depth-1 ancestor
const branch = d => d.ancestors().find(a => a.depth === 1)?.data.name;
cell.attr("fill", d => color(branch(d)))
    .attr("fill-opacity", d => 0.4 + 0.6 * (1 - d.depth / root.height));  // fade deeper nodes
```

**Diverging by change metric** — "what grew or shrank?" For treemaps comparing two time periods:

```js
const color = d3.scaleDiverging([-0.5, 0, 0.5], d3.interpolateRdBu);
cell.attr("fill", d => color(d.data.change));  // change = (new - old) / old
```

## Performance

**SVG vs Canvas threshold.** SVG treemaps work well up to ~500 nodes. Beyond that, DOM overhead causes sluggish interactions and slow initial render. Switch to Canvas for the data layer, keep SVG for labels and interaction overlays:

```js
// Canvas treemap rendering
const ctx = canvas.getContext("2d");
for (const d of root.leaves()) {
  ctx.fillStyle = color(d.data.category);
  ctx.fillRect(d.x0, d.y0, d.x1 - d.x0, d.y1 - d.y0);
  ctx.strokeRect(d.x0, d.y0, d.x1 - d.x0, d.y1 - d.y0);
}
// Hit detection: point-in-rectangle test on root.leaves()
```

**`.sum()` vs `.count()` performance.** Both are O(n) over all nodes. `.sum()` is marginally slower because it calls the accessor function — irrelevant for <10K nodes. For very large trees, avoid re-calling `.sum()` on every update if the accessor hasn't changed; cache the hierarchy object.

**Tiling strategy for animation.** `treemapResquarify` caches the first layout's topology, so subsequent `.tile()` calls only resize — no reordering. This makes transitions smooth. `treemapSquarify` recomputes ordering every time, causing cells to jump. Always use resquarify for animated treemaps.

**Pack layout is expensive.** Circle packing solves a non-trivial optimization problem. For >5K nodes, pre-compute the layout once and cache. For interactive filtering, recompute only the affected subtree if possible.

## Common Pitfalls

1. **Treemap `paddingTop` without labels.** Reserves space for group labels at the top of each cell. If you're not rendering labels there, it wastes space and creates a visual gap the viewer will try to interpret.

2. **Pack and treemap labels overlapping.** These layouts don't guarantee label space — cells and circles can be any size, and parent labels compete with children. Three strategies, from simplest to most robust:

   - **Constraint relaxation:** Run a force simulation on label positions after layout. Each label starts at its circle/cell center, a rectangular collision force pushes overlapping labels apart, an anchor force pulls them back, and a containment constraint keeps them inside their circle. Pre-compute synchronously (`sim.stop(); for 100 ticks`) — the viewer never sees labels jiggle. This produces the densest correct labeling because it finds positions that fit rather than hiding labels that don't. Uses `rectCollideForce` from the `annotation` skill. See `blocks/19-circle-packing-zoom.html`.
   - **Focus-level only:** Show labels only for the focused node and its direct children. At overview depth-0, only show depth-1 labels. When zoomed into a depth-1 node, show depth-2 labels. Eliminates overlap entirely but shows fewer labels. Best combined with constraint relaxation: focus-level selects *which* labels to show, relaxation decides *where* to place them.
   - **Measure and hide:** Approximate text width (`name.length * fontSize * 0.55`) and compare to container width (circle diameter or treemap cell width). Hide labels that don't fit. Simplest approach but still overlaps when siblings are close together.
   - **Hover labels:** Show labels only on hover/focus. Most scalable but loses the overview — the viewer must probe to discover what things are called. Best as a fallback for labels too small to place.

3. **Sunburst root fills center.** Partition allocates the full innermost ring to root, which carries no information. Filter it out: `.filter(d => d.depth > 0)`, or render as a small center circle for zoom-out navigation.

4. **Squarify for animated data.** Squarify reorders nodes to minimize aspect ratios, so cells jump to new positions when data changes. Switch to `treemapResquarify` for any treemap that transitions between data states.

5. **`.sum()` vs `.count()` confusion.** `.sum(d => d.value)` accumulates leaf values up the tree — internal node values are the sum of their descendants. `.count()` ignores data values entirely and counts leaves. If your treemap shows all cells the same size, you probably called `.count()` when you meant `.sum()`. If totals don't add up, check whether your accessor returns values for internal nodes (they get *added* to children's sum, not ignored).

6. **Negative values silently ignored by treemap.** If `.sum(d => d.profit)` encounters negative values, they become 0 in the layout — no warning, no error. The treemap just looks wrong. Check for negatives before layout: `root.leaves().filter(d => d.data.profit < 0)`. To show losses, encode sign as color and use absolute values for area: `.sum(d => Math.abs(d.profit))`.

7. **Stratify with missing parents throws cryptic error.** `d3.stratify()` throws `"missing: X"` when a parentId references an id not in the dataset, or `"ambiguous: X"` for duplicate ids. The error message doesn't say which row caused it. Always run validation first (see d3.stratify section above). Common causes: trailing whitespace in CSV ids (`"Sales "` vs `"Sales"`), null vs empty string for root's parentId, header row included in data.

## Observable Plot

For simple node-link trees from path-like data, Observable Plot's `Plot.tree()` mark handles stratify, links, and label placement declaratively. The D3 skill's value is in space-filling layouts, Canvas rendering, custom interactions, and the coordinate-system control that Plot abstracts away.

## References

- [D3 Hierarchy](https://d3js.org/d3-hierarchy)
- [Squarified Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — Bruls, Huizing & van Wijk (EuroVis 2000)
- [Treemaps for space-constrained visualization](http://www.cs.umd.edu/hcil/treemap-history/) — Shneiderman (1991)
- [Visualization of large hierarchical data by circle packing](https://dl.acm.org/doi/10.1145/1124772.1124851) — Wang et al. (CHI 2006)
- [Flame Graphs](https://www.brendangregg.com/flamegraphs.html) — Brendan Gregg
- [Perceptual Guidelines for Treemaps](https://doi.org/10.1109/TVCG.2010.186) — Kong et al. (aspect ratios near 1 minimize area judgment error)
