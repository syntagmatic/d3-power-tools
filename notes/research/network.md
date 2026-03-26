# Network Visualization Research

Research into techniques beyond what the current `skills/network/SKILL.md` covers.

## Current Coverage

The skill covers five layout types with clear decision guidance:

- **Node-link (force)** -- clusters, bridges, outliers; <500 nodes, <10% density
- **Adjacency matrix** -- all edges equally, weight patterns; 10-500 nodes, any density
- **Arc diagram** -- long vs short range connections; 10-500 nodes, ordered axis
- **Chord diagram** -- inter-group flow volume; 5-20 groups
- **Sankey** -- quantities through a pipeline; 10-100 nodes, DAG

Strengths: good "when not to use" guidance, matrix reordering, validation, accessibility. References Ghoniem 2004 and Okoe 2019 for matrix vs node-link research.

Gaps identified:
1. No deterministic layout option (everything is force-based or manual)
2. No graph analysis library integration (centrality, community detection, shortest path)
3. No path beyond ~2,000 edges except "switch to matrix" or "filter"
4. No community detection or cluster visualization patterns
5. No hybrid representations (matrix + node-link in same view)
6. No linear/non-overlapping layouts (BioFabric)

---

## Hive Plots (deterministic layout, when it beats force)

**Source:** Martin Krzywinski et al., "Hive plots -- rational approach to visualizing networks," *Briefings in Bioinformatics* 13(5):627-644, 2012. [hiveplot.com](https://hiveplot.com/), [Mike Bostock's D3 implementation](https://bost.ocks.org/mike/hive/).

### What problem it solves

Force-directed layouts are non-deterministic: run the same layout twice and you get different positions. This makes comparison between networks impossible and means any visible pattern might be an artifact of the layout algorithm rather than the data. Hive plots fix this by placing nodes on radially oriented linear axes using a well-defined coordinate system.

### How it works

1. **Axis assignment** -- nodes are assigned to 2-5 radial axes based on a categorical property (role, type, community) or a structural property (e.g., degree quartile).
2. **Position on axis** -- nodes are positioned along their axis by a quantitative property (degree, centrality, timestamp).
3. **Edge drawing** -- edges between axes are drawn as curves (typically quadratic Bezier or d3.curveBundle). Edges within the same axis can use a "split axis" (same axis duplicated at two angles) so they remain visible.

### When it beats force

- **Comparing two networks.** Same axis mapping = same layout = visual diff is meaningful.
- **Asking structural questions.** "Do high-degree nodes in group A connect to low-degree nodes in group B?" is directly readable.
- **Presentation and publication.** Deterministic = reproducible figures.
- **Bipartite or k-partite graphs.** Natural axis assignment by partition.

### When force is still better

- Exploratory analysis where you don't yet know what axis mapping to use.
- When the question is "show me the clusters" (hive plots require you to already know the grouping).

### Scale limits

Works well up to ~1,000 nodes per axis. Edge density is the real limit -- past ~5,000 edges the curves become a bundle (though still more readable than a force hairball because the structure is deterministic).

### D3 integration

Mike Bostock's implementation uses a custom `d3.hive.link()` path generator. The core geometry is simple: nodes are placed in polar coordinates (angle = axis, radius = position), then edges are drawn with SVG path curves. No dedicated npm package is maintained, but the implementation is ~50 lines of geometry code.

Key D3 APIs: `d3.scaleLinear` for axis position, polar-to-Cartesian conversion for node placement, custom path generator for curved links.

---

## Graphology Ecosystem (analysis library, integration with D3)

**Source:** [graphology.github.io](https://graphology.github.io/), [npm: graphology](https://www.npmjs.com/package/graphology).

### What problem it solves

D3 has no graph data structure or graph algorithms. `d3-force` handles layout but not analysis. Graphology provides a full graph manipulation library: add/remove nodes and edges, iterate neighbors, compute metrics -- all in JavaScript. This means you can run analysis client-side before visualizing, without a server round-trip to NetworkX or igraph.

### Key capabilities

**Data structure:** Supports directed, undirected, and mixed graphs. Multi-graph support (multiple edges between same pair). Typed (TypeScript declarations). Event-driven (can listen to graph mutations).

**Standard library algorithms (all on npm as separate packages):**
- **Community detection:** `graphology-communities-louvain` -- Louvain algorithm with configurable resolution parameter. Supports directed and undirected graphs. `louvain.assign(graph)` writes community IDs directly onto node attributes. No Leiden implementation yet in JavaScript.
- **Centrality:** betweenness, closeness, degree, eigenvector, PageRank
- **Shortest paths:** Dijkstra, unweighted BFS
- **Layout:** ForceAtlas2 (the layout algorithm used by Gephi), circular, random
- **Metrics:** density, diameter, modularity, clustering coefficient
- **Operators:** subgraph extraction, reverse, union, complement

### Integration with D3

Graphology is rendering-agnostic. Two integration paths:

1. **Graphology for analysis, D3 for rendering.** Run community detection or centrality in graphology, read the computed attributes, feed them into D3 scales for color/size encoding. Use `d3-force` for layout as usual.

2. **Graphology + sigma.js for rendering.** sigma.js uses graphology as its graph model natively. Better for large graphs (WebGL rendering) but less flexible for custom visualizations.

**Pattern:** Use graphology when you need to compute graph metrics that D3 doesn't provide. The typical flow is: load data into graphology graph -> run algorithms (community detection, centrality) -> extract results as node/edge attributes -> pass to D3 for visualization.

```
npm install graphology graphology-communities-louvain graphology-metrics
```

```js
import Graph from 'graphology';
import louvain from 'graphology-communities-louvain';
import { degreeCentrality } from 'graphology-metrics/centrality/degree';

const graph = new Graph();
data.nodes.forEach(n => graph.addNode(n.id, n));
data.links.forEach(l => graph.addEdge(l.source, l.target, l));

// Community detection
louvain.assign(graph);  // writes 'community' attribute to each node

// Centrality
const centrality = degreeCentrality(graph);

// Feed into D3
const colorScale = d3.scaleOrdinal(d3.schemeTableau10);
nodes.forEach(n => {
  n.community = graph.getNodeAttribute(n.id, 'community');
  n.centrality = centrality[n.id];
});
```

---

## Large Graph Rendering (sigma.js, WebGL approaches, 10K+ nodes)

**Sources:** [sigmajs.org](https://www.sigmajs.org/), [sigma.js v3 announcement](https://www.ouestware.com/2024/03/21/sigma-js-3-0-en/), [GitHub](https://github.com/jacomyal/sigma.js/).

### What problem it solves

D3's SVG rendering hits a wall at ~5,000 nodes (DOM overhead). D3 Canvas helps but still relies on CPU for hit detection and drawing. sigma.js uses WebGL to push rendering to the GPU, handling 10K-100K+ nodes with interactive frame rates.

### Architecture (v3)

sigma.js v3 has a clean separation of concerns:
- **Graph model:** graphology (the data layer)
- **Renderer:** WebGL programs for nodes and edges
- **Camera:** zoom/pan state
- **Spatial index:** quadtree for fast hover/click detection

Each visual style (circle node, bordered node, arrow edge) is a "program" -- a pair of vertex/fragment shaders. Custom programs let you draw any shape. v3 uses instanced rendering for better GPU utilization.

### Performance characteristics

| Scale | sigma.js WebGL | D3 SVG | D3 Canvas |
|-------|---------------|--------|-----------|
| 1K nodes | Overkill | Fine | Fine |
| 5K nodes | Smooth | Sluggish | Fine |
| 10K nodes | Smooth | Unusable | Usable |
| 50K nodes | Usable | -- | Slow |
| 100K nodes | Slow but works | -- | -- |

Layout is the bottleneck, not rendering. ForceAtlas2 in a Web Worker (via graphology-layout-forceatlas2) handles ~50K edges before becoming slow. Pre-computed layouts sidestep this entirely.

### D3 integration approach

sigma.js and D3 serve different roles at this scale:

- **Use sigma.js for the main graph canvas** -- it handles zoom, pan, hover, and rendering at scale.
- **Use D3 for overlays** -- HTML tooltips, detail panels, small multiples of subgraphs, axes for hive plots.
- **Use graphology as the shared data layer** -- both sigma.js and your D3 code read from the same graph object.

For the d3-power-tools skill, the recommendation is: mention sigma.js as the escape hatch when D3 Canvas runs out of headroom (>10K nodes), but keep the skill focused on D3-native patterns up to that threshold. The `canvas` and `webgl-rendering` skills already cover GPU acceleration patterns.

### Alternative: deck.gl

For geospatial networks, deck.gl's `GraphLayer` renders millions of edges on a map. Different use case but worth noting for spatial network data.

---

## Community Detection Visualization (Louvain/Leiden + visual encoding)

**Sources:** [graphology-communities-louvain](https://graphology.github.io/standard-library/communities-louvain.html), Traag et al. "From Louvain to Leiden" *Scientific Reports* 2019.

### Algorithms

**Louvain** (Blondel et al. 2008): Greedy modularity optimization. Fast (nearly linear time). The standard for community detection. Available in JavaScript via `graphology-communities-louvain`.

**Leiden** (Traag et al. 2019): Fixes Louvain's major defect -- Louvain can produce badly connected or even disconnected communities, especially on iterative runs. Leiden guarantees connected communities and converges to locally optimal partitions. Runs faster than Louvain. **No JavaScript implementation yet** -- would need WASM compilation from C++ or a port.

### Resolution parameter

Both algorithms take a resolution parameter. Higher resolution = more, smaller communities. This is the main user-facing control. A good visualization lets the user adjust resolution with a slider and see communities re-color in real time.

### Visual encoding patterns

1. **Color by community.** The obvious approach. Use `d3.scaleOrdinal` with a qualitative palette. Works for up to ~12 communities before colors become hard to distinguish. For more communities, use a generated palette (d3-scale-chromatic's `interpolateRainbow` with lightness clamping).

2. **Convex hull overlays.** Draw a semi-transparent convex hull (or d3.polygonHull) around each community's nodes in a force layout. Makes community boundaries explicit. Requires force layout to separate communities (increase `forceCluster` or add a custom clustering force).

3. **Community-aware force layout.** Add a custom force that pulls nodes toward their community centroid. This is the missing piece in most D3 community visualizations -- without it, Louvain assigns colors but force layout scatters communities randomly.

```js
// Custom clustering force
function forceCluster(communities, strength = 0.1) {
  let nodes;
  function force(alpha) {
    const centroids = new Map();
    // Compute community centroids
    nodes.forEach(n => {
      const c = communities[n.id];
      if (!centroids.has(c)) centroids.set(c, { x: 0, y: 0, count: 0 });
      const d = centroids.get(c);
      d.x += n.x; d.y += n.y; d.count++;
    });
    centroids.forEach(d => { d.x /= d.count; d.y /= d.count; });
    // Pull toward centroid
    nodes.forEach(n => {
      const c = centroids.get(communities[n.id]);
      n.vx += (c.x - n.x) * strength * alpha;
      n.vy += (c.y - n.y) * strength * alpha;
    });
  }
  force.initialize = _ => nodes = _;
  return force;
}
```

4. **Nested/hierarchical communities.** Louvain produces a dendrogram of communities at different resolutions. Visualize as a zoomable treemap of communities, or as expandable meta-nodes in a node-link diagram.

5. **Matrix with community ordering.** Sort rows/columns by community assignment. Dense diagonal blocks = communities. Off-diagonal blocks = inter-community connections. This is already partially covered in the skill's matrix reordering section but should be explicitly connected to algorithmic community detection.

---

## Matrix-NodeLink Hybrids (NodeTrix, MatLink)

**Sources:** Henry, Fekete, McGuffin, "NodeTrix: a Hybrid Visualization of Social Networks," IEEE TVCG 13(6):1302-1309, 2007. Henry & Fekete, "MatLink: Enhanced Matrix Visualization for Analyzing Social Networks," INTERACT 2007.

### NodeTrix

**What it is:** Dense subgroups (communities) are shown as adjacency matrices. Connections between groups are shown as node-link edges between the matrices. The user interactively selects groups of nodes and collapses them into matrix blocks.

**What problem it solves:** Real-world social networks are "globally sparse, locally dense." Node-link diagrams become hairballs in the dense regions; matrices lose path information in the sparse global structure. NodeTrix shows each part with its best representation.

**Scale:** Works for networks with clear community structure at 100-1,000 nodes. The number of communities should be manageable (5-30) since each becomes a matrix block.

**D3 implementation approach:**
1. Run community detection (Louvain via graphology)
2. Render each community as a small adjacency matrix (SVG `<rect>` cells)
3. Position matrices using force layout (treat each community as a single node)
4. Draw inter-community edges as curves between matrix borders
5. Interaction: click a matrix to expand it, drag to rearrange

No maintained D3 implementation exists. Would need to be built from primitives.

### MatLink

**What it is:** An adjacency matrix with node-link edges overlaid on the borders. As the user hovers over a cell, paths through that node are highlighted using arcs drawn along the matrix edges.

**What problem it solves:** Path-tracing in standard matrices requires sequential row-column lookups (slow, error-prone). MatLink adds the visual path cues that matrices lack, making it competitive with node-link for path tasks while retaining the matrix's advantages for density and weight comparison.

**D3 implementation approach:** Build the adjacency matrix as usual, then add an arc layer on the borders (similar to arc diagram). On hover, highlight the relevant arcs. This is an overlay -- the matrix remains the primary representation.

### When to use hybrids

- Network has clear community structure with sparse inter-community connections
- Tasks mix density analysis (within communities) and path tracing (between communities)
- Audience needs to see both local and global structure simultaneously

---

## BioFabric and Linear Layouts (alternative to hairball)

**Sources:** Longabaugh, "Combing the hairball with BioFabric," BMC Bioinformatics 13:275, 2012. [biofabric.org](http://www.biofabric.org/). Fuchs et al., "Exploring the Design Space of BioFabric Visualization for Multivariate Network Analysis," Computer Graphics Forum 2024.

### How it works

BioFabric eliminates node overlap entirely by representing:
- **Nodes as horizontal lines** (one row per node)
- **Edges as vertical line segments** connecting two node rows (one column per edge)

The result looks like a barcode or a woven fabric. Node rows are ordered by a breadth-first search from the highest-degree node (visiting neighbors in degree order). Edge columns are ordered by the position of their source node.

### What problem it solves

Every other network visualization struggles with edge crossings in dense graphs. BioFabric has **zero edge crossings by construction** -- edges are vertical segments that never intersect. This means every single edge is individually visible and traceable, even in networks with thousands of edges.

### Strengths

- **No hairball.** Period. Every edge is visible.
- **Edge attributes are encodable.** Each edge has its own column -- color, width, and pattern can encode edge attributes without overlap.
- **Scales to large networks.** The 2024 Fuchs et al. paper explores BioFabric for multivariate network analysis at scale.
- **Node neighborhoods are readable.** A node's horizontal line segment shows all its connections as intersections with vertical edge lines.

### Limitations

- **Unfamiliar.** Users need explanation -- it doesn't look like a network diagram.
- **Path tracing is hard.** Following a path requires jumping between rows, similar to matrix path-tracing.
- **Requires scrolling for large networks.** The layout grows linearly with nodes (rows) and edges (columns).
- **Cluster structure is not visually obvious** unless you pre-order nodes by community.

### D3 implementation

Straightforward with D3:
- Nodes: `<line>` elements, one per row, colored by node attribute
- Edges: `<line>` elements, one per column, colored by edge attribute
- Node-edge connections: small squares at intersections
- Zoom: essential for large networks -- use `d3.zoom()` with both x and y panning

The layout algorithm (BFS ordering) is ~30 lines. The rendering is a simple two-axis grid. The challenge is interaction design -- how to highlight a node's neighborhood, how to show tooltips, how to search.

### When to use BioFabric

- Dense network where node-link is a hairball and you need to see individual edges
- Edge attributes matter (type, weight, timestamp) and need visual encoding
- The audience will spend time exploring (not glancing)
- Network alignment or comparison (Longabaugh extended BioFabric for this)

---

## Decision Guidance (expanded layout selection)

Extended decision table incorporating new techniques:

| Layout | Shows well | Hides | Sweet spot | Key requirement |
|--------|-----------|-------|------------|-----------------|
| Node-link (force) | Clusters, bridges, outliers | Individual edges in dense regions | <500 nodes, <10% density | Exploratory, no prior knowledge |
| Adjacency matrix | All edges, weight patterns, density | Paths, topology | 10-500 nodes, any density | Dense graphs, weight comparison |
| Arc diagram | Long vs short range, ordering effects | Clusters (unless sorted) | 10-500 nodes, ordered axis | Meaningful node order exists |
| Chord diagram | Inter-group flow volume | Individual connections | 5-20 groups | Directed group-to-group flow |
| Sankey | Flow quantities, conservation | Topology, cycles | 10-100 nodes, DAG | Pipeline/flow data |
| **Hive plot** | Structural role patterns, comparison | Free topology | 50-1,000 nodes, 2-5 axes | Known node categorization, reproducibility needed |
| **BioFabric** | Every individual edge, edge attributes | Clusters, paths | 100-5,000 nodes, dense | Need to see every edge, edge attributes matter |
| **NodeTrix** | Community internals + global structure | Scale >30 communities | 100-1,000 nodes, community structure | Globally sparse, locally dense |
| **Community force** | Cluster membership, inter-cluster bridges | Individual edges within clusters | 100-2,000 nodes | Community detection has been run |

### Expanded decision sequence

1. Flow/pipeline with quantities? -> **Sankey**
2. Group-to-group flow with direction? -> **Chord**
3. Node order is meaningful (time, genome)? -> **Arc diagram**
4. Need deterministic, reproducible layout? -> **Hive plot**
5. Need to compare two networks? -> **Hive plot** (same axis mapping)
6. Dense graph, need to see every single edge? -> **BioFabric**
7. Dense graph, need weight comparison? -> **Adjacency matrix**
8. Globally sparse, locally dense with communities? -> **NodeTrix**
9. Need to show community structure? -> **Community force layout** (Louvain + clustering force)
10. Need to find paths or trace connections? -> **Node-link**
11. >10K nodes? -> **sigma.js** (WebGL) or pre-aggregated view

---

## Code Patterns

### Graphology + D3 community-colored force layout

```js
import Graph from 'graphology';
import louvain from 'graphology-communities-louvain';

// Build graphology graph from D3-format data
const graph = new Graph();
data.nodes.forEach(n => graph.addNode(n.id, n));
data.links.forEach(l => graph.addEdge(l.source, l.target));

// Detect communities
const communities = louvain(graph, { resolution: 1.0 });

// Map back to D3 nodes
const colorScale = d3.scaleOrdinal(d3.schemeTableau10);
data.nodes.forEach(n => {
  n.community = communities[n.id];
  n.color = colorScale(n.community);
});

// Add clustering force to simulation
const simulation = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.links).id(d => d.id))
  .force("charge", d3.forceManyBody().strength(-100))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("cluster", forceCluster(communities, 0.15));
```

### Hive plot axis geometry

```js
// 3-axis hive plot
const axes = [0, 120, 240].map(d => d * Math.PI / 180);
const radiusScale = d3.scaleLinear().domain([0, maxDegree]).range([innerRadius, outerRadius]);

// Assign nodes to axes by type, position by degree
nodes.forEach(n => {
  const angle = axes[n.type]; // type: 0, 1, or 2
  const r = radiusScale(n.degree);
  n.x = r * Math.cos(angle);
  n.y = r * Math.sin(angle);
});

// Draw curved links between axes
const hiveLink = (d) => {
  const c1 = [d.source.x, d.source.y];
  const c2 = [d.target.x, d.target.y];
  // Control point at origin for clean curves
  return `M${c1[0]},${c1[1]}Q0,0,${c2[0]},${c2[1]}`;
};
```

### BioFabric layout

```js
// BFS ordering from highest-degree node
function biofabricOrder(nodes, links) {
  const adj = new Map(nodes.map(n => [n.id, []]));
  links.forEach(l => { adj.get(l.source).push(l.target); adj.get(l.target).push(l.source); });

  // Sort neighbors by degree (descending)
  adj.forEach((neighbors, id) => {
    neighbors.sort((a, b) => adj.get(b).length - adj.get(a).length);
  });

  const start = nodes.reduce((a, b) => adj.get(a.id).length > adj.get(b.id).length ? a : b);
  const order = new Map();
  const queue = [start.id];
  let pos = 0;

  while (queue.length > 0) {
    const id = queue.shift();
    if (order.has(id)) continue;
    order.set(id, pos++);
    adj.get(id).forEach(n => { if (!order.has(n)) queue.push(n); });
  }
  // Handle disconnected components
  nodes.forEach(n => { if (!order.has(n.id)) order.set(n.id, pos++); });
  return order;
}

// Render: nodes as horizontal lines, edges as vertical lines
const nodeY = d3.scaleBand().domain(d3.range(nodes.length)).range([0, height]);
const edgeX = d3.scaleBand().domain(d3.range(links.length)).range([0, width]);
```

### Convex hull community overlay

```js
// After force layout stabilizes, draw community hulls
const communities = d3.group(nodes, d => d.community);
const hullPadding = 15;

const hulls = svg.selectAll(".hull")
  .data(Array.from(communities))
  .join("path")
    .attr("class", "hull")
    .attr("d", ([, members]) => {
      const points = members.map(d => [d.x, d.y]);
      const hull = d3.polygonHull(points);
      if (!hull) return null; // <3 points
      return `M${hull.join("L")}Z`;
    })
    .attr("fill", ([key]) => colorScale(key))
    .attr("opacity", 0.1)
    .attr("stroke", ([key]) => colorScale(key))
    .attr("stroke-width", 1.5);
```

---

## References

- Krzywinski et al. (2012) -- "Hive plots -- rational approach to visualizing networks" -- deterministic network layout
- Henry, Fekete, McGuffin (2007) -- "NodeTrix: a Hybrid Visualization of Social Networks" -- matrix-node-link hybrid
- Henry & Fekete (2007) -- "MatLink: Enhanced Matrix Visualization for Analyzing Social Networks" -- matrix with overlaid links
- Longabaugh (2012) -- "Combing the hairball with BioFabric" -- linear edge-first layout
- Fuchs et al. (2024) -- "Exploring the Design Space of BioFabric Visualization for Multivariate Network Analysis" -- extended BioFabric
- Traag, Waltman, van Eck (2019) -- "From Louvain to Leiden: guaranteeing well-connected communities" -- improved community detection
- Blondel et al. (2008) -- "Fast unfolding of communities in large networks" -- Louvain algorithm
- [Graphology](https://graphology.github.io/) -- JavaScript graph analysis library
- [sigma.js](https://www.sigmajs.org/) -- WebGL graph renderer built on graphology
- [graphology-communities-louvain](https://www.npmjs.com/package/graphology-communities-louvain) -- Louvain for JavaScript
- [Mike Bostock's Hive Plot](https://bost.ocks.org/mike/hive/) -- D3 implementation reference
- [d3-radial-axis](https://www.npmjs.com/package/d3-radial-axis) -- radial axis component for hive plots
