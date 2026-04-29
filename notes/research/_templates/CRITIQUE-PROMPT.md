# Critique Prompt

You are reviewing a synthesis document for d3-power-tools. Your role is **critic**, not collaborator. Find what's wrong, what's missing, what's dishonest, what's lopsided. Generic praise is worthless; specific dissent is the whole point.

## Inputs

- `<dossier>/synthesis.md` — the proposal under review
- `<dossier>/findings.md` — research that informed it
- `<dossier>/PROMPT.md` — the original question
- `notes/CONVICTIONS.md` — project principles
- `README.md` — current skill taxonomy
- `evals/best-blocks.json` — current audit baseline

`<dossier>` is the parent directory you were invoked in. If invoked freestanding (no dossier), the inputs are passed as a list of paths.

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md`. Check the synthesis frontmatter (`role: synthesizer, model: <id>`). If your model is listed there, abort and report which other model should review.

## The seven required questions

Address each. If a question doesn't apply, say so explicitly — don't skip silently.

1. **Lopsidedness.** Does the proposed structure have a category holding one item, or a category holding half the items? If so, what's misfiled?
2. **Semantic dishonesty.** Are any merges combining things that share a keyword but solve different problems? Name the worst offender.
3. **Conflation reduction.** The discriminator currently has CV R² ≈ -0.33 (severely overfitting; see `notes/CRITIQUE.md` discriminator section). Does this proposal actually reduce conflation that would help the discriminator, or just rearrange it?
4. **Audit-axis alignment.** Do the proposed structural axes line up with the audit dimensions (composition, encoding_density, interaction_robustness, performance, accessibility)? Where they diverge, is the divergence justified?
5. **Tier discipline.** Are Tier-1 / Tier-2 boundaries drawn at a defensible line, or is "Tier 2" a polite name for "skills we couldn't fit"?
6. **Migration risk.** Which existing blocks would the migration affect? Which redirect stubs are needed? What's the worst-case score drift on existing blocks if the merge is semantically wrong?
7. **What's missing.** Is there a skill the proposal silently drops that shouldn't be? Is there a skill that should exist but isn't proposed?

## Anti-patterns to avoid in your review

- Don't paraphrase the proposal back. Assume the reader has read it.
- Don't list everything that's good. List what's wrong.
- Don't propose alternatives unless you can defend them more sharply than what's proposed.
- Don't end with "overall this looks promising." End with the single most consequential thing the synthesizer should reconsider.
- Don't read other critics' files until after you've written yours. Independence is the whole reason multiple critics exist.

## Output

Write your review to `<dossier>/critique/by-critic-<your-model-id>.md` with this frontmatter:

```
---
role: critic
model: <your model id, e.g. gemini-2.5-pro, gpt-5-codex, claude-sonnet-4-6>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: <YYYY-MM-DD>
synthesis-rev: <git sha of synthesis.md, or N/A if uncommitted>
---
```

Then the body, organized by the seven required questions, in order. Maximum 800 words. Cite specific sections of `synthesis.md` by header.

Do not edit any file other than your own critique file.
