# Test Prompt — Dossier 01 (coordinated-views merge)

You are producing a tracer-bullet block for this dossier. Your role is **alt-generator** — you are validating whether the proposed merged skill produces good output across models. Your block will be audited by a blind judge that did not see your generation.

> This is the dossier-local adaptation of `notes/research/_templates/TEST-PROMPT.md`. The template wins on conflicts.

## What's being tested

The synthesis in this dossier proposes merging `brushing` + `linked-views` + `coordination` into a single `coordinated-views` skill (or one of the alternative options — read `synthesis.md` to confirm which). The merged SKILL.md sits at `tests/skill-under-test/SKILL.md`.

Your job: produce blocks that exercise this merged skill and only this merged skill. If the SKILL.md alone produces consistent good output across models, the merge is well-defined.

## Inputs

- `notes/research/01-coordinated-views-merge/synthesis.md` — proposed shape
- `notes/research/01-coordinated-views-merge/tests/skill-under-test/SKILL.md` — the merged SKILL under test
- `notes/research/01-coordinated-views-merge/tests/fixtures/<fixture-name>/task-spec.md` — what to build
- `notes/research/01-coordinated-views-merge/tests/fixtures/<fixture-name>/data.csv` — the data
- `notes/CONVICTIONS.md` — project principles (read once, then forget)

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md` or wrote `tests/skill-under-test/SKILL.md`. Check those frontmatters. If your model is listed, abort and report.

You may not consult, view, or be given access to:
- Other generators' blocks for this dossier (`tests/blocks/<other-model>/`)
- Audit results from any prior round
- Existing reference blocks in `/blocks/*.html` — particularly `02-linked-scatterplot-matrix` which is the closest existing exemplar

If you find yourself reaching for `/blocks/`, stop. Read `tests/skill-under-test/SKILL.md` instead.

## Task

For each fixture in `tests/fixtures/`, produce one self-contained HTML block. Each block:

- Loads its fixture file from a relative path (`./data.csv`)
- Uses ONLY the merged `coordinated-views` skill — no patterns from `scales`, `color`, `parallel-coordinates`, etc.
- Inlines all CSS and JS
- Loads D3 v7 from a CDN
- Opens in a browser with no build step (verify with `python3 scripts/test-viz.py <block.html>`)
- Implements the visualization described in `task-spec.md`

Write each block to `tests/blocks/<your-model-id>/<fixture-name>.html`.

## Anti-cheat constraints

- **One skill only.** Use whatever scale/color choices come naturally — but don't import patterns from other skill files.
- **No prompt expansion.** Use the task spec as written. Don't add features. Don't make it "nicer" than asked.
- **One shot.** No iteration loops, no self-correction passes. The point is to see what each model produces first-pass.

## What this measures

If three independent generators produce blocks that audit to similar composite scores (within ±1.0), the skill is well-defined. If scores diverge, the skill is underspecified — and *which fixture* causes the divergence is the actionable signal.

If the SKILL.md is ambiguous on a point, **note it in your log** instead of papering over the ambiguity. Specific ambiguities you encountered are more valuable than a polished block.

## Output

Per fixture:
```
notes/research/01-coordinated-views-merge/tests/blocks/<your-model-id>/<fixture-name>.html
```

Plus a generator log:
```
notes/research/01-coordinated-views-merge/tests/blocks/<your-model-id>/log.md
```

With this frontmatter:

```
---
role: alt-generator
model: <your model id>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: 2026-04-29
skill-under-test: coordinated-views
skill-rev: <git sha of skill-under-test/SKILL.md, or N/A>
fixtures: [iris]
---
```

Body of `log.md`: per-fixture notes — what was easy, what was ambiguous in the SKILL.md, what you had to decide unilaterally. Maximum 300 words. Specific ambiguities are gold.

Do not produce audit scores yourself. The blind-judge role does that separately.
