---
name: force-simulation
description: "D3.js force-directed layouts and physics simulations: node positioning with forces, collision detection, clustering, constrained layouts, and drag interaction. Use this skill whenever the user wants to build force-directed graphs, network node-link diagrams, physics-based layouts, bubble collision charts, or interactive simulations. Also use when the user mentions d3.forceSimulation, forceManyBody, forceLink, forceCollide, forceCenter, forceX, forceY, forceRadial, alpha decay, tick management, velocity Verlet, node dragging with fx/fy, force-directed clustering, or scaling force layouts to 10K+ nodes."
---

# Force Simulation

Patterns for force-directed layouts with `d3.forceSimulation`. For network graph types (Sankey, chord, arc), see `network-visualization`. For Canvas rendering, see `canvas`. For GPU at 100K+, see `webgl-rendering`.

## Alpha, Cooling, and Convergence

```js
simulation
  .alpha(1)              // current temperature (0–1)
  .alphaMin(0.001)       // stop threshold
  .alphaDecay(0.0228)    // default ~300 ticks to settle
  .alphaTarget(0)        // equilibrium target
  .velocityDecay(0.4);   // friction (0 = none, 1 = freeze)
```

Tuning:
- Higher `alphaDecay` → faster convergence, less accurate
- `alphaTarget > 0` → simulation never stops (useful for streaming data, drains battery on mobile)
- Higher `velocityDecay` → more damping, less oscillation

### Reheat Strategies

```js
simulation.alpha(1).restart();   // full reheat — layout changes, new data
simulation.alpha(0.3).restart(); // gentle nudge — minor adjustments
```

## Built-in Force Tuning

### forceManyBody — Barnes-Hut N-body

O(n log n). Key parameters beyond defaults:

```js
d3.forceManyBody()
  .strength(-30)         // -100 to -300 for dense graphs
  .distanceMax(300)      // limit range for perf at 1K+ nodes
  .theta(0.9);           // 1.5 = faster, less accurate
```

Per-node: `.strength(d => d.isHub ? -200 : -30)`

### forceLink

```js
d3.forceLink(links).id(d => d.id)
  .distance(d => d.weight ? 30 / d.weight : 100)
  .strength(d => 1 / Math.min(count.get(d.source.id), count.get(d.target.id)))
  .iterations(1);        // higher = more rigid, costs more
```

### forceCollide

```js
d3.forceCollide().radius(d => d.r + 2).strength(0.7).iterations(2);
// 2-3 iterations prevent overlap at cost of speed
```

## Custom Forces

A force is a function with `initialize(nodes, random)` called once, then `force(alpha)` each tick:

```js
function customForce(params) {
  let nodes;
  function force(alpha) {
    for (const d of nodes) { /* modify d.vx, d.vy */ }
  }
  force.initialize = (_nodes) => { nodes = _nodes; };
  return force;
}
```

### Bounding Box

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

### Variants — same pattern, different velocity update

**Swimming lanes**: `d.vy += (laneScale(accessor(d)) - d.y) * alpha * strength;`

**Grid snap**: `d.vx += (Math.round(d.x / cellSize) * cellSize - d.x) * alpha * strength;`

**Cluster pull**: `d.vx += (center.x - d.x) * alpha * strength;`

## Leader-Based Clustering

Link non-leaders to the largest node in their cluster:

```js
const leaders = new Map(clusters.map(([key, group]) =>
  [key, group.reduce((a, b) => a.value > b.value ? a : b)]));
const clusterLinks = nodes.filter(d => d !== leaders.get(d.cluster))
  .map(d => ({ source: d, target: leaders.get(d.cluster) }));
simulation.force("clusterLinks", d3.forceLink(clusterLinks).strength(0.05).distance(50));
```

Alternative: custom cluster-pull force with explicit center coordinates (see custom forces above).

## Tick Management

### Batched — faster convergence with animation

```js
simulation.on("tick", null);
function animate() {
  for (let i = 0; i < 3; i++) simulation.tick(); // 3 ticks per frame
  render();
  if (simulation.alpha() > simulation.alphaMin()) requestAnimationFrame(animate);
}
simulation.restart();
requestAnimationFrame(animate);
```

### Pre-computed (no animation)

```js
simulation.stop();
simulation.tick(300);
render(); // single pass — static views, thumbnails, SSR
```

## Constrained Layouts

### Fixed axis (beeswarm)

```js
simulation
  .force("x", d3.forceX(d => xScale(d.value)).strength(0.8))
  .force("y", d3.forceY(height / 2).strength(0.05))
  .force("collide", d3.forceCollide(d => d.r + 1));
```

### Multi-foci toggle

```js
// Toggle grouped ↔ combined
simulation.force("x", d3.forceX(
  grouped ? d => groupCenters.get(d.group).x : width / 2
).strength(grouped ? 0.1 : 0.02));
simulation.alpha(0.5).restart();
```

## Web Worker Offloading (10K+ nodes)

```js
// force-worker.js
self.onmessage = (e) => {
  const { nodes, links, width, height } = e.data;
  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id))
    .force("charge", d3.forceManyBody().distanceMax(300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .stop();
  for (let i = 0; i < 300; i++) {
    sim.tick();
    if (i % 10 === 0) self.postMessage({ nodes, done: false });
  }
  self.postMessage({ nodes, done: true });
};
```

For worker-based drag: lightweight local simulation for collision during drag, reconcile on end.

## Performance Cliff at ~5K Nodes

The N-body force is O(n log n) per tick. At 5K+:
1. Increase `theta` to 1.5
2. Set `distanceMax` (~300–500)
3. Switch to Canvas
4. Batch ticks (3 per frame)
5. Pre-compute when animation isn't needed

## Common Pitfalls

**Mutated source data.** Simulation writes `x, y, vx, vy, index` onto your objects. Map first: `data.map(d => ({...d}))`.

**Missing `.id()` on forceLink.** String IDs (`{ source: "a", target: "b" }`) require `.id(d => d.id)`. Without it, D3 treats source/target as array indices.

**Nodes pile up at (0, 0).** Missing `forceCenter` or `forceX`/`forceY`.

**Simulation stops too early.** Decrease `alphaDecay` or set `alphaTarget` slightly above 0.

**Simulation never stops.** `alphaTarget > alphaMin` = runs forever. Set `alphaTarget(0)` when interaction ends.

**Drag doesn't work.** Three things: (1) `fx`/`fy` set on start, (2) `alphaTarget(0.3).restart()`, (3) `alphaTarget(0)` on end.

**Links cross.** `forceLink` is a spring, not a routing algorithm. Increase charge or collision radii.

**Quadtree out of sync.** Rebuild every tick — nodes move each frame. Stale quadtrees cause hover/click misses.

## References

- [D3 Force](https://d3js.org/d3-force)
- [Force-Directed Graph](https://observablehq.com/@d3/force-directed-graph)
- [Graph Drawing by Force-directed Placement](https://doi.org/10.1002/spe.4380211102) — Fruchterman & Reingold (1991)
- [Clustered Force Layout](https://observablehq.com/@d3/clustered-force-layout)
