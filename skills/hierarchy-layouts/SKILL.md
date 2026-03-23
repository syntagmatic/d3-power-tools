---
name: hierarchy-layouts
description: "D3.js hierarchy layout computation and rendering: treemaps, sunburst, icicle, circle packing, dendrograms, radial trees, cluster layouts, and partition. Use this skill whenever the user wants to visualize tree-structured or nested data, convert tabular data to a hierarchy, choose a tiling strategy, render node-link diagrams, create space-filling layouts, place labels in hierarchy cells, or work with d3.hierarchy, d3.treemap, d3.pack, d3.tree, d3.cluster, d3.partition, or d3.stratify."
---

# Hierarchy Layouts

Patterns for computing and rendering D3 hierarchy layouts. Covers data preparation, all six layout algorithms, coordinate systems, link generators, labeling, and color encoding.

For interactive patterns (expand/collapse, zoomable drill-down), see the `hierarchy-interaction` skill.

## Data Preparation

### From Nested JSON

The most common input. `d3.hierarchy()` expects an object with a `children` array:

```js
const data = {
  name: "root",
  children: [
    { name: "A", children: [{ name: "A1", value: 10 }, { name: "A2", value: 20 }] },
    { name: "B", value: 30 }
  ]
};

const root = d3.hierarchy(data);
```

### From Tabular Data

Flat CSV/TSV with id and parent columns. `d3.stratify()` builds the tree:

```js
const table = [
  { id: "root", parent: "" },
  { id: "A",    parent: "root" },
  { id: "A1",   parent: "A", value: 10 },
  { id: "A2",   parent: "A", value: 20 },
  { id: "B",    parent: "root", value: 30 },
];

const root = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parent || null)(table);
```

### Data Validation

`d3.stratify()` throws unhelpful errors on bad input. Real-world tabular data often has issues that need handling before layout computation:

- **Duplicate IDs** — multiple rows share the same id
- **Orphaned nodes** — parent ID references a node that doesn't exist
- **Cycles** — A→B→C→A chains that make tree construction impossible
- **Multiple roots** — more than one node with no parent
- **No root** — every node has a parent, so there's no tree root

**Strategy:** Validate before calling `d3.stratify()`. Index all IDs in a Set, then check each parent reference against it. Detect cycles with DFS (gray/black coloring). When errors are found, recover with best-effort cleaning: deduplicate IDs (keep first), break cycles by detaching the back-edge node, graft orphans and extra roots onto a synthetic `__root__` node.

See [`scripts/validate-hierarchy.js`](scripts/validate-hierarchy.js) for a full `validateHierarchy()` / `cleanHierarchy()` implementation.

```js
const { valid, errors } = validateHierarchy(table);
if (!valid) {
  console.warn("Hierarchy issues:", errors);
  table = cleanHierarchy(table);
}
const root = d3.stratify().id(d => d.id).parentId(d => d.parent || null)(table);
```

### `.sum()` vs `.count()`

Space-filling layouts (treemap, pack, partition) need a `.value` on every node.

- **`.sum(accessor)`** — rolls up leaf values. The accessor runs on `.data`, not the node. Internal nodes get the sum of their descendants.
- **`.count()`** — sets each node's value to its number of leaves. Use when you want equal-area leaves regardless of data values.

```js
// Size by data value
root.sum(d => d.value || 0);

// Size by leaf count (equal area per leaf)
root.count();
```

**Gotcha:** `.sum()` visits nodes bottom-up. If your accessor returns a value for internal nodes, those values are *added* to the children's sum — they don't replace it. To size only by leaves, return 0 for nodes with children:

```js
root.sum(d => d.children ? 0 : d.value);
```

### Sorting

Sorting affects visual order in all layouts. Sort after `.sum()` since sort callbacks often use `.value`:

```js
root.sort((a, b) => b.value - a.value);       // largest first
root.sort((a, b) => b.height - a.height        // deepest subtrees first
  || b.value - a.value);                        // then by value
root.sort((a, b) => d3.ascending(a.data.name, b.data.name)); // alphabetical
```

## Node-Link Layouts

### `d3.tree()` — Tidy Tree

Produces a tidy node-link diagram. All nodes at the same depth are aligned. The Reingold-Tilford algorithm minimizes width while keeping subtrees compact.

```js
const treeLayout = d3.tree().size([height, width - 160]);
treeLayout(root);

// Horizontal tree: d.y = horizontal position, d.x = vertical position
// (d3.tree uses [x, y] = [cross-axis, main-axis] convention)

const link = svg.selectAll("path.link")
  .data(root.links())
  .join("path")
    .attr("class", "link")
    .attr("fill", "none")
    .attr("stroke", "#999")
    .attr("d", d3.linkHorizontal().x(d => d.y).y(d => d.x));

const node = svg.selectAll("g.node")
  .data(root.descendants())
  .join("g")
    .attr("class", "node")
    .attr("transform", d => `translate(${d.y},${d.x})`);

node.append("circle").attr("r", 4);
node.append("text")
  .attr("dx", d => d.children ? -8 : 8)
  .attr("text-anchor", d => d.children ? "end" : "start")
  .text(d => d.data.name);
```

### `d3.cluster()` — Dendrogram

Like `d3.tree()` but all leaves are placed at the same depth. Useful for phylogenetic trees and dendrograms where leaf alignment matters.

```js
const cluster = d3.cluster().size([height, width - 160]);
cluster(root);
// Same rendering as tree — only positions differ
```

### Radial Tree / Cluster

Pass `[2 * Math.PI, radius]` as the size. The layout computes angle (`d.x`) and radius (`d.y`):

```js
const tree = d3.tree()
  .size([2 * Math.PI, radius - 100])
  .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);

tree(root);

const link = svg.selectAll("path.link")
  .data(root.links())
  .join("path")
    .attr("fill", "none")
    .attr("stroke", "#999")
    .attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y));

const node = svg.selectAll("g.node")
  .data(root.descendants())
  .join("g")
    .attr("transform", d =>
      `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`);

node.append("circle").attr("r", 3);
node.append("text")
  .attr("dy", "0.31em")
  .attr("x", d => d.x < Math.PI === !d.children ? 6 : -6)
  .attr("text-anchor", d => d.x < Math.PI === !d.children ? "start" : "end")
  .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
  .text(d => d.data.name);
```

### `.separation()`

Controls spacing between adjacent nodes. The default `(a, b) => a.parent === b.parent ? 1 : 2` gives wider gaps between different subtrees. For radial layouts, dividing by depth prevents outer levels from being too spread out.

### Link Generators

| Generator | Use case | Accessors |
|-----------|----------|-----------|
| `d3.linkHorizontal()` | Horizontal tree | `.x(d => d.y).y(d => d.x)` |
| `d3.linkVertical()` | Vertical tree | `.x(d => d.x).y(d => d.y)` |
| `d3.linkRadial()` | Radial tree/cluster | `.angle(d => d.x).radius(d => d.y)` |

These produce cubic Bezier curves. For straight lines, use `d3.line()` or a path `M...L...` instead.

## Space-Filling Layouts

### `d3.treemap()`

Fills a rectangle with nested rectangles. Area encodes value.

```js
const treemap = d3.treemap()
  .size([width, height])
  .paddingInner(1)
  .paddingOuter(3)
  .paddingTop(19)    // space for group labels
  .round(true);

const root = treemap(d3.hierarchy(data).sum(d => d.value).sort((a, b) => b.value - a.value));

const cell = svg.selectAll("g")
  .data(root.leaves())  // or root.descendants() to show groups
  .join("g")
    .attr("transform", d => `translate(${d.x0},${d.y0})`);

cell.append("rect")
  .attr("width", d => d.x1 - d.x0)
  .attr("height", d => d.y1 - d.y0)
  .attr("fill", d => color(d.parent.data.name));

cell.append("text")
  .selectAll("tspan")
  .data(d => d.data.name.split(/(?=[A-Z][a-z])/))
  .join("tspan")
    .attr("x", 3)
    .attr("y", (d, i) => 13 + i * 10)
    .text(d => d);
```

#### Tiling Strategies

```js
treemap.tile(d3.treemapSquarify);      // default — good aspect ratios
treemap.tile(d3.treemapBinary);        // balanced binary split
treemap.tile(d3.treemapSlice);         // horizontal slices only
treemap.tile(d3.treemapDice);          // vertical slices only
treemap.tile(d3.treemapSliceDice);     // alternates by depth
treemap.tile(d3.treemapResquarify);    // stable on data updates (for animation)
```

**When to use which:**
- **Squarify** (default): best for static treemaps — minimizes aspect ratios, cells are readable
- **Resquarify**: same as squarify but preserves node order across updates — essential for animated treemaps
- **Binary**: balanced splits, moderate aspect ratios, stable ordering
- **SliceDice**: preserves ordering and adjacency — useful when spatial position has meaning
- **Slice/Dice**: rarely used alone, but the building blocks for custom strategies

#### Padding

- `paddingInner(px)` — gap between sibling cells
- `paddingOuter(px)` — gap between cell edges and parent boundary
- `paddingTop(px)` — extra top padding for parent labels
- `padding(px)` — sets inner and outer at once

### `d3.pack()` — Circle Packing

Enclosing circles show hierarchy through nesting. Area encodes value.

```js
const pack = d3.pack()
  .size([width, height])
  .padding(3);

const root = pack(d3.hierarchy(data).sum(d => d.value).sort((a, b) => b.value - a.value));

const node = svg.selectAll("circle")
  .data(root.descendants())
  .join("circle")
    .attr("cx", d => d.x)
    .attr("cy", d => d.y)
    .attr("r", d => d.r)
    .attr("fill", d => d.children ? "none" : color(d.data.name))
    .attr("stroke", d => d.children ? "#999" : null);
```

Circle packing wastes more space than treemaps but reveals the hierarchy structure more clearly — you can see nesting at a glance.

### `d3.partition()` — Icicle and Sunburst

Partition divides space by depth (rings or rows) then subdivides by value. The same layout produces both icicle (Cartesian) and sunburst (polar) depending on coordinate mapping.

#### Icicle (Cartesian)

```js
const partition = d3.partition()
  .size([width, height])
  .padding(1);

const root = partition(d3.hierarchy(data).sum(d => d.value));

svg.selectAll("rect")
  .data(root.descendants())
  .join("rect")
    .attr("x", d => d.x0)
    .attr("y", d => d.y0)
    .attr("width", d => d.x1 - d.x0)
    .attr("height", d => d.y1 - d.y0)
    .attr("fill", d => color(d.data.name));
```

#### Sunburst (Polar)

Map `x` to angle, `y` to radius:

```js
const partition = d3.partition()
  .size([2 * Math.PI, radius]);

const root = partition(d3.hierarchy(data).sum(d => d.value));

const arc = d3.arc()
  .startAngle(d => d.x0)
  .endAngle(d => d.x1)
  .padAngle(d => Math.min((d.x1 - d.x0) / 2, 0.005))
  .padRadius(radius / 2)
  .innerRadius(d => d.y0)
  .outerRadius(d => d.y1 - 1);

svg.append("g")
  .attr("transform", `translate(${width / 2},${height / 2})`)
  .selectAll("path")
  .data(root.descendants().filter(d => d.depth))  // skip root
  .join("path")
    .attr("d", arc)
    .attr("fill", d => { while (d.depth > 1) d = d.parent; return color(d.data.name); });
```

**Tip:** Apply a `d3.scaleSqrt` or `d3.scalePow` to the radial dimension so outer rings don't dominate visually:

```js
const y = d3.scaleSqrt().domain([0, radius]).range([0, radius]);
arc.innerRadius(d => y(d.y0)).outerRadius(d => y(d.y1) - 1);
```

## Labels

### Treemap Cell Labels

Fit text inside rectangles. Clip or hide labels that don't fit:

```js
cell.append("text")
  .attr("clip-path", d => `inset(0 ${d.x1 - d.x0}px ${d.y1 - d.y0}px 0)`)
  .selectAll("tspan")
  .data(d => d.data.name.split(/\s+/))
  .join("tspan")
    .attr("x", 3)
    .attr("y", (d, i) => 13 + i * 12)
    .text(d => d);

// Hide labels in cells that are too small
cell.select("text")
  .attr("display", d => (d.x1 - d.x0 > 40 && d.y1 - d.y0 > 14) ? null : "none");
```

### Radial Labels

Labels in radial layouts need rotation and flipping so they're always readable:

```js
node.append("text")
  .attr("transform", d => {
    const angle = d.x * 180 / Math.PI;
    // Flip labels on the left half so they read left-to-right
    return d.x < Math.PI
      ? `rotate(${angle - 90}) translate(${d.y + 6},0)`
      : `rotate(${angle + 90}) translate(${-d.y - 6},0)`;
  })
  .attr("text-anchor", d => d.x < Math.PI ? "start" : "end")
  .text(d => d.data.name);
```

### Sunburst Arc Labels

Place text along the arc midpoint, rotated to follow the ring. Calculate visibility based on available arc length to prevent overlap:

```js
label.attr("transform", d => {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
  const y = (d.y0 + d.y1) / 2;
  return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
})
.attr("text-anchor", "middle")
.attr("opacity", d => {
  // Hide labels for small arcs (arc length < 40px)
  const arcLength = (d.x1 - d.x0) * (d.y0 + d.y1) / 2;
  return arcLength > 40 ? 1 : 0;
});
```

## Color Encoding

### By Group (Top-Level Ancestor)

The most common pattern — all nodes in a subtree share a color:

```js
const color = d3.scaleOrdinal(d3.schemeTableau10);

function groupColor(d) {
  while (d.depth > 1) d = d.parent;
  return color(d.data.name);
}
```

### By Depth

Show hierarchy level:

```js
const color = d3.scaleSequential([0, root.height], d3.interpolateBlues);
// Usage: color(d.depth)
```

### By Value

Encode a metric in color. Works well with space-filling layouts where area already shows one variable:

```js
const color = d3.scaleSequential(d3.extent(root.leaves(), d => d.data.rate), d3.interpolateRdYlGn);
// Usage: color(d.data.rate)
```

### Depth-Faded Opacity

Layer opacity by depth for visual hierarchy — parent groups are lighter, leaves are fully opaque:

```js
const opacity = d3.scaleLinear([0, root.height], [0.3, 1]);
// Usage: .attr("opacity", d => opacity(d.depth))
```

## Hierarchy Traversal

Useful methods on `d3.hierarchy` nodes:

```js
node.ancestors()     // [node, parent, ..., root]
node.descendants()   // [node, ...all children recursively]
node.leaves()        // leaf descendants only
node.links()         // [{source, target}, ...] for all parent-child edges
node.path(other)     // path from node up to LCA and down to other
node.find(fn)        // first descendant matching predicate (D3 v7.1+)

node.depth           // distance from root (root = 0)
node.height          // distance to deepest leaf (leaves = 0)
```

### Walking the Tree

```js
root.each(d => { ... })        // breadth-first
root.eachBefore(d => { ... })  // pre-order depth-first (parent before children)
root.eachAfter(d => { ... })   // post-order depth-first (children before parent)
```

Use `eachAfter` when computing bottom-up aggregates. Use `eachBefore` when propagating top-down properties.

## Jump-Free Transitions

When transitioning between radial (Sunburst) and cartesian (Treemap/Icicle) layouts, the container `<g>` position often jumps because arcs draw relative to their center while rectangles draw relative to their origin.

**The Fix:** Smoothly interpolate the `<g>` to the new centroid, and use a compensating transform on the `<path>` during the "arc phase" to keep it centered at the original `(cx, cy)`.

```js
// Smooth <g> transition
node.transition(t).attr("transform", d => `translate(${d.target_x},${d.target_y})`);

// Compensating <path> transition
path.transition(t)
  .attrTween("transform", (d) => (time) => {
    if (inArcPhase) {
      const curX = interpolateX(time);
      const curY = interpolateY(time);
      return `translate(${cx - curX}, ${cy - curY})`;
    }
    return "translate(0,0)";
  });
```

## Common Pitfalls

1. **Forgetting `.sum()` or `.count()`.** Treemap, pack, and partition require `.value` on every node. Without it, all cells have zero area. The layout runs but produces nothing visible.

2. **`.sum()` accessor gets `.data`, not the node.** Write `d => d.value`, not `d => d.data.value`. The accessor receives the raw data object, not the hierarchy node.

3. **Sorting before `.sum()`.** Sort callbacks often use `node.value`, which isn't set until `.sum()` runs. Always `.sum()` first, then `.sort()`.

4. **Tree/cluster `size` convention.** `d3.tree().size([crossAxis, mainAxis])`. For a horizontal tree: `.size([height, width])`, then use `d.y` for horizontal and `d.x` for vertical position. This is confusing but intentional — it matches the mathematical convention.

5. **Radial coordinate transform.** The layout gives angle in `d.x` and radius in `d.y`. Convert with: `x = d.y * Math.cos(d.x - Math.PI/2)`, `y = d.y * Math.sin(d.x - Math.PI/2)`. The `-Math.PI/2` rotates so angle 0 points up.

6. **Treemap `paddingTop` without group labels.** `paddingTop` reserves space at the top of each internal node's rectangle. If you're not rendering group labels there, it's wasted space. Use `paddingInner` and `paddingOuter` instead.

7. **Circle pack labels overlapping.** Pack doesn't guarantee space for labels. Either show labels only for a certain depth range, clip to the circle, or only label on hover.

8. **Partition root filling the center.** In sunburst, the root arc fills the entire inner circle. Filter it out: `.filter(d => d.depth > 0)`, or render it as a small center circle for "zoom out" navigation.

9. **`d3.stratify` parent ID for root.** The root node must have a null or empty parent ID. If your CSV has the root's parent as an empty string, use `.parentId(d => d.parent || null)`.

## References

- [D3 Hierarchy documentation](https://d3js.org/d3-hierarchy) — Mike Bostock's API reference for all hierarchy layouts
- [Treemaps for space-constrained visualization of hierarchies](http://www.cs.umd.edu/hcil/treemap-history/) — Ben Shneiderman's original treemap research (University of Maryland, 1991)
- [Squarified Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — Mark Bruls, Kees Huizing & Jarke van Wijk's squarify algorithm (EuroVis 2000)
- [Tidy Trees](https://observablehq.com/@d3/tree) — Reingold–Tilford tree layout
- [Circle Packing](https://observablehq.com/@d3/circle-packing) — canonical pack layout
- [Sunburst](https://observablehq.com/@d3/sunburst) — partition-based radial layout
- [Icicle](https://observablehq.com/@d3/icicle) — rectangular partition layout
