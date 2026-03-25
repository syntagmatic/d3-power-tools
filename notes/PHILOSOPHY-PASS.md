# Philosophy Pass — Overnight Loop Plan

Systematically increase the density of insight in every skill by applying the principles from WHY.md. The goal is not to add philosophy to skills — it's to **replace API documentation with judgment**. Every line should earn its place by encoding something you can't get from the D3 docs.

## The Loop

For each skill (working from Tier 4 → Tier 3 → Tier 2, skipping Tier 1):

### Step 1: Research

Before touching the skill, gather outside knowledge. Search the web for:
- Best practices and common pitfalls for this visualization type (e.g. "parallel coordinates best practices", "when to use box plot vs violin")
- Perceptual research relevant to the skill (e.g. preattentive features, change blindness, Gestalt principles as they apply)
- Notable examples and critiques from the D3/Observable community, academic vis papers, or practitioner blogs
- Anti-patterns: real-world examples where this technique was misused and why it failed

Bring back concrete insights that aren't already in the skill. Don't add citations for their own sake — only add knowledge that changes what you'd build.

### Step 2: Read the examples

Read every example HTML in `skills/<name>/examples/`. For each one:
- Does it demonstrate a distinct insight, or is it redundant with another example?
- Does it show the skill at its best, or is it a minimal "it works" demo?
- Could two similar examples be merged into one that covers both cases?

If examples are redundant or overlapping, combine them into a single file that demonstrates both concepts. Update `tests/test.config.json` to reflect any merged or removed files. Less is more — a few strong examples beat many thin ones.

### Step 3: Read and diagnose the skill

Read the full SKILL.md. Classify every section as one of:
- **Insight** — encodes judgment, perception, or a failure mode (keep, sharpen)
- **Recipe** — working code pattern with a non-obvious design choice (keep)
- **API docs** — reorganized D3 documentation (cut or compress to a one-liner with a "why")
- **Boilerplate** — setup code that any competent D3 user would write (cut)

Write the diagnosis to stdout before making changes.

### Step 4: Rewrite the opening

Every skill should open with **why this matters to the viewer** — the perceptual or analytical problem it solves. One or two sentences. Not "Patterns for adding explanatory text" but "A chart without annotation is a chart without an argument."

### Step 5: Add rationales to naked rules

Find rules that say *what* without saying *why*. Add the failure mode or perceptual reason. The format: rule first, then the scar.

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

If a section is just D3 API organized differently, compress it to the minimum needed for context and link to D3 docs. A skill should assume the reader (human or model) can look up `d3.scaleLinear()`. What they can't look up is *when to use log vs symlog* and *why*.

### Step 7: Add "when not to use this" sections

The hardest judgment call is knowing when a technique is wrong. Each skill should have at least one "don't use this when..." with a concrete reason. This is the kind of insight that's invisible in API docs.

### Step 8: Verify and screenshot

After editing, run the test suite for that skill's examples to make sure nothing broke:
```bash
python3 scripts/test-viz.py --config tests/test.config.json --skill <skill-name>
```

Screenshot and read the result to verify visual correctness.

## Skill Order

Work bottom-up by tier. The thinnest skills have the most to gain.

### Round 1 — Tier 4 (Useful but thin)
These need the most work. The goal is to move each to Tier 3 or merge it.

1. **annotation** — Add editorial judgment: when to annotate, what to annotate, how much is too much. The current skill is encyclopedic on leader line geometry but silent on the hard part. Add a "hierarchy of emphasis" framework.
2. **responsive** — Cut the ResizeObserver tutorial (it's MDN content). Focus on the D3-specific decisions: when viewBox breaks, why margins need to be responsive too, what to do when your tick labels don't fit at 320px. Add mobile-specific interaction pitfalls.
3. **small-multiples** — Expand "which scales to share and when" — this is the actual insight. Add: when small multiples beat a single complex chart, how many panels before the viewer loses the comparison, how to order panels for maximum insight.
4. **sparkcharts** — Add Tufte's design principles (data-ink ratio, resolution). Add: when sparkcharts lie (y-axis baseline, truncated ranges). This is a small domain but the pitfalls are real.
5. **data-table** — Decide: merge into canvas-accessibility or deepen. If keeping, add: when a table is better than a chart (exact value lookup, accessibility, small datasets), table design principles (alignment, number formatting, comparison columns).

### Round 2 — Tier 3 (Competent reference)
These have good foundations but read like reorganized docs. Add judgment.

6. **navigation** — When to use geometric vs semantic zoom (not just what they are). Why minimap placement matters. The threshold where zoom becomes disorienting. Add: when NOT to add zoom (most charts don't need it).
7. **network** — Deepen the "which layout for which insight" decision. Adjacency matrix vs node-link is a real analytical choice, not a style choice. Add: when a network viz is the wrong choice entirely (>50 nodes with no clear structure).
8. **visual-texture** — Add perceptual ordering of textures (which patterns read as "more" vs "less"). When texture adds noise vs signal. The accessibility case is strong but the aesthetic case is underargued.
9. **hierarchy-layouts** — Expand the layout selection decision tree. Treemap emphasizes leaf sizes. Sunburst emphasizes depth. Pack emphasizes grouping. Tree emphasizes topology. These aren't interchangeable — the choice is an analytical commitment.
10. **hierarchy-interaction** — Add: when expand/collapse hurts (hides context), when zoomable treemap beats a static one (only when the dataset has 3+ levels with meaningful detail at each). Don't add zoom because you can.
11. **linked-views** — The bitmap crossfilter is the gem. Expand it. Add: coordination pitfalls (feedback loops, update storms), when linking hurts (too many views = cognitive overload). The interaction section of WHY.md applies directly here.
12. **distributions** — Reframe from stats textbook to visualization guidance. When to use a box plot vs violin (box plots hide bimodality). When a histogram beats both (small n). The KDE bandwidth choice is a judgment call with visual consequences — make that vivid.
13. **time-series** — Cut the date parsing tutorial (MDN content). Focus on: horizon charts (when and why), cycle plots (seasonal comparison), the streaming architecture. The LTTB section is good — it's a real judgment call about fidelity vs performance.
14. **scales** — Cut the scale type catalog (D3 docs). Focus on: when to use log vs symlog (zeros kill log), when to use band vs point, the time gap problem (weekends in financial data), responsive tick counts as a design decision not a technical one.

### Round 3 — Tier 2 (Strong domain knowledge)
These are already good. Sharpen, don't expand.

15. **force** — Add: when force layout is the wrong choice (static hierarchy, small graphs). The 5K cliff is good — add the "what to do about it" decision tree.
16. **shape-morphing** — Add: when morphing misleads (implying continuity between categorically different states). The parametric > resampling > topology hierarchy is excellent — ensure it's framed as a decision, not a ranking.
17. **data-gathering** — Add: the autoType trap is good. Add more "data smells" — signs your data has problems that will show up as visual bugs.
18. **edge-bundling** — Add: when bundling hides real structure (too much bundling merges distinct paths). The beta parameter is a judgment call.
19. **webgl** — Add: the honest "you probably don't need WebGL" section. Most people reach for it too early. Canvas handles 100K points fine. WebGL is for when Canvas is genuinely too slow.

### Round 4 — Meta skills
20. **idiomatic-d3** — Frame rules as taste, not law. Each rule should explain what breaks when you violate it, and when violating it is the right call.
21. **cross-skill-composition** — Add the WHY.md warning about architecture for no one. Each archetype should say what viewer experience it produces, not just what code structure it uses.

## Constraints

- **Don't inflate line counts.** Density means insight per line, not more lines. If you add 10 lines of judgment, cut 20 lines of API docs.
- **Consolidate examples.** If a skill has 2+ examples and they're similar, merge them. Update test.config.json. One rich example beats two thin ones.
- **Stay D3-focused.** This is d3-power-tools, not a visualization textbook. Every insight should connect to a concrete D3 implementation choice.
- **Preserve working code.** Don't change code snippets unless they're wrong. The code is the recipe; the prose is the judgment.
- **Test after every skill.** Run the examples. Screenshot them. Don't break things.
- **Commit after each skill.** One skill per commit. Message format: `Sharpen <skill-name>: <what changed>`
- **Log as you go.** Append observations, surprises, cross-skill connections, and open questions to `notes/SHARPENING-LOG.md`. One section per skill. This is the scratchpad for the whole pass — things that don't belong in any single SKILL.md but are worth remembering.

## Loop Command

```
/loop 25m Sharpen one skill per iteration, working through notes/PHILOSOPHY-PASS.md in order. Read the plan first to find which skill is next (check git log for commits matching "Sharpen <name>" to see what's done). Follow all eight steps for that skill: (1) research the web, (2) read and consolidate examples, (3) diagnose the skill, (4) rewrite opening, (5) add rationales, (6) cut API docs, (7) add "when not to", (8) test and screenshot. Commit when done. Move to the next skill in the next iteration.
```

## Done When

All 21 items are committed. Then update CRITIQUE.md with revised tier rankings.
