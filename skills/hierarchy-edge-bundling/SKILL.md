---
name: hierarchy-edge-bundling
description: "Hierarchical edge bundling for D3.js: visualize connections between leaf nodes in a hierarchy by routing edges through least common ancestors with d3.curveBundle. Use this skill whenever the user wants to build a hierarchical edge bundling diagram, radial dendrograms with bundled connections, dependency graphs, import/export visualizations, package dependency wheels, software architecture diagrams showing module relationships, or any visualization that combines tree structure with cross-links between leaves. Covers d3.cluster radial layout, node.path() for LCA routing, d3.curveBundle.beta() tension control, SVG and Canvas rendering of bundled curves, interactive highlighting, data preparation from flat dependency lists, and animated layout transitions (bundle↔pack↔treemap↔tree) with continuous edge redrawing via data-space interpolation."
---

# Hierarchical Edge Bundling

Patterns for visualizing connections between nodes in a hierarchy by routing edges through the tree structure. Reduces visual clutter by bundling edges that share common ancestors, revealing high-level connection patterns between groups.

The canonical reference is Danny Holten's 2006 paper. D3's implementation uses `d3.cluster` for radial leaf placement and `d3.curveBundle` for tension-controlled bundling through LCA paths.

For hierarchy construction and layout details, see the `hierarchy-layouts` skill. For canvas performance patterns, see `canvas`. For advanced highlight/selection patterns, see `brushing`.

## Core Concept

Three ingredients:

1. **A hierarchy** — tree structure placing nodes in groups
2. **Cross-links** — connections between leaf nodes (imports, dependencies, calls)
3. **LCA routing** — each edge routes through the least common ancestor of its endpoints

Edges between leaves in the same subtree bundle tightly; edges between distant subtrees fan out through higher ancestors.

## Data Preparation

Two inputs: a hierarchy and a connection list referencing leaf IDs.

```js
// Hierarchy — flat with parent references
const nodes = [
  { id: "root", parent: "" },
  { id: "vis", parent: "root" },
  { id: "vis.chart", parent: "vis" },
  { id: "vis.bindAxis", parent: "vis" },
  { id: "data", parent: "root" },
  { id: "data.loader", parent: "data" },
];

// Connections between leaves
const connections = [
  { source: "vis.chart", target: "data.loader" },
  { source: "vis.bindAxis", target: "vis.chart" },
];
```

### Computing LCA Paths

`node.path(target)` returns every node from source up to the LCA and back down to target. This array becomes the control points for the bundled curve.

```js
const root = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parent || null)(nodes);

const nodesById = new Map(root.descendants().map(d => [d.data.id, d]));

const links = connections.map(c => {
  const source = nodesById.get(c.source);
  const target = nodesById.get(c.target);
  return source && target ? source.path(target) : null;
}).filter(Boolean);
// Each link: [leaf1, parent1, grandparent, parent2, leaf2]
```

**Gotcha:** If source/target IDs don't match hierarchy nodes, you get silent nulls. Always filter and log mismatches during development.

## Radial Layout

The classic presentation places leaves around a circle using `d3.cluster` with radial coordinates. See `hierarchy-layouts` for radial coordinate details and label flipping.

```js
const radius = Math.min(width, height) / 2;

const cluster = d3.cluster()
  .size([2 * Math.PI, radius - 140])
  .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);

cluster(root);

const g = svg.append("g")
  .attr("transform", `translate(${width / 2},${height / 2})`);

// Only render leaves — internal nodes are invisible routing waypoints
const nodeSelection = g.selectAll("g.node")
  .data(root.leaves())
  .join("g")
    .attr("class", "node")
    .attr("transform", d => {
      const angle = d.x * 180 / Math.PI - 90;
      return `rotate(${angle}) translate(${d.y},0)`;
    });

nodeSelection.append("circle").attr("r", 3);
nodeSelection.append("text")
  .attr("dy", "0.31em")
  .attr("x", d => d.x < Math.PI ? 6 : -6)
  .attr("text-anchor", d => d.x < Math.PI ? "start" : "end")
  .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
  .text(d => d.data.id.split(".").pop());
```

## Edge Bundling with `d3.curveBundle`

`d3.curveBundle.beta(β)` is a B-spline variant where the control points are the LCA path nodes.

```js
const tension = 0.85;  // 0 = straight lines, 1 = maximum bundling
const beta = 1 - tension;

const line = d3.lineRadial()
  .curve(d3.curveBundle.beta(beta))
  .radius(d => d.y)
  .angle(d => d.x);
```

**Tension semantics:**
- `tension = 0` → `beta = 1` → straight lines between endpoints
- `tension = 0.85` → `beta = 0.15` → tight bundling (good default)
- `tension = 1` → `beta = 0` → curves follow tree edges exactly

### SVG Rendering

```js
const linkSelection = g.selectAll("path.link")
  .data(links)
  .join("path")
    .attr("class", "link")
    .attr("fill", "none")
    .attr("stroke", "#888")
    .attr("stroke-opacity", 0.3)
    .attr("d", line);
```

### Canvas Rendering

For >200 edges, canvas is faster. `.context(ctx)` makes the line generator write `moveTo`/`bezierCurveTo` calls directly onto the canvas context:

```js
function drawLinks(ctx, links, tension) {
  const beta = 1 - tension;
  const line = d3.line()
    .curve(d3.curveBundle.beta(beta))
    .x(d => d.cx).y(d => d.cy)
    .context(ctx);

  ctx.save();
  ctx.translate(width / 2, height / 2);
  ctx.strokeStyle = "rgba(136, 136, 136, 0.3)";
  ctx.lineWidth = 1;
  for (const link of links) {
    ctx.beginPath();
    line(link);
    ctx.stroke();
  }
  ctx.restore();
}
```

For Cartesian (non-radial) layouts, use `d3.line` instead of `d3.lineRadial` — same LCA paths, different coordinate accessors.

### Tension Slider

```js
d3.select("#tension").on("input", function() {
  const tension = +this.value / 100;
  line.curve(d3.curveBundle.beta(1 - tension));
  linkSelection.attr("d", line);  // SVG
  // Canvas: clear and call drawLinks()
});
```

## Interaction: Highlighting Connections

An edge connects to a node if either endpoint leaf is a descendant of that node:

```js
function getConnectedLinks(node, links) {
  const leafIds = new Set(node.leaves().map(d => d.data.id));
  return links.filter(link => {
    const sourceId = link[0].data.id;
    const targetId = link[link.length - 1].data.id;
    return leafIds.has(sourceId) || leafIds.has(targetId);
  });
}
```

### SVG Highlighting

```js
nodeSelection
  .on("mouseover", (event, d) => {
    const connected = getConnectedLinks(d, links);
    const connectedIds = new Set();
    connected.forEach(l => {
      connectedIds.add(l[0].data.id);
      connectedIds.add(l[l.length - 1].data.id);
    });

    linkSelection.classed("link--faded", true);
    nodeSelection.classed("node--faded", true);
    linkSelection.filter(l => connected.includes(l))
      .classed("link--faded", false).classed("link--highlighted", true).raise();
    nodeSelection.filter(n => connectedIds.has(n.data.id))
      .classed("node--faded", false).classed("node--highlighted", true);
  })
  .on("mouseout", () => {
    linkSelection.classed("link--faded link--highlighted", false);
    nodeSelection.classed("node--faded node--highlighted", false);
  });
```

```css
.link { stroke: #888; stroke-opacity: 0.3; }
.link--highlighted { stroke: #e03131; stroke-opacity: 0.8; stroke-width: 1.5; }
.link--faded { stroke-opacity: 0.05; }
.node text { fill: #333; font-size: 10px; }
.node--highlighted text { fill: #e03131; font-weight: 600; }
.node--faded text { fill-opacity: 0.2; }
```

For canvas highlighting, render in two passes (faded first, highlighted on top). See `canvas` for batched draw patterns and `brushing` for advanced highlight state management.

## Color by Group

Color nodes and edges by top-level ancestor. See `hierarchy-layouts` for the `groupOf` pattern. For edge bundling, apply to edges by source group:

```js
link.attr("stroke", d => color(groupOf(d[0])));
```

## Structural Context

Edge bundling is most effective when the underlying hierarchy is also visible. In Treemaps or Circle Packs, render the structural rectangles or circles behind the nodes and links.

```js
// Add background rectangles for treemap context
nodeSelection.append("rect")
  .attr("class", "bg")
  .attr("fill", "#555")
  .attr("fill-opacity", 0.05)
  .attr("x", d => -d.current_w / 2)
  .attr("y", d => -d.current_h / 2)
  .attr("width", d => d.current_w || 0)
  .attr("height", d => d.current_h || 0);
```

## Layout Transitions with Bundled Edges

Edge bundling works with any hierarchy layout. The key insight: interpolate node positions in data space (`current_x`/`current_y` on the hierarchy nodes), then re-derive the bundled curves each frame as a downstream effect. The LCA paths never change — only the positions of the nodes they pass through.

### Data-Space Interpolation

Standard D3 transitions interpolate screen-space attributes (SVG `d`, `transform`). For bundled edges, interpolate the data-space coordinates instead and let the line generator recompute paths each frame:

```js
function transitionToLayout(layoutFn) {
  // 1. Snapshot current positions
  root.each(d => { d.source_x = d.current_x; d.source_y = d.current_y; });

  // 2. Compute new layout → target positions
  layoutFn(root);
  root.each(d => {
    // Convert radial layouts to cartesian
    if (layoutFn === cluster) {
      d.target_x = d.y * Math.cos(d.x - Math.PI / 2);
      d.target_y = d.y * Math.sin(d.x - Math.PI / 2);
    } else {
      d.target_x = d.x;
      d.target_y = d.y;
    }
  });

  // 3. Interpolate data-space positions, redraw curves each frame
  const t = svg.transition().duration(1200).ease(d3.easeCubicInOut);
  t.tween("layout", () => time => {
    root.each(d => {
      d.current_x = d.source_x + (d.target_x - d.source_x) * time;
      d.current_y = d.source_y + (d.target_y - d.source_y) * time;
    });
    redrawNodes();
    redrawLinks();  // bundle curves recomputed from current_x/y
  });
}
```

### Cartesian Line Generator

During transitions (and for non-radial layouts), use `d3.line` with `current_x`/`current_y` instead of `d3.lineRadial`:

```js
const cartesianLine = d3.line()
  .curve(d3.curveBundle.beta(1 - tension))
  .x(d => d.current_x)
  .y(d => d.current_y);

function redrawLinks() {
  linkSelection.attr("d", cartesianLine);
}
```

### Internal Nodes as Routing Waypoints

Internal nodes must have interpolated positions even though they may not be visible. In the bundle layout, they sit along the radial hierarchy with `r = 0`. In pack or treemap, they occupy their layout-computed position. During transitions, their smooth movement is what makes the bundled curves deform naturally.

### Layout-Specific Position Mapping

Each layout produces different coordinate semantics. Convert everything to a common cartesian `target_x`/`target_y`:

```js
function computeTargets(layout) {
  root.each(d => {
    switch (layout) {
      case "bundle":   // radial: leaves on ring, internals along hierarchy
      case "cluster":  // radial: d.x = angle, d.y = radius
        d.target_x = d.y * Math.cos(d.x - Math.PI / 2);
        d.target_y = d.y * Math.sin(d.x - Math.PI / 2);
        break;
      case "tree":     // cartesian: d.x = cross-axis, d.y = main-axis
        d.target_x = d.y;  // horizontal tree
        d.target_y = d.x;
        break;
      case "pack":     // cartesian: d.x, d.y = circle center
        d.target_x = d.x - width / 2;
        d.target_y = d.y - height / 2;
        break;
      case "treemap":  // cartesian: d.x0/y0/x1/y1 = rect bounds
        d.target_x = (d.x0 + d.x1) / 2 - width / 2;
        d.target_y = (d.y0 + d.y1) / 2 - height / 2;
        break;
    }
  });
}
```

### Why This Works

The bundle curve is a pure function of its control point positions. Since LCA paths are fixed (they depend on tree structure, not layout), interpolating the control points smoothly deforms the curves. No path morphing library needed — just move the points, redraw the curves.

## Performance

| Edge count | Approach |
|---|---|
| < 200 | SVG with CSS transitions |
| 200–2,000 | SVG, low `stroke-opacity` to manage overdraw |
| 2,000–50,000 | Canvas with `.context(ctx)` |
| 50,000+ | Canvas + Web Worker for path computation |

## Common Pitfalls

1. **Mismatched IDs between hierarchy and connections.** Source/target must exactly match leaf node IDs. `"vis.chart"` vs `"root.vis.chart"` silently drops edges.

2. **`d3.cluster` vs `d3.tree`.** Use `d3.cluster` — it places all leaves at the same radius. `d3.tree` spreads leaves at varying depths, breaking the radial ring.

3. **Beta vs tension confusion.** `d3.curveBundle.beta(β)` where `β = 1 - tension`. High tension = low beta = tight bundling.

4. **Not calling `.raise()` on highlighted links.** Highlighted links render behind faded ones without it. Always `.raise()` (SVG) or draw highlighted in a second pass (canvas).

5. **Labels overlapping at high node counts.** Above ~100 leaves, radial labels collide. Show labels only on hover, increase radius, or filter to every Nth label.

6. **Internal nodes visible as dots.** Only leaves should render. Internal nodes are routing waypoints. Filter to `root.leaves()` for the node selection.

7. **Missing `.separation()` on radial cluster.** Without `(a, b) => (a.parent === b.parent ? 1 : 2) / a.depth`, deeper levels get too much angular space.

8. **Bundling non-leaf connections.** The classic technique assumes leaf-to-leaf connections. Internal node connections produce short paths with minimal bundling.

## References

- [Hierarchical Edge Bundles: Visualization of Adjacency Relations in Hierarchical Data](https://doi.org/10.1109/TVCG.2006.147) — Danny Holten's original paper introducing the technique (IEEE InfoVis 2006)
- [Hierarchical Edge Bundling](https://observablehq.com/@d3/hierarchical-edge-bundling) — Mike Bostock's canonical D3 implementation
- [D3 Hierarchy documentation](https://d3js.org/d3-hierarchy) — API reference for `d3.cluster`, `d3.hierarchy`, and tree traversal
- [D3 Curve Bundle](https://d3js.org/d3-shape/curve#curveBundle) — `d3.curveBundle.beta()` API for controlling bundling tension
- [Force-Directed Edge Bundling](https://doi.org/10.1111/j.1467-8659.2009.01450.x) — Danny Holten & Jarke van Wijk's follow-up technique that doesn't require hierarchy (EuroVis 2009)
- [Radial Dendrogram](https://observablehq.com/@d3/radial-dendrogram) — radial cluster layout, the base for bundled edge visualizations
