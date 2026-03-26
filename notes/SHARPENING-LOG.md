# Sharpening Log

Running notes from the philosophy pass. One section per skill — observations, surprises, cross-skill connections, and open questions.

---

## responsive

**What changed:**
- Rewrote opening to lead with the viewer problem (text shrinks, ticks overlap, legends occlude at small sizes) instead of generic "observe container, re-render"
- Cut "Architecture: The Render Function Pattern" section — boilerplate any D3 user knows
- Compressed ResizeObserver section — removed the HTML wrapper markup, kept the insight (observe a fixed-size wrapper)
- Deduplicated Common Pitfalls — items that repeated earlier sections (infinite loop, Canvas blur, viewBox text) were consolidated
- Compressed "Performance" section — cut debounce/throttle generic web dev advice, kept mobile address bar insight as its own section
- Added "Don't Use Responsive Redraw When..." section with three concrete cases
- Added "Tick Density by Width" section — the most common responsive D3 problem (ticks crowd at 320px) had no coverage
- Added rationales: viewBox table now includes interaction targets row, brush section explains the stale-pixel-coordinates problem before showing code
- Renamed example file from `responsive-charts.html` to `responsive.html` to match test config conventions

**Line count:** 209 -> 194 (net -15 lines despite adding tick density and "when not to use" sections)

**Key insight:** The original skill covered ResizeObserver mechanics well but missed the most common responsive D3 failure: tick labels overlapping at narrow widths. The `axes-and-scales` skill covers tick formatting, but the *decision* to change tick count based on available pixels belongs here in responsive.

---

## annotation

**Diagnosis:** The skill was encyclopedic on leader line geometry, label collision algorithms, and tooltip mechanics, but silent on the editorial question that matters most: what deserves a callout? It treated annotation as a geometry problem rather than a communication problem.

**Changes made:**
- Rewrote opening from generic "Patterns for adding explanatory text" to a claim about annotation's purpose: converting data pictures into arguments.
- Added "Editorial Judgment: What to Annotate" section with hierarchy of emphasis (callouts > thresholds > direct labels > tooltips), the 3-annotation rule with perceptual rationale, guidance on what makes a good annotation candidate (surprising, not obvious).
- Added "when not to annotate" -- exploratory dashboards and small multiples.
- Added rationales to naked rules: why leader lines should be quieter than data, why Voronoi placement degrades with clusters, why tooltip should position at data point not mouse.
- Cut: Tooltip CSS block (boilerplate), Canvas threshold line recipe (trivial setLineDash), d3-annotation type enumeration (API docs), several obvious pitfalls ("SVG text doesn't wrap" -- the wrapText helper already covers this; "annotation z-order wrong" -- layer ordering section already covers this).
- Compressed SVG text wrapping section by folding the getComputedTextLength pitfall into it.
- Added perceptual research citation on emphasis technique effectiveness (blur/focus 830ms > size 910ms > color 1240ms).
- Fixed test config: referenced `annotation.html` but file is `annotations-and-labels.html`.

**Line count:** 359 -> 321 (-38 lines, +editorial judgment section)

**Example status:** Single example `annotations-and-labels.html` demonstrates force-placed labels, callout annotations, threshold line, and responsive resize. Covers the skill well; no redundancy.

---

## small-multiples

**Date:** 2026-03-25

**What changed:**
- Rewrote opening from generic description to problem statement (overplotting/spaghetti charts)
- Added "When Small Multiples Beat a Single Chart" — triggers for choosing multiples over superimposed series
- Added "How Many Panels" — cognitive limits research: ~16-20 for comparison, 50+ shifts to lookup mode, 200+ needs aggregation/filtering. Minimum panel width ~120px for readable line charts
- Added "Panel Ordering" — data-driven ordering (by summary stat, similarity, meaningful category) beats alphabetical; includes D3 sort pattern
- Sharpened scale strategies: added "Danger" callout for independent scales with three concrete mitigations; renamed subsections for clarity
- Added rationale to axis efficiency rule (30-40% pixel budget wasted on repeated axes)
- Cut lazy rendering from 39 lines (two full code blocks) to 3 lines of prose — IntersectionObserver and virtual scrolling are generic web patterns, not D3 judgment
- Cut memory leaks pitfall (generic JS, not D3-specific) and references section (low value)
- Added "When Not to Use This" — fewer than 3 categories, exact value comparison needed, panels too small, aggregate story

**Net line change:** 221 -> 210 (-11 lines), with ~60 lines of new judgment content replacing ~70 lines of API docs and boilerplate

**Cross-skill connections:** Panel ordering by similarity connects to clustering in force-simulation. Independent-scale danger connects to axes-and-scales dual-y guidance. The "too many panels" threshold connects to sparkcharts (sparkline-density panels work at higher counts).

---

## sparkcharts

**What changed:**
- Rewrote opening to lead with the problem sparkcharts solve (context loss when eyes leave the number) rather than describing what they are.
- Added "When Sparkcharts Mislead" section with five concrete failure modes: auto-scaled y-axis hiding magnitude, zero-baseline suppressing signal, aspect ratio distortion, missing data reading as continuity, and color contradicting shape. These connect directly to D3 implementation choices (`d3.extent` vs `[0, max]`, `.defined()`, `preserveAspectRatio`).
- Added "When Not to Use Sparkcharts" section: precise value reading, fewer than 5 data points, mixed units.
- Added rationales to naked rules: curve choice now explains *why* monotoneX avoids false peaks at sparkline scale, `preserveAspectRatio: "none"` explains why horizontal stretching is safe for sparklines specifically, dashboard card additions explain what each element contributes.
- Sharpened "Shared scales across rows" to reference lie factor explicitly.
- Compressed inline text embedding section — cut boilerplate data-attribute parsing code, kept the CSS insight.
- Cut the "Variants" intro sentence that added no information.
- Added explanatory text to Common Pitfalls entries that were too terse.

**Observations:**
- The scaling tension Tufte identified (min-max vs zero-baseline) is the central design judgment in sparklines, and the original skill didn't address it at all. Both choices can mislead; the skill now explains when each is appropriate.
- Only one example file, but it covers all seven chart types plus three embedding contexts (types grid, inline text, table, small multiples). No redundancy to merge.
- The skill had good recipe coverage but was missing the "why" layer — most rules were stated without failure modes.

**Cross-skill connections:**
- The shared-vs-independent scale tension also appears in `small-multiples` and `linked-views`.
- The LTTB downsampling section overlaps with `time-series` — both reference the same algorithm.
- `currentColor` usage for dark mode connects to `color` skill's dark mode section.

---

## data-table

**Decision**: Keep as separate skill. Canvas-accessibility covers making canvas navigable; this covers when and how to build tables as primary or companion views. Overlap is minimal (canvas-accessibility just cross-references this skill).

**What changed**:
- Rewrote opening: dropped "fallback" framing. Tables are first-class views, not afterthoughts.
- Added "Table vs. Chart: When the Table Wins" section with concrete decision criteria (exact value lookup, small n, mixed units, cross-attribute comparison).
- Added "When Not to Use This" section (distribution shape, trends, spatial patterns).
- Added "Number Formatting and Alignment" section: right-align numbers, tabular-nums, consistent precision, units in headers not cells, group separators. This was the biggest gap identified in the philosophy pass.
- Added rationales to naked rules throughout (e.g., why key functions matter, why aria-live is needed for filters).
- Cut: CSV Export section (not D3-specific, pure boilerplate). Sticky Headers section compressed to a pitfall entry. Responsive Patterns cut (generic CSS).
- Compressed: Column Specification, Filtering sections.
- Deduplicated Common Pitfalls (removed entries already explained in their respective sections, added new ones for alignment and aria-live).
- Renamed example from `fallback-table.html` to `data-table.html` to match test config expectations.

**Line count**: 160 -> 131. Net reduction despite adding three new sections.

**Cross-skill connections**: Linked views skill covers coordinated state in more depth. Sparkcharts skill covers inline charts in tables.

---

## navigation

**Diagnosis:** The skill was a competent reference — well-organized recipes for every zoom pattern, but silent on the most important question: should you add zoom at all? The geometric vs semantic section explained what each does but not when to choose one over the other. Several sections (Core API, Zoom Buttons, Clip Path) were reorganized d3-zoom docs.

**Changes made:**
- Rewrote opening to lead with "most charts should not zoom" — the hardest judgment call
- Added "When to Add Zoom" section with concrete signals (data across scales, more points than pixels)
- Added "Don't add zoom when" with reasons (dataset fits at default scale, comparison needs context, wheel hijacks scroll)
- Expanded geometric vs semantic into a decision framework: geometric for spatial metaphors (maps, diagrams), semantic for data charts with axes
- Cut Core API section (just d3-zoom docs), Zoom Buttons section (boilerplate), Clip Path section (standard SVG pattern)
- Added rationales to naked rules: why set all three zoom constraints, why minimaps matter above 5x zoom, why programmatic zoom needs transitions, why rAF debouncing matters
- Added warning about stale scales in rescaleX (pitfall #5)
- Renamed example file from zoom-and-pan.html to navigation.html to match test config expectations

**Cross-skill connections:** The touch filter recipe (single-touch ignore) connects to responsive skill's touch considerations. The SVG overlay pattern is the same architecture described in cross-skill-composition's layer stack. LOD connects directly to canvas skill's quadtree culling.

**Line count:** 352 → 232 lines. Net reduction of 120 lines while adding the "when to zoom" judgment that was the primary gap.

---

## visual-texture

**Line count:** 190 -> 137 (net -53 lines). Cut 5 weak pitfalls (CSS vs attribute trivia, getTotalLength, markers, SVG filter on pattern, numOctaves detail), compressed the filter code block to a decision table, trimmed Canvas atlas to essential pattern. Removed References section.

**Added:**
- "When Not to Use Texture" section — decoration without purpose, small marks that can't resolve patterns, >5-6 pattern limit, photosensitivity warning for high-contrast regular stripes
- "Perceptual Ordering" section — Bertin's classification of texture/grain as ordered variable; density is the ordered dimension (vary spacing for sequential data), type is the categorical dimension (vary pattern shape for nominal data); mixing types for ordinal data confuses the viewer
- Rationales on naked rules: `patternUnits` now explains that density variation reads as data; mark color table now explains the perceptual reason for each threshold; choropleth recipe now notes that density and color reinforce the same ordering

**Cross-skill connections:** The color skill's mark opacity table for dual encoding could reference this skill's L*-based mark color recommendations — they address the same problem from opposite directions. The cartography skill's choropleth patterns should link here for the accessible choropleth recipe.

**Observation:** The existing example (patterned-fills.html) is strong — it demonstrates the catalog, all three encoding modes (color-only, pattern-only, color+pattern), dash patterns, filter textures, density hatching, and Canvas atlas. No consolidation needed since there's only one example doing everything well.

---

## hierarchy-layouts

**Core gap:** No layout selection guidance. The skill explained *how* to use each layout but never *when*. A reader choosing between treemap and sunburst got no help.

**Added:**
- Layout selection decision table mapping each layout to the viewer question it answers, its perceptual channel, and decision shortcuts (wide/shallow vs narrow/deep, size comparison vs grouping vs topology).
- "When not to use" section: flat data, exact comparison tasks, >500 leaves without interaction, no meaningful size variable.
- Rationales to naked rules (e.g., why `paddingTop` without labels misleads, why squarify breaks animated treemaps, why sunburst root wastes the center ring).

**Cut:**
- 5 redundant pitfalls that restated earlier sections (`.sum()` accessor, sort-before-sum, coordinate conventions — all already covered in their own sections).
- Link generators table compressed from 5 lines to 1 sentence — pure API docs.
- `d3.stratify` root parent ID pitfall (too narrow, belongs in data-gathering).

**Kept intact:** Tiling strategy tradeoffs, coordinate semantics, radial label recipe, jump-free transitions. All carry real judgment.

**Examples:** Two examples serve distinct purposes (Canvas morph demo vs SVG 8-layout switcher). No changes needed. All 10 tests pass.

**Line count:** 130 -> 137 (+7). Net increase justified by the layout selection table — the single most important section for someone choosing a hierarchy visualization.

---

## network-visualization (network)

**Date:** 2026-03-25

**Philosophy pass goal:** "Deepen 'which layout for which insight.' Adjacency matrix vs node-link is an analytical choice. Add: when a network viz is wrong entirely (>50 nodes with no clear structure)."

**Diagnosis:** The original SKILL.md had a useful layout comparison table and decision heuristic but lacked perceptual rationale — it said *what* to pick without *why*. The "hairball problem" was mentioned in one sentence. No guidance on when to avoid network visualization entirely. Data validation section was verbose for what it contributed.

**Changes made:**
- **New opening:** Reframed from "patterns for visualizing graph data" to the viewer's question: "how are these things connected?" and the stakes of choosing wrong.
- **Added "When Not to Use Network Visualization":** Five concrete signals (no community structure, too dense, too many nodes with no question, uniform relationships, data is really a hierarchy). This was the biggest gap.
- **Deepened layout comparison:** Added a "Hides" column to the table — what each layout cannot show. Added a section explaining *why* matrix beats node-link for dense graphs, citing Ghoniem et al. 2004 and Okoe et al. 2019 perceptual research.
- **Added rationales to naked rules:** Arc diagram ordering options now explain the perceptual effect (e.g., "by degree — hubs migrate to center; tallest arcs become visible as structural bridges"). Matrix reordering explains what bad ordering does ("scatters clusters across the matrix").
- **Expanded pitfalls:** "Hairball" now has a ranked solution list. Added "force layout as default" anti-pattern and "overloading node size" pitfall.
- **Cut:** Compressed data validation to 2 lines (was 5). Removed redundant `cleanNetwork()` description. Trimmed Sankey section. Removed Wikipedia reference.

**Line count:** 139 → 143 (+4 lines). Added ~30 lines of judgment, cut ~26 lines of API docs and redundancy.

**Tests:** 15/15 pass. No example files changed.

**Cross-skill connections:** The "data is really a hierarchy" escape hatch points to `hierarchy-layouts`. The data table fallback points to `data-table`. Force layout details remain in `force` skill where they belong.

---

## hierarchy-interaction

**Date:** 2026-03-25

**Diagnosis:** The original SKILL.md was solid on recipes (expand/collapse toggle, arc tween, zoomable treemap scale trick) but lacked guidance on when NOT to use each pattern. The opening was technique-focused rather than viewer-problem-focused. The Canvas expand/collapse section had a 50-line code block where only the stale-quadtree insight at the end mattered — the rest was boilerplate interpolation. Some rules lacked rationale ("entering nodes start at the parent's position" — but why does the viewer care?).

**Changes:**
- Rewrote opening to frame the viewer's problem: hierarchies get big fast, interaction controls what's visible
- Added "When Not to Use" section with four specific cases: (1) expand/collapse hides context needed for comparison, (2) expand/collapse is chaotic in wide trees, (3) zoomable treemap is overkill below 3 levels, (4) zoomable sunburst loses area accuracy on zoom
- Cut Canvas expand/collapse code block from 50 lines to prose description — the pattern (position Map + interpolators + d3.timer) is straightforward, the insight (stale quadtree, initialize expanding nodes at parent) is what matters
- Added rationales to naked rules: why enter-at-parent matters perceptually, why attrTween not attr for arcs, why breadcrumbs matter more for treemap than sunburst, why clipPath is needed (linear interpolation doesn't respect containment)
- Added brief rationale annotations to Canvas vs SVG table entries
- Added Cockburn et al. focus+context survey to references

**Lines:** 218 -> 169 (net reduction despite adding "When Not to Use" section)

**Tests:** 8/8 passing (no example changes)

---

## distributions

**Diagnosis:** The skill read like a stats textbook reorganized into markdown. Good code recipes, but the selection table buried the most important insight (box plots hide bimodality) in a table cell. KDE bandwidth was presented as a technical parameter rather than an editorial choice. The QQ normalQuantile function was 30 lines of pure math with zero D3 content.

**Changes:**
- Rewrote opening to frame the core danger: distribution charts can lie confidently
- Added histogram to the selection table — it was missing entirely, despite being the right choice for small n
- Added "the box plot trap" callout — two datasets with identical box plots but completely different shapes
- Reframed KDE bandwidth section from "controls smoothness" to "editorial decision about what features to show"
- Added Silverman's failure mode: it assumes unimodality, so it over-smooths bimodal data
- Added "when not to use" entries for discrete data (KDE at 3.5 children) and density plots with small samples
- Added rationales to whisker variants — each now says when to use it and why
- Compressed QQ normalQuantile from 30 lines of math to a 1-line pointer — the math is pure numerics, not D3 knowledge
- Reframed density scale normalization as "hidden editorial choice" with three options and when each applies
- Cut 4 reference links that were just Wikipedia; kept 2 practitioner references (Wilke, Akin)
- Fixed test config: was pointing to nonexistent `distributions.html`, corrected to `statistical-charts.html`

**Net line change:** ~348 -> ~325 lines. Cut ~23 lines while adding histogram row, box plot trap, discrete data warning, and whisker rationales.

**Cross-skill connections:** The bandwidth-as-editorial-choice pattern echoes the force simulation beta parameter in edge-bundling (both are "how much smoothing" knobs with visual consequences). The density normalization choice connects to the scales skill's guidance on shared vs independent scales in small multiples.

---

## linked-views

**Diagnosis:** The skill was already well-structured with mostly Insight and Recipe content. The opening was generic ("Patterns for coordinating..."). The bitmap crossfilter section was the gem but lacked rationale for why bitmaps beat iteration, incremental update strategy, and a `count()` method for histogram aggregation. Missing entirely: when linking hurts (cognitive overload, feedback loops, update storms).

**Changes:**
- Rewrote opening to state the viewer's problem: one chart = one question, linked views = combinatorial insight, but only if coordination is instant
- Added "When Not to Link" section with four concrete guidelines: view count limits (working memory ~4 chunks), unrelated dimensions, update storms from everything-to-everything linking, and when small multiples are better
- Expanded bitmap crossfilter section: added O(N/32 * D) rationale for why bitmaps beat naive iteration, added `count()` method with popcount for histogram aggregation without index extraction, added incremental update explanation, added "when to skip bitmaps" guidance (<5K rows)
- Renamed "Preventing Infinite Loops" to "Feedback Loops and Update Storms" and added update storm explanation with RAF coalescing cross-reference
- Added rationales to naked rules throughout (e.g., fixed domain preserves spatial memory, auto-rescale during drag "fights the user")
- Added pitfall: linking charts with incompatible data granularity (row-level vs aggregate)
- Added Baldonado et al. reference for multi-view guidelines

**No examples changed.** All 4 tests pass.

---

## time-series

**Diagnosis:** Mix of insight and API docs. The Date Constructor Timezone Trap section was MDN content (cut). Horizon charts and cycle plots had code but no rationale for when/why. LTTB had a good implementation but didn't frame the core tradeoff. Streaming section was already strong.

**Changes:**
- Rewrote opening: viewer-centric problem statement about time being deceptive
- Cut Date Constructor Timezone Trap (MDN content, per philosophy pass directive)
- Compressed scaleTime vs scaleUtc to the judgment call: "scaleUtc is the safe default, scaleTime only for local-timezone labels"
- Added rationale to gap handling: "a bug that looks like a real data crash"
- Added horizon chart perceptual research (Heer et al. CHI 2009): 2 bands match line chart accuracy, degrades beyond 4
- Added "when not to use" for horizon charts: untrained viewers, <5 series, precision reading
- Added rationale to cycle plots: "Is Tuesday always slow, or was last Tuesday unusual?"
- Added "when not to use" for cycle plots: no seasonality = noise
- Added LTTB tradeoff framing: preserves visual shape but distorts frequency content
- Added min-max vs LTTB guidance: speed vs shape fidelity
- Added "when not to use" for streaming: <1 Hz doesn't need the architecture
- Added rationale to Voronoi hit detection: "a 1.5px stroke is nearly impossible to hover"
- Added rationale to TypedArray: "3-5x faster due to memory layout"
- Renamed example file from temporal-time-series.html to time-series.html to match test config

**Line count:** 347 → 329 (net -18 lines, added ~40 lines of rationale, cut ~58 lines of API docs/boilerplate)

**Cross-skill connections:** The LTTB section connects to `canvas` (TypedArray patterns) and `navigation` (virtual windowing on zoom). The overview+detail pattern connects to `brushing` and `linked-views`.

---

## scales (axes-and-scales)

**Diagnosis:** The skill was a reorganized D3 scale/axis API reference. The Scale Selection Guide table listed every scale type with one-sentence descriptions — content available in the D3 docs. Individual scale sections (scaleLinear, scaleBand/scalePoint) were API examples with minimal judgment. The d3.format cheat sheet, axis generation boilerplate, and "removing the domain line" sections added no insight.

**What changed:**
- Cut the scale type catalog table and individual API sections (~100 lines). Replaced with focused sections on the three decision points that actually trip people up: log vs symlog (zeros), band vs point (width vs position), and time gaps (financial data).
- Rewrote opening from generic pipeline description to editorial framing: every scale choice determines what the viewer can see.
- Added rationales to previously naked rules: why dual-y is dangerous (you control the illusion by choosing baselines), why broken axes can mislead (making 900 look close to 50), why bar charts must include zero (proportional encoding).
- Added "when not to use" for: log/symlog (less than one order of magnitude), gap removal (when gaps are the story), dual-y (when you're adjusting scales to "line up"), broken axes (when the outlier is the story).
- Strengthened responsive tick counts section — framed as design decision, not formatting detail.
- Cut: d3.format cheat sheet, axis generation boilerplate, domain line removal, Canvas axis rendering pointer. All are either in D3 docs or trivial.
- Fixed test config: `scales.html` → `axes-and-scales.html` (file path was wrong).

**Line count:** 351 → ~185. Density roughly doubled.

**Cross-skill notes:** Time gap handling overlaps with `time-series` skill — the band approach is duplicated there. Could cross-reference instead of duplicating, but both skills need it in context. The responsive tick section connects to `responsive` skill.

---

## force (force-simulation)

**Diagnosis:** Opening was a dry cross-reference with no viewer problem statement. Alpha/cooling section mixed useful tuning rationale with parameter catalog. Force tuning sections were mostly API docs with some insight buried in them. Missing the two key topics from the philosophy pass: when force layout is the wrong choice, and what to do about the 5K performance cliff.

**Changes:**
- Rewrote opening to state the viewer's problem: "where should nodes go when the only structure is connections?"
- Added "When Force Layout Is the Wrong Choice" section covering: trees/hierarchies (use d3.tree), small static graphs (< 20 nodes — arc diagram or matrix communicates better), dense graphs (adjacency matrix), and when position should encode data (forceX/Y for collision avoidance, not layout).
- Added rationales to naked rules throughout — why higher alphaDecay produces less accurate layouts, why alphaTarget > 0 drains battery, why distanceMax matters for performance, why forceLink default strength formula works.
- Expanded "Performance Cliff at ~5K Nodes" into a proper section explaining the bottleneck (quadtree rebuild + walk per node per tick exceeds 16ms frame budget) and ordering mitigations by effort. Added mention of d3-force-reuse for 10K+.
- Cut redundant API parameter listings that just repeat d3-force docs.
- Renamed `force-simulation.html` → `force.html` to match existing test config references.
- Added test entry for `hybrid-canvas-svg.html`.
- All 7 tests pass.

---

## data-gathering

**Diagnosis:** The autoType section and missing-values table were genuine insight (kept). Common Pitfalls duplicated both sections (items 1-3 repeated autoType/missing). InternMap section was half API docs listing methods. Circular buffer was generic CS, not D3-specific.

**Changes:**
- Rewrote opening to focus on the visual consequence: bad data draws wrong charts, not errors.
- Added "Data Smells" section with 8 visual-bug-causing data problems: unsorted time data (zigzag lines), duplicate rows (inflated bars), inconsistent categories (fragmented groups), sentinel values (blown-out domains), BOM in headers (silent undefined), mixed numeric formats (NaN), single-row groups (meaningless trends), empty-array extent (NaN domain).
- Consolidated Common Pitfalls from 9 to 3 — removed items that duplicated earlier sections.
- Cut circular buffer (generic CS pattern, not D3-specific).
- Cut InternMap method listing; kept just the value-equality insight and the "don't spread to plain Map" warning with a concrete consequence.
- Added rationales: why `isFinite` over `!isNaN`, why explicit row accessors matter (choropleth join example), why pre-sorting matters for `d3.line`.
- Merged two examples into one: `pipeline-demo.html` (stronger) became `data-gathering.html`, removed `data-preparation.html` (redundant — both showed parse/clean/rollup/histogram).

**Line count:** 132 -> 107. Net reduction despite adding Data Smells section.

**Cross-skill connections:** Data smells connect to cartography (FIPS/ZIP autoType), parallel-coordinates (normalization requires clean numeric data), time-series (unsorted dates), distributions (single-row groups)

---

## shape-morphing

**Diagnosis:** Opening was generic ("smoothly transition between shapes") with no viewer problem. Strategy section had the right hierarchy (parametric > resampling) but no rationale for *why*. Cross-layout section was bloated — a 70-line code dump that duplicated the example. No guidance on when morphing misleads.

**Changes:**
- Rewrote opening to state the core claim morphing makes ("these are the same data, seen differently") and when that claim is false.
- Added a decision table (parametric / resampling / topology-aware) with explicit tradeoffs: fidelity, cost, when each fits.
- Added rationales to the two "why not always X" questions that practitioners ask.
- Cut the 70-line Treemap/Pack/Pie code block in Cross-Layout Morphing — it duplicated `examples/layout-morph.html`. Replaced with a 4-step recipe summary that points to the example.
- Added "When Not to Morph" section covering: categorically different data, unrelated geometries, ordering-destroying layout changes, encoding reversals, and too-many-elements swarm.
- Cut 3 reference links that were API docs (D3 Interpolate, D3 Geo Projection, Wikipedia Shape Tweening). Kept flubber, d3-interpolate-path, and Heer & Robertson.
- Trimmed redundant pitfall explanations (already covered inline).

**Line count:** 285 → 192. Net reduction of 93 lines while adding the "when not to morph" section.

**Examples:** All three are distinct and non-redundant (shape-morph.html = parametric + resampling, arc-morph.html = bar/pie/donut arc params, layout-morph.html = cross-layout point resampling). No merges needed.

**Tests:** 19/19 pass (no example changes).

---

## edge-bundling

**Diagnosis:** The skill was a competent reference (Tier 2) but treated beta as a mechanical parameter rather than a judgment call. The opening described the technique without stating the viewer's problem. Radial layout section duplicated hierarchy-layouts content. CSS blocks were boilerplate. The "when not to use" perspective was absent.

**Key changes:**
- Rewrote opening to frame the viewer's problem: hairball vs. group-level pattern, and the tradeoff bundling makes.
- Added "Beta: The Judgment Call" section with CHI 2025 research (Wallinger et al.) on false connections — viewers follow merged bundles and perceive adjacencies that don't exist. Practical guidance on when to reduce tension.
- Cut redundant radial layout code (cross-ref to hierarchy-layouts instead), removed full CSS blocks, compressed SVG rendering section.
- Added "When Not to Use" section: when individual connections matter, when hierarchy is flat/arbitrary, when most edges are within-group, when edge count is too low.
- Added rationale to separation function and cluster-vs-tree choice.
- Added CHI 2025 and Edge-Path Bundling references.
- Cut ~90 lines of API docs/boilerplate, added ~40 lines of judgment. Net reduction ~50 lines.

**Cross-skill connections:** The false-connection problem in bundling parallels the smoothing problem in KDE (distributions skill) — both trade individual data fidelity for aggregate pattern visibility, and both have a single parameter that controls the tradeoff.

**Examples:** Two examples (basic + transitions), both distinct and well-constructed. No merges needed. All 13 tests pass.

---

## cross-skill-composition

**Diagnosis:** The skill had strong recipe content (layer stack, dirty flag, resize contract, pitfalls) but the composition archetypes read as architecture catalogs — they described code structure without saying what the viewer gains. The opening focused on "glue" (developer concern) rather than the viewer's moment of cross-view insight.

**Changes:**
- Rewrote opening to center on the viewer experience: composition lets the viewer hold multiple relationships in mind at once; latency breaks the cognitive link.
- Added viewer-experience paragraphs to all five archetypes (Explorer, Narrative, Dashboard, Spatial Explorer, Layout Morpher), describing what the viewer sees and feels, not just what the code does.
- Added "when it works" guidance to each archetype — concrete conditions under which the pattern helps vs. hurts.
- Added "When Not to Compose" section with five concrete anti-patterns: single-question charts, same-dimension linked views, >6-8 panel dashboards, narrative without transitions, morphing between unrelated layouts.
- Added rationales to Hybrid Pattern (why the viewer benefits), Handoff Pattern (viewer gets fluid motion then interactivity), dirty flag (why without it intermediate states flash), debouncing (the tradeoff), and performance splitting (viewer sees instant primary feedback).
- Compressed initialization sequence explanation from bullet-list dependencies to a single paragraph naming the three real bugs it prevents.
- Added UW IDL Multi-View Composition reference.
- Example unchanged — it already demonstrates the Explorer archetype well with Canvas scatter + SVG histogram + HTML table.

**Line count:** 228 -> 227 (net -1, despite adding ~40 lines of viewer-experience content, offset by compressing boilerplate).

**Cross-skill connections:** The "when not to compose" guidance connects to linked-views (when linking hurts), navigation (when not to add zoom), and shape-morphing (when morphing misleads). These skills should cross-reference each other's "when not to" sections.

---

## idiomatic-d3

**Diagnosis:** The skill was well-structured but read like reorganized D3 docs in several sections. The "Which Methods Return What" table (pure API reference), Import Patterns (3 subsections of boilerplate), Modern JS in D3 Context (general JS advice), and Observable Notebooks section were all things you can look up. The opening described what D3 conventions are rather than why they matter.

**Changes:**
- Rewrote opening: conventions exist because breaking them causes specific failures (unreadable chains, silent data corruption, unmaintainable layouts).
- Added "What breaks" rationale to every major convention: method chaining (can't tell which attrs apply to which element), margin convention (magic numbers scatter), key functions (silent data-element mismatch on update), .call() (copy-pasted blocks drift), scales-as-functions (can't change scale type without rewriting attrs), reusable chart pattern (false reusability, hidden state).
- Added "When to break the rule" for every convention: short chains don't need 2/4-space indent; static one-shot charts don't need key functions; one-off config doesn't need .call() extraction; Prettier-enforced projects should follow their formatter.
- Cut 136 lines (430 → 294): removed "Which Methods Return What" table, Import Patterns section (3 subsections), Modern JS in D3 Context section, Pointer Coordinates subsection. These are all lookupable.
- Compressed Naming Conventions table: added "Why this name" column instead of generic "Notes".
- Enriched Code Review Checklist with "What breaks" column.
- Reduced Common Pitfalls from 10 to 6: merged redundant items (flat indentation → already covered in Method Chaining section; d3.select(this) → already covered in Event Handling; missing key function → already covered in Data Joins). Added Exception notes where breaking the rule is correct (Canvas rendering for loops, D3-for-math-only with frameworks).

**Cross-skill connections:** The reusable chart pattern discussion connects to `cross-skill-composition` (when to abstract). The key function pitfall connects to `motion` (transitions need object constancy). The framework DOM conflict connects to any skill used with React/Vue.

**No tests:** This meta skill has no examples directory or test fixtures. Testing is N/A.

---

## webgl

**Diagnosis:** The original opened with "GPU-accelerated rendering for datasets too large for Canvas 2D" and immediately suggested WebGL at 100K elements — a threshold where Canvas 2D is perfectly fine. The when-to-use table was too aggressive. The compile/link boilerplate was standard WebGL API docs, not D3 insight. Pitfalls were naked rules without rationales.

**Changes:**
- Rewrote opening to lead with "you probably don't need WebGL" — Canvas handles 100K fine, WebGL earns its complexity at 500K+
- Added "When Not to Use WebGL" section: under 500K, complex styling, accessibility needs, prototyping, small multiples (context limits)
- Raised threshold in the when-to-use table from 100K to 500K, added rationales explaining WHY (JS→GPU boundary, parallel vs sequential)
- Cut the standalone compile-and-link section (standard WebGL ceremony, not D3 knowledge) — the attribBuffer helper in the scatter plot section covers the pattern
- Added rationales to all pitfalls (why Y-flip matters, why DPR bites you, why context loss is silent)
- Added rationales to interleaved buffers (cache locality), instanced rendering (divisor explanation), zoom (no re-upload needed), brush filtering (why bufferSubData is fast)
- Cut 2 low-signal references (WebGL2 spec, Book of Shaders) and added editorial note on deck.gl
- Fixed test config: filenames pointed to nonexistent `webgl.html`, corrected to `webgl-rendering.html`

**Line count:** 392 → ~240. Net reduction while adding the "when not to use" section and rationales throughout.

---

## color (research expansion)

**Date:** 2026-03-26

**What changed:**
<<<<<<< HEAD
- Replaced OKLab conversion math (pure numerics) with OKLCH palette generation section: CSS-native oklch() usage and culori library integration for D3-compatible interpolators
- Added "Choosing a Palette System" decision table covering Viridis, Cividis, Magma, Tableau10, Observable10, Tol, ColorBrewer, and Crameri — when to use each and why
- Added APCA contrast section alongside existing WCAG 2: asymmetric scoring, Lc thresholds for chart elements (45 labels, 60 axes, 75 body text), dark mode advantage over WCAG 2
- Added Crameri scientific colour maps guidance (import pattern for D3, when to use: citable scientific publications)
- Updated color space table: HCL "Mostly" uniform hue (honest about blue-purple range), OKLCH as the programmatic generation choice
- Expanded Wide Gamut section with practical guidance (useful for categorical, not sequential)
- Added cross-reference to axes-and-scales for classification scales
- Added Observable Plot note (schemeObservable10 default)
- Updated references: added OKLCH picker, Culori, Crameri Zenodo DOI, APCA
- Timestamped version-dependent claims (d3-color OKLCH support, WCAG 3.0 draft status)

**Line count:** 282 → 329 (+47 lines, +17%). Within 10-30% growth target.

**Key judgment:** The research contained a full d3-scale-chromatic inventory and extensive Crameri map tables. These were compressed into a decision table and brief prose — the skill guides palette *choice*, not palette *enumeration*. The OKLCH section prioritizes the two practical approaches (CSS-native and culori) over conversion math.

**Cross-skill connections:** Classification scales for choropleths cross-referenced to axes-and-scales. APCA thresholds connect to annotation skill's label sizing guidance.

---

## cartography (research expansion)

**Date:** 2026-03-26

**What changed:**
- Added Snyder's projection selection framework: distortion property decision (equal-area vs conformal vs compromise), geographic extent → projection family mapping, common regional setups (Europe ETRS89-LAEA, contiguous US USGS Albers)
- Added "When to Escalate Beyond Pure D3" section with decision table (6 signals: basemap need, zoom levels, projection, deployment, feature count, interaction model)
- Added MapLibre GL JS + D3 overlay integration pattern with geoTransform bridge code
- Added PMTiles serverless tile guidance
- Added performance boundaries table (D3 SVG/Canvas/MapLibre/d3-tile)
- Added dark mode maps paragraph with Schiewe 2024 research on dark-is-more bias, cross-ref to color skill
- Added Observable Plot geo mark note
- Added cross-reference to axes-and-scales for classification scales
- Timestamped version-dependent claims (MapLibre v4+, PMTiles as of March 2026)
- Added 4 references (Projection Wizard, MapLibre, PMTiles, d3-geo-polygon)

**Line count:** 498 → 575 (+77 lines, +15.5%). Within 10-30% growth target.

**Key judgment:** The research contained full MapLibre+PMTiles+D3 stack code (~80 lines), dark mode theme objects with Canvas rendering code (~50 lines), a projection selection helper function (~40 lines), and Tissot's indicatrix code. These were compressed to: a decision table, one bridge pattern, one paragraph, and prose guidance. The skill guides the *choice* of when to escalate, not how to build a full MapLibre app.

**Cross-skill connections:** Classification scales for choropleths cross-referenced to axes-and-scales (don't duplicate). Dark mode palette guidance cross-referenced to color skill. Performance escalation connects to canvas and webgl skills.

---

## data-gathering (research expansion)

**Date:** 2026-03-26

**What changed:**
- Added "When to Escalate Beyond d3.csv" decision table: DuckDB-WASM, hyparquet, apache-arrow, AbortController, ReadableStream -- with bundle sizes, row-count thresholds, and judgment on when each earns its weight
- Added "Cancellable Data Loading" section with AbortController pattern and the visual bug it prevents (stale response overwrites fresh data)
- Added Parquet/Arrow BigInt pitfall (Arrow Int64 columns break D3 scales)
- Added Observable Plot/Framework note on build-time pre-aggregation
- Added DuckDB-WASM and hyparquet references

**Line count:** 136 → 177 (+30%). Growth is decision guidance and one code pattern, not API docs.

**Key judgment:** The research contained full DuckDB-WASM initialization boilerplate, hyparquet examples, Papa Parse streaming, progressive rendering, and NDJSON generators. All compressed into one decision table that tells you *when* to reach for each tool. The skill stays D3-focused -- these are escape hatches, not primary content.
