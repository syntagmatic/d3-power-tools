# Question

What audit data structure, evaluator interface, and comparison protocol does the project need so that dossier graduation criteria are machine-checkable?

This is an **architecture-with-protocol** question, not a methodology survey. Dossier 01 specified a graduation criterion ("cross-model audit composites within ±0.5 of pre-refactor baseline") that the current data layer cannot mechanically check. The fix is partly code (new types, comparison primitives, schema discipline) and partly the rules the code enforces (per-dossier baseline, adversarial pairing, pre-registration). The two cannot be separated without producing a paper spec the code never catches up to.

## Why now

Dossier 01's synthesis exposed the gap; an architectural review (`findings.md`) confirmed it is real:

- The composite formula `(visual_critic 0.30, encoding_integrity 0.25, cognitive_load 0.25, stress_test 0.20)` is duplicated across `run-audit-pipeline.py`, `iterate-block.py`, and `iterate-prompt.py`. The pipeline writes `composite: null` when any dimension is missing; the iterate scripts overwrite that null with a renormalized value. The two policies disagree silently.
- The transition evaluator (`eval-hierarchy-bundles.py:843`) computes `0.6 * t_score + 0.4 * vc` inline. There is no `TRANSITION_WEIGHTS` dict. Its results land in `evals/experiments/hierarchy-bundles-runs.json`, a different file the audit pipeline never reads.
- An iterate script that renames `block_id` from `hierarchy-bundles` would silently start sending it through the general pipeline, producing a different composite on a different scale, with no error.
- Provenance — `(generator_model, judge_model, fixture_id, skill_shas)` — is recorded at run-level. There is no way to ask "show me only the audits where the judge was Sonnet and the generator was Gemini Flash."
- There is no `compare(baseline, treatment)` primitive. The iterate scripts' `decide_*` functions implicitly compare, but they don't produce a structured comparison artifact other consumers can read.
- The JS index reader at `evals/iterations/index.html:291` reads `composite_after ?? scores.composite`, treating null as a fallthrough rather than a signal — confirming nothing downstream interprets null as "incomplete." The pipeline's null-policy is dormant code masking a buggy interaction with the iterate scripts.

A future dossier proposing to split `cartography` or merge `time-series + motion` will hit the same wall. The fix is one-time, project-wide, and must touch both code and protocol.

## What to learn

Six concrete questions. Each must produce a decision recorded in `synthesis.md`.

### 1. What is an `AuditResult`, and what is its schema?

The data class is the smallest load-bearing decision. Sub-questions:

- Should `AuditResult` carry an `AuditSchema` reference, so `composite()` always knows its own weights?
- Are `flags` per-dimension or top-level? (Today: top-level, populated only by stress_test; transition evaluator stuffs `programmatic_issues` here too.)
- What fields belong to provenance — `generator_model`, `judge_model`, `fixture_id`, `block_sha`, `skill_shas`, `timestamp` — and do they sit on `AuditResult` or only on `Run`?
- Round-trip JSON: is the on-disk shape declared in `audit_result.py` or only emergent from `to_dict`/`from_dict`?

### 2. What is an `Evaluator`, and how does dispatch work?

Today, `iterate-prompt.py:49` branches `if block_id == "hierarchy-bundles"`. That's the seam, hidden inside one script. Sub-questions:

- Is `Evaluator` a protocol/ABC, or just a callable signature `(html_path, ctx) → AuditResult`?
- Does the registry live in `evaluator.py` (a dict), or does each evaluator self-register?
- How does a caller pick — by block_id (today's pattern), by config, by an evaluator slug declared on the block, by something else?
- What does an evaluator do *besides* score? It must declare its schema (so callers can compare). Does it also declare its required fixture shape?

### 3. What does `compare()` produce, and what does it refuse?

The graduation criterion "within ±0.5 of baseline" needs a single function call. Sub-questions:

- Signature: `compare(baseline: Run, treatment: Run, tolerance: float) → ComparisonResult`?
- What's in `ComparisonResult`: `schema_match: bool`, `per_dimension_diff: dict`, `composite_diff: float`, `flag_set_change: dict`, `render_error_count: int`, `verdict: "pass" | "fail" | "inconclusive"`?
- What does it refuse loudly? Schema mismatch (different evaluator) → `ValueError`. Different block sets → `ValueError`. Different fixtures → warning or error?
- Is it pure, or does it write a comparison record to disk for the dossier to consume?

### 4. What rules does the protocol document encode that the code enforces?

`notes/EVALUATION-PROTOCOL.md` is short. It documents only what the code makes mechanical:

- Per-dossier baseline declared in the dossier README **before** `findings.md` lands.
- Graduation criteria locked in `synthesis.md` before `tests/tracer/` runs; later changes require an explicit entry in `decision.md`.
- Adversarial pairing read from frontmatter in role files; the comparison or the dossier-graduation script asserts no role conflict.
- Default N: 3 generators × 2 judges × 1 fixture. Per-dossier deviations stated and justified in the dossier README.
- Judge biases mitigated via the audit anchors in `evals/anchors.json` (or its successor) and the inspection-skill rubrics; biases explicitly accepted (position, length, self-preference within Anthropic-family judges) listed by name.
- Discriminator: archived; not a graduation gate. Synthesis may name a specific role to revive it, with justification.

The protocol document **must not** describe rules the code doesn't enforce. If a rule cannot be mechanized, it stays out, or the synthesis says explicitly "this is honor-system."

### 5. What's the migration story?

There are 27MB of historical iterations in `evals/iterations/` and 1.2MB of runs in `evals/runs/`. None of it is in the new schema. Sub-questions:

- Tag `v1-pre-research` at current SHA; move v1 scripts to `archive/v1/scripts/`. Move v1 evals to `archive/v1/evals/` after dossier-02-pilot has used them, or now with PROMPT.md path updates?
- New shape on disk: same path (`evals/runs/`) with a different schema, or new path (`evals/runs-v2/`) for clarity?
- What does the new `scripts/audit/` read on first run when `evals/runs/` is empty? Does it gracefully bootstrap, or require an initial audit to seed?

### 6. What does the tracer bullet test, and what's it allowed to skip?

The graduation gate requires the new package working end-to-end on at least one block per schema. Sub-questions:

- Tracer-bullet block selection: which two blocks (one general, one transition)?
- What does "end-to-end" mean — render + audit + write Run + compare against a synthetic baseline + read back?
- What's allowed to be a stub? `evaluators/general.py` could call only `visual_critic` instead of all four dimensions for the tracer; `compare.py` could ignore flags for the tracer. Synthesis declares what's stubbed.
- What does the tracer not test? (Likely: multi-fixture comparison, full provenance round-trip, the JS index regeneration.)

## Out of scope

- The taxonomy refactor itself. This dossier produces architecture and protocol; it does not decide whether `coordinated-views` should exist.
- Generation-time prompts (system prompts, CLAUDE.md content). Separate concern.
- Per-block iteration methodology. `notes/AUTORESEARCH.md` documents that loop and it works for what it does. The new architecture should preserve at least one path through it (or explicitly archive `iterate-block.py` and replace it later in a separate dossier).
- `pipelines/generate.py` — block generation under research conditions. The dossier protocol may sidestep it; defer.
- Discriminator revival. Default-archived; only resurrected if the synthesizer names a credible role.

## Background

- `notes/research/01-coordinated-views-merge/` — the dossier whose graduation criterion is currently uncheckable.
- `findings.md` (this dossier) — the architectural review surfacing the gap.
- `notes/AUTORESEARCH.md` — the per-block iteration loop the new architecture must not silently break.
- `notes/V2-FINDINGS.md` — empirical model × skill data; useful as input to the synthesis if it bears on default N.
- `notes/CRITIQUE.md` — prior critic feedback, including discriminator state.
- `notes/CONVICTIONS.md` — project principles. The synthesis must not contradict.
- `evals/anchors.json`, `evals/discriminator.json` — current calibration and discriminator artifacts; in scope for archival decisions.
- `scripts/run-audit-pipeline.py`, `scripts/iterate-block.py`, `scripts/iterate-prompt.py`, `scripts/iterate_lib.py`, `scripts/eval-hierarchy-bundles.py` — current pipeline and iteration code, the targets of replacement.

## What "implementation milestone" means here

The synthesizer is expected to:

1. Produce `synthesis.md` as a spec for `scripts/audit/`: file-by-file, class-by-class, with on-disk JSON shapes given as concrete examples.
2. Produce `notes/EVALUATION-PROTOCOL.md` (≤1000 words) documenting the rules the package enforces.
3. List in `library-implications.md` every code commit and template update required for graduation.
4. Justify cuts: literature review depth, sample-size methodology, discriminator role — each with a one-paragraph defence in the synthesis.

The synthesizer is **not** expected to:

- Write the code. Implementation is the tracer-bullet runner's job.
- Produce a survey paper. This is a project-internal architecture document, not a publication.
- Defend every protocol choice with statistics. Pragmatism + a clear residual-risk list is acceptable.

If the synthesizer concludes the right answer is "the architecture is fine, the methodology gap is real and separate," that itself is a finding. State it in `synthesis.md` and bring receipts.
