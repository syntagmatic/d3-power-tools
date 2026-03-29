# Ideas

What's worth building next. Full backlog in `archive/IDEAS.md`.

---

## Simplification

### ~~1. Compress block prompts~~ ✓ Done

All 84 block prompts compressed to avg 29 words (from 160). All 84 v1 blocks generated and tested. Shared defaults.suffix handles boilerplate. Listing pages: `blocks-latest.html` (v1 only), `blocks.html` (archive with v0 Claude/Gemini/v1 + eval scores).

**Next:** Audit v1 blocks (run 5-lens adversarial eval for v0-vs-v1 comparison).

### 2. Compress the largest skills

Top 6 by line count: cartography (401), data-gathering (394), webgl (385), motion (362), canvas (353), navigation (352). Likely contain API docs models already know. Strip API documentation, keep decision frameworks and warnings. Target: each under 300 lines.

### 3. Cull redundant examples

Skills with 3+ examples likely have overlap:
- `color/`: compositing (420 lines), legend (310), compositing-gallery (205) — "compositing" appears twice
- `shape-morphing/`: 4 examples — likely overlap
- `hierarchy-layouts/`: layout-switcher (449) + hierarchy-patterns (350)
- `network/`: 3 examples (arc, adjacency, chord) — each a different chart type, may all be justified

Read and screenshot each. Keep the best per skill. Update test config.

### 4. Consolidate meta skills (11 → 6)

Four auditing skills (visual-critic, encoding-integrity, interaction-stress-test, perceptual-red-team) → one `audit` skill with sections. Two maintenance skills (check-skill, sharpen-tool) → one `skill-maintenance` skill. Keep idiomatic-d3, cross-skill-composition, skill-eval, adversarial-eval as-is.

### 5. Clean up archive

`notes/archive/` has 178K of process logs. Lessons already distilled in CONVICTIONS.md. Delete the directory; content lives in git.

---

## Infrastructure

**Eval as CI.** Wire encoding-integrity metamorphic checks (scaling, permutation, subset, shift) as the first automated eval. Run on every skill commit. If scores drop, the commit is a regression.

**Asymmetric evaluation.** Claude generates, a symbolic checker or different model scores. The only way to break shared-bias evaluation.

**Frontmatter audit.** Review name and description across all skills for consistency and trigger accuracy. Bad descriptions mean wrong skills load.

## Ongoing

**Self-visualization as regression suite.** Skill dependency graph, block × skill matrix, audit scorecard. The project should be its own best test case.

**Ship it.** Distribution, discovery, onboarding.
