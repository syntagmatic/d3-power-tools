Simplify the D3 power-tools skill at `$ARGUMENTS`.

Read the full SKILL.md file, then compress it using these techniques — in order of impact:

## Compression techniques

1. **Strip boilerplate from code examples.** Remove SVG creation, container setup, `role`/`aria-label`, `style("vertical-align", ...)`, option destructuring. Show only the D3 pattern being taught — scales, generators, bindings.

2. **Remove wrapper functions.** Don't wrap every example in `function fooChart(container, data, {...} = {}) { ... }`. Show the D3 code inline. Exception: keep wrapper functions that ARE the pattern (like `patternHatch` or `brokenScale`).

3. **Use terse D3 v7 syntax.** `d3.scaleLinear([domain], [range])` shorthand. Chain `.attr()` calls. Skip intermediate variables when the chain is readable.

4. **Collapse variants.** When multiple chart types share structure (e.g., sparkline variants, hierarchy layouts), show one canonical form in full, then describe each variant's delta in 2-3 lines of code + 1 line of prose. Don't repeat the shared scaffolding.

5. **Deduplicate cross-skill content.** If a pattern is covered thoroughly in another skill, replace with a one-line reference: "See `canvas-rendering` skill for DPR setup." Don't re-explain.

6. **Tighten prose.** Cut sentences that restate what the code shows. One line of context before a code block is usually enough. Remove "Note that..." / "It's important to..." / "You should..." filler.

## What to preserve

- Architecture diagrams (ASCII art flow diagrams)
- Decision tables (scale selection, projection choice, etc.)
- **ALL pitfalls** — never cut or limit the pitfalls list
- References section
- The skill's core teaching: someone should be able to implement any pattern from the compressed version
- Cross-skill `Related:` links at the top

## Process

1. Read the original file and note its line count
2. Apply compression techniques
3. Write the compressed version
4. Report: original lines → compressed lines, compression ratio
5. Immediately run `/check-skill` on the result
