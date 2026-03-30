# v2 Generation Findings

Observations from v2 block generation runs (2026-03-29/30). 40 blocks tested across 6 configs: opus 4.6 and sonnet 4.6 (each with/without skills), gemini 3.1 pro preview (with/without skills).

## Pass rates

| Config | Pass | Fail | Rate |
|--------|------|------|------|
| opus + skills | 61 | 0 | 100% |
| opus + noskills | 39 | 1 | 98% |
| sonnet + skills | 14 | 25 | 36% |
| sonnet + noskills | 20 | 19 | 51% |
| gemini 3.1 pro + skills | 11 | 0 | 100% |
| gemini 3.1 pro + noskills | 11 | 0 | 100% |

All sonnet failures are 300s timeouts (original limit). Retrying 6 at 600s recovered 8/12. Sonnet needs 275-566s per block.

## Skills help opus, hurt sonnet

**Opus with skills** averages +34 lines and +26s per block vs noskills. The extra time is spent reading skills, and the output is richer — more interaction patterns, correct palettes, better accessibility.

**Sonnet with skills is worse than without.** 0 blocks where skills-only passes, 6 blocks where noskills-only passes. Reading 3 SKILL.md files at sonnet speed eats 100+ seconds that could be spent writing. The skills are too long for sonnet's speed budget.

## Skill trigger rates (opus)

Near-perfect: 97%+ of requested skills are read. `brushing` (86%) and `motion` (83%) are occasionally skipped — Claude decides they're not needed or runs out of turns. The CLAUDE.md skill table in the staging dir works well for discovery.

## Sonnet fails on complex skills

0% pass rate with skills for: `brushing`, `canvas-accessibility`, `data-table`, `navigation`, `scales`, `webgl`. These skills have the longest SKILL.md files — more reading time leaves less writing time.

## Noskills baseline is surprisingly good

Opus noskills is 98% (39/40) averaging 344 lines — only 34 fewer than with skills. The models already know D3 well. Skills' value is in judgment calls (palette choice, interaction timing, Canvas thresholds), not basic capability. This is hard to measure from pass/fail alone.

## Gemini is competitive

11/12 pass rate both configs (one timeout on shape-morphing-gallery). Line counts are comparable to opus. Small sample — needs more blocks and audit scoring to compare quality.

## Cost

Opus: ~$0.38/block (one measured, projected ~$40 for full 105). Sonnet passes: not yet measured but expected cheaper per token, offset by longer wall time.

## Implications

**Compressed skills.** Sonnet would benefit from a single-page cheat sheet per skill instead of the full SKILL.md. A `--skill-summary` flag or pre-compressed format could cut skill read time by 60-80%.

**Pre-loaded skills.** Injecting skills into the system prompt (via `--append-system-prompt`) instead of file reads would save turns entirely. Trade-off: larger prompt, no selective reading.

**Audit is the real test.** Pass/fail measures reliability, not quality. Running the audit pipeline (visual-critic, encoding-integrity, stress-test, cognitive-load) on skills-vs-noskills pairs would show whether skills improve the actual visualization quality.

**Timeout should scale with model.** Opus needs ~100s, sonnet ~400s. A `--timeout` flag would be cleaner than one constant. The remaining 19 sonnet failures at 300s would likely mostly pass at 600s.
