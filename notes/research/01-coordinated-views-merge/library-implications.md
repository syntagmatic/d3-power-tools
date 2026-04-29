# Library Implications

Per-action checkboxes. Tick in the same commit as the change. `pnpm research:audit` (when implemented) verifies the README table against actual box counts. Until then, this file is the source of truth.

## Pre-merge prep

- [ ] Pre-refactor baseline audit run logged (cite run ID in `synthesis.md`)
- [ ] Synthesis committed and frontmatter populated (`role: synthesizer`, `model:`, `date:`)
- [ ] `tests/skill-under-test/SKILL.md` written by synthesizer

## Critique phase

- [ ] Critic 1 review filed (`critique/by-critic-<model>.md`)
- [ ] Critic 2 review filed
- [ ] Optional: Critic 3 review filed
- [ ] Maintainer responses to critique filed (`critique/responses.md`)
- [ ] All blockers either resolved or explicitly accepted

## Test phase (only if synthesis chose merge over status-quo)

- [ ] Alt-generator A produced iris block (`tests/blocks/<model-A>/iris.html`)
- [ ] Alt-generator B produced iris block
- [ ] Alt-generator C produced iris block
- [ ] Generator logs filed (`tests/blocks/<model>/log.md`) for each
- [ ] Blind judge 1 audit filed (`tests/audit/by-judge-<model>.md`)
- [ ] Blind judge 2 audit filed
- [ ] Cross-judge agreement check: composite scores within ±1.0 across judges

## Graduation gates

- [ ] Cross-model audit composites within ±0.5 of baseline (per `synthesis.md`)
- [ ] No `render-error` flags in any block
- [ ] `multi-skill-leak` flags ≤1 per block (slight bleed acceptable)
- [ ] Decision filed in `decision.md`

## Library changes (filled when graduating)

> The synthesis defines these. Until synthesis is written, these are placeholders.

### If Option B (move-and-keep):

- [ ] New `skills/coordinated-views/SKILL.md` written
- [ ] `skills/linked-views/SKILL.md` deleted (content absorbed)
- [ ] `skills/coordination/SKILL.md` deleted (content absorbed)
- [ ] `skills/linked-views/SKILL.md` replaced with redirect stub (`→ coordinated-views`)
- [ ] `skills/coordination/SKILL.md` replaced with redirect stub
- [ ] `skills/brushing/SKILL.md` cross-chart linking section removed
- [ ] `skills/brushing/SKILL.md` `description:` frontmatter updated to drop "linked views" / "coordinated highlighting" triggers
- [ ] `notes/research/coordination.md` created (research note absent, should exist)
- [ ] `README.md` taxonomy section updated
- [ ] `meta/jig-template/SKILL.md` cross-references updated (currently mentions linked-views)
- [ ] Other cross-references audited via `grep -l "linked-views\|coordination" skills/*/SKILL.md meta/*/SKILL.md`

### If Option A (full merge):

- [ ] (defer until synthesis chooses)

### If Option C (status quo):

- [ ] SelectionManager / ComposableSelectionManager / SelectionModel deduped to one canonical implementation
- [ ] Cross-references between the three skills tightened
- [ ] No file moves

## Post-graduation

- [ ] Iteration index regenerated (`python3 -c "from scripts.iterate_lib import generate_progress_html; generate_progress_html()"`)
- [ ] Decision archived in `decision.md`
- [ ] Dossier status set to `graduated`
- [ ] Any follow-up dossiers filed (e.g., framework-bridges sub-skill if synthesis surfaces that question)
