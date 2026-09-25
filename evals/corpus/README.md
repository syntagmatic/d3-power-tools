# Corpus (ported from d3pt)

Six fixed chart tasks with real data files, copied from the d3pt repo (github.com/syntagmatic/d3pt, `corpus/` and `prompts/single-shot/`, as of 0718ffa, 2026-05-03). `scripts/ablate.py --suite corpus` uses them to compare three arms on the same task: the plain request (base), d3pt's hand-compressed tier-100 prompt (prompt), and the plain request with one v3 skill staged (skill).

Per task:

- `task.md`: d3pt's task description. Its first paragraph is the plain request for the base and skill arms, and the critics judge every arm against it. `ablate-skill:` in the frontmatter is the one v3 skill the skill arm stages. This field was added here, since d3pt's `skills:` uses its own names.
- `tier-100.md`: d3pt's compact prompt, the prompt arm's text.
- `verify.json`: the structural fingerprint that `scripts/structural.py` checks (selector count bands plus interaction effects, with no LLM).
- `data/`: the dataset, served next to generated pages at the path the prompts name.

d3pt's `hierarchy` task (skill mode: one prompt applied to three held-out datasets) is not ported, because the ablation compares single outputs.

## Changes from d3pt

- `hierarchy-bundles/verify.json`: links max 260 -> 400. A working chart with a visible layer, an invisible hit-area layer, and two-column tree edges had 304.
- The generation text that every arm gets now asks for descriptive class names and class-toggled interaction state. `verify.json` finds marks by class, and before this only the compact prompts asked for classes, so the gate was grading naming.

Change a count band only for a reason visible in the chart, never because of which arm the chart came from.
