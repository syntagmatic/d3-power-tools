# D3 Power Tools — Critique & Iteration Tracker

Gemini reviewed the skill collection with a focus on production-readiness: accessibility gaps in Canvas/WebGL rendering, data robustness for messy inputs, performance under heavy interaction, and modularity. Claude addressed most critiques directly and pushed back where they conflicted with the project's self-contained HTML constraint.

## Core Architectural Goals

- [x] **A11y-by-Default** — Every Canvas/WebGL skill now cross-references `canvas-accessibility` and `data-table`. `force-simulation` has spatial keyboard nav, `aria-live` announcements, and a hybrid Canvas+SVG example. `network-visualization` has per-layout ARIA role guidance.

- [ ] ~~**Modularity (ESM)**~~ — Won't do. Separating layout from rendering into ES modules would require a build step, which conflicts with the self-contained HTML constraint. The separation already exists conceptually within each skill.

- [x] **Data Robustness** — `validateHierarchy()` / `cleanHierarchy()` in `skills/hierarchy-layouts/scripts/validate-hierarchy.js`. `validateNetwork()` / `cleanNetwork()` in `skills/network-visualization/scripts/validate-network.js`. Both handle cycles, orphans, duplicates, and missing roots.

- [ ] **Performance Throttling** — Partially addressed. `canvas` and `brushing` already document rAF frame budgeting and render queues. A standardized cross-skill scheduler was deemed unnecessary coupling — the skills that hit high element counts already handle it.

- [x] **Off-Main-Thread** — `canvas` covers Web Workers + OffscreenCanvas. `webgl-rendering` covers worker-based buffer preparation. `brushing` documents offloading intersection tests to workers for 10K+ rows.

---

## Skill-Specific Critiques

### canvas & webgl-rendering
**Gap:** High-performance but "black boxes" for accessibility.
**Fix:** Added Accessibility sections pointing to `canvas-accessibility` and `data-table`.

### force-simulation
**Gap:** No accessibility pattern for dynamic force layouts.
**Fix:** Added spatial keyboard nav via quadtree (`scripts/spatial-keyboard-nav.js`), `aria-live` convergence announcements, and a hybrid Canvas+SVG example (`examples/hybrid-canvas-svg.html`). ARIA role corrected from the proposed `role="application"` (which disables screen reader shortcuts) to `role="img"` with `aria-roledescription`.

### network-visualization
**Gap:** No ARIA guidance for different graph layouts, no standard data validation step.
**Fix:** Added per-layout ARIA roles (`role="grid"` for adjacency matrix, `role="img"` for arc/force/chord/Sankey). Added "Always validate first" callout linking to `validate-network.js`. Cross-referenced `data-table` for hairball graphs.

### hierarchy-layouts
**Gap:** Assumed clean tree data; failed silently on cycles or missing parents.
**Fix:** Added `validateHierarchy()` covering five failure modes: duplicate IDs, orphans, cycles, multiple roots, no root.

### brushing
**Gap:** SVG-on-Canvas coordination jittery at high element counts.
**Fix:** Added "Performance at Scale" section cross-referencing frame budgeting from `canvas` and `bufferSubData` from `webgl-rendering`.

### shape-morphing
**Gap:** Morph engine was code snippets, not a reusable function.
**Fix:** Extracted `morphPaths(selection, targetPathStr, options)` into `scripts/morph-paths.js` with `resamplePath`, `bestRotation`, and `pointsToPath` as composable steps.

---

## Quality Audit (2026-03-23)

Full review of all 27 skills, 40 examples, and 145 tests. Ranked by how much each skill encodes **hard-won insight** vs reorganized API docs.

### Tier 1 — Genuinely hand-crafted
1. **parallel-coordinates** — Color-picking hit detection, opacity scaling formula, render queue w/ shuffle, Canvas+SVG hybrid. Feels built from real parcoords work.
2. **canvas** — 12 real pitfalls. Progressive render queue, DPR as systematic concern, typed array layouts, batch-by-style, quadtree rebuild timing.
3. **canvas-accessibility** — Solves a problem most skip. Quadtree directional nav with 90° cone, navigation model taxonomy, announce function with field config, DOM mirror.
4. **motion** — TransitionManager for mid-flight interruption. Named transition collision semantics, FLIP, Canvas timer with background-tab fallback.
5. **brushing** — Segment intersection geometry, SelectionManager on EventTarget, "all selected if empty" semantics, 80ms+easeExpOut linked timing, spatial grid indexing.
6. **color** — Tol palettes with bad-color per scheme, overdraw alpha formula+solver, Brettel/Viénot simulation matrices, bivariate legend recipes. Now also: color perception (simultaneous contrast, small-area, Mach bands), scale design principles (sequential lightness, diverging symmetry), dark mode HCL adaptation, wide gamut, masking compositing, auto text color. 375→736 lines.

### Tier 2 — Strong domain knowledge
7. **cartography** — Expanded from 348→1169 lines. Topology operations (merge/dissolve/neighbors), bivariate choropleth, bubble maps with force-collision, hex binning, cartograms (non-contiguous, Dorling), flow maps (great-circle, curved, animated), geographic label placement (polylabel, collision), Canvas multi-layer architecture with color-pick hit detection and frame budgeting, large geometry/LOD, globe versor rotation with back-face, projection transitions. 14 pitfalls. Moved from Tier 4 #27.
8. **force-simulation** — Verlet internals, custom force recipes, 5K performance cliff, hybrid a11y example.
9. **shape-morphing** — Parametric > resampling > topology hierarchy. bestRotation, stash on DOM element not datum.
10. **data-gathering** — autoType FIPS pitfall, circular buffer, columnar typed arrays, pre-computed sort indices.
11. **hierarchy-edge-bundling** — LCA paths, Holten reference, data-space interpolation for layout transitions. Niche but thorough.
12. **webgl-rendering** — Breaks the boilerplate wall. Full shader code, instanced rendering, color-picking framebuffer, honest regl recommendation.

### Tier 3 — Competent reference
13. **navigation** — Geometric vs semantic distinction, minimap, linked-zoom loop prevention. Solid but mostly API docs.
14. **network-visualization** — 5 layouts in 532 lines = breadth over depth. Decision table and validation scripts are strong.
15. **visual-texture** — Expanded from 262→615 lines. Now includes diamond/triangle/zigzag patterns, perceptual distinctiveness ranking, SVG filter textures (feTurbulence, halftone), Canvas pattern atlas, accessible choropleth patterns, pattern+color compositing. 12 pitfalls. Moved from Tier 4 #25.
16. **hierarchy-layouts** — Good validation helpers, layout-switcher example. "Which layout for which insight" deserves more than a table.
17. **hierarchy-interaction** — Well-executed standard patterns (zoomable treemap/sunburst/pack). Observable notebook translations.
18. **linked-views** — Bitmap crossfilter is useful. Core patterns (dispatch, shared selection) are standard.
19. **distributions** — Deep stats (KDE bandwidth, Tukey fences, QQ). Reads like a textbook adapted for D3, not visualization wisdom.
20. **time-series** — 847 lines. Horizon/cycle plot sections are interesting; date parsing and time scale sections are well-covered elsewhere.
21. **axes-and-scales** — D3 API organized well. Time gap via band scale is the most interesting pattern.

### Tier 4 — Useful but thin
22. **annotation** — 769 lines, encyclopedic. Hard part (editorial judgment) untouched.
23. **responsive** — Standard web engineering applied to D3. 628 lines for "use ResizeObserver."
24. **small-multiples** — Core insight (shared scales) is one section. Rest is grid math.
25. **sparkcharts** — Nice pattern collection, fundamentally simple domain.
26. **data-table** — HTML table patterns with D3 joins. Merge candidate with canvas-accessibility.

### Most transformative paths
1. ~~**Cross-skill composition guide**~~ — Done. `cross-skill-composition` skill added.
2. ~~**Deepen cartography**~~ — Done. 348→1169 lines. Cartograms, flow maps, hex bins, Canvas architecture, LOD, globe versor.
3. **Voronoi & Delaunay** — Missing interaction infrastructure. Touches parallel-coords, brushing, canvas, force, time-series.
4. ~~**Consolidate thin skills**~~ — Partially done. visual-texture deepened to 615 lines (Tier 3), no longer a merge candidate. data-table→canvas-accessibility still open.
5. **Real data examples** — 38/40 examples use synthetic data. Real messy data would ground the collection.
6. **Live streaming skill** — time-series covers theory; a working WebSocket example fills a real production gap.

---

## Iteration Log

### 2026-03-21 — Visual Bug Fixes
- **Layout Switcher:** Fixed position jump in arc↔non-arc transitions, restored label visibility.
- **Canvas Rendering:** Fixed density map clipping, added transparent background.
- **Edge Bundling:** Added treemap context rectangles, fixed radial labels.
- Updated SKILL.md files for Canvas, Layouts, and Bundling with these patterns.

### 2026-03-21 → 2026-03-23 — Skill Expansion & Infrastructure
- **3 new skills:** `annotation` (768 lines), `distributions` (855 lines), `small-multiples` (642 lines). All three were high/medium priority items from IDEAS.md.
- **Block generator:** 32 animated D3 compositions in `blocks/generator.html` — demonstrates cross-skill composition at scale.
- **Sparkcharts enhancement:** Shared scales and number columns for sparkcharts in tables.
- **Repo reorganization:** `proofs/` → `blocks/`, `docs/` → `notes/`, test fixtures moved into `skills/*/examples/` for self-contained distribution.
- **Zoom-and-pan compression** and simplify/check skill tooling improvements.
- **Collection now at 24 skills** (up from initial 20).
