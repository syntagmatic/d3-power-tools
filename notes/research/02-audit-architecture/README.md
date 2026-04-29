# Dossier 02 — Audit Architecture & Protocol

**Status:** draft
**Created:** 2026-04-29
**Last reframed:** 2026-04-29 (was "Evaluation Protocol")
**Question:** What audit data structure, evaluator interface, and comparison protocol does the project need so that dossier graduation criteria are machine-checkable?

## Why this dossier

Dossier 01 set a graduation criterion — "cross-model audit composites within ±0.5 of the pre-refactor baseline" — that the current code cannot mechanically check. The current data layer:

- has no `AuditSchema`, so general-pipeline composites (4-dim weighted) and transition-evaluator composites (`0.6 * t + 0.4 * vc`) are not on the same scale yet wear the same field name
- duplicates the weight tuple in three places, with the iterate scripts overwriting the pipeline's `null`-on-incomplete with their own renormalized value
- writes provenance at run-level only — `(generator_model, judge_model, fixture_id)` per result is impossible
- has no `compare(baseline, treatment)` primitive; comparison is implicit in iterate-script `decide_*` functions
- routes hierarchy-bundles through a separate file (`evals/experiments/hierarchy-bundles-runs.json`) on a separate path, which the audit pipeline never sees

So the gap dossier 01 surfaced is **architectural, not methodological**. A protocol document the architecture doesn't enforce is a wish list. This dossier merges the two: the protocol is the spec, and the deliverable includes running code.

## Layout

```
02-audit-architecture/
├── README.md                  ← this file
├── PROMPT.md                  ← the question, fully stated
├── findings.md                ← architectural review of the current data layer
├── synthesis.md               ← spec for scripts/audit/ + EVALUATION-PROTOCOL.md (synthesizer fills)
├── library-implications.md    ← checklist: code commits, archive, template updates
├── decision.md                ← graduate / iterate / shelve (filled at graduation)
├── critique/
│   └── PROMPT.md              ← role brief for critic agents
└── tests/
    ├── PROMPT.md              ← role brief for tracer-bullet validation
    └── tracer/                ← end-to-end runs of new audit package on real blocks
```

The artifact set is: a working `scripts/audit/` package, a short `notes/EVALUATION-PROTOCOL.md`, updates to `notes/research/_templates/`, and an archive of v1 tooling under tag `v1-pre-research` and `archive/v1/`.

## Lifecycle

```
draft → reviewed → synthesized → critiqued → tested → graduated
        (here once findings.md captures the data layer's failures)
```

`reviewed` is the new state — it replaces the deep-research `researched` state. The deliverable for this stage is `findings.md` as architectural review, not a literature survey.

## Adversarial pairing

Each role records its model in frontmatter. No model may play two roles for this dossier.

- **synthesizer** — writes the architecture spec and the protocol document. Should not have authored the existing `scripts/run-audit-pipeline.py` family.
- **critic** — at least two independent critics. One should be the dossier-01 synthesizer (`gpt-5-codex`) — its prior protocol claims are being indirectly tested.
- **tracer-bullet runner** — implements the spec (or its minimum viable subset) and runs the new package end-to-end on at least one block per schema. Should not be the synthesizer.

## Graduation criteria

The dossier graduates iff:

- ≥2 critics signed off, or all blockers resolved in `critique/responses.md`.
- The new `scripts/audit/` package produces a valid `Run` for at least one block under each declared schema (`GENERAL` and `TRANSITION` at minimum).
- `compare(baseline_run, treatment_run, tolerance=0.5)` runs end-to-end and produces a structured `ComparisonResult` with schema-match assertion, paired diffs, and flag check.
- v1 tooling archived: tag `v1-pre-research` exists; `archive/v1/scripts/` populated; v1 evals archived per the plan in `library-implications.md`.
- `notes/research/_templates/*` updated to reference the new types; a `DOSSIER-README.md` template exists.
- `notes/EVALUATION-PROTOCOL.md` written and ≤1000 words.

If any fails, `decision.md` records `iterate` or `shelve`.

## What this dossier outputs

1. `scripts/audit/` package: `schema.py`, `result.py`, `run.py`, `compare.py`, `evaluator.py`, plus at least `evaluators/general.py` and `evaluators/transition.py`.
2. `notes/EVALUATION-PROTOCOL.md` — short document, references the package by name, encodes the rules the code enforces.
3. Updates to `_templates/CRITIQUE-PROMPT.md`, `TEST-PROMPT.md`, `BLIND-JUDGE-PROMPT.md`, plus a new `DOSSIER-README.md` template.
4. Archive: tag + `archive/v1/scripts/` + `notes/ARCHIVE.md` pointer.
5. Tracer-bullet output in `tests/tracer/` showing the package working on real blocks under both schemas.

## What this dossier does NOT output

- A literature review of LLM-as-judge biases. The protocol picks defenses pragmatically and lists residual biases as accepted; lit citations stay one-sentence.
- Sample-size power calculations. The protocol declares a default N (e.g., 3 generators × 2 judges × 1 fixture) and lets per-dossier README justify deviations.
- A discriminator policy adjudicated in detail. Default is "discriminator stays archived, not a graduation gate"; the synthesis only revisits if there's a credible role for it.
- A "paper pilot" against dossier 01. The tracer bullet replaces it: real runs of the new package, not a hypothetical replay.

## Pre-registrations (locked at draft state)

These are recorded here, before findings, so they can fail later and be visible:

1. **The dossier produces working code, not just a spec.** A document without a runnable `scripts/audit/` is an automatic `iterate` or `shelve`.
2. **Graduation criteria above are locked at draft.** Changes after `findings.md` lands require an explicit entry in `decision.md` noting the change and reason.
3. **The discriminator is treated as evidence, not as a graduation gate**, throughout this dossier and any descendants — unless the synthesis names a specific defensible role for it.
