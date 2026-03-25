# Sharpening Pass — Overnight Loop Plan

Increase the density of practical insight in every skill. Replace API documentation with judgment — every line should encode something you can't get from the D3 docs.

## The Loop

For each skill (working from Tier 4 → Tier 3 → Tier 2, skipping Tier 1):

### Step 1: Research

Before touching the skill, search the web for:
- Best practices and common pitfalls for this visualization type
- Perceptual research relevant to the skill (preattentive features, Gestalt principles, etc.)
- Notable examples and critiques from the D3/Observable community or practitioner blogs
- Anti-patterns: real-world cases where this technique was misused and why it failed

Only bring back knowledge that changes what you'd build. No citations for their own sake.

### Step 2: Read the examples

Read every example HTML in `skills/<name>/examples/`. For each one:
- Does it demonstrate a distinct insight, or is it redundant with another example?
- Does it show the skill at its best, or is it a minimal "it works" demo?
- Could two similar examples be merged into one that covers both cases?

If examples are redundant or overlapping, combine them. Update `tests/test.config.json` to reflect merged or removed files. One strong example beats two thin ones.

### Step 3: Diagnose the skill

Read the full SKILL.md. Classify every section as one of:
- **Insight** — judgment, perception, or a failure mode (keep, sharpen)
- **Recipe** — working code with a non-obvious design choice (keep)
- **API docs** — reorganized D3 documentation (cut or compress to a one-liner with a rationale)
- **Boilerplate** — setup code any D3 user would write (cut)

Write the diagnosis to stdout before making changes.

### Step 4: Rewrite the opening

Every skill should open with the problem it solves for the viewer. One or two sentences. Not "Patterns for adding explanatory text" but "A chart without annotation is a chart without an argument."

### Step 5: Add rationales to naked rules

Find rules that say *what* without saying *why*. Add the failure mode or perceptual reason.

Before:
```
Always use `patternUnits="userSpaceOnUse"`.
```

After:
```
Always use `patternUnits="userSpaceOnUse"` — otherwise pattern density
varies with shape size: a large rectangle gets sparse hatching while
a small one gets dense hatching, and the viewer reads density as data.
```

### Step 6: Cut API documentation

If a section is reorganized D3 docs, compress it to the minimum needed for context. A skill should assume the reader can look up `d3.scaleLinear()`. What they can't look up is *when to use log vs symlog* and *why*.

### Step 7: Add "when not to use this"

The hardest judgment call is knowing when a technique is wrong. Each skill should have at least one "don't use this when..." with a concrete reason.

### Step 8: Test and screenshot

Run ONLY the tests for the current skill:
```bash
python3 scripts/test-viz.py --config tests/test.config.json --skill <skill-name>
```

Do NOT run the full test suite. The `--skill` flag filters to just the tests tagged with that skill name.

Screenshot and read the result to verify visual correctness.

## Skill Order

Work bottom-up by tier. The thinnest skills have the most to gain.

### Round 1 — Tier 4 (Useful but thin)
Goal: move each to Tier 3 or merge it.

1. **annotation** — Add editorial judgment: when to annotate, what to annotate, how much is too much. The skill is encyclopedic on leader line geometry but silent on editorial decisions. Add a hierarchy of emphasis.
2. **responsive** — Cut the ResizeObserver tutorial (MDN content). Focus on D3-specific decisions: when viewBox breaks, why margins need to be responsive, what to do when tick labels don't fit at 320px.
3. **small-multiples** — Expand "which scales to share and when." Add: when small multiples beat a single complex chart, how many panels before the viewer loses the comparison, how to order panels.
4. **sparkcharts** — Add: when sparkcharts mislead (y-axis baseline, truncated ranges). Tufte's design principles applied concretely.
5. **data-table** — Decide: merge into canvas-accessibility or deepen. If keeping, add: when a table is better than a chart (exact value lookup, small datasets), alignment and number formatting.

### Round 2 — Tier 3 (Competent reference)
Good foundations, but reads like reorganized docs. Add judgment.

6. **navigation** — When to use geometric vs semantic zoom (not just what they are). When NOT to add zoom (most charts don't need it).
7. **network** — Deepen "which layout for which insight." Adjacency matrix vs node-link is an analytical choice. Add: when a network viz is wrong entirely (>50 nodes with no clear structure).
8. **visual-texture** — Add perceptual ordering (which patterns read as "more" vs "less"). When texture adds noise vs signal.
9. **hierarchy-layouts** — Expand the layout selection decision. Treemap emphasizes leaf sizes. Sunburst emphasizes depth. Pack emphasizes grouping. Tree emphasizes topology. These aren't interchangeable.
10. **hierarchy-interaction** — When expand/collapse hurts (hides context). When zoomable treemap beats static (only with 3+ levels of meaningful detail).
11. **linked-views** — The bitmap crossfilter is the gem. Expand it. Add: coordination pitfalls (feedback loops, update storms), when linking hurts (too many views = cognitive overload).
12. **distributions** — Reframe from stats textbook to visualization guidance. When box plot vs violin (box plots hide bimodality). When histogram beats both (small n). KDE bandwidth as a judgment call with visual consequences.
13. **time-series** — Cut the date parsing tutorial (MDN content). Focus on: horizon charts (when and why), cycle plots (seasonal comparison), streaming architecture. LTTB is a real fidelity vs performance tradeoff.
14. **scales** — Cut the scale type catalog. Focus on: log vs symlog (zeros kill log), band vs point, time gaps (weekends in financial data), responsive tick counts as a design decision.

### Round 3 — Tier 2 (Strong domain knowledge)
Already good. Sharpen, don't expand.

15. **force** — When force layout is the wrong choice (static hierarchy, small graphs). The 5K performance cliff — what to do about it.
16. **shape-morphing** — When morphing misleads (implying continuity between categorically different states). Parametric > resampling > topology as a decision framework.
17. **data-gathering** — The autoType trap is good. Add more data smells — signs your data has problems that will show up as visual bugs.
18. **edge-bundling** — When bundling hides real structure (too much bundling merges distinct paths). The beta parameter as a judgment call.
19. **webgl** — Add: you probably don't need WebGL. Canvas handles 100K points fine. WebGL is for when Canvas is genuinely too slow.

### Round 4 — Meta skills
20. **idiomatic-d3** — Each rule should explain what breaks when you violate it, and when violating it is the right call.
21. **cross-skill-composition** — Each archetype should say what viewer experience it produces, not just what code structure it uses. Abstraction without a viewer is architecture for no one.

## Constraints

- **Don't inflate line counts.** Density means insight per line. If you add 10 lines of judgment, cut 20 lines of API docs.
- **Consolidate examples.** If a skill has 2+ similar examples, merge them. Update test.config.json.
- **Stay D3-focused.** Every insight should connect to a concrete D3 implementation choice.
- **Preserve working code.** Don't change code snippets unless they're wrong.
- **Test after every skill.** Run only that skill's tests. Screenshot them.
- **Log as you go.** Append observations and cross-skill connections to `notes/SHARPENING-LOG.md`. One section per skill.

## Parallelism

Run 3 skills in parallel using worktree-isolated agents. Use `temp/sharpening-queue.json` to coordinate:

```json
{
  "in_progress": ["annotation", "responsive", "small-multiples"],
  "completed": []
}
```

Before starting a skill:
1. Read `temp/sharpening-queue.json`
2. Find the next skill from the ordered list that is NOT in `in_progress` or `completed`
3. Add it to `in_progress` and write the file back
4. Do the work in a worktree-isolated agent
5. When the agent finishes and commits, move the skill from `in_progress` to `completed`

If there are no remaining skills, stop.

## Git Workflow

Each agent works in an isolated worktree. One commit per skill after tests pass.

1. Stage only the files you changed for that skill: SKILL.md, any modified/removed example HTMLs, test.config.json if updated, and `notes/SHARPENING-LOG.md`.
2. Do NOT stage unrelated files, even if they show up in `git status`.
3. Commit message format: `Sharpen <skill-name>: <brief summary>`
4. Do NOT push. Kai will review and push manually.

## Loop Command

```
/loop 25m Sharpen 3 skills in parallel per iteration, working through notes/PHILOSOPHY-PASS.md in order. Read temp/sharpening-queue.json to find which skills are done or in progress. Claim the next 3 unclaimed skills by adding them to in_progress in the queue file. Launch 3 worktree-isolated agents in parallel, one per skill. Each agent follows all eight steps: (1) research the web, (2) read and consolidate examples, (3) diagnose the skill, (4) rewrite opening, (5) add rationales, (6) cut API docs, (7) add "when not to", (8) test and screenshot. Each agent commits when done. After all 3 finish, move them from in_progress to completed in the queue file.
```

## Done When

All 21 items are in `completed` in the queue file. Then update CRITIQUE.md with revised tier rankings. Delete `temp/sharpening-queue.json`.
