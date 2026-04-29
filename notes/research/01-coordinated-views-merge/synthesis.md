---
role: synthesizer
model: gpt-5-codex
harness: codex-cli
date: 2026-04-29
status: proposed
---

# Synthesis: coordinated-views merge proposal

## Decision

Choose **Option B: move-and-keep**. Merge `linked-views` and `coordination` plus the cross-chart linking material currently embedded in `brushing` into `coordinated-views`; keep `brushing` as a mechanics skill for drawing, composing, and testing brush/lasso/fisheye selections.

## Proposed shape

```
skills/coordinated-views/
  description: "Design and implement coordinated multi-view D3 dashboards: linked highlighting, cross-filtering, overview+detail, shared selection state, d3.dispatch/store wiring, render priority, and ghost/active feedback. Use when independent charts need to share selection, hover, filter, zoom, or tooltip state. For lasso, intersection brushing, fisheye, or low-level brush geometry, use brushing."
  covers:
    - when views should and should not be linked
    - overview+detail, cross-filtering, ghost/active, shared tooltip patterns
    - canonical keyed SelectionModel with source-tagged events and mode: intersect | union
    - event-bus vs. SelectionModel vs. store architecture
    - source-first render priority, RAF coalescing, reset behavior
    - bitmap masks for high-row-count cross-filtering
  size: ~170-220 lines

skills/brushing/
  description: "Build low-level D3 selection mechanics: d3.brush extents, lasso selection, intersection/strum brushing, fisheye focus, keyboard brush adjustment, spatial indexes, worker offload, and brush composition within a view. Use when the hard part is defining the selected marks, not coordinating multiple charts."
  covers:
    - line intersection brushing
    - lasso selection
    - fisheye distortion
    - pointer events and keyboard brush adjustment
    - spatial indexing and worker offload
    - local brush composition, with cross-view handoff delegated to coordinated-views
  size: ~190-230 lines

skills/linked-views/
  redirect stub -> skills/coordinated-views/

skills/coordination/
  redirect stub -> skills/coordinated-views/
```

`coordinated-views` becomes the interaction contract for multi-view composition. `brushing` remains a top-level skill because the retained mechanics are not incidental: intersection brushing, lasso geometry, fisheye, spatial indexing, and keyboard-adjustable brush extents are each specialized enough to justify loading only when a prompt asks for selection mechanics.

## What changes

### Files moved

- `skills/linked-views/SKILL.md` -> `skills/coordinated-views/SKILL.md`, absorbed and rewritten.
- `skills/coordination/SKILL.md` -> `skills/coordinated-views/SKILL.md`, absorbed and rewritten.
- `skills/brushing/SKILL.md` section `Cross-Chart Linking` -> `skills/coordinated-views/SKILL.md`, rewritten around the canonical keyed `SelectionModel` (the existing `coordination` class name, extended with a per-source filter map and a `mode: "intersect" | "union"` flag).
- `skills/brushing/SKILL.md` section `Brush Composition / ComposableSelectionManager` -> absorbed into `SelectionModel` as `mode: "union"`. The local multi-region (shift-drag) snippet stays in `brushing` but emits a single key set under its source id; cross-source union/intersect is the model's job, not a separate class.
- `skills/brushing/SKILL.md` section `Scalable Cross-Filtering (Falcon Pattern)` -> dropped from `brushing` entirely. Falcon is query-backed prefetch, not brush-time mechanics; it belongs in a future `large-data` / `query-backed-views` dossier and is explicitly out of this merge.

### Files deleted

- No skill path is hard-deleted at graduation. `linked-views` and `coordination` become redirect stubs so existing tool references fail softly.

### Files left as redirect stubs

- `skills/linked-views/SKILL.md`
- `skills/coordination/SKILL.md`

Each stub should be a 3-line skill with matching frontmatter, a one-sentence pointer to `coordinated-views`, and no duplicated guidance.

### Cross-references updated

- `README.md`: replace separate `linked-views` and `coordination` entries with `coordinated-views`; rewrite `brushing` entry to drop cross-chart linking.
- `skills/brushing/SKILL.md`: add top cross-reference: "For chart-to-chart state, render priority, and shared selection contracts, see `coordinated-views`."
- `skills/small-multiples/SKILL.md`: "For brushing and cross-chart linking, see `brushing`" becomes "For local brush mechanics, see `brushing`; for cross-panel coordination, see `coordinated-views`."
- `skills/choreography/SKILL.md`: "coordinating multiple charts, see `coordination`" becomes `coordinated-views`.
- `skills/distributions/SKILL.md`: ghost/active reference changes from `linked-views` to `coordinated-views`.
- `skills/data-table/SKILL.md`: linked highlighting/shared state reference changes from `linked-views` to `coordinated-views`.
- `meta/jig-template/SKILL.md`: replace `linked-views` references for shared state and bitmap indexing with `coordinated-views`; keep local brush state references to `brushing`.
- `meta/calibrate-tool/sharpening-criteria.json`: rename the `linked-views` criterion entry or add a compatibility alias for `coordinated-views`.
- `notes/research/coordination.md`: create a short research note before graduation, because `coordination` currently has no standalone research record.

## What stays out

Brush mechanics stay in `brushing`: line/intersection brushing, lasso point-in-polygon, fisheye distortion, spatial indexing for segment tests, pointer capture/coalesced events, worker offload for geometric tests, keyboard brush adjustment, and local multi-region brush composition.

Framework-specific bridges stay out of the core `coordinated-views` skill. The merged skill may name React/Vue/Angular as an integration risk, but the code patterns should move to a future `framework-integration` or framework-specific note. The current `coordination` skill is too broad here: framework render-loop advice is not the same tier as D3 multi-view coordination.

Mosaic/DuckDB-WASM/Falcon are also not core. `coordinated-views` should keep the bitmap-mask contract for 100K-ish client-side cross-filtering, then point database-backed dashboards to a future `large-data` or `query-backed-views` dossier. Pulling full database integration into this merge would make the new skill a kitchen sink.

## Pre-refactor baseline

No dossier-specific pre-refactor audit run exists yet. Current `evals/best-blocks.json` contains 103 blocks with numeric composites:

```
baseline-run: NOT RUN (required before graduation)
current best-block inventory mean composite: 7.18
current best-block inventory median: 7.20
n: 103 blocks with numeric composites
```

Known exposed blocks from the critique prompt:

```
02-linked-scatterplot-matrix: composite 6.9
13-radial-dendrogram-edge-bundling: composite 7.0
blockbuilder-explorer: composite 7.6
hierarchy-bundles: composite 6.4
```

Graduation must not use the inventory mean as the baseline. Run and freeze a dossier-specific audit against the current pre-merge skills, then compare the merged `tests/skill-under-test/SKILL.md` against that run.

## Why this shape, not the alternatives

**Option A, full merge**, solves activation by force but makes the new skill semantically dishonest. It would hide brush geometry, lasso containment, fisheye, spatial indexing, and keyboard brush manipulation under a multi-view dashboard label; prompts asking for a single-view lasso would load dashboard coordination baggage.

**Option B, move-and-keep**, matches the evidence in `findings.md`: `linked-views` and `coordination` already form a design/wiring pair, while `brushing` is only conflated because it owns a historical cross-chart linking section and duplicate selection managers. This option removes the overlap without deleting real brush mechanics.

**Option C, status quo with cleanup**, would reduce code inconsistency if it canonicalized the selection model, but it does not fix frontmatter activation. Prompts like "linked brushing", "coordinated highlighting", and "cross-filter dashboard" would still reasonably activate all three skills.

I would change my mind if the pre-refactor/merged test run shows that separating mechanics from coordination drops interaction robustness by more than 0.5 composite points, especially through broken reset behavior, inconsistent selected keys, or loss of source-tagged feedback-loop prevention.

## Risks

The main risk is making `coordinated-views` too narrow. If the executable skill only covers event wiring and omits design judgment, generated dashboards may become technically synchronized but visually noisy. If it only covers design patterns and omits the canonical state contract, the merge will reproduce the existing SelectionManager/SelectionModel split under a new name.

The highest-risk block is `02-linked-scatterplot-matrix`, because it needs brush mechanics, linked highlighting, scale stability, ghost/active feedback, and render scheduling in one artifact. `hierarchy-bundles` is exposed if hover/selection coordination crosses hierarchy and edge-bundling concepts. `blockbuilder-explorer` is exposed because it is large enough for update storms and stale listeners to matter. `13-radial-dendrogram-edge-bundling` should be mostly protected by keeping brush mechanics out of the merge.

Worst-case score drift is likely on `stress_test`, not `visual_critic`: feedback loops, stale selection identity, or render storms could plausibly drop affected coordinated blocks by 1-2 points even if screenshots still look acceptable.

Rollback path: restore `linked-views` and `coordination` from the previous commit, keep the canonical keyed `SelectionModel` as a shared snippet, and retain only the `brushing` frontmatter cleanup if tests show activation improved without score loss.

## Resolved during synthesis

1. **Canonical name = `SelectionModel`** (resolved). Kept from existing `coordination` skill rather than minting a new `SelectionState`. Extended in-place with per-source filter map and `mode: "intersect" | "union"`. Existing block citations of `SelectionModel` continue to read correctly; `SelectionManager` / `ComposableSelectionManager` (from `brushing`) become removals, not renames.
2. **URL serialization = out** (resolved). Removed from `coordinated-views`. Treated as application-state concern; if it returns, it lands in a separate dossier. Encoding `k/x/y` zoom transforms and selected keys is not visualization-grammar guidance.
3. **`ComposableSelectionManager` fate = absorbed** (resolved). Folds into `SelectionModel` as `mode: "union"`. The class doesn't survive in either skill.

## Open questions deferred to critique / test

1. Should local brush composition in `brushing` emit keyed selections directly, or remain index-based with an explicit handoff adapter?
2. Should the test fixture include keyboard reset/escape behavior, or is pointer-driven selection enough for the first graduation gate?
3. Should redirect stubs count as retained skills in the taxonomy README, or only exist for compatibility in the filesystem?
