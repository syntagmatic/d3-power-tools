# Critique Prompt — Dossier 02 (Audit Architecture & Protocol)

You are reviewing the synthesis document for this dossier. Your role is **critic**, not collaborator. Find what's wrong, what's missing, what's dishonest, what's lopsided. Generic praise is worthless; specific dissent is the whole point.

> This dossier merges architecture and methodology. The seven required questions below replace the upstream `_templates/CRITIQUE-PROMPT.md` questions, which are taxonomy-shaped.

## Inputs

- `notes/research/02-audit-architecture/synthesis.md` — the proposal under review (architecture + protocol)
- `notes/research/02-audit-architecture/findings.md` — the architectural review of the current data layer
- `notes/research/02-audit-architecture/PROMPT.md` — the original question
- `notes/research/02-audit-architecture/library-implications.md` — the commit checklist
- `notes/research/01-coordinated-views-merge/` — the dossier whose graduation criteria the proposal must support
- `notes/CONVICTIONS.md` — project principles
- `notes/CRITIQUE.md` — prior critic feedback, including discriminator state
- Source code under review:
  - `scripts/run-audit-pipeline.py`, `iterate-block.py`, `iterate-prompt.py`, `iterate_lib.py`, `eval-hierarchy-bundles.py`
  - `evals/iterations/index.html` (JS reader)

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md` for this dossier. Check the synthesis frontmatter (`role: synthesizer, model: <id>`).

A model that synthesized **dossier 01** is explicitly invited — your prior protocol claims are being indirectly examined and you should get to push back.

## The seven required questions

Address each. Don't skip silently.

1. **Schema discipline.** Does `AuditSchema` actually make schema mismatches *loud*, or is it a label that callers can paper over? Concretely: if `compare(general_run, transition_run)` is called by mistake, does the API raise, return a degraded result, or silently produce a misleading number? Cite the proposed code by section.

2. **Composite comparability.** The findings establish that general and transition composites are not on the same scale. Does the synthesis's `composite()` method enforce this, or just convention? Is there a worked example showing what happens when a future caller (e.g., a leaderboard or a cross-block average) tries to combine composites across schemas?

3. **Provenance integrity.** Dossier 01's graduation gates require per-result `(generator_model, judge_model, fixture_id)`. Does the synthesis put these on `AuditResult` (correct) or only on `Run` (insufficient)? If on `AuditResult`, what's the round-trip story for legacy `evals/runs/*.json` files that don't carry these fields? Does `from_dict` fabricate them, refuse them, or default them?

4. **Pre-registration mechanics.** The README claims graduation criteria are "locked at draft." Does the synthesis specify *how* — file conventions, frontmatter checks, a script that asserts `decision.md` matches the criteria recorded in README and synthesis? If it's honor-system, name it as honor-system. If it's mechanical, walk the enforcement path.

5. **Migration honesty.** The plan archives v1 evals to `archive/v1/evals/` and tags `v1-pre-research`. What old data is *lost in the spirit even if preserved in tag*? Specifically: 27MB of `evals/iterations/` represents 200+ historical iteration runs. Does anything in the new system reference them, or are they truly write-only-from-here? Is the loss acknowledged, or papered over with "tag preserves everything"?

6. **Cost and scope creep.** Walk the proposed `scripts/audit/` package by line count. Is the new package small (≤1500 LOC) and tightly scoped, or has it grown into a framework with policy-layer concerns it doesn't need? Particularly suspect: anything resembling a plugin system, a configuration loader, or an event bus.

7. **What's missing.** What's the protocol silent on that future dossiers will hit? In particular: how does it behave for a *split* dossier (one skill into two) vs a *merge* dossier (two into one)? Are graduation gates symmetric? What about a dossier that proposes deleting a skill entirely with no replacement?

## Anti-patterns

- Don't paraphrase the proposal back. Assume the reader has read it.
- Don't list everything that's good. List what's wrong.
- Don't propose alternatives unless you can defend them more sharply than what's proposed.
- Don't end with "overall this looks promising." End with the single most consequential thing the synthesizer should reconsider.
- Don't read other critics' files until after you've written yours. Independence is the whole reason multiple critics exist.

## Output

Write to `notes/research/02-audit-architecture/critique/by-critic-<your-model-id>.md` with this frontmatter:

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

Body organized by the seven required questions, in order. Maximum 1000 words. Cite specific sections of `synthesis.md` by header and proposed code files by path.

Do not edit any file other than your own critique file.
