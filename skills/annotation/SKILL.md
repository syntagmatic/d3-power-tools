---
name: annotation
description: "Build annotations, callouts, leader lines, and responsive labels for D3.js visualizations. Use this skill when the user needs to add explanatory text, callouts with connector lines, responsive label placement, collision-free labeling, or rich tooltips to charts. Covers d3-annotation patterns, custom callout shapes, leader lines, force-based label placement, and responsive strategies."
---

# Annotations and Labels

A chart without annotation is a chart without an argument. Annotation tells the viewer what to look at, why it matters, and what they might otherwise miss.

For axis labels and tick formatting, see `scales`. For color legends, see `color`. For accessible text alternatives, see `canvas-accessibility`.

## Editorial Judgment: What to Annotate

Every annotation competes for attention with the data. Over-annotate and the viewer reads your notes instead of the chart.

**Hierarchy of emphasis** (most to least prominent):

1. **Callout annotations** with leader lines -- the 1-3 claims that justify the chart. "So what?"
2. **Threshold / reference lines** -- context for interpretation (targets, averages, limits). "Compared to what?"
3. **Direct labels** on data points -- when identity matters (named countries, outliers). "Which one?"
4. **Tooltips** -- detail-on-demand for everything else.

**The 3-annotation rule.** More than 3 callouts means you have a list, not a story. The eye holds one primary and two supporting; beyond that, nothing is emphasized.

**Annotate the surprising, not the obvious.** Good candidates: inflection points, anomalies, crossovers, first/last in a sequence, values that contradict expectations.

**When not to annotate.** Exploratory dashboards (use tooltips and brushing instead) or small-multiples grids (the pattern across panels is the insight).

**Highlight by desaturation.** Make everything else quieter instead of making the annotated element louder:

```js
selection
    .attr("fill", d => annotatedIds.has(d.id) ? color(d.category) : "#ccc")
    .attr("opacity", d => annotatedIds.has(d.id) ? 1 : 0.3);
```

**Text hierarchy.** Five levels: (1) headline states the finding, (2) subtitle gives scope, (3) 1-3 inline callouts, (4) axis labels, (5) source line. Each progressively smaller and lighter.

## Leader Line Geometry

Four connector types -- straight for sparse charts, elbow when the note sits beside the point, quadratic curve and S-curve when routing around data:

```js
const straight = (dx, dy) => `M0,0 L${dx},${dy}`,
      elbow    = (dx, dy) => `M0,0 L${dx},0 L${dx},${dy}`,
      curve    = (dx, dy) => `M0,0 Q${dx},0 ${dx},${dy}`,
      sCurve   = (dx, dy) => `M0,0 C${dx*0.5},0 ${dx*0.5},${dy} ${dx},${dy}`;
```

Push control points away from dense areas: `M0,0 Q${dx*0.3},${cpY} ${dx},${dy}` where `cpY` flips sign opposite to `dy`. Lines should be quieter than data -- thin (0.7-1px), muted color, no arrowheads unless direction matters.

## Label Collision Avoidance

### Force-Simulation Approach

`forceCollide` is circular but text is rectangular -- use a custom rectangular collision force:

```js
function rectCollideForce(sizeFn, padding = 2) {
  let nodes;
  function force(alpha) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j],
              [aw, ah] = sizeFn(a), [bw, bh] = sizeFn(b),
              dx = b.x - a.x, dy = b.y - a.y,
              overlapX = (aw + bw) / 2 + padding - Math.abs(dx),
              overlapY = (ah + bh) / 2 + padding - Math.abs(dy);
        if (overlapX > 0 && overlapY > 0) {
          const axis = overlapX < overlapY ? "x" : "y",
                overlap = axis === "x" ? overlapX : overlapY,
                sign = axis === "x" ? Math.sign(dx) : Math.sign(dy),
                shift = overlap * alpha * 0.5;
          a[axis] -= sign * shift;
          b[axis] += sign * shift;
        }
      }
    }
  }
  force.initialize = (_nodes) => { nodes = _nodes; };
  return force;
}
```

Pre-compute (no animation): `simulation.stop(); for (let i = 0; i < 120; i++) simulation.tick();`

Estimate label width without DOM: `d.label.length * fontSize * 0.6`.

### Greedy Algorithm

Try 8 positions around each point, accept first non-overlapping slot. O(n) vs O(n^2) for force, but worse in dense plots:

```js
function greedyLabels(data, xScale, yScale, { fontSize = 12 } = {}) {
  const placed = [], offsets = [
    [10,0],[10,-10],[0,-14],[-10,-10],[-10,0],[-10,10],[0,14],[10,10]];
  return data.map(d => {
    const px = xScale(d.x), py = yScale(d.y),
          w = d.label.length * fontSize * 0.6, h = fontSize;
    for (const [ox, oy] of offsets) {
      const box = { x: px+ox, y: py+oy-h, width: w, height: h };
      if (!placed.some(p => p.x < box.x+box.width && p.x+p.width > box.x
                         && p.y < box.y+box.height && p.y+p.height > box.y)) {
        placed.push(box);
        return { ...d, labelX: box.x, labelY: py+oy, anchor: ox < 0 ? "end" : "start" };
      }
    }
    return { ...d, labelX: px+10, labelY: py, anchor: "start" };
  });
}
```

### Voronoi-Based Placement

Labels at Voronoi cell centroids. Works for evenly distributed points; degrades with tight clusters:

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

Store in **data coordinates**, re-compute pixels on resize. Flip when they overflow:

```js
annotations.forEach(a => {
  if (a.targetX + a.dx + a.noteWidth > width) a.dx = -Math.abs(a.dx) - a.noteWidth;
  if (a.targetY + a.dy + a.noteHeight > height) a.dy = -Math.abs(a.dy) - a.noteHeight;
});
```

Thin labels at breakpoints -- show every Nth label on narrow screens, keep annotated outliers:

```js
labels.style("display", (d, i) =>
  width < 400 ? (i % 3 === 0 ? null : "none") :
  width < 600 ? (i % 2 === 0 ? null : "none") : null);
```

## Annotation as Data

Treat annotations as structured data, not ad-hoc SVG:

```js
const annotations = [
  { id: "pandemic", x: "2020-03-11", y: 142000, dx: -80, dy: -40,
    title: "Pandemic declared", body: "WHO declaration preceded sharpest weekly rise.",
    priority: 1, connector: "curve" },
  { id: "vaccine", x: "2021-01-04", y: 98000, dx: 60, dy: -30,
    title: "Vaccine rollout", body: "First doses administered.",
    priority: 2, connector: "elbow" },
];
```

This buys: **priority filtering** (show only `priority <= 1` at narrow widths), **separation of concerns** (editors modify text without touching code), and **data-coordinate binding** (survives rescaling). Render with `.data().join()`.

**d3-annotation library.** Susie Lu's [d3-annotation](https://d3-annotation.susielu.com/) (v2.5.1, unmaintained since 2019) -- subject+connector+note architecture with built-in types and `editMode(true)`. Use for 3+ richly styled callouts or non-D3 teams. Hand-roll for Canvas, custom connectors, or full lifecycle control.

## SVG Text Wrapping

SVG has no line wrapping. Split into `<tspan>` elements:

```js
function wrapText(textSel, maxWidth) {
  textSel.each(function () {
    const text = d3.select(this),
          words = text.text().split(/\s+/).reverse(),
          x = text.attr("x") || 0;
    let line = [], tspan = text.text(null)
      .append("tspan").attr("x", x).attr("dy", `${parseFloat(text.attr("dy")) || 0}em`);
    let word;
    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > maxWidth && line.length > 1) {
        line.pop(); tspan.text(line.join(" "));
        line = [word];
        tspan = text.append("tspan").attr("x", x).attr("dy", "1.2em").text(word);
      }
    }
  });
}
```

`getComputedTextLength()` returns 0 if not yet in the DOM -- append first, then measure.

## Canvas Annotations

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

**Hybrid Canvas+SVG.** Canvas for data, SVG overlay for crisp annotation text. See `canvas` skill for the layer stack. Set `pointer-events: none` on SVG so clicks pass through.

**Layer ordering.** Annotations in a `<g>` above data but below tooltips -- SVG renders in document order.

## Tooltip Patterns

Detail-on-demand -- never duplicate what a callout already says. Use HTML over SVG `<title>` for rich formatting.

### Core Pattern with Edge Clamping

```js
const tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("position", "absolute").style("pointer-events", "none").style("opacity", 0);

selection
    .on("pointerenter", (event, d) => {
      tooltip.html(`<strong>${d.name}</strong><br>${d.value}`).style("opacity", 1);
    })
    .on("pointermove", (event) => {
      const tw = tooltip.node().offsetWidth, th = tooltip.node().offsetHeight,
            x = Math.min(event.pageX + 12, window.innerWidth + window.scrollX - tw - 8),
            y = Math.max(event.pageY - th - 8, window.scrollY + 8);
      tooltip.style("left", `${x}px`).style("top", `${y}px`);
    })
    .on("pointerleave", () => tooltip.style("opacity", 0));
```

### Voronoi Tooltip

For small/dense elements, attach tooltip to a Voronoi overlay. Position at the data point (not mouse) for a stable target:

```js
const delaunay = d3.Delaunay.from(data, d => x(d.date), d => y(d.value));
svg.append("rect").attr("width", width).attr("height", height)
    .attr("fill", "none").attr("pointer-events", "all")
    .on("pointermove", (event) => {
      const [mx, my] = d3.pointer(event);
      const i = delaunay.find(mx, my), d = data[i];
      tooltip.html(`${d.name}: ${d.value}`)
          .style("left", `${x(d.date) + margin.left + 12}px`)
          .style("top", `${y(d.value) + margin.top - 12}px`).style("opacity", 1);
    })
    .on("pointerleave", () => tooltip.style("opacity", 0));
```

## Step-Sequenced Annotations

Reveal annotations one at a time on scroll. Map step indices to annotation objects, clear previous on step enter. Wire with [Scrollama](https://github.com/russellsamora/scrollama) or `position: sticky` + IntersectionObserver. For scrollytelling layout, see `motion`.

```js
const stepAnnotations = [
  null,
  { x: "2020-03-11", y: 142000, dx: -80, dy: -40,
    title: "Pandemic declared", body: "Sharpest weekly increase followed." },
  { x: "2021-01-04", y: 98000, dx: 60, dy: -30,
    title: "Vaccines begin", body: "Recovery trend starts here." },
];
function onStepEnter(i) {
  annotationLayer.selectAll(".callout").remove();
  if (stepAnnotations[i]) renderCallout(annotationLayer, stepAnnotations[i], xScale, yScale);
}
```

| Sequence annotations when... | Show all at once when... |
|---|---|
| The story has temporal or causal order | The chart makes one or two claims |
| Multiple callouts would clutter a single view | The audience is expert and scans quickly |
| The audience is general public (news, reports) | The chart is one panel in a dashboard or grid |

## Choosing an Annotation Approach

```
Sequence over scroll? --> Step-sequenced + Scrollama / IntersectionObserver
3+ richly styled callouts? --> d3-annotation or annotation-as-data
Few callouts, SVG? --> Hand-rolled text + leader line
Canvas? --> Canvas callouts (see above)
Non-developer editing? --> Annotation-as-data (JSON alongside dataset)
```

## Common Pitfalls

**Too many annotations.** Perceptual research: blur/focus emphasis perceived fastest (~830ms), then size (~910ms), then color (~1240ms). Callouts work by contrast. Keep to 3; tooltips for the rest.

**Labels overflow bounds.** Force-based: add bounding box force. Greedy: check bounds before accepting.

**Text invisible on varied backgrounds.** Add a background rect:
```js
const bbox = textNode.getBBox();
g.insert("rect", "text")
  .attr("x", bbox.x - 2).attr("y", bbox.y - 1)
  .attr("width", bbox.width + 4).attr("height", bbox.height + 2)
  .attr("fill", "white").attr("opacity", 0.85);
```

**Annotations disappear on resize.** Store in data coordinates, re-compute pixels in resize handler.

**Force labels oscillate.** Increase `velocityDecay` (0.6). Pre-compute: `simulation.stop(); simulation.tick(120);`.

**Canvas text blurry.** See `canvas` skill for DPR/retina setup.

## References

- [d3-annotation](https://d3-annotation.susielu.com/) -- Susie Lu's annotation library (subject+connector+note architecture)
- [Making Annotations First-Class Citizens](https://medium.com/@Elijah_Meeks/making-annotations-first-class-citizens-in-data-visualization-21db6383d3fe) -- Elijah Meeks on annotation as data
- [Scrollama](https://github.com/russellsamora/scrollama) -- IntersectionObserver-based scrollytelling
- [Automatic Label Placement](https://en.wikipedia.org/wiki/Automatic_label_placement) -- computational geometry approaches
- [D3 Voronoi Labels](https://observablehq.com/@d3/voronoi-labels) -- Voronoi-based label placement
- [Emphasis Techniques in Visualization](https://pmc.ncbi.nlm.nih.gov/articles/PMC8841630/) -- perceptual research on visual prominence
