# Force Layout: Beyond d3-force

Research into graph layout algorithms and techniques that complement or replace d3.forceSimulation.

## Current Coverage

The existing `skills/force/SKILL.md` covers:

- **Simulation lifecycle**: alpha, cooling, convergence, reheat
- **All built-in forces**: forceManyBody (Barnes-Hut), forceLink, forceCollide, forceCenter, forceX/Y, forceRadial
- **Custom forces**: bounding box, swim lanes, grid snap, cluster pull (velocity update pattern)
- **Clustering**: leader-link approach using forceLink to pull clusters together
- **Tick management**: batched ticks (3 per frame), pre-computed (no animation)
- **Constrained layouts**: beeswarm (fixed axis + collision), multi-foci toggle
- **Drag**: fx/fy pinning, alphaTarget warm/cool cycle
- **Performance**: the 5K cliff, distanceMax, theta tuning, Canvas rendering, Web Worker sketch, d3-force-reuse mention
- **Common pitfalls**: mutated source data, missing .id(), (0,0) pile-up, stale quadtree

**Gaps identified**: UMAP/t-SNE as layout, stress majorization theory, full WebWorker patterns with interactive drag, ForceAtlas2, constraint-based layout (cola.js), pre-computed/server-side layout pipelines, decision guidance for choosing algorithms.

---

## UMAP/t-SNE as Layout (when dimensionality reduction beats force)

### What they do

UMAP (Uniform Manifold Approximation and Projection) and t-SNE (t-distributed Stochastic Neighbor Embedding) are dimensionality reduction algorithms. They project high-dimensional data (gene expressions, embeddings, feature vectors) into 2D by preserving neighborhood structure. The result is a scatterplot where similar items cluster together.

### What they do better than d3-force

- **Handle high-dimensional similarity directly.** d3-force needs an explicit graph (nodes + links). UMAP/t-SNE take a distance matrix or raw feature vectors and produce layout coordinates without needing to construct a network first.
- **Reveal cluster structure in high-dimensional data.** Force layout with forceLink can show graph topology, but it can't discover that 50-dimensional feature vectors form 7 natural clusters. UMAP/t-SNE can.
- **Global structure preservation (UMAP).** UMAP preserves more of the global relationships between clusters than t-SNE, which tends to compress inter-cluster distances.

### When to use

- Your data is high-dimensional (features, embeddings, text vectors) rather than an explicit graph.
- The goal is cluster discovery or similarity exploration, not network topology.
- You have hundreds to tens of thousands of points with feature vectors.
- You want a stable, reproducible layout (UMAP with fixed random seed).

### When NOT to use

- Your data is already a graph with meaningful edges. Use force layout.
- You need the layout to update incrementally as data streams in. UMAP/t-SNE are batch algorithms.
- Exact distances matter. Both algorithms distort distances; only neighborhood relationships are meaningful.

### JavaScript implementations

**umap-js** (Google PAIR): `npm install umap-js`
- Pure JS, no native dependencies
- Step-based API for incremental rendering: `umap.initializeFit(data)`, then loop `umap.step()`, read `umap.getEmbedding()`
- Async API with epoch callback: `umap.fitAsync(data, epochCallback)`
- Parameters: `nNeighbors` (15), `minDist` (0.1), `nEpochs` (200-500)
- Performance: suitable for up to ~50K points in-browser; beyond that, consider server-side

**t-SNE**: Multiple JS implementations exist (tsnejs, bhtsne-js) but most are unmaintained. UMAP is the better choice for new work -- faster, better global structure, more actively maintained.

### D3 integration pattern

```js
import { UMAP } from 'umap-js';

// data is an array of feature vectors: [[f1, f2, ...], [f1, f2, ...], ...]
const umap = new UMAP({ nNeighbors: 15, minDist: 0.1, nEpochs: 400 });
umap.initializeFit(data);

// Animate the embedding as it converges
const xScale = d3.scaleLinear().range([margin.left, width - margin.right]);
const yScale = d3.scaleLinear().range([margin.top, height - margin.bottom]);

function step() {
  if (umap.step()) {
    requestAnimationFrame(step);
  }
  const embedding = umap.getEmbedding();
  xScale.domain(d3.extent(embedding, d => d[0]));
  yScale.domain(d3.extent(embedding, d => d[1]));
  // render with d3 or canvas using embedding[i][0], embedding[i][1]
}
requestAnimationFrame(step);
```

### Sources

- [umap-js (GitHub)](https://github.com/PAIR-code/umap-js)
- [Understanding UMAP (Google PAIR)](https://pair-code.github.io/understanding-umap/)
- [Observable: UMAP-js worker version](https://observablehq.com/@fil/umap-js-worker)

---

## Stress Majorization (d3-force-reuse, convergence improvements)

### What it is

Stress majorization is a mathematical optimization technique from multidimensional scaling (MDS). It minimizes a "stress" function that measures how well pairwise distances in the layout match the graph-theoretic distances (shortest paths). Each iteration is guaranteed to reduce stress monotonically, unlike velocity Verlet (d3-force) which can oscillate.

### What it does better than d3-force

- **Guaranteed convergence.** Iterations monotonically decrease stress. d3-force's annealing can oscillate and may not find a good layout for some graph structures.
- **Better layout quality for medium graphs.** Stress majorization produces layouts where edge lengths more faithfully represent graph distance, giving more meaningful spatial relationships.
- **Deterministic.** Given the same initial positions, stress majorization always converges to the same result. d3-force is sensitive to initial random positions.

### When to use

- Medium-sized graphs (100-5K nodes) where layout quality matters more than animation.
- When you need edge lengths to reflect graph-theoretic distance (not just connectivity).
- When reproducibility is important.
- When you want fast convergence without tuning alpha/decay parameters.

### d3-force-reuse

Not stress majorization per se, but an optimization of the Barnes-Hut N-body calculation in d3-force. Instead of rebuilding the quadtree every tick, it reuses it for ~13 ticks before rebuilding.

- **Performance**: 10-90% speedup depending on graph density, with no measurable quality loss.
- **API**: Drop-in replacement -- `d3.forceManyBodyReuse()` instead of `d3.forceManyBody()`.
- **D3 compatibility**: Works with d3-force v4+.
- **Best for**: Graphs above 1K nodes where forceManyBody is the bottleneck.

```js
import { forceManyBodyReuse } from 'd3-force-reuse';

simulation.force("charge", forceManyBodyReuse()
  .strength(-30)
  .distanceMax(300));
```

### True stress majorization in JS

No standalone JS library implements full stress majorization for graph layout. The closest options:
- **WebCola** (cola.js) uses stress majorization internally as its layout engine.
- **Graphviz neato** uses stress majorization (server-side, not browser).
- Implementing from scratch is feasible for small graphs -- the algorithm is a weighted least-squares solve per iteration.

### Sources

- [d3-force-reuse (GitHub)](https://github.com/twosixlabs/d3-force-reuse)
- [Faster force-directed layouts by reusing force approximations (Two Six blog)](https://twosixtech.com/blog/faster-force-directed-graph-layouts-by-reusing-force-approximations/)
- [Graph Drawing by Stress Majorization (Gansner, Koren, North)](https://www.graphviz.org/documentation/GKN04.pdf)
- [Stress majorization (Wikipedia)](https://en.wikipedia.org/wiki/Stress_majorization)

---

## WebWorker Simulation (off-main-thread patterns)

### Why

At 5K+ nodes, a single d3-force tick exceeds the 16ms frame budget. Running the simulation in a Web Worker keeps the main thread free for rendering and interaction. Even at smaller scales, offloading the simulation eliminates jank during initial convergence.

### Architecture

```
Main Thread                    Worker Thread
-----------                    -------------
postMessage({nodes, links}) -> Initialize simulation
                               simulation.tick() loop
render(positions)           <- postMessage({positions})
drag event                  -> postMessage({drag: {id, x, y}})
                               update fx/fy, reheat
render(positions)           <- postMessage({positions})
```

### Three patterns

**1. Static pre-computation (simplest)**

Worker runs `simulation.tick(300)`, posts final positions once. No interactivity during layout. Good for dashboards, thumbnails, server-like rendering.

**2. Progressive rendering (animated, no interaction)**

Worker posts positions every N ticks. Main thread renders each update. User sees the layout converge but can't drag nodes.

```js
// worker.js
importScripts('https://d3js.org/d3-force.v3.min.js');

self.onmessage = ({ data: { nodes, links } }) => {
  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id))
    .force("charge", d3.forceManyBody().distanceMax(400))
    .force("center", d3.forceCenter())
    .stop();

  for (let i = 0; i < 300; i++) {
    sim.tick();
    if (i % 5 === 0) {
      self.postMessage(nodes.map(d => ({ id: d.id, x: d.x, y: d.y })));
    }
  }
  self.postMessage({ done: true, nodes: nodes.map(d => ({ id: d.id, x: d.x, y: d.y })) });
};
```

**3. Interactive (full drag support)**

Worker runs a continuous tick loop. Main thread sends drag events (node id + coordinates). Worker sets fx/fy and reheats. This is the most complex pattern but provides the best UX.

```js
// worker.js — interactive version
let sim, nodeMap;

self.onmessage = ({ data }) => {
  if (data.type === 'init') {
    const { nodes, links } = data;
    nodeMap = new Map(nodes.map(d => [d.id, d]));
    sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id))
      .force("charge", d3.forceManyBody().distanceMax(400))
      .force("center", d3.forceCenter(data.width / 2, data.height / 2))
      .on("tick", () => {
        self.postMessage(nodes.map(d => ({ id: d.id, x: d.x, y: d.y })));
      });
  }
  if (data.type === 'drag') {
    const node = nodeMap.get(data.id);
    if (!node) return;
    node.fx = data.x;
    node.fy = data.y;
    sim.alpha(0.3).restart();
  }
  if (data.type === 'dragend') {
    const node = nodeMap.get(data.id);
    if (!node) return;
    node.fx = null;
    node.fy = null;
  }
};
```

### Performance considerations

- **Structured clone overhead.** `postMessage` deep-copies objects. For 10K nodes posting `{id, x, y}` every tick, this is ~1-2ms per message. Acceptable.
- **Transferable ArrayBuffers.** For 50K+ nodes, use Float64Arrays and transfer them: `postMessage(buffer, [buffer])`. Transfer is ~29ms vs ~268ms for clone. But the buffer is detached from the sender, so you need double-buffering.
- **Tick throttling.** Don't post every tick. Post every 2-5 ticks, or use requestAnimationFrame on the main thread to pull the latest state.
- **d3-force in a Worker.** d3-force has no DOM dependency. It works in a Worker with `importScripts()` or by bundling just `d3-force` (not all of d3, which pulls in d3-selection with DOM refs).

### Sources

- [Force-directed web worker (Observable, official D3)](https://observablehq.com/@d3/force-directed-web-worker)
- [Interactive Force-Directed Web Worker (Fabian Iwand)](https://observablehq.com/@mootari/interactive-force-directed-web-worker)
- [d3-force WebWorker layout (gist)](https://gist.github.com/zakjan/b370057873fec41a5d4449d12c3e46e6)
- [Scale up your D3 graph visualisation, part 2 (Neo4j blog)](https://medium.com/neo4j/scale-up-your-d3-graph-visualisation-part-2-2726a57301ec)

---

## ForceAtlas2 (continuous layout, Gephi-style)

### What it is

ForceAtlas2 is a force-directed algorithm designed by the Gephi team, published in PLOS ONE (2014). It combines Barnes-Hut approximation, degree-dependent repulsive force, and adaptive local/global temperatures. It was designed for "handy network visualization" -- meaning the user can drag nodes, add/remove data, and the layout continuously adapts.

### What it does better than d3-force

- **Degree-dependent repulsion.** Hubs naturally get more space, preventing the "hairball in the center" problem common with uniform charge.
- **LinLog mode.** Optional energy model where edge attraction is logarithmic, producing tighter, more distinct clusters. d3-force has no equivalent.
- **Gravity model.** Prevents disconnected components from drifting to infinity without a centering force, and "strong gravity" mode pulls high-degree nodes toward the center.
- **No cooling schedule.** ForceAtlas2 uses per-node adaptive temperatures (local speed limits) and a global adaptive speed. It runs continuously without alpha decay until you stop it. This makes it better for exploratory, interactive use.
- **Better cluster separation.** The combination of degree-dependent repulsion, LinLog mode, and gravity consistently produces cleaner community structure.

### When to use

- Exploratory network analysis where the user wants to interactively adjust the layout.
- Graphs with clear community structure that you want to visually separate.
- Social networks, citation networks, co-occurrence graphs.
- When you want Gephi-quality layouts in the browser.

### JavaScript implementation: graphology-layout-forceatlas2

`npm install graphology-layout-forceatlas2`

- Works with the graphology graph library (not d3 directly, but integration is straightforward).
- Synchronous and WebWorker versions included.
- Barnes-Hut optimization for O(n log n) repulsion.
- Key parameters: `gravity` (1), `scalingRatio` (1), `linLogMode` (false), `strongGravityMode` (false), `barnesHutOptimize` (true for >2000 nodes), `barnesHutTheta` (0.5), `adjustSizes` (prevent overlap).

```js
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';

const graph = new Graph();
// ... add nodes and edges ...

// Pre-assign random positions (required)
graph.forEachNode(node => {
  graph.setNodeAttribute(node, 'x', Math.random() * 100);
  graph.setNodeAttribute(node, 'y', Math.random() * 100);
});

// Synchronous: run N iterations
forceAtlas2.assign(graph, { iterations: 500, settings: {
  gravity: 1,
  scalingRatio: 2,
  linLogMode: true,
  barnesHutOptimize: true
}});

// Read positions back for D3 rendering
graph.forEachNode((node, attrs) => {
  // attrs.x, attrs.y are the layout coordinates
});
```

**WebWorker version:**

```js
import FA2Layout from 'graphology-layout-forceatlas2/worker';

const layout = new FA2Layout(graph, { settings: { gravity: 1 } });
layout.start();
// ... layout runs continuously in background ...
layout.stop();
```

### D3 integration

ForceAtlas2 via graphology produces x/y coordinates. Use these as the data for a standard D3 rendering pipeline (Canvas or SVG). The layout engine is separate from the renderer -- build the graph in graphology, run FA2, then pass positions to D3 scales.

Alternatively, use sigma.js for WebGL rendering of the graphology graph directly, which handles 100K+ nodes.

### Sources

- [graphology-layout-forceatlas2 (docs)](https://graphology.github.io/standard-library/layout-forceatlas2.html)
- [ForceAtlas2 paper (PLOS ONE)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0098679)
- [graphology-layout-forceatlas2 (npm)](https://www.npmjs.com/package/graphology-layout-forceatlas2)
- [sigma.js](https://www.sigmajs.org/)

---

## Constraint-Based Layout (cola.js, WebCola, alignment/grouping)

### What it is

WebCola (cola.js) is a constraint-based layout library that uses stress majorization with separation constraints. Instead of just "push apart and pull together" (force-directed), it allows you to specify that nodes must be aligned, ordered, grouped into non-overlapping containers, or maintain minimum separations.

### What it does better than d3-force

- **Alignment constraints.** "These 5 nodes must share the same y-coordinate." Impossible with pure force layout.
- **Ordering constraints.** "Node A must be left of Node B." Useful for DAGs, workflows, timelines.
- **Group constraints.** Non-overlapping bounding boxes around node groups. Groups can be nested.
- **Convergence.** Uses stress majorization internally -- guaranteed monotonic convergence to a local optimum, unlike d3-force's annealing.
- **Overlap removal.** Built-in constraint to prevent node-label overlap (more principled than forceCollide).

### When to use

- Organizational charts, system architecture diagrams, workflow graphs.
- Any graph where some nodes must align (e.g., same department = same row).
- Layered/hierarchical graphs that aren't strict trees.
- When you need grouping boxes around clusters.
- When forceCollide isn't enough for overlap prevention.

### When NOT to use

- Large graphs (>1K nodes). Constraint solving is more expensive than d3-force.
- When you don't have structural constraints -- plain force layout is simpler and faster.
- Real-time streaming data. WebCola doesn't have a streaming/incremental mode.

### D3 compatibility

WebCola provides a d3 adaptor that's nearly a drop-in replacement:

```js
import * as cola from 'webcola';

const layout = cola.d3adaptor(d3)
  .size([width, height])
  .nodes(nodes)
  .links(links)
  .constraints(constraints)
  .groups(groups)
  .avoidOverlaps(true)
  .start(10, 15, 20);  // unconstrained, user-constrained, all-constraints iterations

layout.on("tick", render);
```

### Constraint types

```js
// Separation: node 0 must be at least 50px left of node 1
{ axis: "x", left: 0, right: 1, gap: 50 }

// Alignment: nodes 1, 2, 3 aligned on x-axis
{ type: "alignment", axis: "x", offsets: [
  { node: 1, offset: 0 },
  { node: 2, offset: 0 },
  { node: 3, offset: 0 }
]}

// Groups: non-overlapping bounding boxes
const groups = [
  { leaves: [0, 1, 2], padding: 10 },
  { leaves: [3, 4], padding: 10 }
];
```

### SetCoLa

A higher-level DSL from UW Data for specifying constraints based on node properties rather than indices. A SetCoLa compiler generates WebCola constraints.

### Sources

- [cola.js (project page)](https://ialab.it.monash.edu/webcola/)
- [WebCola (GitHub)](https://github.com/tgdwyer/WebCola)
- [WebCola constraints wiki](https://github.com/tgdwyer/WebCola/wiki/Constraints)
- [SetCoLa (GitHub)](https://github.com/uwdata/setcola)
- [Observable: Hello CoLa with a constraint](https://observablehq.com/@tgdwyer/hello-cola-with-a-constraint)

---

## Pre-computed Layout (server-side, static snapshots)

### When to use

- The graph doesn't change (reference diagrams, published figures).
- The graph is too large for real-time browser layout (50K+ nodes).
- You need deterministic, reproducible positioning.
- Server-side rendering (Node.js, PDF generation).

### Approaches

**1. d3-force in Node.js**

d3-force has no DOM dependency. Run it server-side:

```js
import { forceSimulation, forceLink, forceManyBody, forceCenter } from 'd3-force';

const sim = forceSimulation(nodes)
  .force("link", forceLink(links).id(d => d.id))
  .force("charge", forceManyBody())
  .force("center", forceCenter(0, 0))
  .stop();

sim.tick(300);
// nodes now have x, y -- serialize to JSON
```

**2. Graphviz (neato/sfdp)**

For production graph layout at scale. `neato` uses stress majorization, `sfdp` uses a multilevel force algorithm that handles 100K+ nodes. Output DOT with coordinates, parse in JS.

**3. UMAP/t-SNE server-side**

Python's `umap-learn` is much faster than `umap-js` for large datasets. Pre-compute embeddings, serve as JSON coordinates.

**4. Static snapshots with interaction**

Pre-compute layout, ship coordinates as part of the data. Use d3-zoom for pan/zoom, quadtree for hover/click hit detection. No simulation needed at runtime -- just a fancy scatterplot at that point.

---

## Decision Guidance (which algorithm for which goal)

| Goal | Best algorithm | Why |
|------|---------------|-----|
| **Explore a network interactively** | d3-force (< 5K) or ForceAtlas2 (any size) | Continuous, draggable, reveals topology |
| **Show community structure** | ForceAtlas2 with LinLog mode | Degree-dependent repulsion + log attraction separates communities |
| **High-dimensional similarity** | UMAP | Preserves neighborhood structure from feature vectors |
| **Constrained diagram** (alignment, ordering, groups) | WebCola | Only option that supports structural constraints |
| **Fast convergence, quality layout** | Stress majorization (WebCola) | Monotonic convergence, faithful edge lengths |
| **10K+ nodes, browser** | ForceAtlas2 (worker) + sigma.js/WebGL | FA2 worker + WebGL rendering |
| **50K+ nodes** | Server-side (sfdp, UMAP) + static render | Too expensive for real-time browser layout |
| **Collision-only layout** (beeswarm, bubble) | d3-force with forceX/Y + forceCollide | d3-force is perfect for this; no graph structure needed |
| **Animated transitions** | d3-force | Built-in alpha/tick animation loop |
| **Reproducible, static** | Pre-computed (any algorithm, .stop().tick(N)) | No animation variance |

### Decision tree

```
Is your data a graph (nodes + edges)?
  YES -> Do you need alignment/ordering/grouping constraints?
    YES -> WebCola
    NO  -> How many nodes?
      < 5K   -> d3-force (simple, well-documented)
      5-50K  -> ForceAtlas2 in WebWorker
      50K+   -> Server-side layout, static render
  NO -> Is it high-dimensional feature data?
    YES -> UMAP (browser < 50K points, server otherwise)
    NO  -> Is it a 1D/2D distribution?
      YES -> d3-force for collision avoidance (beeswarm)
      NO  -> Probably not a force layout problem
```

---

## Code Patterns

### Pattern 1: d3-force-reuse drop-in (simplest perf win)

```js
import { forceManyBodyReuse } from 'd3-force-reuse';

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id))
  .force("charge", forceManyBodyReuse().strength(-50).distanceMax(400))
  .force("center", d3.forceCenter(width / 2, height / 2));
```

### Pattern 2: UMAP to D3 scatterplot

```js
import { UMAP } from 'umap-js';

const umap = new UMAP({ nNeighbors: 15, minDist: 0.1 });
const embedding = await umap.fitAsync(featureMatrix, epoch => {
  // Optional: render intermediate state every 10 epochs
  if (epoch % 10 === 0) renderEmbedding(umap.getEmbedding());
});

function renderEmbedding(coords) {
  const xScale = d3.scaleLinear()
    .domain(d3.extent(coords, d => d[0]))
    .range([margin.left, width - margin.right]);
  const yScale = d3.scaleLinear()
    .domain(d3.extent(coords, d => d[1]))
    .range([margin.top, height - margin.bottom]);

  ctx.clearRect(0, 0, width, height);
  for (let i = 0; i < coords.length; i++) {
    ctx.beginPath();
    ctx.arc(xScale(coords[i][0]), yScale(coords[i][1]), 3, 0, Math.PI * 2);
    ctx.fillStyle = colorScale(labels[i]);
    ctx.fill();
  }
}
```

### Pattern 3: ForceAtlas2 with graphology, rendered by D3

```js
import Graph from 'graphology';
import FA2Layout from 'graphology-layout-forceatlas2/worker';

const graph = new Graph();
nodes.forEach(n => graph.addNode(n.id, { x: Math.random() * 1000, y: Math.random() * 1000, ...n }));
links.forEach(l => graph.addEdge(l.source, l.target));

const fa2 = new FA2Layout(graph, {
  settings: { gravity: 1, scalingRatio: 2, linLogMode: true, barnesHutOptimize: true }
});
fa2.start();

// Render loop reads positions from graphology
function render() {
  ctx.clearRect(0, 0, width, height);
  graph.forEachEdge((edge, attrs, source, target, sourceAttrs, targetAttrs) => {
    ctx.beginPath();
    ctx.moveTo(xScale(sourceAttrs.x), yScale(sourceAttrs.y));
    ctx.lineTo(xScale(targetAttrs.x), yScale(targetAttrs.y));
    ctx.stroke();
  });
  graph.forEachNode((node, attrs) => {
    ctx.beginPath();
    ctx.arc(xScale(attrs.x), yScale(attrs.y), 4, 0, Math.PI * 2);
    ctx.fill();
  });
  if (fa2.isRunning()) requestAnimationFrame(render);
}
requestAnimationFrame(render);
```

### Pattern 4: WebCola with D3 adaptor

```js
import * as cola from 'webcola';

const layout = cola.d3adaptor(d3)
  .size([width, height])
  .nodes(nodes)
  .links(links)
  .avoidOverlaps(true)
  .constraints([
    // Enforce left-to-right ordering for a DAG
    ...dagEdges.map(e => ({ axis: "x", left: e.source, right: e.target, gap: 80 }))
  ])
  .groups([
    { leaves: departmentA_indices, padding: 15 },
    { leaves: departmentB_indices, padding: 15 }
  ])
  .start(20, 20, 30);

layout.on("tick", () => {
  // Standard D3 SVG update
  linkSel.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
         .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  nodeSel.attr("cx", d => d.x).attr("cy", d => d.y);
});
```

### Pattern 5: WebWorker d3-force with interactive drag

```js
// main.js
const worker = new Worker('force-worker.js');

worker.postMessage({ type: 'init', nodes, links, width, height });

worker.onmessage = ({ data }) => {
  if (data.type === 'tick') {
    // Update a Map for O(1) lookup during render
    for (const pos of data.positions) nodePositions.set(pos.id, pos);
    render();
  }
};

// Drag handler sends events to worker
d3.select(canvas).call(d3.drag()
  .subject(event => findNode(event.x, event.y))  // quadtree on main thread positions
  .on("start", (event, d) => worker.postMessage({ type: 'drag', id: d.id, x: event.x, y: event.y }))
  .on("drag", (event, d) => worker.postMessage({ type: 'drag', id: d.id, x: event.x, y: event.y }))
  .on("end", (event, d) => worker.postMessage({ type: 'dragend', id: d.id }))
);
```

### Pattern 6: Float64Array transfer for 50K+ nodes

```js
// worker.js — high-performance position transfer
const STRIDE = 3;  // id_index, x, y
let buffer = new Float64Array(nodes.length * STRIDE);

function postPositions() {
  for (let i = 0; i < nodes.length; i++) {
    buffer[i * STRIDE] = i;
    buffer[i * STRIDE + 1] = nodes[i].x;
    buffer[i * STRIDE + 2] = nodes[i].y;
  }
  // Transfer ownership — buffer is detached after this call
  self.postMessage(buffer.buffer, [buffer.buffer]);
  // Allocate new buffer for next tick
  buffer = new Float64Array(nodes.length * STRIDE);
}
```
