# Skill format (v3)

How I want each merged skill written. The pilot is `skills/legibility/`; copy its
shape.

## What a skill is for

The reader is a current frontier model that already knows the D3 API cold. It
doesn't need `scaleBand` explained or a tooltip snippet. What it gets wrong, or
does blandly, is judgment: which encoding, which default, when to stop. It also
can't recall exact reference data (published palette hex values, thresholds
from perception research), and it walks into specific traps that look fine in
code and break on screen.

So a skill carries three things, in this order of value:

1. **Decisions.** "If the data looks like X, do Y, because Z." Short tables
   with the trigger condition in the first column.
2. **Traps.** Things that silently produce wrong output: NaN positions, lying
   baselines, feedback loops, blurry canvases. Each one is a single line with
   the symptom and the fix.
3. **Reference data.** Exact values the model can't reliably produce: hex
   arrays, numeric thresholds, magic constants with their source.

It doesn't carry API tutorials, snippets that restate the docs, history,
"as of March 2026" asides, or future-tech speculation.

v2 evidence: skills helped most on visual polish (palettes, layout defaults),
and interaction robustness (throttling, stale closures, transition conflicts)
was the weakest dimension across every model. Long skills hurt slower models.
Weight the pages accordingly.

## Layout

```
skills/<name>/
  SKILL.md        <=150 lines, including frontmatter
  references/     one .md per absorbed v2 skill, named after it; loaded on demand
  examples/       tested HTML, moved from the absorbed skills
  scripts/        optional, JS helpers carried over
```

### SKILL.md

- Frontmatter `name` matches the directory. `description` lists what it covers
  and the trigger words of every absorbed skill (so "sankey", "horizon chart",
  "lasso" still route here). Aim for under 600 characters.
- Opening: two or three sentences on the judgment this skill is about.
- Body: decision tables and a trap list. Code only when it's under ~8 lines
  and the idea can't be said in prose (a formula, a one-line guard).
- A closing `## References` index: one line per `references/*.md` saying when
  to open it, plus the examples.

### references/<old-name>.md

- The compressed survivor of the old SKILL.md: keep the judgment, the traps,
  the exact data, and code only where it encodes non-obvious logic (a custom
  force, a piecewise scale, an alpha solver). Cut API walkthroughs.
- Target roughly a third of the original length or less. No hard cap.
- Every fenced `js` block must parse (`node scripts/check-snippets.mjs`). If a
  block is intentionally partial, fence it as `js-fragment`, and use it
  sparingly.
- Fix wrong facts as you go. If you're not sure a claim is true, cut it.

### examples/

Move the absorbed skills' example files unchanged (`mv`, not `git mv`; other
agents share the index). Don't edit them unless they reference a moved path.

## Things not to do

- Don't touch files outside your own `skills/<name>/` directory. I update
  `tests/test.config.json`, `index.html`, the manifest and AGENTS.md centrally.
- Don't run git commands that write (add, mv, commit).
- Don't invent new content. Condense what's there, and correct errors.
