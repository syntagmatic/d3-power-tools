# D3 Power Tools

## What This Is

Skills for building advanced D3.js visualizations. Each one captures the judgment calls — where the tick falls, when to use color vs. position, why this projection — that separate a chart that communicates from one that merely renders. See [CONVICTIONS.md](../notes/CONVICTIONS.md) for the philosophy.

Skills work across contexts: Claude Code, Gemini, and eventually as interactive tutorials for humans.

## Workflow

**Always render and test before claiming something works.**
Visual bugs are invisible in code. After writing a visualization, run the test script to verify it loads, renders, and has no JS errors. Then screenshot it and read the image.

**Keep outputs self-contained.**
Each skill should produce a single HTML file with inline JS/CSS. External data files are fine. No build tools required — just open in a browser.

**Use modern D3 (v7+) and modern browser APIs.**
OffscreenCanvas, Web Workers, pointer events, ResizeObserver, CSS custom properties. No IE11 considerations.

**Canvas for data, SVG for interaction.**
When rendering more than ~500 elements, use Canvas for the data layer and SVG for axes, labels, and interaction targets. This is a proven pattern from the d3.parcoords library.

## Launcher Symlinks

Create these symlinks in the project root (gitignored):

```bash
ln -s ../dotfiles/scripts/worktree.sh branch
ln -s ../dotfiles/scripts/gemini-claude-container.sh box
ln -s ../dotfiles/scripts/claude-container-shell.sh shell
```

- `./branch <name>` — start a new Claude Code session in a git worktree
- `./box [name] [project]` — start a Claude Code session in an Apple Container (auto-builds image on first run)
- `./shell [name]` — open a shell in a running container

## Testing with Playwright

Test runner: `scripts/test-viz.py`. Quick reference:

```bash
# Test a single file
python3 scripts/test-viz.py output.html --out temp/check.png --wait-for "svg"

# Run the test suite
python3 scripts/test-viz.py --config tests/test.config.json

# Run tests for one skill
python3 scripts/test-viz.py --config tests/test.config.json --skill annotation

# Run tests for skills with uncommitted changes
python3 scripts/test-viz.py --config tests/test.config.json --changed
```

Examples live in `skills/*/examples/` and double as test fixtures. Add new test cases to `tests/test.config.json` (paths are relative to project root). After building a visualization:

1. Run the test script to catch JS errors and rendering failures
2. Read the screenshot to verify visual correctness
3. Test interactions if interactive: `--interactions hover,brush,click`
4. Read the post-interaction screenshot

## Blocks

Example visualizations live in `blocks/`. Each version is a generation run against the manifest.

- `blocks/manifest.json` — prompts and skill lists (always current)
- `blocks/{version}-{model}/` — generated blocks, one dir per version+model combo
- `blocks/{version}-{model}/generation.json` — provenance: model, per-block status

**Directory naming:** `v{N}-{model-id}`, e.g. `v0-claude-opus-4-6`, `v1-gemini-3-flash-preview`.

**Generating blocks:**
```bash
python3 scripts/generate-blocks-claude.py v2-claude-opus-4-6          # Claude
python3 scripts/generate-blocks-gemini.py v2-gemini-3-flash-preview   # Gemini
```
Both read manifest, run 5 parallel workers, skip existing files. Safe to re-run for retries.

## Iterating Blocks

`scripts/iterate-block.py` compacts a block's code while preserving audit quality. It uses a git worktree so the main checkout stays untouched.

```bash
# Compact a block (6 experiments, sonnet auditor)
python3 scripts/iterate-block.py --target 04-bee-swarm-census --block-set v2-claude-opus-4-6 --max-experiments 6 --model sonnet

# Longer run for large blocks
python3 scripts/iterate-block.py --target hierarchy-bundles --block-set standalone --max-experiments 50 --model sonnet
```

The loop: propose compaction via `claude -p` → audit → keep if LOC drops and composite holds → repeat. On completion, squash-merges the iterate branch to main.

- **Index page:** `evals/iterations/index.html` — master list with sparkline charts, expandable diffs, score tooltips with auditor feedback, proposer explanations, stress test flags, durations
- **Experiment data:** `evals/iterations/{NNN}-block-{id}.json` — per-experiment scores, diffs, proposer explanation, flags
- **History:** `evals/iterations/history.tsv` — append-only log
- **Shared lib:** `scripts/iterate_lib.py` — TSV logging, keep/discard decisions, worktree helpers, index generation

`scripts/iterate-prompt.py` is the prompt track equivalent (optimizes generation time instead of LOC).

## Multi-Session Coordination

When working alongside other Claude sessions, use `scripts/coord.sh` to coordinate. State lives in `.git/coordination/` (shared across worktrees, containers, and host).

**On startup, always run `scripts/coord.sh ensure` before doing any work.** This auto-registers the session (name and env derived from context) or heartbeats if already registered. No arguments needed.

```bash
# Auto-register (run this first — idempotent, cheap)
scripts/coord.sh ensure

# Declare what you're working on
scripts/coord.sh status "Rewriting projection section"
scripts/coord.sh files skills/cartography/SKILL.md

# Check for other sessions and conflicts
scripts/coord.sh list                     # see all active sessions
scripts/coord.sh conflicts                # check for file overlaps

# Task board
scripts/coord.sh task-list                # see available tasks
scripts/coord.sh task-claim <id>          # claim a task
scripts/coord.sh task-done <id>           # mark complete
scripts/coord.sh task-add <title> [desc]  # add a new task

# When done
scripts/coord.sh done                     # mark session complete
scripts/coord.sh deregister               # remove session
```

Container sessions: `$COORD_SESSION_NAME` and `$COORD_SESSION_ENV` are set automatically.

## Code Style

- ES modules or inline `<script type="module">`
- No frameworks — vanilla JS + D3
- No unnecessary abstractions
- Math-heavy code gets a brief comment explaining the geometry, not the implementation
- Prefer `const` and arrow functions
- Use D3 conventions: selections, joins, scales, axes

## Skills

Each `SKILL.md` encodes domain knowledge, architecture patterns, interaction recipes, and common pitfalls. Grouped by what the viewer needs.

### Seeing patterns
- `skills/parallel-coordinates/` — high-performance multivariate data exploration
- `skills/brushing/` — intersection brushing, lasso, fisheye, cross-chart linking
- `skills/linked-views/` — coordinating multiple views: d3.dispatch, shared state, crossfilter bitmap indexing, coordinated brushing/zoom, overview+detail
- `skills/distributions/` — box plots, violin plots, ridgeline/joy plots, bee swarm, strip/jitter, density, QQ plots, KDE

### Seeing structure
- `skills/hierarchy-layouts/` — treemap, pack, tree, cluster, partition, stratify, tiling strategies, labels, color encoding
- `skills/hierarchy-interaction/` — expand/collapse, zoomable treemap/sunburst/pack, focus+context navigation
- `skills/edge-bundling/` — LCA path routing, d3.curveBundle tension, radial dendrograms, SVG and Canvas rendering
- `skills/force/` — simulation lifecycle, all built-in forces, custom forces, drag, constrained layouts, clustering, 10K+ nodes
- `skills/network/` — node-link diagrams, adjacency matrix, arc diagrams, chord diagrams, Sankey flow

### Seeing place
- `skills/cartography/` — projections, TopoJSON topology operations, choropleth, bubble maps, hex binning, cartograms, flow maps, geographic labels, zoom-to-feature, globe versor rotation, Canvas multi-layer architecture, tile layers, large geometry/LOD, projection transitions

### Seeing change
- `skills/time-series/` — scaleTime vs scaleUtc, time-aware axes, gap handling, horizon charts, swimlanes, Gantt, cycle plots, real-time streaming, brushed time selection, LTTB downsampling
- `skills/motion/` — enter/update/exit, canvas animation, staggering, scrollytelling
- `skills/shape-morphing/` — circle↔rect via cornerRadius, bar↔pie via arc params, arbitrary path morphing via point resampling, projection transitions

### Making it legible
- `skills/scales/` — scale selection, axis customization, tick formats, responsive ticks, label collision, broken axes, dual-y, time gaps
- `skills/color/` — perceptual color spaces, Tol colorblind-safe palettes, compositing, alpha/overdraw, CVD simulation, dark mode, wide gamut, WCAG contrast, color legends
- `skills/visual-texture/` — SVG/Canvas pattern fills (hatching, stipple, diamonds, zigzag), filter textures, pattern+color dual encoding for accessibility
- `skills/annotation/` — callout annotations, leader lines, force-based label collision, responsive labels, tooltips, threshold/reference lines
- `skills/data-table/` — accessible data tables as chart alternatives: sortable, filterable, chart↔table toggle, linked highlighting
- `skills/canvas-accessibility/` — keyboard navigation, screen reader support, ARIA, focus rings, data table fallback

### Making it work
- `skills/canvas/` — high-performance Canvas 2D: quadtree hit detection, typed arrays, batched rendering, zoom, LOD
- `skills/webgl/` — GPU-accelerated rendering for 100K–10M+ elements: shaders, instanced rendering, texture atlases, zoom/picking
- `skills/navigation/` — d3-zoom, geometric vs semantic zoom, rescaleX/rescaleY, zoom constraints, minimap, pinch-to-zoom, level-of-detail
- `skills/responsive/` — ResizeObserver, container sizing, viewBox vs redraw, aspect ratio, breakpoints, touch, Canvas DPI, iframe embedding

### Before you render
- `skills/data-gathering/` — data loading, type coercion, cleaning, reshaping (group/rollup/pivot), aggregation, binning, joining, normalization
- `skills/sparkcharts/` — word-sized inline charts: sparklines, spark bars, win/loss, bullet charts, dot strips, embedding in tables and text
- `skills/small-multiples/` — trellis/faceted layouts, grid layout math, shared vs independent scales, synchronized cross-panel interaction

### Meta Skills

Skills for testing, evaluating, and improving other skills.

#### Code guides
- `meta/d3-idioms/` — D3 code style: method chaining indentation, margin convention, .join() data joins, selection.call() composition, reusable chart closure pattern, naming conventions, anti-patterns
- `meta/jig-template/` — multi-skill assembly: layer stack (Canvas+SVG+HTML), SVG vs Canvas decision, state architecture, dirty-flag rendering, composition archetypes, resize contract

#### Inspection tools
- `meta/visual-critic/` — design quality: color harmony, typographic hierarchy, whitespace, data-ink ratio, overall feel (screenshot-based)
- `meta/encoding-integrity/` — data honesty: lie factor, zero baselines, dual-axis risk, metamorphic relations (scaling, permutation, subset, shift), data join correctness
- `meta/stress-test/` — interaction robustness: update storms, stale closures, feedback loops, transition handoff conflicts
- `meta/cognitive-load/` — cognitive clarity: working memory limits, animation congruence, spaghetti threshold, color overload

#### Workshop tools
- `meta/calibrate-tool/` — measure skill effectiveness: with/without comparison for content skills, blind evaluation protocol for auditing skills
- `meta/sharpen-tool/` — audit and compress SKILL.md files: check for errors, triage sections, compress for token efficiency
