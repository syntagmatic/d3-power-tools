# Adversarial Audit — 105 Gem Blocks

Audited 2026-03-28. Each block evaluated through 5 adversarial lenses with screenshot review for visual and perceptual dimensions.

## Score Summary

| Agent | Avg Score | Verdict |
|-------|:---------:|---------|
| **Visual Critic** | 5.20 | One in five blocks is broken or unreadable; the rest cluster at competent-but-generic |
| **Deception Detector** | 8.82 | Structurally honest across the board; zero lie-factor violations |
| **Interaction Stress-Test** | 6.85 | Un-throttled handlers and missing .interrupt() are endemic in interactive blocks |
| **Perceptual Red-Team** | 6.13 | Broken renders and spaghetti plots drag the average; clean single-chart blocks score well |
| **Metamorphic Tester** | 6.75 | Hardcoded domains are common but acceptable for demo blocks with synthetic data |
| **Overall** | **6.75** | Weaker than the Claude-generated blocks (7.05); broken renders are the biggest drag |

## Top Issues

Ranked by severity and frequency across all agents.

1. **Broken/empty rendering** (Visual + Perceptual, 14 blocks: 09, 25, 27, 31, 40, 52, 59, 75, 76, 77, 81, 90, 96, 101) — Completely broken, empty, or fundamentally unusable output. This is the single largest quality issue: 13% of blocks are visually non-functional. These are build/runtime failures, not design problems.

2. **Un-throttled brush/zoom handlers** (Interaction, ~28 blocks) — Brush or zoom event handlers trigger expensive re-renders (Canvas redraws, DOM rebuilds, data filtering) on every mousemove without RAF coalescing or dirty-flag patterns. Worst offenders: 01, 02, 05, 10, 47, 61, 65, 88, 100.

3. **Missing `.interrupt()` before transitions** (Interaction, ~22 blocks) — New transitions started without interrupting running ones, causing stacking, fights, or NaN attributes during rapid interaction. Affects: 05, 11, 15, 17, 18, 19, 20, 25, 29, 30, 62, 71, 72, 77, 86.

4. **Hardcoded scale domains** (Metamorphic, ~59 blocks) — Most blocks hardcode at least one domain. Acceptable for demos with synthetic data but teaches brittle patterns. Worst offenders (score 5): 04, 08, 10, 37, 45, 47, 64, 100.

5. **Too-small-to-read thumbnails** (Visual + Perceptual, 8 blocks: 02, 03, 04, 05, 07, 08, 46, 88) — Renders at thumbnail size where labels, axes, and data encodings are illegible. Viewport or screenshot capture may be misconfigured.

6. **Parallel coordinates / network spaghetti** (Perceptual, ~11 blocks) — Too many overlapping polylines or tangled edges without sufficient opacity management or bundling tension. Parcoords: 01, 47, 64, 88, 100, 104. Networks: 13, 49, 59, 78, 82.

7. **Permanent timer/animation leaks** (Interaction, 7 blocks: 22, 25, 32, 42, 67, 97, 102) — `d3.timer`, `d3.interval`, `setInterval`, or RAF loops that run indefinitely with no stop condition or cleanup.

8. **Non-zero baseline on area charts** (Deception, 3 blocks: 28, 33, 69) — Area fill with non-zero y origin exaggerates visual differences. Line charts with non-zero baseline are acceptable (Tufte exception) but area fills are not.

9. **Default/generic styling** (Visual, ~18 blocks) — Category10 rainbow, SteelBlue defaults, no typographic hierarchy. The standard AI-generated-chart look. Scores cluster at 4-5.

## Worst Blocks

Composite score < 6.0:

| # | Block | Avg | Primary Issue |
|---|-------|:---:|---------------|
| 25 | projection-morphing | 4.8 | Broken — just a light blue blob with no visible country borders or graticule; only UI buttons work |
| 09 | sparkline-dashboard-table | 5.0 | Broken — only headers render, entire table body is empty white space |
| 96 | regional-parcoords-grid | 5.0 | Completely blank -- 4 panels with axis labels but no data lines rendered |
| 22 | rotating-globe | 5.2 | Globe geometry is broken — countries render as small white rectangles, not proper borders; dark t... |
| 77 | sunburst-breadcrumb-brush | 5.2 | Black sunburst with no visible color encoding — all segments are black/dark; cannot distinguish a... |
| 81 | letter-value-table-toggle | 5.2 | Broken — title and button visible but no visualization or data rendered; completely blank |
| 76 | treemap-sparkline-dashboard | 5.4 | Completely blank — white page with a faint border outline; nothing rendered |
| 90 | skill-growth-sparklines | 5.4 | Broken — dark theme shows table headers only, no data rows or sparklines rendered |
| 101 | webgl-color-space | 5.4 | Broken — control panel visible but 3D color space is completely black/empty; no points rendered |
| 31 | streaming-realtime-line | 5.6 | Nearly empty — line chart shows only a sliver of data on far right; stats panel and controls are ... |
| 40 | minimap-navigator | 5.6 | Broken — main chart shows almost nothing (flat line at edge), NaN values in footer; minimap barel... |
| 04 | bee-swarm-census | 5.8 | Renders too small to evaluate; thumbnail-only |
| 21 | us-choropleth | 5.8 | Cartogram is broken — states are distorted rectangles, not recognizable shapes; hard to read geog... |
| 27 | swimlane-gantt | 5.8 | Mostly broken — swimlanes are empty, tasks only appear in the tiny overview bar at top; 80% of vi... |
| 75 | flame-chart-profile | 5.8 | Mostly broken — only 4-5 bars visible at bottom of vast empty space; no labels on frames; SteelBl... |
| 88 | agent-disagreement-parcoords | 5.8 | Renders too small; gray monochrome lines are barely visible; block numbers are illegible dots |

## Best Blocks

Composite score > 7.5:

| # | Block | Avg | Strength |
|---|-------|:---:|----------|
| 06 | qq-plot-confidence | 8.2 | Exemplary: confidence band, inset histogram, annotation of deviation, two-color scheme, clean axes |
| 87 | skill-anatomy-treemap | 8.2 | Treemap with 5 category colors, clear labels with line counts; hierarchy and relative size immedi... |
| 73 | hierarchy-data-table | 8.0 | Clean sortable file explorer table with proportion bars and pie shares; immediately scannable, ex... |
| 103 | book-sentence-rhythm | 8.0 | Table with sparklines and violin plots per chapter; clean rows, sorted by sentence length, dual c... |
| 28 | cycle-plot | 7.8 | Excellent: 12-month cycle with 5-year trend, annotations for peak/low, monthly means, holiday sea... |
| 34 | visual-texture-a11y | 7.8 | Grouped bar chart with hatching/stipple patterns plus CVD simulation below; effective dual encoding |
| 50 | stippled-density-map | 7.8 | Elegant monochrome stipple technique; print-friendly aesthetic; clear density gradient; clean legend |
| 54 | textured-treemap | 7.8 | Bivariate treemap with pattern fills by subcategory — intentional color+texture dual encoding; cl... |
| 74 | marimekko-chart | 7.8 | 5 categories x 4 segments with clear labels inside each cell; width encodes market size, height e... |
| 92 | score-delta-waterfall | 7.8 | Waterfall chart with green increases and pink decreases; labeled values, clear start/end totals, ... |
| 23 | hex-bin-map | 7.6 | Warm orange palette on light gray base reads well; hex bins are clear, density variation is obvio... |
| 26 | horizon-chart-stack | 7.6 | Clean horizon bands with good blue sequential layering; clear time axis, proper row labels, compa... |
| 33 | annotation-showcase | 7.6 | Stock chart with threshold zones, callout annotations, and reference lines; well-layered information |
| 43 | classification-choropleth | 7.6 | Four US maps showing same data with different classification methods; excellent comparison layout |
| 44 | diverging-midpoint-heatmap | 7.6 | Three-city temperature departure heatmap with diverging blue-red scale; annotations highlight ext... |
| 57 | webgl-streaming-particles | 7.6 | Visually striking flow field with viridis background and golden particles; controls panel is clea... |
| 80 | container-query-chart | 7.6 | Clean scatter plot with 4 categories, annotation callout, good spacing; demonstrates responsive well |
| 84 | sparkline-embed-text | 7.6 | Sparklines inline with narrative text, table with embedded charts; excellent data density, immedi... |
| 89 | score-ridge-plot | 7.6 | Ridge plot with 8 distributions in two overlaid colors (before/after); clean comparison, good lab... |
| 95 | flight-route-bundling | 7.6 | Dark theme with glowing blue flight routes on US map; atmospheric; bundling controls are clean |
| 99 | tidal-harmonic-decomposition | 7.6 | Dark theme with layered harmonic waves; toggle controls for components; atmospheric and educational |

## Per-Block Scorecard

| # | Block | Visual | Deception | Interact | Percept | Metamorph | Avg |
|---|-------|:------:|:---------:|:--------:|:-------:|:---------:|:---:|
| 01 | parallel-coords-sparkline-table | 5 | 9 | 5 | 5 | 8 | 6.4 |
| 02 | linked-scatterplot-matrix | 2 | 9 | 5 | 8 | 8 | 6.4 |
| 03 | violin-plot-orchestra | 2 | 9 | 9 | 7 | 6 | 6.6 |
| 04 | bee-swarm-census | 2 | 9 | 9 | 4 | 5 | 5.8 |
| 05 | crossfilter-flight-explorer | 2 | 9 | 6 | 8 | 6 | 6.2 |
| 06 | qq-plot-confidence | 7 | 9 | 8 | 9 | 8 | 8.2 |
| 07 | density-contour-heatmap | 4 | 9 | 4 | 8 | 7 | 6.4 |
| 08 | small-multiples-seasonal | 4 | 9 | 7 | 7 | 5 | 6.4 |
| 09 | sparkline-dashboard-table | 1 | 8 | 6 | 2 | 8 | 5.0 |
| 10 | strip-plot-marginals | 6 | 9 | 5 | 8 | 5 | 6.6 |
| 11 | zoomable-treemap | 6 | 9 | 6 | 7 | 7 | 7.0 |
| 12 | sunburst-icicle-morph | 5 | 9 | 7 | 7 | 7 | 7.0 |
| 13 | radial-dendrogram-edge-bundling | 4 | 9 | 7 | 4 | 7 | 6.2 |
| 14 | force-directed-clustering | 6 | 9 | 7 | 7 | 7 | 7.2 |
| 15 | adjacency-matrix-reorder | 7 | 9 | 6 | 8 | 7 | 7.4 |
| 16 | sankey-energy-flow | 7 | 9 | 7 | 8 | 6 | 7.4 |
| 17 | chord-diagram-trade | 5 | 9 | 6 | 5 | 6 | 6.2 |
| 18 | collapsible-tree-search | 5 | 9 | 6 | 8 | 8 | 7.2 |
| 19 | circle-packing-zoom | 6 | 9 | 6 | 7 | 7 | 7.0 |
| 20 | arc-diagram | 8 | 8 | 6 | 6 | 6 | 6.8 |
| 21 | us-choropleth | 3 | 7 | 7 | 6 | 6 | 5.8 |
| 22 | rotating-globe | 3 | 9 | 4 | 3 | 7 | 5.2 |
| 23 | hex-bin-map | 7 | 9 | 7 | 7 | 8 | 7.6 |
| 24 | flow-map-arrows | 5 | 9 | 7 | 6 | 7 | 6.8 |
| 25 | projection-morphing | 2 | 9 | 5 | 2 | 6 | 4.8 |
| 26 | horizon-chart-stack | 7 | 9 | 8 | 7 | 7 | 7.6 |
| 27 | swimlane-gantt | 3 | 9 | 6 | 3 | 8 | 5.8 |
| 28 | cycle-plot | 8 | 7 | 9 | 9 | 6 | 7.8 |
| 29 | bar-chart-race | 7 | 9 | 5 | 8 | 7 | 7.2 |
| 30 | scrollytelling-climate | 4 | 9 | 6 | 5 | 6 | 6.0 |
| 31 | streaming-realtime-line | 3 | 9 | 6 | 3 | 7 | 5.6 |
| 32 | shape-morphing-gallery | 6 | 8 | 5 | 8 | 6 | 6.6 |
| 33 | annotation-showcase | 7 | 7 | 9 | 8 | 7 | 7.6 |
| 34 | visual-texture-a11y | 7 | 9 | 9 | 8 | 6 | 7.8 |
| 35 | color-palette-explorer | 5 | 9 | 7 | 6 | 6 | 6.6 |
| 36 | responsive-multi-breakpoint | 5 | 9 | 7 | 7 | 8 | 7.2 |
| 37 | accessible-canvas-scatter | 4 | 9 | 8 | 5 | 5 | 6.2 |
| 38 | dual-axis-gap-handling | 7 | 6 | 9 | 8 | 7 | 7.4 |
| 39 | quadtree-hit-detection | 4 | 9 | 7 | 4 | 6 | 6.0 |
| 40 | minimap-navigator | 2 | 9 | 6 | 3 | 8 | 5.6 |
| 41 | force-bundling-chord-triptych | 5 | 9 | 7 | 7 | 7 | 7.0 |
| 42 | phyllotaxis-data-art | 8 | 8 | 4 | 8 | 6 | 6.8 |
| 43 | classification-choropleth | 7 | 9 | 7 | 8 | 7 | 7.6 |
| 44 | diverging-midpoint-heatmap | 7 | 9 | 8 | 8 | 6 | 7.6 |
| 45 | log-scale-bee-swarm | 5 | 9 | 7 | 6 | 5 | 6.4 |
| 46 | threshold-scale-dashboard | 4 | 9 | 7 | 7 | 7 | 6.8 |
| 47 | mixed-scale-parcoords | 6 | 9 | 6 | 4 | 5 | 6.0 |
| 48 | scale-perception-network | 5 | 9 | 7 | 7 | 7 | 7.0 |
| 49 | textured-network-diagram | 5 | 9 | 7 | 5 | 7 | 6.6 |
| 50 | stippled-density-map | 7 | 9 | 9 | 7 | 7 | 7.8 |
| 51 | accessible-force-network | 5 | 9 | 7 | 6 | 8 | 7.0 |
| 52 | accessible-choropleth | 2 | 9 | 9 | 7 | 6 | 6.6 |
| 53 | textured-raincloud | 5 | 9 | 8 | 7 | 6 | 7.0 |
| 54 | textured-treemap | 7 | 9 | 9 | 7 | 7 | 7.8 |
| 55 | webgl-million-scatter | 7* | 9 | 6 | 7* | 7 | 7.2 |
| 56 | webgl-force-galaxy | 5 | 9 | 6 | 3 | 7 | 6.0 |
| 57 | webgl-streaming-particles | 8 | 9 | 7 | 7 | 7 | 7.6 |
| 58 | webgl-density-heatmap | 7 | 9 | 7 | 7 | 6 | 7.2 |
| 59 | webgl-edge-bundling | 3 | 9 | 9 | 2 | 7 | 6.0 |
| 60 | webgl-animated-treemap | 5 | 9 | 7 | 5 | 7 | 6.6 |
| 61 | progressive-crossfilter | 6 | 9 | 5 | 7 | 7 | 6.8 |
| 62 | icicle-brush-explorer | 6 | 9 | 6 | 7 | 7 | 7.0 |
| 63 | semantic-zoom-distributions | 6 | 9 | 7 | 6 | 7 | 7.0 |
| 64 | strum-brush-parcoords | 4 | 9 | 7 | 5 | 5 | 6.0 |
| 65 | brush-compose-scatter | 5 | 9 | 6 | 7 | 7 | 6.8 |
| 66 | falcon-histogram | 6 | 9 | 6 | 8 | 7 | 7.2 |
| 67 | temporal-edge-bundling | 5 | 9 | 5 | 6 | 7 | 6.4 |
| 68 | animated-sparkline-table | 5 | 8 | 7 | 7 | 8 | 7.0 |
| 69 | prediction-band-timeseries | 6 | 7 | 7 | 8 | 7 | 7.0 |
| 70 | gantt-edge-bundle | 6 | 9 | 8 | 6 | 7 | 7.2 |
| 71 | small-multiples-force | 6 | 9 | 6 | 6 | 7 | 6.8 |
| 72 | scrollytelling-network | 7 | 9 | 6 | 7 | 7 | 7.2 |
| 73 | hierarchy-data-table | 7 | 9 | 8 | 9 | 7 | 8.0 |
| 74 | marimekko-chart | 7 | 9 | 8 | 8 | 7 | 7.8 |
| 75 | flame-chart-profile | 3 | 9 | 7 | 3 | 7 | 5.8 |
| 76 | treemap-sparkline-dashboard | 1 | 9 | 9 | 1 | 7 | 5.4 |
| 77 | sunburst-breadcrumb-brush | 2 | 9 | 6 | 3 | 6 | 5.2 |
| 78 | expandable-edge-bundle | 4 | 9 | 5 | 4 | 8 | 6.0 |
| 79 | reduced-motion-dashboard | 5 | 9 | 7 | 6 | 8 | 7.0 |
| 80 | container-query-chart | 6 | 9 | 9 | 8 | 6 | 7.6 |
| 81 | letter-value-table-toggle | 1 | 9 | 8 | 1 | 7 | 5.2 |
| 82 | hive-plot-accessible | 5 | 9 | 8 | 5 | 6 | 6.6 |
| 83 | community-detection-table | 6 | 9 | 7 | 7 | 7 | 7.2 |
| 84 | sparkline-embed-text | 7 | 8 | 7 | 9 | 7 | 7.6 |
| 85 | skill-constellation | 6 | 9 | 8 | 6 | 7 | 7.2 |
| 86 | block-skill-matrix | 6 | 9 | 6 | 6 | 7 | 6.8 |
| 87 | skill-anatomy-treemap | 8 | 9 | 8 | 9 | 7 | 8.2 |
| 88 | agent-disagreement-parcoords | 3 | 9 | 6 | 5 | 6 | 5.8 |
| 89 | score-ridge-plot | 7 | 9 | 7 | 8 | 7 | 7.6 |
| 90 | skill-growth-sparklines | 2 | 8 | 8 | 2 | 7 | 5.4 |
| 91 | test-coverage-heatmap | 6 | 9 | 8 | 7 | 6 | 7.2 |
| 92 | score-delta-waterfall | 7 | 9 | 7 | 9 | 7 | 7.8 |
| 93 | prompt-complexity-scatter | 6 | 8 | 6 | 6 | 8 | 6.8 |
| 94 | election-swing-map | 8 | 9 | 6 | 7 | 7 | 7.4 |
| 95 | flight-route-bundling | 7 | 9 | 9 | 6 | 7 | 7.6 |
| 96 | regional-parcoords-grid | 2 | 9 | 6 | 1 | 7 | 5.0 |
| 97 | supply-chain-sankey | 4 | 9 | 5 | 5 | 7 | 6.0 |
| 98 | shape-morphing-timeline | 7 | 9 | 7 | 8 | 6 | 7.4 |
| 99 | tidal-harmonic-decomposition | 7 | 9 | 8 | 7 | 7 | 7.6 |
| 100 | city-similarity-explorer | 7 | 9 | 6 | 5 | 5 | 6.4 |
| 101 | webgl-color-space | 2 | 9 | 7 | 2 | 7 | 5.4 |
| 102 | earthquake-depth-globe | 7 | 9 | 5 | 7 | 7 | 7.0 |
| 103 | book-sentence-rhythm | 7 | 9 | 9 | 8 | 7 | 8.0 |
| 104 | nutrient-treemap-explorer | 4 | 9 | 6 | 5 | 7 | 6.2 |
| 105 | migration-flow-chord | 5 | 9 | 7 | 7 | 7 | 7.0 |
| | **Column Average** | **5.20** | **8.82** | **6.85** | **6.13** | **6.75** | **6.75** |

\* Imputed from average of other agents (block 55 missing from visual and perceptual screenshot sets).

## Patterns Worth Fixing

### Quick Wins (high impact, mechanical fixes)

1. **Fix the 14 broken renders.** Blocks 09, 25, 27, 31, 40, 52, 59, 75, 76, 77, 81, 90, 96, 101 are visually non-functional. Debug each for JS errors, missing data, or rendering failures. This would immediately raise the portfolio average by ~0.3 points.

2. **Add RAF coalescing to brush/zoom handlers.** A 5-line wrapper (`let dirty = false; brush.on("brush", () => { dirty = true; }); d3.timer(() => { if (dirty) { dirty = false; render(); } })`) would fix the most common interaction issue across ~28 blocks.

3. **Add `.interrupt()` before transitions.** One line (`selection.interrupt()`) before each `.transition()` call prevents the stacking/jumping bug in ~22 blocks.

4. **Stop timers when paused/hidden.** Blocks 22, 25, 32, 42, 67, 97, 102 run animation loops even when paused or off-screen. Check `document.hidden` or stop the timer.

### Systemic Issues (require design decisions)

5. **Viewport/sizing for thumbnail blocks.** Eight blocks render too small to read. Either the blocks assume a larger viewport than the test harness provides, or the layout math is wrong. Needs per-block diagnosis.

6. **Parallel coordinates alpha tuning.** Blocks 01, 47, 64, 88, 100, 104 have spaghetti at default line counts. Line opacity needs per-block tuning based on line count, or brushing should be active by default to reduce visual noise.

7. **Network edge density.** Blocks 13, 49, 59, 78, 82 render networks as impenetrable tangles. Raise bundling tension to 0.65+, add a tension slider, or reduce edge count via filtering.

8. **Dark theme without content.** Blocks 56, 77, 95, 101 use dark backgrounds but render low-contrast or empty content. Dark themes force deliberate color choices -- these blocks haven't made them.

9. **Dual-axis chart risk.** Block 38 is the only deception flag (score 6). It's self-aware about the technique's risks and includes mitigation, but could add a side-by-side small multiples alternative.

10. **Hardcoded domains throughout.** 59 blocks hardcode at least one scale domain. Not a bug for synthetic-data demos, but teaches brittle patterns. The 8 worst offenders use no d3.extent/max/min at all.
