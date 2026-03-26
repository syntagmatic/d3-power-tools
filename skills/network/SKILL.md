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
| Hive plot | Structural role patterns, network comparison | Free topology, cluster discovery | 50-1,000 nodes, 2-5 axes |

**Decision sequence:**
1. Flow/pipeline with quantities? → **Sankey**
2. Group-to-group flow with direction? → **Chord**
3. Node order is meaningful (time, sequence, genome position)? → **Arc diagram**
4. Need deterministic, reproducible layout or comparing two networks? → **Hive plot** (see below)
5. Dense graph (>30% of possible edges)? → **Adjacency matrix** — node-link will be a hairball
6. Need to find paths or trace connections? → **Node-link** — matrices make path-following hard (Ghoniem et al. 2004)
7. Need to compare edge weights precisely? → **Adjacency matrix** — position-encoded cells beat overlapping lines
8. >10K nodes? → Escalate beyond D3 (see "Scaling Past D3" below)

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

## Hive Plots (Deterministic Layout)

Force-directed layouts are non-deterministic: run the same layout twice and you get different positions. Any visible pattern might be a layout artifact. Hive plots (Krzywinski et al. 2012) fix this by placing nodes on 2-5 radial axes using explicit rules: axis assignment by a categorical property (role, type, community), position along the axis by a quantitative property (degree, centrality).

**When hive plots beat force:** comparing two networks (same axis mapping = visual diff is meaningful), asking structural questions ("do high-degree nodes in group A connect to low-degree in group B?"), bipartite/k-partite graphs, and any context requiring reproducible figures. **When force is still better:** exploratory analysis where you don't yet know the grouping.

Edges between axes are drawn as quadratic Bezier curves through the origin. The core geometry is ~50 lines: polar-to-Cartesian conversion for node placement, a custom path generator for links. No maintained npm package exists, but the implementation is straightforward with `d3.scaleLinear` for axis position. See [Bostock's hive plot](https://bost.ocks.org/mike/hive/) for the reference implementation.

## Community Detection and Graph Analysis

D3 has no graph algorithms beyond layout. For community detection, centrality, or shortest-path computation, use [graphology](https://graphology.github.io/) — a JavaScript graph library that runs client-side without a server round-trip to NetworkX.

**Typical pattern:** load data into graphology, run `graphology-communities-louvain` to assign community IDs, feed results back into D3 scales for color/size encoding. Louvain's resolution parameter controls community granularity — higher values produce more, smaller communities. A slider controlling resolution with real-time re-coloring is the natural interaction.

**Connecting to matrix reordering:** sort rows/columns by Louvain community assignment and dense diagonal blocks appear — communities become visually explicit. This turns the manual "sort by group" pattern (above) into an algorithmic one.

**Convex hull overlays:** after force layout stabilizes, draw `d3.polygonHull` around each community's nodes as a semi-transparent shape. Without a custom clustering force that pulls nodes toward their community centroid, Louvain assigns colors but force layout scatters communities randomly — the hull overlay is meaningless. See the `force` skill for clustering force implementation.

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

## Scaling Past D3

D3 SVG hits a wall at ~5,000 nodes (DOM overhead). D3 Canvas extends this to ~10K with quadtree hit detection (see `canvas` skill). Beyond 10K nodes, consider [sigma.js](https://www.sigmajs.org/) (v3, as of 2024): WebGL rendering built on graphology as its data layer. Use sigma.js for the main graph canvas, D3 for overlays (tooltips, detail panels, small multiples of subgraphs). For geospatial networks, deck.gl's GraphLayer handles millions of edges on a map. The `webgl` skill covers GPU acceleration patterns if you need to stay within D3.

## Common Pitfalls

**Hairball.** The single most common failure mode. Node-link diagrams become unreadable past ~2,000 edges. Solutions in order of preference: (1) filter by weight threshold or degree, (2) aggregate nodes into clusters, (3) switch to adjacency matrix, (4) provide a sortable data table fallback. Adding transparency is not a solution — it just makes a translucent hairball.

**Directed vs undirected mismatch.** Adjacency matrices for undirected graphs must be symmetric. If yours is not and the graph is undirected, half the edges are missing.

**Force layout as default.** Reaching for force-directed layout by default ignores the question of whether topology is the right thing to show. If the insight is about flow volume, use Sankey. If it is about density patterns, use a matrix.

**Overloading node size.** Encoding too many variables on nodes (size + color + border + label + icon) overwhelms the viewer. Two visual channels per element is a practical maximum for untrained audiences.

## References

- Ghoniem, Fekete, Castagliola (2004) — "A Comparison of the Readability of Graphs Using Node-Link and Matrix-Based Representations" — foundational study on matrix vs node-link task performance
- Okoe, Jianu, Kobourov (2019) — "Node-Link or Adjacency Matrices: Old Question, New Insights" — updated replication with larger networks
- Krzywinski et al. (2012) — "Hive plots — rational approach to visualizing networks" — deterministic network layout
- Henry, Fekete, McGuffin (2007) — "NodeTrix" — matrix-node-link hybrid for globally sparse, locally dense networks
- [D3 Sankey plugin](https://github.com/d3/d3-sankey)
- [Matrix Reordering](https://hal.inria.fr/hal-01326759/document) — Fekete's research on optimal matrix orderings
- [Graphology](https://graphology.github.io/) — JavaScript graph analysis library (community detection, centrality, shortest paths)
- [sigma.js](https://www.sigmajs.org/) — WebGL graph renderer for 10K+ nodes (v3, 2024)
