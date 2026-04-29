# Pilot Prompt — Dossier 02 (evaluation protocol)

You are running the **paper pilot** for this dossier. Your role: take the protocol proposed in `synthesis.md` and apply it retroactively to dossier 01, then write what would have been different. The pilot is paper-only — no new generations, no new audits. The deliverable is a delta document, not new data.

## Inputs

- `notes/research/02-evaluation-protocol/synthesis.md` — the proposed protocol
- `notes/research/02-evaluation-protocol/findings.md` — research that informed it
- `notes/research/01-coordinated-views-merge/` — the dossier the protocol must explain
  - `synthesis.md` — what dossier 01 actually proposed
  - `library-implications.md` — what dossier 01 actually committed to as gates
  - `findings.md` — the empirical case
- `notes/CRITIQUE.md`, `notes/V2-FINDINGS.md`, `notes/AUTORESEARCH.md` — for cross-check on what existing data would tell us under the proposed protocol

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md` for this dossier. You may have synthesized dossier 01 — that is in fact useful here, because the pilot questions whether your prior methodology held up.

## Task

Produce a single document, `notes/research/02-evaluation-protocol/tests/pilot/by-pilot-<your-model-id>.md`, that answers:

1. **Baseline.** Under the proposed protocol, what is dossier 01's baseline? (Existing-block snapshot, paired generation, held-out fixtures, or a combination?) Specify exactly what would be measured. If the proposed protocol differs from what dossier 01 currently plans, name the difference in cost and the difference in interpretive power.

2. **Sample size.** How many alt-generators × fixtures × judges does the protocol require for dossier 01 specifically? Is the answer a fixed N or derived from a variance estimate? If derived, what variance was assumed, and is the assumption supported by anything in `notes/V2-FINDINGS.md` or other repo data?

3. **Pre-registration check.** What graduation criteria does the proposed protocol require dossier 01 to lock down before research begins? Compare to dossier 01's actual `library-implications.md` (which was filled after `findings.md`). What changes?

4. **Discriminator integration.** Does the protocol require dossier 01 to use the Ridge discriminator as a gate, sanity check, or not at all? Apply that policy: what does the discriminator say about dossier 01 today?

5. **Verdict.** Would dossier 01 graduate, iterate, or shelve under the proposed protocol — given only what's already in the dossier (no new runs)? If "iterate," what specific revisions would the protocol require?

6. **Failure modes.** What does the protocol fail to catch in dossier 01 that an honest reader of dossier 01 would still want caught? This question is the most important one — answer it carefully.

## Constraints

- **Paper only.** Do not run the audit pipeline, do not generate blocks, do not call any model in a generative loop. Reading repo files, running `grep`, and reading `evals/runs/*.json` is fine.
- **Cite, don't summarize.** When you say "the protocol requires X," quote the section. When you say "dossier 01 chose Y," quote the section.
- **No suggestions for dossier 01.** Your output is about whether the protocol works, not about how to fix dossier 01.

## Output

Frontmatter:

```
---
role: pilot
model: <your model id>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: <YYYY-MM-DD>
protocol-rev: <git sha of synthesis.md, or N/A if uncommitted>
dossier-01-rev: <git sha of dossier 01's synthesis.md>
---
```

Body: six sections matching the six questions above. Maximum 1500 words.

If running the pilot reveals the protocol is internally inconsistent (e.g. requires data the protocol itself doesn't say how to collect), stop and write a one-section report saying so. Do not paper over the inconsistency.
