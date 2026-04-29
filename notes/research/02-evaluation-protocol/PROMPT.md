# Question

How should a skill-refactor dossier measure whether its proposed change is an improvement?

This is a methodology question, not a taxonomy question. Dossier 01 produced a synthesis with a graduation criterion — "cross-model audit composites within ±0.5 of the pre-refactor baseline" — without specifying what generates the baseline, how many comparisons are needed, what variance to expect, or what counts as a negative result. Future dossiers will copy that pattern unless we replace it with something defensible.

## Why now

Dossier 01's synthesis surfaced concrete artifacts of this gap:

- The audit pipeline (`scripts/run-audit-pipeline.py`) scores rendered HTML against four inspection skills. It does not load the skills under test; their content is not in the loop. So auditing the four named exposed blocks (`02-linked-scatterplot-matrix`, `13-radial-dendrogram-edge-bundling`, `hierarchy-bundles`, `blockbuilder-explorer`) gives a snapshot of how those static artifacts score today, not how the merged skill would generate.
- `library-implications.md` lists "alt-generator A produced iris block" as a graduation gate but never declares the matching control — i.e. iris generations under the *current* unmerged library. Without that, baseline and treatment use different prompts.
- `notes/CRITIQUE.md` records the discriminator at CV R² ≈ -0.33 (severely overfit) and identifies brush/link/coord conflation as one driver. The synthesis claims to reduce that conflation but the dossier has no plan to verify it.
- `notes/V2-FINDINGS.md` shows skills can hurt sonnet performance (timeout-driven) — meaning "skill quality" interacts with model capability in ways the audit pipeline doesn't surface.

If a future dossier proposes splitting `cartography` or merging `time-series` and `motion`, we want a protocol it can copy, not a pattern that has to be reinvented per dossier.

## What to learn

### 1. Baseline definition

What is the right counterfactual for a skill-refactor dossier? Three candidates:

- **Block snapshot.** Audit the existing exposed blocks today. Cheap. Doesn't measure generation; only regression on static artifacts.
- **Paired generation.** Same fixture, same alt-generators, generate twice — once under the current library, once under the proposed skill. Audit both. Apples-to-apples but doubles cost.
- **Held-out fixture suite.** A standard corpus (n fixtures, fixed) hit by every coordination-related dossier. Comparable across dossiers but per-dossier specificity drops.

Which (or which combination) should be required, recommended, optional? When does each apply?

### 2. Sample size and statistical power

Today the implicit sample is 3 alt-generators × 1 fixture = N=3 per condition. What's the variance across LLM generations of the same prompt at temperature ~1? What effect size matters? Is a 0.5-composite shift detectable at N=3, and if not, what N gets us 80% power on the smallest interesting effect?

The lit on paired LLM generation comparison and on small-N evaluation methodology (Chatbot Arena, AlpacaEval, MT-Bench) is directly relevant.

### 3. Judge calibration and bias

LLM-as-judge has known biases: position, length, self-preference, verbosity. The current audit anchors (`evals/anchors.json`) catch drift beyond ±2 but don't address ordering effects within a single audit run. Cross-judge agreement is target but not measured systematically.

What concrete calibration moves should every dossier do? Which can be standardized in the inspection skills, which need per-dossier fixtures?

### 4. The discriminator's role

`evals/discriminator.json` is a Ridge regression on 34 features, currently overfit (R² 0.56 train / -0.33 CV). It exists; it isn't used as a graduation gate. Should it be? Options:

- **Gate** — discriminator must improve (less overfit, higher CV R²) for a merge to graduate. Strong claim; dataset may not support it.
- **Sanity check** — print discriminator scores in dossier output but don't gate on them.
- **Shelve** — the symbolic checks in `notes/CRITIQUE.md` are the real signal; deprecate the linear model.

### 5. Anti-leakage

`tests/PROMPT.md` says "use only the skill under test." Enforcement is a prompt instruction. Models can leak patterns from training data, from other skills they have memorized, or from the broader CLAUDE.md context. The `multi-skill-leak` flag exists in `BLIND-JUDGE-PROMPT.md` but is binary and judge-discretion.

How do we measure leakage with something better than judge intuition? Is it worth measuring at all, or is it inevitable noise?

### 6. Pre-registration

When does a graduation criterion get fixed? Today it's specified in `synthesis.md` after `findings.md` is written, and the synthesizer can tune it. That's not pre-registration in the medical-trial sense; it's post-hoc framing. Should graduation criteria be set in `PROMPT.md` (before the question is even researched) instead?

### 7. Negative-result handling

`decision.md` template has graduate / iterate / revert. The iteration loop is unspecified — how many revisions, with what changes between them? When does iterate become revert? When does shelving become an option (the dossier was the wrong question)?

### 8. Cost and cadence

A merge dossier currently runs ~3 generators × ~M fixtures × ~2 judges = O(few dozen) LLM calls. At what cadence is this affordable, and does that constrain how aggressively the taxonomy should refactor?

### 9. Standard fixtures

Should a corpus of fixtures live in `notes/research/_fixtures/` (analogous to `_templates/`) so coordination-related dossiers all hit the same iris/dashboard/scatter cases? Or is per-dossier custom fixturing right because each merge has its own evidentiary needs?

## Out of scope

- The taxonomy refactor itself. This dossier produces protocol; it does not decide whether `coordinated-views` should exist.
- Generation-time prompts (system prompts, CLAUDE.md content). That's a separate engineering question about how skills get loaded.
- Per-block iteration methodology. `notes/AUTORESEARCH.md` already documents that loop and it works; this dossier is about cross-block, cross-skill comparison.

## Background

- Source proposal: this dossier was filed during dossier 01's synthesis review (2026-04-29) when the baseline question surfaced.
- Existing methodology artifacts:
  - `notes/AUTORESEARCH.md` — per-block iteration loop (working)
  - `notes/V2-FINDINGS.md` — empirical pass-rate data across model × skill conditions
  - `notes/CRITIQUE.md` — prior critic feedback including the discriminator state
  - `evals/anchors.json` — calibration anchors for inspection skills
  - `evals/discriminator.json` — current overfit Ridge model
  - `notes/research/_templates/` — current critique/test/judge prompt templates
- LLM-eval lit the deep-research phase should canvas at minimum:
  - LLM-as-judge bias & calibration (Zheng et al. "Judging LLM-as-a-Judge", recent follow-ups through 2025)
  - Pairwise comparison and Bradley-Terry scoring (Chatbot Arena methodology)
  - Pre-registration practice from psychology / clinical trials adapted to AI eval
  - Sample-size planning for paired comparisons at small N

## What "deep research" means here

The synthesizer is expected to:
1. Read all listed background artifacts in this repo before writing `findings.md`.
2. Conduct a focused literature review on the points listed under "What to learn" — at least 6-10 cited references, each with a one-sentence relevance note.
3. Where lit and project state disagree, surface the disagreement explicitly rather than picking a side silently.
4. Run a paper pilot in `tests/pilot/` against dossier 01: take its current synthesis and library-implications, apply the proposed protocol, and write what would change. The pilot's value is in the *delta*, not in repeating dossier 01's work.

The synthesis should land on a concrete, copyable protocol — not a survey. If a survey is the right answer, that itself is a finding worth defending.
