---
role: critic
model: claude-opus-4-7
harness: claude-code
date: 2026-04-29
synthesis-rev: 40b1ffa
also-critiqued-dossier-01: false
---

# Critique — Dossier 02 (Audit Architecture & Protocol)

## 1. Schema discipline

The schema is loud at one chokepoint and silent everywhere else. `compare.py` ("Architecture / scripts/audit/compare.py") refuses mismatched-schema pairings and forbids cross-schema composite aggregation. Good.

But `AuditSchema` is plain data: a string id and a tuple of weighted dimensions. Any consumer that reads `Run.results` and does its own arithmetic — a future dashboard, a leaderboard, a one-off notebook — can average composites across schemas without any object refusing. The schema label is descriptive, not contractually enforced. The synthesis names the prohibition only in the protocol document, which is text, not code. `CompositeSnapshot.value` is a bare `float`; two snapshots from different schemas can be subtracted manually with no type complaint.

Either upgrade the type — a `Composite` value object that overloads subtraction and refuses on `schema_id` mismatch (~20 LOC) — or stop claiming `AuditSchema` makes mismatches "loud." `compare()` is a chokepoint, not a wall.

## 2. Composite comparability

The structured `CompositeSnapshot` (value/policy/schema_id/complete/missing_dimensions) and `from_dict`'s rejection on stored-snapshot/schema mismatch is the second-best decision in the synthesis. Composites are now self-describing.

The gap is the same as Q1: round-tripping the snapshot is documentary, not load-bearing. There is no worked example in the synthesis showing what happens when a future caller computes `mean([r.composite.value for r in run.results])` across mixed schemas. The answer today: nothing — silent, wrong number. The protocol forbids it; the type system permits it. Worked example missing; please add one or admit the discipline is convention.

## 3. Provenance integrity

Per-result provenance on `AuditResult.provenance` (block_id, fixture_id, generator_model, judge_model, evaluator_id, block_sha, timestamp, skill_shas) is correctly placed and strictly validated by `from_dict`. This is the strongest decision in the synthesis.

But the legacy story is elided. Dossier 01's graduation gate is "cross-model audit composites within ±0.5 of *pre-refactor baseline*" — i.e., audits captured under v1, which carries none of these fields. Synthesis says "old audit data is archive-only unless explicitly migrated or rerun" — and then names no migration and no rerun. So the v2 architecture forecloses on the dossier it was built to support. There is no v2-shaped baseline.

Either: (a) schedule a one-time rerun of the pre-refactor baseline against v2 evaluators as a graduation milestone (and put it in `library-implications.md`), or (b) loosen dossier 01's criterion to "newly captured baseline." The current text papers this over with archive rhetoric.

## 4. Pre-registration mechanics

The README claims graduation criteria are "locked at draft." The synthesis proposes `scripts/dossier/check.py` to validate that pre-registration fields *exist*. That is a presence check, not a lock. Nothing prevents a synthesizer from editing the README's "Graduation criteria" section after `findings.md` lands; git history records it, but no script refuses it.

Two options: hash the README's graduation-criteria section at the draft-state commit, store the hash in dossier metadata (`graduation_criteria_hash`), have `scripts/dossier/check.py` recompute and refuse on drift unless `decision.md` carries a matching change-entry — ~30 LOC; or downgrade the claim to "honor-system, recorded in git." Either is fine. The current rhetorical inflation ("locked at draft") plus a presence-only check is the worst combination.

Same critique applies to adversarial pairing: frontmatter is self-reported. The harness does not attest model identity. Honor-system. Name it.

## 5. Migration honesty

27MB of `evals/iterations/` and 1.2MB of `evals/runs/` — ~200+ historical iteration runs — are archived. The synthesis writes "old audit data is archive-only unless explicitly migrated or rerun" and then names neither.

What is lost in spirit, not just in preservation: every prior audit becomes evidence the new comparison primitive cannot consume. Tag-preserves-everything is technically true and substantively misleading. After graduation, "pre-refactor" lives in v1 shape and "post-refactor" in v2; the pivot makes dossier 01's claim *harder*, not easier, unless a baseline rerun is scheduled. The synthesis's silence on this is the most important honesty failure in the document.

## 6. Cost and scope creep

`scripts/audit/` is plausibly tight — schema/result/run/compare/evaluator plus two evaluators, estimate 800–1500 LOC. No plugin system, no event bus, no config loader. Good shape.

The creep is `scripts/iterate/` (loop.py, policies.py, adapters.py). The dossier's stated question is *audit data structure, evaluator interface, and comparison protocol*. F6 motivates iteration consolidation; it does not require it *for graduation*. The tracer-bullet gates and graduation criteria do not mention `scripts/iterate/`. The synthesis even draws a "boundary" — but the boundary is at generation/staging/reporting, not at iteration. The wrong line.

Cut `scripts/iterate/` from this dossier. The synthesizer is trying to graduate one dossier by bundling a second inside it. With it cut, tracer scope shrinks, critique surface narrows, and the "architecture + protocol" framing in the README stays honest. With it included, this is two refactors masquerading as one.

## 7. What's missing

Three protocol silences future dossiers will hit:

- **Split** (one skill into two): treatment is *two* runs against one baseline; both must preserve their subsets *and* avoid co-activation. `compare()` is binary. There is no `compare_split(baseline, treatment_a, treatment_b)`. Synthesis hand-waves "merge/split/delete share primitives but not evidence requirements" without showing how.
- **Delete** with no replacement: the baseline is an absence, not a `Run`. The architecture has no representation for "compare against the null treatment." Either define a null-Run convention or admit delete dossiers will need a separate primitive.
- **Tracer stubbing trivializes the graduation gate.** `general.evaluate()` may run only `visual_critic` for the tracer with status `incomplete` and policy `renormalize_partial`. The corresponding library-implications gate is "Tracer runs end-to-end on at least one block using `evaluators/general.py` → produces a valid `Run`." A 1-of-4-dimension `incomplete` result satisfies that wording. Either tighten to "complete general schema" or admit the tracer does not prove what the gate text implies.

## Single most consequential reconsideration

**Cut `scripts/iterate/` from this dossier.** The synthesizer is graduating one stated dossier (audit architecture + protocol) while quietly bundling a second (iteration consolidation) inside it. Without that cut, the tracer-bullet runner has too much to build, the critique surface is too wide, and the README's "merge architecture and methodology" claim quietly becomes "merge architecture, methodology, and the iteration loop" — a different and harder claim than the one this dossier was opened to answer.
