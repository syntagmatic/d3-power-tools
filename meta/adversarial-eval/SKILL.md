---
name: adversarial-eval
description: "Calibrate and evaluate auditing skills (visual-critic, encoding-integrity, interaction-stress-test, etc.) by testing whether they produce honest, consistent scores. Use when tuning an agent's SKILL.md, running blind evaluations, checking inter-rater reliability, or diagnosing score inflation/deflation."
---

# Auditing Skill Evaluation

The auditing skills produce scores, not code. Evaluating them asks a different question than skill-eval: not "does this help Claude write better code?" but "does this agent score visualizations honestly and consistently?"

## Context Contamination

If you tune an agent's SKILL.md using specific examples ("block 3 should score 2-3"), then test it in the same conversation, the scores are meaningless. The model may be reaching for calibration targets in its context rather than applying the SKILL.md criteria independently.

Context is contaminated any time the conversation contains:
- Calibration anchors (target scores for specific blocks)
- Previous audit reports with scores
- Discussion of what's "too generous" or "too harsh"
- The human's rationale for specific scores

**Rule: Calibration and evaluation must happen in separate contexts.** Tune the SKILL.md in one conversation. Test it in a fresh container with no access to calibration data, audit history, or memory files.

## The Calibration Loop

```
collect anchors → write SKILL.md → blind eval in container → compare → revise → re-run blind
```

### Step 1: Collect Calibration Anchors

The human scores a sample of blocks (6-10 spanning the full range). Good anchor sets include:

- At least one block the human considers broken (1-2)
- At least one generic-but-working block (4-5)
- At least one well-designed block (7-8)
- Blocks the human suspects the agent will get wrong (edge cases for the agent's criteria)

Store anchors somewhere the eval agent won't see — in the conversation, or in a file the container prompt explicitly excludes.

### Step 2: Run Blind Eval

Run in a fresh container session. The prompt must:

- Tell the agent to read ONLY its own SKILL.md for criteria
- Specify which blocks to screenshot and evaluate
- Write scores to a specific output file
- **Explicitly forbid** reading notes/, memory files, or previous audit reports

Example container prompt:
```
Read meta/<agent-name>/SKILL.md for your evaluation criteria.
Screenshot and evaluate these blocks: [list].
Write evaluations to notes/<AGENT>-CALIBRATION-TEST.md.
Do NOT read any other files in notes/. Do NOT read any memory files.
Do NOT look at previous audit reports.
```

For agents that evaluate screenshots (like visual-critic), the prompt should instruct the agent to take its own screenshots rather than using cached ones — cached screenshots are fine for production audits, but for calibration you want the agent to do the full workflow.

### Step 3: Compare Blind Scores to Anchors

The agent is well-calibrated if:

- **Accuracy:** scores are within ±1 of anchors for most blocks
- **Rank ordering:** if anchor says A > B, the agent agrees
- **Floor enforcement:** broken blocks (anchor 1-2) don't score above 3
- **Ceiling restraint:** generic blocks (anchor 4-5) don't score above 6

### Step 4: Diagnose Divergence

| Pattern | Likely cause | Fix |
|---------|-------------|-----|
| Inflated across the board | Scoring scale language is too soft | Tighten anchors: "generic but working = 4-5, not 7" |
| Deflated across the board | Agent penalizes missing features rather than evaluating what's there | Reframe criteria around what's present, not what's absent |
| Wrong dimension weighted | Agent scores X when it should prioritize Y | Sharpen scope boundaries, add "does NOT evaluate Z" |
| Correct rank order, wrong absolute values | Scale is shifted but judgment is sound | Adjust scale descriptions, the criteria are working |
| Wrong rank order | Criteria don't capture what matters | Rewrite criteria based on what the human actually values |
| Inconsistent across runs | Criteria are ambiguous | Add concrete examples to the scoring scale |

## Inter-Rater Reliability

An agent that gives different scores on different runs is unreliable. To test:

1. Run the same blind eval **twice** in separate containers
2. Compare the two score sets
3. Scores for the same block differing by more than ±1 across runs means the SKILL.md criteria are too vague

## What Belongs in an Agent's SKILL.md

- **Scoring scale with concrete anchors** — not just "1-10" but what each tier looks and feels like
- **Evaluation procedure** — screenshot first? Read code? Both? In what order?
- **Scope boundaries** — what this agent does NOT evaluate (to avoid overlap with other agents)
- **Reporting format** — structured output so scores are comparable across runs

## What Does NOT Belong in an Agent's SKILL.md

- **Specific block scores** — "block 50 should be a 6" is a test fixture, not a criterion. It belongs in calibration anchors, not the skill.
- **Checklists that encourage box-ticking** — especially for holistic evaluations like visual design. Dimensions are lenses, not checkboxes.
- **Criteria that duplicate other agents** — each agent owns a distinct dimension. Visual critic doesn't score accessibility. Encoding integrity doesn't score typography.
