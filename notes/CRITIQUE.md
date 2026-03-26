# D3 Power Tools — Critique & Iteration Tracker

Gemini reviewed the skill collection with a focus on production-readiness: accessibility gaps in Canvas/WebGL rendering, data robustness for messy inputs, performance under heavy interaction, and modularity. Claude addressed most critiques directly and pushed back where they conflicted with the project's self-contained HTML constraint.

## Core Architectural Goals

- [x] **A11y-by-Default** — Every Canvas/WebGL skill now cross-references `canvas-accessibility` and `data-table`. `force` has spatial keyboard nav, `aria-live` announcements, and a hybrid Canvas+SVG example. `network` has per-layout ARIA role guidance.

- [ ] ~~**Modularity (ESM)**~~ — Won't do. Separating layout from rendering into ES modules would require a build step, which conflicts with the self-contained HTML constraint. The separation already exists conceptually within each skill.

- [x] **Data Robustness** — `validateHierarchy()` / `cleanHierarchy()` in `skills/hierarchy-layouts/scripts/validate-hierarchy.js`. `validateNetwork()` / `cleanNetwork()` in `skills/network/scripts/validate-network.js`. Both handle cycles, orphans, duplicates, and missing roots.

- [ ] **Performance Throttling** — Partially addressed. `canvas` and `brushing` already document rAF frame budgeting and render queues. A standardized cross-skill scheduler was deemed unnecessary coupling — the skills that hit high element counts already handle it.

- [x] **Off-Main-Thread** — `canvas` covers Web Workers + OffscreenCanvas. `webgl` covers worker-based buffer preparation. `brushing` documents offloading intersection tests to workers for 10K+ rows.

---

## Skill-Specific Critiques

### canvas & webgl
**Gap:** High-performance but "black boxes" for accessibility.
**Fix:** Added Accessibility sections pointing to `canvas-accessibility` and `data-table`.

### force
**Gap:** No accessibility pattern for dynamic force layouts.
**Fix:** Added spatial keyboard nav via quadtree (`scripts/spatial-keyboard-nav.js`), `aria-live` convergence announcements, and a hybrid Canvas+SVG example (`examples/hybrid-canvas-svg.html`). ARIA role corrected from the proposed `role="application"` (which disables screen reader shortcuts) to `role="img"` with `aria-roledescription`.

### network
**Gap:** No ARIA guidance for different graph layouts, no standard data validation step.
**Fix:** Added per-layout ARIA roles (`role="grid"` for adjacency matrix, `role="img"` for arc/force/chord/Sankey). Added "Always validate first" callout linking to `validate-network.js`. Cross-referenced `data-table` for hairball graphs.

### hierarchy-layouts
**Gap:** Assumed clean tree data; failed silently on cycles or missing parents.
**Fix:** Added `validateHierarchy()` covering five failure modes: duplicate IDs, orphans, cycles, multiple roots, no root.

### brushing
**Gap:** SVG-on-Canvas coordination jittery at high element counts.
**Fix:** Added "Performance at Scale" section cross-referencing frame budgeting from `canvas` and `bufferSubData` from `webgl`.

### shape-morphing
**Gap:** Morph engine was code snippets, not a reusable function.
**Fix:** Extracted `morphPaths(selection, targetPathStr, options)` into `scripts/morph-paths.js` with `resamplePath`, `bestRotation`, and `pointsToPath` as composable steps.

---

## Quality Audit (2026-03-23)

Full review of all 27 skills, 40 examples, and 145 tests. Ranked by how much each skill encodes **hard-won insight** vs reorganized API docs.

### Tier 1 — Genuinely hand-crafted
1. **parallel-coordinates** — Color-picking hit detection, opacity scaling, render queue w/ shuffle, Canvas+SVG hybrid. Now also: Inselberg duality reading (crossing patterns → correlation), axis ordering strategies with greedy algorithm, strum brushing geometry. Decision table vs alternatives.
2. **canvas** — 12 real pitfalls. Progressive render queue, DPR, typed arrays, batch-by-style, quadtree rebuild. Now also: OffscreenCanvas worker bridge with zoom message passing, texture atlas for custom markers, GPU escalation decision table (Canvas 2D → OffscreenCanvas → regl → WebGPU).
3. **canvas-accessibility** — Solves a problem most skip. Quadtree directional nav, navigation model taxonomy, announce function, DOM mirror. Now also: system preference queries (prefers-reduced-motion, prefers-contrast, forced-colors), forced-colors gap as hard compliance requirement.
4. **motion** — TransitionManager for mid-flight interruption, FLIP, Canvas timer. Now also: Heer & Robertson perception research (when animation helps vs. small multiples), research-backed duration guidelines, sticky-graphic scrollytelling with scrollama, View Transitions API guidance, CSS scroll-driven animations.
5. **brushing** — Segment intersection geometry, SelectionManager, linked timing, spatial grid indexing. Now also: 8-scenario selection decision table, brush composition (shift+drag multi-region, union/intersect), Falcon prefetch cross-filtering for O(1) brush updates, progressive reservoir-sampled filtering for 50K+ points.
6. **color** — Tol palettes, overdraw alpha solver, Brettel/Viénot CVD simulation, bivariate legends, perception pitfalls, dark mode. Now also: OKLCH palette generation (CSS-native + culori), palette selection decision table (Viridis/Cividis/Tol/ColorBrewer/Crameri), APCA contrast with Lc thresholds for chart elements, Crameri scientific colour maps.

### Tier 2 — Strong domain knowledge
7. **cartography** — Topology operations, bivariate choropleth, bubble maps, hex binning, cartograms, flow maps, geographic labels, Canvas multi-layer, LOD, globe versor. Now also: Snyder's projection selection framework (distortion property → geographic extent → projection family), MapLibre+D3 escalation with geoTransform bridge, PMTiles serverless tiles, dark mode maps (Schiewe 2024).
8. **force** — Verlet internals, custom forces, 5K cliff, hybrid a11y. Now also: three WebWorker patterns (static/progressive/interactive with drag), d3-force-reuse, "Beyond d3-force" decision table (UMAP, ForceAtlas2, WebCola, stress majorization).
9. **distributions** — KDE bandwidth, Tukey fences, QQ. Now also: raincloud plots (half-violin + box + strip), letter-value plots with stopping rule (Hofmann/Wickham/Kafadar 2017), sample-size selection flowchart (5 tiers), defensive KDE (clip to data range). Moved from Tier 3 — the selection guidance and composite chart patterns encode real visualization judgment.
10. **scales** — Time gap via band scale, scale selection. Now also: diverging scale midpoint problem (symmetric vs asymmetric domains), classification scales for choropleths (quantize/quantile/threshold/Jenks decision table + code), the quantile trap warning, scale selection decision framework. Moved from Tier 3 — classification scale guidance is editorial, not API docs.
11. **linked-views** — Bitmap crossfilter, dispatch, shared selection. Now also: Baldonado's four guidelines (parsimony, complementarity, self-evidence, attention), owned-state pattern for 4+ views, scalability ladder (Array.filter → crossfilter → Falcon → Mosaic/DuckDB-WASM), framework decision rule (Vega-Lite/Plot/Mosaic). Moved from Tier 3 — the Baldonado framing and escalation ladder add real architectural judgment.
12. **time-series** — Horizon/cycle plots, streaming. Now also: 9-question chart selection table, prediction bands with graduated opacity, semantic temporal zoom (getTemporalLevel), difference area with two-clip approach. Moved from Tier 3 — the selection table and semantic zoom encode visualization judgment beyond API docs.
13. **annotation** — Now also: highlight-by-desaturation, text hierarchy framework, annotation-as-data (structured JSON with priority filtering), step-sequenced annotations with scrollama, decision flowchart. Moved from Tier 4 — the editorial judgment gap is now addressed (desaturation, text hierarchy, when-to-annotate guidance).
14. **shape-morphing** — Parametric > resampling > topology hierarchy, bestRotation. Now also: library decision tree (d3-interpolate-path → flubber → polymorph → GSAP MorphSVG).
15. **data-gathering** — autoType FIPS pitfall, circular buffer, columnar typed arrays. Now also: "When to Escalate Beyond d3.csv" decision table (DuckDB-WASM, hyparquet, apache-arrow), cancellable loading with AbortController, Arrow BigInt pitfall.
16. **edge-bundling** — LCA paths, Holten reference, layout transitions. Now also: algorithm comparison table (hierarchical vs Edge-Path vs Divided bundling), directional bundling guidance.
17. **webgl** — Full shaders, instanced rendering, color-picking framebuffer, regl recommendation. Now also: WebGPU status and migration decision table (stay WebGL 2 / luma.gl v9 / raw WebGPU).

### Tier 3 — Competent reference
18. **visual-texture** — Patterns, perceptual ranking, SVG filters, Canvas atlas. Now also: Julesz texton theory (scientific foundation for pattern limits), canonical 6-pattern accessible set with texton dimensions, Voronoi stippling guidance, CSS Paint API status. Solid scientific grounding but narrower domain than Tier 2.
19. **responsive** — ResizeObserver, viewBox vs redraw. Now also: container queries for CSS-level adaptation, WCAG 2.2 touch targets (24/44px), prefers-reduced-motion, high-DPI print, decision table. More opinionated than before but still fundamentally web engineering applied to charts.
20. **hierarchy-layouts** — Validation helpers, layout-switcher. Now also: icicle/flame graph/left-to-right partition variants as coordinate remappings, expanded tiling strategy tradeoffs, Marimekko-as-sliceDice.
21. **network** — 5 layouts, decision table, validation. Now also: hive plots (deterministic alternative to force), community detection with graphology + Louvain, scaling path (SVG → Canvas → sigma.js → deck.gl).
22. **hierarchy-interaction** — Zoomable treemap/sunburst/pack. Now also: breadcrumbs as mandatory (not optional), label fitting on zoom, WCAG 2.5.8 touch targets, two-step tap pattern.
23. **navigation** — Geometric vs semantic zoom, minimap. Now also: LOD state machine with hysteresis bands, scroll-driven animations vs d3-zoom clarification, wheel passthrough at zoom limits.

### Tier 4 — Useful but focused
24. **small-multiples** — Shared scales, grid math. Now also: facet wrap recipe with column-count formula, Observable Plot fx/fy note. Core domain is inherently simple.
25. **sparkcharts** — Pattern collection. Now also: KPI card layout recipe, fixed-window vs auto-scaled guidance. Simple domain, well-served.
26. **data-table** — HTML table patterns with D3 joins. Now also: Ctrl+F gotcha in virtual scrolling, buffer rows, pagination decision guidance. Still a merge candidate with canvas-accessibility for a unified "accessible alternatives" skill.

### Most transformative paths
1. ~~**Cross-skill composition guide**~~ — Done. `cross-skill-composition` skill added.
2. ~~**Deepen cartography**~~ — Done. 348→1169 lines. Cartograms, flow maps, hex bins, Canvas architecture, LOD, globe versor.
3. **Voronoi & Delaunay** — Missing interaction infrastructure. Touches parallel-coords, brushing, canvas, force, time-series.
4. ~~**Consolidate thin skills**~~ — Partially done. visual-texture deepened to 615 lines (Tier 3), no longer a merge candidate. data-table→canvas-accessibility still open.
5. ~~**Real data examples**~~ — Partially addressed. `blocks/blockbuilder-explorer.html` loads 34K real blocks from the Blockbuilder dataset. Still only 1 of 48 blocks uses real data.
6. **Live streaming skill** — time-series covers theory; a working WebSocket example fills a real production gap.

### Gaps identified from Blockbuilder data (2026-03-25)

Analysis of 34,196 real D3 blocks from Blockbuilder Search reveals which D3 modules practitioners actually use vs. what the skills cover. See `blocks/blockbuilder-explorer.html` for the interactive analysis.

**Coverage gaps ranked by real-world usage:**

1. **d3-selection** — In 95% of blocks, no dedicated skill. `.join()`, enter/update/exit, nested selections, `.each()`, `.call()`, data key functions are foundational knowledge that every other skill assumes. Currently re-taught piecemeal across skills. A focused selection skill could be "the first skill you read."
2. **d3-shape** — `d3.line` (8%), `d3.arc` (3.6%), `d3.area`, `d3.pie`, `d3.stack` collectively in ~13% of blocks. No dedicated skill. Partially scattered across `time-series` (line/area), `hierarchy-layouts` (arc/pie), `distributions` (stack). Generators, curves, custom symbols, and the shape API surface deserve consolidation.
3. **d3-drag** — In 4% of blocks (more than brush or zoom). No dedicated skill. Shows up in force layouts, custom sliders, annotation repositioning, sortable lists. `force` mentions it but general patterns (constrained drag, drag data binding, snap) aren't captured.
4. **d3-transition** — In 3% of blocks explicitly. `motion` covers animation philosophy but the bread-and-butter `.transition().duration().ease()` patterns, interruption semantics, and named transition collision are buried.

**Module usage vs. skill depth alignment:**
- d3-geo (8% of blocks) has the deepest skill (1169 lines) — proportionally over-served but the depth is warranted by complexity.
- d3-force (4.6% of blocks) has good coverage — appropriate.
- d3-hierarchy (1800 uses) has two skills — appropriate for the interaction complexity.
- d3-brush (339 uses, 1% of blocks) has its own skill — low usage but high value for exploratory tools.

**V3→V7 migration reality:** ~40% of blocks use v3 API (`d3.scale.linear`, `d3.svg.axis`, `d3.layout.force`). The skills correctly target v7 only, but this means the skills don't help people migrating old blocks — a potential "migration recipes" appendix could address this.

---

## Iteration Log

### 2026-03-21 — Visual Bug Fixes
- **Layout Switcher:** Fixed position jump in arc↔non-arc transitions, restored label visibility.
- **Canvas Rendering:** Fixed density map clipping, added transparent background.
- **Edge Bundling:** Added treemap context rectangles, fixed radial labels.
- Updated SKILL.md files for Canvas, Layouts, and Bundling with these patterns.

### 2026-03-25 — Blockbuilder Explorer & Coverage Analysis
- **Blockbuilder explorer:** `blocks/blockbuilder-explorer.html` — 4-view linked explorer (timeline, force network, color scatter, block list) of 34K real D3 blocks from Blockbuilder Search Data. Loads blocks-api.json (10MB) + blocks-colors.json (12MB). Exercises linked-views, force, canvas, color, time-series, and data-gathering skills simultaneously.
- **Coverage gap analysis:** Compared API function usage across 34K blocks against skill coverage. Identified 3 high-priority missing skills: selections (95% of blocks), shapes (13%), drag (4%). Updated IDEAS.md with data-informed prioritization.
- **First real-data block:** All previous blocks use synthetic data. This is the first to load and explore a real external dataset.

### 2026-03-26 — Research-Driven Expansion (Philosophy Pass 2)
- **All 26 skills research-expanded** with alternatives, decision guidance, and field references. Pre-gathered research in `notes/research/` compressed into judgment-first additions.
- **Priority 1–3 skills** (color, distributions, network, data-gathering, force, cartography, time-series, linked-views, annotation, canvas, hierarchy-layouts, brushing, scales, visual-texture, motion) received 18-30% growth with new sections, decision tables, and cross-references.
- **Priority 4 skills** (parallel-coordinates, responsive, small-multiples, sparkcharts, data-table, navigation, webgl, canvas-accessibility, edge-bundling, shape-morphing, hierarchy-interaction) received 6-13% targeted additions.
- **4 skills promoted**: distributions and scales (Tier 3→2), annotation (Tier 4→2), time-series (Tier 3→2), linked-views (Tier 3→2). Promotions driven by added decision guidance that moved skills from "API reference" to "editorial judgment."
- **Cross-reference audit**: Fixed 3 stale directory names in CLAUDE.md and 6 cross-reference mismatches across skills.
- **158/158 tests pass** after expansion.
- **Total: 8,744 lines across 26 skills** (up from ~7,200 pre-expansion).

### 2026-03-21 → 2026-03-23 — Skill Expansion & Infrastructure
- **3 new skills:** `annotation` (768 lines), `distributions` (855 lines), `small-multiples` (642 lines). All three were high/medium priority items from IDEAS.md.
- **Block generator:** 32 animated D3 compositions in `blocks/generator.html` — demonstrates cross-skill composition at scale.
- **Sparkcharts enhancement:** Shared scales and number columns for sparkcharts in tables.
- **Repo reorganization:** `proofs/` → `blocks/`, `docs/` → `notes/`, test fixtures moved into `skills/*/examples/` for self-contained distribution.
- **Zoom-and-pan compression** and simplify/check skill tooling improvements.
- **Collection now at 24 skills** (up from initial 20).
