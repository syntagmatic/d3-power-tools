# Adversarial Audit: Blocks 85-105

Audit date: 2026-03-27. All 21 blocks read in full, screenshotted, and evaluated through 5 adversarial lenses.

## Score Summary

| Agent | Avg Score | Verdict |
|-------|:---------:|---------|
| Visual Critic | 6.7 | Competent across the board; one broken treemap (#104) drags the average down |
| Deception Detector | 8.1 | Structurally honest; one radius-scaling violation (#93) |
| Interaction Stress-Test | 6.2 | Weakest dimension — un-throttled canvas redraws and missing .interrupt() are systemic |
| Perceptual Red-Team | 6.7 | Generally manageable complexity; color overload in #93, broken treemap in #104 |
| Metamorphic Tester | 6.9 | Mostly data-driven scales; hardcoded domains are code quality, not bugs |

## Top Issues

**1. Block 104 — Treemap renders as solid gray rectangle (Visual: 4, Perceptual: 5)**
The nutrient treemap at root level collapses all food items into an unreadable mass. Individual cells are invisible; only "All Foods" label shows. The parallel coordinates below work fine. The treemap only becomes usable after clicking to zoom into a food group, but a first-time viewer sees a broken chart.

**2. Block 93 — Radius-based scaling for dot size (Deception: 6)**
Uses `d3.scaleLinear().domain([2, 4]).range([4, 10])` for circle radius. Skill count 4 gets radius 10 (area ~314) vs skill count 2 getting radius 4 (area ~50), a 6.3x visual ratio for a 2x data ratio. Should use `d3.scaleSqrt`.

**3. Block 93 — 13 categorical colors (Perceptual: 5)**
The legend has 13 block-group colors displayed simultaneously. Matching a legend entry to its dots requires scanning all 13 hues, well beyond the 8-color warning threshold. No interaction to isolate groups.

**4. Block 96 — Brush counter double-counts (Interaction: 5)**
The two-pass rendering (faded then highlighted) increments `showing` during the highlighted pass, but the variable isn't reset between passes — it counts highlighted items twice, then divides by 2 as a workaround. Fragile.

**5. Block 101 — O(N) brute-force hover on every mousemove (Interaction: 5)**
WebGL color space projects all ~1800 points to screen coordinates on every mousemove to find the nearest. No spatial index, no throttling.

**6. Block 103 — Full table re-render on sparkline hover (Interaction: 5)**
Hovering a sparkline sets `expandedRow` and calls `renderTable(getCurrentSort())`, which rebuilds every row's SVG sparklines and violins. This fires on mouseenter and mouseleave, causing heavy DOM churn.

**7. Systemic: No RAF throttling on brush/slider Canvas redraws (Blocks 88, 95, 96, 100, 104)**
Multiple blocks re-render Canvas directly inside brush/slider event handlers without requestAnimationFrame coalescing. With 60+ events/second during active brushing, this causes unnecessary work.

**8. Systemic: Missing .interrupt() before transitions (Blocks 94, 98, 105)**
Slider-driven transitions in the election map, morphing timeline, and chord diagram don't interrupt in-flight transitions before starting new ones. Rapid slider movement can cause queued/fighting transitions.

## Per-Block Scorecard

| # | Block | Visual | Deception | Interact | Percept | Metamorph | Avg |
|---|-------|:------:|:---------:|:--------:|:-------:|:---------:|:---:|
| 85 | Skill Constellation | 7 | 8 | 7 | 7 | 7 | 7.2 |
| 86 | Block-Skill Matrix | 6 | 9 | 7 | 6 | 6 | 6.8 |
| 87 | Skill Anatomy Treemap | 8 | 9 | 7 | 8 | 7 | 7.8 |
| 88 | Agent Disagreement Parcoords | 6 | 8 | 6 | 7 | 7 | 6.8 |
| 89 | Score Ridge Plot | 8 | 8 | 7 | 8 | 7 | 7.6 |
| 90 | Skill Growth Sparklines | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 91 | Test Coverage Heatmap | 7 | 9 | 7 | 8 | 7 | 7.6 |
| 92 | Score Delta Waterfall | 7 | 9 | 7 | 7 | 8 | 7.6 |
| 93 | Prompt Complexity Scatter | 7 | 6 | 7 | 5 | 7 | 6.4 |
| 94 | Election Swing Map | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 95 | Flight Route Bundling | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 96 | Regional Parcoords Grid | 7 | 8 | 5 | 7 | 6 | 6.6 |
| 97 | Supply Chain Sankey | 8 | 9 | 7 | 7 | 8 | 7.8 |
| 98 | Shape Morphing Timeline | 7 | 9 | 6 | 8 | 7 | 7.4 |
| 99 | Tidal Harmonic Decomposition | 7 | 9 | 7 | 6 | 8 | 7.4 |
| 100 | City Similarity Explorer | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 101 | WebGL Color Space | 7 | 8 | 5 | 7 | 8 | 7.0 |
| 102 | Earthquake Depth Globe | 7 | 8 | 6 | 7 | 7 | 7.0 |
| 103 | Book Sentence Rhythm | 8 | 7 | 5 | 7 | 6 | 6.6 |
| 104 | Nutrient Treemap Explorer | 4 | 8 | 5 | 5 | 7 | 5.8 |
| 105 | Migration Flow Chord | 7 | 8 | 6 | 6 | 7 | 6.8 |
| | **Column Average** | **6.7** | **8.1** | **6.2** | **6.7** | **6.9** | **7.0** |

## Patterns Worth Fixing

### Quick wins

1. **Block 93: Switch `d3.scaleLinear` to `d3.scaleSqrt` for dot radius.** One-line fix, eliminates only lie-factor violation in the batch.

2. **Block 104: Set minimum cell dimensions or default to zoomed-in view.** The root treemap is unreadable — either increase `paddingInner` so cells get borders, or start with the largest group pre-selected.

3. **Block 96: Fix double-count bug.** Reset `showing = 0` before the highlighted pass, or count in only one pass.

4. **Block 103: Don't re-render entire table on sparkline hover.** Only re-render the affected row's sparkline cell, or use CSS height transition instead of full `renderTable()`.

### Systemic issues

5. **Add RAF coalescing to Canvas brush handlers.** Blocks 88, 95, 96, 100, 104 all render Canvas directly in brush/input callbacks. Wrap in a dirty-flag + requestAnimationFrame pattern:
   ```js
   let dirty = false;
   brush.on("brush end", () => {
     updateState();
     if (!dirty) { dirty = true; requestAnimationFrame(() => { render(); dirty = false; }); }
   });
   ```

6. **Add `.interrupt()` before slider-driven transitions.** Blocks 94, 98, 105 start new transitions on rapid slider input without interrupting previous ones. Add `selection.interrupt()` before `.transition()`.

7. **Block 101: Add spatial index for WebGL hover.** The brute-force O(N) projection loop on every mousemove is wasteful. A 2D grid or quadtree on projected coordinates (rebuilt on rotation) would reduce to O(1) average.

8. **Block 93: Reduce categorical colors from 13 to ~6-7.** Group the 13 block categories into broader themes, or add click-to-highlight interaction so viewers don't need to match all 13 simultaneously.
