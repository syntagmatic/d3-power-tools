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

Renamed all meta skills for the power-tool theme. Auditing skills kept separate (research-backed): visual-critic (design), encoding-integrity (honesty), stress-test (robustness), cognitive-load (clarity). Merged adversarial-eval + skill-eval → calibrate-tool. Code guides: d3-idioms (style), jig-template (architecture). check-skill merged into sharpen-tool.

### ~~5. Clean up archive~~ ✓ Done

Deleted `notes/archive/` (178K, 7 files). Lessons in CONVICTIONS.md, content in git history.

## Ongoing

- **Standardize Chart Communication:** Use `d3.dispatch` with mandatory namespacing (`event.id`) and a shared `state` object. Document bridge patterns for React (Context/Hooks), Vue (Provide/Inject), and Angular (runOutsideAngular) to avoid update storms.
- **Choreography Skill:** Formalize multi-stage sequencing using `async/await` with `transition.end()`. Include staggering patterns and the "Sticky Graphic" scrollytelling layout as a standard orchestration pattern.
- **Self-visualization as regression suite.** Skill dependency graph, block × skill matrix, audit scorecard. The project should be its own best test case.

## Autoresearch iteration

Pipeline built and tested. See `AUTORESEARCH.md` for full details and next steps.

- `iterate-block.py` compacts blocks (LOC ↓, composite holds). 5 blocks done, ~15-20% reduction typical, ~75% keep rate.
- `iterate-prompt.py` optimizes prompts (gen time ↓, features preserved). Not yet exercised end-to-end.
- Skill track deferred until block/prompt tracks prove out.

**Next steps (in priority order):**
1. **Batch runner** — iterate across 20 worst-scoring blocks overnight. Highest leverage.
2. **Visual regression detection** — screenshot diff as a gate in decide_block. Catches layout breakage that composite scores miss.
3. **Diminishing returns stop** — stop when last 5 keeps average <5 lines. Saves budget for the batch runner.
4. **Exercise prompt track** — run iterate-prompt on a slow-generating block.
5. **Proposer prompt tuning** — A/B test different proposer prompts, measure keep rate.
6. **Skill track** — iterate SKILL.md files (noisiest, needs multi-block averaging).

## From v2 findings

See `V2-FINDINGS.md` for full data.

- **Compressed skill summaries.** Skills help quality (+0.06 to +0.45 composite) but hurt sonnet completion rate (skills take too long to read). A one-page cheat sheet per skill would preserve quality gains without the time cost. Highest-value next step for skill effectiveness.
- **Strengthen stress-test patterns.** All models score lowest on interaction robustness (6.0-7.0). Skills should include explicit RAF coalescing, debounced brush handlers, and transition conflict guards. The patterns exist in the stress-test audit criteria but not in the content skills.
- **Sonnet with longer timeout.** Sonnet quality matches opus (7.06 vs 7.04 composite) but 64% of blocks timeout at 300s. Most pass at 600s. Worth completing the full 105 at 600s to get a proper quality comparison.
- **Full 105-block audit comparison.** Currently 52 opus blocks audited. Running opus+skills for all 105 would give a definitive quality baseline for the skills.

**Ship it.** Distribution, discovery, onboarding.
