# D3 Power Tools

## What This Is

A collection of skills for building advanced D3.js visualizations. Each skill encodes deep domain knowledge so you get production-quality results without rediscovering every pitfall.

Skills are designed to be useful across contexts: as Claude Code skills, as Gemini skills, and eventually as interactive tutorials for humans.

## Workflow

**Always render and test before claiming something works.**
Visual bugs are invisible in code. After writing a visualization, run the test script to verify it loads, renders, and has no JS errors. Then screenshot it and read the image.

**Keep outputs self-contained.**
Each skill should produce a single HTML file with inline JS/CSS. External data files are fine. No build tools required — just open in a browser.

**Use modern D3 (v7+) and modern browser APIs.**
OffscreenCanvas, Web Workers, pointer events, ResizeObserver, CSS custom properties. No IE11 considerations.

**Canvas for data, SVG for interaction.**
When rendering more than ~500 elements, use Canvas for the data layer and SVG for axes, labels, and interaction targets. This is a proven pattern from the d3.parcoords library.

## Testing with Playwright

Test runner: `scripts/test-viz.py`. Quick reference:

```bash
# Test a single file
python3 scripts/test-viz.py output.html --out /tmp/check.png --wait-for "svg"

# Run the test suite
python3 scripts/test-viz.py --config tests/test.config.json
```

Examples live in `skills/*/examples/` and double as test fixtures. Add new test cases to `tests/test.config.json` (paths are relative to project root). After building a visualization:

1. Run the test script to catch JS errors and rendering failures
2. Read the screenshot to verify visual correctness
3. Test interactions if interactive: `--interactions hover,brush,click`
4. Read the post-interaction screenshot

## Code Style

- ES modules or inline `<script type="module">`
- No frameworks — vanilla JS + D3
- No unnecessary abstractions
- Math-heavy code gets a brief comment explaining the geometry, not the implementation
- Prefer `const` and arrow functions
- Use D3 conventions: selections, joins, scales, axes

## Skills

Each subdirectory under `skills/` contains a `SKILL.md` with domain knowledge, architecture patterns, interaction recipes, and common pitfalls for a specific visualization type.

- `skills/axes-and-scales/` — scale selection (linear, log, symlog, pow, time, band, point), axis customization, tick formats, responsive tick counts, label collision avoidance, broken axes, dual-y, time gaps, ordinal grouping, Canvas axis rendering
- `skills/data-preparation/` — data loading, type coercion, cleaning, reshaping (group/rollup/pivot), aggregation, binning, joining, normalization
- `skills/sparkcharts/` — word-sized inline charts: sparklines, spark bars, win/loss, bullet charts, band/range, dot strips, embedding in tables and text
- `skills/parallel-coordinates/` — high-performance multivariate data exploration
- `skills/animated-transitions/` — enter/update/exit, canvas animation, staggering, scrollytelling
- `skills/shape-morphing/` — circle↔rect via cornerRadius, bar↔pie via arc params, arbitrary path morphing via point resampling, map projection transitions
- `skills/brushing-and-selection/` — intersection brushing, lasso, fisheye, cross-chart linking
- `skills/canvas-accessibility/` — keyboard navigation, screen reader support, ARIA, focus rings, data table fallback
- `skills/canvas-rendering/` — high-performance Canvas 2D patterns: quadtree hit detection, typed arrays, batched rendering, zoom, LOD
- `skills/color-and-compositing/` — color spaces, Paul Tol colorblind-safe palettes, canvas compositing (globalCompositeOperation), SVG blending, alpha/opacity strategies, color legends
- `skills/fallback-table/` — accessible data tables as chart alternatives: sortable columns, filtering, chart↔table toggle, linked highlighting, virtual scrolling, CSV export
- `skills/force-simulation/` — force-directed layouts: simulation lifecycle, all built-in forces, custom forces, drag interaction, constrained layouts, clustering, performance at 10K+ nodes
- `skills/hierarchy-edge-bundling/` — hierarchical edge bundling: LCA path routing, d3.curveBundle tension, radial dendrograms with cross-links, SVG and Canvas rendering
- `skills/hierarchy-interaction/` — expand/collapse, zoomable treemap/sunburst/pack, focus+context navigation
- `skills/hierarchy-layouts/` — treemap, pack, tree, cluster, partition, stratify, tiling strategies, labels, color encoding
- `skills/network-visualization/` — network graph types: node-link diagrams, adjacency matrix, arc diagrams, chord diagrams, Sankey flow diagrams
- `skills/patterned-fills/` — SVG pattern fills (hatching, dots, cross-hatch, stipple), stroke dash patterns, Canvas equivalents, markers, color+pattern dual encoding for accessibility
- `skills/geographic-maps/` — geographic maps: projections (selection, fitSize, rotation, clipping, insets), GeoJSON/TopoJSON (mesh, merge, neighbors, topology operations), choropleth (sequential, diverging, bivariate), point/bubble maps (scaleSqrt, force-collision), hex binning, cartograms (non-contiguous, Dorling), flow maps (great-circle arcs, curved, animated), geographic label placement (centroid, pole of inaccessibility, collision), zoom-to-feature (viewBox, d3.zoom, projection-based), globe rendering (versor rotation, back-face), Canvas architecture (multi-layer stack, batch-by-color, color-pick hit detection, frame budgeting), tile layers (SVG, Canvas with caching), geodesic operations, large geometry (simplification, LOD, streaming), small multiples, projection transitions
- `skills/webgl-rendering/` — GPU-accelerated rendering for 100K–10M+ elements: shaders, instanced rendering, D3+WebGL integration, texture atlases, zoom/picking
- `skills/color-themes/` — theming systems: light/dark/high-contrast modes, CSS custom properties, semantic color tokens, prefers-color-scheme auto dark mode, theme-aware D3 scales, Canvas theming, WCAG contrast compliance
- `skills/zoom-and-pan/` — d3-zoom API, geometric vs semantic zoom, SVG and Canvas zoom, rescaleX/rescaleY axis integration, zoom constraints, programmatic zoom-to-fit, minimap, pinch-to-zoom, zoom-linked views, level-of-detail, brush-to-zoom
- `skills/annotations-and-labels/` — callout annotations, leader lines (straight/elbow/curved), force-based label collision avoidance, responsive labels, rich tooltips, threshold/reference lines, Canvas annotations
- `skills/statistical-charts/` — box plots, violin plots, ridgeline/joy plots, bee swarm plots, strip/jitter plots, density plots, QQ plots, kernel density estimation, quartile calculation
- `skills/small-multiples/` — trellis/faceted layouts, grid layout math, shared vs independent scales, synchronized cross-panel interaction, responsive reflow, Canvas small multiples, lazy rendering
- `skills/temporal-time-series/` — time scales (scaleTime vs scaleUtc), date parsing pitfalls, time-aware axes, gap handling, horizon charts, swimlanes/event timelines, Gantt charts, cycle plots, real-time streaming (sliding window, circular buffer, WebSocket), brushed time selection, multi-series with Voronoi nearest, LTTB downsampling
- `skills/linked-views/` — coordinating multiple views: event bus (d3.dispatch), shared state store, crossfilter pattern, coordinated brushing/zoom, overview+detail, focus+context, shared scales, heterogeneous chart linking, state serialization, bitmap indexing for large datasets
- `skills/responsive-charts/` — ResizeObserver lifecycle, container-based sizing, viewBox vs redraw-on-resize, aspect ratio strategies, responsive margins, breakpoint-driven layout, responsive text/labels, touch adaptation, Canvas DPI handling, iframe embedding with postMessage, print styles
- `skills/cross-skill-composition/` — architectural patterns for combining skills: layer stack (Canvas+SVG+HTML), SVG vs Canvas decision framework, initialization sequence, state architecture (data/view/interaction), dirty-flag rendering, performance budgets, composition archetypes (explorer, narrative, dashboard, spatial, morpher), resize contract, Canvas↔SVG handoff
