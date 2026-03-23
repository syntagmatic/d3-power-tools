---
name: annotations-and-labels
description: "Build annotations, callouts, leader lines, and responsive labels for D3.js visualizations. Use this skill when the user needs to add explanatory text, callouts with connector lines, responsive label placement, collision-free labeling, or rich tooltips to charts. Covers d3-annotation patterns, custom callout shapes, leader lines, force-based label placement, and responsive strategies."
---

# Annotations and Labels

Patterns for adding explanatory text, callouts, leader lines, and labels to D3 visualizations. Covers annotation types, leader line routing, label collision avoidance, responsive strategies, rich tooltips, the d3-annotation library, building annotations from scratch, and Canvas annotations.

For axis labels and tick formatting, see `axes-and-scales`. For color legends, see `color-and-compositing`. For accessible text alternatives, see `canvas-accessibility`.

## Annotation Types

### Callout with Leader Line

The most common annotation: text connected to a data point by a line. Three parts: **subject** (the data point), **connector** (the leader line), and **note** (the text block).

```js
// Manual callout — full control, no library needed
const annotation = svg.append("g")
  .attr("class", "annotation")
  .attr("transform", `translate(${x},${y})`);

// Subject marker
annotation.append("circle")
  .attr("r", 5)
  .attr("fill", "none")
  .attr("stroke", "#e15759");

// Leader line (elbow connector)
const noteX = 60, noteY = -40;
annotation.append("path")
  .attr("d", `M0,0 L${noteX},0 L${noteX},${noteY}`)
  .attr("fill", "none")
  .attr("stroke", "#999")
  .attr("stroke-width", 1);

// Note text
annotation.append("text")
  .attr("x", noteX)
  .attr("y", noteY - 4)
  .attr("text-anchor", "middle")
  .text("Peak value: 42");
```

### Badge / Circle Annotation

A numbered or labeled circle overlay, used for step-by-step callouts:

```js
const badge = svg.append("g")
  .attr("transform", `translate(${x},${y})`);

badge.append("circle")
  .attr("r", 12)
  .attr("fill", "#4e79a7");

badge.append("text")
  .attr("text-anchor", "middle")
  .attr("dy", "0.35em")
  .attr("fill", "white")
  .attr("font-size", "11px")
  .attr("font-weight", "bold")
  .text("1");
```

### Bracket Annotation

Spans a range on an axis, useful for highlighting periods or groups:

```js
function drawBracket(svg, x1, x2, y, height, label) {
  const g = svg.append("g").attr("class", "bracket-annotation");
  const bracketY = y - height;

  // Bracket shape: vertical ticks at ends connected by horizontal bar
  g.append("path")
    .attr("d", `M${x1},${y} L${x1},${bracketY} L${x2},${bracketY} L${x2},${y}`)
    .attr("fill", "none")
    .attr("stroke", "#666")
    .attr("stroke-width", 1.5);

  g.append("text")
    .attr("x", (x1 + x2) / 2)
    .attr("y", bracketY - 6)
    .attr("text-anchor", "middle")
    .attr("font-size", "12px")
    .text(label);
}
```

### Threshold / Reference Line

Horizontal or vertical line across the chart with a label:

```js
function addThresholdLine(svg, yScale, value, width, label, color = "#e15759") {
  const y = yScale(value);
  const g = svg.append("g").attr("class", "threshold");

  g.append("line")
    .attr("x1", 0).attr("x2", width)
    .attr("y1", y).attr("y2", y)
    .attr("stroke", color)
    .attr("stroke-width", 1.5)
    .attr("stroke-dasharray", "6,3");

  g.append("text")
    .attr("x", width - 4)
    .attr("y", y - 6)
    .attr("text-anchor", "end")
    .attr("fill", color)
    .attr("font-size", "12px")
    .attr("font-weight", 600)
    .text(label);
}
```

### Text-Only Annotation

Free-floating text placed directly on the chart, no connector:

```js
svg.append("text")
  .attr("x", xScale(targetDate))
  .attr("y", yScale(targetValue) - 12)
  .attr("text-anchor", "middle")
  .attr("font-size", "13px")
  .attr("fill", "#555")
  .text("Policy change");
```

For multi-line text, use `<tspan>`:

```js
const text = svg.append("text")
  .attr("x", x).attr("y", y);

["Line one", "Line two"].forEach((line, i) => {
  text.append("tspan")
    .attr("x", x)
    .attr("dy", i === 0 ? 0 : "1.2em")
    .text(line);
});
```

## Leader Lines

### Straight Line

Simplest connector. Works when there's no clutter between subject and note.

```js
// From data point to label
annotation.append("line")
  .attr("x1", 0).attr("y1", 0)
  .attr("x2", dx).attr("y2", dy)
  .attr("stroke", "#999")
  .attr("stroke-width", 1);
```

### Elbow (Rectilinear)

A horizontal-then-vertical (or vice versa) path. Clean, professional look:

```js
// Horizontal first, then vertical
const elbowPath = (dx, dy) => `M0,0 L${dx},0 L${dx},${dy}`;

// Vertical first, then horizontal
const elbowPathV = (dx, dy) => `M0,0 L0,${dy} L${dx},${dy}`;
```

### Curved (Quadratic Bezier)

Smooth arc from subject to note. Control point determines curvature:

```js
// Quadratic bezier — control point at (dx, 0) for horizontal departure
const curvedPath = (dx, dy) => `M0,0 Q${dx},0 ${dx},${dy}`;

// S-curve with cubic bezier for more complex routing
const sCurve = (dx, dy) => `M0,0 C${dx * 0.5},0 ${dx * 0.5},${dy} ${dx},${dy}`;
```

### Avoiding Other Elements

When leader lines cross data points, route around them. Two strategies:

**Offset approach** — move the control point away from dense areas:

```js
const avoidanceOffset = 30; // push control point away from data
const cpX = dx > 0 ? dx * 0.3 : dx * 0.3;
const cpY = dy > 0 ? -avoidanceOffset : avoidanceOffset;
const path = `M0,0 Q${cpX},${cpY} ${dx},${dy}`;
```

**Two-segment with intermediate point:**

```js
// Route through a waypoint that avoids the cluster
const midX = dx * 0.5, midY = dy - 30;
const path = `M0,0 L${midX},${midY} L${dx},${dy}`;
```

## Label Collision Avoidance

### Force-Simulation Approach

Best for scatterplots with many labels. Create a secondary simulation that positions labels near their data points while preventing overlap:

```js
function forceLabels(data, xScale, yScale, { width, height, fontSize = 12, padding = 2 } = {}) {
  // Create label nodes with target positions
  const labelNodes = data.map(d => ({
    ...d,
    targetX: xScale(d.x),
    targetY: yScale(d.y),
    x: xScale(d.x),
    y: yScale(d.y),
  }));

  // Estimate label dimensions (width depends on text length)
  labelNodes.forEach(d => {
    d.labelWidth = d.label.length * fontSize * 0.6 + padding * 2;
    d.labelHeight = fontSize + padding * 2;
  });

  // Run simulation to resolve overlaps
  const simulation = d3.forceSimulation(labelNodes)
    .force("x", d3.forceX(d => d.targetX).strength(0.5))
    .force("y", d3.forceY(d => d.targetY).strength(0.5))
    .force("collide", rectCollideForce(d => [d.labelWidth, d.labelHeight]))
    .force("bounds", boundingBoxForce(0, 0, width, height))
    .stop();

  // Pre-compute (no animation needed for labels)
  for (let i = 0; i < 120; i++) simulation.tick();

  return labelNodes;
}
```

### Rectangular Collision Force

Standard `forceCollide` is circular. For text labels, use rectangular collision:

```js
function rectCollideForce(sizeFn, padding = 2) {
  let nodes;
  function force(alpha) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const [aw, ah] = sizeFn(a);
        const [bw, bh] = sizeFn(b);

        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const overlapX = (aw + bw) / 2 + padding - Math.abs(dx);
        const overlapY = (ah + bh) / 2 + padding - Math.abs(dy);

        if (overlapX > 0 && overlapY > 0) {
          // Push apart along the axis of least overlap
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

### Greedy Algorithm

Simpler approach: try placement positions in priority order for each label:

```js
function greedyLabels(data, xScale, yScale, { fontSize = 12, padding = 4 } = {}) {
  const placed = []; // bounding boxes of placed labels

  // 8 candidate positions: right, upper-right, above, upper-left, left, lower-left, below, lower-right
  const offsets = [
    [10, 0], [10, -10], [0, -14], [-10, -10],
    [-10, 0], [-10, 10], [0, 14], [10, 10],
  ];

  return data.map(d => {
    const px = xScale(d.x), py = yScale(d.y);
    const w = d.label.length * fontSize * 0.6;
    const h = fontSize;

    for (const [ox, oy] of offsets) {
      const box = { x: px + ox, y: py + oy - h, width: w, height: h };
      if (!placed.some(p => boxesOverlap(p, box))) {
        placed.push(box);
        return { ...d, labelX: box.x, labelY: py + oy, anchor: ox < 0 ? "end" : "start" };
      }
    }
    // Fallback: place at default position
    return { ...d, labelX: px + 10, labelY: py, anchor: "start" };
  });
}

function boxesOverlap(a, b) {
  return a.x < b.x + b.width && a.x + a.width > b.x &&
         a.y < b.y + b.height && a.y + a.height > b.y;
}
```

### Voronoi-Based Label Placement

Use Voronoi cells to find the nearest empty space for each label:

```js
const delaunay = d3.Delaunay.from(data, d => xScale(d.x), d => yScale(d.y));
const voronoi = delaunay.voronoi([0, 0, width, height]);

data.forEach((d, i) => {
  const cell = voronoi.cellPolygon(i);
  if (!cell) return;
  // Place label at centroid of Voronoi cell
  const cx = d3.mean(cell, p => p[0]);
  const cy = d3.mean(cell, p => p[1]);
  d.labelX = cx;
  d.labelY = cy;
});
```

## Responsive Labels

### Hiding at Breakpoints

Remove or thin labels when the chart shrinks:

```js
function updateLabels(width) {
  labels.style("display", (d, i) => {
    if (width < 400) return i % 3 === 0 ? null : "none"; // show every 3rd
    if (width < 600) return i % 2 === 0 ? null : "none"; // show every 2nd
    return null; // show all
  });
}
```

### Abbreviating Text

```js
function responsiveLabel(d, width) {
  if (width < 400) return d.abbrev || d.label.slice(0, 3);
  if (width < 600) return d.shortLabel || d.label.slice(0, 8);
  return d.label;
}
```

### Repositioning

Move annotations to avoid clipping when the container shrinks:

```js
function repositionAnnotations(width, height) {
  annotations.forEach(a => {
    // Flip annotation to left side if it would overflow right edge
    if (a.targetX + a.dx + a.noteWidth > width) {
      a.dx = -Math.abs(a.dx) - a.noteWidth;
    }
    // Move above if it would overflow bottom
    if (a.targetY + a.dy + a.noteHeight > height) {
      a.dy = -Math.abs(a.dy) - a.noteHeight;
    }
  });
}
```

### Font-Size Scaling

Scale annotation text proportionally to chart width:

```js
const baseFontSize = 13;
const scaledFontSize = Math.max(10, Math.min(14, baseFontSize * (width / 800)));
annotationText.attr("font-size", `${scaledFontSize}px`);
```

### ResizeObserver Pattern

```js
const ro = new ResizeObserver(entries => {
  const { width, height } = entries[0].contentRect;
  // Rebuild scales, re-place labels, reposition annotations
  updateChart(width, height);
});
ro.observe(container.node());
```

## Rich Tooltips

### Follow-Cursor Tooltip

```js
const tooltip = d3.select("body").append("div")
  .attr("class", "tooltip")
  .style("position", "absolute")
  .style("pointer-events", "none")
  .style("opacity", 0);

selection.on("pointerenter", (event, d) => {
  tooltip
    .html(`<strong>${d.label}</strong><br/>Value: ${d.value}`)
    .style("opacity", 1);
})
.on("pointermove", (event) => {
  const [mx, my] = [event.pageX, event.pageY];
  // Flip tooltip to avoid viewport edges
  const ttWidth = tooltip.node().offsetWidth;
  const ttHeight = tooltip.node().offsetHeight;
  const left = mx + 15 + ttWidth > window.innerWidth ? mx - ttWidth - 10 : mx + 15;
  const top = my - ttHeight - 10 < 0 ? my + 15 : my - ttHeight - 10;
  tooltip.style("left", `${left}px`).style("top", `${top}px`);
})
.on("pointerleave", () => {
  tooltip.style("opacity", 0);
});
```

### Pinned Tooltip

Click to pin a tooltip in place; click again or elsewhere to dismiss:

```js
let pinnedTooltip = null;

selection.on("click", (event, d) => {
  event.stopPropagation();
  if (pinnedTooltip === d) {
    pinnedTooltip = null;
    tooltip.style("opacity", 0);
    return;
  }
  pinnedTooltip = d;
  tooltip
    .html(`<strong>${d.label}</strong><br/>Value: ${d.value}`)
    .style("opacity", 1)
    .style("pointer-events", "auto") // allow interaction with pinned tooltip
    .style("left", `${event.pageX + 15}px`)
    .style("top", `${event.pageY - 10}px`);
});

d3.select("body").on("click", () => {
  pinnedTooltip = null;
  tooltip.style("opacity", 0).style("pointer-events", "none");
});
```

### Edge-Aware Positioning

```js
function positionTooltip(tooltip, event, margin = 10) {
  const node = tooltip.node();
  const rect = node.getBoundingClientRect();
  const vw = window.innerWidth, vh = window.innerHeight;
  let left = event.pageX + margin;
  let top = event.pageY - rect.height - margin;

  if (left + rect.width > vw) left = event.pageX - rect.width - margin;
  if (top < 0) top = event.pageY + margin;
  if (left < 0) left = margin;

  tooltip.style("left", `${left}px`).style("top", `${top}px`);
}
```

## d3-annotation Library

[d3-annotation](https://d3-annotation.susielu.com/) by Susie Lu provides declarative annotations. Good for quick setups; build from scratch when you need full control.

```html
<script src="https://cdn.jsdelivr.net/npm/d3-svg-annotation@2"></script>
```

```js
const annotations = [
  {
    note: { label: "Peak revenue", title: "Q3 2024", wrap: 150 },
    x: xScale(peakDate), y: yScale(peakValue),
    dx: 50, dy: -30,
    type: d3.annotationCalloutElbow,
  },
  {
    note: { label: "Below target threshold" },
    type: d3.annotationXYThreshold,
    y: yScale(threshold),
    subject: { x1: 0, x2: width },
  },
];

const makeAnnotations = d3.annotation()
  .type(d3.annotationLabel)
  .annotations(annotations);

svg.append("g")
  .attr("class", "annotation-group")
  .call(makeAnnotations);
```

### Available Types

- `annotationLabel` — text only, no connector
- `annotationCallout` — line connector
- `annotationCalloutElbow` — rectilinear connector
- `annotationCalloutCurve` — curved connector
- `annotationCalloutCircle` — circle subject with connector
- `annotationXYThreshold` — threshold line
- `annotationBadge` — numbered badge

### Styling d3-annotation

```css
.annotation path { stroke: #666; fill: none; }
.annotation text { fill: #333; font-size: 12px; }
.annotation .annotation-note-bg { fill: white; opacity: 0.85; }
.annotation-note-title { font-weight: 600; }
```

## Building Annotations from Scratch

When d3-annotation is too heavy or you need custom behavior, build with plain D3:

### Reusable Annotation Component

```js
function createAnnotation(svg, {
  x, y,            // subject position (data point)
  dx, dy,          // offset to note
  title = "",
  text = "",
  connector = "elbow",  // "straight" | "elbow" | "curve"
  color = "#666",
  fontSize = 12,
  wrap = 150,
}) {
  const g = svg.append("g")
    .attr("class", "annotation")
    .attr("transform", `translate(${x},${y})`);

  // Subject dot
  g.append("circle")
    .attr("r", 4)
    .attr("fill", "none")
    .attr("stroke", color)
    .attr("stroke-width", 1.5);

  // Connector path
  let pathD;
  if (connector === "straight") pathD = `M0,0 L${dx},${dy}`;
  else if (connector === "elbow") pathD = `M0,0 L${dx},0 L${dx},${dy}`;
  else pathD = `M0,0 Q${dx},0 ${dx},${dy}`;

  g.append("path")
    .attr("d", pathD)
    .attr("fill", "none")
    .attr("stroke", color)
    .attr("stroke-width", 1);

  // Note
  const note = g.append("g")
    .attr("transform", `translate(${dx},${dy})`);

  if (title) {
    note.append("text")
      .attr("font-size", `${fontSize}px`)
      .attr("font-weight", 600)
      .attr("fill", "#333")
      .attr("dy", "-0.3em")
      .text(title);
  }

  if (text) {
    note.append("text")
      .attr("font-size", `${fontSize - 1}px`)
      .attr("fill", "#666")
      .attr("dy", title ? "1em" : "0")
      .text(text);
  }

  return g;
}
```

### Annotation Layer Pattern

Keep annotations in a dedicated `<g>` layer above the data but below tooltips:

```js
// Layer ordering matters
const dataLayer = svg.append("g").attr("class", "data-layer");
const axisLayer = svg.append("g").attr("class", "axis-layer");
const annotationLayer = svg.append("g").attr("class", "annotation-layer");
// Tooltips are HTML divs on top of everything
```

### Wrapping Long Text

SVG text doesn't wrap. Manually split into `<tspan>` elements:

```js
function wrapText(textSelection, maxWidth) {
  textSelection.each(function () {
    const text = d3.select(this);
    const words = text.text().split(/\s+/).reverse();
    const lineHeight = 1.2; // em
    const x = text.attr("x") || 0;
    const dy = parseFloat(text.attr("dy")) || 0;
    let line = [], lineNumber = 0, tspan = text.text(null)
      .append("tspan").attr("x", x).attr("dy", `${dy}em`);

    let word;
    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > maxWidth && line.length > 1) {
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        tspan = text.append("tspan")
          .attr("x", x)
          .attr("dy", `${lineHeight}em`)
          .text(word);
        lineNumber++;
      }
    }
  });
}
```

## Canvas Annotations

When the chart uses Canvas rendering, draw annotations on the canvas context or use a hybrid approach with an SVG overlay.

### Canvas Callout

```js
function drawCallout(ctx, { x, y, dx, dy, title, text, color = "#666" }) {
  ctx.save();

  // Connector line
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + dx, y);
  ctx.lineTo(x + dx, y + dy);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.stroke();

  // Subject circle
  ctx.beginPath();
  ctx.arc(x, y, 4, 0, 2 * Math.PI);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Note text
  ctx.font = "bold 12px sans-serif";
  ctx.fillStyle = "#333";
  ctx.textAlign = dx > 0 ? "start" : "end";
  if (title) ctx.fillText(title, x + dx + (dx > 0 ? 4 : -4), y + dy - 4);

  ctx.font = "11px sans-serif";
  ctx.fillStyle = "#666";
  if (text) ctx.fillText(text, x + dx + (dx > 0 ? 4 : -4), y + dy + 12);

  ctx.restore();
}
```

### Canvas Threshold Line

```js
function drawThreshold(ctx, { y, width, label, color = "#e15759" }) {
  ctx.save();
  ctx.setLineDash([6, 3]);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(width, y);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.font = "bold 12px sans-serif";
  ctx.fillStyle = color;
  ctx.textAlign = "end";
  ctx.fillText(label, width - 4, y - 6);
  ctx.restore();
}
```

### Hybrid: Canvas Data + SVG Annotations

Best of both worlds — canvas for performance, SVG for crisp text and interactivity:

```js
// Canvas layer for data
const canvas = d3.select(container).append("canvas")
  .style("position", "absolute");

// SVG layer for annotations (on top)
const svg = d3.select(container).append("svg")
  .style("position", "absolute")
  .style("pointer-events", "none"); // let clicks pass through to canvas

// Annotation elements in SVG get crisp rendering and CSS styling
const annotationLayer = svg.append("g").attr("class", "annotations");
```

## Common Pitfalls

**Labels overflow the chart bounds.** Always clamp label positions to the plot area. With force-based placement, add a bounding box force. With greedy placement, check bounds before accepting a position.

**Leader lines cross other labels.** This is hard to solve perfectly. Force-based layout naturally minimizes crossings. For manual annotations, route leader lines around obstacles using intermediate waypoints.

**Text not visible on dark backgrounds.** Add a semi-transparent background rect behind annotation text:
```js
// Measure text, then insert rect before the text node
const bbox = textNode.getBBox();
g.insert("rect", "text")
  .attr("x", bbox.x - 2).attr("y", bbox.y - 1)
  .attr("width", bbox.width + 4).attr("height", bbox.height + 2)
  .attr("fill", "white").attr("opacity", 0.85);
```

**SVG text doesn't wrap.** SVG has no automatic line wrapping. You must split text into `<tspan>` elements manually. Use the `wrapText` helper above, or pre-split at a known character limit.

**Annotations disappear on resize.** Annotations with hardcoded pixel positions break when the chart resizes. Store annotations in data coordinates and re-compute pixel positions in the resize handler.

**Too many annotations clutter the chart.** Less is more. Annotate 3-5 key insights, not every data point. For dense data, use tooltips for detail-on-demand and annotations only for the narrative.

**Annotation z-order wrong.** Annotations should render above data but below tooltips. SVG renders in document order, so append annotation `<g>` after data elements. For canvas, draw annotations after data in the render loop.

**getComputedTextLength() returns 0.** This happens when the text element isn't in the DOM yet. Ensure the element is appended to the SVG before measuring. Use `requestAnimationFrame` if needed.

**Canvas text looks blurry.** Canvas text rendering depends on the device pixel ratio. Scale the canvas for retina:
```js
const dpr = window.devicePixelRatio || 1;
canvas.width = width * dpr;
canvas.height = height * dpr;
ctx.scale(dpr, dpr);
```

**Force-based labels oscillate forever.** Increase `velocityDecay` (e.g., 0.6) and reduce iteration count. For label placement, pre-compute with `simulation.stop(); simulation.tick(120);` rather than animating.

## References

- [d3-annotation](https://d3-annotation.susielu.com/) — Susie Lu's annotation library
- [Labeling and Annotation Best Practices](https://www.visualisingdata.com/2015/01/make-grey-best-colour/) — Andy Kirk on annotation hierarchy
- [Automatic Label Placement](https://en.wikipedia.org/wiki/Automatic_label_placement) — computational geometry approaches
- [D3 Voronoi Labels](https://observablehq.com/@d3/voronoi-labels) — Voronoi-based label placement
- [Force-Directed Label Placement](https://observablehq.com/@d3/force-directed-labels) — using simulation for labels
