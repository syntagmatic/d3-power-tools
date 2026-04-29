# Library Implications

Per-action checkboxes. Tick in the same commit as the change. The first three sections are pre-synthesis discipline; everything after the synthesis lands becomes concrete commits.

## Pre-synthesis prep

- [x] `findings.md` populated with architectural review of the current data layer
- [ ] `findings.md` reviewed by maintainer (sanity check on findings F1–F8 before synthesis)
- [ ] Pre-registrations in README (lines under "Pre-registrations") confirmed; any disagreement surfaces here

## Synthesis phase

- [ ] `synthesis.md` committed with frontmatter (`role: synthesizer`, `model:`, `date:`)
- [ ] Synthesis specifies file-by-file the contents of `scripts/audit/`: `schema.py`, `result.py`, `run.py`, `compare.py`, `evaluator.py`, `evaluators/general.py`, `evaluators/transition.py`
- [ ] Synthesis names the on-disk JSON shape with a concrete example for both `Run` (general schema) and `Run` (transition schema)
- [ ] Synthesis specifies the `compare()` signature and the `ComparisonResult` shape
- [ ] Synthesis includes a one-paragraph defense for each of: lit review depth, sample-size methodology, discriminator role
- [ ] `notes/EVALUATION-PROTOCOL.md` drafted (≤1000 words) and referenced from `synthesis.md`

## Critique phase

- [ ] Critic 1 review filed (`critique/by-critic-<model>.md`)
- [ ] Critic 2 review filed
- [ ] At least one critic is the dossier-01 synthesizer (`gpt-5-codex`), or an explicit note explains why this wasn't possible
- [ ] Maintainer responses filed (`critique/responses.md`)
- [ ] All blockers resolved or explicitly accepted

## Tracer-bullet phase

- [ ] Tracer-bullet runner produces `tests/tracer/by-runner-<model>.md`
- [ ] `scripts/audit/` package exists at minimum-viable scope (schema + result + run + one general evaluator + one transition evaluator + compare)
- [ ] Tracer runs end-to-end on at least one block using `evaluators/general.py` → produces a valid `Run`
- [ ] Tracer runs end-to-end on at least one block using `evaluators/transition.py` → produces a valid `Run`
- [ ] `compare(baseline, treatment, tolerance=0.5)` returns a structured `ComparisonResult` against synthetic inputs
- [ ] Tracer report names what was stubbed for the bullet and what fails loudly when called outside that scope

## Code commits (filled when synthesis lands)

> Synthesis defines the exact file contents. These are the concrete commits the tracer-bullet runner is expected to produce.

### `scripts/audit/` package

- [ ] `scripts/audit/__init__.py` exports public surface
- [ ] `scripts/audit/schema.py` — `AuditSchema` dataclass + `GENERAL` + `TRANSITION` instances + validation
- [ ] `scripts/audit/result.py` — `AuditResult` dataclass with provenance, `composite()`, `is_complete()`, `to_dict`/`from_dict`
- [ ] `scripts/audit/run.py` — `Run` dataclass + run-level provenance + JSON I/O
- [ ] `scripts/audit/compare.py` — `compare(baseline, treatment, tolerance) → ComparisonResult` with schema-match assertion
- [ ] `scripts/audit/evaluator.py` — Evaluator protocol/ABC + registry
- [ ] `scripts/audit/evaluators/general.py` — replaces logic in `run-audit-pipeline.py` for the 4-dim schema
- [ ] `scripts/audit/evaluators/transition.py` — replaces logic in `eval-hierarchy-bundles.py` for the 2-dim schema

### Tests

- [ ] Round-trip JSON test for `AuditResult` and `Run` (from_dict ∘ to_dict ≡ identity)
- [ ] `compare()` schema-mismatch raises explicitly
- [ ] `compare()` flag-set change is reflected in `ComparisonResult`
- [ ] `compute_composite()` renormalizes correctly when one dimension is missing
- [ ] `compute_composite()` returns None when no dimensions are present (rather than divide-by-zero)

## Archive

- [ ] `git tag -a v1-pre-research -m "Pre-research-pivot snapshot"` at current SHA
- [ ] `archive/v1/scripts/` populated with: `run-audit-pipeline.py`, `iterate-block.py`, `iterate-prompt.py`, `iterate-campaign.py`, `iterate_lib.py`, `eval-hierarchy-bundles.py`, `generate-blocks-claude.py`, `generate-blocks-gemini.py`, `extract-features.py`, `train-discriminator.py`, `proposer-prompts/`
- [ ] Decision recorded on whether `archive/v1/evals/` is populated now or after this dossier's synthesis consumes the inputs
- [ ] `archive/v1/README.md` written: 1 paragraph "this is the pre-research project state, frozen at tag v1-pre-research, do not modify"
- [ ] `notes/ARCHIVE.md` written: pointer to tag + archive directory + brief explanation
- [ ] `archive/` added to `.rgignore` (or equivalent) so `rg` defaults exclude it

## Templates

- [ ] `notes/research/_templates/CRITIQUE-PROMPT.md` updated to reference the new `Run`/`ComparisonResult` types in question 4 (audit-axis alignment) and question 6 (migration risk)
- [ ] `notes/research/_templates/TEST-PROMPT.md` updated: alt-generators write `Run` JSON via `scripts/audit/`; the dossier's comparison goes through `compare()`
- [ ] `notes/research/_templates/BLIND-JUDGE-PROMPT.md` updated: judge results land as `AuditResult` with judge_model in provenance
- [ ] New `notes/research/_templates/DOSSIER-README.md` extracted from this dossier and dossier 01's READMEs, including the "pre-registrations" section convention
- [ ] New `notes/research/_templates/LIBRARY-IMPLICATIONS.md` extracted from this file as a reusable shape

## Protocol document

- [ ] `notes/EVALUATION-PROTOCOL.md` written (≤1000 words). Encodes only what the code enforces. Lists residual judge biases as accepted.
- [ ] `notes/CONVICTIONS.md` cross-references `EVALUATION-PROTOCOL.md` from the relevant entries

## Discriminator policy

- [ ] Default decision recorded: archived, not a graduation gate
- [ ] If synthesis revives it: role specified (gate / sanity check), threshold or improvement criterion documented, dataset-size remediation plan attached
- [ ] If kept archived: `evals/discriminator.json` moved to `archive/v1/evals/discriminator.json` (with the rest of v1 evals)

## Backfill into dossier 01

- [ ] Dossier 01's `library-implications.md` graduation gates rewritten in terms of the new types (`Run` composites, `compare()` verdict, `ComparisonResult` flag check)
- [ ] Dossier 01's `critique/PROMPT.md` question 3 (discriminator-driven conflation) downgraded from "graduation gate" to "evidence" — or removed if synthesis archives the discriminator
- [ ] Dossier 01's fixture `tests/fixtures/iris/` task spec sharpened so alt-generators have a concrete deliverable (precondition for fair cross-generator comparison)
- [ ] Dossier 01's tests/PROMPT.md updated so alt-generators write through the new `Run` shape

## Post-graduation

- [ ] Decision archived in `decision.md`
- [ ] Dossier status set to `graduated`
- [ ] First post-protocol dossier (dossier 03+) opened against the new architecture — note the dossier number here when filed
- [ ] Memory updated: a short entry in `MEMORY.md` recording the pivot, with date
