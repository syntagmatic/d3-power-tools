# D3 Power Tools

## What this is

A Claude Code plugin (and plain skill folders usable by other agents) for building D3.js visualizations. The skills carry judgment: which scale, which form, which palette, what breaks under fast input. They leave out the API, which current models already know. See [notes/CONVICTIONS.md](notes/CONVICTIONS.md) for the philosophy and [notes/ROADMAP-V3.md](notes/ROADMAP-V3.md) for the restructure plan.

The repo has two halves:

- **Product:** everything under `plugin/`: `skills/`, `agents/`, `hooks/`, `.claude-plugin/plugin.json`, `package.json`, and the scripts they call (`plugin/scripts/probe.mjs`, `hook-render-check.mjs`, `check-snippets.mjs`). The root `.claude-plugin/marketplace.json` points at `./plugin`, so an install copies only this folder.
- **Lab:** everything else at the root: `blocks/`, `evals/`, `meta/` (calibrate, sharpen, and the v2 audit rubrics, which `run-audit-pipeline.py --critics v2` and iterate-block still use; the default v3 set runs the `plugin/agents/` critics), `notes/`, `tests/`, `vendor/`, and the generation/iteration/ablation scripts in `scripts/`.

Nothing in `plugin/` may depend on a lab path. The lab reads `plugin/` freely.

## Skills

`design` is the entry point and routes to the rest.

| Skill | Covers |
|---|---|
| `design` | exploratory design process, data loading/cleaning/reshaping, routing |
| `legibility` | scales and axes, color, texture/pattern fills, annotation and labels |
| `patterns` | distributions, parallel coordinates, small multiples, sparklines |
| `hierarchy` | tree layouts, treemap/pack/partition, hierarchy navigation, edge bundling |
| `networks` | node-link, matrix, arc, chord, sankey, force simulation |
| `maps` | projections, TopoJSON, choropleth and other map forms, globe, map rendering |
| `time` | temporal forms, gaps, downsampling, streaming, focus+context |
| `interaction` | brushing, linked views, coordination architecture, zoom/navigation, robustness |
| `motion` | transitions, choreography/scrollytelling, shape morphing |
| `rendering` | SVG vs Canvas vs WebGL, responsive sizing, code structure and idioms |
| `accessibility` | keyboard, screen readers, ARIA, data tables |
| `review` | runs the three critics in parallel and merges their findings |

Format rules for every skill are in [notes/SKILL-FORMAT.md](notes/SKILL-FORMAT.md): SKILL.md ≤150 lines of decisions, traps and exact reference data. Detail goes in `references/<v2-skill-name>.md`, and long code only in tested `examples/`. The v2 → v3 name map is `scripts/skill_aliases.json`.

## Critics

`plugin/agents/` holds three subagents. They never share context with the maker, or with each other.

- `viz-critic`: screenshot + request only, and a design score calibrated to Kai's anchors.
- `encoding-auditor`: source + data. Honesty checks and metamorphic robustness.
- `interaction-tester`: URL only. Drives `plugin/scripts/probe.mjs`.

## Workflow

**Render and test before claiming something works.** Visual bugs are invisible in code.

**Keep outputs self-contained.** Single HTML file, inline JS/CSS, no build step. External data files are fine.

**Modern D3 (v7+) and modern browser APIs.** OffscreenCanvas, Web Workers, pointer events, ResizeObserver, CSS custom properties.

**Canvas for data, SVG for interaction** past ~500 elements.

**Snippets must parse.** `node plugin/scripts/check-snippets.mjs` checks every ```js block in `plugin/skills/`. Fence intentional fragments as `js-fragment`.

## Setup

```bash
npm install && npx playwright install chromium   # probe.mjs, hook, check-snippets
./scripts/vendor.sh                               # vendor/ (gitignored) for blocks; refreshes the committed plugin/vendor/ subset the examples load
```

Host Python usually lacks Playwright. Run Python test scripts with `uv run --with playwright python3 scripts/...`.

Launcher symlinks (gitignored) in the project root:

```bash
ln -s ../dotfiles/scripts/worktree.sh branch
ln -s ../dotfiles/scripts/gemini-claude-container.sh box
ln -s ../dotfiles/scripts/claude-container-shell.sh shell
```

## Testing

```bash
node plugin/scripts/probe.mjs <file-or-url> [--checks load,nan,hover,brush,storm,resize,keys,click] [--out dir]
python3 scripts/test-viz.py <file> --out temp/check.png --wait-for "svg"
python3 scripts/test-viz.py --config tests/test.config.json [--skill legibility] [--changed]
```

Examples in `plugin/skills/*/examples/` double as test fixtures and are registered in `tests/test.config.json`. After building something: probe it, read the screenshot, and exercise the interactions you'd actually click.

## Blocks (lab)

- `blocks/manifest.json`: prompts and v3 skill lists (`skills_v2` keeps the originals)
- `blocks/{id}.html`: best version of each block
- `blocks/archive/{version}-{model}/`: all generation runs
- `evals/best-blocks.json`: which run each promoted block came from

```bash
python3 scripts/generate-blocks-claude.py <version> [--model M] [--no-skills]
python3 scripts/generate-blocks-gemini.py <version>
python3 scripts/ablate.py plan|gen|audit|pair|report|cost   # with/without-skill ablation, blind pairwise judging
python3 scripts/ablate.py --suite corpus plan|gen|struct|audit|pair|report   # base / d3pt prompt / skill on evals/corpus/
```

`scripts/iterate-block.py` compacts a block's code under audit (git worktree, squash-merges on completion). After every run, regenerate the index:

```bash
python3 -c "from scripts.iterate_lib import generate_progress_html; generate_progress_html()"
git add evals/iterations/index.html && git commit -m "Refresh iterations index"
```

## Multi-session coordination

Run `scripts/coord.sh ensure` on startup. State lives in `.git/coordination/`.

```bash
scripts/coord.sh status "what I'm doing"; scripts/coord.sh files <paths>
scripts/coord.sh list | conflicts | task-list | task-claim <id> | task-done <id> | done | deregister
```

## Code style

- ES modules or inline `<script type="module">`; vanilla JS + D3, no frameworks
- No unnecessary abstractions; `const` and arrow functions
- Math-heavy code gets a brief comment on the geometry, not the implementation
- D3 conventions: selections, `.join()`, scales, axes
