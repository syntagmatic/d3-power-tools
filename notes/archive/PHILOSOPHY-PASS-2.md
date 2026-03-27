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

### Step 1: Read the research

Research is pre-gathered in `notes/research/<skill-name>.md` (or `priority-4-batch.md` for priority 4 skills). Read the research file and the current SKILL.md to identify gaps.

### Step 2: Expand the skill

Add new sections or broaden existing ones based on research findings. The expansion should:
- Offer alternatives, not just one way ("Tol palettes are excellent for colorblind safety; here are three other options and when each fits better")
- Reference real-world usage (Observable notebooks, production dashboards, notable visualizations)
- Add new recipes where the research reveals them
- Keep the judgment-first philosophy — don't just list options, guide the choice

### Step 3: Verify accuracy

Every new code snippet must be tested. Every new claim must be verifiable. Run the skill's tests.

### Step 4: Update the example if needed

If the skill expanded significantly, the example should demonstrate the new material.

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

## Status

**Phase A (research) is complete.** Research files exist for all 26 skills:
- Priority 1–3 and parallel-coordinates, responsive: individual files in `notes/research/<skill-name>.md`
- Remaining priority 4: combined in `notes/research/priority-4-batch.md`

**Phase B (expansion) is next.** Run in container with 3 worktree-isolated agents in parallel.

## Expansion Queue

Queue file: `temp/research-queue.json`. Skills are listed in priority order. Each agent:
1. Claims next skill from `queue`, moves to `expand_in_progress`
2. Reads `notes/research/<skill-name>.md` (or the relevant section of `priority-4-batch.md`)
3. Reads the current `skills/<skill-name>/SKILL.md`
4. Expands with researched alternatives and decision guidance
5. Updates the example if the skill gained significant new material
6. Runs tests: `python3 scripts/test-viz.py --config tests/test.config.json --skill <skill-name>`
7. Commits: `Research-expand <skill-name>: <brief summary>`
8. Moves skill from `expand_in_progress` to `expanded`

## Constraints

- **Don't bloat.** Research expands options, but the skill should guide choices, not list everything. If adding 3 palette systems, add a decision table for when to use each. Extract verbose inventories (e.g., all 60 d3-scale-chromatic schemes) to appendices, not main skill text.
- **Verify everything.** New code snippets must work. New palette names must be correct. New library references must be current. Timestamp version-dependent claims: "as of March 2026: ~70% browser support."
- **Stay D3-focused.** Mention alternatives (deck.gl, Observable Plot, Falcon, Mosaic) but frame them as "when to reach for this instead," not as tutorials for other libraries. External libraries get 1-2 paragraphs of "when to escalate" + link to external docs, not embedded tutorials.
- **Observable Plot "vs D3"** — where Plot offers the same pattern, add a consistent 1-2 sentence note: "Observable Plot's X mark handles this declaratively; use it for quick exploratory work, D3 for custom interaction or Canvas rendering." Don't teach Plot.
- **Respect skill ownership.** Each technique lives in ONE skill, cross-referenced from others:
  - OKLCH/color spaces → `color` skill
  - GPU escalation (WebGL/WebGPU decision) → `canvas` skill
  - Scrollytelling general patterns → `motion` skill; step-sequenced annotations → `annotation` skill
  - Falcon/scalable cross-filtering → `brushing` skill
  - Classification scales for choropleths → `scales` skill; color perception → `color` skill
- **Update examples.** If a skill gains significant new material, the example should demonstrate it.
- **Log findings.** Append to `notes/SHARPENING-LOG.md`.

## Git Workflow

Same as Phase 1. One commit per skill: `Research-expand <skill-name>: <brief summary>`

## Loop Command

Run in container:
```
/loop 25m Expand 3 skills in parallel per iteration. Read temp/research-queue.json. Claim next 3 skills from queue. Launch 3 worktree-isolated agents. Each agent: (1) read notes/research/<skill-name>.md (or relevant section of priority-4-batch.md for priority 4 skills), (2) read skills/<skill-name>/SKILL.md, (3) expand with researched alternatives and decision guidance, (4) update example if needed, (5) run tests with python3 scripts/test-viz.py --config tests/test.config.json --skill <skill-name>, (6) commit as "Research-expand <skill-name>: <brief summary>". Move skill from queue to expanded in the JSON.
```

## Done When

All 26 skills have been research-expanded. Then update CRITIQUE.md with revised tier rankings.

## Verification

After the full pass:
1. Run full test suite: `python3 scripts/test-viz.py --config tests/test.config.json`
2. Spot-check 5 skills by reading SKILL.md for accuracy
3. Verify new palette/library references are current (not deprecated)
4. Compare line counts — skills should grow modestly (10-30%), not double
