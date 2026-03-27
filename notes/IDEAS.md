# D3 Power Tools — Ideas & Improvements

## Next

- [ ] Review front matter (name, description) across all 27 skills for consistency and trigger accuracy
- [ ] Calibrate remaining 5 adversarial agents (deception-detector, interaction-stress-test, perceptual-red-team, robustness-contract, metamorphic-tester) using the blind eval protocol in `meta/adversarial-eval/`
- [ ] Voronoi & Delaunay — interactive nearest-neighbor lookup, Voronoi diagrams as tooltip regions, Voronoi treemaps, Delaunay triangulation, clipped Voronoi cells
- [ ] Live & streaming data — append-only charts with sliding window, circular buffers, WebSocket integration, `requestAnimationFrame`-gated updates, graceful reconnection

## Self-Visualization Blocks

Visualizations of d3-power-tools itself, using the skills to explore the project's own structure.

- [ ] **Skill dependency graph** — cross-references between skills as a force-directed network or chord diagram (`network`, `force`, `edge-bundling`)
- [ ] **Block × skill matrix** — which blocks exercise which skills, as an adjacency matrix or heatmap. Data from `manifest.json` (`network`, `color`)
- [ ] **Skill size treemap** — line counts as area, grouped by category (`hierarchy-layouts`)
- [ ] **Adversarial audit scorecard** — per-block × per-agent score matrix as a diverging heatmap (`color`, `scales`)
- [ ] **Test coverage map** — tests per skill linked to examples, sparkline of coverage depth (`linked-views`, `sparkcharts`)

---

## New Skill Ideas

- **Text & labels** — force-based label placement, occlusion culling, text wrapping in constrained shapes, curved text on arcs, automatic abbreviation
- **Export & serialization** — SVG-to-PNG via `OffscreenCanvas`, PDF generation, responsive embed snippets, copy-to-clipboard, SVG optimization
- **Heatmaps & matrices** — calendar heatmaps, correlation matrices, pixel-level Canvas rendering, cell annotations, row/column clustering and reordering
- **Radial & polar charts** — radar/spider charts, polar area (Nightingale rose), radial bar, wind roses, clock visualizations, circular heatmaps
- **Waffle & unit charts** — isotype/pictogram grids, proportional unit squares, animated counting transitions, icon arrays, XKCD-style magnitude charts
- **Slope & bump charts** — rank changes over time, paired slope comparisons, label placement at endpoints, highlighting crossovers, tie handling
- **Marimekko & mosaic** — variable-width bars, two-dimensional proportional area, spine plots, categorical breakdowns with nested proportions
- **Hexbin & 2D density** — hexagonal binning, 2D kernel density estimation, contour plots, bandwidth selection, color vs size encoding, Canvas rendering for large n
- **Tooltip patterns** — positioning with edge-flip, rich HTML tooltips, follow-cursor vs anchor, shared tooltips across linked views, mobile long-press, Voronoi hover regions
- **SVG filters & effects** — drop shadows, glow, blur, morphological operations (`feMorphology`), turbulence textures, displacement maps, performance considerations
- **Comparison charts** — dumbbell/lollipop, Cleveland dot plots, back-to-back bars, tornado/butterfly charts, diverging stacked bars, gap charts
- **Waterfall charts** — running totals, bridge charts, positive/negative contributions, subtotal bars, connecting lines, financial and funnel variants
- **Error & uncertainty** — error bars, confidence intervals, gradient uncertainty bands, fan charts, ensemble spaghetti plots, probability density overlays
- **Stacked area & streamgraph** — stacked area, streamgraph with baseline algorithms (wiggle, silhouette, expand), difference area charts, ThemeRiver, transition between baselines
- **Clip paths & masks** — reveal animations, viewport clipping, shaped masks, gradient masks, animated clip transitions, sparkline-in-shape patterns
- **Progress & gauges** — radial progress arcs, linear progress bars, goal markers, animated fill, donut gauges, bullet-style gauges (extends sparkcharts bullets)
- **Dashboard composition** — CSS grid + D3 coordination, responsive card layout, shared filter controls, coordinated update lifecycle, print-friendly styles
- **Gesture & touch** — pinch-to-zoom, swipe between states, long-press context menus, multi-touch interaction, momentum/inertial pan, touch-friendly hit target sizing
- **Isoline & isoband** — marching squares, filled contour bands, topographic/elevation rendering, weather maps, interpolation from irregular points
- **Proportional symbols** — graduated circles/symbols on maps or scatter, size legends, overlap handling with collision detection, Dorling-style packing layout

### Niche but interesting
- **Audio + data sonification** — Web Audio API mapped to data dimensions, tone/pitch/rhythm encoding, accessibility complement to visual channels
- **3D with WebGPU** — point clouds, 3D scatter, camera orbit controls, D3 scale integration, depth-based LOD, GPU compute for layout
- **Cartograms & distortion** — Dorling cartograms, contiguous cartograms, anamorphic projections, fisheye for focus+context on any layout
- **Animation choreography** — staggered enter sequences, orchestrated multi-chart transitions, scroll-triggered animation timelines, keyframe interpolation
- **Custom curves & shapes** — superformula shapes, custom D3 curve implementations, rounded polygons, smooth closed curves, parametric shapes

---

## Existing Skill Improvements

### shape-morphing
- [ ] Canvas shape morphing — point-array polygon rendering, no SVG path dependency
- [ ] Topology-aware morphing — winding order, hole handling, genus changes (Flubber-style)
- [ ] Combined morph + stagger — morphing shapes with staggered timing per element
- [ ] Performance guidance — sample count tradeoffs, caching strategies for complex paths

### motion
- [ ] Collapse/expand animations — children fade to opacity 0 and converge to parent position, then layout recomputes
- [ ] SVG ↔ Canvas handoff — animate in Canvas then settle into interactive SVG
- [ ] Text morphing — number tickers, interpolating formatted values
- [ ] More morph examples — scatter↔line, grouped↔stacked bar, small multiples↔single
- [ ] Cross-layout chart morphing — coordinating shape-morphing with layout recomputation (bar→pie, scatter→line)
- [ ] Momentum/inertial motion — easing into rest, not just eased transitions

### force
- [ ] Precomputed layout interpolation — distinguish "force as layout engine" (run to convergence, interpolate snapshots) from "force as animation driver" (live simulation)
- [ ] Force-directed label placement — labels that don't overlap, as a custom force or post-simulation pass
- [ ] Multi-layer forces — applying different force sets to different node subsets simultaneously

### hierarchy-layouts
- [ ] Canvas hierarchy rendering — treemap/pack at scale via Canvas (currently SVG-only)
- [ ] Animated layout transitions — complete working code for treemap↔sunburst↔pack with shape morphing
- [ ] Responsive hierarchy sizing — ResizeObserver, reflowing layouts on resize

### brushing
- [ ] Dual-phase highlighting — hover = temporary, click = persistent with context fading
- [ ] Highlight propagation via graph connectivity — `node.descendants()` + connected links
- [ ] Compound selections — union, intersection, difference of multiple brush regions

### parallel-coordinates
- [ ] `d3.curveBundle.beta().context(ctx)` — D3 curve generators on Canvas with tunable tension
- [ ] Statistical overlays — box-and-whisker per axis, density ribbons, confidence bands

### annotation
- [ ] Canvas annotation recipe (skill covers it, example is SVG-only)
- [ ] Leader line variants: straight, elbow, curved in example
- [ ] Force-based label collision avoidance in example

### distributions
- [ ] Standalone density plot / KDE panel (example shows violin but not standalone)
- [ ] QQ plot panel
- [ ] Strip/jitter plot panel

### small-multiples
- [ ] Canvas small multiples example (skill documents it, example is SVG-only)
- [ ] Synchronized cross-panel hover in example
- [ ] Lazy rendering for offscreen panels

### time-series
- [ ] Cycle plot panel in example
- [ ] Gantt chart example (separate file or panel)
- [ ] LTTB downsampling toggle (show raw vs downsampled)
- [ ] Real-time streaming example (separate file, simulated WebSocket)

### linked-views
- [ ] Coordinated zoom example (two time-series sharing x-axis)
- [ ] State serialization (URL encoding of brush/selection state)
- [ ] Undo/redo (StateHistory pattern from skill)

### responsive
- [ ] Print styles in example (@media print)
- [ ] Iframe embedding example (postMessage height negotiation)
- [ ] Touch adaptation demo (pointer-type-aware interactions)

### Cross-skill composition
- [ ] Additional archetype examples — narrative (scrollytelling), spatial explorer (map+linked panels)

---

## Evaluator Suite

- [ ] Review `notes/archive/EVALUATION-LOG.md` holistically — which criteria caught real issues? Which always passed trivially?
- [ ] Tighten or cut criteria that never failed — they're not earning their place
- [ ] Add new criteria discovered via META observations in the evaluation reports
- [ ] Decide if the evaluator is worth running on every sharpening pass, or only on major rewrites

## Test Fixture Ideas
- [ ] Interruption stress test — rapid-fire random clicks, verify no stuck states
- [ ] Large data fixtures — 1K, 10K, 100K rows to catch perf regressions
- [ ] Accessibility audit fixture — keyboard-only navigation, screen reader output capture
- [ ] Mobile viewport fixtures — 375px and 768px width rendering
