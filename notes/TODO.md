# TODO

## Evaluation pipeline

- [ ] Run full audit sweep to populate best-blocks.json
  All 108 blocks across all block-sets. Currently only 8/108 entries. Prerequisite for folder flatten and discriminator training.

- [x] Build discriminator training pipeline
  Done. Ridge regression baseline: R²=0.56 train, CV R²=-0.33 (overfits on 104 samples). Top predictors: brush (-), geo (-), function_count (-), d3_api_count (+). Needs more data to generalize.

- [ ] Validate semantic tag quality (spot-check encoding_density)
  encoding_density heavily concentrated at 2 (64/108 blocks). May be real or sonnet defaulting when uncertain. Spot-check 10 blocks tagged density=2 against code. Re-tag with `--force` if miscalibrated.

- [ ] Replace stress_test and encoding_integrity audits with programmatic checks
  Use structural features to build heuristic auditors (grep for RAF coalescing, debounce, transition conflicts, zero baselines, dual-y, truncated axes). Cuts audit from 4 LLM calls to 2.

## Benchmarking

- [ ] Explore CPU throttling and WebGL support in bench-fps.py
  All blocks hit 60fps in headless Chromium. Try: (1) CDP CPU throttling (4x slowdown), (2) fix WebGL hangs (--use-gl=swiftshader), (3) add bench-fps to iteration loop to catch perf regressions.

## Project structure

- [x] Flatten blocks/ to single dir with archive
  Done. 108 blocks at blocks/{id}.html, 11 old dirs at blocks/archive/. Selected by: 95 highest composite, 8 best-blocks.json, 5 priority. v1-sonnet won 72/108.
