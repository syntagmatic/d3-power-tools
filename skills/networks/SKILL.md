---
name: networks
description: "Visualize relationships and flows with D3: choosing node-link vs adjacency matrix vs arc diagram vs chord (d3.chord, d3.ribbon) vs Sankey (d3-sankey) vs hive plot; dependency graphs, weighted and directed edges, hairball reduction, communities, temporal networks. Force-directed layout: forceSimulation, forceManyBody, forceLink, forceCollide, forceX/forceY, forceRadial, alpha decay, tick management, drag with fx/fy, clustering, beeswarm, Web Worker layout, 10K+ nodes."
---

# Networks

Two judgments decide a network chart. First, which form: the layout decides whether the viewer can see clusters, paths, flow volume or density, and node-link is the default far more often than it's the right answer. Second, if it is node-link, how to run the force simulation so it settles into something readable and stays responsive.

## Should this be a network at all?

Use a table, list or summary instead when:

- connectivity is random-like (no communities): force gives a uniform blob, a sorted adjacency list says the same;
- relationships are uniform (same neighbors, same weights): there's no signal;
- the question is "show me everything" on hundreds of nodes, with nothing to find;
- the data has a root: use tree, treemap or partition, which lay out instantly and deterministically;
- it's under ~20 nodes and static: an arc diagram, matrix or table often reads faster than animated physics.

## Which network form

| If the data / task is... | Use | Sweet spot | Hides |
|---|---|---|---|
| quantities moving through stages (budgets, funnels, energy) | **Sankey** | 10-100 nodes, DAG | topology, cycles |
| flow between a few groups, direction and volume matter | **Chord** | 5-20 groups | individual edges |
| nodes with a meaningful order (time, sequence, genome position) | **Arc diagram** | 10-500 nodes | clusters unless sorted |
| dense (>~30% of possible edges) or comparing edge weights | **Adjacency matrix** | 10-500 nodes, any density | paths |
| tracing paths, finding bridges, clusters, outliers | **Node-link (force)** | <500 nodes, <10% density, <~2K edges | edges in dense regions |
| comparing networks, role questions, reproducible figure | **Hive plot** | 50-1K nodes, 2-5 axes | free topology |
| >10K nodes | node-link on canvas/WebGL, or sigma.js with D3 overlays | | |

Matrix vs node-link (Ghoniem 2004, Okoe 2019): matrices win on cluster detection and weight comparison once the graph is dense; node-link wins on path tracing even when dense, because following a path in a matrix means row-to-column lookups.

Force layout by reflex is the most common mistake. Flow volume wants a Sankey; density wants a matrix; positions that encode data (time, geography, category) want `forceX`/`forceY` with collision, which is force as a de-overlapper, not as layout.

## Before any layout: validate

Real graph data has dangling references, self-loops, duplicate edges and disconnected components. They fail silently: nodes at (0, 0), missing links, NaN coordinates. Run `scripts/validate-network.js` first. Undirected data in a matrix must be symmetric.

## Node-link encoding

- Edge weight: stroke width on `scaleSqrt` (0.5-6px), plus sequential color on the same domain for redundancy.
- At most two channels per node (e.g. size + color). Border, icon and label on top overwhelm.
- Arrowheads: `refX` is per marker, not per link. For variable radii, trim the path end to the target's boundary. Use `markerUnits="userSpaceOnUse"` or markers scale with stroke width.
- Hairball: threshold by weight → top-k edges per node → aggregate communities → switch to a matrix. Lowering opacity is not a fix.
- Communities: D3 has no graph algorithms. Use graphology + Louvain for ids, then color, sort the matrix, or hull them. Hulls need a cluster force, or members scatter.

## Force simulation

### Lifecycle

`alpha` is temperature. It decays by `alphaDecay` each tick toward `alphaTarget` and the timer stops when it falls below `alphaMin`. Defaults (1, 0.0228, 0, 0.001) give ~300 ticks.

| Situation | Do |
|---|---|
| new data, structural change | `alpha(1).restart()` |
| filter, small update, want layout to adapt | `alpha(0.3-0.5).restart()` |
| drag in progress | `alphaTarget(0.3).restart()` on start; `alphaTarget(0)` on end |
| nodes jitter instead of settling | raise `velocityDecay` to 0.6-0.8 |
| settles into a poor layout | lower `alphaDecay` (more ticks) |
| streaming data | small `alphaTarget`, and reset it to 0 when idle (it drains mobile batteries) |

### Which forces

| Goal | Forces |
|---|---|
| general graph | `forceLink().id(d => d.id)` + `forceManyBody` + `forceCenter` |
| position encodes data (beeswarm, timeline) | strong `forceX` (0.8) on the data axis, weak `forceY` (0.05), `forceCollide(r + 1)` |
| grouped / ungrouped toggle | `forceX`/`forceY` to group centers; switch targets and `alpha(0.5)` to preserve spatial memory |
| clusters | leader links (each node linked to its cluster's largest node, strength 0.05) or a custom cluster-pull force |
| keep nodes on screen | custom bounding-box force that clamps `x`/`y` and zeroes velocity |
| bubbles without overlap | `forceCollide` with 2-3 iterations when packed tight |

Starting parameters by graph shape:

| Shape | charge | link distance | extras |
|---|---|---|---|
| sparse, tree-like (degree 1-3) | -200 | 80 | no collision needed |
| dense communities (50-500 nodes) | -80, `distanceMax(250)` | 30 | link strength 0.3 intra / 0.01 inter, `forceCollide(r + 1)` |
| bipartite | -30 | 100 | `forceX` to two columns (0.4), weak `forceY` |
| hub-and-spoke | -300 hubs, -30 leaves | 60 hub, 30 leaf | per-node charge |

### Drag

Set `fx`/`fy` on start and on every drag event, warm with `alphaTarget(0.3).restart()`, and on end set `alphaTarget(0)` and null `fx`/`fy` (keep them if pinning is a feature). Missing any of the three steps makes drag feel dead or leaves the sim running forever.

### Large graphs and precomputing

| Nodes / need | Approach |
|---|---|
| <1K, animated | defaults, SVG |
| 1K-5K | `distanceMax(300-500)`, canvas rendering, 3 ticks per frame |
| ~5K+ | `theta(1.5)`, `d3-force-reuse`, simulation in a Web Worker |
| layout doesn't need to be watched | `simulation.stop().tick(n)` then render once, or in a worker, or offline and ship the x/y |
| 5K-50K | ForceAtlas2 in a worker |
| 50K+ | server-side layout (Graphviz `sfdp`), static render |

The cliff at ~5K is `forceManyBody` rebuilding its quadtree every tick; one tick blows the 16ms frame. SVG adds an O(n) DOM update per tick on top. In a worker, d3-force needs d3-dispatch, d3-quadtree and d3-timer too, so load the full d3 bundle.

Tick count to cool from alpha 1 (use it instead of a magic 300):

```js
const n = Math.ceil(Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay()));
```

## Traps

- The simulation mutates your objects (`x, y, vx, vy, index`, and link endpoints become node objects). Clone input: `data.map(d => ({...d}))`.
- String ids without `forceLink().id(d => d.id)` are read as array indices: wrong edges, no error.
- Everything in the top-left corner: nodes start around (0, 0). Add `forceCenter` or `forceX`/`forceY`.
- Never stops: `alphaTarget` left above `alphaMin`.
- Driving ticks manually without `simulation.stop()`: the internal timer ticks too. Manual `tick()` fires no tick events.
- Hit-test quadtree built once goes stale as nodes move. Rebuild per tick, or use `simulation.find(x, y, r)`.
- d3-sankey throws on cycles. Remove back edges (DFS) or use d3-sankey-circular.
- Sankey nodes named only by value ("Other" in two columns) merge into one node and create a cycle. Prefix with the column.
- Force never guarantees few crossings. If crossings matter, use arc with ordering, or a matrix.

## References

- `references/network.md`: matrix ordering, arc ordering, chord matrix building and labels, Sankey from tabular data and cycles, hive plots, arrowheads, parallel edges, labels, hairball fixes, temporal networks, accessibility.
- `references/force.md`: cooling math, force parameters, custom forces (bounding box, lanes, grid), leader-link clustering, batched ticks, worker patterns and buffer transfer, alternatives (ForceAtlas2, WebCola, UMAP, sfdp).
- `scripts/validate-network.js`: graph validation. `scripts/spatial-keyboard-nav.js`: arrow-key focus on canvas node layouts.
- `examples/`: `adjacency-matrix.html`, `arc-diagram.html`, `chord-diagram.html`, `force.html`, `hybrid-canvas-svg.html` (canvas nodes + SVG interaction).
