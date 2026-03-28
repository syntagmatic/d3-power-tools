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

## Weighted Edge Encoding

Stroke-width is the natural channel for edge weight. Use `scaleSqrt` — linear width exaggerates heavy edges because the eye reads area, not width:

```js
const widthScale = d3.scaleSqrt()
  .domain(d3.extent(links, d => d.weight))
  .range([0.5, 6]);

link.attr("stroke-width", d => widthScale(d.weight));
```

For color encoding, a sequential scale on weight works when topology matters more than precise comparison. Combine with width for redundant encoding — accessible and more legible:

```js
const colorScale = d3.scaleSequential(d3.interpolateYlOrRd)
  .domain(d3.extent(links, d => d.weight));
link.attr("stroke", d => colorScale(d.weight))
    .attr("stroke-width", d => widthScale(d.weight));
```

**Bundled parallel edges** between the same node pair — offset each by index so they don't stack:

```js
// Pre-compute: group parallel edges and assign offset index
const pairMap = new Map();
links.forEach(d => {
  const key = [d.source.id, d.target.id].sort().join("--");
  if (!pairMap.has(key)) pairMap.set(key, []);
  pairMap.get(key).push(d);
});
pairMap.forEach(group => group.forEach((d, i) => {
  d.parallelIndex = i;
  d.parallelCount = group.length;
}));

// Render with offset curvature
link.attr("d", d => {
  const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  // Spread parallel edges; single edges get straight line
  const offset = d.parallelCount === 1 ? 0
    : (d.parallelIndex - (d.parallelCount - 1) / 2) * 30;
  const dr = offset === 0 ? 0 : dist / (2 * Math.sin(Math.atan(offset / dist)));
  return offset === 0
    ? `M${d.source.x},${d.source.y}L${d.target.x},${d.target.y}`
    : `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,${offset > 0 ? 1 : 0} ${d.target.x},${d.target.y}`;
});
```

## Label Placement

### Node-Link Labels

For sparse graphs (<50 nodes), offset labels from node center and let the eye resolve collisions:

```js
label.attr("x", d => d.x + d.r + 4).attr("y", d => d.y + 4);
```

For denser graphs, use force-based label collision avoidance — same pattern as `annotation` skill's rectangular collision force. Create label proxy objects so the main node positions aren't mutated:

```js
const labelNodes = nodes.map(d => ({id: d.id, anchorX: d.x, anchorY: d.y, labelWidth: d.labelWidth}));
const labelSim = d3.forceSimulation(labelNodes)
  .force("x", d3.forceX(d => d.anchorX).strength(0.5))
  .force("y", d3.forceY(d => d.anchorY).strength(0.5))
  .force("collide", d3.forceCollide(d => d.labelWidth / 2 + 2))
  .stop();
labelSim.tick(50);
label.data(labelNodes).attr("x", d => d.x).attr("y", d => d.y);
```

### Arc Diagram Labels

Place labels below the axis, rotated 45 degrees. Stagger vertically when neighbors overlap:

```js
label.attr("transform", d => `translate(${x(d.id)},${y0 + 12}) rotate(45)`)
    .attr("text-anchor", "start");
```

### Chord Diagram Outer Labels

Labels sit outside the arcs, rotated to follow the circle. Flip text on the left half so it reads left-to-right:

```js
label.attr("transform", d => {
  const angle = (d.startAngle + d.endAngle) / 2;
  const rotate = angle * 180 / Math.PI - 90;
  const flip = angle > Math.PI;  // left half of circle
  return `rotate(${rotate}) translate(${outerRadius + 10}) ${flip ? "rotate(180)" : ""}`;
})
.attr("text-anchor", d => {
  const angle = (d.startAngle + d.endAngle) / 2;
  return angle > Math.PI ? "end" : "start";
});
```

## Chord Diagrams

Best for 5-20 groups with asymmetric flows. The input matrix must be square — non-square bipartite data needs reshaping (pad with zeros or restructure).

### Edge List to Square Matrix

The most common stumbling block. `d3.chord()` requires a square matrix, but data usually arrives as `[{source, target, value}]`:

```js
// Edge list → square matrix for d3.chord
const names = Array.from(new Set(edges.flatMap(d => [d.source, d.target])));
const index = new Map(names.map((name, i) => [name, i]));
const n = names.length;
const matrix = Array.from({length: n}, () => new Array(n).fill(0));

// Aggregate duplicate source-target pairs
const rolled = d3.rollup(edges, v => d3.sum(v, d => d.value), d => d.source, d => d.target);
for (const [source, targets] of rolled) {
  for (const [target, value] of targets) {
    matrix[index.get(source)][index.get(target)] = value;
  }
}

const chords = d3.chord().padAngle(0.05)(matrix);
```

For undirected data, symmetrize: `matrix[i][j] = matrix[j][i] = value`. For bipartite data (e.g., countries-to-products), pad with zeros:

```js
// Bipartite: rows are sources, cols are targets — pad to make square
const nSrc = sources.length, nTgt = targets.length, total = nSrc + nTgt;
const matrix = Array.from({length: total}, () => new Array(total).fill(0));
edges.forEach(d => {
  matrix[srcIndex.get(d.source)][nSrc + tgtIndex.get(d.target)] = d.value;
  matrix[nSrc + tgtIndex.get(d.target)][srcIndex.get(d.source)] = d.value; // symmetric
});
```

Hide labels for small groups to prevent overlap:
```js
.attr("visibility", d => d.endAngle - d.startAngle > 0.1 ? "visible" : "hidden")
```

## Sankey Diagrams

Requires `d3-sankey` (separate package): `https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js`

### Tabular Data to Sankey Format

Sankey needs `{nodes: [{name}], links: [{source, target, value}]}`. Tabular data (CSV rows with category columns) needs reshaping — build links between adjacent columns:

```js
// CSV rows like: {region: "West", product: "Widget", channel: "Online", revenue: 500}
const columns = ["region", "product", "channel"];  // flow order
const nodeSet = new Set();
const linkMap = new Map();

data.forEach(row => {
  for (let i = 0; i < columns.length - 1; i++) {
    const src = `${columns[i]}:${row[columns[i]]}`;
    const tgt = `${columns[i + 1]}:${row[columns[i + 1]]}`;
    nodeSet.add(src);
    nodeSet.add(tgt);
    const key = `${src}→${tgt}`;
    linkMap.set(key, (linkMap.get(key) || 0) + +row.revenue);
  }
});

const nodes = Array.from(nodeSet, name => ({name}));
const nodeIndex = new Map(nodes.map((d, i) => [d.name, i]));
const links = Array.from(linkMap, ([key, value]) => {
  const [source, target] = key.split("→");
  return {source: nodeIndex.get(source), target: nodeIndex.get(target), value};
});
```

### Cycle Removal

`d3.sankey()` does not handle cycles — it throws or produces broken layouts. For flows that loop back (recycling, user session flows), detect and remove back edges via DFS before layout:

```js
function removeCycles(nodes, links) {
  const adj = new Map(nodes.map((_, i) => [i, []]));
  links.forEach((l, i) => adj.get(l.source).push({target: l.target, index: i}));

  const state = new Array(nodes.length).fill(0); // 0=white, 1=grey, 2=black
  const backEdges = new Set();

  function dfs(u) {
    state[u] = 1;
    for (const {target: v, index} of adj.get(u)) {
      if (state[v] === 1) backEdges.add(index);  // back edge = cycle
      else if (state[v] === 0) dfs(v);
    }
    state[u] = 2;
  }

  nodes.forEach((_, i) => { if (state[i] === 0) dfs(i); });
  return links.filter((_, i) => !backEdges.has(i));
}
```

For flows where cycles are meaningful (e.g., user session loops), use [d3-sankey-circular](https://github.com/tomshanley/d3-sankey-circular) which routes back-edges as arcs below the diagram.

## Accessibility by Layout Type

- **Adjacency matrix** — `role="grid"` with `role="row"` and `role="gridcell"`. The most inherently accessible layout because it maps to a table.
- **Arc diagram / Node-link** — `role="img"` with descriptive `aria-label`. Provide a hidden data table as the accessible alternative (see `data-table` skill).
- **Chord / Sankey** — `role="img"` with summary label. Offer underlying matrix/flow data as an accessible table.

## Force Tuning Recipes for Network Layout

The `force` skill covers simulation mechanics in depth. Here are ready-to-use parameter sets for common graph shapes:

**Sparse tree-like** (acyclic or near-acyclic, degree mostly 1-3):
```js
simulation
  .force("charge", d3.forceManyBody().strength(-200))
  .force("link", d3.forceLink(links).id(d => d.id).distance(80))
  .force("center", d3.forceCenter(width / 2, height / 2));
// High repulsion + long links spread the tree. No collision needed — low density.
```

**Dense community graph** (50-500 nodes, 5-15 communities):
```js
simulation
  .force("charge", d3.forceManyBody().strength(-80).distanceMax(250))
  .force("link", d3.forceLink(links).id(d => d.id).distance(30).strength(d =>
    d.source.group === d.target.group ? 0.3 : 0.01))
  .force("collide", d3.forceCollide(d => d.r + 1))
  .force("center", d3.forceCenter(width / 2, height / 2));
// Intra-community links pull tight, inter-community links are slack → groups separate.
```

**Bipartite** (two node types, edges only between types):
```js
const leftX = width * 0.3, rightX = width * 0.7;
simulation
  .force("x", d3.forceX(d => d.type === "A" ? leftX : rightX).strength(0.4))
  .force("y", d3.forceY(height / 2).strength(0.01))
  .force("charge", d3.forceManyBody().strength(-30))
  .force("link", d3.forceLink(links).id(d => d.id).distance(100))
  .force("collide", d3.forceCollide(d => d.r + 2));
// Strong x-force pins types to columns; weak y lets them spread vertically.
```

**Hub-and-spoke** (few hubs with high degree, many leaves):
```js
simulation
  .force("charge", d3.forceManyBody().strength(d => d.degree > 10 ? -300 : -30))
  .force("link", d3.forceLink(links).id(d => d.id)
    .distance(d => d.source.degree > 10 || d.target.degree > 10 ? 60 : 30))
  .force("collide", d3.forceCollide(d => d.r + 1))
  .force("center", d3.forceCenter(width / 2, height / 2));
// Per-node charge gives hubs room; shorter leaf links keep spokes compact.
```

## Hairball Reduction

When a node-link diagram becomes unreadable, these are practical fixes — not just "add opacity."

**Minimum weight threshold** — the simplest filter. Use a slider for exploration:

```js
function filterByWeight(links, minWeight) {
  return links.filter(d => d.weight >= minWeight);
}
// Bind to slider:
slider.on("input", function() {
  const filtered = filterByWeight(allLinks, +this.value);
  simulation.force("link", d3.forceLink(filtered).id(d => d.id));
  simulation.alpha(0.3).restart();
});
```

**Top-k edges per node** — keeps the strongest connections of every node, preventing isolates:

```js
function topKEdgesPerNode(links, k) {
  const keep = new Set();
  const byNode = d3.group(links, d => d.source.id);
  for (const [, nodeLinks] of byNode) {
    nodeLinks.sort((a, b) => b.weight - a.weight);
    nodeLinks.slice(0, k).forEach(l => keep.add(l));
  }
  // Also check target side
  const byTarget = d3.group(links, d => d.target.id);
  for (const [, nodeLinks] of byTarget) {
    nodeLinks.sort((a, b) => b.weight - a.weight);
    nodeLinks.slice(0, k).forEach(l => keep.add(l));
  }
  return Array.from(keep);
}
```

**Community-based aggregation** — collapse each community to a single meta-node, showing inter-community edges as weighted links. Turns a 500-node hairball into a 10-node summary:

```js
// After Louvain community detection (via graphology), aggregate
function aggregateByCommunity(nodes, links) {
  const communityNodes = Array.from(
    d3.group(nodes, d => d.community),
    ([id, members]) => ({id, label: `Community ${id}`, size: members.length})
  );
  const communityLinks = d3.rollups(
    links.filter(d => d.source.community !== d.target.community),
    v => d3.sum(v, d => d.weight || 1),
    d => d.source.community,
    d => d.target.community
  ).flatMap(([src, targets]) =>
    targets.map(([tgt, weight]) => ({source: src, target: tgt, weight}))
  );
  return {nodes: communityNodes, links: communityLinks};
}
```

**Fisheye on hover** — keep the full graph but magnify the neighborhood under the cursor. See the `brushing` skill for the fisheye distortion pattern. The key idea: apply fisheye to node positions on mousemove, redraw, and snap back on mouseout.

## Temporal Networks

Edges that appear and disappear over time. The core pattern: filter links by a time range and transition the visual state.

```js
const timeScale = d3.scaleTime()
  .domain(d3.extent(links, d => d.timestamp))
  .range([0, sliderWidth]);

function updateTime(t0, t1) {
  const active = links.filter(d => d.timestamp >= t0 && d.timestamp <= t1);
  const activeSet = new Set(active.map(d => `${d.source.id}--${d.target.id}`));

  // Links: fade in/out
  linkSel.transition().duration(300)
    .attr("stroke-opacity", d =>
      activeSet.has(`${d.source.id}--${d.target.id}`) ? 0.6 : 0.02);

  // Nodes: highlight if they have any active edge
  const activeNodes = new Set(active.flatMap(d => [d.source.id, d.target.id]));
  nodeSel.transition().duration(300)
    .attr("fill-opacity", d => activeNodes.has(d.id) ? 1 : 0.15)
    .attr("r", d => activeNodes.has(d.id) ? radiusScale(d.degree) : 2);
}

// Bind to range slider or play button
slider.on("input", function() {
  const t = timeScale.invert(+this.value);
  const windowMs = 30 * 24 * 60 * 60 * 1000; // 30-day window
  updateTime(new Date(t - windowMs), t);
});
```

For animated playback, step through time with `d3.interval`:

```js
const windowMs = 30 * 24 * 60 * 60 * 1000; // 30-day window
const play = d3.interval(elapsed => {
  const t = timeScale.invert(elapsed * 10); // 10x speed
  updateTime(new Date(t - windowMs), t);
  if (t > timeScale.domain()[1]) play.stop();
}, 50);
```

Keep the force simulation running during time animation — nodes settle into new positions as their connections change. Reheat gently (`alpha(0.1)`) on each time step to avoid jarring jumps.

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
- [d3-sankey-circular](https://github.com/tomshanley/d3-sankey-circular) — Sankey layout with cycle support
