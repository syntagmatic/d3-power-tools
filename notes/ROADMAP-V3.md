# Roadmap v3: fewer skills, separate critics, plugin packaging

Written 2026-09-23, after a 10-agent audit of the whole repo.

## Status (2026-09-23, branch `v3-restructure`)

I skipped the phase 1 ablation for now and did phases 2-4 by judgment:

- 29 skills merged into the 11 below, plus `review`. The SKILL.md files run 85-128 lines; the references are 87-541 lines per skill. All 127 js blocks parse (`scripts/check-snippets.mjs`), and all 156 example tests pass. About 40 factual errors were fixed during the merge, including the `curveBundle.beta(1 - tension)` inversion, which lived in the edge-bundling *examples*, not the SKILL.md text.
- `agents/` has viz-critic, encoding-auditor and interaction-tester. `scripts/probe.mjs` does the scripted checks.
- Plugin: `.claude-plugin/plugin.json` + `marketplace.json` (source `./`), `hooks/hooks.json` (render check after HTML writes), `package.json` (Playwright).
- AGENTS.md is at the root; `.claude/CLAUDE.md` imports it. The manifest has v3 skill names, with `skills_v2` kept; `scripts/staging.py` copies whole skill dirs.

Still open: ablation (phase 1, now run on 11 skills via `scripts/ablate.py`) and phase 5.

2026-09-24, lab split: the product moved to `plugin/` (skills, agents, hooks, `plugin.json`, `package.json`, and probe/hook-render-check/check-snippets under `plugin/scripts/`). The root `marketplace.json` source is `./plugin`, so an install no longer copies blocks/ and evals/ (~40MB). The lab stays at the root in the same repo, because the change-a-skill/re-measure loop needs both side by side. Rule: nothing in `plugin/` depends on a lab path. `plugin.json`'s `hooks` value needed a `./` prefix to pass `claude plugin validate`. That problem predated the move.

Examples now load from a committed `plugin/vendor/` (d3 UMD + ESM, topojson-client, two atlas files, 1.5MB), so they render from an install. I checked this by probing a copy of `plugin/` made outside the repo. `probe.mjs` picks its serve root at the nearest `.git`, `.claude-plugin` or `package.json`, so `../` paths resolve in an installed plugin too. `vendor.sh` refreshes the subset.

2026-09-24: `run-audit-pipeline.py` now runs the three `agents/` critics by default (`--critics v3`). Each runs headless as itself (`claude --agents ... --agent <name> --setting-sources project` from an empty dir, so no user CLAUDE.md reaches it) and gets only its slice: viz-critic the manifest prompt + screenshot, the other two the HTML path. The composite is 0.4 design / 0.3 encoding / 0.3 interaction, for ablation only. Anchor drift compares against the v2 anchors approximately. iterate-block and iterate_lib pass `--critics v2` until phase 5 replaces them. About $0.07-0.11 per block on Sonnet. `probe.mjs` now serves local files over http from the git root, because under file:// the ESM `../vendor` imports failed and the page rendered blank.

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

2026-09-24, corpus suite: d3pt's six single-shot tasks (real data, `verify.json` fingerprints, tier-100 prompts) are in `evals/corpus/`, and `ablate.py --suite corpus` compares three arms: plain request, d3pt's compact prompt, and plain request plus skill. `scripts/structural.py` is d3pt's structural gate ported to Python. It agreed with d3pt on 35/39 recorded cells, and the 4 disagreements were stale d3pt records. A smoke run on hierarchy-bundles (one output per arm, Opus 5.5) found two gate biases, now fixed: class names are asked for in every arm, and the links band was widened. After the fixes, base and skill passed, and the prompt arm threw `multiple roots` and rendered nothing. The full run (36 generations, about $20) has not been done. The critics and pairwise judging have not been exercised on this suite yet.

2026-09-25, first corpus run (Sonnet 5 generating, Opus 5.5 critics and judge; 6 tasks x 3 arms x 2 samples; numbers in `notes/ablation-corpus-data.md`): no arm clearly wins. Pairwise over all tasks: skill beat base 7-5, prompt lost to base 5-7, and skill vs prompt tied 6-6. Almost every margin was "slight". Mean composite was base 5.96, prompt 6.16, skill 5.54, but one broken skill output on choropleth (1.3) pulls the skill mean down. At n=2 per cell none of these differences is signal. What the run did show:

- The choropleth task's data is defective. d3pt's `us-states.json` is overlapping rectangles, and every arm scored 1-4 from the viz critic. Replace it with real TopoJSON (the committed `plugin/vendor` atlas) before the next run.
- The plain request first used only the task's first paragraph, which dropped requirements that verify.json checks, so 16 of the 19 structural failures were base or skill. The request is now every requirement paragraph. After that and five arm-blind checker fixes (axis nesting, arc names, hover triggers, morph sampling), structural passes 33/36. The 3 failures are real: a filter bug that set `pointer-events: none` on every dot, and two sunburst outputs that folded the headcount ring into the leaf arcs.
- Maps skill: the winding advice is right, but one output reversed at the wrong nesting depth (treating a Polygon as a MultiPolygon) and swapped lat/lon. A line on Polygon vs MultiPolygon depth would prevent it.
- Next: more samples per cell (n=2 can't separate arms), a fixed choropleth, and possibly a second judge family.

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

## Next session prompt

v3-restructure merged to main on 2026-09-25. The phase 1 prompt that was here is obsolete: the skills are already merged to 11, and the ablation now runs on the corpus suite.

```
I'm continuing d3-power-tools per notes/ROADMAP-V3.md. The first corpus
ablation (notes/ablation-corpus-data.md) couldn't separate the three arms at
n=2 per cell, and the choropleth task's data was broken. I want a run that
can actually tell me whether the skills help.

First, replace the choropleth task's us-states.json with real TopoJSON from
the committed plugin/vendor atlas, and update its verify.json to match.
Probe one output to confirm the task renders a real map. Then add the
Polygon vs MultiPolygon nesting-depth line to the maps skill.

Then estimate the cost of scripts/ablate.py --suite corpus at n=5 per cell
and check with me before generating. After the run, add the numbers to
notes/ablation-corpus-data.md and a dated entry to the roadmap: per-task
winner, whether any arm's margin is larger than sample noise, and which skill
sections the winning outputs used.
```
