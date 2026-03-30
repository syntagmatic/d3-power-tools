# v2 Generation Findings

Observations from v2 block generation and audit runs (2026-03-29/30). 40 blocks tested across 6 configs: opus 4.6 and sonnet 4.6 (each with/without skills), gemini 3.1 pro preview (with/without skills). Audits run with sonnet 4.6 as evaluator across 4 dimensions.

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

11/12 pass rate both configs (one timeout on shape-morphing-gallery). Line counts are comparable to opus.

## Cost

Opus: ~$0.38/block (one measured, projected ~$40 for full 105). Sonnet passes: not yet measured but expected cheaper per token, offset by longer wall time.

## Audit scores

Audits run with sonnet 4.6 as evaluator across 4 inspection tools (visual-critic, encoding-integrity, stress-test, cognitive-load).

| Config | Rendered | Vis Critic | Encoding | Stress | Cognitive | Composite |
|--------|----------|-----------|----------|--------|-----------|-----------|
| opus + skills | 52/61 | 6.6 | 7.4 | 7.0 | 7.3 | **7.04** |
| opus + noskills | 31/39 | 6.5 | 7.4 | 6.8 | 7.3 | 6.98 |
| sonnet + skills | 14/15 | 6.7 | 7.6 | 6.1 | 7.6 | **7.06** |
| sonnet + noskills | 18/21 | 6.4 | 7.6 | 6.4 | 7.4 | 6.93 |
| gemini + skills | 8/11 | 6.6 | 7.5 | 6.4 | 7.5 | **7.01** |
| gemini + noskills | 8/11 | 5.6 | 7.0 | 6.4 | 7.4 | 6.56 |

### Skills consistently improve quality

Skills advantage by model: opus +0.06, sonnet +0.13, gemini +0.45 composite. The effect is consistent but varies in magnitude. Per-block comparison on 27 shared opus blocks: skills win 12, lose 6, tie 9 (threshold ±0.3).

### Biggest impact: visual critic

Skills most improve the visual-critic dimension (design polish, whitespace, typography). Gemini drops from 6.6 to 5.6 without skills — the largest single-dimension swing. This makes sense: skills encode palette choices, small-area chroma boosts, and layout conventions that models don't reliably produce from training alone.

### Sonnet quality matches opus when it completes

Sonnet+skills composite (7.06) slightly exceeds opus+skills (7.04). The problem is purely completion rate (36% vs 100%), not output quality. Sonnet's higher encoding (7.6) and cognitive (7.6) scores suggest it may produce more careful, well-reasoned visualizations when given enough time.

### Stress test is the weak dimension

All configs score lowest on stress-test (6.0-7.0). Common failures: unthrottled brush/mousemove handlers, missing RAF coalescing, stale closures on scale inversion. This is the dimension where skills should help most, and opus+skills (7.0) does lead — but there's room to improve the stress-test patterns in the skills themselves.

## Implications

**Compressed skills.** Sonnet would benefit from a single-page cheat sheet per skill instead of the full SKILL.md. A `--skill-summary` flag or pre-compressed format could cut skill read time by 60-80%. This would address sonnet's timeout problem without sacrificing the quality gains skills provide.

**Pre-loaded skills.** Injecting skills into the system prompt (via `--append-system-prompt`) instead of file reads would save turns entirely. Trade-off: larger prompt, no selective reading.

**Stress-test patterns need strengthening.** The skills should include more explicit interaction robustness patterns: RAF coalescing, debounced brush handlers, transition conflict guards. This is the dimension with the most room to improve.

**Timeout should scale with model.** Opus needs ~100s, sonnet ~400s. A `--timeout` flag would be cleaner than one constant. The remaining sonnet failures at 300s would likely mostly pass at 600s.

**Sonnet is the right auditor model.** It's cheaper than opus and produces calibrated scores. Using sonnet as evaluator and opus as generator is a good division of labor.
