# Applying autoresearch to d3-power-tools

Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) is an autonomous AI research system: an agent modifies `train.py`, runs a 5-minute experiment, checks if `val_bpb` improved, keeps or discards, and loops forever. You wake up to ~100 experiments and a better model.

d3-power-tools has all the infrastructure for a similar loop but doesn't close it. We generate blocks, audit them with 4 scoring skills, track results — but there's no automated feedback from scores back into improvement. The pipeline is open-loop.

## The autoresearch pattern

Three files matter:

- **`prepare.py`** — fixed constants, data prep, evaluation metric. Read-only.
- **`train.py`** — the single file the agent edits. Architecture, optimizer, hyperparameters.
- **`program.md`** — agent instructions. The human edits this.

The loop:

```
1. Read current train.py + results history
2. Propose a change
3. git commit
4. uv run train.py > run.log 2>&1  (5 min fixed budget)
5. Extract val_bpb from log
6. If improved: keep commit
   If worse: git reset
7. Log to results.tsv
8. GOTO 1 (never stop, human may be sleeping)
```

Key design choices:
- **Single metric** (`val_bpb`) — deterministic, vocab-size independent
- **Fixed time budget** (5 min) — all experiments directly comparable
- **Single file** — diffs are reviewable, attribution is clear
- **Simplicity criterion** — "0.001 improvement from 20 lines of hacky code? Not worth it. From deleting code? Definitely keep."
- **Git-based state** — commits for keeps, resets for discards, full history
- **TSV results log** — simple, appendable, human-readable
- **Progress chart** — running best over experiments, green dots for keeps, gray for discards
- **Autonomous overnight** — ~12 experiments/hour, ~100 in 8 hours

## Iteration tracks

Three parallel tracks for closing the loop. **Build blocks and prompts first; skills deferred.**

| Track | Target file | Primary metric | Constraint | Cycle time |
|-------|------------|----------------|------------|------------|
| **Block** | The HTML file directly | LOC (lower is better) | Audit composite can't drop > 0.3 | ~3-5 min |
| **Prompt** | Prompt text (in campaign config) | Generation time (seconds) | Must pass structural feature checks | ~5-10 min |
| **Skill** (deferred) | SKILL.md content | Audit composite (avg across test blocks) | Generation time can't regress > 20% | ~15-20 min |

Each track has its own script, proposer prompt, and metric — but shares logging, keep/discard logic, git strategy, and cost tracking via `scripts/iterate_lib.py`.

### Block track

The most natural autoresearch analog. One file, direct modification, low noise.

- Agent reads the HTML, rewrites for compactness/readability, writes it back
- No staging or generation pipeline — direct `claude -p` with proposer prompt
- Metric: LOC reduction while audit composite holds
- Invocation: `claude -p "$(cat scripts/proposer-prompts/block.md)" --allowedTools Read,Write --max-turns 10`

### Prompt track

Iterates on prompt text to minimize generation time while ensuring required features appear.

- Features specified as grep patterns in campaign config (not in manifest.json)
- Constraint gate: all feature patterns must match in generated HTML or automatic discard
- Uses generation pipeline (`generate-blocks-claude.py`) for each experiment

### Skill track (deferred)

Iterates on SKILL.md to improve audit composites of generated blocks.

- Noisy: requires test-set averaging over 4-6 blocks per skill
- Test block selection: TBD (future enhancement)
- Highest noise, longest cycle, most expensive — build after proving the other tracks work

## Architecture decisions

### Scripts

Three iterate scripts + shared module:

- `scripts/iterate-block.py` (~150 lines)
- `scripts/iterate-prompt.py` (~150 lines)
- `scripts/iterate-skill.py` (~150 lines, deferred)
- `scripts/iterate_lib.py` — shared logging, keep/discard, cost tracking, progress HTML

### Proposer prompts

`program.md`-style instruction files, versioned in the repo:

- `scripts/proposer-prompts/block.md`
- `scripts/proposer-prompts/prompt.md`
- `scripts/proposer-prompts/skill.md` (deferred)

The human iterates on these; the agent iterates on the target. Keeps proposer logic reviewable.

### Keep/discard logic

```python
# Block track: optimize LOC, constrain composite
def decide_block(composite_before, composite_after, lines_before, lines_after):
    composite_delta = composite_after - composite_before
    if composite_delta < -0.3:
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

# Skill track (deferred): optimize composite, constrain time
def decide_skill(composite_before, composite_after, lines_before, lines_after):
    delta = composite_after - composite_before
    if delta >= 0.3:
        if lines_after > lines_before * 1.5 and delta < 0.6:
            return "discard"  # improvement not worth complexity
        return "keep"
    if delta > -0.3 and lines_after < lines_before * 0.8:
        return "keep"  # simpler with same quality
    return "discard"
```

### Convergence

- **3 consecutive discards** = converged for this target
- **Per-track cost cap** within budget
- **$80/night total budget** cap across all tracks

### Git strategy

- Branch-and-merge: `iterate/block-{target}`, `iterate/prompt-{target}`
- Iterate scripts create the branch, commit on keep, checkout on discard
- Human reviews and merges to main when satisfied

### Experiment artifacts

Blocks generated during iteration go to `temp/iterate/{track}-{experiment}/`. The `blocks/` directory stays clean — only human-promoted block sets live there.

Requires adding `--block-dir` flag to `run-audit-pipeline.py` (currently hardcodes `blocks/` prefix).

### Campaign config

Sequential execution, config-driven. Lives in `evals/campaigns/`:

```json
{
  "budget_usd": 80,
  "convergence_discards": 3,
  "delay_between_calls_s": 5,
  "model": "sonnet",
  "tracks": [
    {
      "track": "block",
      "target": "47-hierarchical-edge-bundling",
      "block_set": "v2-claude-opus-4-6",
      "max_experiments": 15
    },
    {
      "track": "prompt",
      "target": "47-hierarchical-edge-bundling",
      "features": ["d3.cluster|d3.tree", "d3.curveBundle|bundle", "transition"],
      "max_experiments": 10
    }
  ]
}
```

### Best-of tracking

Three auto-updated JSON files in `evals/`:

- `evals/best-blocks.json`
- `evals/best-prompts.json`
- `evals/best-skills.json` (deferred)

Updated automatically on every "keep" decision. Optional `"promoted": true` flag for human-verified entries.

```json
{
  "47-hierarchical-edge-bundling": {
    "block_set": "v2-claude-opus-4-6",
    "composite": 8.1,
    "lines": 247,
    "scores": {"visual_critic": 8, "encoding_integrity": 9, "stress_test": 7, "cognitive_load": 8},
    "iteration": "exp-12",
    "git_sha": "abc1234"
  }
}
```

## Results tracking

**TSV log** (`evals/iterations/history.tsv`):
```
exp  track    target                           metric  delta  decision  cost   description
1    block    47-hierarchical-edge-bundling     342     0      baseline  0.00   Initial baseline
2    block    47-hierarchical-edge-bundling     298     -44    keep      0.80   Inlined helper functions
3    block    47-hierarchical-edge-bundling     301     +3     discard   0.75   Tried extracting constants
```

**Per-experiment JSON** (`evals/iterations/{exp}-{track}-{target}.json`):
Full audit details, git shas, proposer context.

**Progress visualization** (`evals/iterations/progress.html`):
Running best per target over experiments. Staircase pattern like autoresearch's `progress.png`.

## Infrastructure changes

- **New**: `scripts/iterate-block.py`, `scripts/iterate-prompt.py`, `scripts/iterate_lib.py`
- **New**: `scripts/proposer-prompts/block.md`, `scripts/proposer-prompts/prompt.md`
- **New**: `evals/campaigns/`, `evals/iterations/`, `evals/best-*.json`
- **Modify**: `scripts/run-audit-pipeline.py` — add `--block-dir` flag
- **Unchanged**: `scripts/generate-blocks-claude.py`, `scripts/staging.py`, `scripts/test-viz.py`

## Future enhancements

- **Skill track**: Build after proving block and prompt tracks work
- **Orchestration strategies**: Round-robin, worst-first, or diminishing-returns scheduling (start with sequential)
- **Auto-derive test blocks for skills**: From manifest skill frequency + score distribution
- **Adaptive thresholds**: Based on observed score variance per track
- **Iterating on audit skills**: Meta-optimization of the scoring skills themselves
- **Iterating on staging CLAUDE.md**: Improve skill triggering rate
- **Visual diffing**: Compare screenshots between iterations to catch rendering regressions
- **Holdout validation**: Periodically run full block set to catch overfitting to test set

## Open questions

1. **Is 0.3 the right composite threshold?** Needs empirical validation with first 10 manual experiments.
2. **What does "readability" mean for blocks?** Currently proxied by "composite holds while LOC drops." May need a dedicated readability metric later.
3. **How aggressive should prompt compression be?** Speed vs. specificity tradeoff — shorter prompts generate faster but may miss nuances.
