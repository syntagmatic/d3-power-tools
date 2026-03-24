---
name: simplify-skill
description: "Compress and simplify a D3 power-tools SKILL.md for clarity and token efficiency. Use this skill when the user says 'simplify skill', 'compress skill', 'shorten skill', or wants to reduce a SKILL.md's line count while preserving all teaching value."
---

# Simplify Skill

Simplify the D3 power-tools skill at `$ARGUMENTS`.

Read the full SKILL.md file, then compress it using these techniques — in order of impact:

## Calibrate first

- **Verbose files (600+ lines, wrapper functions, repeated scaffolding):** Apply all 6 techniques aggressively. Target 40-50% reduction.
- **Moderate files (400-600 lines):** Focus on techniques 1-4. Target 20-30% reduction.
- **Already lean files (<400 lines, terse code, no wrappers):** Focus on techniques 4-6 only. Target 10-15% reduction. Don't force compression — an already-tight file compressed further just loses clarity.

## Compression techniques

1. **Strip boilerplate from code examples.** Remove SVG creation, container setup, `role`/`aria-label`, `style("vertical-align", ...)`, option destructuring. Show only the D3 pattern being taught — scales, generators, bindings.

2. **Remove wrapper functions.** Don't wrap every example in `function fooChart(container, data, {...} = {}) { ... }`. Show the D3 code inline. Exception: keep wrapper functions that ARE the pattern (like `patternHatch` or `brokenScale`).

3. **Use terse D3 v7 syntax.** `d3.scaleLinear([domain], [range])` shorthand. Chain `.attr()` calls on one line when ≤3 attrs. Use comma-separated `const` for related variables. Skip intermediate variables when the chain is readable.

4. **Collapse variants.** When multiple chart types share structure (e.g., sparkline variants, hierarchy layouts), show one canonical form in full, then describe each variant's delta in 2-3 lines of code + 1 line of prose. Don't repeat the shared scaffolding.

5. **Deduplicate cross-skill content.** If a pattern is covered thoroughly in another skill, replace with a one-line reference: "See `canvas-rendering` skill for DPR setup." Don't re-explain.

6. **Tighten prose.** Cut sentences that restate what the code shows. One line of context before a code block is usually enough. Remove "Note that..." / "It's important to..." / "You should..." filler.

## What to preserve

- Architecture diagrams (ASCII art flow diagrams)
- Decision tables (scale selection, projection choice, etc.)
- **ALL pitfalls** — never cut or limit the pitfalls list
- References section
- The skill's core teaching: someone should be able to implement any pattern from the compressed version. Never compress a section below the point where a developer could implement the pattern from it alone.
- Cross-skill `Related:` links at the top

## Process

1. Read the original file and note its line count
2. Apply compression techniques
3. Write the compressed version
4. Report: original lines → compressed lines, compression ratio
5. Immediately run `/check-skill` on the result
