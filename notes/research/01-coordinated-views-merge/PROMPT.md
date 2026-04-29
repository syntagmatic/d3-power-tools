# Question

Should `skills/brushing/`, `skills/linked-views/`, and `skills/coordination/` merge into a single skill named `coordinated-views`?

## What we're trying to learn

1. **Is the apparent overlap real or surface-level?** All three skills fire on prompts mentioning brushing, linking, cross-filtering, coordinated highlighting. The discriminator can't separate blocks produced by them. But that could mean the skills genuinely cover one concept, or that the *prompts* are lazy — same trigger, different content underneath.

2. **If we merge, what loses scope?** brushing has 304 lines covering brush mechanics (intersection, lasso, fisheye, keyboard, spatial indexing) AND cross-chart linking AND a SelectionManager AND a ComposableSelectionManager. The brush-mechanic content is genuinely about selection; the linking content overlaps with both other skills.

3. **What's the right grain?** Three options worth weighing in synthesis:
   - **Full merge:** all three become `coordinated-views`. ~490 lines collapsed.
   - **Move-and-keep:** lift the linking content out of brushing into a merged `coordinated-views` (linked-views + coordination), keep `brushing` focused on brush mechanics.
   - **Status quo with cleanup:** keep all three, dedup the SelectionManager class definitions, make cross-references stricter.

4. **Will the merge actually reduce conflation in produced blocks?** This is the empirical question the test phase answers. Critics can argue about taxonomic cleanliness; only the cross-model block scores tell us whether the merge improves the discriminator's signal.

## Out of scope for this dossier

- Reorganizing `parallel-coordinates`, `small-multiples`, or any other skill that cross-references these three.
- The broader axis-aligned taxonomy refactor (Encoding/Layout/Interaction/Rendering/Composition). That's a separate dossier.
- Changing block content. Blocks stay where they are; only skill files move.

## Background

- Source proposal: the skill-taxonomy sketch in `notes/IDEAS.md` (and the conversation that produced this dossier system).
- Current discriminator state: `notes/CRITIQUE.md` discriminator section, R² 0.56 train / -0.33 CV, severely overfitting. Conflation between brush/link/coord skills is hypothesized as one driver.
- Existing per-skill research: `notes/research/brushing.md`, `notes/research/linked-views.md`. No `coordination.md` exists yet (recent skill, not yet researched).
