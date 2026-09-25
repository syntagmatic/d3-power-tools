# Force simulation

Absorbed from the v2 `force` skill. Open when writing a custom force, precomputing in a worker, pushing past ~5K nodes, or choosing a layout engine other than d3-force.

## Cooling

Defaults: `alpha(1)`, `alphaMin(0.001)`, `alphaDecay(0.0228)` (≈300 ticks to cool), `alphaTarget(0)`, `velocityDecay(0.4)`. The tick count to cool from alpha 1:

```js
const ticks = Math.ceil(Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay()));
```

- Higher `alphaDecay` settles faster and worse: nodes freeze before finding good positions.
- `velocityDecay` 0.6-0.8 stops jitter and oscillation.
- Reheat: `alpha(1)` reshuffles; `alpha(0.3-0.5)` adapts the current layout.

## Force parameters

- `forceManyBody`: `.strength(-30)` default; -100 to -300 for dense graphs. `.distanceMax(300)` matters for performance at 1K+. `.theta(0.9)` default; 1.5 is faster and coarser. Per-node strength gives hubs room: `.strength(d => d.isHub ? -200 : -30)`.
- `forceLink`: default strength is `1 / min(degree(source), degree(target))`, so links to low-degree nodes pull harder. Encode weight as `distance(d => 30 / d.weight)`. `iterations` stiffens links at linear cost.
- `forceCollide`: `.radius(d => d.r + 2)`. 1 iteration if loosely packed, 2-3 if dense.

## Custom forces

A force is a function of `alpha` called each tick, with `initialize(nodes)`. Nudge `vx`/`vy` and let the integrator move `x`/`y`. The exception is a hard boundary, which clamps position and zeroes velocity:

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

Same shape, different update line:

- Swim lanes: `d.vy += (laneY(d) - d.y) * alpha * strength`
- Grid snap: `d.vx += (Math.round(d.x / cell) * cell - d.x) * alpha * strength`
- Cluster pull: `d.vx += (center.x - d.x) * alpha * strength`

## Clustering via leader links

Link each non-leader to the largest node in its cluster. Simpler and more stable than a custom cluster force:

```js
const leaders = new Map(clusters.map(([key, group]) =>
  [key, group.reduce((a, b) => a.value > b.value ? a : b)]));
const clusterLinks = nodes.filter(d => d !== leaders.get(d.cluster))
  .map(d => ({ source: d, target: leaders.get(d.cluster) }));
simulation.force("clusterLinks", d3.forceLink(clusterLinks).strength(0.05).distance(50));
```

## Constrained layouts

- Beeswarm: `forceX(d => x(d.value)).strength(0.8)`, `forceY(h / 2).strength(0.05)`, `forceCollide(d => d.r + 1)`.
- Multi-foci toggle: swap the `forceX` target between group centers (strength 0.1) and the middle (0.02), then `alpha(0.5).restart()`. Moderate alpha keeps spatial memory.

## Tick strategies

Batched (3 ticks per frame, ~100 frames instead of ~300). `simulation.tick()` doesn't fire tick events and the internal timer must be stopped or it double-ticks:

```js
simulation.stop();
function animate() {
  for (let i = 0; i < 3; i++) simulation.tick();
  render();
  if (simulation.alpha() > simulation.alphaMin()) requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
```

Precomputed: `simulation.stop().tick(ticks)` then render once. For static views, thumbnails, server-side output.

## The ~5K node cliff

At ~5K nodes with defaults one tick exceeds a 16ms frame, mostly `forceManyBody` rebuilding and walking its quadtree. In order of effort:

1. `distanceMax(300-500)`: often doubles throughput.
2. `theta(1.5)`.
3. Canvas instead of SVG: per-tick DOM updates are the other O(n).
4. Batch ticks.
5. Precompute if the viewer doesn't need to watch it form.
6. Web Worker. d3-force has no DOM dependency but needs d3-dispatch, d3-quadtree and d3-timer, so `importScripts` the full d3 bundle (or all four modules).
7. `d3-force-reuse`: `forceManyBodyReuse()` drop-in that reuses the quadtree across ticks instead of rebuilding it each one.

### Worker patterns

- Static: worker runs `tick(n)`, posts final positions once.
- Progressive: post positions every N ticks; the viewer watches it converge but can't interact.

```js
// force-worker.js
importScripts("https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js");
self.onmessage = ({ data: { nodes, links, width, height } }) => {
  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id))
    .force("charge", d3.forceManyBody().distanceMax(400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .stop();
  const snapshot = () => nodes.map(d => ({ id: d.id, x: d.x, y: d.y }));
  for (let i = 0; i < 300; i++) {
    sim.tick();
    if (i % 5 === 0) self.postMessage({ done: false, nodes: snapshot() });
  }
  self.postMessage({ done: true, nodes: snapshot() });
};
```

- Interactive: worker keeps the simulation running with a tick handler that posts positions. Main thread sends `{type: "drag", id, x, y}`; worker sets `fx`/`fy` and `alpha(0.3).restart()`. On `dragend`, clear `fx`/`fy`. Keep a `Map` from id to node in the worker.

`postMessage` structured-clones. `{id, x, y}` for 10K nodes per tick is fine. At 50K+, pack into a `Float64Array` and transfer the buffer (`postMessage(buf, [buf.buffer])`); the sender's copy is detached, so double-buffer.

## Beyond d3-force

d3-force is right for a graph under ~5K nodes that should animate and be draggable. Otherwise:

| Situation | Tool | Why |
|---|---|---|
| Feature vectors, not edges | UMAP (`umap-js`) | clusters from features; force needs explicit edges |
| Communities must separate | ForceAtlas2 (`graphology-layout-forceatlas2`) | degree-dependent repulsion and LinLog mode split communities d3-force blends |
| Alignment, ordering, group boxes | WebCola | constraint-based |
| 5K-50K nodes | ForceAtlas2 in a worker | adaptive per-node temperature, no alpha tuning |
| 50K+ nodes | server-side layout (Graphviz `sfdp`) + static render | too expensive in the browser |
| Edge lengths must be faithful | stress majorization (WebCola) | monotonic convergence; annealing oscillates |

All of these output x/y. Render with D3 as usual.

## Traps

- Simulation mutates nodes (`x, y, vx, vy, index`) and replaces link `source`/`target` strings with node objects. Clone first: `data.map(d => ({...d}))`.
- String ids without `forceLink.id(d => d.id)`: d3 treats them as indices and connects the wrong nodes.
- Graph crammed into the top-left corner: nodes initialize around (0, 0). Add `forceCenter` or `forceX`/`forceY`.
- Never stops: `alphaTarget > alphaMin`. Reset `alphaTarget(0)` when interaction ends.
- Stops too early: lower `alphaDecay`.
- Drag: `fx`/`fy` on start and drag, `alphaTarget(0.3).restart()` on start, `alphaTarget(0)` and clear `fx`/`fy` on end (unless pinning is the point).
- Crossings: `forceLink` is a spring, not a router. More charge helps; nothing guarantees planarity.
- Hit-testing quadtree built once: rebuild it each tick or clicks miss where the layout moved most.
