---
role: findings
date: 2026-04-29
sources: [skills/brushing/SKILL.md, skills/linked-views/SKILL.md, skills/coordination/SKILL.md, notes/research/brushing.md, notes/research/linked-views.md]
---

# Findings: empirical comparison of brushing / linked-views / coordination

## What each skill currently is

### `brushing` (304 lines)

**Stated scope (description frontmatter):** "advanced brushing, selection, and cross-chart linking interactions ... lasso, fisheye, intersection brushing, focus+context, brush-and-link."

**Actual content, by section:**
- Choosing a selection approach (decision table)
- Line intersection brushing (cross-product math, parcoords application, Web Worker offload)
- Render queue (delegated to `canvas` skill)
- Fisheye distortion (cartesian + radial)
- **Cross-chart linking** — `SelectionManager extends EventTarget`, connecting views, canvas highlight pattern, linked view timing
- Lasso selection (ray-casting, pointer events)
- Pointer Events best practices
- Keyboard brush adjustment
- Spatial indexing for intersection testing
- **Brush composition** — multi-region (shift+drag), `ComposableSelectionManager` with union/intersect modes
- Scalable cross-filtering (Falcon pattern, falcon-vis)
- Performance at scale (delegates to canvas/webgl skills)
- Common pitfalls

The skill is a hybrid: brush mechanics + cross-chart linking + cross-filtering. Roughly 60% mechanics, 40% linking.

### `linked-views` (53 lines)

**Stated scope:** "design patterns for multi-chart dashboards ... layout (Overview+Detail, Cross-filtering), scale consistency, visual feedback (Ghost/Active patterns)."

**Actual content:**
- When not to link (Parsimony, Complementarity, Attention Management)
- Design patterns: Overview+Detail, Cross-filtering, Ghost+Active layering
- Scale domain strategies (fixed vs auto-rescale)
- State serialization (URL encoding)
- Tooltip coordination
- Animation and feedback
- Scaling to large data (one-line pointer to Mosaic)

**Explicit cross-references at the top:** "For technical wiring (d3.dispatch, stores, framework bridges), see `coordination`. For brush mechanics, see `brushing`. For faceted layouts of the same chart type, see `small-multiples`."

This skill is well-scoped. It is purely about *design judgment* — when, why, how many, what pattern.

### `coordination` (133 lines)

**Stated scope:** "technical foundation for multi-chart communication ... d3.dispatch, shared state stores, selection models, namespacing, framework bridges (React/Vue/Angular), bitmap indexing for 100K+ rows."

**Actual content:**
- Coordination architecture: event bus (d3.dispatch), shared state store, selection model
- Framework bridges (React Context+Hook, Vue Provide/Inject, Angular runOutsideAngular)
- Performance: RAF coalescing, bitmap indexing, render priority (source first)
- Common pitfalls (feedback loops, stale closures, memory leaks)

**Explicit cross-references at the top:** "For design patterns (Overview+Detail, Cross-filtering), see `linked-views`. For brush mechanics, see `brushing`. For faceted layouts, see `small-multiples`."

Also well-scoped. Purely about *implementation wiring*.

## Cross-references

| From → To | Direction |
|-----------|-----------|
| linked-views → coordination | "For technical wiring, see coordination" |
| linked-views → brushing | "For brush mechanics, see brushing" |
| coordination → linked-views | "For design patterns, see linked-views" |
| coordination → brushing | "For brush mechanics, see brushing" |
| brushing → coordination | (none — brushing has its own SelectionManager and doesn't defer) |
| brushing → linked-views | (none) |

`linked-views` and `coordination` already form a clean two-skill pair: design vs. wiring. They reference each other and reference `brushing` as the source for brush mechanics. **The asymmetry is on `brushing`'s side** — it doesn't defer to coordination for the wiring layer; it has its own.

## Where the overlap actually lives

Three places:

### 1. SelectionManager class — three definitions

| Skill | Class name | Purpose |
|-------|-----------|---------|
| brushing | `SelectionManager extends EventTarget` | row indices, all-selected-if-empty, source-tagged events |
| brushing | `ComposableSelectionManager extends EventTarget` | union/intersect modes across multi-source brushes |
| coordination | `SelectionModel` | key-based selection, dispatch-based notifications, all-selected-if-empty |

These are three implementations of the same abstraction. The distinction (indices vs keys, EventTarget vs d3.dispatch) is real but minor. A reader following `brushing` learns one pattern; a reader following `coordination` learns another. Multi-skill blocks that cite both produce inconsistent code.

### 2. Cross-chart linking section in `brushing`

Lines 92–157 of `brushing/SKILL.md`. Includes:
- ASCII diagram of "View A / View B / View C → SelectionManager"
- The `SelectionManager` class
- "Connecting Views" wiring example
- Canvas highlight pattern
- Linked View Timing

This material belongs to either `linked-views` (timing, ghost/active) or `coordination` (wiring) by content, but lives in `brushing` by history. It's the single largest source of conflation.

### 3. RAF coalescing and render priority

`coordination` covers these explicitly. `brushing` mentions them via delegation (see `canvas` skill). `linked-views` references "see `coordination` for render priority." No actual duplication — cleanest of the three overlaps.

## Activation-trigger overlap (description fields)

Words triggering ≥2 of the three skills, scanned from frontmatter descriptions:

| Trigger | brushing | linked-views | coordination |
|---------|:--------:|:------------:|:------------:|
| brushing | ✓ | ✓ (in cross-references) | ✓ (in cross-references) |
| linked / linked views | ✓ | ✓ | ✓ |
| coordinated / coordination | ✓ | ✓ | ✓ |
| selection | ✓ | — | ✓ |
| cross-filtering | ✓ | ✓ | (implicit via bitmap) |
| dispatch / d3.dispatch | — | ✓ (defer) | ✓ |
| highlight | ✓ | ✓ | (implicit) |

A prompt like *"add brushing and linked highlighting"* or *"build a coordinated-views dashboard"* could match all three with similar score. The auto-activation router has no signal to disambiguate.

## Block-level evidence (sampled from `/blocks/`)

Spot-checked blocks that import patterns from these skills:

- `02-linked-scatterplot-matrix.html` — uses brushing's intersection logic, coordination-style RAF coalescing, linked-views' ghost/active visual treatment. All three skills' patterns appear in one block. (This is fine for a multi-skill block; it just means the discriminator can't tell which skill "produced" it.)
- `13-radial-dendrogram-edge-bundling.html` — pure brushing.
- `hierarchy-bundles.html` — brushing + coordination.

A pre-refactor baseline audit run would quantify how many blocks touch ≥2 of these three skills. Hypothesis: most "linked" blocks touch all three.

## Distinct content that must not be lost in a merge

If `brushing` is absorbed into `coordinated-views`, these chunks need a new home (NOT this skill):

- Line intersection brushing (cross-product math, parcoords-specific)
- Lasso selection (ray-casting, polygonContains)
- Fisheye distortion (cartesian + radial)
- Spatial indexing for intersection testing
- Keyboard brush adjustment

These are brush *mechanics*. They have nothing to do with cross-chart coordination. A merge that drops them is wrong.

## Three structural options for the synthesizer

| Option | Action | Cost | Benefit |
|--------|--------|------|---------|
| **A. Full merge** | All three → `coordinated-views`. ~490 lines compressed to ~250–300. | High: brush mechanics get buried under linking content; the merged skill becomes a kitchen sink. | Single activation target; no triple-conflation. |
| **B. Move-and-keep** | Move linking content from `brushing` into a merged `linked-views + coordination = coordinated-views`. Keep `brushing` focused on mechanics (now ~150 lines). | Medium: requires rewriting `brushing`'s description to drop linking triggers. Two skills instead of three, but `brushing` stays distinct. | Cleanest separation: mechanics vs. coordination. |
| **C. Status quo with cleanup** | Dedup the three SelectionManager classes. Tighten cross-references. Don't merge. | Low: minimal file moves. | Preserves existing block citations and prompt history. Doesn't reduce activation conflation. |

The synthesis must pick one and defend it. Option B is a priori the strongest (it matches what the existing cross-references already imply) but the test phase will tell us whether the discriminator agrees.

## Open questions for synthesis

1. If Option B: where do the SelectionManager class definitions live? In `coordinated-views` only? Both? Cross-referenced?
2. Are framework bridges (React/Vue/Angular) really part of `coordinated-views`, or do they belong in their own (currently nonexistent) `framework-integration` skill?
3. Does Mosaic / DuckDB-WASM / Falcon belong in `coordinated-views` or in a separate `large-data` skill? The current scattering is itself a problem.
4. What's the right name? `coordinated-views` is descriptive but long. Alternatives: `linked-views` (reuse), `dashboards`, `multi-view`. The name affects activation triggering.
