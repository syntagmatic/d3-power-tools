# Applying autoresearch to d3-power-tools

Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) is an autonomous AI research system: an agent modifies `train.py`, runs a 5-minute experiment, checks if `val_bpb` improved, keeps or discards, and loops forever. You wake up to ~100 experiments and a better model.

d3-power-tools applies the same pattern to D3 visualizations: propose a code change, audit quality, keep or discard, repeat.

## The loop

```
1. Copy block to git worktree on iterate branch
2. Baseline audit (4 inspection skills → composite score)
3. Propose compaction via claude -p (reads file, makes ONE change, writes it back)
4. Audit the modified block
5. If LOC dropped and composite held (within 0.3): keep
   If quality regressed or code grew: discard, feed regression details to next proposer
6. Log to history.tsv + experiment JSON (with diff, proposer explanation, audit notes, flags)
7. GOTO 3 (until max experiments or 3 consecutive discards)
8. Squash-merge iterate branch to main, clean up worktree
```

## Iteration tracks

| Track | Script | Target | Primary metric | Constraint |
|-------|--------|--------|----------------|------------|
| **Block** | `iterate-block.py` | HTML file | LOC (lower is better) | Composite can't drop > 0.3 |
| **Prompt** | `iterate-prompt.py` | Prompt text | Generation time (seconds) | Must pass structural feature checks |
| **Skill** | (deferred) | SKILL.md | Composite (avg across test blocks) | Generation time can't regress > 20% |

## Usage

```bash
# Compact a block
python3 scripts/iterate-block.py \
  --target 04-bee-swarm-census \
  --block-set v2-claude-opus-4-6 \
  --max-experiments 12 \
  --model sonnet

# Iterate on a prompt
python3 scripts/iterate-prompt.py \
  --target 47-hierarchical-edge-bundling \
  --block-set v2-claude-opus-4-6 \
  --features "d3.cluster|d3.tree" "d3.curveBundle|bundle"
```

## Key design choices

- **Git worktrees** — iterate branch lives in `temp/worktrees/`, main checkout untouched. Safe to run in background while doing other work.
- **Squash-merge** — all experiment commits collapsed into one clean commit on main.
- **Single file** — proposer reads and rewrites one HTML file. Diffs are reviewable.
- **Proposer gets context** — current audit scores with notes, stress test flags, and if the last experiment was discarded, which dimensions regressed and why.
- **Experiment JSONs** — each experiment saves scores, diff, proposer explanation, audit notes, flags, durations. Self-contained record of what happened.
- **TSV log** — append-only, human-readable history across all runs.

## Artifacts

```
evals/iterations/
  index.html          — master list: sparkline charts, score tooltips, expandable diffs
  history.tsv         — append-only experiment log
  {NNN}-block-{id}.json — per-experiment data (scores, diff, proposer, flags, durations)

evals/best-blocks.json — best composite + lines per target (auto-updated on keep)
evals/runs/            — raw audit run output from run-audit-pipeline.py

scripts/
  iterate-block.py     — block compaction loop
  iterate-prompt.py    — prompt optimization loop
  iterate_lib.py       — shared: TSV logging, keep/discard, worktree helpers, index generation
  proposer-prompts/
    block.md           — proposer instructions for block compaction
    prompt.md          — proposer instructions for prompt rewriting
```

## Keep/discard logic

```python
# Block track: optimize LOC, constrain composite
def decide_block(composite_before, composite_after, lines_before, lines_after):
    if composite_after - composite_before < -0.3:
        return "discard"  # quality regression
    if lines_after >= lines_before:
        return "discard"  # didn't get shorter
    return "keep"

# Prompt track: optimize gen time, constrain features
def decide_prompt(time_before, time_after, features_pass):
    if not features_pass:
        return "discard"  # missing required features
    if time_after >= time_before * 0.85:
        return "discard"  # not meaningfully faster
    return "keep"
```

**Convergence:** 3 consecutive discards stops the run (configurable via `--convergence-discards`).

## Results so far (2026-03-30)

| Block | Before | After | Experiments | Keeps | Composite |
|-------|--------|-------|-------------|-------|-----------|
| 13-radial-dendrogram-edge-bundling | 321 | 266 | 5 | 5 | 7.2→7.0 |
| 02-linked-scatterplot-matrix | 344 | 306 | 5 | 3 | 6.6→6.9 |
| hierarchy-bundles | 1012 | 846 | 13 | 11 | 5.2→5.7 |
| 04-bee-swarm-census | 265 | 241 | 6 | 5 | 7.7→7.7 |
| 32-shape-morphing-gallery | 451 | 360 | 12 | 9 | 6.6→6.3 |

## Future enhancements

- **Skill track**: Iterate on SKILL.md to improve audit composites of generated blocks
- **Diminishing returns detector**: Stop when last N keeps average below a threshold
- **Visual regression check**: Pixel-diff or perceptual hash between iterations
- **Batch runner**: Iterate across multiple blocks in sequence overnight
- **Proposer prompt iteration**: The proposer prompt itself could be iterated on
