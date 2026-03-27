# Adversarial Audit — All 84 Blocks

Audited 2026-03-27. Each block evaluated through 5 adversarial lenses with screenshot review for visual and perceptual dimensions.

## Score Summary

| Agent | Avg Score | Verdict |
|-------|:---------:|---------|
| **Visual Critic** | 7.20 | Most blocks are competently designed; a handful are publication-quality, none are broken |
| **Deception Detector** | 8.12 | Structurally honest across the board; synthetic data limits real deception risk |
| **Interaction Stress-Test** | 6.38 | Weakest dimension — un-throttled handlers and missing .interrupt() are endemic |
| **Perceptual Red-Team** | 6.73 | Generally readable; network/parcoords blocks push cognitive limits |
| **Metamorphic Tester** | 6.82 | Hardcoded domains are common but acceptable for demo blocks; key functions used where needed |
| **Overall** | **7.05** | Solid portfolio with a clear systemic weakness in interaction robustness |

## Top Issues

Ranked by severity and frequency across all agents.

1. **Un-throttled brush/zoom handlers** (Interaction, ~30 blocks) — Most interactive blocks fire full re-renders on every `mousemove`/`pointermove` without `requestAnimationFrame` coalescing or dirty-flag patterns. Worst offenders: 07, 23, 31, 55, 56, 59, 61, 63, 77.

2. **Missing `.interrupt()` before transitions** (Interaction, ~20 blocks) — Rapid clicks or brush drags during in-flight transitions cause jumping/NaN. Affects: 11, 17, 25, 29, 32, 35, 36, 45, 49, 62, 70, 77, 78.

3. **Hardcoded scale domains** (Metamorphic, ~15 blocks) — Domains like `[0, 100]` or `[60, 170]` work for the synthetic data but won't adapt. Affects: 28, 30, 76, 80 and others. Code quality issue, not correctness bug.

4. **Network/edge density overwhelming** (Perceptual, ~8 blocks) — Edge bundles at low beta, force layouts with high connectivity, or parallel coordinates at low alpha create visual noise. Worst: 39, 47, 64, 67, 71, 78.

5. **Dual-axis deception risk** (Deception, 1 block) — Block 38 uses dual-axis with conflated temperature/rainfall scales. Well-executed but inherently misleading.

6. **Timer/animation lifecycle leaks** (Interaction, ~5 blocks) — `d3.timer` or `setInterval` loops that never stop: 29, 42, 56, 67, 72.

## Worst Blocks

No blocks scored below 5.0 composite. Blocks below 6.0:

| # | Block | Avg | Primary Issue |
|---|-------|:---:|---------------|
| 21 | us-choropleth | 5.8 | Simplified geometry makes states look like crude rectangles; low visual impact |
| 39 | quadtree-hit-detection | 5.8 | 5000 uniform random points are near-invisible confetti; no visual structure to perceive |
| 78 | expandable-edge-bundle | 5.6 | Cluttered edges at low beta; full SVG redraws on every expand/collapse without transition |

## Best Blocks

Composite score > 7.5:

| # | Block | Avg | Strength |
|---|-------|:---:|----------|
| 06 | qq-plot-confidence | 8.2 | Publication-quality with inset histogram, confidence bands, annotation; statistically rigorous |
| 53 | textured-raincloud | 8.0 | Proper Silverman KDE, correct box-plot math, CVD simulation toggle; exemplary |
| 69 | prediction-band-timeseries | 8.0 | Fan chart with widening confidence bands, zero-anchored bridge, honest axes |
| 26 | horizon-chart-stack | 7.8 | Excellent 3-band folding with correlated spikes visible across servers |
| 50 | stippled-density-map | 7.8 | Elegant print-friendly stipple with proportional encoding; honest 1-dot-per-10K |
| 81 | letter-value-table-toggle | 7.8 | Publication-quality LV plot with forced-colors hatching; correct quantile math |
| 84 | sparkline-embed-text | 7.8 | Tufte-style inline sparklines in narrative prose; exemplary data-text integration |
| 02 | linked-scatterplot-matrix | 7.6 | Polished SPLOM with KDE diagonals and cross-cell brushing |
| 10 | strip-plot-marginals | 7.6 | Regression with R-squared, marginal box plots update on brush |
| 15 | adjacency-matrix-reorder | 7.6 | Excellent information density with degree sidebar and legends |
| 18 | collapsible-tree-search | 7.6 | Search expands ancestors and highlights path; proper key functions throughout |
| 24 | flow-map-arrows | 7.6 | Animated dashed arrows with scaleSqrt; rich tooltip with inflow/outflow breakdown |
| 28 | cycle-plot | 7.6 | Clear seasonal pattern, holiday bracket annotation, shared y-axis |
| 33 | annotation-showcase | 7.6 | Force-based label placement, elbow leaders, threshold bands, trend line |
| 34 | visual-texture-a11y | 7.6 | Effective dual-encoding with deuteranopia simulation; zero-baseline bars |
| 43 | classification-choropleth | 7.6 | Pedagogically excellent — exposes classification bias; Jenks implementation correct |
| 57 | webgl-streaming-particles | 7.6 | Beautiful flow field with trail-fade; dt clamped to prevent spiral on tab-switch |
| 58 | webgl-density-heatmap | 7.6 | Semantic zoom with hysteresis band; sqrt perceptual scaling on color ramp |
| 68 | animated-sparkline-table | 7.6 | Publication-quality dashboard with KPI cards, 4 sparkline types, staggered animation |

## Per-Block Scorecard

| # | Block | Visual | Deception | Interact | Percept | Metamorph | Avg |
|---|-------|:------:|:---------:|:--------:|:-------:|:---------:|:---:|
| 01 | parallel-coords-sparkline-table | 7 | 8 | 6 | 6 | 7 | 6.8 |
| 02 | linked-scatterplot-matrix | 8 | 9 | 7 | 7 | 7 | 7.6 |
| 03 | violin-plot-orchestra | 7 | 8 | 7 | 5 | 8 | 7.0 |
| 04 | bee-swarm-census | 8 | 8 | 7 | 7 | 6 | 7.2 |
| 05 | crossfilter-flight-explorer | 7 | 7 | 6 | 7 | 7 | 6.8 |
| 06 | qq-plot-confidence | 9 | 9 | 7 | 8 | 8 | 8.2 |
| 07 | density-contour-heatmap | 7 | 8 | 5 | 7 | 7 | 6.8 |
| 08 | small-multiples-seasonal | 7 | 8 | 7 | 7 | 7 | 7.2 |
| 09 | sparkline-dashboard-table | 8 | 7 | 7 | 7 | 6 | 7.0 |
| 10 | strip-plot-marginals | 8 | 9 | 6 | 8 | 7 | 7.6 |
| 11 | zoomable-treemap | 7 | 8 | 6 | 6 | 6 | 6.6 |
| 12 | sunburst-icicle-morph | 8 | 8 | 7 | 6 | 7 | 7.2 |
| 13 | radial-dendrogram-edge-bundling | 7 | 9 | 6 | 6 | 7 | 7.0 |
| 14 | force-directed-clustering | 7 | 8 | 7 | 7 | 7 | 7.2 |
| 15 | adjacency-matrix-reorder | 8 | 9 | 7 | 7 | 7 | 7.6 |
| 16 | sankey-energy-flow | 8 | 8 | 6 | 7 | 8 | 7.4 |
| 17 | chord-diagram-trade | 7 | 9 | 6 | 6 | 7 | 7.0 |
| 18 | collapsible-tree-search | 7 | 9 | 7 | 7 | 8 | 7.6 |
| 19 | circle-packing-zoom | 8 | 8 | 7 | 7 | 7 | 7.4 |
| 20 | arc-diagram | 7 | 7 | 7 | 6 | 6 | 6.6 |
| 21 | us-choropleth | 5 | 6 | 7 | 5 | 6 | 5.8 |
| 22 | rotating-globe | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 23 | hex-bin-map | 7 | 8 | 5 | 7 | 7 | 6.8 |
| 24 | flow-map-arrows | 8 | 8 | 7 | 7 | 8 | 7.6 |
| 25 | projection-morphing | 5 | 8 | 6 | 6 | 6 | 6.2 |
| 26 | horizon-chart-stack | 8 | 9 | 7 | 8 | 7 | 7.8 |
| 27 | swimlane-gantt | 7 | 9 | 6 | 6 | 8 | 7.2 |
| 28 | cycle-plot | 8 | 8 | 7 | 8 | 7 | 7.6 |
| 29 | bar-chart-race | 7 | 8 | 5 | 7 | 6 | 6.6 |
| 30 | scrollytelling-climate | 7 | 9 | 7 | 7 | 6 | 7.2 |
| 31 | streaming-realtime-line | 7 | 8 | 5 | 7 | 7 | 6.8 |
| 32 | shape-morphing-gallery | 6 | 8 | 6 | 5 | 6 | 6.2 |
| 33 | annotation-showcase | 8 | 8 | 7 | 8 | 7 | 7.6 |
| 34 | visual-texture-a11y | 8 | 9 | 7 | 7 | 7 | 7.6 |
| 35 | color-palette-explorer | 7 | 8 | 7 | 6 | 7 | 7.0 |
| 36 | responsive-multi-breakpoint | 7 | 8 | 6 | 7 | 8 | 7.2 |
| 37 | accessible-canvas-scatter | 6 | 7 | 7 | 6 | 6 | 6.4 |
| 38 | dual-axis-gap-handling | 7 | 5 | 7 | 6 | 7 | 6.4 |
| 39 | quadtree-hit-detection | 5 | 8 | 6 | 4 | 6 | 5.8 |
| 40 | minimap-navigator | 7 | 9 | 6 | 7 | 7 | 7.2 |
| 41 | force-bundling-chord-triptych | 8 | 8 | 7 | 7 | 7 | 7.4 |
| 42 | phyllotaxis-data-art | 8 | 9 | 6 | 7 | 7 | 7.4 |
| 43 | classification-choropleth | 8 | 9 | 7 | 7 | 7 | 7.6 |
| 44 | diverging-midpoint-heatmap | 7 | 9 | 7 | 6 | 7 | 7.2 |
| 45 | log-scale-bee-swarm | 7 | 8 | 5 | 6 | 5 | 6.2 |
| 46 | threshold-scale-dashboard | 7 | 8 | 7 | 8 | 7 | 7.4 |
| 47 | mixed-scale-parcoords | 7 | 8 | 7 | 5 | 7 | 6.8 |
| 48 | scale-perception-network | 7 | 9 | 6 | 6 | 6 | 6.8 |
| 49 | textured-network-diagram | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 50 | stippled-density-map | 8 | 9 | 7 | 8 | 7 | 7.8 |
| 51 | accessible-force-network | 7 | 8 | 7 | 7 | 7 | 7.2 |
| 52 | accessible-choropleth | 7 | 7 | 7 | 7 | 7 | 7.0 |
| 53 | textured-raincloud | 8 | 9 | 7 | 8 | 8 | 8.0 |
| 54 | textured-treemap | 7 | 8 | 6 | 6 | 7 | 6.8 |
| 55 | webgl-million-scatter | 7 | 8 | 6 | 7 | 6 | 6.8 |
| 56 | webgl-force-galaxy | 7 | 8 | 5 | 7 | 6 | 6.6 |
| 57 | webgl-streaming-particles | 8 | 8 | 7 | 8 | 7 | 7.6 |
| 58 | webgl-density-heatmap | 8 | 8 | 7 | 8 | 7 | 7.6 |
| 59 | webgl-edge-bundling | 8 | 8 | 5 | 7 | 7 | 7.0 |
| 60 | webgl-animated-treemap | 7 | 8 | 6 | 6 | 7 | 6.8 |
| 61 | progressive-crossfilter | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 62 | icicle-brush-explorer | 7 | 8 | 6 | 7 | 6 | 6.8 |
| 63 | semantic-zoom-distributions | 7 | 9 | 5 | 8 | 6 | 7.0 |
| 64 | strum-brush-parcoords | 6 | 8 | 6 | 5 | 7 | 6.4 |
| 65 | brush-compose-scatter | 7 | 8 | 7 | 7 | 7 | 7.2 |
| 66 | falcon-histogram | 7 | 8 | 7 | 7 | 8 | 7.4 |
| 67 | temporal-edge-bundling | 7 | 9 | 6 | 6 | 7 | 7.0 |
| 68 | animated-sparkline-table | 8 | 8 | 7 | 8 | 7 | 7.6 |
| 69 | prediction-band-timeseries | 8 | 9 | 7 | 8 | 8 | 8.0 |
| 70 | gantt-edge-bundle | 7 | 8 | 6 | 6 | 6 | 6.6 |
| 71 | small-multiples-force | 6 | 8 | 5 | 5 | 6 | 6.0 |
| 72 | scrollytelling-network | 7 | 9 | 6 | 7 | 7 | 7.2 |
| 73 | hierarchy-data-table | 7 | 8 | 6 | 7 | 6 | 6.8 |
| 74 | marimekko-chart | 8 | 7 | 7 | 8 | 7 | 7.4 |
| 75 | flame-chart-profile | 6 | 8 | 7 | 5 | 7 | 6.6 |
| 76 | treemap-sparkline-dashboard | 8 | 8 | 6 | 7 | 7 | 7.2 |
| 77 | sunburst-breadcrumb-brush | 7 | 8 | 5 | 6 | 6 | 6.4 |
| 78 | expandable-edge-bundle | 5 | 8 | 5 | 4 | 6 | 5.6 |
| 79 | reduced-motion-dashboard | 7 | 7 | 6 | 6 | 7 | 6.6 |
| 80 | container-query-chart | 8 | 8 | 7 | 8 | 6 | 7.4 |
| 81 | letter-value-table-toggle | 8 | 9 | 7 | 8 | 7 | 7.8 |
| 82 | hive-plot-accessible | 7 | 8 | 7 | 6 | 7 | 7.0 |
| 83 | community-detection-table | 7 | 7 | 6 | 7 | 6 | 6.6 |
| 84 | sparkline-embed-text | 8 | 8 | 7 | 9 | 7 | 7.8 |
| | **Column Average** | **7.20** | **8.12** | **6.38** | **6.73** | **6.82** | **7.05** |

## Patterns Worth Fixing

### Quick Wins (high impact, mechanical fixes)

1. **Add RAF coalescing to brush/zoom handlers.** A 5-line wrapper (`let dirty = false; brush.on("brush", () => { dirty = true; }); d3.timer(() => { if (dirty) { dirty = false; render(); } })`) would fix the most common interaction issue across ~30 blocks.

2. **Add `.interrupt()` before transitions.** One line (`selection.interrupt()`) before each `.transition()` call prevents the stacking/jumping bug in ~20 blocks.

3. **Stop timers when paused/hidden.** Blocks 42 (phyllotaxis), 56 (webgl-force-galaxy), 72 (scrollytelling-network) run animation loops even when paused or off-screen. Check `document.hidden` or stop the timer.

### Systemic Issues (require design decisions)

4. **Block 21 (us-choropleth) needs real geometry.** The simplified polygons make it look broken. Either use proper TopoJSON or acknowledge it's a schematic.

5. **Block 39 (quadtree-hit-detection) needs visual structure.** 5000 uniform random points don't demonstrate anything. Use clustered data so the quadtree visualization is meaningful.

6. **Block 78 (expandable-edge-bundle) needs higher beta.** The 0.15 tension barely bundles edges, defeating the purpose. Raise to 0.65+ or add a tension slider.

7. **Block 38 (dual-axis-gap-handling) is the only deception flag.** It's well-executed but inherently misleading. Add a "Why dual-axis is risky" annotation or side-by-side small multiples alternative.

8. **Parallel coordinates alpha tuning** (blocks 47, 64). Line opacity of 0.04–0.33 at 150–300 lines makes selected data nearly invisible or creates spaghetti. Needs per-block tuning based on line count.

9. **Force layout `alphaTarget` never settling** (block 72). Setting `alphaTarget(0.05)` creates perpetual jitter. Use `alphaTarget(0)` with `alphaDecay(0.01)` for eventual settling.
