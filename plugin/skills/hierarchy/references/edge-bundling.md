# Hierarchical edge bundling

Absorbed from the v2 `edge-bundling` skill. Open when drawing leaf-to-leaf links over a hierarchy: dependency wheels, import graphs, module coupling.

Bundling (Holten 2006) routes each link along the tree path between its endpoints, through their lowest common ancestor. Links that share ancestry merge into visible bundles. It trades edge-level accuracy for group-level pattern.

## Beta

`d3.curveBundle.beta(β)` straightens each control point toward the chord between the endpoints: `p' = β·p + (1 − β)·(straight-line point)`.

| β | Result |
|---|---|
| 0 | straight line between endpoints (no bundling) |
| 0.85 | d3's default; group-level bundles, individual links still partly separable |
| 1 | B-spline through the full LCA control path (maximum bundling) |

Higher β = tighter bundles. Never write `beta(1 - tension)`: that inverts the slider so "high tension" draws nearly straight lines. The v2 examples shipped with that bug.

- Start at 0.85. If bundles from unrelated clusters merge into one river, lower β (~0.5-0.7) until they separate.
- Tight bundles invite false connections: viewers follow a merged bundle and read paths that aren't in the data. For static output (no slider to check against), bundle less.
- A β slider turns bundling into a lens the viewer controls.

## Data

```js
function bundleLinks(root, connections) {
  const byId = new Map(root.leaves().map(d => [d.data.id, d]));
  const missing = [];
  const links = connections.flatMap(c => {
    const s = byId.get(c.source), t = byId.get(c.target);
    if (!s || !t) { missing.push(c); return []; }
    return [s.path(t)]; // [source, ..., LCA, ..., target]
  });
  if (missing.length) console.warn("unmatched link ids", missing);
  return links;
}
```

Unmatched ids drop edges silently. Typical mismatch: `"vis.chart"` vs `"root.vis.chart"`. Log them.

## Layout

- `d3.cluster`, not `d3.tree`: cluster puts every leaf on the same ring.
- `.size([2 * Math.PI, radius - labelRoom])`, and `.separation((a, b) => a.parent === b.parent ? 1 : 2)` to open gaps between groups.
- Draw only leaves. Internal nodes are invisible waypoints.
- Radial path: `d3.lineRadial().curve(d3.curveBundle.beta(0.85)).radius(d => d.y).angle(d => d.x)`. Cartesian layouts use `d3.line` with x/y accessors over the same `node.path()` arrays.

## Rendering

| Links | Approach |
|---|---|
| < 200 | SVG paths |
| 200-2,000 | SVG with low `stroke-opacity` (~0.2-0.3) against overdraw |
| 2,000-50,000 | Canvas: `line.context(ctx)`, one `beginPath`/`stroke` per link |
| 50,000+ | Canvas, path computation in a Worker |

Highlighting is what makes bundling analyzable: on hover, collect links whose first or last node is in `node.leaves()`, fade the rest, and `.raise()` the highlighted paths (Canvas: draw them in a second pass). Otherwise they sink under the gray.

## Transitions between layouts

Bundles survive layout changes because `node.path()` depends on the tree, not on positions. Interpolate every node's position (internal nodes too) in data space, then redraw the curves each frame from the current positions.

```js
function tweenLayout(root, toXY, redraw) {
  root.each(d => { d.sx = d.cx; d.sy = d.cy; [d.tx, d.ty] = toXY(d); });
  return t => {
    root.each(d => { d.cx = d.sx + (d.tx - d.sx) * t; d.cy = d.sy + (d.ty - d.sy) * t; });
    redraw(); // d3.line().curve(d3.curveBundle.beta(b)).x(d => d.cx).y(d => d.cy)
  };
}
```

Convert radial layouts to Cartesian in `toXY` first. No path morphing needed: the curve is a function of its control points.

## When not to bundle

- The viewer must answer "does A depend on B?": bundling hides it. Use an adjacency matrix or node-link with hover.
- The hierarchy is flat or arbitrary: bundles only mean what the grouping means. Root → leaves gives nothing.
- Most links stay within one parent: they barely curve. A grouped adjacency matrix shows within-group density better.
- Under ~30 links: straight lines plus highlighting.

## Other bundling families

| Method | Needs | Use when |
|---|---|---|
| Hierarchical (Holten 2006) | a tree | natural grouping exists; bundles reflect the hierarchy, not graph paths |
| Edge-path bundling (Wallinger et al. 2022) | a graph | no hierarchy, and merged bundles must correspond to real paths |
| Divided edge bundling (Selassie, Heller, Heer 2011) | directed edges | direction matters; opposite flows are separated instead of merged |

None ship with D3 besides hierarchical; Observable Plot has no bundling.

## Pitfalls

- Mismatched ids: silent edge loss.
- Internal nodes drawn as dots.
- Radial labels collide past roughly 100 leaves at typical sizes: enlarge the radius, label on hover, or thin the labels.
- Links to internal nodes: short LCA paths, little bundling, stray straight-ish strokes in the middle.
