# Tracer-Bullet Prompt — Dossier 02 (Audit Architecture & Protocol)

You are running the **tracer-bullet validation** for this dossier. Your role: implement the spec in `synthesis.md` (or its minimum-viable subset, declared up front) and prove the new package works end-to-end on real blocks.

This is **running code**, not a paper analysis. The deliverable is the new `scripts/audit/` package plus a short report — not a hypothetical replay of dossier 01.

## Inputs

- `notes/research/02-audit-architecture/synthesis.md` — the spec to implement
- `notes/research/02-audit-architecture/findings.md` — context on what the data layer was missing
- `notes/research/02-audit-architecture/library-implications.md` — the commit checklist
- `scripts/run-audit-pipeline.py`, `scripts/eval-hierarchy-bundles.py` — current logic to mirror in the new evaluators
- `meta/visual-critic/SKILL.md`, `meta/encoding-integrity/SKILL.md`, `meta/cognitive-load/SKILL.md`, `meta/stress-test/SKILL.md` — inspection skills the general evaluator runs
- `blocks/manifest.json` — block IDs and prompts
- One general-schema test block (suggested: `02-linked-scatterplot-matrix`)
- One transition-schema test block (must be: `hierarchy-bundles`)

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md` for this dossier.

## Task

Produce three things in this order. Stop and report if any step fails.

### Step 1 — Implement the minimum viable subset

Build `scripts/audit/` per the synthesis. Minimum viable scope:

- `schema.py` — `AuditSchema` + `GENERAL` + `TRANSITION` instances + validation
- `result.py` — `AuditResult` with provenance, `composite()`, `is_complete()`, `to_dict`/`from_dict`
- `run.py` — `Run` + run-level provenance + JSON I/O
- `compare.py` — `compare(baseline, treatment, tolerance) → ComparisonResult` with schema-match assertion
- `evaluator.py` — Evaluator protocol (or callable signature)
- `evaluators/general.py` — at minimum, runs `visual_critic` and produces a partial `AuditResult` with the other three dimensions left as None and `is_complete() == False`. Stubbing one or more dimensions is allowed *for the tracer*; the report names what's stubbed.
- `evaluators/transition.py` — at minimum, runs the existing transition-evaluation flow on `hierarchy-bundles` and wraps the result in an `AuditResult` with `TRANSITION` schema.

If the synthesis specifies more, you may build it; the tracer only requires the above to declare success at this step.

### Step 2 — Run end-to-end on two blocks

Render and audit one general-schema block and one transition-schema block:

```bash
python3 -c "
from scripts.audit import evaluators, run as run_module
from pathlib import Path
gen_result = evaluators.general.evaluate(Path('blocks/02-linked-scatterplot-matrix.html'), block_id='02-linked-scatterplot-matrix')
trans_result = evaluators.transition.evaluate(Path('blocks/hierarchy-bundles.html'), block_id='hierarchy-bundles')
run = run_module.Run(timestamp=..., results=[gen_result, trans_result], ...)
run.write(Path('notes/research/02-audit-architecture/tests/tracer/run.json'))
"
```

Adjust to match the actual API the synthesis defines. Record exact commands used.

Required output: `tests/tracer/run.json` containing both `AuditResult`s in the new shape, with provenance populated.

### Step 3 — Run `compare()` end-to-end

Either:
- (a) Construct a synthetic baseline `Run` with hand-edited dimension scores and feed it to `compare()` against the run from Step 2, or
- (b) Run Step 2 twice (once on the original block, once on a deliberately worse copy) and compare those two runs.

Required output: `tests/tracer/comparison.json` containing the `ComparisonResult` artifact, plus a paragraph in the report explaining what the verdict means.

The comparison **must** demonstrate:
- Schema-match assertion (try comparing a general `Run` to a transition `Run` and confirm it raises)
- Per-dimension diff
- Composite diff
- Flag-set change (engineer at least one to differ)
- Render-error count

## Constraints

- **Real runs, not mocks.** The tracer's value is that the package works against the actual audit pipeline and meta skills, not against fixtures.
- **Stub list explicit.** Every dimension or feature you stub is named in the report's "what was stubbed" section. If the synthesis disallows a stub, don't stub it.
- **No backward compat shims.** If a legacy `evals/runs/*.json` won't load via `from_dict`, that's expected — the new shape is intentional. Note it in the report; don't write a compatibility layer.
- **Cite, don't summarize.** When you say "the package does X," reference the file and function.

## Output

`notes/research/02-audit-architecture/tests/tracer/by-runner-<your-model-id>.md` with this frontmatter:

```
---
role: tracer-bullet-runner
model: <your model id>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: <YYYY-MM-DD>
synthesis-rev: <git sha of synthesis.md>
package-rev: <git sha of scripts/audit/ commits>
---
```

Body sections, in order:

1. **Implementation summary.** What was built, what was stubbed, file paths and line counts.
2. **Step 2 — End-to-end audits.** Commands run, paths to outputs (`tests/tracer/run.json`), unexpected failures or warnings.
3. **Step 3 — Comparison.** Commands run, paths to outputs (`tests/tracer/comparison.json`), schema-mismatch test, what the verdict means in plain English.
4. **What was stubbed.** Itemized list of every shortcut taken. For each, name what would change if it were not stubbed.
5. **What broke that the synthesis did not predict.** Honest list. If nothing broke, say so explicitly — it usually means the spec was already drafted with implementation in mind, which is fine but worth noting.
6. **Verdict on graduation criteria.** Did the package satisfy each gate listed in `library-implications.md`'s "Tracer-bullet phase"? Tick or untick each.

Maximum 1500 words.

If the synthesis specifies an API that turns out to be unimplementable as drafted, stop at Step 1 and write a one-section report explaining the obstacle. Do not paper over it.
