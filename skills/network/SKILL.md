---
name: network
description: "D3.js network and graph visualization: node-link diagrams, adjacency matrices, arc diagrams, chord diagrams, and Sankey flow diagrams. Use this skill whenever the user wants to visualize relationships, dependencies, flows, or connections between entities. Also use when the user mentions network graph, graph layout, adjacency matrix, arc diagram, d3.chord, d3.ribbon, d3.sankey, flow diagram, dependency graph, node-link, or wants to choose between different graph visualization types."
---

# Network Visualization

Network visualization answers the question: *how are these things connected?* The layout determines which structural features the viewer can perceive — clusters, bridges, flow direction, or density. Pick the wrong layout and the answer is buried.

For force-directed simulation tuning, see the `force` skill. For hierarchical edge bundling, see `edge-bundling`.

## When Not to Use Network Visualization

**Signs you should use a table, matrix, or list instead:**
- **No community structure.** Random-like connectivity → force layout produces a uniform blob. A sorted adjacency list communicates the same information.
- **Too dense.** Past ~2,000 edges in node-link, occlusion makes edges indistinguishable. Switch to adjacency matrix or aggregate.
- **Too many nodes with no clear question.** Showing 500 nodes "to see what's there" rarely works. Human short-term memory holds ~7 items.
- **Relationships are uniform.** Same neighbors, same weight → no signal to visualize. A summary statistic communicates more.
- **The data is really a hierarchy.** Use tree/treemap/sunburst instead — force layout obscures depth.

## Choosing a Layout

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
4. Need deterministic, reproducible layout or comparing two networks? → **Hive plot**
5. Dense graph (>30% of possible edges)? → **Adjacency matrix** — node-link will be a hairball
6. Need to find paths or trace connections? → **Node-link** — matrices make path-following hard (Ghoniem et al. 2004)
7. Need to compare edge weights precisely? → **Adjacency matrix**
8. >10K nodes? → Escalate beyond D3 (see "Scaling Past D3" below)

### Why matrix beats node-link for dense graphs

Perceptual research (Ghoniem et al. 2004, Okoe et al. 2019) consistently finds: for cluster detection and edge-weight comparison in dense graphs, adjacency matrices are faster and more accurate. But for path-tracing tasks, node-link wins even in dense graphs — path following in a matrix requires sequential row-column lookups.

## Data Validation

Real-world network data has dangling references, self-loops, duplicate edges, and disconnected components. Validate before any layout — these cause silent rendering bugs (nodes at 0,0, missing links, NaN coordinates).

## Directional Edge Markers

`refX` must account for the target node's radius, or the arrowhead hides inside the circle:

```js
.attr("refX", d => radiusScale(d.target.degree) + 10)
```

Use `orient="auto"`. Test with actual curves — marker orientation on arcs can differ from straight lines.

## Adjacency Matrix Reordering

Visual quality depends entirely on row/column ordering. Sort by cluster, then degree within cluster to reveal community structure as dense diagonal blocks:

```js
order.sort((a, b) => d3.ascending(nodes[a].group, nodes[b].group)
  || d3.descending(nodes[a].degree, nodes[b].degree));
```

Animated reorder lets the viewer track which rows moved — transition row `transform` and cell `x` positions over ~500ms.

## Arc Diagram Node Ordering

Nodes sit along a line with arcs connecting them. Ordering determines what the viewer sees:

- **By cluster** — same-group arcs become short, visually grouping related items
- **By degree** — hubs migrate to center; tallest arcs reveal structural bridges
- **Minimize crossings** — NP-hard in general, but greedy barycenter heuristics work for <500 nodes

## Hive Plots (Deterministic Layout)

Force layouts are non-deterministic — any visible pattern might be a layout artifact. Hive plots (Krzywinski et al. 2012) place nodes on 2-5 radial axes using explicit rules: axis by categorical property (role, type, community), position by quantitative property (degree, centrality). Edges are quadratic Bezier curves through the origin.

**When hive plots beat force:** comparing two networks, structural questions ("do high-degree A nodes connect to low-degree B?"), bipartite/k-partite graphs, reproducible figures. **When force is better:** exploratory analysis where grouping is unknown.

See [Bostock's hive plot](https://bost.ocks.org/mike/hive/) for the reference implementation (~50 lines of polar-to-Cartesian conversion + custom path generator).

## Community Detection and Graph Analysis

D3 has no graph algorithms beyond layout. Use [graphology](https://graphology.github.io/) client-side: load data, run `graphology-communities-louvain` to assign community IDs, feed results into D3 scales for color/size. Louvain's resolution parameter controls granularity — a slider with real-time re-coloring is the natural interaction.

**Matrix integration:** sort rows/columns by Louvain assignment and dense diagonal blocks appear.

**Convex hull overlays:** `d3.polygonHull` around each community after force layout stabilizes. Requires a custom clustering force that pulls nodes toward their community centroid (see `force` skill) — without it, communities scatter randomly and the hull is meaningless.

## Weighted Edge Encoding

Stroke-width is the natural channel. Use `scaleSqrt` — linear width exaggerates heavy edges because the eye reads area, not width:

```js
const widthScale = d3.scaleSqrt()
  .domain(d3.extent(links, d => d.weight))
  .range([0.5, 6]);
link.attr("stroke-width", d => widthScale(d.weight));
```

For redundant encoding (accessible and more legible), add a sequential color scale: `d3.scaleSequential(d3.interpolateYlOrRd)` on the same weight domain.

**Parallel edges** between the same node pair: group by sorted `source--target` key, assign each an offset index, render with arc curvature proportional to offset. Single edges stay straight; parallel edges fan out as arcs with `dr = dist / (2 * sin(atan(offset / dist)))`.

## Label Placement

**Node-link (sparse, <50 nodes):** offset from node center: `label.attr("x", d => d.x + d.r + 4).attr("y", d => d.y + 4)`. For denser graphs, use force-based label collision — create label proxy objects (don't mutate node positions), run a secondary simulation with `forceX`/`forceY` anchored to node positions + `forceCollide` on label width. See `annotation` skill for the rectangular collision pattern.

**Arc diagram:** labels below the axis, rotated 45°, `text-anchor: start`. Stagger vertically when neighbors overlap.

**Chord diagram outer labels:** rotated to follow the circle, flipped on the left half so text reads left-to-right:

```js
label.attr("transform", d => {
  const angle = (d.startAngle + d.endAngle) / 2;
  const rotate = angle * 180 / Math.PI - 90;
  const flip = angle > Math.PI;
  return `rotate(${rotate}) translate(${outerRadius + 10}) ${flip ? "rotate(180)" : ""}`;
})
.attr("text-anchor", d => (d.startAngle + d.endAngle) / 2 > Math.PI ? "end" : "start");
```

## Chord Diagrams

Best for 5-20 groups with asymmetric flows. `d3.chord()` requires a square matrix, but data usually arrives as `[{source, target, value}]`:

```js
const names = Array.from(new Set(edges.flatMap(d => [d.source, d.target])));
const index = new Map(names.map((name, i) => [name, i]));
const n = names.length;
const matrix = Array.from({length: n}, () => new Array(n).fill(0));

const rolled = d3.rollup(edges, v => d3.sum(v, d => d.value), d => d.source, d => d.target);
for (const [source, targets] of rolled) {
  for (const [target, value] of targets) {
    matrix[index.get(source)][index.get(target)] = value;
  }
}

const chords = d3.chord().padAngle(0.05)(matrix);
```

**Undirected data:** symmetrize with `matrix[i][j] = matrix[j][i] = value`. **Bipartite data** (countries-to-products): pad with zeros — create a `(nSrc + nTgt)²` matrix, fill cross-quadrants with edge values, leave same-type quadrants as zeros.

Hide labels for small groups: `.attr("visibility", d => d.endAngle - d.startAngle > 0.1 ? "visible" : "hidden")`.

## Sankey Diagrams

Requires `d3-sankey` (separate package): `https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js`

### Tabular Data to Sankey Format

Sankey needs `{nodes: [{name}], links: [{source, target, value}]}`. Tabular CSV rows need reshaping — build links between adjacent columns:

```js
// CSV rows like: {region: "West", product: "Widget", channel: "Online", revenue: 500}
const columns = ["region", "product", "channel"];
const nodeSet = new Set(), linkMap = new Map();

data.forEach(row => {
  for (let i = 0; i < columns.length - 1; i++) {
    const src = `${columns[i]}:${row[columns[i]]}`;
    const tgt = `${columns[i + 1]}:${row[columns[i + 1]]}`;
    nodeSet.add(src); nodeSet.add(tgt);
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

`d3.sankey()` does not handle cycles — it throws or produces broken layouts. Detect and remove back edges via DFS (color nodes white→grey→black; a grey→grey edge is a back edge). Filter those links before layout.

For flows where cycles are meaningful (user session loops), use [d3-sankey-circular](https://github.com/tomshanley/d3-sankey-circular) which routes back-edges as arcs below the diagram.

## Accessibility by Layout Type

- **Adjacency matrix** — `role="grid"` with `role="row"` and `role="gridcell"`. Most inherently accessible — maps to a table.
- **Arc diagram / Node-link** — `role="img"` with descriptive `aria-label`. Provide a hidden data table as the accessible alternative (see `data-table` skill).
- **Chord / Sankey** — `role="img"` with summary label. Offer underlying matrix/flow data as an accessible table.

## Force Tuning Recipes

The `force` skill covers simulation mechanics in depth. Ready-to-use parameter sets for common graph shapes:

| Graph shape | charge | link distance | link strength | extras |
|---|---|---|---|---|
| **Sparse tree-like** (acyclic, degree 1-3) | `-200` | `80` | default | No collision needed — low density |
| **Dense community** (50-500 nodes, 5-15 communities) | `-80`, `distanceMax(250)` | `30` | `0.3` intra-community, `0.01` inter | `forceCollide(d.r + 1)` |
| **Bipartite** (edges only between types) | `-30` | `100` | default | `forceX` pins types to columns (strength `0.4`), weak `forceY` |
| **Hub-and-spoke** (few high-degree hubs) | `-300` hubs, `-30` leaves | `60` hub edges, `30` leaf edges | default | Per-node charge gives hubs room |

## Hairball Reduction

When node-link becomes unreadable — not "add opacity," actual fixes:

**Minimum weight threshold** — simplest. Use a slider: `links.filter(d => d.weight >= minWeight)`, update force link, reheat `alpha(0.3)`.

**Top-k edges per node** — keeps strongest connections of every node, preventing isolates. Group links by source and target, keep top-k by weight from each side, deduplicate with a Set.

**Community aggregation** — collapse each community to a meta-node. Use `d3.group(nodes, d => d.community)` for meta-nodes (sized by member count), `d3.rollups` on inter-community links for meta-edges (weighted by sum). Turns a 500-node hairball into a 10-node summary.

**Fisheye on hover** — keep full graph, magnify neighborhood under cursor. See `brushing` skill for the fisheye distortion pattern.

## Temporal Networks

Edges that appear/disappear over time. Filter links by a time range and transition the visual state:

```js
const timeScale = d3.scaleTime()
  .domain(d3.extent(links, d => d.timestamp))
  .range([0, sliderWidth]);

function updateTime(t0, t1) {
  const active = links.filter(d => d.timestamp >= t0 && d.timestamp <= t1);
  const activeSet = new Set(active.map(d => `${d.source.id}--${d.target.id}`));
  const activeNodes = new Set(active.flatMap(d => [d.source.id, d.target.id]));

  linkSel.transition().duration(300)
    .attr("stroke-opacity", d => activeSet.has(`${d.source.id}--${d.target.id}`) ? 0.6 : 0.02);
  nodeSel.transition().duration(300)
    .attr("fill-opacity", d => activeNodes.has(d.id) ? 1 : 0.15)
    .attr("r", d => activeNodes.has(d.id) ? radiusScale(d.degree) : 2);
}
```

Bind to a range slider. For animated playback, step with `d3.interval` at accelerated speed. Keep force simulation running during animation — reheat gently (`alpha(0.1)`) per step to avoid jarring jumps.

## Scaling Past D3

D3 SVG hits a wall at ~5K nodes. D3 Canvas extends to ~10K with quadtree hit detection (see `canvas` skill). Beyond 10K, consider [sigma.js](https://www.sigmajs.org/) (v3): WebGL rendering on graphology. Use sigma for the graph canvas, D3 for overlays. For geospatial networks, deck.gl's GraphLayer handles millions of edges. The `webgl` skill covers GPU acceleration if staying within D3.

## Common Pitfalls

**Hairball.** The most common failure. Node-link becomes unreadable past ~2,000 edges. In order: (1) filter by weight/degree, (2) aggregate into clusters, (3) switch to adjacency matrix, (4) provide a sortable data table fallback. Transparency is not a solution.

**Directed vs undirected mismatch.** Adjacency matrices for undirected graphs must be symmetric. If yours isn't and the graph is undirected, half the edges are missing.

**Force layout as default.** Reaching for force by default ignores whether topology is the right thing to show. Flow volume → Sankey. Density patterns → matrix.

**Overloading node size.** Encoding too many variables (size + color + border + label + icon) overwhelms the viewer. Two visual channels per element is the practical maximum.

## References

- Ghoniem, Fekete, Castagliola (2004) — matrix vs node-link task performance
- Okoe, Jianu, Kobourov (2019) — updated replication with larger networks
- Krzywinski et al. (2012) — "Hive plots — rational approach to visualizing networks"
- Henry, Fekete, McGuffin (2007) — "NodeTrix" — matrix-node-link hybrid
- [D3 Sankey plugin](https://github.com/d3/d3-sankey)
- [Matrix Reordering](https://hal.inria.fr/hal-01326759/document) — Fekete's research
- [Graphology](https://graphology.github.io/) — JavaScript graph analysis library
- [sigma.js](https://www.sigmajs.org/) — WebGL graph renderer for 10K+ nodes
- [d3-sankey-circular](https://github.com/tomshanley/d3-sankey-circular) — Sankey with cycle support
