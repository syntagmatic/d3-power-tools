---
name: calibrate-tool
description: "Measure and tune skill effectiveness. Use when the user says 'calibrate', 'eval', 'test the skill', or wants to check if a skill improves output. Two modes: content skills (with/without baseline comparison) and auditing skills (blind evaluation against human anchors). Covers diagnosis, eval writing, and iterative improvement."
---

# Calibrate Tool

Measure whether a skill improves Claude's output, diagnose why it doesn't, and fix the right thing. Two modes: content skills (does the skill improve generated code?) and auditing skills (does the auditor score honestly?).

## Content Skills: With/Without Comparison

### The Eval Loop

```
run eval → compare with-skill vs baseline → diagnose → fix → re-run
```

The eval runner at `evals/run-evals.py` sends a prompt through `claude -p` twice — once from the project root (skills loaded) and once from a bare directory (no skills) — then tests the generated HTML and runs structural checks.

```bash
python3 evals/run-evals.py                    # all evals
python3 evals/run-evals.py --id scatter-10k   # one eval
python3 evals/run-evals.py --runs 3           # variance check
```

Results go to `evals/results/<eval-id>/<mode>/output.html`. Read both output files and compare directly — don't rely solely on structural checks.

The verdict: **BETTER** (with-skill uses techniques baseline doesn't), **SAME** (equivalent), or **WORSE** (baseline is better — skill is misleading).

### Diagnosis

When SAME or WORSE, determine which of three things to fix:

1. **Checks too crude.** Both pass the same structural checks, but reading the code reveals with-skill uses better patterns. Fix: add more specific checks, or accept some differences need code review.

2. **Prompt too easy.** The baseline handles it fine because the prompt doesn't trigger the skill's edge-case knowledge. Fix: increase data scale (10K→100K), add interaction requirements, require specific techniques.

3. **Skill doesn't teach the right thing.** With-skill output doesn't use the patterns the skill describes. Causes: skill too long (key patterns buried), teaches concepts without code, description doesn't trigger for this prompt. Fix: restructure — highest-value patterns first, add concrete code snippets, shorten non-contributing sections.

### Writing Evals

Add entries to `evals/eval.config.json`:

```json
{
  "id": "short-kebab-name",
  "prompt": "The exact prompt. End with: The file must work when opened directly in a browser (use CDN imports).",
  "target_skills": ["skill-a", "skill-b"],
  "wait_for": "canvas or svg",
  "structural_checks": { "check_name": "grep pattern" }
}
```

Good eval prompts are specific enough to test, open enough that approach matters, hard enough that the skill's patterns are necessary. Don't name the technique you want — say "make it fast" not "use a quadtree."

### Iterative Improvement

Change one thing per round. Don't change prompt, checks, and skill simultaneously.

```
Round 1: Run → SAME → prompt too easy
Round 2: Harden prompt → BETTER (4/5 vs 1/5)
Round 3: Check the miss → skill doesn't teach it clearly
Round 4: Add code snippet → BETTER (5/5 vs 1/5) → lock in
```

Stop when: with-skill is measurably better, baseline can't match it, `--runs 3` gives consistent results.

## Auditing Skills: Blind Evaluation

The auditing skills (visual-critic, encoding-integrity, stress-test, cognitive-load) produce scores, not code. Calibrating them asks: "does this agent score visualizations honestly and consistently?"

### Context Contamination

If you tune an agent's SKILL.md using specific examples ("block 3 should score 2-3"), then test it in the same conversation, the scores are meaningless. The model reaches for calibration targets in context rather than applying criteria independently.

**Rule: Calibration and evaluation must happen in separate contexts.** Tune in one conversation. Test in a fresh container with no access to calibration data, audit history, or memory files.

### The Calibration Loop

```
collect anchors → write SKILL.md → blind eval in container → compare → revise → re-run blind
```

1. **Collect anchors.** Human scores 6-10 blocks spanning the full range (broken 1-2, generic 4-5, well-designed 7-8, edge cases).

2. **Run blind eval.** Fresh container. Tell the agent to read ONLY its own SKILL.md, screenshot and evaluate specified blocks, write scores to output file. **Explicitly forbid** reading notes/, memory files, or previous reports.

3. **Compare.** Well-calibrated if: scores within ±1 of anchors, rank ordering matches, broken blocks don't score above 3, generic blocks don't score above 6.

4. **Diagnose divergence:**

| Pattern | Cause | Fix |
|---------|-------|-----|
| Inflated across the board | Scale language too soft | Tighten: "generic = 4-5, not 7" |
| Deflated across the board | Penalizes missing features | Reframe around what's present |
| Wrong dimension weighted | Priorities misaligned | Sharpen scope, add "does NOT evaluate Z" |
| Correct rank, wrong absolute | Scale shifted but judgment sound | Adjust scale descriptions |
| Wrong rank order | Criteria miss what matters | Rewrite based on human values |
| Inconsistent across runs | Criteria ambiguous | Add concrete scoring examples |

### Inter-Rater Reliability

Run the same blind eval twice in separate containers. Scores differing by >±1 across runs means the SKILL.md criteria are too vague.

## Common Patterns

**Skill is too long.** 800+ lines and eval shows SAME → model overwhelmed by context. Move 3 most important patterns to top, cut API docs, focus on what to do differently.

**Skill teaches concepts, not code.** "Use a render queue" without showing the pattern → model may not produce it. Add concrete code blocks.

**Baseline already knows it.** D3 APIs the model knows well (treemap, forceSimulation, basic transitions) won't show improvement. Value is in patterns the model wouldn't discover: render queues, color-picking, dirty-flag rendering.

**Checklists encourage box-ticking.** Especially for holistic evaluations (visual-critic). Dimensions are lenses, not checkboxes. Each auditing skill owns a distinct dimension.
