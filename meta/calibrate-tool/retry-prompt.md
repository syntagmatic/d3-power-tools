# Skill Fix — Evaluator Feedback

A separate evaluator agent reviewed this skill and found issues. Your job is to fix ONLY the flagged issues — do not re-sharpen the entire skill.

## Process

1. Read the evaluator's report (provided below or in the evaluation log)
2. Read the current SKILL.md
3. Fix each FAIL criterion with the minimum change needed
4. Run the skill's tests: `python3 scripts/test-viz.py --config tests/test.config.json --skill <name>`
5. Commit: `Fix <skill-name>: address evaluator feedback`

## Rules

- Fix only what the evaluator flagged. Do not refactor, reorganize, or "improve" other sections.
- Keep changes minimal. If the evaluator says "add a rationale to line 45," add a rationale to line 45. Don't rewrite the paragraph.
- If the evaluator's suggestion is wrong or doesn't apply, skip it and note why in your commit message.
- Do not inflate line count. If you add a rationale, you don't need to cut something else to compensate — the sharpening pass already did that.
- Stage only files for this skill. Do not stage unrelated changes.
- Do not push.

## Evaluator report

The evaluator's report for this skill follows. Each FAIL entry has a line reference and suggested fix.
