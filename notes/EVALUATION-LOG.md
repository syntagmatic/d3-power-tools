# Evaluation Log

Running results from the evaluator feedback loop. One section per skill — pass/fail per criterion, evaluator notes, retry outcomes.

---


## distributions — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Box plot bimodality trap called out explicitly | PASS | Lines 18-19 (table: "Hides: Shape — bimodal data looks identical to unimodal") and lines 26-27 ("The box plot trap" dedicated paragraph with concrete example of two datasets producing identical box plots) |
| KDE bandwidth framed as editorial judgment, not technical parameter | PASS | Lines 57-59: "Bandwidth is not a technical parameter — it's an editorial decision about what features to show the viewer." Full subsection (lines 57-77) frames choices in terms of what the viewer sees vs misses |
| Rules have rationales | PASS | Whisker variants (lines 133-138) explain when/why each is appropriate. Chart selection table (lines 16-24) explains what each type shows AND hides. Density scale normalization (lines 295-299) explains editorial consequences of each choice |
| When-not-to-use guidance | PASS | Lines 30-37: six specific cases with rationales (box plots n<10, violins n<30, density for small samples, bee swarm n>500, ridgeline for unordered categories, smoothed charts for discrete data) |
| Code snippets are idiomatic D3 | PASS | KDE function, computeStats, dodge algorithm, ridgeline area generator all follow D3 conventions (selections, scales, area/line generators, curveBasis) |
| Seeing vs drawing orientation | PASS | Skill opens with "Every distribution chart answers one question: what does the data look like?" and consistently frames choices around what the viewer perceives, not implementation details |

### PHILOSOPHY

- **Seeing vs drawing**: Strong. The skill consistently frames decisions in terms of what the viewer will perceive or miss. The chart selection table's "Shows/Hides" columns are a good example.
- **Practitioner value**: High. The box plot trap, bandwidth as editorial judgment, density normalization as hidden editorial choice — these are all things a practitioner learns the hard way.
- **Density**: Good. No filler paragraphs. Every section earns its place.
- **Example quality**: The single example is well-constructed (same data, four chart types) but doesn't demonstrate the skill's most important insight (bimodal data revealing box plot limitations).
- **When-not-to quality**: Strong. Six specific cases, each with a reason and an alternative.

### EXAMPLES

- `statistical-charts.html`: Renders four chart types (box, violin, ridgeline, bee swarm) from the same synthetic data with interactive view switching. Demonstrates comparison across chart types — a useful pedagogical pattern. However, uses only normal distributions, so it does not demonstrate the bimodality trap or KDE bandwidth sensitivity that the skill emphasizes. Shows competent rendering with tooltips and transitions.

### TESTS

- 7/7 passed (1 file)

### META

- **Test coverage gaps**: No interaction tests (the view-switching buttons are untested). Single example file.
- **Missing examples**: No bimodal data example (would powerfully demonstrate the box plot trap). No QQ plot example despite full QQ coverage in the skill. No density plot overlay example. No ridgeline with ordered time-series data.
- **Criteria gaps**: None for the specified criteria.

### OVERALL: PASS

The skill content is sharp and practitioner-focused. Both distribution-specific criteria (bimodality trap, bandwidth as editorial judgment) pass cleanly. The when-not-to-use section is thorough. The main gap is example coverage — additional examples showing bimodal data, QQ plots, and density overlays would strengthen the skill but are not required for a passing grade on the current criteria.


## annotation — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem or analytical question | PASS | Line 8: "A chart without annotation is a chart without an argument." Frames annotation as editorial intent, not API mechanics. |
| Has at least one 'when not to use' section with concrete reasons | PASS | Line 27: "When not to annotate" — exploratory dashboards (imposes narrative on open-ended exploration) and small-multiples grids (cross-panel pattern is the insight). |
| No sections that are pure reorganized API docs | PASS | Every section includes judgment. Leader line geometry explains when to use each type. Label collision compares three approaches with tradeoffs. |
| Rules and recommendations include failure modes/consequences | PASS | Line 297: over-annotation pitfall cites perceptual research (blur ~830ms, size ~910ms, color ~1240ms). Line 47: leader line styling rationale. |
| Related skills are cross-referenced | PASS | Line 10: axes-and-scales, color, canvas-accessibility. Line 214: hybrid Canvas+SVG connects to canvas skill. |
| Code examples demonstrate non-obvious design choices | PASS | Rectangular collision force (forceCollide is circular), Bezier control point avoidance, Voronoi centroid placement with degeneracy case, edge clamping with scroll-aware positioning. |
| Pitfalls explain what goes wrong and why | PASS | Force oscillation mechanism + fix, Canvas blur retina scaling, getComputedTextLength returns 0 before DOM append. |
| Has editorial judgment guidance: callout hierarchy of emphasis | PASS | Lines 14-27: four-level hierarchy (callout > threshold > direct label > tooltip), each with the viewer question it answers. 3-annotation rule with perceptual reasoning. "Annotate the surprising, not the obvious." |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. The hierarchy of emphasis maps annotation types to viewer questions. Editorial guidance about what deserves emphasis, not how to render a callout.
- **Practitioner value**: High. The 3-annotation rule, rectangular collision force, Voronoi placement degeneracy warning, "annotate the surprising" heuristic, and perceptual timing research are all non-obvious.
- **Density**: Good. Editorial judgment, three label placement strategies, responsive strategies, Canvas/SVG hybrid, tooltips, and pitfalls — each section earns its space.
- **Example quality**: Demonstrates multiple techniques in one chart — force-placed labels, callout annotations, threshold line, responsive label thinning, background rects, responsive repositioning with clamping.
- **When-not-to quality**: Real and specific. Exploratory dashboards and small-multiples are legitimate cases with reasoning.

### EXAMPLES

- `annotations-and-labels.html`: Demonstrates genuine insight. Full annotation stack — force-based rectangular collision, callout connectors, threshold reference line, responsive label thinning at breakpoints, annotation clamping on resize.

### TESTS

- 7/7 passed (1 file)

### META

- **Test coverage gaps**: No tooltip test, no resize/responsive test, no Canvas annotation test.
- **Missing test cases**: Render at 400px width to verify label thinning and annotation clamping. Voronoi tooltip example. Canvas annotation example.
- **Criteria gaps**: No assessment of annotation accessibility (aria-label on annotation groups).
- **Regression test idea**: Render at 400px width, verify label thinning works and annotations stay within SVG bounds.

### OVERALL: PASS

The annotation skill delivers genuine editorial guidance. The hierarchy of emphasis, 3-annotation rule, and "annotate the surprising" heuristic teach how to see, not just how to draw. Main gaps are missing tooltip/Canvas examples and no responsive test coverage.


## sparkcharts — 2026-03-25

EVALUATION: sparkcharts

CRITERIA:
- [PASS] Opening states a viewer problem or analytical question, not an API description or generic pattern summary
  Line 8: "Readers lose context when they have to look away from a number to find its trend."
- [PASS] Has at least one 'when not to use' or 'when to avoid' section with concrete reasons
  Lines 282-287: Three concrete reasons with viewer-grounded consequences.
- [PASS] No sections that are pure reorganized API docs without rationale for when/why to use them
  Each variant is concise and purpose-driven.
- [PASS] Rules and recommendations include failure modes, perceptual reasons, or concrete consequences
  curveMonotoneX rationale (line 36), shared scales/lie factor (line 164), mislead section (lines 272-279).
- [PASS] Related skills are cross-referenced where the reader would need them
  Canvas skill (line 241), canvas-accessibility (line 252), LTTB (line 258).
- [PASS] Code examples demonstrate non-obvious design choices, not boilerplate setup
  Endpoint radius padding, flat-line domain fallback, shared domain parameter.
- [PASS] Pitfalls explain what goes wrong and why, not just what to avoid
  Each pitfall names symptom, cause, and fix (lines 290-294).
- [PASS] Covers when sparkcharts mislead (baseline, truncation, aspect ratio) [skill-specific override]
  Lines 268-279: Five misleading scenarios with perceptual consequences.

PHILOSOPHY:
- Teaches seeing vs drawing: The skill teaches seeing. "When Sparkcharts Mislead" is about viewer perception, not rendering mechanics. Curve choice explains perceptual consequences of overshooting.
- Practitioner value: Zero-baseline vs extent-baseline tension (crediting Tufte), color-without-context trap, LTTB threshold are non-obvious insights.
- Density: Good. ~300 lines covering 7 chart types, embedding, misleading scenarios, pitfalls, performance. No filler.
- Example quality: Demonstrates judgment — shared y-domain in grid, sparklines paired with numbers, accessibility attributes throughout.
- "When not to" quality: Concrete. "<5 data points" and "mixing units" are real hazards with specific reasons.

EXAMPLES:
- sparkcharts.html: Demonstrates insight. Stock table pairs sparklines with numbers (skill advice). Grid uses shared globalExtent. Inline text shows proper vertical alignment. All seven chart types. Accessibility present throughout.

TESTS: 7/7 passed (1 file)

META:
- Test coverage: Only checks page load and SVG presence. Does not exercise judgment calls.
- Missing test cases: hover interaction, shared-vs-independent scale visual test, null-data gap handling, bullet chart edge cases.
- Criteria gaps: "Shared vs independent scale guidance has concrete viewer consequence" is present but not criteria-checked.
- Regression test idea: Render sparklines with null values and verify path has a gap (M command after break) to catch if .defined() guidance were lost.

OVERALL: PASS
The sparkcharts skill is solid across all criteria. It opens with a viewer problem, covers seven chart types with non-obvious design choices, has a strong misleading-scenarios section addressing baseline, truncation, aspect ratio, missing data, and color traps, and the example demonstrates the skill's judgment calls.


Running results from the evaluator feedback loop. One section per skill -- pass/fail per criterion, evaluator notes, retry outcomes.

---

## force (2026-03-25)

### CRITERIA

| # | Criterion | Grade | Notes |
|---|-----------|-------|-------|
| 1 | Addresses when force layout is the wrong choice (force override) | PASS | Lines 11-18: covers trees/hierarchies, small static graphs, dense graphs, position-encoding data. Each explains WHY force is wrong and what to use instead. |
| 2 | 5K performance cliff has actionable mitigations (force override) | PASS | Lines 170-200: 6 mitigations in order of effort (distanceMax, theta, Canvas, batch ticks, pre-compute, Web Worker), each with concrete code or parameter values. Mentions d3-force-reuse for 10K+. |
| 3 | Rules have rationales | PASS | Throughout. alphaDecay tradeoff (line 33), velocityDecay purpose (line 35), reheat levels (line 44), per-node strength rationale (line 59), forceLink default strength explained (line 64), collision iterations cost (line 77). |
| 4 | Code examples are self-contained | PASS | All code blocks define their own variables or use clearly external inputs (d3.*, simulation, nodes, links). One fix applied: bounding box force prose-code contradiction (line 81). |
| 5 | Pitfalls section present and complete | PASS | Lines 202-218: 7 pitfalls covering mutated data, missing .id(), origin pileup, early/never stopping, drag requirements, link crossings, stale quadtree. Each has cause and fix. |
| 6 | Density -- no API rehash | PASS | 225 lines. Teaches patterns and judgment, not D3 API docs. Every section adds practitioner value beyond what d3-force docs provide. |
| 7 | Cross-references to related skills | PASS | Line 8 references network, canvas, webgl. Line 200 references webgl for 10K+. |

### PHILOSOPHY

- **Seeing vs drawing:** The skill focuses on judgment (when to use force, how to tune parameters, what the tradeoffs are) rather than API mechanics. The "When Force Layout Is the Wrong Choice" section is a strong example of seeing-first thinking.
- **Practitioner value:** High. The 5K cliff section with ordered mitigations is exactly the kind of knowledge that takes multiple failed attempts to accumulate. The custom force pattern (velocity updates vs position clamping) addresses a common misunderstanding.
- **Density:** At 225 lines, very lean. No filler or repeated scaffolding.
- **Example quality:** Both examples demonstrate insight, not just rendering. force.html shows mode switching and dynamic data. hybrid-canvas-svg.html demonstrates the Canvas+SVG layered pattern with accessibility.
- **When-not-to quality:** Strong. Four distinct cases, each with an alternative and a reason.

### EXAMPLES

| Example | Demonstrates insight? | Notes |
|---------|----------------------|-------|
| force.html | Yes | Multi-mode layout (combined/clustered/radial), dynamic add/remove nodes, charge tuning slider, Canvas rendering with DPR, quadtree hit detection, proper drag with alphaTarget. |
| hybrid-canvas-svg.html | Yes | Canvas for data + SVG for labels/focus rings, keyboard navigation with directional movement, screen reader support with aria-live, toggle labels for high-degree nodes. |

### TESTS

7/7 passed. Coverage: default render, clustered mode, radial mode, add nodes, remove nodes, mode transitions, hybrid Canvas+SVG example.

### META

- **Test coverage gaps:** No drag interaction test (would need mouse drag simulation). No charge slider test. No keyboard navigation test for hybrid example. These are minor -- the core functionality is well covered.
- **Missing test cases:** Could add a test verifying tooltip content on hover matches expected format.
- **Criteria gaps:** None. Both force-specific override criteria are well addressed.

### FIX APPLIED

- Line 81: Changed "never `d.x`/`d.y` directly" to "Usually it modifies `d.vx` and `d.vy`... The exception is hard boundary clamping" -- the original prose contradicted the immediately following bounding box example which correctly sets `d.x`/`d.y` for hard constraints.

### OVERALL: PASS


## responsive — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "A chart built for 960px becomes unreadable at 320px — not because the data changed, but because tick labels overlap, legends occlude data, and 14px text shrinks to 7px." |
| Has 'when not to use' section | PASS | Lines 24-29: three concrete scenarios (static export, fixed container, scrollytelling step). |
| No pure API doc sections | PASS | ResizeObserver section leads with the infinite-loop bug, not the API. Canvas DPI explains the state-reset consequence. |
| Rules include failure modes/consequences | PASS | Infinite loop from observer, hard-coded margins clip labels, crowded ticks at 320px, blurry Canvas on retina, canvas.width resets context state, SVG default 150px height. |
| Related skills cross-referenced | PASS | Line 10: axes-and-scales, canvas, small-multiples. |
| Code examples show non-obvious choices | PASS | Measuring tick label width for dynamic margins, brush domain preservation across resize, brush-to-range-input fallback at narrow widths, DPR change detection via matchMedia. |
| Pitfalls explain mechanisms | PASS | Each pitfall states what happens and why — getBoundingClientRect returns zero for display:none, transitions cancelled on re-bind. |
| D3-specific responsive decisions (override) | PASS | Dynamic margins from measured labels, tick density tied to pixel budgets (80px/tick numeric, 100px/tick time), brush persistence across resize. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Opening frames the problem as readability. viewBox-vs-redraw table structured around what the viewer experiences.
- **Practitioner value**: High. Brush-domain-preservation, mobile-address-bar skip, and dynamic margin measurement are real bugs practitioners hit.
- **Density**: Good. 238 lines covering 10 distinct topics with no padding.
- **Example quality**: Slider lets the viewer directly observe breakpoint-driven layout changes (vertical grouped→horizontal stacked, legend repositioning, tick density, font sizes).
- **When-not-to quality**: Real. Static export, fixed container, scrollytelling are specific scenarios, not strawmen.

### EXAMPLES

- `responsive.html`: Demonstrates real insight. Four levels of breakpoint adaptation with different chart modes, tick counts, date formats, legend positions, font sizes. Canvas sparkline with DPR-aware rendering.

### TESTS

- 4/4 passed

### META

- **Test coverage gaps**: No canvas sparkline test, no slider interaction test, no very-wide viewport test.
- **Missing test cases**: Count `.tick` elements at 900px vs 400px to verify tick density adaptation. Test canvas element renders.
- **Regression test idea**: Render at 900px, count ticks, re-render at 400px, verify tick count decreased.

### OVERALL: PASS

The responsive skill teaches D3-specific judgment — dynamic margins, tick density budgets, brush domain preservation, layout mode switching — rather than being a ResizeObserver tutorial.


## small-multiples — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "Small multiples solve the overplotting problem: when too many series on one chart turn it into spaghetti, repeating the same chart structure across panels lets the eye compare without untangling." |
| Has 'when not to use' section | PASS | Lines 187-193: four concrete reasons — exact value comparison, fewer than 3 categories, panels too small, aggregate story. |
| No pure API doc sections | PASS | All sections include judgment. Cross-tabulation section is the thinnest but brief and practical. |
| Rules include failure modes/consequences | PASS | Panel count guidance explains perceptual mechanism (visual memory scanning). "Redundant axes waste 30-40% of pixel budget." Independent scales "silently mislead." |
| Related skills cross-referenced | PASS | Line 10: axes-and-scales, brushing, canvas. |
| Code examples show non-obvious choices | PASS | Crosshair sync pattern, brush sync with loop-prevention guard, shared canvas clipping. |
| Pitfalls explain mechanisms | PASS | "All panels look identical" explains scoping bug. "Crosshair breaks" explains pixel-mapping issue. |
| Shared vs separate scales with consequences (override) | PASS | Lines 43-69: shared, independent, hybrid — each with viewer consequences. "Independent y-scales silently mislead." |

### PHILOSOPHY

- **Seeing vs drawing**: Solidly on "seeing" side. Panel count framed in visual memory capacity. Scale choice in terms of viewer questions.
- **Practitioner value**: High. 120px minimum panel width, 16-20 panel scanning limit, shared-scale bug pattern, event-loop prevention.
- **Density**: Well-calibrated. No bloat.
- **Example quality**: Shared scales make Sydney's inverted seasonal pattern visible. Synchronized crosshair across 12 panels. Minor inconsistency: renders axes on all panels despite skill advising against it.
- **When-not-to quality**: Strong. Four concrete viewer situations.

### EXAMPLES

- `small-multiples.html`: Demonstrates insight. Minor inconsistencies with skill's own advice (axes on all panels, alphabetical ordering).

### TESTS

- 7/7 passed (1 file)

### META

- **Test coverage gaps**: No crosshair interaction test. No responsive reflow test.
- **Missing test cases**: Hover one panel, verify crosshair in non-hovered panel.
- **Regression test idea**: Hover one panel, check crosshair elements visible across multiple panels.

### OVERALL: PASS

Teaches judgment about small multiples with clear perceptual reasoning. Shared-vs-independent scale decision is thorough. Minor: example contradicts skill's axis-efficiency advice.


## navigation — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 6: "Most charts should not zoom." Immediately frames the judgment call, not API mechanics. Lines 10-12: concrete signals for when zoom is warranted. |
| Has 'when not to use' section | PASS | Lines 18-22: four concrete reasons — dataset fits at default scale, viewer needs full comparison, small multiples better, wheel zoom hijacks scrolling. |
| No pure API doc sections | PASS | Every section pairs mechanics with reasoning. Zoom constraints lead with "users can pan data off-screen" failure mode. |
| Rules include failure modes/consequences | PASS | "Text and strokes scale too, making labels unreadable at extremes." "Instant transform changes are disorienting — viewer loses spatial context." "Hard LOD cuts make the viewer think data changed." |
| Related skills cross-referenced | PASS | Line 49: scales, canvas, brushing, cartography, hierarchy-interaction — placed at the geometric-vs-semantic decision point. |
| Code examples show non-obvious choices | PASS | rescaleX warning to always pass original scale (common bug), brush-to-zoom sourceEvent guard preventing infinite loops, touch filter for mobile, syncing flag for linked views. |
| Pitfalls explain mechanisms | PASS | 9 pitfalls. "D3 stores transform on element via __zoom — setting manually without zoom.transform causes state divergence, next gesture jumps." "Wheel events captured before page can scroll." |
| Addresses when NOT to add zoom (override) | PASS | Opening thesis of the skill. "Most charts should not zoom" is line 8, with four concrete don't-add-zoom scenarios. Not buried — it's the first thing the reader sees. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Geometric-vs-semantic framed as viewer-experience choice. LOD section: "at overview they want patterns, zoomed in they want specifics."
- **Practitioner value**: High. The rescaleX original-scale bug, infinite-loop prevention, touch event filtering, and the "most charts shouldn't zoom" anti-recommendation are all hard-won knowledge.
- **Density**: Good. Covers decision framework, both zoom types, Canvas zoom, minimap, brush-to-zoom, LOD, touch, linked views, and 9 pitfalls without bloat.
- **Example quality**: Five-panel gallery covering semantic zoom, Canvas zoom with minimap, brush-to-zoom, LOD with fade transitions, SVG-on-Canvas overlay. LOD panel is standout.
- **When-not-to quality**: Strong. Four specific scenarios. Opening position is the right editorial choice.

### EXAMPLES

- `navigation.html`: Five-panel gallery. LOD panel is particularly good — density bins at overview, individual points at mid-zoom, labeled points at deep zoom with smooth fades. Minor: all panels use synthetic scatter data; a time-series example would reinforce when zoom is essential vs decorative.

### TESTS

- 5/5 passed

### META

- **Test coverage gaps**: No zoom interaction test, no minimap sync test, no LOD transition verification.
- **Missing test cases**: Zoom interaction that verifies axis rescaling. Brush-to-zoom sync test.
- **Regression test idea**: Zoom in, count visible tick labels, verify they changed (semantic zoom working).

### OVERALL: PASS

Strong opening anti-recommendation, clear geometric-vs-semantic framework, 9 well-explained pitfalls. The five-panel example gallery is comprehensive. Minor gaps in accessibility guidance for zoom and minimap clutter thresholds.


## data-table — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "Charts show patterns; tables show values." Frames around viewer's task. |
| Has 'when not to use' section | PASS | Lines 22-24: distribution shape, trends over time, spatial patterns. "A 500-row table of time-series data is less useful than a line chart." |
| No pure API doc sections | PASS | Number formatting explains why right-alignment matters perceptually. Virtual scrolling explains scroll-position gotcha. |
| Rules include failure modes/consequences | PASS | "Numbers that aren't right-aligned are impossible to compare by scanning." Nested join flash-of-wrong-content failure mode. |
| Related skills cross-referenced | **FAIL** | No cross-references to any related skill. Should link to canvas-accessibility, linked-views, brushing, color. |
| Code examples show non-obvious choices | PASS | Nested join pattern (keyed outer, unkeyed inner) with formatted-value collision failure mode. Shared state coordination. |
| Pitfalls explain mechanisms | PASS | 7 pitfalls, each with concrete consequence. "position: sticky breaks with border-collapse: collapse." Screen reader experience of silent filter. |
| Tables framed as first-class representation (override) | PASS | "Build tables as first-class views alongside D3 visualizations, not as accessibility afterthoughts." Five scenarios where table is the better representation. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Right-align rationale grounded in perception ("the eye decodes at ~10% precision"). Table-vs-chart framing based on viewer's analytical task.
- **Practitioner value**: High. Nested join pattern, sticky header CSS trap, keyed-outer/unkeyed-inner asymmetry are genuinely non-obvious.
- **Density**: Good. No bloat.
- **Example quality**: Well-executed chart-table toggle with sortable columns, filtering, CSV export, accessibility. Minor: contradicts skill's pitfall 5 (scrollIntoView on hover).
- **When-not-to quality**: Concrete with threshold example.

### EXAMPLES

- `data-table.html`: Gapminder-style scatterplot with chart/table toggle, sortable columns, text filtering, linked hover, CSV export. Thorough. Missing: virtual scrolling (skill documents it, example has only 80 rows), standalone table without chart.

### TESTS

- 5/5 passed

### META

- **Test coverage gaps**: No virtual scrolling test. No standalone table test.
- **Missing test cases**: Virtual scroll with 1000+ rows. Standalone table without chart companion.
- **Regression test idea**: Remove key function from outer join, verify flash-of-wrong-content on sort.

### OVERALL: NEEDS_RETRY → PASS (after fix)

Solid skill with strong first-class framing and excellent pitfalls section. Original fail: zero cross-references. Fix applied: added Related line (linked-views, brushing, canvas-accessibility, color, responsive) and changed scrollIntoView from hover to click. Tests pass.


## network — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "Network visualization answers the question: how are these things connected?" Frames around analytical question. |
| Has 'when not to use' section | PASS | Lines 12-21: five concrete signs — no community structure, too dense, too many nodes, uniform relationships, hierarchical data. Each with alternative. |
| No pure API doc sections | PASS | Every section includes rationale. Even the thinnest (Sankey, chord) explain why and when. |
| Rules include failure modes/consequences | PASS | Matrix-vs-node-link cites Ghoniem 2004 and Okoe 2019 with task-performance findings. Hairball failure mode with ranked solutions. Two-channel perceptual limit. |
| Related skills cross-referenced | PASS | Lines 9-10: force, edge-bundling. Line 125: data-table for accessibility. Could also reference canvas, brushing, color. |
| Code examples show non-obvious choices | PASS | Curved multi-edge with arc curvature offsets. refX marker arrowhead-inside-circle fix. Matrix reorder with group-then-degree sort. |
| Pitfalls explain mechanisms | PASS | Hairball explains occlusion from edge crossings. Directed/undirected mismatch explains half-missing-edges bug. "Transparency just makes a translucent hairball." |
| When network viz is the wrong choice (override) | PASS | Lines 12-21: five scenarios with alternatives. "Ask whether the data actually has exploitable structure." One of the strongest when-not-to sections across skills. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Layout comparison table and decision sequence encode analytical judgment about what each layout reveals vs hides.
- **Practitioner value**: High. Perceptual research citations give matrix-vs-node-link argument real authority. Hairball prevention is hard-won knowledge.
- **Density**: Good overall, but uneven — matrix and arc sections are deep, chord gets 4 lines, Sankey gets 3.
- **Example quality**: Three examples (chord, matrix, arc), all interactive with non-obvious choices. Matrix reorder demonstrates core claim that ordering determines quality.
- **When-not-to quality**: One of the best across all skills. Concrete, structural reasoning, specific alternatives.

### EXAMPLES

- `chord-diagram.html`: Dataset switching, pad angle adjustment, group-hover highlighting, bidirectional flow values.
- `adjacency-matrix.html`: Three sort orders with animated reordering, two color modes, cross-highlighting. Good demonstration that ordering determines matrix quality.
- `arc-diagram.html`: Three orderings, weight filtering, click-to-highlight with neighbor emphasis, scaleSqrt for node radius.
- Missing: No Sankey or node-link example despite both being in scope.

### TESTS

- 15/15 passed (3 files, 5 variants each)

### META

- **Test coverage gaps**: No Sankey or node-link examples to test. Random data means screenshots can't be used for visual regression.
- **Missing test cases**: Sankey example with cycle handling. Node-link with multi-edge curve technique.
- **Regression test idea**: Matrix reorder test — verify diagonal block structure appears after group sort.

### OVERALL: PASS

Solid skill. Greatest strength is the "when not to use" section and layout decision framework. Main improvement opportunity: coverage balance — Sankey and chord deserve deeper treatment and examples.


## visual-texture — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Lines 6-8: "Texture gives a chart a second voice when color alone can't speak — for the 8% of men who are colorblind, for the printer, for the reader who needs to tell groups apart without hue." |
| Has 'when not to use' section | PASS | Lines 12-19: four reasons with perceptual thresholds — decoration clutter, marks under ~20px, more than 5-6 patterns, photosensitivity risk. |
| No pure API doc sections | PASS | Pattern library earns its place — explains why userSpaceOnUse matters perceptually. Filter section has performance trade-off table. |
| Rules include failure modes/consequences | PASS | "Viewer reads density as data" for objectBoundingBox. Two charts sharing id silently conflict. fill-opacity affects entire tile including transparent background. |
| Related skills cross-referenced | PASS | Line 10: color, canvas, cartography with specific reasons. |
| Code examples show non-obvious choices | PASS | patternTransform: rotate() instead of computing rotated geometry. Canvas globalCompositeOperation="multiply" for layering. Dual-channel choropleth encoding. |
| Pitfalls explain mechanisms | PASS | 7 pitfalls. stroke-dashoffset animation triggers repaint per frame (not GPU-accelerated). url(#id) resolves against base URL, not page. |
| Perceptual ordering of textures (override) | PASS | Lines 21-29: "Density is the ordered dimension. Sparse dots read as 'less'; dense cross-hatch reads as 'more.' Orientation and shape are categorical." Bertin citation. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Perceptual ordering section captures knowledge practitioners learn from bad charts. Mark color vs background lightness table with L* thresholds.
- **Practitioner value**: High. userSpaceOnUse rationale, perceptual ordering, batch-by-pattern Canvas advice, base tag URL resolution gotcha.
- **Density**: Good. Pattern library, perceptual ordering, dual-channel encoding, Canvas, filters, pitfalls — well-calibrated.
- **Example quality**: Two thorough examples. pattern-gallery.html has color/pattern/both toggle. patterned-fills.html demonstrates density hatching (spacing decreases as value increases).
- **When-not-to quality**: Strong. Perceptual thresholds (20px minimum, 5-6 pattern max) with specific reasons.

### EXAMPLES

- `pattern-gallery.html`: 6 sections — catalog, grouped bar with toggle, line chart dashes, map patterns, Canvas, animated strokes. Interactive mode switching shows accessibility argument.
- `patterned-fills.html`: Density hatching, SVG filter textures, expanded catalog, Canvas pattern atlas. Density chart directly demonstrates perceptual ordering concept.

### TESTS

- 31/31 checks passed (4 test files)

### META

- **Test coverage gaps**: No canvas-accessibility integration test. No pattern legend test.
- **Missing test cases**: Test color/pattern toggle verifies accessibility argument.
- **Regression test idea**: Render bars with density hatching, verify spacing decreases with value (perceptual ordering intact).

### OVERALL: PASS

Solid skill with genuine perceptual insight. The ordering section and dual-channel encoding are standouts. Two thorough examples demonstrate the accessibility argument interactively.


## hierarchy-layouts — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "The layout you choose determines which question the viewer can answer at a glance — leaf sizes, nesting depth, grouping, or topology — and these are not interchangeable." |
| Has 'when not to use' section | PASS | Lines 31-37: four reasons — flat data, exact value comparison, too many leaves without interaction, no meaningful size variable. |
| No pure API doc sections | PASS | .sum() vs .count() earns its place with the non-obvious trap: internal node values get added to children's sum. Tiling strategies paired with design rationales. |
| Rules include failure modes/consequences | PASS | "Wastes ~30% of space." "Treemap cells for deep leaves become unreadably thin." "Node order NOT preserved across data updates — jumpy animations." |
| Related skills cross-referenced | PASS | hierarchy-interaction referenced twice in the right places. Missing color and canvas references but not a failure. |
| Code examples show non-obvious choices | PASS | Radial label upside-down fix, arc-length label hiding, .x(d => d.y).y(d => d.x) swap, jump-free layout transitions. |
| Pitfalls explain mechanisms | PASS | paddingTop "creates a visual gap the viewer will try to interpret." Squarify for animated data: "cells jump to new positions." |
| Layout selection guidance mapping layouts to viewer questions (override) | PASS | Lines 14-21: table mapping each layout to viewer question and perceptual channel. Lines 23-29: decision shortcuts with conditional routing. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Layout selection table is the centerpiece — which question can the viewer answer at a glance.
- **Practitioner value**: High. Coordinate system semantics (.size([crossAxis, mainAxis]) being counterintuitive), tiling strategy tradeoffs.
- **Density**: Good. 137 lines covering 6 layouts, tiling, coordinates, links, radial labels, transitions, pitfalls. Nothing padded.
- **Example quality**: Two examples — Canvas (treemap/sunburst/pack with morphing) and SVG (all 8 layout types with morphing). Both demonstrate genuine design choices.

### EXAMPLES

- `hierarchy-patterns.html`: Canvas-based, 3 layouts, point-resampling morphing, hover hit-testing, DPI scaling.
- `layout-switcher.html`: SVG-based, all 8 layout types, label visibility adapts per layout, coordinate system semantics demonstrated.

### TESTS

- 10/10 passed

### META

- **Missing**: scaleSqrt code snippet for sunburst, cross-references to color and canvas skills.
- **Regression test idea**: Switch to sunburst layout, verify outer rings don't visually dominate (scaleSqrt applied).

### OVERALL: PASS

Layout selection table is the skill's strength. Consistent "why not what" standard throughout. Two instructive examples with non-trivial morphing.


## hierarchy-interaction — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Lines 8-10: "A 4-level tree with branching factor 5 has 780 nodes — too many to show at once, too connected to split across pages." |
| Has 'when not to use' section | PASS | Lines 12-20: four scenarios — comparison tasks, 50+ siblings, shallow hierarchies, area-accuracy loss in sunburst. |
| No pure API doc sections | PASS | _children toggle explains why entering nodes start at parent position — "preserving the spatial metaphor." attrTween vs attr explains garbled intermediate paths. |
| Rules include failure modes/consequences | PASS | "Viewer loses spatial connection." "Animation is chaotic — too many things move at once." "Cells overshoot parent bounds mid-transition." |
| Related skills cross-referenced | **FAIL** | No cross-references. Should link to navigation (semantic vs geometric zoom overlap), canvas, hierarchy-layouts, brushing (fisheye). |
| Code examples show non-obvious choices | PASS | _children toggle idiom, scale-domain narrowing for zoomable treemap, attrTween with stashed d.current, d3.interpolateZoom. |
| Pitfalls explain mechanisms | PASS | "Children appear from (0,0)" without parent position. Overflow visible "only during animation — easy to miss in development." |
| When expand/collapse hurts (override) | PASS | Lines 13-14: "Viewer can't compare a collapsed branch against an expanded one. If the task is comparison across branches, use a static layout or linked highlighting." |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Interaction framed as controlling visibility, not as API mechanics.
- **Practitioner value**: High. Scale-domain narrowing for zoomable treemap is genuinely non-obvious. attrTween gotcha saves real debugging time.
- **Density**: Well-calibrated. Clean separation from hierarchy-layouts.
- **Example quality**: Three examples (collapsible tree, zoomable treemap, zoomable sunburst). Treemap missing clipPath that skill warns about.

### EXAMPLES

- `collapsible-tree.html`: _children toggle with proper enter/exit transitions, expand-all/collapse-all controls.
- `zoomable-treemap.html`: Scale-domain zoom, breadcrumb navigation. Missing clipPath (contradicts skill's own pitfall).
- `zoomable-sunburst.html`: Arc tween with d.current stashing, center circle zoom-out.

### TESTS

- 8/8 passed

### META

- **Test coverage gaps**: No circle pack example despite skill documenting it.
- **Regression test idea**: Expand a node, verify children animate from parent position (not from origin).

### OVERALL: NEEDS_RETRY → PASS (after fix)

Strong skill with 7/8 criteria passing. Original fail: no cross-references. Fix applied: added Related line (hierarchy-layouts, navigation, canvas, brushing). Tests pass.


## linked-views — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "A single chart shows one question. Linked views let the viewer ask a question in one chart and see the answer ripple across others." |
| Has 'when not to use' section | PASS | Lines 12-19: four reasons — working memory ~4 chunks, linking unrelated dimensions = noise, update storms, small multiples sometimes better. Baldonado et al. citation. |
| No pure API doc sections | PASS | BitFilter explains why bitmaps beat naive iteration with concrete numbers (O(N/32 * D), 32x improvement). State store is a practical template. |
| Rules include failure modes/consequences | PASS | Auto-rescale "destroys spatial consistency." Rescaling during drag "makes the chart feel like it's fighting the user." "Blank dashboard trap" named with fix. |
| Related skills cross-referenced | PASS | Line 10: brushing, axes-and-scales, navigation, small-multiples, data-gathering, parallel-coordinates. Comprehensive. |
| Code examples show non-obvious choices | PASS | SelectionModel with "empty = everything" semantics and source param for loop prevention. BitFilter with bit-twiddling. RAF coalescing. |
| Pitfalls explain mechanisms | PASS | "Stale closures" — listener captures initial scale. "Tooltip fights" — multiple simultaneous tooltips. Incompatible data granularity with resolution. |
| Coordination pitfalls: feedback loops, update storms, overload (override) | PASS | Feedback loops: dedicated section with 3 graduated strategies. Update storms: RAF coalescing. Overload: working memory limits, 3-4 view max, spatial grouping. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Linked views framed as "a question the viewer can ask." Interaction is first-class.
- **Practitioner value**: High. Bitmap crossfilter, "empty = everything" semantics, perceptual timing (transitions on `end` not during `drag`, source chart renders first).
- **Density**: Good. Three-tier architecture, bitmap filtering, selection model, feedback loops, performance — all substantive.
- **Example quality**: 4-view dashboard with brush-to-filter, click-to-filter, hover coordination, ghost bars. Demonstrates dispatch, fixed domains, feedback loop prevention.
- **When-not-to quality**: Unusually strong — argues against the skill's own premise with research-backed reasoning.

### EXAMPLES

- `linked-views.html`: 4-view dashboard (scatter, histogram, table, bar). Brush filters all views, category click filters, hover highlights. Ghost bars show full-data context. Missing: bitmap/crossfilter demo, synchronized zoom.

### TESTS

- 31/31 checks passed (4 configs). Brush test visually confirms coordination. Hover/click tests may pass on structural checks only.

### META

- **Test coverage gaps**: Hover and click interactions may not verify visual coordination. No bitmap/crossfilter example to test.
- **Missing test cases**: Bitmap crossfilter demo with large data. Zoom sync example.
- **Regression test idea**: Brush scatter, verify histogram bar count changes (coordination working).

### OVERALL: PASS

Strong skill. "When not to link" is unusually honest. Bitmap crossfilter section bridges theory and implementation. SelectionModel's empty-selection semantics prevents a common dashboard failure. Main gaps are practical: only one example, no crossfilter demo.


## time-series — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "Time is the one axis viewers think they understand — until DST eats an hour, a weekend gap implies a crash, or 100K points turn a line chart into a solid rectangle." |
| Has 'when not to use' section | PASS | Three separate sections: horizon charts (untrained viewers misread band boundaries), cycle plots (no seasonality = noise), real-time (data < 1Hz, skip streaming). |
| No pure API doc sections | PASS | scaleTime vs scaleUtc explains DST failure mode. LTTB includes fidelity-vs-accuracy tradeoff. Circular buffer explains why Array.shift() is O(n). |
| Rules include failure modes/consequences | PASS | Missing .defined() → spike-to-origin bug. Continuous time axis → Mondays look like plateaus. String dates → silent wrong results. |
| Related skills cross-referenced | PASS | Line 10: scales, brushing, navigation, canvas, motion, annotation — six skills with connection phrases. |
| Code examples show non-obvious choices | PASS | Horizon band-folding algorithm, LTTB full implementation, gap sentinel pattern, circular buffer with generator. |
| Pitfalls explain mechanisms | PASS | scaleTime domain with strings: "treats as generic continuous values, axis renders nonsense labels." Brush pixel-vs-data-space mismatch. |
| Horizon chart perceptual research (override) | PASS | Lines 79-81: Heer, Kong, Agrawala CHI 2009 — "2-band matches standard line chart accuracy, degrades beyond 4 bands." Concrete recommendation: 2 for general, 3-4 for expert. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. DST traps, gap handling, when horizon charts mislead are all viewer-centric.
- **Practitioner value**: High. LTTB tradeoff ("preserves what the chart looks like but not what the data says"), circular buffer O(n) trap, horizon band-count research.
- **Density**: Good. 325+ lines covering scales, gaps, horizon, cycle, swimlane, streaming, LTTB, overview+detail, pitfalls.
- **Example quality**: Comprehensive dashboard — multi-series with gaps, crosshair tooltip, overview+detail with brush, horizon charts, quick-select buttons. Flaw: multi-series chart plots 3 different scales on single y-axis without warning.

### TESTS

- 4/4 configs passed (31/31 checks). Covers render, brush, hover, quick-select.

### META

- **Noted issues**: Gantt chart promised in frontmatter but absent from body. Horizon chart code has O(n²) lookup. Example's multi-axis rendering is misleading.
- **Regression test idea**: Verify horizon chart uses 2 bands matching skill guidance.

### OVERALL: PASS

Strong skill with consistent judgment-over-docs standard. Three distinct "when not to" sections. Perceptual research backing for horizon charts. Main gaps: Gantt chart promise undelivered, example multi-axis rendering issue.


## scales (axes-and-scales) — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "A reader's first question is 'how much?' Scales answer it — but the wrong scale lies." |
| Has 'when not to use' section | PASS | Multiple: log/symlog neither (bar chart on log is a lie), gap removal (hiding sensor outage hides the story), broken axis (outlier is the story), dual-y (fabricating correlation). |
| No pure API doc sections | PASS | Grid lines explains when to use vs skip. .nice() gives three "skip when" cases. Every section pairs technique with judgment. |
| Rules include failure modes/consequences | PASS | Log zeros: "D3 silently returns NaN — points vanish without error." Bar not at zero: "50→80 looks like 80 is almost double 50." Dual-y false correlations. |
| Related skills cross-referenced | PASS | Line 10: data-gathering, brushing, motion, canvas, responsive with connection phrases. |
| Code examples show non-obvious choices | PASS | Broken axis piecewise scale with fallback. Responsive tick calculation with pixel-per-tick heuristic. Financial time gap Monday-only filter. |
| Pitfalls explain mechanisms | PASS | "Every axis without a label forces the reader to guess units." "Manually appended labels duplicate on resize." "Unsorted categories look like noise." |
| Log vs symlog with zeros failure mode (override) | PASS | Lines 12-31: 20-line dedicated section. Broken code → NaN. When log is correct (strictly positive, 2+ orders). When symlog (zeros/negatives). When neither (<1 order). |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Every scale choice framed as "editorial decision about what the viewer can see."
- **Practitioner value**: High. Pixels-per-tick heuristic saves trial-and-error. Dual-y section honest about danger without being dogmatic.
- **Density**: Good. Scale selection, time gaps, axis formatting, structural patterns, pitfalls — broad and organized.
- **Example quality**: Six-panel gallery (log/symlog comparison, label collision strategies, broken axis, dual-y, time gaps, nested ordinal). Minor: symlog tick overlap, panels cut off at bottom.

### TESTS

- 7/7 passed (render-only check)

### META

- **Scope gaps**: No coverage of scaleQuantize/Quantile/Threshold, scaleSqrt, scale.clamp(). Minor.
- **Regression test idea**: Render with zero-containing data on scaleLog, verify NaN handling.

### OVERALL: PASS

Well-written skill capturing editorial judgment about scale decisions. Log/symlog section is thorough. "When not to" guidance throughout reflects taste-encoding philosophy. Scope gaps in quantize/sqrt scales don't undermine core quality.


## idiomatic-d3 — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "Break these conventions and you lose the visual structure that makes chains parseable, the data binding that makes updates correct, and the composition patterns that keep charts maintainable." |
| Has 'when not to use' section | PASS | Multiple "when to break it" sections: reusable chart pattern warns against over-application, .call() says when to skip, .join() says when key functions are unnecessary. |
| No pure API doc sections | PASS | Naming conventions table includes "Why this name" column. Code review checklist has "What breaks" column. |
| Rules include failure modes/consequences | PASS | Key function: "bars morph into unrelated values — visual corruption invisible in code review." Arrow function: "d3.select(this) selects window or undefined." |
| Related skills cross-referenced | PASS | Lines 10-11: motion, data-gathering, cross-skill-composition. Line 295: Observable Plot escape hatch. |
| Code examples show non-obvious choices | PASS | Indentation staircase showing which .attr() applies to which element. Full .join() with animated enter/update/exit. Idempotent render trick. |
| Pitfalls explain mechanisms | PASS | "Bypasses data join — no exit handling, no transitions, no key-based identity." "React re-renders and wipes D3's changes." |
| Each convention explains what breaks AND when breaking is correct (override) | PASS | Defining structural pattern of the skill. Every major section has "what breaks" + "when to break it." Indentation, margin, key functions, .call(), reusable chart, naming — all covered. |

### PHILOSOPHY

- **Seeing vs drawing**: Meta skill about code style — weaker connection to viewer perception by nature, but grounds conventions in downstream effects on chart correctness.
- **Practitioner value**: High. "What breaks / when to break" structure is exactly what experienced developers need.
- **Density**: Good. Code review checklist is an excellent quick-reference artifact.

### EXAMPLES & TESTS

- No examples or tests (meta skill about code style). Noted as gap but not a criterion failure.

### META

- **Gaps**: No Observable notebook conventions, no TypeScript guidance, frontmatter promises import strategy coverage not delivered in body.
- **Strength**: Code review checklist (lines 276-286) is actionable and dense.

### OVERALL: PASS

Strong prose with consistent "what breaks / when to break" structure. All 8 criteria pass on content. No examples/tests is the main gap.


## data-gathering — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "Bad data doesn't throw errors — it draws wrong charts." Three concrete visual failures. |
| Has 'when not to use' section | PASS | autoType "Convenient Until It Isn't" — ZIP codes losing zeros, boolean coercion, inconsistent missing values. |
| No pure API doc sections | PASS | d3.bin explains domain mismatch bug. InternMap explains why Date keys work. Typed arrays motivated by GC pressure. |
| Rules include failure modes/consequences | PASS | `+"" === 0` draws a bar at zero. timeParse returns null silently. d3.sort returns new array (silent no-op). |
| Related skills cross-referenced | PASS | Frontmatter: parallel-coordinates, canvas/webgl, cartography, hierarchy-layouts, data-table. Inline cross-refs sparse. |
| Code examples show non-obvious choices | PASS | Row accessor keeping FIPS as string. Streaming CSV buffer/incomplete-line pattern. Pre-computed sort indices. |
| Pitfalls explain mechanisms | PASS | CSV string concatenation, timeParse null, d3.sort new array — each with consequence. |
| Data smells connecting bad data to visual bugs (override) | PASS | Lines 47-65: seven smells — unsorted dates→zigzag, duplicates→inflated bars, sentinels→blown scale, BOM→broken keys, mixed numeric→NaN, empty extent→undefined domain. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. "Bad data draws wrong charts" frames everything around visual consequences.
- **Practitioner value**: High. Missing-value table, `+"" === 0` trap, BOM detection trick are production knowledge.
- **Density**: Excellent. 137 lines, no padding.

### EXAMPLES

- `data-gathering.html`: Complete pipeline — raw data with problems, cleaning, dedup, rollup, histogram, small multiples. Problem cells highlighted red. Only one example; streaming/typed arrays not demonstrated.

### TESTS

- 7/7 passed (1 file)

### META

- **Gaps**: Frontmatter promises pivot, normalization, cumsum, rank, cross, stratify — body doesn't deliver. Two minor typos.
- **Regression test idea**: Feed data with `+"" === 0` trap, verify no zero-bar appears.

### OVERALL: PASS

Focused, judgment-rich skill. Data Smells section is excellent. Main weakness: frontmatter scope exceeds body content.


## webgl — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "You probably don't need WebGL." Frames rendering performance at extreme scale as the viewer problem. |
| Has 'when not to use' section | PASS | Lines 22-29: five bullets — under 500K, complex per-element styling, accessibility needs, quick prototyping, small multiples. |
| No pure API doc sections | PASS | Shader pair explains CSS-pixel-to-clip-space with rationale. Instanced rendering explains why (gl.POINTS size limits). Texture atlas connects to D3 symbol generator. |
| Rules include failure modes/consequences | PASS | Y-flip: "upside-down charts that look plausible." DPR: "half-size on Retina." Context loss: "silently goes blank." |
| Related skills cross-referenced | PASS | canvas (lines 8, 28, 42), canvas-accessibility (lines 26, 336), data-table (line 336). At decision points. |
| Code examples show non-obvious choices | PASS | attribBuffer helper, interleaved buffers for GPU cache locality, bufferSubData for brush filtering, RGB ID encoding for 16M-element picking. |
| Pitfalls explain mechanisms | PASS | 7 pitfalls with symptoms and mechanisms. Buffer upload stalls with double-buffering mitigation. Float precision for IDs above 2^24. |
| Honestly addresses when you don't need WebGL (override) | PASS | Opening sentence + decision table setting 500K boundary + first "when not to" bullet. Canvas handles 50K-500K. "Profile before reaching for WebGL." |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Decision table maps element counts to rendering strategy. Interaction (quadtree, GPU picking, brush, zoom) treated seriously.
- **Practitioner value**: High. The anti-recommendation is rare and valuable. Cost-of-WebGL paragraph names specific tax (shader debugging, buffer management).
- **Density**: Good. Covers decision framework, shaders, instancing, interaction, brush filtering, zoom, context loss, regl escape hatch.

### EXAMPLES

- `webgl-rendering.html`: Five modes (100K points, instanced quads, 1M points, thick lines, brush filtering). Full hybrid architecture. D3 zoom with WebGL uniforms, quadtree hover. Missing: GPU picking demo.

### TESTS

- 7/7 passed (separate configs for each mode + interactions)

### META

- **Housekeeping**: Directory is `skills/webgl/` but CLAUDE.md references `skills/webgl-rendering/`. Path mismatch.
- **Regression test idea**: Render 1M points, verify frame doesn't drop below threshold.

### OVERALL: PASS

Leads with honest judgment about when not to use the technology. Decision table with concrete thresholds. Five rendering modes demonstrated with real interaction. Directory name mismatch is housekeeping issue.


## edge-bundling — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "A network of 500 edges between leaf nodes is unreadable as straight lines — a hairball." |
| Has 'when not to use' section | PASS | Lines 183-191: four scenarios — individual connections matter, hierarchy arbitrary, most edges within-group, fewer than ~30 edges. |
| No pure API doc sections | PASS | Radial layout explains why cluster not tree. Canvas section explains why .context(ctx) matters. |
| Rules include failure modes/consequences | PASS | Beta discussion cites CHI 2025 research on false connections. Missing .raise() → "highlighted edges disappear into the gray." |
| Related skills cross-referenced | PASS | Line 76: hierarchy-layouts. When-not-to recommends force-directed and adjacency matrix (could name skills explicitly). |
| Code examples show non-obvious choices | PASS | LCA path computation, Canvas .context(ctx) pattern, data-space interpolation for layout transitions. |
| Pitfalls explain mechanisms | PASS | Beta vs tension backwards naming. Internal nodes as routing waypoints. String format mismatch for IDs. |
| Beta parameter as judgment call with false-connection tradeoff (override) | PASS | Lines 23-43: "Beta: The Judgment Call." Tradeoff between clarity and pattern. CHI 2025 citation. Starting value 0.15, interactive slider recommendation, presentation vs interactive context distinction. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Beta is an editorial decision, not a parameter. Highlighting is "what makes bundling useful for analysis rather than just aesthetics."
- **Practitioner value**: High. CHI 2025 false-connection research, interactive vs presentation tension choice, cluster-not-tree perceptual reasoning.
- **Density**: Good. Covers beta judgment, LCA paths, radial layout, Canvas, interaction, transitions, performance, pitfalls.

### EXAMPLES

- `edge-bundling.html`: Radial bundled layout with tension slider, click-to-highlight, color-by-group toggle. 22 leaves, 32 connections.
- `edge-bundling-transitions.html`: Five layout modes (bundle, cluster, tree, pack, treemap) with continuous edge redrawing. Ambitious and functional.

### TESTS

- 13/13 passed. Thorough coverage of rendering, tension states, highlighting, all 5 layout modes, mid-flight transitions.

### META

- **Housekeeping**: CLAUDE.md references `skills/hierarchy-edge-bundling/` but actual dir is `skills/edge-bundling/`.
- **Regression test idea**: Change beta to 0, verify edges are straight (no bundling).

### OVERALL: PASS

Beta judgment call section is the standout — treats a numeric parameter as editorial decision backed by research. Transitions example is impressive in scope. 13/13 tests.


## cross-skill-composition — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Lines 7-8: "Brush a scatterplot and watch a histogram reshape, revealing that high-revenue companies cluster in one industry." Concrete analytical moment. |
| Has 'when not to use' section | PASS | Lines 191-199: five anti-patterns — single question, no cross-view insight, beyond 6-8 panels, narrative without transitions, morphing unrelated layouts. |
| No pure API doc sections | PASS | Layer stack has collapse table by scenario. Initialization sequence explains three bugs the ordering prevents. |
| Rules include failure modes/consequences | PASS | 10 composition pitfalls with causes/fixes. Dirty-flag explains stale intermediate states. Performance budget with ms-level costs. |
| Related skills cross-referenced | PASS | Throughout: initialization maps steps to skills, resize contract maps per-skill obligations, performance budget references canvas, linked-views, brushing, scales. |
| Code examples show non-obvious choices | PASS | Dirty-flag with bitwise layer granularity. remapBrush for pixel-coordinate brush extent staleness after resize. |
| Pitfalls explain mechanisms | PASS | "Scales built before container measured" → range([0, width]) where width=0. "Selection manager fires during init" → cascade before B finishes init. |
| Each archetype describes viewer experience (override) | PASS | Five archetypes (Explorer, Narrative, Dashboard, Spatial, Morpher) each open with quoted viewer experience, then architecture and failure modes. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Archetypes lead with viewer perspective. Architecture grounded in viewer experience.
- **Practitioner value**: High. Resize contract table, performance budget with per-step costs, dirty-flag pattern.
- **Density**: Good for a meta skill. Grounds architecture in concrete failures.

### EXAMPLES

- `composition-explorer.html`: Explorer archetype — Canvas scatter + SVG histogram + HTML table linked via d3.dispatch. Follows initialization sequence. Implements dirty-flag and layer stack.

### TESTS

- 3/3 passed (render, brush, hover). Tests verify no crashes but may not confirm cross-view linking visually.

### META

- **Gaps**: One example for five archetypes. Handoff pattern described but no code example.
- **Regression test idea**: Brush scatter, verify histogram bar heights change.

### OVERALL: PASS

Well-written, viewer-centric meta skill. Archetypes section is the strongest contribution — each leads with viewer experience. Resize contract table and performance budget are unique reference material. Main gap: one example for five archetypes.


## shape-morphing — 2026-03-25

### CRITERIA

| Criterion | Grade | Evidence |
|-----------|-------|----------|
| Opening states a viewer problem | PASS | Line 8: "A smooth morph tells the viewer 'these are the same data, seen differently.' When that claim is false, the animation misleads by implying continuity that does not exist." |
| Has 'when not to use' section | PASS | Lines 174-186: five scenarios — categorically different data, unrelated geometries, ordering destruction, encoding reversals, element count limits. |
| No pure API doc sections | PASS | "Choosing an Approach" table includes "when to use" column + "Why not just..." rationale paragraphs. |
| Rules include failure modes/consequences | PASS | "Pinch" artifact from cross-layout morphing. Spinning artifact from unaligned start points. Stashing on datum causes instant snaps. "Swarm" effect beyond 30 elements. |
| Related skills cross-referenced | PASS | Line 144: cartography for projection transitions. Flubber and d3-interpolate-path as alternatives. Missing motion and canvas refs. |
| Code examples show non-obvious choices | PASS | Bar-to-pie via arc parameterization. Stashing on `this` vs datum. bestRotation algorithm. Cross-layout morph with absolute coordinate alignment. |
| Pitfalls explain mechanisms | PASS | interpolateString "produces garbage when paths have different commands." Datum stashing fails "because .data() rebinds." Resampling per frame slow "because getPointAtLength() is expensive." |
| When morphing misleads — false continuity (override) | PASS | Lines 174-186: five misleading scenarios. "Morphing revenue into headcount suggests continuous relationship. Use a cut instead — discontinuity correctly signals data changed." Encoding-reversal insight: intermediate frames encode as neither height nor angle. |

### PHILOSOPHY

- **Seeing vs drawing**: Teaches seeing. Opens with the communication claim a morph makes. "When Not to Morph" is about viewer interpretation, not implementation limits.
- **Practitioner value**: High. Tiered approach hierarchy (parametric > resampling > topology-aware), bestRotation, encoding-reversal insight.
- **Density**: Good. Three tiers, cross-layout morphing, projection transitions, when-not-to, pitfalls — no padding.

### EXAMPLES

- `shape-morph.html`: Parametric cornerRadius + point-resampled arbitrary paths. Interrupt testing.
- `arc-morph.html`: Bar/pie/donut parametric with staged enter/exit. NaN detection post-morph.
- `layout-morph.html`: Treemap/pack/pie cross-layout morph. Pack as neutral alignment target. Mid-transition screenshots confirm smooth interpolation.

### TESTS

- 19/19 passed. Covers initial/end states, mid-transition captures, data mutations, transition interrupts.

### META

- **Gaps**: Projection transition code has no example/test and thin rationale. No cross-ref to motion skill. morph-paths.js referenced but not imported by examples.
- **Regression test idea**: Mid-transition capture of bar→pie, verify no degenerate/NaN path coordinates.

### OVERALL: PASS

Strong skill. Tiered approach, five distinct "when not to morph" failure modes, three well-tested examples including interrupt scenarios. The false-continuity insight is the defining contribution.


---

# Evaluation Summary — 2026-03-25

All 21 skills evaluated. **21/21 PASS** (2 required fixes: data-table and hierarchy-interaction, both for missing cross-references).

## Patterns observed

### Criteria that always passed
- **Opening states a viewer problem**: 21/21. The sharpening pass succeeded here — every skill opens with a viewer-centric framing.
- **When not to use section**: 21/21. Every skill has concrete reasons.
- **No pure API doc sections**: 21/21.
- **Rules include failure modes**: 21/21.
- **Code examples show non-obvious choices**: 21/21.
- **Pitfalls explain mechanisms**: 21/21.
- **Override criteria**: 21/21. Each skill-specific criterion passed.

### Criteria that caught real issues
- **Related skills cross-referenced**: 19/21 on first pass. data-table and hierarchy-interaction had zero cross-references. Both fixed by adding a Related line. This is the only criterion that produced failures.

### Common observations (not failures)
- Several skills have only one example where 2-3 would strengthen coverage (linked-views, data-gathering, cross-skill-composition)
- Test suites generally verify rendering but not interaction outcomes (hover/brush tests pass structurally but don't confirm visual coordination)
- A few frontmatter descriptions promise topics the body doesn't deliver (data-gathering, time-series)
- Directory name mismatches between CLAUDE.md and actual paths (webgl, edge-bundling)

### Strongest skills by evaluator enthusiasm
- **network**: "When not to use" section is one of the best across all skills
- **edge-bundling**: Beta judgment call section treats a numeric parameter as editorial decision backed by CHI research
- **linked-views**: "When not to link" argues against the skill's own premise with research backing
- **shape-morphing**: False-continuity insight and encoding-reversal observation are standouts
- **navigation**: Opening anti-recommendation ("most charts should not zoom") is rare and valuable
