---
name: annotations-and-labels
description: "Build annotations, callouts, leader lines, and responsive labels for D3.js visualizations. Use this skill when the user needs to add explanatory text, callouts with connector lines, responsive label placement, collision-free labeling, or rich tooltips to charts. Covers d3-annotation patterns, custom callout shapes, leader lines, force-based label placement, and responsive strategies."
---

# Annotations and Labels

Patterns for adding explanatory text, callouts, leader lines, and labels to D3 visualizations.

For axis labels and tick formatting, see `axes-and-scales`. For color legends, see `color-and-compositing`. For accessible text alternatives, see `canvas-accessibility`.

## Leader Line Geometry

Three connector types — choose based on visual density:

```js
const straight = (dx, dy) => `M0,0 L${dx},${dy}`;
const elbow = (dx, dy) => `M0,0 L${dx},0 L${dx},${dy}`;
const curved = (dx, dy) => `M0,0 Q${dx},0 ${dx},${dy}`;
const sCurve = (dx, dy) => `M0,0 C${dx*0.5},0 ${dx*0.5},${dy} ${dx},${dy}`;
```

When leader lines cross data points, push the bezier control point away from dense areas:

```js
const cpY = dy > 0 ? -avoidanceOffset : avoidanceOffset;
const path = `M0,0 Q${dx * 0.3},${cpY} ${dx},${dy}`;
```

## Label Collision Avoidance

### Force-Simulation Approach

Best for scatterplots with many labels. Key insight: `forceCollide` is circular, but text labels are rectangular. Use a custom rectangular collision force:

```js
function rectCollideForce(sizeFn, padding = 2) {
  let nodes;
  function force(alpha) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const [aw, ah] = sizeFn(a);
        const [bw, bh] = sizeFn(b);
        const dx = b.x - a.x, dy = b.y - a.y;
        const overlapX = (aw + bw) / 2 + padding - Math.abs(dx);
        const overlapY = (ah + bh) / 2 + padding - Math.abs(dy);
        if (overlapX > 0 && overlapY > 0) {
          // Push apart along axis of least overlap
          if (overlapX < overlapY) {
            const shift = overlapX * alpha * 0.5;
            a.x -= Math.sign(dx) * shift;
            b.x += Math.sign(dx) * shift;
          } else {
            const shift = overlapY * alpha * 0.5;
            a.y -= Math.sign(dy) * shift;
            b.y += Math.sign(dy) * shift;
          }
        }
      }
    }
  }
  force.initialize = (_nodes) => { nodes = _nodes; };
  return force;
}
```

Wire it into a simulation with bounding-box and positional forces. Pre-compute (no animation needed): `simulation.stop(); for (let i = 0; i < 120; i++) simulation.tick();`

Estimate label width: `d.label.length * fontSize * 0.6` (rough but avoids DOM measurement).

### Greedy Algorithm

Simpler: try 8 candidate positions around each point in priority order, accept the first non-overlapping slot:

```js
function greedyLabels(data, xScale, yScale, { fontSize = 12 } = {}) {
  const placed = [];
  // 8 candidates: right, upper-right, above, upper-left, left, lower-left, below, lower-right
  const offsets = [
    [10, 0], [10, -10], [0, -14], [-10, -10],
    [-10, 0], [-10, 10], [0, 14], [10, 10],
  ];
  return data.map(d => {
    const px = xScale(d.x), py = yScale(d.y);
    const w = d.label.length * fontSize * 0.6, h = fontSize;
    for (const [ox, oy] of offsets) {
      const box = { x: px + ox, y: py + oy - h, width: w, height: h };
      if (!placed.some(p =>
        p.x < box.x + box.width && p.x + p.width > box.x &&
        p.y < box.y + box.height && p.y + p.height > box.y
      )) {
        placed.push(box);
        return { ...d, labelX: box.x, labelY: py + oy, anchor: ox < 0 ? "end" : "start" };
      }
    }
    return { ...d, labelX: px + 10, labelY: py, anchor: "start" }; // fallback
  });
}
```

Faster than force but produces worse results for dense plots.

### Voronoi-Based Label Placement

Place labels at Voronoi cell centroids — guarantees each label is in the nearest open space:

```js
const delaunay = d3.Delaunay.from(data, d => xScale(d.x), d => yScale(d.y));
const voronoi = delaunay.voronoi([0, 0, width, height]);
data.forEach((d, i) => {
  const cell = voronoi.cellPolygon(i);
  if (!cell) return;
  d.labelX = d3.mean(cell, p => p[0]);
  d.labelY = d3.mean(cell, p => p[1]);
});
```

## Responsive Repositioning

Store annotations in **data coordinates**, re-compute pixel positions on resize. Flip when annotations overflow:

```js
function repositionAnnotations(width, height) {
  annotations.forEach(a => {
    if (a.targetX + a.dx + a.noteWidth > width)
      a.dx = -Math.abs(a.dx) - a.noteWidth;
    if (a.targetY + a.dy + a.noteHeight > height)
      a.dy = -Math.abs(a.dy) - a.noteHeight;
  });
}
```

Thin labels at breakpoints — show every Nth label on narrow screens:

```js
function updateLabels(width) {
  labels.style("display", (d, i) => {
    if (width < 400) return i % 3 === 0 ? null : "none";
    if (width < 600) return i % 2 === 0 ? null : "none";
    return null;
  });
}
```

Scale annotation font size proportionally: `Math.max(10, Math.min(14, baseFontSize * (width / 800)))`.

## SVG Text Wrapping

SVG has no automatic line wrapping. Split into `<tspan>` elements, measuring with `getComputedTextLength()`:

```js
function wrapText(textSelection, maxWidth) {
  textSelection.each(function () {
    const text = d3.select(this);
    const words = text.text().split(/\s+/).reverse();
    const x = text.attr("x") || 0;
    const dy = parseFloat(text.attr("dy")) || 0;
    let line = [], tspan = text.text(null)
      .append("tspan").attr("x", x).attr("dy", `${dy}em`);
    let word;
    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > maxWidth && line.length > 1) {
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        tspan = text.append("tspan").attr("x", x).attr("dy", "1.2em").text(word);
      }
    }
  });
}
```

## Canvas Annotations

### Canvas Callout

```js
function drawCallout(ctx, { x, y, dx, dy, title, text, color = "#666" }) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(x, y); ctx.lineTo(x + dx, y); ctx.lineTo(x + dx, y + dy);
  ctx.strokeStyle = color; ctx.lineWidth = 1; ctx.stroke();
  ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI);
  ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.textAlign = dx > 0 ? "start" : "end";
  const tx = x + dx + (dx > 0 ? 4 : -4);
  if (title) { ctx.font = "bold 12px sans-serif"; ctx.fillStyle = "#333"; ctx.fillText(title, tx, y + dy - 4); }
  if (text) { ctx.font = "11px sans-serif"; ctx.fillStyle = "#666"; ctx.fillText(text, tx, y + dy + 12); }
  ctx.restore();
}
```

### Canvas Threshold Line

```js
function drawThreshold(ctx, { y, width, label, color = "#e15759" }) {
  ctx.save();
  ctx.setLineDash([6, 3]);
  ctx.strokeStyle = color; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
  ctx.setLineDash([]);
  ctx.font = "bold 12px sans-serif"; ctx.fillStyle = color;
  ctx.textAlign = "end"; ctx.fillText(label, width - 4, y - 6);
  ctx.restore();
}
```

### Hybrid: Canvas Data + SVG Annotations

Best of both worlds. Canvas layer for data performance, SVG overlay for crisp text and interactivity:

```js
const canvas = d3.select(container).append("canvas").style("position", "absolute");
const svg = d3.select(container).append("svg")
  .style("position", "absolute")
  .style("pointer-events", "none"); // clicks pass through to canvas
```

### Annotation Layer Ordering

Keep annotations in a dedicated `<g>` layer above data but below tooltips. SVG renders in document order:

```js
const dataLayer = svg.append("g").attr("class", "data-layer");
const axisLayer = svg.append("g").attr("class", "axis-layer");
const annotationLayer = svg.append("g").attr("class", "annotation-layer");
// Tooltips are HTML divs on top of everything
```

## d3-annotation Library

[d3-annotation](https://d3-annotation.susielu.com/) by Susie Lu provides declarative annotations. Good for quick setups; build from scratch when you need full control.

Types: `annotationLabel`, `annotationCallout`, `annotationCalloutElbow`, `annotationCalloutCurve`, `annotationCalloutCircle`, `annotationXYThreshold`, `annotationBadge`.

## Common Pitfalls

**Labels overflow the chart bounds.** Always clamp label positions to the plot area. With force-based placement, add a bounding box force. With greedy placement, check bounds before accepting.

**Leader lines cross other labels.** Force-based layout naturally minimizes crossings. For manual annotations, route leader lines around obstacles using intermediate waypoints.

**Text not visible on dark backgrounds.** Add a semi-transparent background rect behind annotation text:
```js
const bbox = textNode.getBBox();
g.insert("rect", "text")
  .attr("x", bbox.x - 2).attr("y", bbox.y - 1)
  .attr("width", bbox.width + 4).attr("height", bbox.height + 2)
  .attr("fill", "white").attr("opacity", 0.85);
```

**SVG text doesn't wrap.** No automatic line wrapping. Use the `wrapText` helper above.

**Annotations disappear on resize.** Store annotations in data coordinates and re-compute pixel positions in the resize handler.

**Too many annotations clutter the chart.** Annotate 3-5 key insights, not every data point. Use tooltips for detail-on-demand.

**Annotation z-order wrong.** SVG renders in document order — append annotation `<g>` after data elements. For canvas, draw annotations after data in the render loop.

**getComputedTextLength() returns 0.** Element isn't in the DOM yet. Ensure the element is appended before measuring.

**Canvas text looks blurry.** Scale canvas for retina: `canvas.width = width * dpr; ctx.scale(dpr, dpr)`.

**Force-based labels oscillate forever.** Increase `velocityDecay` (e.g., 0.6). Pre-compute with `simulation.stop(); simulation.tick(120);` rather than animating.

## References

- [d3-annotation](https://d3-annotation.susielu.com/) — Susie Lu's annotation library
- [Automatic Label Placement](https://en.wikipedia.org/wiki/Automatic_label_placement) — computational geometry approaches
- [D3 Voronoi Labels](https://observablehq.com/@d3/voronoi-labels) — Voronoi-based label placement
- [Force-Directed Label Placement](https://observablehq.com/@d3/force-directed-labels) — using simulation for labels
