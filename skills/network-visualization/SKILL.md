---
name: network-visualization
description: "D3.js network and graph visualization: node-link diagrams, adjacency matrices, arc diagrams, chord diagrams, and Sankey flow diagrams. Use this skill whenever the user wants to visualize relationships, dependencies, flows, or connections between entities. Also use when the user mentions network graph, graph layout, adjacency matrix, arc diagram, d3.chord, d3.ribbon, d3.sankey, flow diagram, dependency graph, node-link, or wants to choose between different graph visualization types."
---

# Network Visualization

Patterns for visualizing graph and network data with D3. Covers data preparation, five major layout types, and guidance on choosing between them.

For force-directed node positioning and simulation tuning, see the `force-simulation` skill. For hierarchical edge bundling, see `hierarchy-edge-bundling`.

## Data Validation

> **Always validate first.** Real-world network data has dangling references, self-loops, duplicate edges, and disconnected components. Run [`validateNetwork()`](scripts/validate-network.js) before any layout — it catches issues that cause silent rendering bugs.

See [`scripts/validate-network.js`](scripts/validate-network.js) for the full `validateNetwork()` / `cleanNetwork()` implementation. Detects: duplicate node IDs, dangling source/target references, self-loops, duplicate edges, invalid/negative weights, disconnected components, and isolated nodes.

## Curved Links and Multi-Edges

When there are multiple edges between the same pair of nodes, offset them with curves:

```js
// Detect parallel edges
const linkCounts = new Map();
links.forEach(d => {
  const key = [d.source.id, d.target.id].sort().join("--");
  linkCounts.set(key, (linkCounts.get(key) || 0) + 1);
});

// Draw as arcs with curvature proportional to offset
link.attr("d", d => {
  const dx = d.target.x - d.source.x;
  const dy = d.target.y - d.source.y;
  const dr = Math.sqrt(dx * dx + dy * dy) * (d.curveOffset || 1);
  return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
});
```

## Directional Edge Markers on Curves

`refX` must account for the target node's radius, or the arrow tip will be hidden inside the node circle:

```js
.attr("refX", d => radiusScale(d.target.degree) + 10)
```

Use `orient="auto"` and test with actual curves — marker orientation on arcs can point in unexpected directions compared to straight lines.

## Adjacency Matrix

Better than node-link for dense graphs (>50% edge density) where hairball node-link diagrams become unreadable.

### Reordering Strategies

The visual quality depends entirely on row/column ordering. Options:

```js
// By cluster — groups related cells into blocks on the diagonal
order.sort((a, b) => d3.ascending(nodes[a].group, nodes[b].group)
  || d3.descending(nodes[a].degree, nodes[b].degree));

// Animated reorder
function reorder(sortFn) {
  const newOrder = d3.range(n).sort(sortFn);
  const t = svg.transition().duration(500);
  row.transition(t)
    .attr("transform", d => `translate(${margin.left},${margin.top + newOrder.indexOf(d) * cellSize})`);
  row.selectAll(".cell").transition(t)
    .attr("x", d => newOrder.indexOf(d.col) * cellSize);
}
```

For discovering hidden structure, see Fekete's matrix reordering research (reference below).

## Arc Diagram Node Ordering

The visual quality of arc diagrams depends heavily on node order:

- **By cluster** — groups related arcs together
- **By degree** — hubs in center, reduces long arcs
- **Minimize crossings** — seriation / optimal leaf order (NP-hard in general, but greedy barycenter heuristics work well for <500 nodes)

## Chord Diagrams

Best for 5-20 groups with asymmetric flows. The input matrix must be square — non-square bipartite data needs reshaping (pad with zeros or restructure).

### Label Overlap

With many groups, labels around the circle overlap. Hide labels for groups below an angle threshold:

```js
.attr("visibility", d => d.endAngle - d.startAngle > 0.1 ? "visible" : "hidden")
```

## Sankey Diagrams

Requires `d3-sankey` (separate package, not in d3 core). CDN: `https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js`

### Circular Sankey

`d3.sankey()` doesn't handle cycles — it throws or produces broken layouts. Remove cycles before layout (find back edges via DFS, remove the weakest) or use the circular Sankey extension for flows that loop back (recyclable materials, user session flows).

## Layout Comparison

| Layout | Best For | Node Count | Edge Density | Shows |
|--------|----------|------------|--------------|-------|
| Node-link (force) | Exploring topology, communities | 10-5K | Sparse (<10%) | Clusters, bridges, outliers |
| Adjacency matrix | Dense/complete graphs, comparing structure | 10-500 | Any | All edges equally, no occlusion |
| Arc diagram | Sequential/ordered data, link distance | 10-500 | Sparse-medium | Long vs short range connections |
| Chord diagram | Inter-group flows, asymmetric relationships | 5-20 groups | N/A (aggregated) | Flow direction and volume |
| Sankey | Multi-stage flows, budgets, processes | 10-100 nodes | N/A (flow) | Quantities through a pipeline |

**Decision heuristic:**
1. Flow/pipeline? -> Sankey
2. Group-to-group relationships? -> Chord
3. Node order meaningful? -> Arc diagram
4. Dense graph (>30% edges)? -> Adjacency matrix
5. Otherwise -> Node-link with force layout

## Accessibility by Layout Type

Different layouts need different ARIA strategies:

- **Adjacency matrix** — `role="grid"` with `role="row"` and `role="gridcell"`. The most inherently accessible layout because it maps directly to a table.
- **Arc diagram / Node-link** — `role="img"` with descriptive `aria-label`. Provide a hidden data table as the accessible alternative (see `data-table`).
- **Chord / Sankey** — `role="img"` with summary label. Offer underlying matrix/flow data as an accessible table. Chord group-hover should announce via `aria-live`.

## Common Pitfalls

**Hairball problem.** Node-link diagrams become unreadable past ~2,000 edges. Filter by weight threshold, aggregate into clusters, switch to adjacency matrix, or provide a sortable data table fallback.

**Directed vs undirected confusion.** Adjacency matrices for undirected graphs should be symmetric. If yours isn't and the graph is undirected, you're missing half the edges.

## References

- [D3 Sankey plugin](https://github.com/d3/d3-sankey) — Sankey diagram layout for D3
- [Matrix Reordering](https://hal.inria.fr/hal-01326759/document) — Jean-Daniel Fekete's research on optimal matrix orderings for pattern discovery
- [Sankey diagram](https://en.wikipedia.org/wiki/Sankey_diagram) — Captain Matthew Sankey's original 1898 energy flow diagram
