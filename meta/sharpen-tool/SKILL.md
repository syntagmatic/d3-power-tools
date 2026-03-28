---
name: sharpen-tool
description: "Compress and simplify a D3 power-tools SKILL.md for clarity and token efficiency. Use this skill when the user says 'sharpen', 'simplify skill', 'compress skill', 'shorten skill', or wants to reduce a SKILL.md's line count while preserving all teaching value."
---

# Simplify Skill

Simplify the D3 power-tools skill at `$ARGUMENTS`.

Read the full SKILL.md, then work through three phases: triage, compress, verify.

## Phase 1 — Triage

Before editing anything, build a section inventory. For each `##` section, note its line count and classify it:

| Classification | Meaning | Action |
|---|---|---|
| **core** | High-frequency pattern, hard to derive | Keep in full |
| **compress** | Valuable but verbose or repetitive | Tighten (Phase 2) |
| **reference** | Covered better in another skill | Replace with one-line cross-skill pointer |
| **cut** | Niche, rarely needed, or derivable from core sections | Remove entirely |

Decision criteria for each section:
- How often does a developer need this pattern? (weekly → core, rarely → cut candidate)
- Is this the *owning* skill for this pattern, or does another skill cover it better?
- Can a developer who understands the core sections derive this one without help?
- Does the section duplicate infrastructure (state management, Worker setup, DOM boilerplate) that appears elsewhere in this file?

**Show the triage table to the user and get approval before proceeding.** This is where the biggest gains come from — cutting or replacing entire sections beats line-level compression.

### Hard constraints — never cut these
- Architecture diagrams (ASCII art flow diagrams)
- Decision tables (scale selection, projection choice, layout flowcharts)
- **All pitfalls** — never cut, shorten, or limit the pitfalls list
- References section
- Cross-skill `Related:` links at the top

### Skill map for cross-references

When classifying sections as "reference," point to the right owner. Consult the project's CLAUDE.md skill listing for the full map. Common ownership boundaries:
- Zoom/pan mechanics → `navigation`
- DPR, resize, container sizing → `responsive`
- Quadtree hit detection, typed arrays → `canvas`
- Color scales, palettes, CVD → `color`
- Brushing, lasso, linked selection → `brushing`
- ARIA, keyboard nav, screen readers → `canvas-accessibility`
- Tooltip positioning, leader lines → `annotation`
- Data loading, reshaping, binning → `data-gathering`
- Enter/update/exit, transitions → `motion`

## Phase 2 — Compress

Apply these techniques to sections classified as "compress," ordered by typical impact:

1. **Collapse variants.** When multiple sub-patterns share structure (filter types, layout variants, chart flavors), show one canonical form in full. Describe each variant's delta in 2-3 lines of code + 1 line of prose. Don't repeat shared scaffolding.

2. **Extract shared infrastructure.** If the same state object, Worker setup, event wiring, or DOM scaffold appears in multiple sections, define it once and reference it. "Uses the state pattern from §Chart↔Table Toggle" beats repeating 15 lines.

3. **Strip code boilerplate.** Remove SVG/container creation, `role`/`aria-label`, style resets, option destructuring. Show only the D3 pattern being taught.

4. **Remove wrapper functions.** Don't wrap examples in `function fooChart(container, data, opts) { ... }` unless the wrapper IS the pattern (like a reusable chart closure).

5. **Tighten prose.** Cut sentences that restate what the code shows. One line of context before a code block is enough. Remove "Note that..." / "It's important to..." filler.

6. **Use terse D3 v7 syntax.** `d3.scaleLinear([0,1], [0,w])` shorthand. Chain ≤3 `.attr()` calls on one line. Comma-separated `const` for related variables.

## Phase 3 — Verify

1. **Coverage diff.** List every implementable pattern from the original. Verify each one is either still present or explicitly referenced to another skill. A developer should be able to implement any pattern from the compressed version alone (or by following one cross-skill pointer).

2. **Run `/check-skill`** on the compressed file to catch undefined variables, dangling function references, and code/prose mismatches.

3. **Eval check (if available).** If `meta/evals/eval.config.json` lists evals targeting this skill, run them before and after compression. If structural check scores drop, the compression cut too deep — restore that section.

4. **Report.** Original lines → compressed lines, compression ratio, and which sections were triaged as reference/cut.
