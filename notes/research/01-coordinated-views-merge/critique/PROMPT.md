# Critique Prompt — Dossier 01 (coordinated-views merge)

You are reviewing the synthesis document for this dossier. Your role is **critic**, not collaborator. Find what's wrong, what's missing, what's dishonest, what's lopsided. Generic praise is worthless; specific dissent is the whole point.

> This is the dossier-local adaptation of `notes/research/_templates/CRITIQUE-PROMPT.md`. If anything in this file conflicts with the upstream template, the template wins — flag the divergence in your review.

## Inputs

- `notes/research/01-coordinated-views-merge/synthesis.md` — the proposal under review
- `notes/research/01-coordinated-views-merge/findings.md` — empirical comparison of the three skills
- `notes/research/01-coordinated-views-merge/PROMPT.md` — the original question
- `notes/CONVICTIONS.md` — project principles
- `notes/CRITIQUE.md` (existing) — prior critic feedback for context, especially the discriminator section
- `README.md` (project root) — current skill taxonomy
- Source skills under review:
  - `skills/brushing/SKILL.md`
  - `skills/linked-views/SKILL.md`
  - `skills/coordination/SKILL.md`
- `evals/best-blocks.json` — current audit baseline

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md`. Check the synthesis frontmatter (`role: synthesizer, model: <id>`). If your model is listed there, abort and report which other model should review.

## The seven required questions

Address each. Don't skip silently.

1. **Lopsidedness.** Does the proposed shape leave any skill carrying a single concept while another carries five? In particular: if `brushing` is supposed to focus on mechanics post-merge, does it still have enough content to justify a top-level skill, or does it become a stub?

2. **Semantic dishonesty.** Three SelectionManager-like classes exist today (see findings §"Where the overlap actually lives"). Does the merge actually pick one and absorb the others, or does it paper over the difference? Name the worst offender.

3. **Conflation reduction.** The discriminator currently has CV R² ≈ -0.33 with `interaction_brush` as a top *negative* predictor (per `notes/CRITIQUE.md`). Does this proposal genuinely reduce the conflation that's driving that signal, or just rearrange it?

4. **Audit-axis alignment.** Where does `coordinated-views` (or whatever the merged skill is called) sit on the audit dimensions (composition, encoding_density, interaction_robustness, performance, accessibility)? Is the answer "all of them" — and if so, is that a sign the merge is too broad?

5. **Tier discipline.** The broader proposal puts `coordinated-views` in Tier-1 Interaction. But framework bridges (React/Vue/Angular) and Mosaic/Falcon/DuckDB integrations are arguably Tier-2 specialties. Does the synthesis split these correctly, or stuff everything into one tier?

6. **Migration risk.** Which existing blocks would the migration affect most? In particular: `02-linked-scatterplot-matrix`, `13-radial-dendrogram-edge-bundling`, `hierarchy-bundles`, and `blockbuilder-explorer` are known multi-skill blocks. What's the worst-case score drift if the merged SKILL.md is semantically narrower than the union of the three?

7. **What's missing.** Brush mechanics (intersection, lasso, fisheye, spatial indexing) must not get lost. Does the synthesis explicitly preserve them and state where they live? Is anything else silently dropped?

## Anti-patterns

- Don't paraphrase the proposal back. Assume the reader has read it.
- Don't list everything that's good. List what's wrong.
- Don't propose alternatives unless you can defend them more sharply than what's proposed. The synthesis already canvasses three options (full merge / move-and-keep / status quo); a fourth must clear that bar.
- Don't end with "overall this looks promising." End with the single most consequential thing the synthesizer should reconsider.
- Don't read other critics' files until after you've written yours. Independence is the whole reason multiple critics exist.

## Output

Write to `notes/research/01-coordinated-views-merge/critique/by-critic-<your-model-id>.md` with this frontmatter:

```
---
role: critic
model: <your model id, e.g. gemini-2.5-pro, gpt-5-codex, claude-sonnet-4-6>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: 2026-04-29  # or whatever today is
synthesis-rev: <git sha of synthesis.md, or N/A if uncommitted>
---
```

Then the body, organized by the seven required questions, in order. Maximum 800 words. Cite specific sections of `synthesis.md` by header.

Do not edit any file other than your own critique file.
