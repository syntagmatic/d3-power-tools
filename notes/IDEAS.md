# Ideas

What's worth building next. Full backlog in `archive/IDEAS.md`.

---

## Simplification

### ~~1. Compress block prompts~~ ✓ Done

All 105 block prompts compressed. All 105 v1 blocks generated (85-105 added with simplified prompts). Shared defaults.suffix handles boilerplate. Generation script: `scripts/generate-blocks-claude.py`.

**Next:** Audit v1 blocks (run 5-lens adversarial eval for v0-vs-v1 comparison).

### ~~2. Compress the largest skills~~ ✓ Done

Six skills compressed: cartography 401→279, data-gathering 394→195, webgl 385→273, motion 362→253, canvas 353→251, navigation 352→286. All under 300 lines. Stripped API docs, kept decision frameworks and warnings.

### ~~3. Cull redundant examples~~ ✓ Done

Deleted 3 redundant examples (966 lines): color-compositing (compositing-gallery covers it), layout-morph (shape-morph covers point resampling), hierarchy-patterns (layout-switcher covers all 8 layouts). Network examples kept (3 different chart types). Test config updated.

### ~~4. Consolidate meta skills~~ ✓ Partially done

Merged check-skill into sharpen-tool (checking is part of sharpening). Auditing skills (visual-critic, encoding-integrity, interaction-stress-test, perceptual-red-team) kept separate — research confirms decomposed single-criterion evaluation outperforms combined prompts (lost-in-the-middle, attention dilution, instruction omission at scale).

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
