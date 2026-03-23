---
name: force-simulation
description: "D3.js force-directed layouts and physics simulations: node positioning with forces, collision detection, clustering, constrained layouts, and drag interaction. Use this skill whenever the user wants to build force-directed graphs, network node-link diagrams, physics-based layouts, bubble collision charts, or interactive simulations. Also use when the user mentions d3.forceSimulation, forceManyBody, forceLink, forceCollide, forceCenter, forceX, forceY, forceRadial, alpha decay, tick management, velocity Verlet, node dragging with fx/fy, force-directed clustering, or scaling force layouts to 10K+ nodes."
---

# Force Simulation

Patterns for building force-directed layouts with `d3.forceSimulation`. Covers the simulation lifecycle, all built-in forces, custom forces, tick management, drag interaction, constrained layouts, clustering, and performance at scale.

For network graph types (Sankey, chord, adjacency matrix, arc diagrams), see `network-visualization`. For canvas rendering patterns, see `canvas-rendering`. For GPU-accelerated rendering at 100K+ nodes, see `webgl-rendering`.

## Simulation Lifecycle

`d3.forceSimulation(nodes)` creates a simulation with velocity Verlet integration. It mutates each node, adding `x`, `y`, `vx`, `vy`, `index`. Nodes start in a phyllotaxis arrangement by default.

```js
const nodes = data.map(d => ({ id: d.id, group: d.group }));
const simulation = d3.forceSimulation(nodes);

// Optional: control initial positions
nodes.forEach(d => { d.x = xScale(d.value); d.y = height / 2; });
```

### Alpha, Cooling, and Convergence

Internal temperature (`alpha`) decays toward `alphaMin` each tick. When alpha < alphaMin, the simulation stops.

```js
simulation
  .alpha(1)              // current temperature (0–1), default 1
  .alphaMin(0.001)       // stop threshold
  .alphaDecay(0.0228)    // cooling rate, default ~300 ticks to settle
  .alphaTarget(0)        // equilibrium target
  .velocityDecay(0.4);   // friction (0 = none, 1 = freeze)
```

- Higher `alphaDecay` → faster convergence, less accurate
- `alphaTarget > 0` → simulation never stops (useful for streaming data)
- Higher `velocityDecay` → more damping, less oscillation

### Restart, Reheat, Stop

```js
simulation.alpha(1).restart();   // full reheat
simulation.alpha(0.3).restart(); // gentle nudge
simulation.stop();               // pause
simulation.on("tick", null);     // remove listeners before discarding
```

## Built-in Forces

Add with `.force(name, force)`. Remove with `.force(name, null)`.

```js
const simulation = d3.forceSimulation(nodes)
  .force("charge", d3.forceManyBody())
  .force("link", d3.forceLink(links).id(d => d.id))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide(d => d.r + 1));
```

### forceLink — Edge Constraints

```js
d3.forceLink(links)
  .id(d => d.id)         // match source/target strings
  .distance(50)          // target length, default 30
  .strength(d => 1 / Math.min(count.get(d.source.id), count.get(d.target.id)))
  .iterations(1);        // higher = more rigid, costs more per tick
```

Distance as function: `.distance(d => d.weight ? 30 / d.weight : 100)`

### forceManyBody — Charge / Repulsion

Barnes-Hut N-body force, O(n log n). Negative = repulsion, positive = attraction.

```js
d3.forceManyBody()
  .strength(-30)         // default; -100 to -300 for dense graphs
  .distanceMin(1)        // avoid extreme close-range forces
  .distanceMax(Infinity) // limit for perf at 1K+ nodes (use ~300–500)
  .theta(0.9);           // Barnes-Hut accuracy; 1.5 = faster, less accurate
```

Per-node: `.strength(d => d.isHub ? -200 : -30)`

### forceCollide — Prevent Overlap

```js
d3.forceCollide()
  .radius(d => d.r + 2).strength(0.7).iterations(1);
```

For bubble charts, beeswarm plots. Multiple iterations (2–3) prevent overlap at cost of speed.

### Positioning Forces

```js
d3.forceCenter(width / 2, height / 2)   // shifts centroid, no push
  .strength(1);

d3.forceX(d => groupX(d.group))          // pull toward target x
  .strength(0.1);
d3.forceY(height / 2).strength(0.1);     // pull toward target y

d3.forceRadial(d => ringRadius(d.tier), width / 2, height / 2)
  .strength(0.8);                         // pull toward circle
```

Combine `forceX`/`forceY` with `forceManyBody` for category-clustered layouts.

## Custom Forces

A force is any function with an `initialize` method. The simulation calls `force.initialize(nodes, random)` once, then `force(alpha)` each tick:

```js
// General pattern — all custom forces follow this structure
function customForce(params) {
  let nodes;
  function force(alpha) {
    for (const d of nodes) {
      // modify d.x, d.y, d.vx, d.vy based on params
    }
  }
  force.initialize = (_nodes) => { nodes = _nodes; };
  return force;
}
```

### Bounding Box — clamp positions

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
  force.initialize = (_nodes) => { nodes = _nodes; };
  return force;
}
```

### Variants — same pattern, different velocity update

**Swimming lanes** — constrain to horizontal bands:
```js
d.vy += (laneScale(accessor(d)) - d.y) * alpha * strength;
```

**Grid snap** — nudge toward nearest grid intersection:
```js
d.vx += (Math.round(d.x / cellSize) * cellSize - d.x) * alpha * strength;
d.vy += (Math.round(d.y / cellSize) * cellSize - d.y) * alpha * strength;
```

**Cluster pull** — attract toward cluster center:
```js
const c = centerAccessor(d);
d.vx += (c.x - d.x) * alpha * strength;
d.vy += (c.y - d.y) * alpha * strength;
```

## Tick Management

### Animated ticks — render in the callback

```js
// SVG
simulation.on("tick", () => {
  nodeSelection.attr("cx", d => d.x).attr("cy", d => d.y);
  linkSelection.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
});

// Canvas — clear and redraw. See `canvas-rendering` for batching patterns.
simulation.on("tick", () => {
  ctx.clearRect(0, 0, width, height);
  // draw links, then nodes
});
```

### Pre-computed (sync) — no animation overhead

```js
simulation.stop();
simulation.tick(300);
render(); // single pass — use for static views, thumbnails, SSR
```

### Batched — faster convergence with animation

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

## Drag Interaction

D3 drag integrates via `fx`/`fy` (fixed position overrides). SVG and canvas share the same `fx`/`fy` pattern:

```js
function drag(simulation) {
  return d3.drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    })
    .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
    .on("end", (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null; d.fy = null; // release
    });
}
nodeSelection.call(drag(simulation)); // SVG
```

### Canvas drag — use quadtree hit detection

```js
d3.select(canvas).call(d3.drag()
  .subject(event => {
    const [mx, my] = d3.pointer(event, canvas);
    return quadtree.find(mx, my, 20) || null;
  })
  .on("start", (event) => {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x; event.subject.fy = event.subject.y;
  })
  .on("drag", (event) => { event.subject.fx = event.x; event.subject.fy = event.y; })
  .on("end", (event) => {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null; event.subject.fy = null;
  })
);
```

Rebuild the quadtree each tick if using it for both hover and drag:
```js
simulation.on("tick", () => {
  quadtree = d3.quadtree().x(d => d.x).y(d => d.y).addAll(nodes);
  render();
});
```

### Sticky nodes — keep pinned after drag

Don't clear `fx`/`fy` in drag end. Click to unpin:
```js
nodeSelection.on("click", (event, d) => {
  d.fx = null; d.fy = null;
  simulation.alpha(0.3).restart();
});
```

## Constrained Layouts

### Bounding box — clamp in tick

```js
nodes.forEach(d => {
  d.x = Math.max(d.r, Math.min(width - d.r, d.x));
  d.y = Math.max(d.r, Math.min(height - d.r, d.y));
});
```

### Multi-foci grouping

```js
simulation
  .force("x", d3.forceX(d => groupCenters.get(d.group).x).strength(0.1))
  .force("y", d3.forceY(d => groupCenters.get(d.group).y).strength(0.1))
  .force("charge", d3.forceManyBody().strength(-20))
  .force("collide", d3.forceCollide(d => d.r + 2));

// Toggle grouped ↔ combined
simulation.force("x", d3.forceX(
  grouped ? d => groupCenters.get(d.group).x : width / 2
).strength(grouped ? 0.1 : 0.02));
simulation.alpha(0.5).restart();
```

### Fixed axis (beeswarm)

```js
simulation
  .force("x", d3.forceX(d => xScale(d.value)).strength(0.8))
  .force("y", d3.forceY(height / 2).strength(0.05))
  .force("collide", d3.forceCollide(d => d.r + 1));
```

## Clustering

### Multi-foci with custom cluster force

```js
const clusters = d3.groups(nodes, d => d.cluster);
const clusterCenters = new Map(clusters.map(([key], i) => [key, {
  x: width / 2 + 150 * Math.cos(2 * Math.PI * i / clusters.length),
  y: height / 2 + 150 * Math.sin(2 * Math.PI * i / clusters.length),
}]));

// Cluster pull force — uses the custom force pattern from above
function forceCluster(centerFn, strength = 0.15) {
  let nodes;
  function force(alpha) {
    for (const d of nodes) {
      const c = centerFn(d);
      d.vx += (c.x - d.x) * alpha * strength;
      d.vy += (c.y - d.y) * alpha * strength;
    }
  }
  force.initialize = n => { nodes = n; };
  return force;
}

simulation
  .force("cluster", forceCluster(d => clusterCenters.get(d.cluster)))
  .force("collide", d3.forceCollide(d => d.r + 1).iterations(2))
  .force("charge", d3.forceManyBody().strength(-5));
```

### Leader-based clustering — link non-leaders to leaders

```js
const leaders = new Map(clusters.map(([key, group]) =>
  [key, group.reduce((a, b) => a.value > b.value ? a : b)]));
const clusterLinks = nodes.filter(d => d !== leaders.get(d.cluster))
  .map(d => ({ source: d, target: leaders.get(d.cluster) }));
simulation.force("clusterLinks", d3.forceLink(clusterLinks).strength(0.05).distance(50));
```

## Performance at Scale

For 500+ nodes, use canvas. See `canvas-rendering` for quadtree hit detection, batched drawing, multi-layer canvas. See `webgl-rendering` for 100K+ nodes.

### Reducing simulation cost

```js
d3.forceManyBody().strength(-30).distanceMax(300)  // limit charge range: O(n) when local
d3.forceManyBody().theta(1.5)                      // less accurate, faster Barnes-Hut
simulation.alphaDecay(0.05)                        // converge in ~100 ticks vs ~300
simulation.stop(); simulation.tick(200); render(); // pre-compute, no animation
```

### Web Worker offloading (10K+ nodes)

```js
// main.js
const worker = new Worker("force-worker.js");
worker.postMessage({ nodes, links, width, height });
worker.onmessage = (e) => { nodes = e.data.nodes; render(); };

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

See `canvas-rendering` for OffscreenCanvas + worker patterns. For worker-based drag, create a lightweight local simulation for collision during drag, then reconcile.

## Updating Data

```js
function updateData(newNodes, newLinks) {
  const existing = new Map(nodes.map(d => [d.id, d]));
  const merged = newNodes.map(d => {
    const prev = existing.get(d.id);
    return prev ? Object.assign(prev, d) : d;
  });
  simulation.nodes(merged);
  simulation.force("link").links(newLinks);
  simulation.alpha(0.5).restart();
}
```

To animate between force configurations, swap forces and remove old ones:
```js
for (const [name, force] of Object.entries(newForces)) simulation.force(name, force);
for (const name of oldForceNames) if (!(name in newForces)) simulation.force(name, null);
simulation.alpha(0.8).restart();
```

## Accessibility

See `canvas-accessibility` for keyboard navigation, screen reader patterns, hidden DOM mirrors. Key force-specific points:

- **Spatial nav via quadtree** — arrow keys find nearest node in direction. Rebuild quadtree each tick.
- **Announce stabilization** — `simulation.on("end", () => liveRegion.textContent = "...")`. Don't announce every reheat.
- **Hybrid rendering** — canvas for data, SVG overlay for focus rings and labels.
- **Data validation** — see `network-visualization` skill's `validate-network.js` for catching dangling refs, self-loops, duplicate edges.

## Common Pitfalls

**Mutated source data.** The simulation writes `x`, `y`, `vx`, `vy`, `index` directly onto your node objects. If you don't want your source data mutated, map to new objects first: `data.map(d => ({...d}))`.

**Missing `.id()` on forceLink.** If your links use string IDs (`{ source: "a", target: "b" }`) instead of node references, you must set `.id(d => d.id)`. Without it, D3 treats source/target as array indices.

**Nodes pile up at (0, 0).** Usually means `forceCenter` or `forceX`/`forceY` is missing. Without a centering force, nodes drift to wherever their initial positions were (often 0, 0).

**Simulation stops too early.** Increase `alphaMin` threshold or decrease `alphaDecay`. Or set `alphaTarget` slightly above 0 to keep it running indefinitely.

**Simulation never stops.** `alphaTarget > alphaMin` means it runs forever. This may be intentional for live data, but drains battery on mobile. Set `alphaTarget(0)` when interaction ends.

**Drag doesn't work.** Three things to check: (1) `fx`/`fy` must be set on drag start, (2) simulation must be reheated (`alphaTarget(0.3).restart()`), (3) `alphaTarget` must be reset to 0 on drag end.

**Links cross when they shouldn't.** `forceLink` doesn't prevent crossing — it's a spring, not a routing algorithm. For cleaner edge routing, increase `forceManyBody` strength or use `forceCollide` with generous radii.

**Performance cliff at ~5K nodes.** The N-body force is O(n log n) per tick. At 5K+ nodes: (1) increase `theta` to 1.5, (2) set `distanceMax`, (3) switch to canvas, (4) batch ticks, (5) pre-compute when animation isn't needed.

**Quadtree out of sync.** If you use a quadtree for hit detection, rebuild it on every tick — nodes move each frame. Stale quadtrees cause hover/click misses.

## References

- [D3 Force documentation](https://d3js.org/d3-force)
- [Force-Directed Graph](https://observablehq.com/@d3/force-directed-graph) — canonical force layout example
- [Graph Drawing by Force-directed Placement](https://doi.org/10.1002/spe.4380211102) — Fruchterman & Reingold (1991)
- [D3 Force Simulation Internals](https://observablehq.com/@mbostock/d3-force-simulation) — alpha decay and velocity Verlet
- [Clustered Force Layout](https://observablehq.com/@d3/clustered-force-layout)
- [Disjoint Force-Directed Graph](https://observablehq.com/@d3/disjoint-force-directed-graph) — handling disconnected components
