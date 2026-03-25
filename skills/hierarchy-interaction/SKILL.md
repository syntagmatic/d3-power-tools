---
name: hierarchy-interaction
description: "Interactive patterns for D3.js hierarchy visualizations: expand/collapse subtrees, zoomable treemap, zoomable sunburst, zoomable circle pack, and focus+context navigation. Use this skill whenever the user wants to make a tree, treemap, sunburst, icicle, dendrogram, or circle pack interactive — collapsing or expanding branches, zooming into subtrees, clicking to drill down, animating between hierarchy focus levels, or adding breadcrumb navigation. Also use when the user mentions collapsible tree, drill-down, zoom-to-node, or focus+context in the context of hierarchies."
---

# Hierarchy Interaction

Hierarchies get big fast. A 4-level tree with branching factor 5 has 780 nodes — too many to show at once, too connected to split across pages. Interaction lets the viewer control what's visible: collapse hides subtrees they don't need, zoom reveals detail in the subtree they do.

Both require animated transitions. Without animation, the viewer loses the spatial connection between "where I was" and "where I am," and the hierarchy feels like a sequence of unrelated pictures.

## When Not to Use

**Expand/collapse hurts when context matters.** Collapsing a subtree hides it completely — the viewer can't compare a collapsed branch against an expanded one. If the task is comparison across branches (e.g., "which department spends more?"), use a static layout that shows everything, or use linked highlighting instead. Collapse works best for navigation tasks ("find the node called X") where hiding irrelevant branches reduces clutter.

**Expand/collapse also hurts at scale.** Each toggle re-runs the layout and shifts every sibling. In wide trees (50+ siblings at one level), the resulting animation is chaotic — too many things move at once for the viewer to track what changed. Consider a zoomable layout or fisheye distortion instead.

**Zoomable treemap is overkill without 3+ levels of meaningful detail.** If your hierarchy is only 2 levels deep, a static treemap with group labels is clearer — the viewer sees everything at once without needing to click. Zooming pays off when deeper levels contain genuinely different information (e.g., department > team > person > project), not just more of the same.

**Zoomable sunburst loses area accuracy.** As arcs zoom to fill the circle, the viewer loses the part-to-whole comparison that made the sunburst useful. If precise size comparison matters, a zoomable treemap preserves rectangular proportions better.

## Expand/Collapse: The `_children` Toggle

D3 hierarchy layouts only visit `node.children`. To collapse, move children to a private `_children` property:

```js
function toggle(event, d) {
  if (d.children) { d._children = d.children; d.children = null; }
  else if (d._children) { d.children = d._children; d._children = null; }
  update(d);
}
```

After toggling, recompute layout and rejoin. **Entering nodes must start at the parent's previous position, exiting nodes must converge to the parent's new position.** This is what makes the animation legible — children visually emerge from or collapse into their parent, preserving the spatial metaphor that children belong to that parent. Without it, nodes appear from the origin or vanish in place, and the viewer can't tell what changed. Stash positions after each update:

```js
nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y; });
```

After swapping `children`/`_children`, re-run the layout (and `.sum()` if values depend on leaves).

## Canvas Expand/Collapse (500+ Nodes)

Without DOM elements, maintain a `positions` Map and interpolate toward layout targets using `d3.timer`. The pattern: compute target positions for all nodes (visible nodes get their layout position, collapsed children converge to their parent's position), build interpolators from current to target, and animate.

For nodes being expanded, initialize their position at the parent before interpolating — otherwise they appear from whatever stale position they had last.

**Stale quadtree after collapse:** The quadtree holds positions from before the transition. Rebuild it in the timer's completion callback, not at the start — otherwise hit detection is wrong during the entire animation.

## Zoomable Treemap

Click a cell to zoom into that subtree. The key insight: **narrow the x/y scale domains to the focused node's bounds.** All descendants rescale automatically because they're positioned through the same scales. No need to re-run `d3.treemap()` — the layout coordinates don't change, only the mapping to screen pixels does.

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

Without clipping, cells overshoot their parent's bounds mid-transition — the linear interpolation of source and target positions doesn't respect containment at intermediate frames. Apply `clipPath` to each group and transition the clip rect dimensions alongside the cell rect.

### Breadcrumb Navigation

Build from `focus.ancestors().reverse()`. Each crumb click resets `x`/`y` domains to that ancestor's bounds. Breadcrumbs matter more here than in sunburst/pack because treemap cells don't have an obvious "click to go back" target — the parent cell is behind the children, not visually distinct.

## Zoomable Sunburst: Arc Tween

Click an arc to make it the new center. The partition layout is computed once; zoom remaps angles and radii relative to the clicked node so it fills the full circle.

```js
function clicked(event, p) {
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

**Why `attrTween`, not `attr`:** Arc paths are complex strings. Interpolating the string directly produces garbled intermediate paths. Instead, interpolate the numeric angle/radius properties and call the arc generator each frame. Stash these on the datum (`d.current`) — initialize with `paths.each(d => { d.current = d; })`.

**Visibility during zoom:** Arcs outside the visible ring range (`y0 >= 1 && y1 <= 3`) should get `pointer-events: none` and `fill-opacity: 0`. Labels need a stricter test — only show when the arc's angular span times radial span exceeds a threshold (~0.03), otherwise text overlaps.

## Zoomable Circle Pack

Uses `d3.interpolateZoom` (van Wijk & Nuij, 2003) for mathematically smooth zooming — it pans and scales simultaneously along the shortest perceptual path, avoiding the disorienting "zoom all the way out then back in" effect that naive position + scale interpolation produces.

All circles are positioned relative to a `view = [x, y, diameter]`:

```js
function zoomTo(v) {
  const k = width / v[2];
  view = v;
  node.attr("transform", d =>
    `translate(${(d.x - v[0]) * k + width / 2},${(d.y - v[1]) * k + height / 2})`);
  node.select("circle").attr("r", d => d.r * k);
}

svg.transition().duration(750)
  .tween("zoom", () => {
    const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
    return t => zoomTo(i(t));
  });
```

## Semantic vs Geometric Zoom

**Geometric zoom** applies a single CSS/Canvas transform — fast, but text and strokes scale with everything else, becoming unreadable at extremes. **Semantic zoom** re-renders at the new scale with appropriate detail levels. Use semantic zoom when the hierarchy has meaningful information at multiple scales:

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
| Collapsible tree, <500 nodes | Preferred — transitions and hit detection are free | |
| Collapsible tree, >500 nodes | | Preferred — DOM nodes are the bottleneck |
| Zoomable treemap | Preferred — rect transitions, clipPath | |
| Zoomable sunburst | Preferred — `attrTween` makes arc interpolation clean | |
| Pan+zoom over large hierarchy | | Preferred — geometric zoom is a single transform |

## Common Pitfalls

1. **Children appear from (0,0) on expand.** Entering nodes must start at the parent's position. Stash `d.x0`/`d.y0` after each update — the stashed position becomes the source for the next transition's enter animation.
2. **Double-click fires click first.** Use a 250ms timer to distinguish, or avoid the conflict entirely: single-click for toggle, modifier+click for select.
3. **Treemap cells overflow during zoom transition.** Apply `clipPath` so children don't render outside parent bounds mid-transition. This is only visible during the animation — easy to miss in development.
4. **Enter + update not merged.** Use `.merge()` or `.join()` so both entering and updating nodes get the position transition. Otherwise new nodes jump to final position while existing nodes animate.

## References

- [Zoomable Treemap](https://observablehq.com/@d3/zoomable-treemap) — Mike Bostock's canonical drill-down treemap
- [Zoomable Sunburst](https://observablehq.com/@d3/zoomable-sunburst) — arc-tween sunburst with focus+context
- [Zoomable Circle Packing](https://observablehq.com/@d3/zoomable-circle-packing) — zoom-to-focus circle pack
- [Animated Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — van Wijk & van de Wetering on smooth treemap transitions (IEEE InfoVis 2001)
- [Focus+Context Interfaces Review](https://worrydream.com/refs/Cockburn_2007_-_A_Review_of_Overview+Detail,_Zooming,_and_Focus+Context_Interfaces.pdf) — Cockburn et al. survey of overview+detail, zooming, and focus+context techniques
