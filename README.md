# D3 Power Tools

**[Demo Gallery](https://syntagmatic.github.io/d3-power-tools/)**

Skills for building advanced D3.js visualizations. Each one captures the judgment calls that separate a chart that communicates from one that merely renders. See [WHY.md](notes/WHY.md) for the philosophy.

Each skill is a `SKILL.md` file — patterns, code, and pitfalls for a specific visualization domain. Skills load automatically based on what you're building. They produce self-contained HTML files with inline JS/CSS. No build tools, no frameworks — just vanilla JS + D3 v7.

## Skills

### Seeing patterns

How to reveal relationships in data through selection, comparison, and coordination.

**[parallel-coordinates](skills/parallel-coordinates/SKILL.md)** — See relationships across many dimensions at once. Canvas rendering, axis reordering, composite brushing, progressive rendering for large datasets.

**[brushing](skills/brushing/SKILL.md)** — Ask questions with your hand. Intersection brushing, lasso, fisheye, cross-chart linking, SVG and Canvas selection state.

**[linked-views](skills/linked-views/SKILL.md)** — Make separate charts into one instrument. d3.dispatch, shared state, crossfilter bitmap indexing, coordinated brushing/zoom, overview+detail.

**[distributions](skills/distributions/SKILL.md)** — Show the shape of data, not just summaries. Box plots, violins, ridgelines, bee swarms, strip/jitter, density, QQ plots, KDE.

### Seeing structure

How to make hierarchies, networks, and relationships legible.

**[hierarchy-layouts](skills/hierarchy-layouts/SKILL.md)** — Choose the right layout for the insight. Treemap, pack, tree, cluster, partition, stratify, tiling strategies, label placement.

**[hierarchy-interaction](skills/hierarchy-interaction/SKILL.md)** — Navigate large trees without losing context. Expand/collapse, zoomable treemap/sunburst/pack, focus+context.

**[edge-bundling](skills/edge-bundling/SKILL.md)** — Reveal connection patterns in dense graphs. LCA path routing, curveBundle tension, animated layout transitions with data-space interpolation.

**[force](skills/force/SKILL.md)** — Let structure emerge from constraints. Simulation lifecycle, custom forces, drag, clustering, performance at 10K+ nodes.

**[network](skills/network/SKILL.md)** — Pick the right representation for the graph. Node-link, adjacency matrix, arc, chord, Sankey — each reveals different structure.

### Seeing place

How to ground data in geography.

**[cartography](skills/cartography/SKILL.md)** — Maps as analytical instruments. Projections, TopoJSON operations, choropleth, bubble maps, hex bins, cartograms, flow maps, globe rendering, Canvas multi-layer architecture, tile layers, large geometry/LOD.

### Seeing change

How to show what happened, what's happening, and what things become.

**[time-series](skills/time-series/SKILL.md)** — Time as a first-class dimension. scaleTime vs scaleUtc, horizon charts, swimlanes, Gantt, cycle plots, real-time streaming, LTTB downsampling.

**[motion](skills/motion/SKILL.md)** — Guide the eye with movement. Enter/update/exit, canvas animation, staggering, scrollytelling, mid-flight interruption.

**[shape-morphing](skills/shape-morphing/SKILL.md)** — Show continuity between states. circle↔rect, bar↔pie, arbitrary path morphing via point resampling, projection transitions.

### Making it legible

How to ensure the viewer actually reads what you drew.

**[scales](skills/scales/SKILL.md)** — Map data to visual space correctly. Scale selection, tick formats, responsive ticks, label collision, broken axes, dual-y, time gaps.

**[color](skills/color/SKILL.md)** — Color as encoding, not decoration. Perceptual spaces, Tol colorblind-safe palettes, compositing, CVD simulation, dark mode, WCAG contrast, color legends.

**[visual-texture](skills/visual-texture/SKILL.md)** — A second channel beyond color. Hatching, stipple, diamonds, filter textures, pattern+color dual encoding for accessibility and print.

**[annotation](skills/annotation/SKILL.md)** — Tell the viewer what matters. Callout annotations, leader lines, force-based label collision, tooltips, threshold/reference lines.

**[data-table](skills/data-table/SKILL.md)** — An equal representation, not a fallback. Sortable, filterable, chart↔table toggle, linked highlighting.

**[canvas-accessibility](skills/canvas-accessibility/SKILL.md)** — Make Canvas visible to everyone. Keyboard navigation, ARIA, focus rings, screen reader announcements, data table fallback.

### Making it work

How to handle performance, responsiveness, and navigation.

**[canvas](skills/canvas/SKILL.md)** — When SVG runs out of room. Quadtree hit detection, typed arrays, batched rendering, multi-layer architecture, zoom with LOD, frame budgets.

**[webgl](skills/webgl/SKILL.md)** — When Canvas runs out of room. Shaders, instanced rendering, texture atlases, zoom via uniforms, GPU picking. 100K–10M+ elements.

**[navigation](skills/navigation/SKILL.md)** — Move through visual space. Geometric vs semantic zoom, rescaleX/rescaleY, constraints, minimap, pinch-to-zoom, level-of-detail.

**[responsive](skills/responsive/SKILL.md)** — Fit any container without losing meaning. ResizeObserver, viewBox vs redraw, aspect ratio, breakpoints, touch, Canvas DPI.

### Before you render

How to prepare data and choose the right container.

**[data-gathering](skills/data-gathering/SKILL.md)** — Get data into shape. Loading, type coercion, cleaning, reshaping, aggregation, binning, joining, normalization.

**[sparkcharts](skills/sparkcharts/SKILL.md)** — Charts at the size of a word. Sparklines, spark bars, win/loss, bullet charts, dot strips, embedded in tables and text.

**[small-multiples](skills/small-multiples/SKILL.md)** — Repeat to compare. Grid layout math, shared vs independent scales, synchronized cross-panel interaction, responsive reflow.

### Meta

Skills for testing, evaluating, and improving other skills. The compound tool.

**[idiomatic-d3](meta/idiomatic-d3/SKILL.md)** — What good D3 code looks like. Chaining indentation, margin convention, `.join()` with key functions, `selection.call()`, reusable chart closures.

**[cross-skill-composition](meta/cross-skill-composition/SKILL.md)** — How skills fit together. Layer stacks, state architecture, dirty-flag rendering, performance budgets, composition archetypes.

**[check-skill](meta/check-skill/SKILL.md)** — Audit a skill for dangling references and broken examples.

**[simplify-skill](meta/simplify-skill/SKILL.md)** — Compress a SKILL.md for clarity and token efficiency.

**[skill-eval](meta/skill-eval/SKILL.md)** — Evaluate skill effectiveness with before/after comparisons.

**[metamorphic-tester](meta/metamorphic-tester/SKILL.md)** — Validate math and logic via visual invariants. Scaling, permutation, and subset relations to catch silent bugs.

**[visual-critic](meta/visual-critic/SKILL.md)** — Audit design quality and "taste." Typographic hierarchy, 8px grid, WCAG accessibility, and visual logic.

**[robustness-contract](meta/robustness-contract/SKILL.md)** — Pre-negotiate behavior for edge cases. "Data of Death" defense (nulls, outliers, cardinality) and interaction state machines.

**[perceptual-red-team](meta/perceptual-red-team/SKILL.md)** — Audit for cognitive overload. Working memory limits, "Chart Fatigue," hairball detection, and congruence in animation.

**[deception-detector](meta/deception-detector/SKILL.md)** — Audit for mathematical and ethical honesty. Truncated axes, "The Lie Factor," quantile traps, and fabricated correlations.

**[interaction-stress-test](meta/interaction-stress-test/SKILL.md)** — Audit for race conditions and "update storms." Feedback loops, stale closures, RAF coalescing, and dirty-flag rendering.

## Testing

41 test fixtures with 161 test cases covering rendering, interactions, transitions, and edge cases:

```bash
# Run the full suite
python3 scripts/test-viz.py --config tests/test.config.json

# Test a single visualization
python3 scripts/test-viz.py skills/edge-bundling/examples/edge-bundling.html --out /tmp/check.png
```

Tests use Playwright to verify pages load without JS errors, render expected DOM elements, and capture screenshots for visual inspection. See the [test config](tests/test.config.json) for the full list.
