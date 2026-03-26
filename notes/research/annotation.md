# Annotation Research

Research into state-of-the-art annotation and storytelling techniques beyond the current skill's coverage.

## Current Coverage

The `skills/annotation/SKILL.md` covers:

- **Editorial judgment** -- what to annotate, the 3-annotation rule, hierarchy of emphasis
- **Leader line geometry** -- straight, elbow, curve, S-curve connectors with avoidance
- **Label collision avoidance** -- force-simulation (rectangular collision), greedy 8-position, Voronoi centroid placement
- **Responsive repositioning** -- data-coordinate storage, edge flipping, label thinning at breakpoints
- **SVG text wrapping** -- tspan-based line breaking with `getComputedTextLength`
- **Canvas annotations** -- callout drawing, hybrid Canvas data + SVG annotation overlay
- **Tooltips** -- HTML tooltips, edge clamping, Voronoi tooltips for dense data
- **Common pitfalls** -- clutter, overflow, background rects, resize, force oscillation, Canvas DPI

**Not covered:** scrollytelling/narrative sequencing, annotation-as-data patterns, d3-annotation library API details, Observable Plot annotation marks, structured/declarative annotation grammars.

---

## Scrollytelling Patterns

Scroll-driven narrative visualization sequences annotations and chart states as the reader scrolls. Instead of showing all annotations at once, each "step" reveals one insight.

### Scrollama + IntersectionObserver

[Scrollama](https://github.com/russellsamora/scrollama) (Russell Samora, The Pudding) is the standard library. It wraps IntersectionObserver to fire callbacks when step elements cross a viewport threshold.

**Core API:**

```js
import scrollama from "scrollama";

const scroller = scrollama();
scroller
  .setup({
    step: ".step",        // selector for step elements
    offset: 0.5,          // trigger at 50% viewport height
    progress: true,        // enable 0-1 progress tracking
  })
  .onStepEnter(({ element, index, direction }) => {
    // Update chart: add annotation, change highlight, transition data
    updateChart(index, direction);
  })
  .onStepExit(({ element, index, direction }) => {
    // Clean up: remove annotation if scrolling backward
  })
  .onStepProgress(({ element, index, progress }) => {
    // Continuous: drive animation progress 0-1
  });
```

**D3 integration pattern -- sticky graphic with step-driven annotations:**

```html
<section id="scrolly">
  <div class="sticky-graphic">
    <!-- D3 chart lives here, position: sticky -->
  </div>
  <div class="steps">
    <div class="step" data-annotation="intro">The trend held steady until 2019...</div>
    <div class="step" data-annotation="spike">Then COVID caused a 40% spike.</div>
    <div class="step" data-annotation="recovery">Recovery began in Q3 2021.</div>
  </div>
</section>
```

```css
.sticky-graphic {
  position: sticky;
  top: 0;
  height: 100vh;
}
.step {
  min-height: 80vh;      /* enough scroll distance per step */
  padding: 1rem;
}
```

**Step handler pattern -- each step maps to a chart mutation:**

```js
const steps = [
  // Each function takes the chart state and adds/removes elements
  (svg) => { /* show base chart, no annotations */ },
  (svg) => { /* highlight 2019, add callout */ },
  (svg) => { /* highlight COVID spike, add reference line */ },
  (svg) => { /* show recovery trend, add trend annotation */ },
];

function updateChart(index, direction) {
  steps[index](svg);
}
```

**v3 changes:** Scrollama v2+ deprecated container enter/exit in favor of CSS `position: sticky`. v3+ deprecated the `order` property. The library is stable and maintained.

### CSS Scroll-Driven Animations (emerging)

Chrome supports native `animation-timeline: scroll()` and `animation-timeline: view()` for scroll-linked animations without JS. Safari and Firefox are implementing. For D3 use cases, this is relevant for:

- Animating annotation opacity/position tied to scroll position (no JS needed)
- `scroll-snap-type: y mandatory` for step-locking (steps snap to viewport)
- Detecting `position: sticky` stuck state via scroll-state queries (Chrome 2025+)

These are CSS-only complements to Scrollama, not replacements. Scrollama still handles the step logic and D3 integration; CSS scroll-driven animations handle the visual transitions.

### When to use scrollytelling vs static annotation

| Use scrollytelling when... | Use static annotations when... |
|---|---|
| The story has a sequence (temporal, causal) | The chart makes one or two claims |
| You need to build up complexity gradually | The audience is expert and scans quickly |
| Multiple annotations would clutter a single view | The chart is one panel in a grid |
| The audience is general public (news, reports) | The context is a dashboard or tool |

### What this adds beyond the current skill

The current skill treats annotations as simultaneous -- all visible at once. Scrollytelling adds **temporal sequencing** of annotations, step-based chart state management, and the sticky-graphic layout pattern. This is the dominant pattern in data journalism (NYT, WaPo, The Pudding, Reuters Graphics).

---

## Annotation as Data

The idea that annotations should be treated as structured data, not ad-hoc SVG elements hand-positioned in code.

### Elijah Meeks: First-Class Citizens

[Meeks' 2017 article](https://medium.com/@Elijah_Meeks/making-annotations-first-class-citizens-in-data-visualization-21db6383d3fe) argues annotations are "where we're going to see the next wave of innovation in data visualization." Key ideas:

- **Annotation is data visualization of metadata.** The annotation layer visualizes editorial judgment the same way the data layer visualizes measurements.
- **Multi-layer architecture.** A chart has multiple layers: data marks, annotations, interaction targets, axes. Only one layer is "traditional data visualization" -- the others are equally important.
- **Semiotic's approach.** The Semiotic framework (React) integrates d3-annotation as a first-class layer, treating annotations with the same lifecycle as data marks.

### Annotations as a JSON/CSV data layer

Store annotations alongside data, not inline in rendering code:

```json
[
  {
    "id": "covid-spike",
    "x": "2020-03-15",
    "y": 142000,
    "dx": -80,
    "dy": -40,
    "title": "COVID-19 declared pandemic",
    "body": "WHO declaration on March 11 preceded the sharpest weekly increase.",
    "priority": 1,
    "connector": "curve"
  },
  {
    "id": "vaccine-rollout",
    "x": "2021-01-04",
    "y": 98000,
    "dx": 60,
    "dy": -30,
    "title": "Vaccine rollout begins",
    "body": "First doses administered in the US.",
    "priority": 2,
    "connector": "elbow"
  }
]
```

Benefits:
- **Separation of concerns.** Designers edit annotations without touching rendering code.
- **Data-coordinate binding.** Annotations reference data values, not pixel positions. They survive rescaling, resizing, and data updates.
- **Priority filtering.** At narrow widths, show only `priority <= 1`. In a scrollytelling context, show annotations by step index.
- **Portability.** Same annotation data can drive d3-annotation, Observable Plot marks, or a Canvas renderer.

### ChartMark: Declarative Annotation Grammar

[ChartMark](https://chartmark.github.io/) (2025 research, IEEE VIS) is a structured grammar for chart annotation with declarative JSON syntax. Key design:

- Separates annotation **semantics** (what to annotate, why) from **implementation** (how to render)
- Atomic components (highlights, markers, labels, reference lines) compose into complex annotations
- Converters translate ChartMark specs to Vega-Lite, ECharts, or D3
- Hierarchical JSON maps onto annotation dimensions: task, chart context, visual encoding

This is a research prototype, not production-ready, but the design principle is sound: annotation specifications should be engine-agnostic.

### What this adds beyond the current skill

The current skill stores annotations in data coordinates for responsive repositioning but doesn't formalize the annotation data model. A structured approach enables: priority-based filtering, step-based sequencing, collaborative editing (non-coders can edit annotation JSON), and automated annotation placement from LLM-generated metadata.

---

## Observable Plot Annotations

Observable Plot treats annotations as marks -- the same abstraction used for bars, lines, and areas. No special annotation API; you compose from primitive marks.

### Tip Mark (tooltips + static callouts)

```js
Plot.plot({
  marks: [
    Plot.line(data, { x: "date", y: "value" }),
    // Static annotation using tip mark
    Plot.tip(["COVID-19 declared pandemic"], {
      x: new Date("2020-03-11"),
      y: 142000,
      anchor: "bottom"
    }),
    // Interactive tooltip on hover
    Plot.tip(data, Plot.pointer({ x: "date", y: "value" }))
  ]
})
```

The tip mark can be static (annotating specific points) or interactive (following the pointer). It auto-positions to avoid edges and supports multi-channel formatting.

### Rule Mark (reference lines)

```js
Plot.plot({
  marks: [
    Plot.barY(data, { x: "category", y: "value" }),
    // Threshold line
    Plot.ruleY([targetValue], { stroke: "red", strokeDasharray: "4,4" }),
    // Vertical event marker
    Plot.ruleX([new Date("2020-03-11")], { stroke: "gray" })
  ]
})
```

### Text Mark (direct labels)

```js
Plot.plot({
  marks: [
    Plot.dot(data, { x: "x", y: "y" }),
    Plot.text(data, {
      x: "x", y: "y",
      text: "label",
      dy: -10,
      lineWidth: 20,    // auto line wrapping (in ems)
      fontSize: 11
    })
  ]
})
```

The text mark supports automatic line wrapping via `lineWidth` -- something SVG lacks natively and the current skill implements manually with tspan splitting.

### Design philosophy: annotations are marks

Plot's approach eliminates the conceptual separation between "data" and "annotations." A reference line is just a `ruleY` mark with a single datum. A callout is a `tip` mark with static data. This composability is elegant but lacks d3-annotation's multi-part structure (subject + connector + note).

### What this adds beyond the current skill

Plot's marks-are-annotations philosophy is worth noting as a design influence. For D3 code, the takeaway is: treat annotation elements the same way you treat data elements -- bind them to data, use scales, use enter/update/exit. The `lineWidth` auto-wrapping is a feature gap in pure SVG that Plot solves.

---

## d3-annotation Library

[d3-annotation](https://d3-annotation.susielu.com/) by Susie Lu. The canonical annotation library for D3.

### Architecture: Subject + Connector + Note

Every annotation has three parts:
- **Subject** -- what is being annotated (circle, rect, threshold, badge)
- **Connector** -- line connecting subject to note (line, elbow, curve, with optional end arrows/dots)
- **Note** -- the text (title + label, with wrap, align, padding, background)

Any part can be disabled: `disable: ["connector"]`.

### Built-in annotation types

| Type | Subject | Use case |
|---|---|---|
| `annotationLabel` | none | Simple positioned text |
| `annotationCallout` | none | Text with connector line |
| `annotationCalloutCircle` | circle | Circled data point with callout |
| `annotationCalloutRect` | rectangle | Highlighted region with callout |
| `annotationCalloutElbow` | none | Elbow connector |
| `annotationCalloutCurve` | none | Curve connector |
| `annotationXYThreshold` | threshold line | Reference line with label |
| `annotationBadge` | badge icon | Numbered markers |

### Usage pattern

```js
import { annotation, annotationCalloutCircle } from "d3-svg-annotation";

const annotations = [
  {
    note: { title: "COVID spike", label: "40% increase in one week", wrap: 150 },
    x: xScale(new Date("2020-03-15")),
    y: yScale(142000),
    dx: -80, dy: -40,
    subject: { radius: 7 },
  }
];

const makeAnnotations = annotation()
  .type(annotationCalloutCircle)
  .annotations(annotations);

svg.append("g")
  .attr("class", "annotation-group")
  .call(makeAnnotations);
```

### Editability mode

d3-annotation has a built-in drag-to-reposition mode for authoring:

```js
makeAnnotations.editMode(true);  // enables dragging annotations to find good positions
```

This is valuable for the authoring workflow: position annotations visually, then read the x/y/dx/dy values from the DOM.

### When to use d3-annotation vs hand-roll

| Use d3-annotation when... | Hand-roll when... |
|---|---|
| You need 3+ callouts with connectors | You need 1-2 simple labels |
| You want the editMode authoring workflow | Canvas rendering (library is SVG-only) |
| Standard annotation types suffice | Custom annotation shapes needed |
| Rapid prototyping, Observable notebooks | Production code where you control every pixel |
| Team includes non-D3 developers | You're already managing annotation as data |

### Limitations

- **SVG only.** No Canvas support.
- **D3 v4 era.** Works with v7 but hasn't been updated since 2019 (v2.5.1). The API is stable but the codebase is unmaintained.
- **No responsive repositioning.** You must re-call the annotation generator on resize.
- **Styling.** Uses CSS classes, which is fine, but the default styles are opinionated.

### Alternatives

- **react-annotation** -- Susie Lu's React port, same concepts
- **d3-ring-note** -- Andrew Mollica's plugin for circle+text annotations (simpler)
- **Observable Plot marks** -- tip, text, rule as annotation primitives
- **Hand-rolled SVG/Canvas** -- what the current skill teaches
- **ChartMark** -- research grammar, not production-ready

The ecosystem hasn't produced a successor to d3-annotation. For D3 v7 projects, the choice is between d3-annotation (stable, unmaintained) and hand-rolling (more control, more code).

---

## Editorial Best Practices

Patterns from data journalism organizations (NYT, Washington Post, The Pudding, Reuters Graphics).

### What makes a good annotation

1. **Annotate the claim, not the data.** A callout on a bar saying "42%" wastes ink -- the viewer can read the axis. A callout saying "First time exports exceeded imports since 2008" earns its space because it provides context the axis cannot.

2. **Text hierarchy within the chart.** NYT graphics use a consistent hierarchy:
   - **Headline** (above chart): the takeaway, phrased as a finding
   - **Subtitle/deck**: methodology or scope context
   - **Inline annotations**: 1-3 callouts within the chart area
   - **Axis labels**: minimal, just enough to read values
   - **Source line**: data provenance

3. **Arrows, dots, circles as visual anchors.** Newsroom graphics use small visual elements -- a circle around an outlier, a thin arrow pointing to an inflection -- to direct the eye before the reader processes the text. These are cheaper than full callout annotations.

4. **Sufficient text is preferred.** Research (survey of data stories, Garreton et al. 2025) shows readers prefer more text integration with charts, not less. The fear of "too many words" is overblown for explanatory visualization.

5. **Design for the final data.** Unlike dashboards, editorial graphics are authored after the data is collected. The designer sees the shape of the data and adapts annotations to it. This is why newsroom graphics look better than automated ones -- annotations are hand-tuned to the specific dataset.

6. **Progressive disclosure in scrollytelling.** Build complexity step by step:
   - Step 1: Show the chart with minimal context
   - Step 2: Add the first annotation (the main claim)
   - Step 3: Add supporting evidence
   - Step 4: Add counterpoint or nuance
   - Step 5: Full picture with all context visible

### NYT/WaPo annotation style conventions

- **Muted connector lines.** Thin (0.5-1px), gray (#999 or lighter), no arrowheads unless direction matters.
- **Sans-serif annotation text.** Slightly smaller than body text (11-12px), regular weight for labels, bold for titles.
- **Background padding.** Semi-transparent white/cream rect behind annotation text to separate from data.
- **Highlight via desaturation.** Instead of making the annotated element louder, make everything else quieter. Gray out non-annotated data; the annotated element "pops" by being the only colored one.

### What this adds beyond the current skill

The current skill has the 3-annotation rule and editorial judgment section. What's missing:
- **Highlight-by-desaturation** pattern (gray everything except the annotated point)
- **Progressive disclosure** sequencing for scrollytelling
- **Text hierarchy** framework (headline/deck/inline/axis/source)
- **Newsroom connector styling** conventions (specific weights, colors)

---

## Decision Guidance

### Choosing an annotation approach

```
Need to sequence annotations over scroll?
  YES -> Scrollytelling (Scrollama + step functions)
  NO -> Static annotations

Need 3+ callouts with connectors?
  YES -> d3-annotation library or structured annotation data
  NO -> Hand-rolled SVG text + line

Need Canvas rendering?
  YES -> Hand-rolled Canvas callouts (current skill covers this)
  NO -> SVG annotations

Need responsive repositioning?
  YES -> Store in data coordinates, recompute on resize
  NO -> Fixed pixel positions are fine for static exports

Need non-developer editing?
  YES -> Annotation-as-data (JSON), d3-annotation editMode
  NO -> Inline in code is fine

Need cross-platform portability?
  YES -> ChartMark grammar (research) or annotation JSON with adapters
  NO -> D3-specific code is fine
```

### Annotation technique by chart type

| Chart type | Primary technique | Secondary |
|---|---|---|
| Line chart (time series) | Callout at inflection points | Reference lines for events/thresholds |
| Bar chart | Direct labels on notable bars | Threshold line for target |
| Scatterplot | Force-placed labels on outliers | Voronoi tooltip for exploration |
| Map | Positioned callouts with leader lines | Tooltip for detail |
| Small multiples | One shared annotation per grid | No per-panel callouts |
| Scrollytelling | Step-sequenced callouts | Highlight-by-desaturation |

---

## Code Patterns

### Pattern 1: Scrollama + D3 step-based annotations

```js
// Annotation data, one per step
const stepAnnotations = [
  null, // step 0: no annotation
  {
    x: "2020-03-11", y: 142000,
    dx: -80, dy: -40,
    title: "Pandemic declared",
    body: "WHO declares COVID-19 a global pandemic."
  },
  {
    x: "2021-01-04", y: 98000,
    dx: 60, dy: -30,
    title: "Vaccines begin",
    body: "First doses administered."
  },
];

function updateChart(stepIndex) {
  // Remove previous annotations
  annotationLayer.selectAll(".callout").remove();

  const ann = stepAnnotations[stepIndex];
  if (!ann) return;

  const cx = xScale(new Date(ann.x));
  const cy = yScale(ann.y);

  const g = annotationLayer.append("g")
    .attr("class", "callout")
    .attr("transform", `translate(${cx},${cy})`);

  // Leader line
  g.append("path")
    .attr("d", `M0,0 Q${ann.dx * 0.5},0 ${ann.dx},${ann.dy}`)
    .attr("fill", "none")
    .attr("stroke", "#999")
    .attr("stroke-width", 0.8);

  // Subject dot
  g.append("circle").attr("r", 4)
    .attr("fill", "none").attr("stroke", "#333").attr("stroke-width", 1.5);

  // Note
  const note = g.append("g")
    .attr("transform", `translate(${ann.dx},${ann.dy})`);
  note.append("text")
    .attr("font-weight", "bold").attr("font-size", 12)
    .text(ann.title);
  note.append("text")
    .attr("dy", "1.3em").attr("font-size", 11).attr("fill", "#666")
    .text(ann.body);
}
```

### Pattern 2: Annotation data layer with priority filtering

```js
// annotations.json loaded alongside data
async function loadAnnotations(url, maxPriority = 3) {
  const all = await d3.json(url);
  return all
    .filter(a => a.priority <= maxPriority)
    .map(a => ({
      ...a,
      // Convert data coordinates to pixel coordinates
      px: xScale(a.xType === "date" ? new Date(a.x) : a.x),
      py: yScale(a.y),
    }));
}

function renderAnnotations(annotations) {
  const groups = annotationLayer.selectAll(".annotation")
    .data(annotations, d => d.id)
    .join("g")
    .attr("class", "annotation")
    .attr("transform", d => `translate(${d.px},${d.py})`);

  // ... render subject, connector, note per annotation
}

// On resize: recompute px/py from data coordinates, re-render
function onResize() {
  const width = container.clientWidth;
  xScale.range([0, width - margin.left - margin.right]);
  const annotations = currentAnnotations.map(a => ({
    ...a,
    px: xScale(a.xType === "date" ? new Date(a.x) : a.x),
    py: yScale(a.y),
  }));
  renderAnnotations(annotations);
}
```

### Pattern 3: Highlight-by-desaturation

```js
function highlightAnnotated(data, annotatedIds) {
  // Gray out everything except annotated points
  selection
    .attr("fill", d => annotatedIds.has(d.id) ? color(d.category) : "#ccc")
    .attr("opacity", d => annotatedIds.has(d.id) ? 1 : 0.3)
    .attr("stroke", d => annotatedIds.has(d.id) ? "#333" : "none");
}
```

### Pattern 4: d3-annotation with responsive resize

```js
import { annotation, annotationCallout } from "d3-svg-annotation";

function buildAnnotations(xScale, yScale) {
  return annotation()
    .type(annotationCallout)
    .annotations(annotationData.map(a => ({
      note: { title: a.title, label: a.body, wrap: 150 },
      x: xScale(new Date(a.x)),
      y: yScale(a.y),
      dx: a.dx,
      dy: a.dy,
    })));
}

// Initial render
const makeAnnotations = buildAnnotations(xScale, yScale);
svg.append("g").attr("class", "annotation-group").call(makeAnnotations);

// On resize: rebuild with new scales
function onResize() {
  xScale.range([0, newWidth]);
  yScale.range([newHeight, 0]);
  const updated = buildAnnotations(xScale, yScale);
  svg.select(".annotation-group").call(updated);
}
```

---

## Sources

- [Scrollama](https://github.com/russellsamora/scrollama) -- IntersectionObserver-based scrollytelling
- [Introducing Scrollama](https://pudding.cool/process/introducing-scrollama/) -- The Pudding's intro
- [Making Annotations First-Class Citizens](https://medium.com/@Elijah_Meeks/making-annotations-first-class-citizens-in-data-visualization-21db6383d3fe) -- Elijah Meeks
- [d3-annotation](https://d3-annotation.susielu.com/) -- Susie Lu's annotation library
- [d3-annotation Design & Modes](https://www.susielu.com/data-viz/d3-annotation-design-and-modes) -- Susie Lu
- [ChartMark](https://chartmark.github.io/) -- Structured grammar for chart annotation (IEEE VIS)
- [Observable Plot Tip Mark](https://observablehq.com/plot/marks/tip) -- Plot's tooltip/annotation mark
- [Observable Plot Rule Mark](https://observablehq.com/plot/marks/rule) -- Reference lines as marks
- [Observable Plot Text Mark](https://observablehq.com/plot/marks/text) -- Text labels with auto-wrap
- [Plot Static Annotations](https://observablehq.com/@observablehq/plot-static-annotations) -- Annotation patterns in Plot
- [CSS Scroll-Driven Animations](https://tympanus.net/codrops/2024/01/17/a-practical-introduction-to-scroll-driven-animations-with-css-scroll-and-view/) -- Codrops intro
- [Scrollytelling on Steroids](https://css-tricks.com/scrollytelling-on-steroids-with-scroll-state-queries/) -- CSS scroll-state queries
- [Narrative Visualization: Telling Stories with Data](https://hci.ucsd.edu/220/NarrativeVisualization.pdf) -- Segel & Heer
- [Survey of Data Stories](https://journals.sagepub.com/doi/10.1177/14738716241287116) -- Garreton et al. 2025
- [Scrollama + D3 demo](https://github.com/edriessen/scrollytelling-scrollama-d3-demo) -- Integration example
