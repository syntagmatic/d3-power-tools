# Hierarchy interaction

Absorbed from the v2 `hierarchy-interaction` skill. Open when building expand/collapse trees or zoomable treemap, sunburst, icicle, or pack.

## When interaction hurts

- **Collapse hides comparison.** A collapsed branch can't be compared with an expanded one. For "which branch is bigger" tasks, show everything or use linked highlighting. Collapse suits navigation ("find X").
- **Wide levels (50+ siblings).** Each toggle re-runs the layout and shifts every sibling, too much motion to track. Use a zoomable layout or fisheye.
- **Zoomable treemap on 2 levels.** A static treemap with group labels shows it all. Zoom pays off at 3+ levels where deeper levels say something new.
- **Zoomable sunburst** loses part-to-whole once arcs stretch to fill the circle. If size comparison matters, zoom a treemap instead.

## Expand/collapse

Layouts only visit `children`, so park collapsed children on `_children`:

```js
function toggle(d) {
  if (d.children) { d._children = d.children; d.children = null; }
  else if (d._children) { d.children = d._children; d._children = null; }
}
```

Then re-run `.sum()` if values roll up, re-run the layout, and rejoin. Enter at the clicked node's **old** position (`source.x0, source.y0`), exit to its **new** position, then stash `d.x0 = d.x; d.y0 = d.y` for next time. Otherwise children fly from (0,0) or vanish in place.

Canvas (500+ nodes): keep a `positions` Map, build interpolators from current to target (hidden nodes target their visible ancestor), and step them in `d3.timer`. Newly expanded nodes start at the parent. Rebuild the hit-test quadtree when the timer finishes, not when it starts.

## Zoomable treemap

Lay out once. Zoom by narrowing the x/y scale domains to the focus node's bounds; everything re-maps through the same scales.

```js
function zoomTo(focus, cell, x, y, t) {
  x.domain([focus.x0, focus.x1]);
  y.domain([focus.y0, focus.y1]);
  cell.transition(t)
    .attr("transform", d => `translate(${x(d.x0)},${y(d.y0)})`)
    .select("rect")
      .attr("width", d => Math.max(0, x(d.x1) - x(d.x0)))
      .attr("height", d => Math.max(0, y(d.y1) - y(d.y0)));
}
```

- Clip each cell (`clipPath`, transitioned alongside the rect). Mid-transition interpolation doesn't respect containment, so children overshoot their parent. Only visible while animating, so it's easy to miss.
- Breadcrumbs from `focus.ancestors().reverse()` are required, not optional. After two zoom levels nobody can reconstruct the path, and in a treemap the parent sits behind its children.
- Re-fit labels on transition **end**, not per frame (flicker).
- Touch: small cells can't be tapped reliably. Aim for 44×44px targets (WCAG 2.5.5 AAA; the AA minimum in 2.5.8 is 24×24). For smaller cells, first tap selects and outlines, second tap zooms.

## Zoomable sunburst

Partition once. On click, compute a target for every node relative to the clicked node `p`, then tween the numbers and call the arc generator each frame. Interpolating path strings produces garbage.

```js
function sunburstTargets(root, p) {
  root.each(d => {
    d.target = {
      x0: Math.max(0, Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
      x1: Math.max(0, Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
      y0: Math.max(0, d.y0 - p.depth),
      y1: Math.max(0, d.y1 - p.depth),
    };
  });
}
// path.transition(t).tween("data", d => { const i = d3.interpolate(d.current, d.target); return t => d.current = i(t); })
//     .attrTween("d", d => () => arc(d.current));
```

Initialize `d.current = d` on first draw. Arc visible when `y1 <= 3 && y0 >= 1 && x1 > x0` (else `fill-opacity: 0` and `pointer-events: none`); label visible when `(y1 - y0) * (x1 - x0) > 0.03`.

## Zoomable pack

Position everything relative to `view = [cx, cy, diameter]` and tween with `d3.interpolateZoom` (van Wijk & Nuij), which pans and zooms together along a smooth path instead of zooming out and back in.

```js
function packZoomTo(v, node, width, height) {
  const k = width / v[2];
  node.attr("transform", d => `translate(${(d.x - v[0]) * k + width / 2},${(d.y - v[1]) * k + height / 2})`);
  node.select("circle").attr("r", d => d.r * k);
}
// tween: const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]); t => packZoomTo(view = i(t), ...)
```

## Geometric vs semantic zoom

Geometric (one transform) scales text and strokes with everything. Semantic zoom redraws with detail chosen by `k`: overview without labels, primary labels past ~2×, sub-nodes past ~4×.

## SVG or Canvas

| Pattern | Use |
|---|---|
| Collapsible tree < 500 nodes, zoomable treemap, zoomable sunburst | SVG (transitions, clipPath, `attrTween`) |
| Collapsible tree > 500 nodes, pan/zoom over a large hierarchy | Canvas |

## Pitfalls

- Children appear from (0,0): no stashed `x0/y0`.
- dblclick fires two clicks first. Use a ~250ms timer, or modifier+click for the second action.
- New nodes jump while old ones animate: enter and update weren't merged (`.join()`).
- Two unnamed transitions on the same element (one for transform, one for opacity): the second interrupts the first and nodes never move. Chain on one transition or name them.
- Observable Plot has no hierarchy interaction; use it only to decide whether interaction is warranted.
