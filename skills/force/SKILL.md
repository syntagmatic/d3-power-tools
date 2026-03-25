---
name: force
description: "D3.js force-directed layouts and physics simulations: node positioning with forces, collision detection, clustering, constrained layouts, and drag interaction. Use this skill whenever the user wants to build force-directed graphs, network node-link diagrams, physics-based layouts, bubble collision charts, or interactive simulations. Also use when the user mentions d3.forceSimulation, forceManyBody, forceLink, forceCollide, forceCenter, forceX, forceY, forceRadial, alpha decay, tick management, velocity Verlet, node dragging with fx/fy, force-directed clustering, or scaling force layouts to 10K+ nodes."
---

# Force Simulation

Force layout answers one question: where should nodes go when the only structure is connections? It works by treating links as springs and nodes as charged particles, then letting physics find a readable arrangement. For network graph types (Sankey, chord, arc), see `network`. For Canvas rendering patterns, see `canvas`. For GPU at 100K+, see `webgl`.

## When Force Layout Is the Wrong Choice

**Trees and hierarchies.** If your data has a root, use `d3.tree`, `d3.treemap`, or `d3.partition`. These algorithms exploit parent-child structure to produce stable, deterministic layouts instantly. Force layout ignores that structure and produces a hairball where a clean tree would communicate better.

**Small, static graphs (< 20 nodes).** A hand-tuned or algorithmically-placed layout (arc diagram, adjacency matrix, or even a table) often communicates more clearly. Force layout adds animation and non-determinism that distracts when the graph is simple enough to read at a glance.

**Dense graphs.** When edge count >> node count, force layout produces a tangle. Consider an adjacency matrix (see `network`) — it shows every connection without overlap.

**When position should encode data.** If nodes have meaningful x/y coordinates (geographic, temporal, categorical), use `forceX`/`forceY` to constrain them rather than letting physics decide. At that point you're using force for collision avoidance, not layout — which is fine, but know the difference.

## Alpha, Cooling, and Convergence

The simulation has a temperature (`alpha`) that decays each tick. When alpha drops below `alphaMin`, the simulation stops.

```js
simulation
  .alpha(1)              // current temperature (0–1)
  .alphaMin(0.001)       // stop threshold
  .alphaDecay(0.0228)    // default ~300 ticks to settle
  .alphaTarget(0)        // equilibrium target
  .velocityDecay(0.4);   // friction (0 = none, 1 = freeze)
```

- Higher `alphaDecay` converges faster but produces less accurate layouts — nodes don't have time to find good positions.
- `alphaTarget > 0` means the simulation never stops. Useful for streaming data, but drains battery on mobile — always set it back to 0 when interaction ends.
- Higher `velocityDecay` damps oscillation. Raise it (0.6–0.8) when nodes jitter instead of settling.

### Reheat

```js
simulation.alpha(1).restart();   // full reheat — new data, layout changes
simulation.alpha(0.3).restart(); // gentle nudge — minor adjustments
```

Full reheat reshuffles everything. Use 0.3–0.5 for changes where you want the existing layout to adapt rather than restart from scratch.

## Force Tuning

### forceManyBody — Barnes-Hut N-body

O(n log n) via quadtree approximation. The key parameters beyond defaults:

```js
d3.forceManyBody()
  .strength(-30)         // more negative = more repulsion. -100 to -300 for dense graphs
  .distanceMax(300)      // stop calculating beyond this radius — critical for perf at 1K+
  .theta(0.9);           // Barnes-Hut accuracy: 1.5 = faster but coarser grouping
```

Per-node strength lets hubs push harder: `.strength(d => d.isHub ? -200 : -30)`

### forceLink

The default strength formula is inversely proportional to the lesser degree of the two endpoints — loosely-connected nodes pull harder. Override `distance` to encode weight:

```js
d3.forceLink(links).id(d => d.id)
  .distance(d => d.weight ? 30 / d.weight : 100)
  .iterations(1);  // higher = more rigid links, but costs linearly
```

### forceCollide

```js
d3.forceCollide().radius(d => d.r + 2).strength(0.7).iterations(2);
```

2–3 iterations prevent overlap but cost proportionally. One iteration is usually enough if nodes aren't densely packed.

## Custom Forces

A force is a function called each tick with the current `alpha`. Usually it modifies `d.vx` and `d.vy` — the Verlet integrator handles `d.x`/`d.y`. The exception is hard boundary clamping, where you set position directly and zero velocity:

```js
function forceBoundingBox(x0, y0, x1, y1) {
  let nodes;
  function force() {
    for (const d of nodes) {
      if (d.x < x0) { d.x = x0; d.vx = 0; }
      if (d.x > x1) { d.x = x1; d.vx = 0; }
      if (d.y < y0) { d.y = y0; d.vy = 0; }
      if (d.y > y1) { d.y = y1; d.vy = 0; }
    }
  }
  force.initialize = n => { nodes = n; };
  return force;
}
```

### Common Variants — Same Pattern, Different Velocity Update

**Swim lanes**: `d.vy += (laneY(d) - d.y) * alpha * strength;`

**Grid snap**: `d.vx += (Math.round(d.x / cell) * cell - d.x) * alpha * strength;`

**Cluster pull**: `d.vx += (center.x - d.x) * alpha * strength;`

## Clustering via Leader Links

Link non-leaders to the largest node in their cluster. This uses `forceLink` to pull clusters together — simpler and more stable than a custom cluster force:

```js
const leaders = new Map(clusters.map(([key, group]) =>
  [key, group.reduce((a, b) => a.value > b.value ? a : b)]));
const clusterLinks = nodes.filter(d => d !== leaders.get(d.cluster))
  .map(d => ({ source: d, target: leaders.get(d.cluster) }));
simulation.force("clusterLinks", d3.forceLink(clusterLinks).strength(0.05).distance(50));
```

## Tick Management

### Batched — Faster Convergence, Still Animated

Run multiple simulation ticks per animation frame. The viewer sees faster settling without losing the physics-in-motion feel:

```js
simulation.on("tick", null);
function animate() {
  for (let i = 0; i < 3; i++) simulation.tick();
  render();
  if (simulation.alpha() > simulation.alphaMin()) requestAnimationFrame(animate);
}
simulation.restart();
requestAnimationFrame(animate);
```

### Pre-computed (No Animation)

Skip animation entirely when the viewer doesn't need to see the layout form — static views, thumbnails, server-side rendering:

```js
simulation.stop();
simulation.tick(300);
render();
```

## Constrained Layouts

### Fixed Axis (Beeswarm)

One axis encodes data, the other uses force for jittering. Strong x-force keeps nodes on their data position; weak y-force and collision prevent overlap:

```js
simulation
  .force("x", d3.forceX(d => xScale(d.value)).strength(0.8))
  .force("y", d3.forceY(height / 2).strength(0.05))
  .force("collide", d3.forceCollide(d => d.r + 1));
```

### Multi-foci Toggle

Switch between grouped and combined views by changing the force target. Moderate alpha (0.5) preserves spatial memory so the viewer can track which node went where:

```js
simulation.force("x", d3.forceX(
  grouped ? d => groupCenters.get(d.group).x : width / 2
).strength(grouped ? 0.1 : 0.02));
simulation.alpha(0.5).restart();
```

## The 5K Performance Cliff

The N-body force is O(n log n) per tick, but the constant factor is large — at ~5K nodes with default settings, a single tick takes longer than a 16ms frame budget, and the layout visibly stutters. The bottleneck is `forceManyBody`, which rebuilds a quadtree and walks it for every node on every tick.

**What to do about it, in order of effort:**

1. **Set `distanceMax`** (300–500). Nodes beyond this range contribute negligible force but still cost quadtree traversal. This alone often doubles throughput.
2. **Raise `theta`** to 1.5. More aggressive Barnes-Hut approximation — clusters further away are treated as single points sooner. Layout quality barely suffers.
3. **Switch to Canvas.** SVG DOM updates are O(n) per tick on top of the simulation cost. Canvas `beginPath`/`arc` batches are an order of magnitude cheaper.
4. **Batch ticks** (3 per frame). The simulation converges in ~100 frames instead of ~300, reducing total work.
5. **Pre-compute** when animation isn't needed. `simulation.stop(); simulation.tick(300);` runs synchronously — no rendering overhead at all.
6. **Web Worker offloading.** Move the simulation off the main thread entirely. Post node positions back every N ticks for rendering:

```js
// force-worker.js
self.onmessage = (e) => {
  const { nodes, links, width, height } = e.data;
  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id))
    .force("charge", d3.forceManyBody().distanceMax(300).theta(1.5))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .stop();
  for (let i = 0; i < 300; i++) {
    sim.tick();
    if (i % 10 === 0) self.postMessage({ nodes, done: false });
  }
  self.postMessage({ nodes, done: true });
};
```

At 10K+ nodes, consider `d3-force-reuse` (drops `forceManyBody` cost by reusing the quadtree across ticks instead of rebuilding every tick) or switch to WebGL rendering (see `webgl`).

## Common Pitfalls

**Mutated source data.** Simulation writes `x, y, vx, vy, index` onto your objects. Clone first: `data.map(d => ({...d}))`.

**Missing `.id()` on forceLink.** String IDs (`{ source: "a", target: "b" }`) require `.id(d => d.id)`. Without it, D3 treats source/target as array indices and you get silent wrong connections.

**Nodes pile at (0, 0).** Missing `forceCenter` or `forceX`/`forceY` — nothing pushes nodes apart from the origin.

**Simulation stops too early.** Decrease `alphaDecay` or set `alphaTarget` slightly above 0 during interaction.

**Simulation never stops.** `alphaTarget > alphaMin` runs forever. Always set `alphaTarget(0)` when interaction ends.

**Drag doesn't work.** Three requirements: (1) set `fx`/`fy` on drag start, (2) call `alphaTarget(0.3).restart()` to keep the sim warm, (3) set `alphaTarget(0)` on drag end.

**Links cross.** `forceLink` is a spring, not a routing algorithm. You can reduce crossings by increasing charge strength or collision radii, but force layout will never guarantee planar drawing.

**Stale quadtree.** If you maintain a quadtree for hit detection, rebuild it every tick — nodes move each frame. A stale quadtree causes hover/click misses in exactly the places where the layout shifted most.

## References

- [D3 Force](https://d3js.org/d3-force)
- [Force-Directed Graph](https://observablehq.com/@d3/force-directed-graph)
- [d3-force-reuse](https://github.com/twosixlabs/d3-force-reuse) — quadtree reuse for faster N-body
- [Clustered Force Layout](https://observablehq.com/@d3/clustered-force-layout)
