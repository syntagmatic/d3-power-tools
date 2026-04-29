# Dossier 02 — Evaluation Protocol

**Status:** draft
**Created:** 2026-04-29
**Question:** How should a skill-refactor dossier measure whether its proposed change is an improvement?

## Why this dossier

Dossier 01 (`coordinated-views-merge`) surfaced a methodology gap that every future dossier inherits unless we fix it now: the audit pipeline scores rendered HTML, but skill refactors are claims about generation quality. Auditing the four existing exposed blocks gives a regression floor; it is not the apples-to-apples comparator that the graduation criterion ("within ±0.5 of baseline") implies. This dossier exists to design the protocol — what counts as baseline, how many generators, how judges are calibrated, what's pre-registered, what counts as a negative result — before we run it for real.

This is **deep research**: the synthesizer is expected to do a lit review (LLM-as-judge, counterfactual eval, sample-size for paired comparisons, pre-registration) plus an empirical examination of the project's own prior artifacts (`notes/V2-FINDINGS.md`, `notes/AUTORESEARCH.md`, `notes/CRITIQUE.md`, `evals/anchors.json`, `evals/discriminator.json`).

## Layout

```
02-evaluation-protocol/
├── README.md                  ← this file
├── PROMPT.md                  ← the question, fully stated
├── findings.md                ← lit review + empirical examination of project artifacts
├── synthesis.md               ← proposed protocol (filled by synthesizer)
├── library-implications.md    ← checkboxed migration plan (template & docs updates)
├── decision.md                ← adopt / iterate / shelve (filled at graduation)
├── critique/
│   └── PROMPT.md              ← role brief for critic agents
└── tests/
    ├── PROMPT.md              ← role brief for pilot runs
    └── pilot/                 ← empirical pilot: re-test dossier 01 under proposed protocol
```

There is no `skill-under-test` here. The artifact is a protocol document plus revisions to `notes/research/_templates/`.

## Lifecycle

```
draft → researched → synthesized → critiqued → piloted → graduated
                                                  ↑ on dossier 01 data
```

## Adversarial pairing

Each role records its model. No model may play two roles for this dossier. Recommended assignments:

- **synthesizer** — a model that did **not** synthesize dossier 01 (dossier 01's synthesizer was `gpt-5-codex`). Suggest Claude Opus or Gemini Pro.
- **critic** — at least two, one of which is the dossier-01 synthesizer (`gpt-5-codex`) so a model whose work is being indirectly examined gets to push back.
- **pilot runner** — uses the proposed protocol to re-evaluate dossier 01's question. Should not be the synthesizer.

## Graduation criteria

A protocol graduates iff:
- ≥2 critics signed off, or all blockers resolved in `critique/responses.md`.
- The pilot in `tests/pilot/` produces a decision recommendation for dossier 01 that is either (a) consistent with dossier 01's own decision when it lands, or (b) flags a specific dossier-01 weakness that the old protocol missed.
- All checkboxes in `library-implications.md` ticked, including updates to `notes/research/_templates/*.md`.

If any fails, `decision.md` records `iterate` or `shelve`.

## What this dossier outputs

1. A revised evaluation protocol document (likely `notes/EVALUATION-PROTOCOL.md`).
2. Updates to `notes/research/_templates/CRITIQUE-PROMPT.md`, `TEST-PROMPT.md`, `BLIND-JUDGE-PROMPT.md`.
3. Updates to the dossier-level README template and `library-implications.md` template.
4. A standard fixture corpus, if the synthesizer concludes per-dossier custom fixtures harm comparability.
5. A recommendation on the discriminator's role — graduation gate, sanity check, or shelf.
