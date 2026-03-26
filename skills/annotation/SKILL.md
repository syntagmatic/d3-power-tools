---
name: annotation
description: "Build annotations, callouts, leader lines, and responsive labels for D3.js visualizations. Use this skill when the user needs to add explanatory text, callouts with connector lines, responsive label placement, collision-free labeling, or rich tooltips to charts. Covers d3-annotation patterns, custom callout shapes, leader lines, force-based label placement, and responsive strategies."
---

# Annotations and Labels

A chart without annotation is a chart without an argument. Annotation converts a picture of data into a claim about the world -- it tells the viewer what to look at, why it matters, and what they might otherwise miss.

For axis labels and tick formatting, see `axes-and-scales`. For color legends, see `color`. For accessible text alternatives, see `canvas-accessibility`.

## Editorial Judgment: What to Annotate

The hardest part of annotation is not geometry -- it is deciding what deserves a callout. Every annotation competes for attention with the data itself. Over-annotate and the viewer reads your notes instead of the chart. Under-annotate and they leave without the insight you intended.

**Hierarchy of emphasis** (most to least prominent):

1. **Callout annotations** with leader lines -- reserve for the 1-3 claims that justify the chart's existence. These answer "so what?"
2. **Threshold / reference lines** -- encode context the viewer needs to interpret the data (targets, averages, regulatory limits). These answer "compared to what?"
3. **Direct labels** on data points -- use when identity matters (named countries, companies, outliers). These answer "which one?"
4. **Tooltips** -- detail-on-demand for everything else. The viewer chooses what to inspect.

**The 3-annotation rule.** If you have more than 3 callout annotations, you don't have a story -- you have a list. Demote the weaker ones to direct labels or tooltips. The eye can hold one primary and two supporting callouts; beyond that, nothing is emphasized because everything is.

**Annotate the surprising, not the obvious.** A callout on the highest bar in a sorted bar chart wastes ink. A callout on the bar that broke a trend earns its space. Good candidates: inflection points, anomalies, crossovers, first/last in a sequence, values that contradict expectations.

**When not to annotate.** Exploratory dashboards where the user defines their own questions. Annotation imposes the author's narrative; if the viewer's task is open-ended exploration, use tooltips and brushing instead. Also skip annotation when the chart is one panel in a small-multiples grid -- the pattern across panels *is* the insight.

**Highlight by desaturation.** Instead of making the annotated element louder, make everything else quieter. Gray out non-annotated data so the annotated point pops by being the only colored element. This scales better than adding callout decorations:

```js
selection
    .attr("fill", d => annotatedIds.has(d.id) ? color(d.category) : "#ccc")
    .attr("opacity", d => annotatedIds.has(d.id) ? 1 : 0.3);
```

**Text hierarchy in the chart.** A well-annotated chart has five levels: (1) headline above the chart states the finding, (2) subtitle gives scope or method, (3) 1-3 inline callouts within the chart area, (4) axis labels -- minimal, just enough to read values, (5) source line for provenance. Each level uses progressively smaller, lighter type. If you skip the headline, the viewer must reconstruct your claim from scattered annotations.

## Leader Line Geometry

Three connector types. Straight lines for sparse charts; elbows when the note sits directly above/beside the point; curves when you need to route around nearby data:

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

Leader lines should be visually quieter than the data -- thin (0.7-1px), muted color, no arrowheads unless direction matters. If the line is louder than the data, the annotation is fighting the chart.

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

Try 8 candidate positions around each point in priority order, accept the first non-overlapping slot. Faster than force (O(n) vs O(n^2) per tick) but produces worse results for dense plots:

```js
function greedyLabels(data, xScale, yScale, { fontSize = 12 } = {}) {
  const placed = [];
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

### Voronoi-Based Label Placement

Place labels at Voronoi cell centroids -- guarantees each label is in the nearest open space. Works well when points are evenly distributed; degrades when clusters create tiny cells:

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

Thin labels at breakpoints -- show every Nth label on narrow screens. Prioritize by importance (annotated outliers keep their labels; middle-of-pack points lose theirs first):

```js
function updateLabels(width) {
  labels.style("display", (d, i) => {
    if (width < 400) return i % 3 === 0 ? null : "none";
    if (width < 600) return i % 2 === 0 ? null : "none";
    return null;
  });
}
```

## Annotation as Data

Treat annotations as structured data, not ad-hoc SVG elements hand-positioned in rendering code. Store them in a JSON array alongside your dataset:

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

This buys you three things: **priority filtering** (at narrow widths, show only `priority <= 1`), **separation of concerns** (editors modify annotation text without touching rendering code), and **data-coordinate binding** (annotations survive rescaling because they reference data values, not pixels). Render with a standard `.data().join()` -- annotations are just more data bound to groups with connector paths and note text.

**When to use d3-annotation instead.** Susie Lu's [d3-annotation](https://d3-annotation.susielu.com/) library (as of March 2026, stable at v2.5.1 but unmaintained since 2019) provides a subject+connector+note architecture with built-in types (callout, circle, rect, threshold, badge) and an `editMode(true)` for drag-to-position authoring. Use it when you need 3+ richly styled callouts quickly or when your team includes non-D3 developers. Hand-roll when you need Canvas rendering, custom connector shapes, or full control over the annotation lifecycle.

> **Observable Plot note.** Plot treats annotations as ordinary marks -- `Plot.tip()` for callouts, `Plot.ruleY()` for thresholds, `Plot.text()` with `lineWidth` for auto-wrapping labels. The design principle is sound for D3 too: bind annotations to data, use scales, use enter/update/exit.

## SVG Text Wrapping

SVG has no automatic line wrapping. Split into `<tspan>` elements:

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

Note: `getComputedTextLength()` returns 0 if the element is not yet in the DOM. Append first, then measure.

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

### Hybrid: Canvas Data + SVG Annotations

Canvas for data performance, SVG overlay for crisp annotation text and interactivity. Annotations need subpixel text rendering and easy event binding that Canvas lacks:

```js
const canvas = d3.select(container).append("canvas").style("position", "absolute");
const svg = d3.select(container).append("svg")
  .style("position", "absolute")
  .style("pointer-events", "none"); // clicks pass through to canvas
```

### Layer Ordering

Keep annotations in a dedicated `<g>` above data but below tooltips. SVG renders in document order:

```js
const dataLayer = svg.append("g").attr("class", "data-layer");
const annotationLayer = svg.append("g").attr("class", "annotation-layer");
// Tooltips are HTML divs on top of everything
```

## Tooltip Patterns

Tooltips are detail-on-demand -- they should never duplicate what a callout already says. Use HTML tooltips over SVG `<title>` for rich formatting and viewport-aware positioning.

### Core Pattern

```js
const tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("position", "absolute")
    .style("pointer-events", "none")  // prevents stealing hover
    .style("opacity", 0);

selection
    .on("pointerenter", (event, d) => {
      tooltip.html(`<strong>${d.name}</strong><br>${d.value}`)
          .style("opacity", 1);
    })
    .on("pointermove", (event) => {
      tooltip.style("left", `${event.pageX + 12}px`)  // pageX works in scrollable containers
          .style("top", `${event.pageY - 12}px`);
    })
    .on("pointerleave", () => tooltip.style("opacity", 0));
```

### Edge Clamping

Prevent the tooltip from overflowing the viewport:

```js
.on("pointermove", (event) => {
  const ttNode = tooltip.node();
  const ttW = ttNode.offsetWidth, ttH = ttNode.offsetHeight;
  const x = Math.min(event.pageX + 12, window.innerWidth + window.scrollX - ttW - 8);
  const y = Math.max(event.pageY - ttH - 8, window.scrollY + 8);
  tooltip.style("left", `${x}px`).style("top", `${y}px`);
})
```

### Voronoi Tooltip

When elements are small or dense, attach the tooltip to a Voronoi overlay so the user doesn't need to hover exactly on a 3px point. Position at the data point, not the mouse -- this gives the viewer a stable reading target:

```js
const delaunay = d3.Delaunay.from(data, d => x(d.date), d => y(d.value));

svg.append("rect")
    .attr("width", width).attr("height", height)
    .attr("fill", "none")
    .attr("pointer-events", "all")
    .on("pointermove", (event) => {
      const [mx, my] = d3.pointer(event);
      const i = delaunay.find(mx, my);
      const d = data[i];
      tooltip.html(`${d.name}: ${d.value}`)
          .style("left", `${x(d.date) + margin.left + 12}px`)
          .style("top", `${y(d.value) + margin.top - 12}px`)
          .style("opacity", 1);
    })
    .on("pointerleave", () => tooltip.style("opacity", 0));
```

## Step-Sequenced Annotations

When a chart tells a multi-step story, show annotations one at a time as the reader scrolls rather than cluttering a single view. Each step reveals one insight -- the annotation equivalent of progressive disclosure.

The pattern: a sticky chart with scroll-triggered step handlers. Map each step index to an annotation object (or `null` for no annotation). On step enter, clear previous callouts and render the current one at data coordinates. Wire steps to scroll position with [Scrollama](https://github.com/russellsamora/scrollama) (IntersectionObserver-based, stable as of March 2026) or CSS `position: sticky` with your own IntersectionObserver:

```js
const stepAnnotations = [
  null,  // step 0: base chart, no annotation
  { x: "2020-03-11", y: 142000, dx: -80, dy: -40,
    title: "Pandemic declared", body: "Sharpest weekly increase followed." },
  { x: "2021-01-04", y: 98000, dx: 60, dy: -30,
    title: "Vaccines begin", body: "Recovery trend starts here." },
];

function onStepEnter(stepIndex) {
  annotationLayer.selectAll(".callout").remove();
  const ann = stepAnnotations[stepIndex];
  if (ann) renderAnnotation(ann, xScale, yScale); // reuse your callout renderer
}
```

For the general scrollytelling layout pattern (sticky graphic, step containers, CSS scroll-snap), see `motion`.

**When to sequence vs. show all at once:**

| Sequence annotations when... | Show all at once when... |
|---|---|
| The story has temporal or causal order | The chart makes one or two claims |
| Multiple callouts would clutter a single view | The audience is expert and scans quickly |
| The audience is general public (news, reports) | The chart is one panel in a dashboard or grid |

## Choosing an Annotation Approach

```
Need to sequence annotations over scroll?
  YES → Step-sequenced (above) + Scrollama / IntersectionObserver
  NO ↓

Need 3+ richly styled callouts quickly?
  YES → d3-annotation library or annotation-as-data with full renderer
  NO → Hand-rolled SVG text + leader line

Rendering on Canvas?
  YES → Hand-rolled Canvas callouts (see Canvas Annotations above)
  NO → SVG annotations

Need non-developer editing of annotation text?
  YES → Annotation-as-data pattern (JSON alongside dataset)
  NO → Inline in rendering code is fine
```

## Common Pitfalls

**Too many annotations clutter the chart.** If every point has a callout, none stand out. Research on visual emphasis shows blur/focus is perceived fastest (~830ms), followed by size (~910ms), then color (~1240ms). Callouts work by contrast with unannotated data -- that contrast disappears when everything is annotated. Keep to 3 callouts; use tooltips for the rest.

**Labels overflow the chart bounds.** With force-based placement, add a bounding box force. With greedy placement, check bounds before accepting.

**Text not visible on varied backgrounds.** Add a semi-transparent background rect behind annotation text:
```js
const bbox = textNode.getBBox();
g.insert("rect", "text")
  .attr("x", bbox.x - 2).attr("y", bbox.y - 1)
  .attr("width", bbox.width + 4).attr("height", bbox.height + 2)
  .attr("fill", "white").attr("opacity", 0.85);
```

**Annotations disappear on resize.** Store in data coordinates, re-compute pixel positions in the resize handler.

**Force-based labels oscillate forever.** Increase `velocityDecay` (e.g., 0.6). Pre-compute with `simulation.stop(); simulation.tick(120);` rather than animating.

**Canvas text looks blurry.** Scale canvas for retina: `canvas.width = width * dpr; ctx.scale(dpr, dpr)`.

## References

- [d3-annotation](https://d3-annotation.susielu.com/) -- Susie Lu's annotation library (subject+connector+note architecture)
- [Making Annotations First-Class Citizens](https://medium.com/@Elijah_Meeks/making-annotations-first-class-citizens-in-data-visualization-21db6383d3fe) -- Elijah Meeks on annotation as data visualization of metadata
- [Scrollama](https://github.com/russellsamora/scrollama) -- IntersectionObserver-based scrollytelling
- [Automatic Label Placement](https://en.wikipedia.org/wiki/Automatic_label_placement) -- computational geometry approaches
- [D3 Voronoi Labels](https://observablehq.com/@d3/voronoi-labels) -- Voronoi-based label placement
- [Emphasis Techniques in Visualization](https://pmc.ncbi.nlm.nih.gov/articles/PMC8841630/) -- perceptual research on visual prominence
