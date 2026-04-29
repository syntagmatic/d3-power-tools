# Blind Judge Prompt — Dossier 01 (coordinated-views merge)

You are auditing tracer-bullet blocks for this dossier. Your role is **blind-judge**: score each block on the standard audit dimensions without seeing the skill that produced it, the synthesis that proposed it, or prior audit baselines.

> This is the dossier-local adaptation of `notes/research/_templates/BLIND-JUDGE-PROMPT.md`. The template wins on conflicts.

## What you receive

- `notes/research/01-coordinated-views-merge/tests/judge-input/<anon-id>.html` — anonymized blocks if available. If `judge-input/` doesn't exist, judge `tests/blocks/<model>/<fixture>.html` directly, but DO NOT let the model-name-in-path influence scoring.
- `notes/research/01-coordinated-views-merge/tests/fixtures/iris/data.csv` — the data the block was given
- `notes/research/01-coordinated-views-merge/tests/fixtures/iris/task-spec.md` — what the generator was asked to build
- `meta/visual-critic/SKILL.md` — rubric for design quality
- `meta/encoding-integrity/SKILL.md` — rubric for data honesty
- `meta/stress-test/SKILL.md` — rubric for interaction robustness
- `meta/cognitive-load/SKILL.md` — rubric for cognitive clarity

## Inputs you must NOT read

- `notes/research/01-coordinated-views-merge/synthesis.md` — would bias you toward the proposed shape
- `notes/research/01-coordinated-views-merge/tests/skill-under-test/SKILL.md` — same
- `notes/research/01-coordinated-views-merge/critique/*` — same
- `notes/research/01-coordinated-views-merge/tests/blocks/<model>/log.md` — generator's self-report would contaminate
- `evals/best-blocks.json` and `evals/iterations/*` — prior audit results
- `/blocks/*.html` — existing reference blocks would re-anchor your scoring
- Other judges' files in `tests/audit/` — independence is the whole point

If you accidentally open any of these, log it in your frontmatter (`contaminated: true`).

## Adversarial pairing rule

You may not play this role if your model:
- wrote `synthesis.md`
- wrote any block in `tests/blocks/<your-model>/`
- played `critic` for this dossier (check `critique/` filenames)

If any check fails, abort and report.

## How to inspect a block

Render it. Don't just read source.

```bash
python3 scripts/test-viz.py <block.html> --out temp/judge/<anon-id>.png --wait-for "svg, canvas"
python3 scripts/test-viz.py <block.html> --out temp/judge/<anon-id>-after.png --interactions hover,brush,click
```

Read both screenshots. Read the source. Both are required.

## The five audit dimensions

Score each 0–10, with a one-sentence justification per score citing what you observed.

| Dimension | Rubric | What to look for |
|-----------|--------|------------------|
| **composition** | visual-critic | Layout, hierarchy, whitespace, overall feel |
| **encoding_density** | (CONVICTIONS "Complexity matches the data") | Does the encoding match the data's dimensionality? |
| **interaction_robustness** | stress-test | Survives update storms, stale closures, transition handoffs? |
| **performance** | (no dedicated rubric — judge by frame timing during interaction) | Smooth at iris-scale (150 rows trivially)? |
| **accessibility** | canvas-accessibility + general | Keyboard reachable? Color contrast? |

## Flag list (separate from scores)

- `render-error` — block failed to load or threw a JS error
- `interaction-error` — interaction (hover/brush/click) threw an error
- `static` — claims to be coordinated but isn't
- `lossy-encoding` — encoding hides structure visible in the data
- `hardcoded-data` — block embeds the fixture data inline instead of loading
- `multi-skill-leak` — uses patterns clearly from skills other than `coordinated-views`. Examples: explicit `d3.scaleQuantize` reasoning from `scales`; explicit Tableau10 selection from `color`. Borderline cases (using a scale, picking a color) are fine.

## Blind comparison

After scoring all blocks, produce a per-fixture ranking by anonymized ID. Best, worst, single most decisive difference. Independent of per-dimension scores — sometimes the best-scoring block isn't the best block.

## Anti-patterns

- Don't score by source verbosity — score by rendered output.
- Don't compare blocks to each other while scoring individual dimensions; compare each block to the rubric. Cross-block comparison happens in the blind ranking, separately.
- Don't suggest fixes. Score, don't revise.

## Output

Write to `notes/research/01-coordinated-views-merge/tests/audit/by-judge-<your-model-id>.md` with this frontmatter:

```
---
role: blind-judge
model: <your model id>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: 2026-04-29
blocks-judged: [<anon-id-1>, <anon-id-2>, ...]
contaminated: <true|false>
contamination-note: <if true, what you saw>
---
```

Body, in this order:

1. **Score table:**

   | anon-id | fixture | composition | encoding_density | interaction_robustness | performance | accessibility | composite |
   |---------|---------|-------------|------------------|------------------------|-------------|---------------|-----------|

   Composite = unweighted mean of the five dimensions, one decimal place.

2. **Score justifications**, one paragraph per (anon-id × fixture). Maximum 60 words each.

3. **Flag list**, by anon-id.

4. **Blind ranking**, by fixture: best → worst, plus the single most decisive difference.

5. **Calibration check**: are any of your scores >2 points away from where you'd expect a competent block to land? If so, note it.

Maximum 1500 words (score table doesn't count).

Do not edit any file other than your own audit file.
