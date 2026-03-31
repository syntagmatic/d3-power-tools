# TODO

## Evaluation pipeline

- [ ] Run full audit sweep to populate best-blocks.json
  All 108 blocks across all block-sets. Currently only 8/108 entries. Prerequisite for folder flatten and discriminator training.

- [ ] Build discriminator training pipeline
  Combine block-tags.json (semantic), block-features.json (structural), and audit scores into training dataset. 24 input features → 4 dimension scores + composite. Start with linear regression or random forest baseline. Use iteration history (~400+ experiments) as additional data.

- [ ] Validate semantic tag quality (spot-check encoding_density)
  encoding_density heavily concentrated at 2 (64/108 blocks). May be real or sonnet defaulting when uncertain. Spot-check 10 blocks tagged density=2 against code. Re-tag with `--force` if miscalibrated.

- [ ] Replace stress_test and encoding_integrity audits with programmatic checks
  Use structural features to build heuristic auditors (grep for RAF coalescing, debounce, transition conflicts, zero baselines, dual-y, truncated axes). Cuts audit from 4 LLM calls to 2.

## Benchmarking

- [ ] Explore CPU throttling and WebGL support in bench-fps.py
  All blocks hit 60fps in headless Chromium. Try: (1) CDP CPU throttling (4x slowdown), (2) fix WebGL hangs (--use-gl=swiftshader), (3) add bench-fps to iteration loop to catch perf regressions.

## Project structure

- [ ] Flatten blocks/ to single dir with archive
  Once best-blocks.json has full coverage: promote best version to blocks/{id}.html, archive old versions to blocks/archive/{block-set}/. Update manifest, scripts, paths. Provenance in block-tags.json.
