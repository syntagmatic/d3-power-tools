# TODO

## Evaluation pipeline

- [x] Run full audit sweep to populate best-blocks.json
  Done. 107/107 blocks scored (101-webgl via swiftshader). 525 observations across 143 runs.

- [x] Build discriminator training pipeline
  Done. Ridge regression baseline with feature pruning (top-10). CV R²=0.15 — not yet usable for decision-making.

- [ ] Rethink discriminator approach
  CV R²=0.15 on 105 samples isn't actionable. Needs: (1) more sample diversity — audit same block across multiple block-sets to get feature variation, not just coverage; (2) consider non-linear models once n > 500; (3) dimensional specialization (separate models per audit dimension); (4) early-exit filtering and guided compaction blocked until CV R² is reliably positive.

- [ ] Validate semantic tag quality (spot-check encoding_density)
  encoding_density heavily concentrated at 2 (64/108 blocks). May be real or sonnet defaulting when uncertain. Spot-check 10 blocks tagged density=2 against code. Re-tag with `--force` if miscalibrated.

- [ ] Replace stress_test and encoding_integrity audits with programmatic checks
  Use structural features to build heuristic auditors (grep for RAF coalescing, debounce, transition conflicts, zero baselines, dual-y, truncated axes). Cuts audit from 4 LLM calls to 2.

## Benchmarking

- [ ] Explore CPU throttling and WebGL support in bench-fps.py
  All blocks hit 60fps in headless Chromium. Try: (1) CDP CPU throttling (4x slowdown), (2) fix WebGL hangs (--use-gl=swiftshader), (3) add bench-fps to iteration loop to catch perf regressions.

## Project structure

- [x] Flatten blocks/ to single dir with archive
  Done. 107 blocks at blocks/{id}.html, 11 old dirs at blocks/archive/. Selected by: 95 highest composite, 8 best-blocks.json, 5 priority. v1-sonnet won 72/107.
