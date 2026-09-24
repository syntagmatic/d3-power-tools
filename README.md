# D3 Power Tools

**[Demo Gallery](https://syntagmatic.github.io/d3-power-tools/)**

Skills for building D3.js visualizations. Current models already know the D3 API. What they get wrong is judgment: a log scale on data with zeros, ten default category colors, a brush handler that redraws everything on every mousemove. Each skill is a short set of decisions, traps and exact reference values (palette hex codes, perception thresholds), with longer detail in reference files and tested examples. See [CONVICTIONS.md](notes/CONVICTIONS.md) for the philosophy.

The plugin also ships three critics that review a finished chart without seeing how it was made.

## Install

### Claude Code plugin

```
/plugin marketplace add syntagmatic/d3-power-tools
/plugin install d3-power-tools@d3-power-tools
```

The critics and the render-check hook need Playwright. In the plugin directory:

```bash
npm install && npx playwright install chromium
```

Without it, the skills still work, the hook stays silent, and `review` reports which critics couldn't run.

### Plain skill folders (Claude Code, Gemini CLI, Antigravity, others)

The skills are plain markdown folders with standard `name`/`description` frontmatter:

```bash
ln -s /path/to/d3-power-tools/skills .claude/skills     # Claude Code
ln -s /path/to/d3-power-tools/skills .gemini/skills     # Gemini CLI
ln -s /path/to/d3-power-tools/skills .agent/skills      # Antigravity
```

Or link individual skills. Any tool that reads context files can be pointed at `skills/<name>/SKILL.md`.

## Skills

Start with **[design](skills/design/SKILL.md)**. It's about finding the data's natural form before building, and it routes to the others.

| Skill | What it decides |
|---|---|
| [design](skills/design/SKILL.md) | What the data wants to be; loading, cleaning and reshaping it |
| [legibility](skills/legibility/SKILL.md) | Which scale, which colors, when to add texture, what to annotate |
| [patterns](skills/patterns/SKILL.md) | Distributions, parallel coordinates, small multiples, sparklines |
| [hierarchy](skills/hierarchy/SKILL.md) | Tree, treemap, pack, partition; navigating big trees; edge bundling |
| [networks](skills/networks/SKILL.md) | Node-link vs matrix vs arc vs chord vs sankey; force simulation |
| [maps](skills/maps/SKILL.md) | Projection, map form, TopoJSON, globes, rendering many features |
| [time](skills/time/SKILL.md) | Temporal forms, gaps, downsampling, streaming, focus+context |
| [interaction](skills/interaction/SKILL.md) | Brushing, linked views, coordination, zoom, and staying robust under fast input |
| [motion](skills/motion/SKILL.md) | When to animate, staging, interruption, scrollytelling, shape morphing |
| [rendering](skills/rendering/SKILL.md) | SVG vs Canvas vs WebGL, responsive sizing, code structure |
| [accessibility](skills/accessibility/SKILL.md) | Keyboard paths, screen readers, ARIA that works, chart ↔ table |

Each skill folder:

```
skills/legibility/
├── SKILL.md        # decisions, traps, reference values (≤150 lines)
├── references/     # detail, loaded when needed (one file per topic)
├── examples/       # working HTML pages, covered by the test suite
└── scripts/        # helpers the skill points to
```

## Critics

The judge and the maker shouldn't share a room. Each critic is a subagent with its own context and a different slice of the artifact:

- **viz-critic** sees the screenshot and the original request, never the code, and scores design against calibrated anchors.
- **encoding-auditor** reads the source and checks honesty (baselines, area scaling, dual axes, binning) and whether scales and joins survive changes to the data.
- **interaction-tester** gets only the URL and drives the page headlessly with `scripts/probe.mjs`: hover sweeps, brushing, pointer storms, rapid clicks, resizing to phone width, keyboard.

The **[review](skills/review/SKILL.md)** skill runs all three in parallel and merges their findings into a fix-first list.

`probe.mjs` also works on its own:

```bash
node scripts/probe.mjs chart.html --out temp/probe    # JSON findings + a screenshot per stage
```

## Vendored assets

Examples and blocks load D3, topojson and fonts from `vendor/` by relative path, so they render offline and inside network-restricted sandboxes.

```bash
./scripts/vendor.sh    # populates vendor/ (gitignored)
python3 -m http.server 8000
```

ES module pages need an HTTP origin. Serve the directory rather than opening the file directly. Files under `blocks/archive/` and `evals/` are a record of generated output and still point at CDNs.

## Testing

```bash
python3 scripts/test-viz.py --config tests/test.config.json            # example suite
python3 scripts/test-viz.py skills/hierarchy/examples/edge-bundling.html --out /tmp/check.png
node scripts/check-snippets.mjs                                         # every js block in skills/ must parse
```

## The lab

`blocks/`, `evals/`, `meta/` and most of `scripts/` are the workshop where the skills get tested: generated example blocks, audit runs, with/without-skill ablations, and code-compaction experiments. See [AGENTS.md](AGENTS.md).
