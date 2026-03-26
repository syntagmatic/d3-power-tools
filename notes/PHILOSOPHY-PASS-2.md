# Philosophy Pass 2: Research-Driven Expansion

## Context

The first philosophy pass (notes/PHILOSOPHY-PASS.md) cut API docs and added judgment — "why" rationales, "when not to use" sections, failure modes. It succeeded: every skill now has editorial guidance and the collection is denser.

But the skills still reflect a narrow slice of the practice. The color skill offers Tol palettes as if they're the only colorblind-safe option. The force skill covers d3-force but not the broader landscape of graph layout algorithms. The cartography skill mentions projections but doesn't cover the projection selection problem deeply. Each skill represents *one practitioner's* judgment — this pass brings in the broader field.

## What's Different This Time

| First pass | This pass |
|---|---|
| Cut API docs, add judgment | Research the field, expand the solution space |
| "When not to use X" | "What else could you use instead of X" |
| Internal critique | External research |
| Tighten | Broaden then tighten |

## The Loop

For each skill:

### Step 1: Deep web research

Search for state-of-the-art in the skill's domain. Not D3 API docs — practitioner wisdom, perceptual research, notable examples, alternative approaches the skill doesn't cover.

Research targets per skill (examples, not exhaustive):

**color** — ColorBrewer, Cynthia Brewer's work. Crameri scientific palettes (batlow, roma). Matplotlib/seaborn palettes that have crossed over. WCAG 3.0 APCA contrast. oklch() in CSS. D3 chromatic schemes beyond what's listed. When Tol is right and when it's not the only answer.

**cartography** — Mapbox/MapLibre projection work. PMTiles and vector tiles. Observable Plot's geo mark. Natural Earth projections. Equal-area vs conformal decision in modern practice. Dark-mode cartography.

**force** — UMAP/t-SNE as layout alternatives. Stress majorization (d3-force-reuse). WebWorker force simulation. Cola.js constraints. Gephi's ForceAtlas2. When to pre-compute layout server-side.

**parallel-coordinates** — Observable Plot parallel coordinates. Reorderable axes research (Pargnostics). Dimension reduction as alternative (PCA biplot). Angular parallel coordinates.

**brushing** — Observable Plot's faceted brush. Cross-filtering at scale (Falcon, Crossfilter2). Lasso vs rectangle vs arbitrary region. Brush composition (union, intersection).

**canvas** — OffscreenCanvas + Worker patterns in production. WebGPU as Canvas successor. Texture atlases for markers. regl vs raw WebGL decision.

**distributions** — Raincloud plots (Allen et al. 2019). Letter-value plots (Hofmann et al.). Density ridgeline innovations. Observable Plot distribution marks.

**time-series** — Observable Plot's time-series patterns. Grafana-style annotation bands. Anomaly detection visualization. Multi-scale time (year→minute drill-down).

**network** — Graphology.js ecosystem. Sigma.js for large graphs. Hive plots. BioFabric. Matrix+node-link hybrid. Community detection visualization.

**annotation** — Arquero-driven data annotations. Observable's Plot annotation mark. Scrollytelling annotation patterns (scrollama). Annotation as data (structured vs ad-hoc).

**hierarchy-layouts** — Icicle plots (underrepresented). Flame charts as hierarchy viz. Marimekko/mosaic as treemap variant. Observable Plot's tree mark.

**linked-views** — Vega-Lite selections. Observable's synchronized views. Mosaic (UW) for cross-filtered dashboards. When to use a library vs hand-rolling.

**scales** — D3 diverging scales. Threshold scales for choropleth. Band scale outer padding. Scale breaks (gap encoding). Perceptual uniformity in practice.

**motion** — View transitions API. FLIP technique (already covered, verify currency). Scrollytelling frameworks (scrollama, Intersection Observer patterns). Morph transition choreography.

**responsive** — Container queries (CSS). Responsive Observable notebooks. Mobile-first chart design patterns. Print stylesheets for charts.

**small-multiples** — Trellis plots in Observable Plot. Automated faceting. When to use sparklines-in-table vs small multiples.

**sparkcharts** — Observable Plot inline marks. Edward Tufte's original work revisited. Sparklines in dashboards (Grafana, Datadog patterns).

**visual-texture** — CSS Houdini paint worklets. SVG 2 paint servers. Pattern perception research (Ware, Chapter 5). When texture outperforms color.

**navigation** — Semantic zoom in Observable. Minimap patterns. Scroll-driven zoom (intersection observer + zoom). Level-of-detail state machines.

**data-gathering** — Arrow/Parquet in the browser. DuckDB-WASM for client-side analytics. Observable's FileAttachment patterns. Streaming CSV parsing.

**webgl** — deck.gl layer system. WebGPU status and timeline. Three.js integration with D3 scales. Instanced rendering patterns from GPU.js.

**canvas-accessibility** — ARIA 1.3 developments. High-contrast mode support. Reduced motion preferences. Screen reader testing methodology.

**data-table** — AG Grid patterns worth stealing. Virtualized rendering (TanStack). Sticky headers and columns. Responsive table patterns.

**edge-bundling** — Edge-path bundling (Wallinger et al.). Divided edge bundling. Confluent drawing. When bundling hides structure vs reveals it.

**shape-morphing** — Flubber.js current state. SMIL deprecation and CSS animation alternatives. Three.js morph targets. Morphing as storytelling device.

### Step 2: Audit the examples

For each skill, ask: does the example demonstrate the *expanded* skill, or is it stuck in the pre-research version? Flag examples that need updating.

### Step 3: Expand the skill

Add new sections or broaden existing ones based on research findings. The expansion should:
- Offer alternatives, not just one way ("Tol palettes are excellent for colorblind safety; here are three other options and when each fits better")
- Reference real-world usage (Observable notebooks, production dashboards, notable visualizations)
- Add new recipes where the research reveals them
- Keep the judgment-first philosophy — don't just list options, guide the choice

### Step 4: Verify accuracy

Every new code snippet must be tested. Every new claim must be verifiable. Run the skill's tests.

### Step 5: Update the example if needed

If the skill expanded significantly, the example should demonstrate the new material. A color skill that now covers 4 palette systems should show them, not just Tol.

## Skill Order

Research-expand the skills where the gap between "what we cover" and "what exists" is largest:

### Priority 1 — Biggest expansion potential
1. **color** — Tol is one of many colorblind-safe systems. ColorBrewer, Crameri, matplotlib, oklch, APCA.
2. **distributions** — Raincloud plots, letter-value plots, ridgeline innovations.
3. **network** — Graphology, sigma.js, hive plots, matrix hybrids.
4. **data-gathering** — Arrow, DuckDB-WASM, Parquet in browser.
5. **force** — UMAP/t-SNE, stress majorization, WebWorker patterns, ForceAtlas2.

### Priority 2 — Moderate expansion
6. **cartography** — Vector tiles, PMTiles, projection selection depth.
7. **time-series** — Multi-scale time, anomaly bands, Grafana patterns.
8. **linked-views** — Mosaic, Vega-Lite selections, when to use a framework.
9. **annotation** — Scrollytelling, annotation-as-data, Observable Plot marks.
10. **canvas** — OffscreenCanvas workers, WebGPU horizon, texture atlases.

### Priority 3 — Targeted additions
11. **hierarchy-layouts** — Icicle, flame charts, marimekko-as-treemap.
12. **brushing** — Falcon, lasso, brush composition.
13. **scales** — Diverging, threshold, perceptual uniformity.
14. **visual-texture** — Houdini paint worklets, perception research.
15. **motion** — View transitions API, scrollama.

### Priority 4 — Polish
16-26. Remaining skills get targeted research additions without full expansion.

## Container Network Constraints

The container firewall (`init-firewall.sh`) blocks all outbound traffic except GitHub, npm, Anthropic, and Sentry. Sub-agents inside the container **cannot** do web searches or fetch arbitrary URLs.

### Two-phase approach

**Phase A: Research (on host, before container)**
Run from the host machine with full internet access. For each skill:
1. Do 3-5 web searches for state-of-the-art in the skill's domain
2. Save findings as structured markdown files in `temp/research/<skill-name>.md`
3. Include: key techniques to add, palette/library names, code patterns, notable examples, citations

This can be parallelized with 3 research agents running concurrently. Each produces a research file that the container agents will consume.

**Phase B: Expansion (in container)**
Run inside the container. For each skill:
1. Read `temp/research/<skill-name>.md` for pre-gathered research
2. Read the current SKILL.md
3. Expand the skill based on research findings
4. Update examples if needed
5. Run tests
6. Commit

### Alternative: Add research domains to firewall

Add commonly-needed research domains to `init-firewall.sh`:
```bash
# Research domains for philosophy pass
for domain in \
    "observablehq.com" \
    "d3js.org" \
    "colorbrewer2.org" \
    "developer.mozilla.org" \
    "arxiv.org" \
    "dl.acm.org" \
    "clauswilke.com" \
    "cran.r-project.org"; do
    ...
done
```

This is simpler but permanently widens the firewall. The two-phase approach is safer.

## Parallelism

### Phase A (host): 3 research agents in parallel
Each agent does web research for one skill and writes `temp/research/<skill-name>.md`.

### Phase B (container): 3 expansion agents in parallel via worktrees
Queue file at `temp/research-queue.json`.

Each agent:
1. Reads `temp/research/<skill-name>.md` (pre-gathered research)
2. Reads the current SKILL.md
3. Identifies gaps between current coverage and state of the art
4. Expands the skill with researched alternatives and guidance
5. Updates the example if needed
6. Runs tests
7. Commits

## Constraints

- **Don't bloat.** Research expands options, but the skill should guide choices, not list everything. If adding 3 palette systems, add a decision table for when to use each.
- **Verify everything.** New code snippets must work. New palette names must be correct. New library references must be current.
- **Stay D3-focused.** Mention alternatives (deck.gl, Observable Plot) but frame them as "when to reach for this instead," not as tutorials for other libraries.
- **Update examples.** If a skill gains significant new material, the example should demonstrate it.
- **Log findings.** Append to `notes/SHARPENING-LOG.md`.

## Git Workflow

Same as Phase 1. One commit per skill: `Research-expand <skill-name>: <brief summary>`

## Loop Commands

### Phase A: Research (run on host with internet)
```
/loop 25m Research 3 skills in parallel per iteration. Read temp/research-queue.json. Claim next 3 skills not yet researched. Launch 3 agents in parallel. Each agent: (1) do 3-5 web searches for state-of-the-art techniques, palettes, libraries, perceptual research, and notable examples, (2) read the current SKILL.md to understand what's already covered, (3) write findings to temp/research/<skill-name>.md with sections: New Techniques, Broader Alternatives, Notable Examples, Code Patterns, Decision Guidance. Mark as researched in the queue.
```

### Phase B: Expansion (run in container)
```
/loop 25m Expand 3 skills in parallel per iteration. Read temp/research-queue.json. Claim next 3 researched-but-not-expanded skills. Launch 3 worktree-isolated agents. Each agent: (1) read temp/research/<skill-name>.md, (2) read the current SKILL.md, (3) expand with researched alternatives and decision guidance, (4) update example if needed, (5) run tests, (6) commit. Mark as expanded in the queue.
```

## Done When

All 26 skills have been research-expanded. Then update CRITIQUE.md with revised tier rankings.

## Verification

After the full pass:
1. Run full test suite: `python3 scripts/test-viz.py --config tests/test.config.json`
2. Spot-check 5 skills by reading SKILL.md for accuracy
3. Verify new palette/library references are current (not deprecated)
4. Compare line counts — skills should grow modestly (10-30%), not double
