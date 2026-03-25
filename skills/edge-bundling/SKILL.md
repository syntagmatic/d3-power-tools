---
name: edge-bundling
description: "Hierarchical edge bundling for D3.js: visualize connections between leaf nodes in a hierarchy by routing edges through least common ancestors with d3.curveBundle. Use this skill whenever the user wants to build a hierarchical edge bundling diagram, radial dendrograms with bundled connections, dependency graphs, import/export visualizations, package dependency wheels, software architecture diagrams showing module relationships, or any visualization that combines tree structure with cross-links between leaves. Covers d3.cluster radial layout, node.path() for LCA routing, d3.curveBundle.beta() tension control, SVG and Canvas rendering of bundled curves, interactive highlighting, data preparation from flat dependency lists, and animated layout transitions (bundle↔pack↔treemap↔tree) with continuous edge redrawing via data-space interpolation."
---

# Hierarchical Edge Bundling

A network of 500 edges between leaf nodes is unreadable as straight lines — a hairball. Edge bundling routes each connection through the tree structure so edges that share ancestry merge into visible rivers, revealing group-level traffic patterns that individual edges never could.

The tradeoff is real: bundling trades edge-level accuracy for group-level pattern. A tightly bundled diagram tells you "these two clusters are heavily connected" but not "which specific leaf connects to which." That tradeoff is controlled by a single parameter — beta — and getting it right is the central judgment call.

## Core Concept

Three ingredients:

1. **A hierarchy** — tree structure placing nodes in groups
2. **Cross-links** — connections between leaf nodes (imports, dependencies, calls)
3. **LCA routing** — each edge routes through the least common ancestor of its endpoints

Edges between leaves in the same subtree bundle tightly; edges between distant subtrees fan out through higher ancestors.

## Beta: The Judgment Call

`d3.curveBundle.beta(β)` controls how tightly edges follow the tree structure:

- **β = 1** — straight lines between endpoints. Maximum edge clarity, maximum clutter.
- **β = 0.15** (tension 0.85) — tight bundling. Good default for showing group-level flow.
- **β = 0** — curves follow tree edges exactly. Maximum bundling, maximum ambiguity.

**The perceptual trap:** CHI 2025 research (Wallinger et al.) confirms that tight bundling creates *false connections* — viewers follow merged bundles and perceive adjacencies that don't exist in the data. When two bundles merge and split, viewers read the split point as a path in the graph. They do this even while reporting the diagram feels "ambiguous."

**Practical guidance:**
- Start at β = 0.15 (tension 0.85) for the overview. This bundles enough to show group patterns without merging unrelated clusters.
- If distinct clusters' bundles merge into a single river, *reduce* tension (raise β toward 0.3–0.5) until they separate. The visual merge is a lie — those paths don't share structure.
- Add a tension slider so viewers can unbundle on demand. This turns bundling from a fixed editorial choice into an interactive lens.
- For presentations (no interaction), err toward less bundling. The viewer can't unbundle to check.

```js
const line = d3.lineRadial()
  .curve(d3.curveBundle.beta(0.15))
  .radius(d => d.y)
  .angle(d => d.x);
```

## Data Preparation

Two inputs: a hierarchy and a connection list referencing leaf IDs.

```js
const root = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parent || null)(nodes);

const nodesById = new Map(root.descendants().map(d => [d.data.id, d]));

// node.path(target) returns [source, ..ancestors.., LCA, ..ancestors.., target]
const links = connections.map(c => {
  const source = nodesById.get(c.source);
  const target = nodesById.get(c.target);
  return source && target ? source.path(target) : null;
}).filter(Boolean);
```

**Gotcha:** If source/target IDs don't match hierarchy node IDs, `nodesById.get()` returns undefined and the edge silently disappears. Always log mismatches during development — `"vis.chart"` vs `"root.vis.chart"` is a common one.

## Radial Layout

Use `d3.cluster` (not `d3.tree`) — it places all leaves at the same radius, forming the ring. `d3.tree` spreads leaves at varying depths, breaking the circular structure.

```js
const cluster = d3.cluster()
  .size([2 * Math.PI, radius - 140])
  .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);
```

The `.separation()` function matters: without `/ a.depth`, deeper levels get disproportionate angular space, crowding shallow groups. See `hierarchy-layouts` for radial coordinate details and label flipping.

Only render leaves — internal nodes are invisible routing waypoints:

```js
const nodeSelection = g.selectAll("g.node")
  .data(root.leaves())
  .join("g")
    .attr("class", "node")
    .attr("transform", d =>
      `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`);
```

## Rendering

### SVG (< 200 edges)

```js
g.selectAll("path.link")
  .data(links)
  .join("path")
    .attr("class", "link")
    .attr("fill", "none")
    .attr("stroke", "#888")
    .attr("stroke-opacity", 0.3)
    .attr("d", line);
```

### Canvas (200+ edges)

`.context(ctx)` makes the line generator write `moveTo`/`bezierCurveTo` directly onto the canvas context — no intermediate SVG path strings:

```js
function drawLinks(ctx, links, beta) {
  const line = d3.line()
    .curve(d3.curveBundle.beta(beta))
    .x(d => d.cx).y(d => d.cy)
    .context(ctx);

  ctx.save();
  ctx.translate(width / 2, height / 2);
  ctx.strokeStyle = "rgba(136, 136, 136, 0.3)";
  ctx.lineWidth = 1;
  for (const link of links) {
    ctx.beginPath();
    line(link);
    ctx.stroke();
  }
  ctx.restore();
}
```

For Cartesian layouts, use `d3.line` instead of `d3.lineRadial` — same LCA paths, different coordinate accessors.

## Interaction: Highlighting Connections

Highlighting is what makes bundling useful for analysis rather than just aesthetics. Without it, the viewer sees group patterns but can't verify specific connections.

```js
function getConnectedLinks(node, links) {
  const leafIds = new Set(node.leaves().map(d => d.data.id));
  return links.filter(link => {
    const sourceId = link[0].data.id;
    const targetId = link[link.length - 1].data.id;
    return leafIds.has(sourceId) || leafIds.has(targetId);
  });
}
```

Always `.raise()` highlighted links (SVG) or draw highlighted in a second pass (Canvas) — otherwise highlighted edges render behind faded ones and disappear into the gray.

## Layout Transitions with Bundled Edges

Edge bundling works with any hierarchy layout. The key insight: interpolate node positions in data space (`current_x`/`current_y` on hierarchy nodes), then re-derive bundled curves each frame. The LCA paths never change — only the positions of the nodes they pass through.

```js
function transitionToLayout(layoutFn) {
  root.each(d => { d.source_x = d.current_x; d.source_y = d.current_y; });

  layoutFn(root);
  root.each(d => {
    // Convert all layouts to common cartesian coordinates
    if (layoutFn === cluster) {
      d.target_x = d.y * Math.cos(d.x - Math.PI / 2);
      d.target_y = d.y * Math.sin(d.x - Math.PI / 2);
    } else {
      d.target_x = d.x;
      d.target_y = d.y;
    }
  });

  svg.transition().duration(1200).ease(d3.easeCubicInOut)
    .tween("layout", () => time => {
      root.each(d => {
        d.current_x = d.source_x + (d.target_x - d.source_x) * time;
        d.current_y = d.source_y + (d.target_y - d.source_y) * time;
      });
      redrawNodes();
      redrawLinks();  // bundle curves recomputed from current_x/y
    });
}
```

Internal nodes must have interpolated positions even though they're invisible — their smooth movement is what makes bundled curves deform naturally during the transition.

**Why this works:** The bundle curve is a pure function of its control point positions. Since LCA paths depend on tree structure (not layout), interpolating control points smoothly deforms the curves. No path morphing library needed.

## When Not to Use Edge Bundling

**When individual connections matter more than group patterns.** If the viewer needs to trace specific edges (e.g., "does module A depend on module B?"), bundling actively hides the answer. Use a force-directed layout with highlight-on-hover, or an adjacency matrix.

**When the hierarchy is arbitrary or flat.** Bundling quality depends entirely on how well the hierarchy groups related nodes. A two-level hierarchy (root → leaves) produces no meaningful bundling. If your grouping doesn't reflect real structure, the bundles will be meaningless rivers.

**When most edges are within-group.** Bundling reveals cross-group connections by routing them through ancestors. If 90% of edges stay within the same parent, those short paths barely curve and the diagram adds complexity without insight. A grouped adjacency matrix shows within-group density better.

**When you have fewer than ~30 edges.** Straight lines with highlighting are clearer. Bundling solves a clutter problem that doesn't exist at small scale.

## Performance

| Edge count | Approach |
|---|---|
| < 200 | SVG with CSS transitions |
| 200–2,000 | SVG, low `stroke-opacity` to manage overdraw |
| 2,000–50,000 | Canvas with `.context(ctx)` |
| 50,000+ | Canvas + Web Worker for path computation |

## Common Pitfalls

1. **Mismatched IDs between hierarchy and connections.** Source/target must exactly match leaf node IDs. Silent edge drops are the most common bug.

2. **Beta vs tension confusion.** `d3.curveBundle.beta(β)` where `β = 1 - tension`. High tension = low beta = tight bundling. The naming is backwards from intuition — beta 0 is maximum bundling, not minimum.

3. **Labels overlapping at high node counts.** Above ~100 leaves, radial labels collide. Show labels only on hover, increase radius, or filter to every Nth label.

4. **Internal nodes visible as dots.** Only leaves should render. Internal nodes are routing waypoints — filter to `root.leaves()` for the node selection.

5. **Bundling non-leaf connections.** The technique assumes leaf-to-leaf connections. Internal node connections produce short LCA paths with minimal bundling — they look like straight lines floating in the middle of the diagram.

## References

- [Hierarchical Edge Bundles](https://doi.org/10.1109/TVCG.2006.147) — Danny Holten's original paper (IEEE InfoVis 2006)
- [How Do People Perceive Bundling?](https://dl.acm.org/doi/10.1145/3706598.3713444) — CHI 2025 study on false connections and bundling ambiguity
- [Hierarchical Edge Bundling](https://observablehq.com/@d3/hierarchical-edge-bundling) — Mike Bostock's canonical D3 implementation
- [Edge-Path Bundling](https://arxiv.org/abs/2108.05467) — less ambiguous alternative that bundles along graph paths rather than spatial proximity
