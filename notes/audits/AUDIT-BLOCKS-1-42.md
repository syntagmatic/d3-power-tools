# Adversarial Audit: Blocks 1-42

Six adversarial agents reviewed all 42 original blocks. Date: 2026-03-27.

## Score Summary

| Agent | Score | Verdict |
|-------|:-----:|---------|
| Deception Detector | **7.6/10** | Mathematically honest overall. No fabricated correlations, correct zero baselines on bars. Block 14 uses linear radius (should be sqrt), block 38 uses dual-axis without strong justification. |
| Perceptual Red-Team | **6.4/10** | Generally readable. Small-multiples blocks push cognitive limits; some spaghetti risk in force/network blocks. |
| Interaction Stress-Test | **5.6/10** | Un-throttled brush/zoom/pointermove handlers everywhere. No RAF coalescing. Timer races in blocks 7, 25, 32. |
| Metamorphic Tester | **4.8/10** | Widespread hardcoded domains, missing key functions in data joins, append-only rendering with no update path. |
| Robustness Contract | **4.6/10** | No empty-state handling, no NaN guards, no `line.defined()`, no timer cleanup. Synthetic data masks all edge cases. |
| Visual Critic | **4.6/10** | Accessibility is catastrophic. 40/42 blocks have zero ARIA attributes, zero keyboard navigation. Only blocks 9 and 37 have any accessibility. |

**Composite: 5.6/10**

---

## Top Issues (cross-agent)

### 1. Near-zero accessibility (Visual Critic: 4.6)
40 of 42 blocks have no `role`, `aria-label`, `<title>`, `<desc>`, or keyboard navigation on SVG/Canvas elements. Only block 9 (sparkline table) has `role="img"` and `aria-label` on inline SVGs, and block 37 (accessible canvas scatter) has full keyboard nav, `aria-live`, and data table toggle. Every other block is completely invisible to screen readers and unreachable by keyboard.

### 2. Zero defensive coding (Robustness: 4.6)
No block handles empty data, null values, NaN, or Infinity. No `line.defined()` or `area.defined()` anywhere. No `if (!data.length)` guards. Synthetic data generation masks this entirely — every block would break on real-world messy data. Timers (`d3.timer`, `setInterval`, `requestAnimationFrame`) run indefinitely without cleanup in blocks 7, 22, 25, 29, 31, 32, 42.

### 3. Hardcoded scale domains (Metamorphic: 4.8)
Most blocks hardcode scale domains rather than deriving them from data. Worst offenders: block 3 ([0, 120] temperature), block 4 ([12K, 600K] income), block 8 ([0, 60] energy), block 28 ([60, 170] sales), block 34 ([0, 80] bar height). Data outside these ranges would clip silently. Missing key functions in `.data()` joins are pervasive — only blocks 9, 15, 18, 27 use proper key functions.

### 4. Un-throttled interaction handlers (Stress-Test: 5.6)
Brush, zoom, and pointermove handlers fire full re-renders on every event without RAF coalescing, dirty flags, or debouncing. Worst offenders: block 23 re-renders 15K hex bins on every pointermove; block 7 has competing `d3.timer` instances on rapid brush-zoom; block 13 does O(leaves * edges) computation per hover; block 5 does full linear scans of 2000 records per brush event.

### 5. Timer race conditions (Stress-Test + Robustness)
Block 7 creates new `d3.timer` instances without stopping previous ones — rapid brush-zoom creates competing animations. Block 25 has the same issue with projection morphing timers. Block 32's 9 infinite `setTimeout` chains have no cancellation mechanism and break when tabs are backgrounded.

---

## Worst Blocks (by composite score)

| Block | Avg Score | Primary Issues |
|-------|:---------:|----------------|
| **07-density-contour-heatmap** | 4.5 | Timer race on rapid brush-zoom, diverging colormap for density (no midpoint), no ARIA, 8K points redrawn per frame |
| **32-shape-morphing-gallery** | 4.5 | 9 infinite animation loops with no cleanup, no `.interrupt()`, tab backgrounding breaks `setTimeout` chains, index-based treemap-to-pack correspondence |
| **22-rotating-globe** | 4.7 | No legend for continent colors, no timer cleanup, all hardcoded (600x600, scale 270), imperative loop with no data joins |
| **23-hex-bin-map** | 4.8 | Full 15K-point re-render on every pointermove, no throttle, no ARIA, hardcoded 960x600 |
| **29-bar-chart-race** | 4.8 | `setInterval` + transition stacking (no `.interrupt()`), no empty-year guard, `textTween` null risk |
| **02-linked-scatterplot-matrix** | 5.0 | No source guard on dispatch (redundant updates), no key functions, SteelBlue default color, 16 cells pushes cognitive limits |

---

## Best Blocks (by composite score)

| Block | Avg Score | Strengths |
|-------|:---------:|-----------|
| **18-collapsible-tree-search** | 6.7 | Proper key functions (`d => d.id`), handles collapse/expand state correctly, search with path expansion |
| **34-visual-texture-a11y** | 6.5 | Color+pattern dual encoding, CVD simulation, static (no interaction bugs), pedagogically strong |
| **37-accessible-canvas-scatter** | 6.5 | Full keyboard nav, `aria-live`, focus ring, data table toggle, debounced announcements |
| **21-us-choropleth** | 6.3 | Missing-data fallback (`"#ccc"`), key function (`d => d.id`), `viewBox` responsive, D3 zoom integration |
| **31-streaming-realtime-line** | 6.3 | RAF loop (not setInterval), brush source guard, LTTB downsampling, dynamic scale domains |
| **27-swimlane-gantt** | 6.2 | Key functions everywhere (`d => d.id`, `d => d.team`), parameterized render, brush-to-zoom |

---

## Per-Block Scorecard

| # | Block | Visual | Deception | Interact | Percept | Robust | Metamorph | Avg |
|---|-------|:------:|:---------:|:--------:|:-------:|:------:|:---------:|:---:|
| 1 | parallel-coords-sparkline-table | 5 | 7 | 4 | 6 | 4 | 5 | 5.2 |
| 2 | linked-scatterplot-matrix | 4 | 8 | 5 | 5 | 4 | 4 | 5.0 |
| 3 | violin-plot-orchestra | 6 | 7 | 8 | 5 | 5 | 4 | 5.8 |
| 4 | bee-swarm-census | 6 | 7 | 7 | 6 | 5 | 4 | 5.8 |
| 5 | crossfilter-flight-explorer | 4 | 7 | 4 | 7 | 5 | 5 | 5.3 |
| 6 | qq-plot-confidence | 5 | 9 | 7 | 7 | 5 | 3 | 6.0 |
| 7 | density-contour-heatmap | 4 | 6 | 3 | 6 | 3 | 5 | **4.5** |
| 8 | small-multiples-seasonal | 4 | 8 | 5 | 7 | 4 | 4 | 5.3 |
| 9 | sparkline-dashboard-table | 7 | 7 | 5 | 7 | 5 | 5 | 6.0 |
| 10 | strip-plot-marginals | 3 | 8 | 5 | 7 | 4 | 5 | 5.3 |
| 11 | zoomable-treemap | 3 | 8 | 6 | 6 | 5 | 5 | 5.5 |
| 12 | sunburst-icicle-morph | 4 | 8 | 7 | 7 | 5 | 5 | 6.0 |
| 13 | radial-dendrogram-edge-bundling | 3 | 9 | 5 | 6 | 4 | 4 | 5.2 |
| 14 | force-directed-clustering | 3 | 8 | 6 | 6 | 5 | 5 | 5.5 |
| 15 | adjacency-matrix-reorder | 4 | 8 | 5 | 7 | 5 | 6 | 5.8 |
| 16 | sankey-energy-flow | 4 | 8 | 5 | 7 | 4 | 5 | 5.5 |
| 17 | chord-diagram-trade | 4 | 8 | 5 | 6 | 5 | 5 | 5.5 |
| 18 | collapsible-tree-search | 5 | 9 | 6 | 7 | 6 | 7 | **6.7** |
| 19 | circle-packing-zoom | 5 | 8 | 5 | 7 | 5 | 5 | 5.8 |
| 20 | arc-diagram | 4 | 7 | 6 | 6 | 5 | 5 | 5.5 |
| 21 | us-choropleth | 5 | 7 | 7 | 7 | 6 | 6 | 6.3 |
| 22 | rotating-globe | 3 | 7 | 4 | 7 | 4 | 3 | **4.7** |
| 23 | hex-bin-map | 4 | 7 | 3 | 7 | 4 | 4 | **4.8** |
| 24 | flow-map-arrows | 5 | 8 | 5 | 6 | 4 | 5 | 5.5 |
| 25 | projection-morphing | 5 | 8 | 4 | 6 | 4 | 5 | 5.3 |
| 26 | horizon-chart-stack | 5 | 7 | 6 | 5 | 5 | 4 | 5.3 |
| 27 | swimlane-gantt | 6 | 8 | 5 | 6 | 5 | 7 | 6.2 |
| 28 | cycle-plot | 6 | 8 | 8 | 7 | 4 | 3 | 6.0 |
| 29 | bar-chart-race | 3 | 7 | 4 | 6 | 4 | 5 | **4.8** |
| 30 | scrollytelling-climate | 5 | 7 | 5 | 7 | 4 | 5 | 5.5 |
| 31 | streaming-realtime-line | 4 | 8 | 7 | 7 | 5 | 7 | 6.3 |
| 32 | shape-morphing-gallery | 3 | 8 | 4 | 5 | 3 | 4 | **4.5** |
| 33 | annotation-showcase | 6 | 7 | 8 | 6 | 5 | 5 | 6.2 |
| 34 | visual-texture-a11y | 7 | 8 | 8 | 7 | 5 | 4 | 6.5 |
| 35 | color-palette-explorer | 6 | 8 | 6 | 6 | 5 | 5 | 6.0 |
| 36 | responsive-multi-breakpoint | 4 | 8 | 5 | 7 | 4 | 5 | 5.5 |
| 37 | accessible-canvas-scatter | 8 | 7 | 6 | 8 | 5 | 5 | 6.5 |
| 38 | dual-axis-gap-handling | 6 | 5 | 8 | 7 | 4 | 4 | 5.7 |
| 39 | quadtree-hit-detection | 3 | 8 | 7 | 6 | 5 | 5 | 5.7 |
| 40 | minimap-navigator | 4 | 7 | 6 | 7 | 5 | 5 | 5.7 |
| 41 | force-bundling-chord-triptych | 5 | 8 | 6 | 6 | 5 | 6 | 6.0 |
| 42 | phyllotaxis-data-art | 3 | 9 | 6 | 6 | 4 | 5 | 5.5 |

**Column averages:** Visual 4.6 · Deception 7.6 · Interaction 5.6 · Perceptual 6.4 · Robustness 4.6 · Metamorphic 4.8 · **Overall 5.6**

---

## Patterns Worth Fixing

**Quick wins (improve many blocks):**
1. Add `role="img"` + `<title>` + `<desc>` to all SVGs — 40 blocks affected, ~3 lines each
2. Add `.interrupt()` before all transitions in click/brush/toggle handlers — blocks 7, 11, 15, 17, 25, 29, 32, 35
3. Add `line.defined(d => d != null && isFinite(d.value))` to all line/area generators — blocks 8, 26, 28, 30, 31
4. Replace `Math.random()` with seeded PRNG in blocks 13, 38, 40
5. Add `.stop()` to force simulations after convergence — blocks 14, 22

**Systemic (architectural):**
1. Replace hardcoded scale domains with `d3.extent(data, ...)` — blocks 3, 4, 5, 8, 10, 22, 26, 28, 34
2. Add key functions to all `.data()` joins — only 4/42 blocks use them (9, 15, 18, 27)
3. Add RAF coalescing wrapper to all brush/zoom/pointermove handlers — blocks 1, 2, 5, 7, 8, 10, 13, 23, 39
4. Add empty-state guards (`if (!data.length) { showEmptyMessage(); return; }`) as a standard pattern
5. Add timer/interval cleanup on page visibility change or teardown — blocks 7, 22, 25, 29, 31, 32, 42
6. Fix `scaleLinear` on radius to `scaleSqrt` for area-proportional encoding — blocks 14, 20
