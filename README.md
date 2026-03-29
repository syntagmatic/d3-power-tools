# D3 Power Tools

**[Demo Gallery](https://syntagmatic.github.io/d3-power-tools/)**

Skills for building advanced D3.js visualizations. Each one captures the judgment calls that separate a chart that communicates from one that merely renders. See [WHY.md](notes/WHY.md) for the philosophy.

Each skill is a `SKILL.md` file — patterns, code, and pitfalls for a specific visualization domain. Skills load automatically based on what you're building. They produce self-contained HTML files with inline JS/CSS. No build tools, no frameworks — just vanilla JS + D3 v7.

## Install

Each skill is a folder with a `SKILL.md` file and optional examples and scripts. AI coding tools auto-discover skills from specific directories — install by symlinking or copying the skills you want.

### Claude Code

```bash
# All skills (symlink the whole directory)
ln -s /path/to/d3-power-tools/skills .claude/skills

# Or individual skills
mkdir -p .claude/skills
ln -s /path/to/d3-power-tools/skills/cartography .claude/skills/cartography
```

Skills live in `.claude/skills/` at project or user (`~/.claude/skills/`) scope. Claude reads the `description` frontmatter in each `SKILL.md` and loads the right skill automatically when your prompt matches — ask for a treemap and the `hierarchy-layouts` skill activates.

### Gemini CLI

```bash
# All skills
ln -s /path/to/d3-power-tools/skills .gemini/skills

# Or individual skills
mkdir -p .gemini/skills
ln -s /path/to/d3-power-tools/skills/force .gemini/skills/force
```

Skills live in `.gemini/skills/` at project or user (`~/.gemini/skills/`) scope. Same auto-activation based on `description` frontmatter.

### Antigravity

```bash
# All skills
ln -s /path/to/d3-power-tools/skills .agent/skills

# Or individual skills
mkdir -p .agent/skills
ln -s /path/to/d3-power-tools/skills/color .agent/skills/color
```

Skills live in `.agent/skills/` at project or user (`~/.gemini/antigravity/skills/`) scope.

### Other tools and manual use

The skills are plain markdown. Any tool that reads structured context files can use them — point it at `skills/<name>/SKILL.md`.

**Skill folder structure:**
```
skills/cartography/
├── SKILL.md           # The skill itself (required)
├── examples/          # Working HTML files you can open in a browser
│   ├── choropleth.html
│   └── globe.html
└── scripts/           # Reusable JS (referenced from SKILL.md)
    └── projection-picker.js
```

The `SKILL.md` frontmatter follows the emerging cross-tool standard:
```yaml
---
name: cartography
description: "Build maps with D3.js — projections, TopoJSON, choropleth, ..."
---
```

The `name` identifies the skill. The `description` tells the tool when to activate it. Everything after the frontmatter is the skill content: judgment calls, code patterns, and pitfalls.

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

The workshop. Each tool does one job.

**Code guides**

**[square-tool](meta/square-tool/SKILL.md)** — D3 code style. Chaining indentation, margin convention, `.join()` with key functions, `selection.call()`, reusable chart closures.

**[jig-template](meta/jig-template/SKILL.md)** — Multi-skill assembly. Layer stacks, state architecture, dirty-flag rendering, performance budgets, composition archetypes.

**Inspection tools**

**[polish-tool](meta/polish-tool/SKILL.md)** — Design quality. Color harmony, typographic hierarchy, whitespace, data-ink ratio, overall feel.

**[level-tool](meta/level-tool/SKILL.md)** — Data honesty. Lie factor, zero baselines, metamorphic relations, data join correctness.

**[stress-tool](meta/stress-tool/SKILL.md)** — Interaction robustness. Update storms, stale closures, feedback loops, transition handoff conflicts.

**[scope-tool](meta/scope-tool/SKILL.md)** — Cognitive clarity. Working memory limits, animation congruence, spaghetti threshold, color overload.

**Workshop tools**

**[calibrate-tool](meta/calibrate-tool/SKILL.md)** — Measure skill effectiveness. With/without comparison for content skills, blind evaluation for auditing skills.

**[sharpen-tool](meta/sharpen-tool/SKILL.md)** — Audit and compress SKILL.md files for clarity and token efficiency.

## Testing

41 test fixtures with 161 test cases covering rendering, interactions, transitions, and edge cases:

```bash
# Run the full suite
python3 scripts/test-viz.py --config tests/test.config.json

# Test a single visualization
python3 scripts/test-viz.py skills/edge-bundling/examples/edge-bundling.html --out /tmp/check.png
```

Tests use Playwright to verify pages load without JS errors, render expected DOM elements, and capture screenshots for visual inspection. See the [test config](tests/test.config.json) for the full list.
