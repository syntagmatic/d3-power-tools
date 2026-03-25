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
