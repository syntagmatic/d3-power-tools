# Annotation

Absorbed from the v2 `annotation` skill. Open for callout geometry, label collision code, SVG text wrapping, Canvas callouts, or scroll-sequenced notes.

## Connectors

Offsets `(dx, dy)` from the subject to the note:

```js
const connectors = {
  straight: (dx, dy) => `M0,0L${dx},${dy}`,
  elbow:    (dx, dy) => `M0,0L${dx},0L${dx},${dy}`,
  curve:    (dx, dy) => `M0,0Q${dx},0 ${dx},${dy}`,
  sCurve:   (dx, dy) => `M0,0C${dx / 2},0 ${dx / 2},${dy} ${dx},${dy}`,
};
```

Straight for sparse charts, elbow when the note sits beside the point, and curves to route around dense regions. Put the control point on the side away from the data.

## Annotation as data

```js
const annotations = [
  { id: "declared", x: new Date("2020-03-11"), y: 142000, dx: -80, dy: -40, title: "Pandemic declared", body: "Sharpest weekly rise followed.", priority: 1, connector: "curve" },
  { id: "vaccine",  x: new Date("2021-01-04"), y: 98000,  dx: 60,  dy: -30, title: "Vaccine rollout",   body: "First doses administered.",     priority: 2, connector: "elbow" },
];
```

Render with a keyed `.join()`. On resize, recompute pixels from data coordinates, filter by priority, and flip offsets that would overflow:

```js
function fitNote(a, width, height) {
  if (a.px + a.dx + a.w > width) a.dx = -Math.abs(a.dx) - a.w;
  if (a.py + a.dy + a.h > height) a.dy = -Math.abs(a.dy) - a.h;
  return a;
}
```

Susie Lu's d3-annotation (unmaintained since 2019) gives the subject + connector + note model with an edit mode. It's worth it for many richly styled SVG callouts. Hand-roll for Canvas or custom connectors.

## Label collision

Rectangular collision force. `forceCollide` is circular and wrong for text boxes.

```js
function rectCollide(size, padding = 2) {
  let nodes;
  function force(alpha) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const [aw, ah] = size(a), [bw, bh] = size(b);
        const dx = b.x - a.x, dy = b.y - a.y;
        const ox = (aw + bw) / 2 + padding - Math.abs(dx);
        const oy = (ah + bh) / 2 + padding - Math.abs(dy);
        if (ox <= 0 || oy <= 0) continue;
        const k = ox < oy ? "x" : "y";
        const shift = (k === "x" ? ox : oy) * alpha * 0.5 * (Math.sign(k === "x" ? dx : dy) || 1);
        a[k] -= shift; b[k] += shift;
      }
    }
  }
  force.initialize = n => { nodes = n; };
  return force;
}
```

Pair it with weak `forceX/forceY` back to the anchor. Run `sim.stop(); sim.tick(120);` offline. If labels jitter, raise `velocityDecay` to ~0.6. Width without the DOM: `label.length * fontSize * 0.6`.

Greedy placement, O(n) and good for sparse charts:

```js
const OFFSETS = [[10, 0], [10, -10], [0, -14], [-10, -10], [-10, 0], [-10, 10], [0, 14], [10, 10]];
function greedyLabels(points, { fontSize = 12 } = {}) {
  const placed = [];
  const hit = b => placed.some(p => p.x < b.x + b.w && p.x + p.w > b.x && p.y < b.y + b.h && p.y + p.h > b.y);
  return points.map(d => {
    const w = d.label.length * fontSize * 0.6, h = fontSize;
    for (const [ox, oy] of OFFSETS) {
      const box = { x: ox < 0 ? d.px + ox - w : d.px + ox, y: d.py + oy - h, w, h };
      if (!hit(box)) { placed.push(box); return { ...d, lx: d.px + ox, ly: d.py + oy, anchor: ox < 0 ? "end" : "start" }; }
    }
    return { ...d, hidden: true };
  });
}
```

Points that can't be placed are hidden and left to the tooltip. Don't stack them on top of one another.

## SVG text wrapping

SVG doesn't wrap. Split into `<tspan>`s by measuring. The node must already be in the DOM, or `getComputedTextLength()` returns 0.

```js
function wrap(text, maxWidth) {
  text.each(function () {
    const t = d3.select(this), x = t.attr("x") || 0;
    const words = t.text().split(/\s+/).reverse();
    let line = [], word, tspan = t.text(null).append("tspan").attr("x", x);
    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > maxWidth && line.length > 1) {
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        tspan = t.append("tspan").attr("x", x).attr("dy", "1.2em").text(word);
      }
    }
  });
}
```

## Canvas callouts

Draw the connector, a ring on the subject, then text with `textAlign` chosen by the sign of `dx`. Wrap in `save()/restore()`. For crisp text over a Canvas data layer, put the annotations in an SVG overlay with `pointer-events: none`.

## Scroll-sequenced annotations

Map step index to an annotation, or `null`. On step enter, clear the layer and render that step's note. Sequence the notes when the story has order or several notes would clutter one view. Show them all at once for one or two claims, expert audiences, or dashboard panels.

## Pitfalls

- More than three callouts and nothing is emphasized.
- Labels past the plot bounds: clamp in the force (a bounding force) or reject in the greedy check.
- Text over varied fills: `paint-order: stroke; stroke: <bg>; stroke-width: 3px`.
- Annotations positioned in pixels drift on resize. Store data coordinates.
