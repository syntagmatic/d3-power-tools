# D3 Power Tools

**[Demo Gallery](https://syntagmatic.github.io/d3-power-tools/)**

Claude Code skills for building advanced D3.js visualizations. Each skill encodes deep domain knowledge — layout algorithms, interaction patterns, rendering strategies, and common pitfalls — so you get production-quality results without rediscovering every gotcha.

## Skills

### Data Exploration

**[parallel-coordinates](skills/parallel-coordinates/SKILL.md)** — High-performance multivariate data exploration. Canvas rendering with D3 curve generators, axis reordering, composite brushing, and progressive rendering for large datasets.

**[brushing](skills/brushing/SKILL.md)** — Intersection brushing, lasso selection, fisheye distortion, and cross-chart linking. Covers both SVG and canvas selection state management with fade/highlight patterns.

**[linked-views](skills/linked-views/SKILL.md)** — Coordinating multiple views: d3.dispatch event bus, shared state stores, crossfilter-style filtering with bitmap indexing, coordinated brushing and zoom, overview+detail, focus+context, state serialization with undo/redo.

### Hierarchy

**[hierarchy-layouts](skills/hierarchy-layouts/SKILL.md)** — All six D3 hierarchy layouts: treemap, pack, tree, cluster, partition, and stratify. Tiling strategies, radial coordinates, label placement, color encoding, and the `.sum()`/`.sort()` pipeline.

**[hierarchy-interaction](skills/hierarchy-interaction/SKILL.md)** — Expand/collapse trees, zoomable treemaps and sunbursts, focus+context circle packing, pan and zoom. Animated transitions between hierarchy states.

**[hierarchy-edge-bundling](skills/hierarchy-edge-bundling/SKILL.md)** — Hierarchical edge bundling for dependency graphs and module relationships. LCA path routing with `node.path()`, `d3.curveBundle.beta()` tension control, and animated layout transitions (bundle, cluster, tree, pack, treemap) with continuous per-frame edge redrawing via data-space interpolation.

### Networks & Forces

**[force-simulation](skills/force-simulation/SKILL.md)** — Force-directed layouts with `d3.forceSimulation`. Simulation lifecycle, all built-in forces, custom forces, tick management, drag interaction, constrained layouts, clustering, and performance at 10K+ nodes.

**[network-visualization](skills/network-visualization/SKILL.md)** — Network and graph visualization types: node-link diagrams, adjacency matrices, arc diagrams, chord diagrams, and Sankey flow diagrams. Data preparation, layout comparison, and interaction patterns.

### Styling & Color

**[visual-texture](skills/visual-texture/SKILL.md)** — SVG pattern fills (hatching, dots, cross-hatch, stipple, diamonds, triangles, zigzag), perceptual distinctiveness ranking, SVG filter textures (feTurbulence, halftone), stroke dash patterns, Canvas pattern atlas, Canvas pattern+color compositing, SVG markers, color+pattern dual encoding for accessible choropleth, animated patterns, print considerations.

**[color](skills/color/SKILL.md)** — Color spaces (Lab, HCL, OKLab), color perception (simultaneous contrast, small-area, Mach bands), scale design principles (sequential lightness, diverging symmetry), Paul Tol colorblind-safe palettes, CVD simulation, Canvas compositing (lighter, multiply, source-in, masking), SVG blending/feColorMatrix, alpha/opacity strategies, dark mode adaptation, wide gamut (P3, oklch), WCAG contrast, color legends (continuous, categorical, bivariate, size).

### Time & Responsiveness

**[time-series](skills/time-series/SKILL.md)** — Time scales (scaleTime vs scaleUtc), date parsing pitfalls, time-aware axes, gap handling, horizon charts, swimlanes, Gantt charts, cycle plots, real-time streaming with sliding window and WebSocket, brushed time selection, multi-series with Voronoi nearest, LTTB downsampling.

**[responsive](skills/responsive/SKILL.md)** — ResizeObserver lifecycle, container-based sizing, viewBox vs redraw-on-resize, aspect ratio strategies, responsive margins, breakpoint-driven layout changes, responsive text and labels, touch adaptation, Canvas DPI handling, iframe embedding, print styles.

### Rendering & Animation

**[canvas](skills/canvas/SKILL.md)** — High-performance Canvas 2D patterns for 1K–1M+ elements. Quadtree hit detection, typed arrays, batched rendering, multi-layer canvas architecture, zoom with LOD, and frame budget management.

**[motion](skills/motion/SKILL.md)** — Enter/update/exit with keyed joins, canvas animation pipelines with D3 interpolators, staggered animations, and scrollytelling.

**[shape-morphing](skills/shape-morphing/SKILL.md)** — Smoothly morph between shapes: circle↔rect via cornerRadius, bar↔pie via arc parameters, arbitrary path morphing via point resampling with rotation alignment. No external libraries.

**[canvas-accessibility](skills/canvas-accessibility/SKILL.md)** — Making canvas visualizations accessible. Keyboard tree navigation (arrow keys, Home/End, Enter/Escape), ARIA roles and live regions, shape-adaptive focus rings, screen reader announcements, and data table fallback views.

**[webgl-rendering](skills/webgl-rendering/SKILL.md)** — GPU-accelerated rendering for 100K–10M+ elements. Vertex/fragment shaders, instanced rendering, D3+WebGL integration, texture atlases, zoom via uniforms, and GPU picking.

### Charts & Statistics

**[axes-and-scales](skills/axes-and-scales/SKILL.md)** — Scale selection, axis customization, tick formats, responsive tick counts, label collision avoidance, broken axes, dual-y, time gaps, ordinal grouping.

**[data-gathering](skills/data-gathering/SKILL.md)** — Data loading, type coercion, cleaning, reshaping (group/rollup/pivot), aggregation, binning, joining, normalization, columnar typed arrays.

**[sparkcharts](skills/sparkcharts/SKILL.md)** — Word-sized inline charts: sparklines, spark bars, win/loss strips, bullet charts, band/range charts, dot strips, embedded in tables and text.

**[distributions](skills/distributions/SKILL.md)** — Box plots, violin plots, ridgeline/joy plots, bee swarm plots, strip/jitter plots, density plots, QQ plots, kernel density estimation.

**[small-multiples](skills/small-multiples/SKILL.md)** — Trellis/faceted layouts, grid layout math, shared vs independent scales, synchronized cross-panel interaction, responsive reflow.

**[annotation](skills/annotation/SKILL.md)** — Callout annotations, leader lines, force-based label collision avoidance, responsive labels, rich tooltips, threshold/reference lines.

**[cartography](skills/cartography/SKILL.md)** — Projections, GeoJSON/TopoJSON topology operations (merge/dissolve/neighbors), choropleth (sequential, diverging, bivariate), bubble maps with force-collision, hex binning, cartograms, flow maps (great-circle, curved, animated), geographic label placement, zoom-to-feature, globe (versor rotation, back-face), Canvas multi-layer architecture with hit detection, tile layers, geodesic operations, large geometry/LOD, projection transitions.

**[data-table](skills/data-table/SKILL.md)** — Accessible data tables as chart alternatives: sortable columns, filtering, chart↔table toggle, linked highlighting, virtual scrolling, CSV export.

**[navigation](skills/navigation/SKILL.md)** — d3-zoom API, geometric vs semantic zoom, SVG and Canvas zoom, rescaleX/rescaleY axis integration, zoom constraints, minimap, pinch-to-zoom, level-of-detail.

### Meta Skills

Skills for testing, evaluating, and improving other skills.

**[idiomatic-d3](meta/idiomatic-d3/SKILL.md)** — D3 code style and review: method chaining indentation, margin convention, `.join()` data joins with key functions, `selection.call()` composition, reusable chart closure pattern, naming conventions, anti-patterns checklist.

**[cross-skill-composition](meta/cross-skill-composition/SKILL.md)** — Architectural patterns for combining skills: Canvas+SVG+HTML layer stacks, initialization sequencing, state architecture (data/view/interaction), dirty-flag rendering, performance budgets, five composition archetypes (explorer, narrative, dashboard, spatial, morpher), and the resize contract.

**[check-skill](meta/check-skill/SKILL.md)** — Audit a skill for dangling references, broken code examples, and incorrect descriptions.

**[simplify-skill](meta/simplify-skill/SKILL.md)** — Compress and simplify a SKILL.md for clarity and token efficiency.

**[skill-eval](meta/skill-eval/SKILL.md)** — Evaluate skill effectiveness with before/after comparisons and iterative improvement.

## How It Works

Each skill is a `SKILL.md` file containing patterns, code snippets, and pitfalls for a specific visualization type. When you ask Claude Code to build a visualization, the relevant skill loads automatically based on what you're building — you don't need to reference them directly.

Skills produce self-contained HTML files with inline JS/CSS. No build tools, no frameworks — just vanilla JS + D3 v7. Open in a browser.

## Testing

41 test fixtures with 161 test cases covering rendering, interactions, transitions, and edge cases:

```bash
# Run the full suite
python3 scripts/test-viz.py --config tests/test.config.json

# Test a single visualization
python3 scripts/test-viz.py skills/hierarchy-edge-bundling/examples/edge-bundling.html --out /tmp/check.png
```

Tests use Playwright to verify pages load without JS errors, render expected DOM elements, and capture screenshots for visual inspection. See the [test config](tests/test.config.json) for the full list.
