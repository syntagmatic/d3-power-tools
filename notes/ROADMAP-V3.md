# Roadmap v3: fewer skills, separate critics, plugin packaging

Written 2026-09-23, after a 10-agent audit of the whole repo.

## Status (2026-09-23, branch `v3-restructure`)

I skipped the phase 1 ablation for now and did phases 2-4 by judgment:

- 29 skills merged into the 11 below, plus `review`. The SKILL.md files run 85-128 lines; the references are 87-541 lines per skill. All 127 js blocks parse (`scripts/check-snippets.mjs`), and all 156 example tests pass. About 40 factual errors were fixed during the merge, including the `curveBundle.beta(1 - tension)` inversion, which lived in the edge-bundling *examples*, not the SKILL.md text.
- `agents/` has viz-critic, encoding-auditor and interaction-tester. `scripts/probe.mjs` does the scripted checks.
- Plugin: `.claude-plugin/plugin.json` + `marketplace.json` (source `./`), `hooks/hooks.json` (render check after HTML writes), `package.json` (Playwright).
- AGENTS.md is at the root; `.claude/CLAUDE.md` imports it. The manifest has v3 skill names, with `skills_v2` kept; `scripts/staging.py` copies whole skill dirs.

Still open: ablation (phase 1, now run on 11 skills via `scripts/ablate.py`), the lab split (the plugin source is currently the whole repo, lab included), `run-audit-pipeline.py` still uses the v2 `meta/` rubrics rather than the new agents, and phase 5.

## Why I'm restructuring

This project started in the Opus 4.5 era. The skills were written for a model
that needed D3 API help, so most of the 8,200 lines of SKILL.md are code
snippets and API walkthroughs. Current models already know the API. My own
first conviction says to strip API patterns and keep process, and the repo
doesn't follow it yet.

The audit made the cost concrete:

- Around 25 real errors in SKILL.md code: syntax errors (duplicate `const`),
  snippets that throw, upside-down projections, an infinite brush-zoom loop.
- `curveBundle.beta` was described backwards in the edge-bundling skill, and
  that error had already propagated into blocks 13 and 70. A wrong snippet is
  worse than no snippet because the model trusts it over its own prior.
- Examples are covered by the test suite (155 files). Snippets inside SKILL.md
  are covered by nothing.
- 29 content skills with overlapping descriptions compete for triggering
  (brushing / linked-views / coordination / choreography / motion /
  shape-morphing all describe similar territory).
- The installable product (skills) lives in the same repo as ~40MB of lab
  material (blocks, evals, iterate runs).

What I want: a small set of skills that carry judgment the current model
actually lacks, critics that are structurally separated from the maker, and a
plugin someone can install without pulling the lab.

## Target shape

### Skills: 34 -> 11

| New skill | Absorbs |
|---|---|
| design | exploratory-design, data-gathering |
| patterns | distributions, parallel-coordinates, small-multiples, sparkcharts |
| hierarchy | hierarchy-layouts, hierarchy-interaction, edge-bundling |
| networks | network, force |
| maps | cartography |
| time | time-series |
| legibility | scales, color, visual-texture, annotation |
| interaction | brushing, linked-views, coordination, navigation |
| motion | motion, choreography, shape-morphing |
| rendering | canvas, webgl, responsive, jig-template, d3-idioms |
| accessibility | canvas-accessibility, data-table |

`design` is the entry point and routes to the others.

Each skill:

```
skills/<name>/
  SKILL.md       <=150 lines: decision frameworks, pitfalls the ablation shows
                 models still get wrong, index of references
  references/    one file per absorbed skill, loaded on demand
  examples/      tested HTML; the only home for long code
```

Rules:

- Long code lives in `examples/`, which the suite tests.
- Any code left in SKILL.md or `references/` passes a CI check that extracts
  fenced blocks and parses them.
- Old skill names survive as `references/` filenames, and their trigger words
  go into the merged description.

### Critics: 8 meta skills -> 3 subagents

"Judge and maker must not share a room" becomes structure. Each critic runs
in its own context, never sees the maker's transcript, and gets a different
slice of the artifact.

| Agent | Absorbs | Sees | Does |
|---|---|---|---|
| viz-critic | visual-critic, cognitive-load | screenshot + original prompt, no code | holistic design score against my calibration anchors, top 3 issues |
| encoding-auditor | encoding-integrity | source + data | zero baselines, lie factor, metamorphic checks (rescale, permute, subset), mostly scripted |
| interaction-tester | stress-test, keyboard path from canvas-accessibility | URL only | drives the page with `scripts/probe.mjs`: hover, brush, update storms, resize, keyboard |

- A `review` skill fans out all three in parallel and merges results into the
  `Run` schema in `scripts/audit/`, so product and lab share one format.
- Critics use a different model from the maker where possible.
- `scripts/probe.mjs` consolidates the six Playwright probes the audit agents
  wrote independently (see the 2026-09-23 audit scratchpad; rewrite if lost).
  This also covers the TODO item about replacing stress_test and
  encoding_integrity LLM audits with programmatic checks.
- d3-idioms and jig-template fold into `rendering`. calibrate-tool and
  sharpen-tool stay lab-only.

### Product vs lab

- Plugin: 11 skills, 3 critic agents, `review` skill, optional hook that runs
  render-check after an HTML write. Plain SKILL.md folders stay usable by
  Gemini and other tools.
- Lab: blocks, evals, iterate-block, calibrate, sharpen, research notes,
  audit comparison tooling. Either a top-level `lab/` split or a second repo;
  decide in phase 4.

## Phases

### Phase 1: ablation on the current model

Question: which skills still change output quality?

For each of the 29 content skills, pick 3-4 manifest prompts it's meant to
help. Generate with and without the skill on the current model, audit blind
with the existing pipeline (`scripts/run-audit-pipeline.py`, `scripts/audit/`
for comparison). Record per-skill delta and which sections the positive
cases leaned on.

Output: `notes/ablation-v3.md` with a keep / compress / cut verdict per skill
and, for keepers, the specific pitfalls worth retaining.

Gate: I review the verdicts before any merge.

### Phase 2: pilot merge (legibility)

Merge scales, color, visual-texture, annotation into `skills/legibility/`
using the ablation verdicts. Add the snippet parse check to CI. Compare the
merged skill against the four originals on the same prompts.

Gate: merged skill scores at least as well as the originals, with a
SKILL.md under 150 lines.

### Phase 3: remaining merges

The other 10 groups, in parallel (one session or agent per group). Update
`tests/test.config.json`, `index.html`, AGENTS.md skill list.

### Phase 4: critics, probe, packaging

Build `scripts/probe.mjs`, the three agents, the `review` skill, plugin
manifest. Decide the lab split. Move project instructions from
`.claude/CLAUDE.md` to root `AGENTS.md` with a CLAUDE.md pointer
(`.gitignore` already references an AGENTS.md that doesn't exist).

### Phase 5: change the eval target

`iterate-block` optimizes block LOC, but blocks are outputs, not the product.
Switch the standing metric to per-skill uplift (with vs without), run on every
skill change, per the "every skill is a bet" conviction.

## Open questions

- Is 11 the right count, or should networks fold into hierarchy?
- Does `design` as a router actually improve triggering, or just add a hop?
- Lab split: directory or separate repo?

## Next session prompt (phase 1)

```
I'm restructuring d3-power-tools per notes/ROADMAP-V3.md. Start phase 1: the
ablation. I want to know which of the 29 content skills in skills/ still
improve output on the current model, because the skills were written for
Opus 4.5 and are mostly API snippets the model may no longer need.

For each skill, pick 3-4 prompts from blocks/manifest.json that the skill is
meant to help. Generate each with and without the skill loaded, then audit
blind using the existing pipeline (scripts/run-audit-pipeline.py and the
scripts/audit/ package). Keep the maker and judge in separate contexts.

Write notes/ablation-v3.md: a table of per-skill score delta, a keep /
compress / cut verdict, and for keepers the specific sections or pitfalls
the winning outputs relied on. Don't merge or delete any skills yet; I'll
review the verdicts first. Estimate cost before generating and check with me
if it's large.
```
