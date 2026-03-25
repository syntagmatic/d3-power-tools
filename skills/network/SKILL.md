---
name: network
description: "D3.js network and graph visualization: node-link diagrams, adjacency matrices, arc diagrams, chord diagrams, and Sankey flow diagrams. Use this skill whenever the user wants to visualize relationships, dependencies, flows, or connections between entities. Also use when the user mentions network graph, graph layout, adjacency matrix, arc diagram, d3.chord, d3.ribbon, d3.sankey, flow diagram, dependency graph, node-link, or wants to choose between different graph visualization types."
---

# Network Visualization

Network visualization answers the question: *how are these things connected?* The layout you choose determines which structural features the viewer can actually perceive — clusters, bridges, flow direction, or density. Pick the wrong layout and the answer is buried; pick the wrong representation entirely and a sorted table would have been clearer.

For force-directed node positioning and simulation tuning, see the `force` skill. For hierarchical edge bundling, see `edge-bundling`.

## When Not to Use Network Visualization

A network diagram is not the only way to show relationships, and it is often the wrong way. Before reaching for a node-link diagram, ask whether the data actually has exploitable structure.

**Signs you should use a table, matrix, or list instead:**
- **No community structure.** If nodes connect roughly at random (Erdos-Renyi-like), force layout produces a uniform blob. A sorted adjacency list or data table communicates the same information without the false implication of spatial meaning.
- **Too dense.** Past ~2,000 edges in a node-link diagram, occlusion makes individual edges indistinguishable — the "hairball." Filtering, aggregation, or switching to an adjacency matrix are real fixes; adding opacity is a band-aid.
- **Too many nodes with no clear question.** Showing 500 nodes "to see what's there" rarely works. Human short-term memory holds ~7 items. If you cannot state what structural feature the viewer should notice, the visualization has no job to do.
- **Relationships are uniform.** If every node connects to roughly the same neighbors with the same weight, there is no signal to visualize. A summary statistic (average degree, clustering coefficient) communicates more than a diagram.
- **The data is really a hierarchy.** Parent-child relationships are better served by tree/treemap/sunburst layouts, which encode depth. Force-directed layout obscures the levels.

## Choosing a Layout

The layout is an analytical choice, not a stylistic one. Each makes certain structures perceptible and hides others.

| Layout | Shows well | Hides | Sweet spot |
|--------|-----------|-------|------------|
| Node-link (force) | Clusters, bridges, outliers | Individual edges in dense regions | <500 nodes, <10% density |
| Adjacency matrix | All edges equally, weight patterns, density | Paths, topology | 10-500 nodes, any density |
| Arc diagram | Long vs short range connections, ordering effects | Clusters (unless pre-sorted) | 10-500 nodes, ordered axis |
| Chord diagram | Inter-group flow volume and direction | Individual connections | 5-20 groups |
| Sankey | Quantities through a pipeline, conservation | Topology, cycles | 10-100 nodes, DAG |

**Decision sequence:**
1. Flow/pipeline with quantities? → **Sankey**
2. Group-to-group flow with direction? → **Chord**
3. Node order is meaningful (time, sequence, genome position)? → **Arc diagram**
4. Dense graph (>30% of possible edges)? → **Adjacency matrix** — node-link will be a hairball
5. Need to find paths or trace connections? → **Node-link** — matrices make path-following hard (Ghoniem et al. 2004)
6. Need to compare edge weights precisely? → **Adjacency matrix** — position-encoded cells beat overlapping lines

### Why matrix beats node-link for dense graphs

In node-link diagrams, edge crossings cause the eye to lose track of which line connects which pair. Perceptual research (Ghoniem et al. 2004, Okoe et al. 2019) consistently finds: for cluster detection and edge-weight comparison in dense graphs, adjacency matrices are faster and more accurate. But for path-tracing tasks ("is A connected to B through C?"), node-link wins even in dense graphs — because path following in a matrix requires sequential row-column lookups.

## Data Validation

Real-world network data has dangling references, self-loops, duplicate edges, and disconnected components. Run [`validateNetwork()`](scripts/validate-network.js) before any layout — it catches issues that cause silent rendering bugs (nodes positioned at 0,0, missing links, NaN coordinates).

## Curved Links and Multi-Edges

When multiple edges connect the same pair, offset them with arc curvature so they remain individually visible:

```js
const linkCounts = new Map();
links.forEach(d => {
  const key = [d.source.id, d.target.id].sort().join("--");
  linkCounts.set(key, (linkCounts.get(key) || 0) + 1);
});

link.attr("d", d => {
  const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
  const dr = Math.sqrt(dx * dx + dy * dy) * (d.curveOffset || 1);
  return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
});
```

## Directional Edge Markers

`refX` must account for the target node's radius, or the arrowhead hides inside the circle:

```js
.attr("refX", d => radiusScale(d.target.degree) + 10)
```

Use `orient="auto"`. Test with actual curves — marker orientation on arcs can point in unexpected directions compared to straight lines.

## Adjacency Matrix Reordering

The visual quality of an adjacency matrix depends entirely on row/column ordering. Bad ordering scatters clusters across the matrix; good ordering reveals them as dense blocks on the diagonal.

```js
// Sort by cluster, then degree within cluster — reveals community structure
order.sort((a, b) => d3.ascending(nodes[a].group, nodes[b].group)
  || d3.descending(nodes[a].degree, nodes[b].degree));

// Animated reorder lets the viewer track which rows moved
function reorder(sortFn) {
  const newOrder = d3.range(n).sort(sortFn);
  const t = svg.transition().duration(500);
  row.transition(t)
    .attr("transform", d => `translate(${margin.left},${margin.top + newOrder.indexOf(d) * cellSize})`);
  row.selectAll(".cell").transition(t)
    .attr("x", d => newOrder.indexOf(d.col) * cellSize);
}
```

## Arc Diagram Node Ordering

Arc diagrams place nodes along a line with arcs above (or below) connecting them. The ordering determines what the viewer sees:

- **By cluster** — arcs between same-group nodes become short, visually grouping related items
- **By degree** — hubs migrate to center; the tallest arcs (long-range connections) become immediately visible as structural bridges
- **Minimize crossings** — NP-hard in general, but greedy barycenter heuristics work for <500 nodes. Reduces visual noise so individual connections are traceable

## Chord Diagrams

Best for 5-20 groups with asymmetric flows. The input matrix must be square — non-square bipartite data needs reshaping (pad with zeros or restructure).

Hide labels for small groups to prevent overlap:
```js
.attr("visibility", d => d.endAngle - d.startAngle > 0.1 ? "visible" : "hidden")
```

## Sankey Diagrams

Requires `d3-sankey` (separate package): `https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js`

`d3.sankey()` does not handle cycles — it throws or produces broken layouts. For flows that loop back (recycling, user session flows), remove back edges via DFS before layout, or use the circular Sankey extension.

## Accessibility by Layout Type

- **Adjacency matrix** — `role="grid"` with `role="row"` and `role="gridcell"`. The most inherently accessible layout because it maps to a table.
- **Arc diagram / Node-link** — `role="img"` with descriptive `aria-label`. Provide a hidden data table as the accessible alternative (see `data-table` skill).
- **Chord / Sankey** — `role="img"` with summary label. Offer underlying matrix/flow data as an accessible table.

## Common Pitfalls

**Hairball.** The single most common failure mode. Node-link diagrams become unreadable past ~2,000 edges. Solutions in order of preference: (1) filter by weight threshold or degree, (2) aggregate nodes into clusters, (3) switch to adjacency matrix, (4) provide a sortable data table fallback. Adding transparency is not a solution — it just makes a translucent hairball.

**Directed vs undirected mismatch.** Adjacency matrices for undirected graphs must be symmetric. If yours is not and the graph is undirected, half the edges are missing.

**Force layout as default.** Reaching for force-directed layout by default ignores the question of whether topology is the right thing to show. If the insight is about flow volume, use Sankey. If it is about density patterns, use a matrix.

**Overloading node size.** Encoding too many variables on nodes (size + color + border + label + icon) overwhelms the viewer. Two visual channels per element is a practical maximum for untrained audiences.

## References

- Ghoniem, Fekete, Castagliola (2004) — "A Comparison of the Readability of Graphs Using Node-Link and Matrix-Based Representations" — foundational study on matrix vs node-link task performance
- Okoe, Jianu, Kobourov (2019) — "Node-Link or Adjacency Matrices: Old Question, New Insights" — updated replication with larger networks
- [D3 Sankey plugin](https://github.com/d3/d3-sankey)
- [Matrix Reordering](https://hal.inria.fr/hal-01326759/document) — Fekete's research on optimal matrix orderings
