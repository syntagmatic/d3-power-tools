---
name: hierarchy-interaction
description: "Interactive patterns for D3.js hierarchy visualizations: expand/collapse subtrees, zoomable treemap, zoomable sunburst, zoomable circle pack, and focus+context navigation. Use this skill whenever the user wants to make a tree, treemap, sunburst, icicle, dendrogram, or circle pack interactive — collapsing or expanding branches, zooming into subtrees, clicking to drill down, animating between hierarchy focus levels, or adding breadcrumb navigation. Also use when the user mentions collapsible tree, drill-down, zoom-to-node, or focus+context in the context of hierarchies."
---

# Hierarchy Interaction

Interactive patterns for navigating hierarchical data with D3. Collapse hides complexity, zoom reveals detail. Both need animated transitions so the viewer maintains spatial context — without animation, the connection between "where I was" and "where I am" is lost.

## Expand/Collapse (SVG)

The canonical D3 pattern for collapsible trees. Works with `d3.tree()`, `d3.cluster()`, or any layout that reads `.children`.

### The `_children` Toggle

D3 hierarchy layouts only visit `node.children`. To collapse, move children to a private `_children` property:

```js
function toggle(event, d) {
  if (d.children) {
    d._children = d.children;
    d.children = null;
  } else if (d._children) {
    d.children = d._children;
    d._children = null;
  }
  update(d);
}
```

### The Update Function

After toggling, recompute layout and rejoin. The key: entering nodes start at the parent's **previous** position, exiting nodes converge to the parent's **new** position. This creates the visual effect of children emerging from or collapsing into their parent.

```js
function update(source) {
  const treeLayout = d3.tree().size([height, width - 160]);
  treeLayout(root);

  const nodes = root.descendants();
  const links = root.links();

  // Nodes
  const node = svg.selectAll("g.node")
    .data(nodes, d => d.data.id);

  const nodeEnter = node.enter().append("g")
    .attr("class", "node")
    .attr("transform", `translate(${source.y0},${source.x0})`)
    .on("click", toggle);

  nodeEnter.append("circle")
    .attr("r", 1e-6)
    .attr("fill", d => d._children ? "#555" : "#999");

  const nodeUpdate = nodeEnter.merge(node);

  nodeUpdate.transition().duration(500)
    .attr("transform", d => `translate(${d.y},${d.x})`);

  nodeUpdate.select("circle")
    .attr("r", 5)
    .attr("fill", d => d._children ? "#555" : "#999");

  const nodeExit = node.exit().transition().duration(500)
    .attr("transform", `translate(${source.y},${source.x})`)
    .remove();

  nodeExit.select("circle").attr("r", 1e-6);

  // Links
  const link = svg.selectAll("path.link")
    .data(links, d => d.target.data.id);

  const linkEnter = link.enter().insert("path", "g")
    .attr("class", "link")
    .attr("d", d3.linkHorizontal()
      .x(() => source.y0).y(() => source.x0));

  linkEnter.merge(link).transition().duration(500)
    .attr("d", d3.linkHorizontal().x(d => d.y).y(d => d.x));

  link.exit().transition().duration(500)
    .attr("d", d3.linkHorizontal()
      .x(() => source.y).y(() => source.x))
    .remove();

  // Stash positions for next transition
  nodes.forEach(d => {
    d.x0 = d.x;
    d.y0 = d.y;
  });
}
```

### Collapse Indicators

Filled vs hollow circles are the simplest indicator. For explicit `+`/`-`:

```js
nodeUpdate.select("text.indicator")
  .text(d => d._children ? "+" : d.children ? "\u2212" : "");
```

### Click vs Double-Click Disambiguation

If single-click selects and double-click toggles, use a timer to distinguish:

```js
let clickTimer = null;

function onClick(event, d) {
  if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; return; }
  clickTimer = setTimeout(() => { clickTimer = null; select(d); }, 250);
}

function onDblClick(event, d) {
  if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; }
  toggle(event, d);
}
```

An alternative: use single-click for toggle (simpler, more common in Bostock's examples), and hover for highlighting.

## Expand/Collapse (Canvas)

For hierarchies with 500+ nodes, Canvas avoids DOM overhead. The core `_children` toggle is identical. The differences are in rendering and animation.

### Position Tracking and Animation

Without DOM elements, maintain current positions and interpolate toward targets:

```js
const positions = new Map(); // nodeId → {x, y, r, opacity}

function toggle(d) {
  if (d.children) { d._children = d.children; d.children = null; }
  else if (d._children) { d.children = d._children; d._children = null; }
  animateToLayout();
}

function animateToLayout() {
  const treeLayout = d3.tree().size([height, width - 160]);
  treeLayout(root);

  // Compute targets: visible nodes at layout positions,
  // hidden nodes at their parent's position
  const targets = new Map();
  root.descendants().forEach(d => {
    targets.set(d.data.id, { x: d.y, y: d.x, r: 5, opacity: 1 });
  });

  // Collapsed children converge to parent
  root.each(d => {
    if (d._children) {
      d._children.forEach(function walk(child) {
        targets.set(child.data.id, {
          x: d.y, y: d.x, r: 0, opacity: 0
        });
        (child.children || child._children || []).forEach(walk);
      });
    }
  });

  // Expanding children: initialize at parent position if no prior position
  for (const [id, target] of targets) {
    if (!positions.has(id)) {
      positions.set(id, { ...target });
    }
  }

  const duration = 500;
  const ease = d3.easeCubicInOut;
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
    const t = ease(Math.min(1, elapsed / duration));

    for (const [id, interp] of interps) {
      positions.set(id, {
        x: interp.x(t), y: interp.y(t),
        r: interp.r(t), opacity: interp.opacity(t),
      });
    }

    draw();
    if (elapsed >= duration) {
      // Snap to final values
      for (const [id, target] of targets) positions.set(id, { ...target });
      draw();
      rebuildHitDetection(); // quadtree must reflect new positions
      return true; // stop timer
    }
  });
}
```

### Hit Detection After Collapse

After a collapse/expand transition completes, the quadtree must be rebuilt — it still holds the old positions. See the `canvas-rendering` skill for quadtree hit detection patterns.

## Zoomable Treemap

Click a cell to zoom into that subtree. The canonical pattern rescales existing layout coordinates rather than re-running `d3.treemap()`.

### Setup

```js
const treemap = d3.treemap()
  .size([width, height])
  .paddingOuter(3)
  .paddingInner(1)
  .paddingTop(19)
  .round(true);

const root = treemap(d3.hierarchy(data)
  .sum(d => d.value)
  .sort((a, b) => b.value - a.value));

const x = d3.scaleLinear().rangeRound([0, width]);
const y = d3.scaleLinear().rangeRound([0, height]);
```

### Zoom to Node

The key insight: narrow the x/y scale domains to the focused node's bounds. All descendants rescale automatically.

```js
let currentFocus = root;

function zoomIn(d) {
  const group = d.parent === currentFocus ? d : d.parent;
  if (!group || !group.children) return;
  currentFocus = group;

  x.domain([group.x0, group.x1]);
  y.domain([group.y0, group.y1]);

  const t = svg.transition().duration(750);

  cell.transition(t)
    .attr("transform", d => `translate(${x(d.x0)},${y(d.y0)})`)
    .select("rect")
      .attr("width", d => x(d.x1) - x(d.x0))
      .attr("height", d => y(d.y1) - y(d.y0));

  // Hide cells not in the focused subtree
  cell.transition(t)
    .attr("opacity", d => isDescendant(d, group) ? 1 : 0);
}

function zoomOut() {
  if (currentFocus === root) return;
  currentFocus = currentFocus.parent;

  x.domain([currentFocus.x0, currentFocus.x1]);
  y.domain([currentFocus.y0, currentFocus.y1]);

  const t = svg.transition().duration(750);

  cell.transition(t)
    .attr("transform", d => `translate(${x(d.x0)},${y(d.y0)})`)
    .attr("opacity", d => isDescendant(d, currentFocus) ? 1 : 0)
    .select("rect")
      .attr("width", d => x(d.x1) - x(d.x0))
      .attr("height", d => y(d.y1) - y(d.y0));
}

function isDescendant(node, ancestor) {
  while (node) {
    if (node === ancestor) return true;
    node = node.parent;
  }
  return false;
}
```

### Breadcrumb Navigation

```js
function updateBreadcrumbs(focus) {
  const ancestors = focus.ancestors().reverse();

  const crumb = nav.selectAll("span.crumb")
    .data(ancestors, d => d.data.name);

  crumb.enter().append("span")
    .attr("class", "crumb")
    .style("cursor", "pointer")
    .text(d => d.data.name)
    .on("click", (event, d) => {
      currentFocus = d;
      x.domain([d.x0, d.x1]);
      y.domain([d.y0, d.y1]);
      transition();
    });

  crumb.exit().remove();
}
```

### Clipping During Transitions

Without clipping, cells overshoot their parent's bounds mid-transition:

```js
// Add clipPath per group
group.append("clipPath")
  .attr("id", d => `clip-${d.data.id}`)
  .append("rect");

// Reference it
group.attr("clip-path", d => `url(#clip-${d.data.id})`);

// Update clip rect with parent bounds during transition
group.select("clipPath rect").transition(t)
  .attr("width", d => x(d.x1) - x(d.x0))
  .attr("height", d => y(d.y1) - y(d.y0));
```

## Zoomable Sunburst

Click an arc to make it the new center. The partition layout is computed once; zoom is achieved by remapping angles and radii relative to the clicked node.

### Setup

```js
const radius = width / 2;
const partition = d3.partition().size([2 * Math.PI, radius]);
const root = partition(d3.hierarchy(data).sum(d => d.value));

const arc = d3.arc()
  .startAngle(d => d.x0)
  .endAngle(d => d.x1)
  .padAngle(d => Math.min((d.x1 - d.x0) / 2, 0.005))
  .padRadius(radius / 2)
  .innerRadius(d => d.y0)
  .outerRadius(d => Math.max(d.y0, d.y1 - 1));
```

### Arc Tween on Click

Each arc stores its `current` angles/radii. On click, compute `target` angles/radii relative to the clicked node, then tween between them.

```js
function clicked(event, p) {
  // Compute target layout: p fills the full circle
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
    .filter(function(d) {
      return +this.getAttribute("fill-opacity") || arcVisible(d.target);
    })
    .attr("fill-opacity", d => arcVisible(d.target) ? (d.children ? 0.6 : 0.4) : 0)
    .attr("pointer-events", d => arcVisible(d.target) ? "auto" : "none")
    .attrTween("d", d => () => arc(d.current));

  // Update labels similarly
  labels.transition(t)
    .attr("fill-opacity", d => +labelVisible(d.target))
    .attrTween("transform", d => () => labelTransform(d.current));
}

function arcVisible(d) {
  return d.y1 <= 3 && d.y0 >= 1 && d.x1 > d.x0;
}

function labelVisible(d) {
  return d.y1 <= 3 && d.y0 >= 1 && (d.y1 - d.y0) * (d.x1 - d.x0) > 0.03;
}

function labelTransform(d) {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
  const y = (d.y0 + d.y1) / 2 * radius;
  return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
}
```

### Stashing Current State

The `.current` property must be initialized when arcs are first created:

```js
paths.each(function(d) { d.current = d; });
```

This is the starting state for the first tween. Stash on the datum (not `this`) because `d3.interpolate` reads the angle/radius properties directly.

## Zoomable Circle Pack

Click a circle to zoom in. Uses `d3.interpolateZoom` for mathematically smooth zooming (van Wijk & Nuij, 2003).

### Setup

```js
const pack = d3.pack()
  .size([width, height])
  .padding(3);

const root = pack(d3.hierarchy(data)
  .sum(d => d.value)
  .sort((a, b) => b.value - a.value));

let focus = root;
let view;
```

### Zoom Transform

All circles are positioned relative to a `view` = `[x, y, diameter]`:

```js
function zoomTo(v) {
  const k = width / v[2];
  view = v;

  node.attr("transform", d =>
    `translate(${(d.x - v[0]) * k + width / 2},${(d.y - v[1]) * k + height / 2})`);
  node.select("circle").attr("r", d => d.r * k);
}

// Initialize
zoomTo([root.x, root.y, root.r * 2]);
```

### Click to Zoom

```js
function zoom(event, d) {
  focus = d;
  event.stopPropagation();

  svg.transition().duration(750)
    .tween("zoom", () => {
      const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
      return t => zoomTo(i(t));
    });

  // Show labels only for children of the focused node
  label.transition().duration(750)
    .style("fill-opacity", d => d.parent === focus ? 1 : 0)
    .style("display", d => d.parent === focus ? "inline" : "none");
}

// Click background to zoom out
svg.on("click", (event) => zoom(event, root));
```

`d3.interpolateZoom` automatically computes the optimal zoom path — it pans and scales simultaneously along the shortest perceptual path, avoiding the disorienting "zoom all the way out then back in" effect.

## Zoom + Pan with `d3.zoom()`

For free-form navigation over a hierarchy (or any visualization):

```js
const zoom = d3.zoom()
  .scaleExtent([1, 8])
  .translateExtent([[0, 0], [width, height]])
  .on("zoom", zoomed);

svg.call(zoom);

function zoomed(event) {
  g.attr("transform", event.transform);
}
```

### Canvas Zoom

For Canvas, apply the transform before drawing:

```js
const zoom = d3.zoom()
  .scaleExtent([0.5, 10])
  .on("zoom", (event) => {
    ctx.save();
    ctx.clearRect(0, 0, width, height);
    ctx.translate(event.transform.x, event.transform.y);
    ctx.scale(event.transform.k, event.transform.k);
    draw();
    ctx.restore();
  });

d3.select(canvas).call(zoom);
```

### Semantic vs Geometric Zoom

**Geometric zoom** scales the entire drawing uniformly — fast but text and strokes scale too. **Semantic zoom** re-renders at the new scale with appropriate detail levels:

```js
function zoomed(event) {
  const k = event.transform.k;

  if (k > 4) {
    drawDetailedView(event.transform);  // show labels, sub-nodes
  } else if (k > 2) {
    drawMediumView(event.transform);    // show primary labels
  } else {
    drawOverview(event.transform);       // aggregate, no labels
  }
}
```

See the `canvas-rendering` skill for level-of-detail rendering patterns.

## Canvas vs SVG

| Pattern | SVG | Canvas |
|---------|-----|--------|
| Collapsible tree, <500 nodes | Preferred — DOM join handles enter/exit naturally | |
| Collapsible tree, >500 nodes | | Preferred — no DOM overhead |
| Zoomable treemap | Preferred — rect transitions, clipPath | |
| Zoomable sunburst | Preferred — arc tween with `attrTween` | |
| Zoomable circle pack | Either works well | |
| Pan+zoom over large hierarchy | | Preferred — geometric zoom is a single transform |

For Canvas interaction patterns (hit detection, keyboard nav), see the `canvas-rendering` and `canvas-accessibility` skills. For animation mechanics (easing, interruption, canvas animation loops), see the `animated-transitions` skill.

## Common Pitfalls

1. **Children appear from (0,0) on expand.** Entering nodes must start at the parent's position, not the SVG origin. Stash `d.x0`/`d.y0` after each update and use them as the enter position on the next update.

2. **Layout values wrong after toggle.** After swapping `children`/`_children`, you must re-run the layout (and `.sum()` if values depend on leaves). The layout reads the current `.children` — stale values produce wrong sizes.

3. **Arc tween goes the wrong way around.** `d3.interpolate` on raw angles works because it interpolates numbers directly. Don't interpolate SVG path strings — use `attrTween("d", ...)` with the arc generator called per-frame on the interpolated angle/radius object.

4. **Double-click fires click first.** A click handler fires on the first click of a double-click. Use a 250ms timer to distinguish, or avoid the conflict entirely by using single-click for the more common action (toggle) and a modifier key or separate UI for the less common one (select).

5. **Treemap cells overflow during zoom transition.** Rescaling `x`/`y` domains causes cells to pass through intermediate sizes. Apply `clipPath` to each group so children don't render outside their parent's bounds mid-transition.

6. **Stale quadtree after collapse (Canvas).** The quadtree holds positions from before the transition. Rebuild it in the timer's completion callback, not at the start.

7. **Enter + update not merged.** In the collapsible tree pattern, entering nodes need the same transition as updating nodes. Use `.merge()` or `.join()` so both sets get the position transition — otherwise entering nodes appear at the parent position and stay there.

## References

- [Zoomable Treemap](https://observablehq.com/@d3/zoomable-treemap) — Mike Bostock's canonical drill-down treemap
- [Zoomable Sunburst](https://observablehq.com/@d3/zoomable-sunburst) — arc-tween sunburst with focus+context
- [Zoomable Circle Packing](https://observablehq.com/@d3/zoomable-circle-packing) — zoom-to-focus circle pack
- [Collapsible Tree](https://observablehq.com/@d3/collapsible-tree) — expand/collapse tree layout
- [D3 Zoom documentation](https://d3js.org/d3-zoom) — API reference for `d3.zoom`, transforms, and programmatic zoom
- [D3 Hierarchy documentation](https://d3js.org/d3-hierarchy) — `d3.hierarchy`, traversal helpers, `node.descendants()`, `node.copy()`
- [Animated Treemaps](https://www.win.tue.nl/~vanwijk/stm.pdf) — Jarke van Wijk & Huub van de Wetering's research on smooth treemap transitions (IEEE InfoVis 2001)
