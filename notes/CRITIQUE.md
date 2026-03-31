# Critique

Dissenting feedback about where the project stands. Full history in `archive/CRITIQUE.md`.

---

## Where the convictions lead

**Date:** March 28, 2026
**Reviewer:** Gemini

How the library has to change if CONVICTIONS.md means what it says.

### Skills should stop teaching D3

Models already know `d3.scaleLinear` from pre-training. The skills that survive compression will be pure decision frameworks: when to use log vs linear, why sqrt for bubble area, when to break the axis. Anti-patterns ("don't force-layout a hierarchy") will outweigh happy-path examples because they prevent more errors per token.

### Multi-skill composition is the real problem

Single skills work fine in isolation. The failures show up when you combine `webgl` + `brushing` + `linked-views` and the state sync, resize handling, and event routing all need to agree. The library needs a standardized contract (shared `d3.dispatch` namespace, common `state` object pattern) that all skills follow. Without it, multi-skill blocks will keep breaking at the seams.

The "floors not ceilings" principle pushes the same direction: strong foundational constraints that guarantee correctness, loose enough that output stays diverse. Measure by variety of valid outputs, not adherence to a template.

### Token efficiency drives everything

Skills get compressed until quality drops, then you stop. Every commit gets tested against an automated eval suite -- different model as judge, not the generator. If a skill edit makes generated blocks worse, the edit is a regression. This is expensive to maintain (symbolic checkers for "visual logic" are hard to write) but there's no honest alternative.

### Static charts are failures

If the conviction that "interaction is the point" is real, every skill should assume brushing, tooltips, and semantic zoom by default. Evaluate by viewer task ("can you find the outliers?"), not code structure ("does it have a brush?").

The self-referential test: if the library can't visualize its own structure (skill dependencies, block scores, audit results) using its own skills, something is wrong.

---

## Plan evaluation

**Date:** March 29, 2026
**Reviewer:** Gemini

The IDEAS.md plan has two parts: simplify (fewer tokens, less redundancy) and validate (adversarial evals on every change).

Simplification: compress block prompts from 160 to 30-60 words, strip API docs from the 6 largest skills (target <300 lines each), merge 11 meta-skills to 6, cull redundant examples.

Validation: automated scoring on every commit, different model as judge to avoid shared bias.

### The judgment-over-API pivot works

Dropping D3 syntax in favor of visualization taste is the right move. The risk is a compression floor -- strip too much implementation detail and the model reverts to its pre-trained defaults. Keep a code idiom next to each judgment call (e.g., `const r = d3.scaleSqrt().range([0, maxR])` alongside the "eye reads area not radius" rule).

### Composition needs a contract, not just docs

The meta-skill consolidation is good but the composition skill can't just be documentation. It needs a concrete interaction contract -- shared `d3.dispatch` namespace, specific state object shape -- that all skills reference. Otherwise multi-skill blocks like `webgl` + `brushing` stay fragile.

### Eval-as-CI is right but heavy

Moving from subjective review to empirical testing is the correct direction. Start with metamorphic testing (change the data, check that the chart updates correctly) before building full model-based grading. Symbolic checkers for visual logic are hard to write and harder to maintain.

### Priority order

1. Consolidate meta-skills (11 to 6) and delete `notes/archive/`. Low effort, immediate cleanup.
2. Compress prompts for blocks 01-10, regenerate, compare. If quality holds, do the rest.
3. Distill the top 6 skills. Anti-pattern content has the best signal-per-token ratio.
4. Wire the eval-as-CI pipeline.

Token efficiency is the binding constraint for AI tool usage right now. The plan gets this right.

---

## Discriminator evaluation

**Date:** March 31, 2026
**Reviewer:** Gemini

The **discriminator training plan** for autoresearch in this project is currently in its "Baseline" phase—the infrastructure is built, but the model is not yet operational for decision-making.

### Current state: the overfitting gap

The discriminator is a Ridge regression model designed to predict a block's `composite` quality score based on 34 structural and semantic features (e.g., `lines`, `d3_api_count`, `has_transition`).

*   **Performance:** It currently has an **R² of 0.56** on training data but a **CV R² of -0.33**. 
*   **Diagnosis:** It is severely overfitting. With only 104 training samples against 34 features, the model is "memorizing" specific blocks rather than learning generalizable D3 quality patterns.

### Feature engineering insights

The model has already yielded high-signal insights despite the overfitting:
*   **Top negative predictors:** `interaction_brush`, `has_geo`, and `function_count`. This suggests that complex, interactive, or boilerplate-heavy blocks currently score lower in audits (likely due to higher "Stress Test" or "Cognitive Load" failure rates).
*   **Top positive predictors:** `d3_api_count` and `has_timer`.
*   **Weakness:** Many features like `renderer_webgl` or `has_reduced_motion` have 0.0 coefficients because they are too sparse in the current dataset.

### Evaluation of the plan

The project's stated plan (found in `notes/TODO.md` and `notes/IDEAS.md`) involves a full audit sweep, heuristic replacement of expensive LLM audits, and visual regression detection.

*   **Full audit sweep:** Fixing data scarcity is the correct first move.
*   **Heuristic replacement:** This "symbolic" discriminator approach is likely to be more robust and cheaper than the linear model for catching technical regressions.
*   **Visual regression detection:** This fills a major blind spot; the linear model cannot yet "see" broken layouts that pass structural checks.

### Strategic recommendations

1.  **Guided compaction:** Feed top coefficients back into `proposer-prompts/block.md` (e.g., "Avoid increasing function_count; ensure RAF coalescing").
2.  **Early-exit filtering:** Use the discriminator to score proposed changes *before* the 600s audit; discard immediately if the predicted score drops >1.0.
3.  **Dimensional specialization:** Train separate small models for `stress_test` (technical) vs `visual_critic` (aesthetic), as predictive features are likely disjoint.
4.  **Feature pruning:** Reduce the 34 features to the top 10 most impactful to improve CV R² until the dataset exceeds 500 samples.

