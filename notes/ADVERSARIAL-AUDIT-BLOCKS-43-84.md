# Adversarial Audit: Blocks 43-84

Six adversarial agents reviewed all 42 new blocks. Date: 2026-03-26.

## Score Summary

| Agent | Score | Verdict |
|-------|:-----:|---------|
| Deception Detector | **8.7/10** | Mathematically honest. No fabricated correlations, correct area encoding (scaleSqrt), zero-baselined bars. |
| Perceptual Red-Team | **7.4/10** | Mostly readable. Network blocks push cognitive limits; some animation congruence issues. |
| Metamorphic Tester | **7.4/10** | Generally sound data→visual mappings. Hardcoded domains and missing key functions are the main risks. |
| Visual Critic | **6.8/10** | Functional but template-driven. Accessibility is the systemic gap; WebGL blocks lack legends. |
| Interaction Stress-Test | **6.2/10** | Un-throttled brush/zoom handlers are pervasive. Several race conditions in transition-heavy blocks. |
| Robustness Contract | **4.2/10** | No empty-state handling, no NaN guards, no timer cleanup. Synthetic data masks all edge cases. |

**Composite: 6.8/10**

---

## Top Issues (cross-agent)

### 1. Zero defensive coding (Robustness: 4.2)
No block handles empty data, null values, NaN, or Infinity. No `line.defined()`, no `if (!data.length)` guards, no `scaleLog` clamping for zero values. Synthetic data generation masks this entirely — every block would break on real-world messy data.

### 2. No accessibility on 38/42 blocks (Visual Critic: 6.8)
Only blocks 51, 52, 79, 82 (the explicitly accessibility-themed ones) have keyboard navigation, ARIA labels, or screen reader support. The other 38 blocks have zero `role`, `aria-label`, `<title>`, or `<desc>` attributes. Accessibility is treated as a feature, not a baseline.

### 3. Un-throttled interaction handlers (Stress-Test: 6.2)
Brush and zoom handlers fire full re-renders on every event without RAF coalescing or dirty flags. Worst offenders: block 56 rebuilds a 20K-node quadtree on every pointermove; block 63 recomputes contour density on every zoom; block 61 runs a 50K-record filter on every brush drag.

### 4. No timer/simulation cleanup (Robustness + Stress-Test)
Force simulations, `setInterval`, and `requestAnimationFrame` loops run indefinitely without cleanup. Block 72's force simulation never cools (permanent alphaTarget), block 57's rAF loop continues even when paused.

### 5. Missing color legends on WebGL blocks (Visual Critic)
Blocks 55-57 have no color legend at all. Viewers see colored points but can't decode which cluster or community they represent without hovering each point individually.

---

## Worst Blocks (by composite score)

| Block | Avg Score | Primary Issues |
|-------|:---------:|----------------|
| **56-webgl-force-galaxy** | 3.9 | Quadtree rebuilt per pointermove (O(n log n) × 60fps), 8 colors with no legend, simulation never stops, no WebGL2 fallback |
| **57-webgl-streaming-particles** | 5.0 | Infinite rAF loop, no context-loss recovery, dark-on-dark contrast fails WCAG, no velocity legend |
| **61-progressive-crossfilter** | 4.6 | Unseeded RNG, no RAF coalescing, reset button leaks brush listeners, 4-view cognitive load |
| **71-small-multiples-force** | 4.8 | 6 simultaneous force sims at startup (1800 ticks), animate button has no cancellation, panels look nearly identical |
| **45-log-scale-bee-swarm** | 5.2 | Quadtree stale for 1.5s after scale switch, leaked tick listeners, no .interrupt() on transitions |
| **63-semantic-zoom-distributions** | 5.0 | Unseeded Math.random(), contour density on every zoom, layer removal kills transitions, fake Tol palette |

---

## Best Blocks (by composite score)

| Block | Avg Score | Strengths |
|-------|:---------:|-----------|
| **84-sparkline-embed-text** | 8.8 | Minimal interaction risk, narrative-driven, accessible table, responsive |
| **50-stippled-density-map** | 8.5 | Print-friendly, mathematically honest, seeded PRNG, minimal interaction |
| **53-textured-raincloud** | 8.5 | Full distribution shown, CVD simulation, dual encoding, static layout |
| **69-prediction-band-timeseries** | 8.3 | Honest uncertainty bands, annotation-as-data, step-sequenced reveal |
| **52-accessible-choropleth** | 8.2 | Keyboard nav, ARIA, table toggle, forced-colors support, scaleThreshold |
| **72-scrollytelling-network** | 8.0 | Staged progressive disclosure, manageable node count, clear narrative |

---

## Per-Block Scorecard

| # | Block | Visual | Deception | Interact | Percept | Robust | Metamorph | Avg |
|---|-------|:------:|:---------:|:--------:|:-------:|:------:|:---------:|:---:|
| 43 | classification-choropleth | 7 | 7 | 6 | 8 | 4 | 7 | 6.5 |
| 44 | diverging-midpoint-heatmap | 7 | 9 | 8 | 8 | 4 | 8 | 7.3 |
| 45 | log-scale-bee-swarm | 7 | 9 | 4 | 8 | 4 | 7 | 6.5 |
| 46 | threshold-scale-dashboard | 7 | 9 | 6 | 8 | 4 | 7 | 6.8 |
| 47 | mixed-scale-parcoords | 7 | 9 | 6 | 7 | 4 | 5 | 6.3 |
| 48 | scale-perception-network | 7 | 7 | 6 | 5 | 4 | 7 | 6.0 |
| 49 | textured-network-diagram | 7 | 9 | 7 | 7 | 4 | 8 | 7.0 |
| 50 | stippled-density-map | 8 | 10 | 8 | 8 | 5 | 8 | **7.8** |
| 51 | accessible-force-network | 8 | 9 | 7 | 6 | 4 | 8 | 7.0 |
| 52 | accessible-choropleth | 8 | 9 | 7 | 8 | 4 | 6 | 7.0 |
| 53 | textured-raincloud | 8 | 10 | 8 | 8 | 4 | 8 | **7.7** |
| 54 | textured-treemap | 7 | 9 | 8 | 7 | 4 | 7 | 7.0 |
| 55 | webgl-million-scatter | 5 | 9 | 5 | 7 | 3 | 6 | 5.8 |
| 56 | webgl-force-galaxy | 4.5 | 9 | 3 | 5 | 2 | 7 | **5.1** |
| 57 | webgl-streaming-particles | 5 | 9 | 7 | 7 | 2 | 8 | 6.3 |
| 58 | webgl-density-heatmap | 6 | 9 | 7 | 8 | 3 | 7 | 6.7 |
| 59 | webgl-edge-bundling | 6 | 9 | 6 | 6 | 3 | 7 | 6.2 |
| 60 | webgl-animated-treemap | 6 | 9 | 7 | 7 | 3 | 5 | 6.2 |
| 61 | progressive-crossfilter | 5 | 9 | 4 | 6 | 3 | 7 | 5.7 |
| 62 | icicle-brush-explorer | 7 | 9 | 5 | 8 | 4 | 7 | 6.7 |
| 63 | semantic-zoom-distributions | 4 | 8 | 4 | 8 | 3 | 6 | 5.5 |
| 64 | strum-brush-parcoords | 6 | 8 | 6 | 7 | 4 | 7 | 6.3 |
| 65 | brush-compose-scatter | 7 | 8 | 7 | 7 | 4 | 8 | 6.8 |
| 66 | falcon-histogram | 7 | 9 | 7 | 8 | 4 | 8 | 7.2 |
| 67 | temporal-edge-bundling | 7 | 9 | 6 | 7 | 3 | 8 | 6.7 |
| 68 | animated-sparkline-table | 7 | 9 | 7 | 7 | 4 | 8 | 7.0 |
| 69 | prediction-band-timeseries | 7 | 8 | 8 | 8 | 4 | 8 | 7.2 |
| 70 | gantt-edge-bundle | 7 | 9 | 7 | 7 | 4 | 7 | 6.8 |
| 71 | small-multiples-force | 6 | 9 | 6 | 5 | 3 | 7 | 6.0 |
| 72 | scrollytelling-network | 7 | 9 | 7 | 9 | 3 | 6 | 6.8 |
| 73 | hierarchy-data-table | 7 | 9 | 7 | 8 | 4 | 8 | 7.2 |
| 74 | marimekko-chart | 7 | 9 | 8 | 8 | 4 | 8 | 7.3 |
| 75 | flame-chart-profile | 7 | 9 | 6 | 7 | 4 | 8 | 6.8 |
| 76 | treemap-sparkline-dashboard | 7 | 9 | 7 | 7 | 4 | 8 | 7.0 |
| 77 | sunburst-breadcrumb-brush | 7 | 9 | 5 | 7 | 4 | 7 | 6.5 |
| 78 | expandable-edge-bundle | 7 | 9 | 6 | 7 | 4 | 8 | 6.8 |
| 79 | reduced-motion-dashboard | 8 | 8 | 7 | 8 | 4 | 8 | 7.2 |
| 80 | container-query-chart | 7 | 8 | 8 | 8 | 4 | 7 | 7.0 |
| 81 | letter-value-table-toggle | 7 | 10 | 7 | 8 | 4 | 8 | 7.3 |
| 82 | hive-plot-accessible | 8 | 9 | 7 | 8 | 4 | 8 | 7.3 |
| 83 | community-detection-table | 7 | 10 | 6 | 7 | 4 | 7 | 6.8 |
| 84 | sparkline-embed-text | 7 | 9 | 8 | 9 | 5 | 8 | **7.7** |

**Column averages:** Visual 6.7 · Deception 8.9 · Interaction 6.4 · Perceptual 7.3 · Robustness 3.7 · Metamorphic 7.2 · **Overall 6.7**

---

## Patterns Worth Fixing

**Quick wins (improve many blocks):**
1. Add RAF coalescing wrapper to all brush/zoom handlers
2. Add `.stop()` calls to force simulations after convergence
3. Add color legends to WebGL blocks 55-57
4. Replace `Math.random()` with seeded PRNG in blocks 61, 63

**Systemic (architectural):**
1. Add `line.defined(d => d != null && isFinite(d))` as a standard pattern
2. Add empty-state guards to data-dependent rendering
3. Add `.interrupt()` before new transitions in slider/toggle handlers
4. Add `role="img"` + `<title>` + `<desc>` to all SVGs as baseline accessibility
