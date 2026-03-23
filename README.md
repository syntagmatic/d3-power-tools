# D3 Power Tools

Claude Code skills for building advanced D3.js visualizations. Each skill encodes deep domain knowledge — layout algorithms, interaction patterns, rendering strategies, and common pitfalls — so you get production-quality results without rediscovering every gotcha.

## Skills

### Data Exploration

**[parallel-coordinates](skills/parallel-coordinates/SKILL.md)** — High-performance multivariate data exploration. Canvas rendering with D3 curve generators, axis reordering, composite brushing, and progressive rendering for large datasets.

**[brushing-and-selection](skills/brushing-and-selection/SKILL.md)** — Intersection brushing, lasso selection, fisheye distortion, and cross-chart linking. Covers both SVG and canvas selection state management with fade/highlight patterns.

### Hierarchy

**[hierarchy-layouts](skills/hierarchy-layouts/SKILL.md)** — All six D3 hierarchy layouts: treemap, pack, tree, cluster, partition, and stratify. Tiling strategies, radial coordinates, label placement, color encoding, and the `.sum()`/`.sort()` pipeline.

**[hierarchy-interaction](skills/hierarchy-interaction/SKILL.md)** — Expand/collapse trees, zoomable treemaps and sunbursts, focus+context circle packing, pan and zoom. Animated transitions between hierarchy states.

**[hierarchy-edge-bundling](skills/hierarchy-edge-bundling/SKILL.md)** — Hierarchical edge bundling for dependency graphs and module relationships. LCA path routing with `node.path()`, `d3.curveBundle.beta()` tension control, and animated layout transitions (bundle, cluster, tree, pack, treemap) with continuous per-frame edge redrawing via data-space interpolation.

### Networks & Forces

**[force-simulation](skills/force-simulation/SKILL.md)** — Force-directed layouts with `d3.forceSimulation`. Simulation lifecycle, all built-in forces, custom forces, tick management, drag interaction, constrained layouts, clustering, and performance at 10K+ nodes.

**[network-visualization](skills/network-visualization/SKILL.md)** — Network and graph visualization types: node-link diagrams, adjacency matrices, arc diagrams, chord diagrams, and Sankey flow diagrams. Data preparation, layout comparison, and interaction patterns.

### Styling & Patterns

**[patterned-fills](skills/patterned-fills/SKILL.md)** — SVG pattern fills (diagonal hatching, cross-hatch, dots, stipple, checkerboard, wavy lines), stroke dash patterns, Canvas pattern equivalents, SVG markers for decorated strokes, and color+pattern dual encoding for accessible, print-friendly charts.

### Rendering & Animation

**[canvas-rendering](skills/canvas-rendering/SKILL.md)** — High-performance Canvas 2D patterns for 1K–1M+ elements. Quadtree hit detection, typed arrays, batched rendering, multi-layer canvas architecture, zoom with LOD, and frame budget management.

**[animated-transitions](skills/animated-transitions/SKILL.md)** — Enter/update/exit with keyed joins, canvas animation pipelines with D3 interpolators, staggered animations, and scrollytelling.

**[shape-morphing](skills/shape-morphing/SKILL.md)** — Smoothly morph between shapes: circle↔rect via cornerRadius, bar↔pie via arc parameters, arbitrary path morphing via point resampling with rotation alignment. No external libraries.

**[canvas-accessibility](skills/canvas-accessibility/SKILL.md)** — Making canvas visualizations accessible. Keyboard tree navigation (arrow keys, Home/End, Enter/Escape), ARIA roles and live regions, shape-adaptive focus rings, screen reader announcements, and data table fallback views.

## How It Works

Each skill is a `SKILL.md` file containing patterns, code snippets, and pitfalls for a specific visualization type. When you ask Claude Code to build a visualization, the relevant skill loads automatically based on what you're building — you don't need to reference them directly.

Skills produce self-contained HTML files with inline JS/CSS. No build tools, no frameworks — just vanilla JS + D3 v7. Open in a browser.

## Testing

28 test fixtures with 123 test cases covering rendering, interactions, transitions, and edge cases:

```bash
# Run the full suite
python3 scripts/test-viz.py --config tests/test.config.json

# Test a single visualization
python3 scripts/test-viz.py skills/hierarchy-edge-bundling/examples/edge-bundling.html --out /tmp/check.png
```

Tests use Playwright to verify pages load without JS errors, render expected DOM elements, and capture screenshots for visual inspection. See the [test config](tests/test.config.json) for the full list.
