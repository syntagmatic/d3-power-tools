---
name: hierarchy-interaction
description: "Interactive patterns for D3.js hierarchy visualizations: expand/collapse subtrees, zoomable treemap, zoomable sunburst, zoomable circle pack, and focus+context navigation. Use this skill whenever the user wants to make a tree, treemap, sunburst, icicle, dendrogram, or circle pack interactive — collapsing or expanding branches, zooming into subtrees, clicking to drill down, animating between hierarchy focus levels, or adding breadcrumb navigation. Also use when the user mentions collapsible tree, drill-down, zoom-to-node, or focus+context in the context of hierarchies."
---

# Hierarchy Interaction

Interactive patterns for navigating hierarchical data with D3. Collapse hides complexity, zoom reveals detail. Both need animated transitions so the viewer maintains spatial context — without animation, the connection between "where I was" and "where I am" is lost.

## Expand/Collapse: The `_children` Toggle

D3 hierarchy layouts only visit `node.children`. To collapse, move children to a private `_children` property:

```js
function toggle(event, d) {
  if (d.children) { d._children = d.children; d.children = null; }
  else if (d._children) { d.children = d._children; d._children = null; }
  update(d);
}
```

After toggling, recompute layout and rejoin. The key: **entering nodes start at the parent's previous position, exiting nodes converge to the parent's new position.** This creates children emerging from or collapsing into their parent. Stash positions after each update:

```js
nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y; });
```

After swapping `children`/`_children`, you must re-run the layout (and `.sum()` if values depend on leaves).

## Canvas Expand/Collapse (500+ Nodes)

Without DOM elements, maintain current positions and interpolate toward targets using `d3.timer`:

```js
function animateToLayout() {
  const treeLayout = d3.tree().size([height, width - 160]);
  treeLayout(root);

  // Visible nodes at layout positions; collapsed children converge to parent
  const targets = new Map();
  root.descendants().forEach(d => {
    targets.set(d.data.id, { x: d.y, y: d.x, r: 5, opacity: 1 });
  });
  root.each(d => {
    if (d._children) {
      d._children.forEach(function walk(child) {
        targets.set(child.data.id, { x: d.y, y: d.x, r: 0, opacity: 0 });
        (child.children || child._children || []).forEach(walk);
      });
    }
  });

  // Expanding children: initialize at parent position if no prior position
  for (const [id, target] of targets) {
    if (!positions.has(id)) positions.set(id, { ...target });
  }

  const interps = new Map();
  for (const [id, target] of targets) {
    const source = positions.get(id);
    interps.set(id, {
      x: d3.interpolateNumber(source.x, target.x),
      y: d3.interpolateNumber(source.y, target.y),
      r: d3.interpolateNumber(source.r, target.r),
      opacity: d3.interpolateNumber(source.opacity, target.opacity),
    });
  }

  d3.timer((elapsed) => {
    const t = d3.easeCubicInOut(Math.min(1, elapsed / 500));
    for (const [id, interp] of interps) {
      positions.set(id, { x: interp.x(t), y: interp.y(t), r: interp.r(t), opacity: interp.opacity(t) });
    }
    draw();
    if (elapsed >= 500) {
      for (const [id, target] of targets) positions.set(id, { ...target });
      draw();
      rebuildHitDetection(); // quadtree must reflect new positions
      return true;
    }
  });
}
```

**Stale quadtree after collapse:** The quadtree holds positions from before the transition. Rebuild it in the timer's completion callback, not at the start.

## Zoomable Treemap

Click a cell to zoom into that subtree. The key insight: **narrow the x/y scale domains to the focused node's bounds.** All descendants rescale automatically. No need to re-run `d3.treemap()`.

```js
const x = d3.scaleLinear().rangeRound([0, width]);
const y = d3.scaleLinear().rangeRound([0, height]);

function zoomIn(group) {
  currentFocus = group;
  x.domain([group.x0, group.x1]);
  y.domain([group.y0, group.y1]);

  const t = svg.transition().duration(750);
  cell.transition(t)
    .attr("transform", d => `translate(${x(d.x0)},${y(d.y0)})`)
    .select("rect")
      .attr("width", d => x(d.x1) - x(d.x0))
      .attr("height", d => y(d.y1) - y(d.y0));
  cell.transition(t)
    .attr("opacity", d => isDescendant(d, group) ? 1 : 0);
}
```

### Clipping During Transitions

Without clipping, cells overshoot their parent's bounds mid-transition. Apply `clipPath` to each group and update clip rect dimensions during the transition.

### Breadcrumb Navigation

Build from `focus.ancestors().reverse()`. Each crumb click resets `x`/`y` domains to that ancestor's bounds.

## Zoomable Sunburst: Arc Tween

Click an arc to make it the new center. The partition layout is computed once; zoom remaps angles and radii relative to the clicked node.

```js
function clicked(event, p) {
  // p fills the full circle — remap all arcs relative to p
  root.each(d => {
    d.target = {
      x0: Math.max(0, Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
      x1: Math.max(0, Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
      y0: Math.max(0, d.y0 - p.depth),
      y1: Math.max(0, d.y1 - p.depth),
    };
  });

  const t = svg.transition().duration(750);
  paths.transition(t)
    .tween("data", d => {
      const i = d3.interpolate(d.current, d.target);
      return t => d.current = i(t);
    })
    .attrTween("d", d => () => arc(d.current));
}
```

**Stashing current state:** Initialize with `paths.each(d => { d.current = d; })`. Stash on the datum (not `this`) because `d3.interpolate` reads angle/radius properties directly. Don't interpolate SVG path strings — use `attrTween("d", ...)` with the arc generator called per-frame.

### Visibility Tests

```js
function arcVisible(d) { return d.y1 <= 3 && d.y0 >= 1 && d.x1 > d.x0; }
function labelVisible(d) { return d.y1 <= 3 && d.y0 >= 1 && (d.y1 - d.y0) * (d.x1 - d.x0) > 0.03; }
function labelTransform(d) {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
  const y = (d.y0 + d.y1) / 2 * radius;
  return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
}
```

## Zoomable Circle Pack

Uses `d3.interpolateZoom` (van Wijk & Nuij, 2003) for mathematically smooth zooming — pans and scales simultaneously along the shortest perceptual path, avoiding the disorienting "zoom all the way out then back in" effect.

All circles are positioned relative to a `view = [x, y, diameter]`:

```js
function zoomTo(v) {
  const k = width / v[2];
  view = v;
  node.attr("transform", d =>
    `translate(${(d.x - v[0]) * k + width / 2},${(d.y - v[1]) * k + height / 2})`);
  node.select("circle").attr("r", d => d.r * k);
}

// Click to zoom
svg.transition().duration(750)
  .tween("zoom", () => {
    const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
    return t => zoomTo(i(t));
  });
```

## Semantic vs Geometric Zoom

**Geometric zoom** scales the entire drawing uniformly — fast but text and strokes scale too. **Semantic zoom** re-renders at the new scale with appropriate detail levels:

```js
function zoomed(event) {
  const k = event.transform.k;
  if (k > 4) drawDetailedView(event.transform);     // labels, sub-nodes
  else if (k > 2) drawMediumView(event.transform);  // primary labels
  else drawOverview(event.transform);                 // aggregate, no labels
}
```

## Canvas vs SVG Decision

| Pattern | SVG | Canvas |
|---------|-----|--------|
| Collapsible tree, <500 nodes | Preferred | |
| Collapsible tree, >500 nodes | | Preferred |
| Zoomable treemap | Preferred — rect transitions, clipPath | |
| Zoomable sunburst | Preferred — arc tween with `attrTween` | |
| Pan+zoom over large hierarchy | | Preferred — geometric zoom is a single transform |

## Common Pitfalls

1. **Children appear from (0,0) on expand.** Entering nodes must start at the parent's position. Stash `d.x0`/`d.y0` after each update.
2. **Double-click fires click first.** Use a 250ms timer to distinguish, or avoid the conflict: single-click for toggle (common), modifier key for select.
3. **Treemap cells overflow during zoom transition.** Apply `clipPath` so children don't render outside parent bounds mid-transition.
4. **Enter + update not merged.** Use `.merge()` or `.join()` so both sets get the position transition.

## References

- [Zoomable Treemap](https://observablehq.com/@d3/zoomable-treemap) — Mike Bostock's canonical drill-down treemap
- [Zoomable Sunburst](https://observablehq.com/@d3/zoomable-sunburst) — arc-tween sunburst with focus+context
- [Zoomable Circle Packing](https://observablehq.com/@d3/zoomable-circle-packing) — zoom-to-focus circle pack
- [Animated Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — van Wijk & van de Wetering on smooth treemap transitions (IEEE InfoVis 2001)
