---
name: skill-eval
description: "Evaluate and improve D3 Power Tools skills by measuring whether they improve Claude's output. Use this skill when the user wants to test a skill's effectiveness, run evals, diagnose why a skill isn't helping, compare with-skill vs baseline output, or iteratively improve a skill's content. Also use when the user says 'eval', 'test the skill', 'is this skill working', 'improve the skill', or 'run the evals'."
---

# Skill Evaluation

Measure whether a skill improves Claude's D3 output, diagnose why it doesn't, and fix the right thing.

## The Eval Loop

```
run eval → compare with-skill vs baseline → diagnose → fix → re-run
```

### Running Evals

The eval runner lives at `meta/evals/run-evals.py`. It sends a prompt through `claude -p` twice — once from the project root (skills loaded) and once from a bare directory (no skills) — then tests the generated HTML with `scripts/test-viz.py` and runs structural checks.

```bash
# Run all evals
python3 meta/evals/run-evals.py

# Run one eval
python3 meta/evals/run-evals.py --id scatter-10k-brush

# Only with-skill or only baseline
python3 meta/evals/run-evals.py --skill-only
python3 meta/evals/run-evals.py --baseline-only

# Multiple runs for variance
python3 meta/evals/run-evals.py --runs 3

# Different model
python3 meta/evals/run-evals.py --model opus
```

Results go to `meta/evals/results/<eval-id>/<mode>/`:
- `output.html` — the generated visualization
- `screenshot.png` — rendered screenshot

### Reading Results

After an eval run, read both output files and compare them directly. Don't rely solely on the structural check scores — read the actual code.

The verdict is one of:
- **BETTER**: with-skill output uses techniques the baseline doesn't
- **SAME**: both outputs are equivalent in quality
- **WORSE**: baseline output is better (rare, indicates skill is misleading)

## Diagnosis

When the verdict is SAME or WORSE, determine which of three things to fix:

### 1. The Checks Are Too Crude

**Symptom:** Both outputs pass the same structural checks, but reading the code reveals the with-skill output uses better patterns.

**Example:** Both match `beginPath` (the structural check), but with-skill batches draws by category while baseline calls `beginPath` per element. The check can't distinguish them.

**Fix:** Add more specific structural checks to `meta/evals/eval.config.json`, or accept that some quality differences require reading the code.

### 2. The Prompt Doesn't Require the Skill's Knowledge

**Symptom:** The baseline handles the prompt fine because it's not hard enough. The skill teaches patterns for edge cases the prompt doesn't trigger.

**Example:** The skill teaches render queues for 50K+ points, but the prompt only asks for 10K which Sonnet handles naively without stuttering.

**Fix:** Make the prompt harder. Add constraints that force the skill's patterns to matter:
- Increase data scale (10K → 100K)
- Add interaction requirements (brush + zoom + hover simultaneously)
- Require specific techniques ("use Canvas with quadtree hit detection")
- Add edge cases ("handle missing values", "support axis inversion")

### 3. The Skill Doesn't Teach the Right Thing

**Symptom:** Reading both outputs shows the with-skill output doesn't use the patterns the skill describes. The skill content isn't reaching the generated code.

**Possible causes:**
- Skill is too long — key patterns buried in 800 lines of context
- Skill teaches concepts but not concrete code patterns
- Skill's description doesn't trigger for this prompt
- The pattern is described but not actionable enough to reproduce

**Fix:** Restructure the skill. Move the highest-value patterns earlier. Add concrete code snippets for the specific techniques that should appear in the output. Shorten sections that aren't contributing.

## The Diagnosis Process

1. **Read both output files** (`meta/evals/results/<id>/with-skill/output.html` and `meta/evals/results/<id>/baseline/output.html`)
2. **List the techniques each uses** — rendering approach (SVG/Canvas/WebGL), interaction pattern, state management, accessibility, performance strategies
3. **Compare against what the target skills teach** — read the relevant SKILL.md files and check which taught patterns appear in each output
4. **Classify the gap** — crude checks, easy prompt, or ineffective skill
5. **Recommend a specific fix** with the file to edit and what to change

### Diagnosis Output Format

```
DIAGNOSIS: scatter-10k-brush (verdict: SAME)

with-skill techniques:
  - Canvas rendering with DPR handling ✓
  - d3.brush on SVG overlay ✓
  - quadtree for hover ✗ (used brute-force loop)
  - batch-by-category rendering ✗ (one beginPath per point)

baseline techniques:
  - Canvas rendering with DPR handling ✓
  - d3.brush on SVG overlay ✓
  - brute-force hover (same as with-skill)
  - unbatched rendering (same as with-skill)

patterns skill teaches but neither output uses:
  - render queue with shuffle (canvas-rendering)
  - spatial grid indexing (brushing-and-selection)

gap type: PROMPT TOO EASY
  The prompt asks for 10K points which both handle without
  advanced techniques. The skill's value shows at 50K+.

recommendation:
  1. Change prompt to 50K points
  2. Add "maintain 60fps during brush interaction" requirement
  3. Add structural check for "d3.shuffle|renderQueue"
```

## Writing New Evals

Add entries to `evals/meta/evals/eval.config.json`. Each eval needs:

```json
{
  "id": "short-kebab-name",
  "prompt": "The exact prompt sent to Claude. Always end with: The file must work when opened directly in a browser (use CDN imports).",
  "target_skills": ["skill-a", "skill-b"],
  "wait_for": "canvas or svg or CSS selector",
  "interactions": ["brush", "hover", "click", "zoom"],
  "structural_checks": {
    "check_name": "pattern to grep for"
  }
}
```

### Good Eval Prompts

- **Specific enough** to produce testable output, **open enough** that the approach matters
- **Hard enough** that the skill's patterns are necessary, not just nice-to-have
- Always include "self-contained HTML file" and "CDN imports" so the output is testable
- Don't name the specific technique you want — that bypasses the skill's influence. Say "make it fast" not "use a quadtree"

### Good Structural Checks

- Check for **techniques**, not **APIs**. `quadtree` is better than `d3.quadtree()` because the model might inline the concept
- Use `|` for OR patterns when there are multiple valid approaches
- Keep checks minimal — 3-6 per eval. Each should represent a meaningful quality signal
- The checks are a quick filter; the real diagnosis comes from reading the code

## Iterative Improvement

After diagnosing, make one change and re-run. Don't change the prompt, checks, and skill simultaneously — you won't know what worked.

### Improvement Cycle

```
Round 1: Run eval → SAME → diagnose → prompt too easy
Round 2: Harden prompt → re-run → BETTER (4/5 vs 1/5)
Round 3: Check the 1 miss → skill doesn't teach it clearly
Round 4: Add code snippet to skill → re-run → BETTER (5/5 vs 1/5)
Round 5: Lock in. Move to next eval.
```

### When to Stop

- The with-skill output is measurably better on checks AND visually better on screenshots
- The baseline can't match it without the skill — the skill is teaching something non-obvious
- Running 3 times with `--runs 3` gives consistent results (not just lucky generation)

### Variance

LLM output is non-deterministic. A single run can be misleading. Use `--runs 3` to check consistency. If results vary wildly between runs, the eval prompt is ambiguous — tighten it.

## Common Patterns

### Skill Is Too Long

If the skill is 800+ lines and the eval shows SAME, the model may be overwhelmed by context. Try:
1. Move the 3 most important patterns to the top of the SKILL.md
2. Cut sections that are API documentation (the model already knows D3 APIs)
3. Focus on **what to do differently** rather than **how the API works**

### Skill Teaches Concepts, Not Code

If the skill says "use a render queue for progressive rendering" but doesn't show the code pattern, the model may not produce it. Add a concrete, copy-pasteable code block.

### Baseline Already Knows It

Some things Sonnet already knows well: d3.treemap, d3.forceSimulation, basic transitions, SVG axes. Skills that only document these APIs won't show improvement. The value is in patterns the model wouldn't discover: render queues, color-picking hit detection, spatial keyboard navigation, dirty-flag layer management.
