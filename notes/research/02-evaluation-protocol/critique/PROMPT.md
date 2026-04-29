# Critique Prompt — Dossier 02 (evaluation protocol)

You are reviewing the synthesis document for this dossier. Your role is **critic**, not collaborator. Find what's wrong, what's missing, what's dishonest, what's lopsided. Generic praise is worthless; specific dissent is the whole point.

> This is the dossier-local adaptation of `notes/research/_templates/CRITIQUE-PROMPT.md`. Because dossier 02's question is methodology rather than taxonomy, the seven required questions are restated below — they replace, not augment, the template's questions.

## Inputs

- `notes/research/02-evaluation-protocol/synthesis.md` — the proposal under review
- `notes/research/02-evaluation-protocol/findings.md` — lit review + project-artifact examination
- `notes/research/02-evaluation-protocol/PROMPT.md` — the original question
- `notes/research/02-evaluation-protocol/tests/pilot/` — paper pilot applying the proposal to dossier 01
- `notes/research/01-coordinated-views-merge/` — full dossier 01 (the empirical case the proposal must explain)
- `notes/CONVICTIONS.md` — project principles
- `notes/CRITIQUE.md` — discriminator state, prior methodology critiques
- `notes/V2-FINDINGS.md` — empirical pass-rate data
- `notes/AUTORESEARCH.md` — per-block iteration loop (the working methodology to compare against)
- `evals/anchors.json`, `evals/discriminator.json` — current calibration and discriminator artifacts

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md`. Check the synthesis frontmatter (`role: synthesizer, model: <id>`).

A model that synthesized **dossier 01** is explicitly invited to critique here — its work is being indirectly examined and it should get to push back.

## The seven required questions

Address each. Don't skip silently.

1. **Does the proposed protocol actually solve dossier 01's baseline gap?** Concretely: if dossier 01 had used this protocol from the start, would it have generated a different (better) baseline plan? Cite the specific section of the proposal that closes the gap, or name what's still missing.

2. **Sample-size honesty.** Does the proposal specify N (generators × fixtures × judges) and defend it with variance estimates or a power calculation? Or does it wave at "more is better"? If the proposal increases cost relative to the status quo, is the increase justified by the effect size it can detect?

3. **Judge bias coverage.** LLM-as-judge has known biases: position, length, self-preference, verbosity. Does the proposal name which biases it controls for, and how? Which known biases does it leave on the table?

4. **Pre-registration vs post-hoc framing.** Where in the dossier lifecycle do graduation criteria get locked? If they're set in `synthesis.md` after `findings.md` is written, that's post-hoc. Does the proposal address this, or does it dress post-hoc framing in pre-registration language?

5. **Discriminator role.** Does the proposal make a defensible call on the Ridge discriminator (gate / sanity check / shelve)? If "gate," is there a plan for the dataset-size problem? If "sanity check," what's the threshold for it to flag a problem? If "shelve," is the replacement signal specified?

6. **Cost feasibility.** Walk through a hypothetical merge dossier under the proposed protocol. Count LLM calls. Is the per-dossier cost roughly known and roughly affordable, or is the proposal a methodology that the project cannot actually run at the cadence it wants to refactor?

7. **What's missing.** What methodology question that future dossiers will hit is silently dropped? In particular: how does this protocol behave for a *split* dossier (one skill into two) vs a *merge* dossier (two into one)? Are the gates symmetric?

## Anti-patterns

- Don't paraphrase the proposal back. Assume the reader has read it.
- Don't list everything that's good. List what's wrong.
- Don't propose alternatives unless you can defend them more sharply than what's proposed.
- Don't end with "overall this looks promising." End with the single most consequential thing the synthesizer should reconsider.
- Don't read other critics' files until after you've written yours. Independence is the whole reason multiple critics exist.

## Output

Write to `notes/research/02-evaluation-protocol/critique/by-critic-<your-model-id>.md` with this frontmatter:

```
---
role: critic
model: <your model id>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: <YYYY-MM-DD>
synthesis-rev: <git sha of synthesis.md, or N/A if uncommitted>
also-critiqued-dossier-01: <true|false>
---
```

Body organized by the seven required questions, in order. Maximum 1000 words. Cite specific sections of `synthesis.md` by header.

Do not edit any file other than your own critique file.
