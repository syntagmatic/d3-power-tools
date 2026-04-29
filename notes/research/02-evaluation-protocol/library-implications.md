# Library Implications

Per-action checkboxes. Tick in the same commit as the change. Until the synthesis lands, the second section is a placeholder.

## Pre-synthesis prep

- [ ] `findings.md` populated (lit review + project-artifact examination)
- [ ] `findings.md` cites ≥6 external references with one-sentence relevance notes
- [ ] `findings.md` includes a section on how dossier 01's gaps would be addressed by each candidate protocol shape

## Synthesis phase

- [ ] `synthesis.md` committed with frontmatter (`role: synthesizer`, `model:`, `date:`)
- [ ] Synthesis names a single recommended protocol, not a survey
- [ ] Synthesis specifies sample size with a variance-based justification, or explicitly states no variance estimate is available and what the consequence is

## Critique phase

- [ ] Critic 1 review filed (`critique/by-critic-<model>.md`)
- [ ] Critic 2 review filed
- [ ] At least one critic is the dossier-01 synthesizer (gpt-5-codex), or an explicit note explains why this wasn't possible
- [ ] Maintainer responses filed (`critique/responses.md`)
- [ ] All blockers resolved or explicitly accepted

## Pilot phase

- [ ] Pilot runner produced `tests/pilot/by-pilot-<model>.md`
- [ ] Pilot's verdict on dossier 01 (graduate / iterate / shelve) is recorded
- [ ] Pilot's "failure modes" section is non-empty — if empty, that's a finding worth flagging

## Graduation gates

- [ ] ≥2 critics signed off
- [ ] Pilot's verdict on dossier 01 is either consistent with dossier 01's actual decision (when known) or names a specific weakness the old protocol missed
- [ ] Decision filed in `decision.md`

## Library changes (filled when graduating)

> The synthesis defines these. Until synthesis is written, these are placeholders.

### Templates

- [ ] `notes/research/_templates/CRITIQUE-PROMPT.md` updated (or rationale documented for leaving alone)
- [ ] `notes/research/_templates/TEST-PROMPT.md` updated
- [ ] `notes/research/_templates/BLIND-JUDGE-PROMPT.md` updated
- [ ] Dossier-level `README.md` template (currently inline in dossier 01) extracted to `_templates/DOSSIER-README.md`
- [ ] `library-implications.md` template extracted to `_templates/LIBRARY-IMPLICATIONS.md`

### Protocol document

- [ ] `notes/EVALUATION-PROTOCOL.md` written (single source of truth for graduation criteria, sample size policy, judge calibration, pre-registration policy, discriminator role)
- [ ] `notes/CONVICTIONS.md` cross-references `EVALUATION-PROTOCOL.md` from the "Judge and maker must not share a room" entry

### Standard fixtures (if synthesis recommends)

- [ ] `notes/research/_fixtures/` created
- [ ] At least one fixture migrated from dossier 01 (`tests/fixtures/iris/`) into `_fixtures/` for reuse
- [ ] `_fixtures/README.md` explains when to use a standard fixture vs roll a per-dossier one

### Discriminator policy

- [ ] Discriminator role decided (gate / sanity check / shelve)
- [ ] If gate: dataset-size remediation plan documented
- [ ] If sanity check: threshold for a flag documented
- [ ] If shelve: replacement signal documented and `evals/discriminator.json` either removed or marked deprecated

### Backfill into dossier 01

- [ ] Dossier 01's `library-implications.md` updated to match the new protocol (or explicit grandfathering note)
- [ ] If dossier 01 has not yet graduated: its synthesis is given a chance to revise under the new protocol before tests run

## Post-graduation

- [ ] Iteration index regenerated (`python3 -c "from scripts.iterate_lib import generate_progress_html; generate_progress_html()"`)
- [ ] Decision archived in `decision.md`
- [ ] Dossier status set to `graduated`
- [ ] First post-protocol dossier (03+) opened against the new protocol — note the dossier number here when filed
