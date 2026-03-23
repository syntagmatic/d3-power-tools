---
name: network-visualization
description: "D3.js network and graph visualization: node-link diagrams, adjacency matrices, arc diagrams, chord diagrams, and Sankey flow diagrams. Use this skill whenever the user wants to visualize relationships, dependencies, flows, or connections between entities. Also use when the user mentions network graph, graph layout, adjacency matrix, arc diagram, d3.chord, d3.ribbon, d3.sankey, flow diagram, dependency graph, node-link, or wants to choose between different graph visualization types."
---

# Network Visualization

Patterns for visualizing graph and network data with D3. Covers data preparation, five major layout types, and guidance on choosing between them.

For force-directed node positioning and simulation tuning, see the `force-simulation` skill. For hierarchical edge bundling, see `hierarchy-edge-bundling`.

## Graph Data Preparation

> **Always validate first.** Real-world network data has dangling references, self-loops, duplicate edges, and disconnected components. Run [`validateNetwork()`](scripts/validate-network.js) before any layout — it catches issues that cause silent rendering bugs. See the [Data Validation](#data-validation) section below.

### Edge List

The most common input — an array of `{ source, target }` objects:

```js
const links = [
  { source: "Alice", target: "Bob", weight: 3 },
  { source: "Bob", target: "Carol", weight: 1 },
  { source: "Alice", target: "Carol", weight: 2 },
];
```

Extract unique nodes from edges:

```js
const nodeIds = new Set(links.flatMap(d => [d.source, d.target]));
const nodes = Array.from(nodeIds, id => ({ id }));
```

### Adjacency List

When the source data is node-centric (each node lists its connections):

```js
const adjList = [
  { id: "Alice", connections: ["Bob", "Carol"] },
  { id: "Bob", connections: ["Carol"] },
];

// Convert to edge list
const links = adjList.flatMap(d =>
  d.connections.map(target => ({ source: d.id, target }))
);
```

### Adjacency Matrix

A 2D array where `matrix[i][j]` represents the connection weight from node `i` to node `j`. Some data arrives in this format (e.g., correlation matrices, migration tables):

```js
// Convert matrix to edge list (skip zero/null entries)
const links = [];
matrix.forEach((row, i) => {
  row.forEach((value, j) => {
    if (value && i !== j) links.push({ source: names[i], target: names[j], value });
  });
});
```

### Data Validation

Network data from real sources often has issues: dangling edge references, self-loops, duplicate edges, disconnected components. Validate before layout:

```js
const { valid, errors } = validateNetwork({ nodes, links });
if (!valid) {
  console.warn("Network issues:", errors);
  ({ nodes, links } = cleanNetwork({ nodes, links }));
}
```

See [`scripts/validate-network.js`](scripts/validate-network.js) for the full `validateNetwork()` / `cleanNetwork()` implementation. Detects: duplicate node IDs, dangling source/target references, self-loops, duplicate edges, invalid/negative weights, disconnected components, and isolated nodes. Cleaning adds missing nodes, removes self-loops, deduplicates edges, and clamps bad weights.

### Computing Degree and Metrics

Degree (number of connections) is the most useful derived metric for sizing and filtering:

```js
const degree = new Map();
links.forEach(d => {
  degree.set(d.source, (degree.get(d.source) || 0) + 1);
  degree.set(d.target, (degree.get(d.target) || 0) + 1);
});
nodes.forEach(d => { d.degree = degree.get(d.id) || 0; });
```

## Node-Link Diagrams

The default network visualization — nodes as circles, edges as lines. Uses `d3.forceSimulation` for layout.

### Basic Setup

```js
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(60))
  .force("charge", d3.forceManyBody().strength(-100))
  .force("center", d3.forceCenter(width / 2, height / 2));

// Links — draw first so they appear behind nodes
const link = svg.selectAll(".link")
  .data(links).join("line")
  .attr("class", "link")
  .attr("stroke", "#999")
  .attr("stroke-opacity", 0.6)
  .attr("stroke-width", d => Math.sqrt(d.weight || 1));

// Nodes
const node = svg.selectAll(".node")
  .data(nodes).join("circle")
  .attr("class", "node")
  .attr("r", d => Math.sqrt(d.degree + 1) * 3)
  .attr("fill", d => color(d.group))
  .call(drag(simulation)); // see force-simulation skill for drag function

// Labels
const label = svg.selectAll(".label")
  .data(nodes.filter(d => d.degree > 3)).join("text")
  .attr("class", "label")
  .attr("text-anchor", "middle")
  .attr("dy", d => -Math.sqrt(d.degree + 1) * 3 - 4)
  .text(d => d.id);

simulation.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("cx", d => d.x).attr("cy", d => d.y);
  label.attr("x", d => d.x).attr("y", d => d.y);
});
```

### Curved Links and Multi-Edges

When there are multiple edges between the same pair of nodes, offset them with curves:

```js
// Detect parallel edges
const linkCounts = new Map();
links.forEach(d => {
  const key = [d.source.id, d.target.id].sort().join("--");
  linkCounts.set(key, (linkCounts.get(key) || 0) + 1);
});

// Draw as paths with curvature
link.attr("d", d => {
  const dx = d.target.x - d.source.x;
  const dy = d.target.y - d.source.y;
  const dr = Math.sqrt(dx * dx + dy * dy) * (d.curveOffset || 1);
  return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
});
```

### Directional Edges

For directed graphs, add arrowheads via SVG markers:

```js
svg.append("defs").selectAll("marker")
  .data(["arrow"]).join("marker")
  .attr("id", "arrow")
  .attr("viewBox", "0 -5 10 10")
  .attr("refX", 15)        // offset from node center by node radius
  .attr("refY", 0)
  .attr("markerWidth", 6)
  .attr("markerHeight", 6)
  .attr("orient", "auto")
  .append("path")
  .attr("d", "M0,-5L10,0L0,5")
  .attr("fill", "#999");

link.attr("marker-end", "url(#arrow)");
```

**Gotcha:** `refX` must account for the target node's radius, or the arrow tip will be hidden inside the node circle. Scale `refX` based on the target node's radius:

```js
.attr("refX", d => radiusScale(d.target.degree) + 10)
```

## Adjacency Matrix

An `n x n` grid where cell `(i, j)` represents the edge from node `i` to node `j`. Better than node-link for dense graphs (>50% edge density) where hairball node-link diagrams become unreadable.

```js
const n = nodes.length;
const cellSize = Math.min((width - margin.left - margin.right) / n, 20);

// Build matrix from edge list
const matrix = Array.from({ length: n }, () => new Array(n).fill(0));
const nodeIndex = new Map(nodes.map((d, i) => [d.id, i]));
links.forEach(d => {
  const i = nodeIndex.get(d.source), j = nodeIndex.get(d.target);
  if (i !== undefined && j !== undefined) {
    matrix[i][j] = d.weight || 1;
    matrix[j][i] = d.weight || 1; // symmetric for undirected
  }
});

// Sort nodes for visual structure — by cluster, then by degree
const order = d3.range(n).sort((a, b) =>
  d3.ascending(nodes[a].group, nodes[b].group) || d3.descending(nodes[a].degree, nodes[b].degree)
);

const colorScale = d3.scaleSequential(d3.interpolateBlues)
  .domain([0, d3.max(matrix.flat())]);

// Rows
const row = svg.selectAll(".row")
  .data(order).join("g")
  .attr("class", "row")
  .attr("transform", (d, i) => `translate(${margin.left},${margin.top + i * cellSize})`);

// Cells
row.selectAll(".cell")
  .data((rowIdx) => order.map((colIdx) => ({
    row: rowIdx, col: colIdx, value: matrix[rowIdx][colIdx]
  }))).join("rect")
  .attr("class", "cell")
  .attr("x", (d, i) => i * cellSize)
  .attr("width", cellSize - 1)
  .attr("height", cellSize - 1)
  .attr("fill", d => d.value ? colorScale(d.value) : "#f5f5f5");

// Row labels
row.append("text")
  .attr("x", -6).attr("y", cellSize / 2)
  .attr("text-anchor", "end").attr("alignment-baseline", "middle")
  .style("font-size", `${Math.min(cellSize - 2, 12)}px`)
  .text(d => nodes[d].id);
```

### Reorderable Matrix

Let users reorder rows/columns to reveal clusters:

```js
function reorder(sortFn) {
  const newOrder = d3.range(n).sort(sortFn);
  const t = svg.transition().duration(500);
  row.transition(t)
    .attr("transform", (d) => `translate(${margin.left},${margin.top + newOrder.indexOf(d) * cellSize})`);
  row.selectAll(".cell").transition(t)
    .attr("x", (d) => newOrder.indexOf(d.col) * cellSize);
}

// Sort by cluster
reorder((a, b) => d3.ascending(nodes[a].group, nodes[b].group));
```

## Arc Diagrams

Nodes arranged on a line, edges drawn as arcs above (and optionally below). Good for ordered/sequential data (timelines, genomes, text) and for showing link distance patterns.

```js
const xScale = d3.scalePoint()
  .domain(nodes.map(d => d.id))
  .range([margin.left, width - margin.right]);

// Nodes on the line
svg.selectAll(".node")
  .data(nodes).join("circle")
  .attr("cx", d => xScale(d.id))
  .attr("cy", height / 2)
  .attr("r", d => Math.sqrt(d.degree + 1) * 2)
  .attr("fill", d => color(d.group));

// Arcs
svg.selectAll(".arc")
  .data(links).join("path")
  .attr("class", "arc")
  .attr("fill", "none")
  .attr("stroke", "#999")
  .attr("stroke-opacity", 0.4)
  .attr("stroke-width", d => Math.sqrt(d.weight || 1))
  .attr("d", d => {
    const x1 = xScale(d.source.id ?? d.source);
    const x2 = xScale(d.target.id ?? d.target);
    const midX = (x1 + x2) / 2;
    const r = Math.abs(x2 - x1) / 2;
    return `M${x1},${height / 2} A${r},${r} 0 0,${x1 < x2 ? 1 : 0} ${x2},${height / 2}`;
  });
```

### Node Ordering

The visual quality of arc diagrams depends heavily on node order. Options:

```js
// By cluster — groups related arcs
nodes.sort((a, b) => d3.ascending(a.group, b.group));

// By degree — hubs in center
nodes.sort((a, b) => d3.descending(a.degree, b.degree));

// Minimize crossings — seriation / optimal leaf order
// (NP-hard in general, but greedy barycenter heuristics work well for <500 nodes)
```

## Chord Diagrams

Show flows between groups in a circular layout. Each group gets an arc proportional to its total flow; ribbons connect groups proportional to their pairwise flow. Best for 5–20 groups with asymmetric flows.

```js
// Input: square matrix[i][j] = flow from group i to group j
const matrix = [
  [0, 50, 20, 10],
  [30, 0, 40, 15],
  [10, 25, 0, 35],
  [20, 10, 30, 0],
];
const names = ["Engineering", "Design", "Product", "Marketing"];

const chord = d3.chord()
  .padAngle(0.05)        // gap between groups
  .sortSubgroups(d3.descending);

const chords = chord(matrix);
const arc = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);
const ribbon = d3.ribbon().radius(innerRadius);

const g = svg.append("g")
  .attr("transform", `translate(${width / 2},${height / 2})`);

// Group arcs
g.selectAll(".group")
  .data(chords.groups).join("path")
  .attr("class", "group")
  .attr("d", arc)
  .attr("fill", d => color(names[d.index]))
  .attr("stroke", "#fff");

// Group labels
g.selectAll(".group-label")
  .data(chords.groups).join("text")
  .attr("class", "group-label")
  .each(d => { d.angle = (d.startAngle + d.endAngle) / 2; })
  .attr("dy", "0.35em")
  .attr("transform", d =>
    `rotate(${d.angle * 180 / Math.PI - 90}) translate(${outerRadius + 10})${d.angle > Math.PI ? " rotate(180)" : ""}`)
  .attr("text-anchor", d => d.angle > Math.PI ? "end" : null)
  .text(d => names[d.index]);

// Ribbons
g.selectAll(".ribbon")
  .data(chords).join("path")
  .attr("class", "ribbon")
  .attr("d", ribbon)
  .attr("fill", d => color(names[d.source.index]))
  .attr("stroke", "#fff")
  .attr("fill-opacity", 0.67);
```

### Interaction: Highlight on Hover

Fade all ribbons except those connected to the hovered group:

```js
g.selectAll(".group")
  .on("mouseover", (event, d) => {
    g.selectAll(".ribbon")
      .attr("fill-opacity", r =>
        r.source.index === d.index || r.target.index === d.index ? 0.8 : 0.1);
  })
  .on("mouseout", () => {
    g.selectAll(".ribbon").attr("fill-opacity", 0.67);
  });
```

## Sankey Diagrams

Flow diagrams showing quantities through a system. Nodes are stages/categories, links are flows with width proportional to value. Requires `d3-sankey` (separate package, not in d3 core).

```js
// import { sankey, sankeyLinkHorizontal } from "d3-sankey";
// or: const { sankey, sankeyLinkHorizontal } = d3;

const sankeyLayout = d3.sankey()
  .nodeId(d => d.id)
  .nodeWidth(15)
  .nodePadding(10)
  .nodeAlign(d3.sankeyJustify)  // sankeyLeft, sankeyRight, sankeyCenter, sankeyJustify
  .extent([[margin.left, margin.top], [width - margin.right, height - margin.bottom]]);

const { nodes, links } = sankeyLayout({
  nodes: data.nodes.map(d => ({ ...d })),
  links: data.links.map(d => ({ ...d })),
});

// Links (flows)
svg.selectAll(".link")
  .data(links).join("path")
  .attr("class", "link")
  .attr("d", d3.sankeyLinkHorizontal())
  .attr("fill", "none")
  .attr("stroke", d => color(d.source.category))
  .attr("stroke-opacity", 0.4)
  .attr("stroke-width", d => Math.max(1, d.width));

// Nodes
svg.selectAll(".node")
  .data(nodes).join("rect")
  .attr("class", "node")
  .attr("x", d => d.x0).attr("y", d => d.y0)
  .attr("width", d => d.x1 - d.x0)
  .attr("height", d => d.y1 - d.y0)
  .attr("fill", d => color(d.category));

// Labels
svg.selectAll(".node-label")
  .data(nodes).join("text")
  .attr("x", d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
  .attr("y", d => (d.y0 + d.y1) / 2)
  .attr("text-anchor", d => d.x0 < width / 2 ? "start" : "end")
  .attr("dy", "0.35em")
  .text(d => d.id);
```

### Circular Sankey

When flows loop back (e.g., recyclable materials, user session flows), use `d3.sankeyJustify` with the circular extension or draw backward links as arcs below the main diagram.

### Sankey Interaction

Highlight a flow path on hover:

```js
svg.selectAll(".link")
  .on("mouseover", function(event, d) {
    d3.select(this).attr("stroke-opacity", 0.8);
    // Highlight connected nodes
    svg.selectAll(".node")
      .attr("opacity", n => n === d.source || n === d.target ? 1 : 0.3);
  })
  .on("mouseout", () => {
    svg.selectAll(".link").attr("stroke-opacity", 0.4);
    svg.selectAll(".node").attr("opacity", 1);
  });
```

## Layout Comparison

| Layout | Best For | Node Count | Edge Density | Shows |
|--------|----------|------------|--------------|-------|
| Node-link (force) | Exploring topology, communities | 10–5K | Sparse (<10%) | Clusters, bridges, outliers |
| Adjacency matrix | Dense/complete graphs, comparing structure | 10–500 | Any | All edges equally, no occlusion |
| Arc diagram | Sequential/ordered data, link distance | 10–500 | Sparse–medium | Long vs short range connections |
| Chord diagram | Inter-group flows, asymmetric relationships | 5–20 groups | N/A (aggregated) | Flow direction and volume between groups |
| Sankey | Multi-stage flows, budgets, processes | 10–100 nodes | N/A (flow) | Quantities through a pipeline |

**Decision heuristic:**
1. **Is the data a flow/pipeline?** → Sankey
2. **Is it group-to-group relationships?** → Chord
3. **Is node order meaningful?** → Arc diagram
4. **Is the graph dense (>30% of possible edges)?** → Adjacency matrix
5. **Otherwise** → Node-link with force layout

## Accessibility

Different network layouts need different ARIA strategies. The right roles depend on the topology being rendered.

### Adjacency Matrix

The matrix is a data grid — `role="grid"` with `role="row"` and `role="gridcell"` is the correct semantic. Row and column headers provide node labels. This is the most inherently accessible network layout because it maps directly to a table:

```js
svg.attr("role", "grid").attr("aria-label", "Adjacency matrix showing connections between modules");

rows.attr("role", "row");
cells.attr("role", "gridcell")
  .attr("aria-label", d => `${nodes[d.row].label} to ${nodes[d.col].label}: ${d.value || "no connection"}`);
```

### Arc Diagram and Node-Link

These are visual/spatial layouts with no natural grid or list structure. Use `role="img"` with a descriptive `aria-label`, and provide a hidden data table as the accessible alternative:

```js
svg.attr("role", "img")
  .attr("aria-roledescription", "network diagram")
  .attr("aria-label", `Arc diagram with ${nodes.length} nodes and ${links.length} connections`);
```

For interactive force-directed layouts on canvas, see the `force-simulation` skill's spatial keyboard navigation and hybrid rendering patterns. For hidden data table alternatives, see `fallback-table`.

### Chord Diagram and Sankey

These show aggregated flows — the data is a matrix or flow table, not individual nodes. Use `role="img"` on the SVG with a summary label, and offer the underlying matrix/flow data as an accessible table:

```js
svg.attr("role", "img")
  .attr("aria-label", `Flow diagram showing ${names.length} groups with ${chords.length} connections`);
```

For chord diagrams, the group-hover interaction should announce the highlighted group and its total flow via `aria-live`.

## Common Pitfalls

**Hairball problem.** Node-link diagrams become unreadable past ~2,000 edges. Solutions: filter edges by weight threshold, aggregate into clusters, switch to adjacency matrix, or provide a sortable data table as a fallback (see `fallback-table` skill).

**Sankey needs d3-sankey.** Unlike chord and force which are in d3 core, Sankey requires the separate `d3-sankey` package. Include via CDN: `https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js`

**Chord matrix must be square.** `d3.chord()` expects an `n x n` matrix. Non-square input (e.g., bipartite data) needs reshaping: pad with zeros or restructure as a square bipartite matrix.

**Arc diagram node order matters enormously.** A random order produces unreadable crossings. Always sort nodes meaningfully — by cluster, by degree, or by optimal leaf order.

**Directed vs undirected confusion.** Adjacency matrices for undirected graphs should be symmetric (`matrix[i][j] === matrix[j][i]`). If yours isn't symmetric and the graph is undirected, you're missing half the edges.

**Sankey cycles.** `d3.sankey()` doesn't handle cycles — it throws or produces broken layouts. Remove cycles before layout (find back edges via DFS, remove the weakest) or use a circular Sankey extension.

**Arrow markers on curved paths.** SVG marker orientation on arcs and curves can point in unexpected directions. Use `orient="auto"` and test with actual curves, not just straight lines.

**Chord label overlap.** With many groups, labels around the circle overlap. Rotate labels to follow the arc tangent (shown above) and hide labels for groups below an angle threshold:

```js
.attr("visibility", d => d.endAngle - d.startAngle > 0.1 ? "visible" : "hidden")
```

## References

- [D3 Force documentation](https://d3js.org/d3-force) — Mike Bostock's API for force-directed node-link layouts
- [D3 Chord documentation](https://d3js.org/d3-chord) — API reference for chord diagrams
- [D3 Sankey plugin](https://github.com/d3/d3-sankey) — Sankey diagram layout for D3
- [Adjacency Matrix](https://observablehq.com/@d3/adjacency-matrix) — matrix layout for networks
- [Arc Diagram](https://observablehq.com/@d3/arc-diagram) — arc-based network layout
- [Matrix Reordering](https://hal.inria.fr/hal-01326759/document) — Jean-Daniel Fekete's research on optimal matrix orderings for pattern discovery
- [Sankey diagram](https://en.wikipedia.org/wiki/Sankey_diagram) — Captain Matthew Sankey's original 1898 energy flow diagram, the namesake
- [Graph Drawing](https://en.wikipedia.org/wiki/Graph_drawing) — overview of graph layout algorithms and their trade-offs
