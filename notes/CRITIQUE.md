# D3 Power Tools — Critique & Iteration Tracker

Gemini reviewed the skill collection with a focus on production-readiness: accessibility gaps in Canvas/WebGL rendering, data robustness for messy inputs, performance under heavy interaction, and modularity. Claude addressed most critiques directly and pushed back where they conflicted with the project's self-contained HTML constraint.

## Core Architectural Goals

- [x] **A11y-by-Default** — Every Canvas/WebGL skill now cross-references `canvas-accessibility` and `fallback-table`. `force-simulation` has spatial keyboard nav, `aria-live` announcements, and a hybrid Canvas+SVG example. `network-visualization` has per-layout ARIA role guidance.

- [ ] ~~**Modularity (ESM)**~~ — Won't do. Separating layout from rendering into ES modules would require a build step, which conflicts with the self-contained HTML constraint. The separation already exists conceptually within each skill.

- [x] **Data Robustness** — `validateHierarchy()` / `cleanHierarchy()` in `skills/hierarchy-layouts/scripts/validate-hierarchy.js`. `validateNetwork()` / `cleanNetwork()` in `skills/network-visualization/scripts/validate-network.js`. Both handle cycles, orphans, duplicates, and missing roots.

- [ ] **Performance Throttling** — Partially addressed. `canvas-rendering` and `brushing-and-selection` already document rAF frame budgeting and render queues. A standardized cross-skill scheduler was deemed unnecessary coupling — the skills that hit high element counts already handle it.

- [x] **Off-Main-Thread** — `canvas-rendering` covers Web Workers + OffscreenCanvas. `webgl-rendering` covers worker-based buffer preparation. `brushing-and-selection` documents offloading intersection tests to workers for 10K+ rows.

---

## Skill-Specific Critiques

### canvas-rendering & webgl-rendering
**Gap:** High-performance but "black boxes" for accessibility.
**Fix:** Added Accessibility sections pointing to `canvas-accessibility` and `fallback-table`.

### force-simulation
**Gap:** No accessibility pattern for dynamic force layouts.
**Fix:** Added spatial keyboard nav via quadtree (`scripts/spatial-keyboard-nav.js`), `aria-live` convergence announcements, and a hybrid Canvas+SVG example (`examples/hybrid-canvas-svg.html`). ARIA role corrected from the proposed `role="application"` (which disables screen reader shortcuts) to `role="img"` with `aria-roledescription`.

### network-visualization
**Gap:** No ARIA guidance for different graph layouts, no standard data validation step.
**Fix:** Added per-layout ARIA roles (`role="grid"` for adjacency matrix, `role="img"` for arc/force/chord/Sankey). Added "Always validate first" callout linking to `validate-network.js`. Cross-referenced `fallback-table` for hairball graphs.

### hierarchy-layouts
**Gap:** Assumed clean tree data; failed silently on cycles or missing parents.
**Fix:** Added `validateHierarchy()` covering five failure modes: duplicate IDs, orphans, cycles, multiple roots, no root.

### brushing-and-selection
**Gap:** SVG-on-Canvas coordination jittery at high element counts.
**Fix:** Added "Performance at Scale" section cross-referencing frame budgeting from `canvas-rendering` and `bufferSubData` from `webgl-rendering`.

### shape-morphing
**Gap:** Morph engine was code snippets, not a reusable function.
**Fix:** Extracted `morphPaths(selection, targetPathStr, options)` into `scripts/morph-paths.js` with `resamplePath`, `bestRotation`, and `pointsToPath` as composable steps.

---

## Iteration Log

### 2026-03-21 — Visual Bug Fixes
- **Layout Switcher:** Fixed position jump in arc↔non-arc transitions, restored label visibility.
- **Canvas Rendering:** Fixed density map clipping, added transparent background.
- **Edge Bundling:** Added treemap context rectangles, fixed radial labels.
- Updated SKILL.md files for Canvas, Layouts, and Bundling with these patterns.

### 2026-03-21 → 2026-03-23 — Skill Expansion & Infrastructure
- **3 new skills:** `annotations-and-labels` (768 lines), `statistical-charts` (855 lines), `small-multiples` (642 lines). All three were high/medium priority items from IDEAS.md.
- **Color themes skill:** `color-themes` (664 lines) with shared theme system (`style/d3-power-tools.css`), light/dark mode switcher, FOWT prevention, CSS custom properties.
- **Block generator:** 32 animated D3 compositions in `blocks/generator.html` — demonstrates cross-skill composition at scale.
- **Sparkcharts enhancement:** Shared scales and number columns for sparkcharts in tables.
- **Repo reorganization:** `proofs/` → `blocks/`, `docs/` → `notes/`, test fixtures moved into `skills/*/examples/` for self-contained distribution.
- **Zoom-and-pan compression** and simplify/check skill tooling improvements.
- **Collection now at 24 skills** (up from initial 20).
