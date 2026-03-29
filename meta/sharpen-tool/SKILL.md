---
name: sharpen-tool
description: "Audit, compress, and simplify a D3 power-tools SKILL.md. Use this skill when the user says 'sharpen', 'check skill', 'audit skill', 'simplify skill', 'compress skill', or wants to verify/reduce a SKILL.md while preserving all teaching value."
---

# Sharpen Tool

Audit and simplify the D3 power-tools skill at `$ARGUMENTS`.

Read the full SKILL.md, then work through three phases: triage, compress, verify.

## Phase 1 — Triage

Before editing, build a section inventory. For each `##` section, note its line count and classify it:

| Classification | Meaning | Action |
|---|---|---|
| **core** | High-frequency pattern, hard to derive | Keep in full |
| **compress** | Valuable but verbose or repetitive | Tighten (Phase 2) |
| **reference** | Covered better in another skill | Replace with one-line cross-skill pointer |
| **cut** | Niche, rarely needed, or derivable from core sections | Remove entirely |

Decision criteria:
- How often does a developer need this pattern? (weekly → core, rarely → cut candidate)
- Is this the *owning* skill for this pattern, or does another skill cover it better?
- Can a developer who understands the core sections derive this one without help?
- Does the section duplicate infrastructure that appears elsewhere in this file?

**Show the triage table to the user and get approval before proceeding.**

### Hard constraints — never cut these
- Architecture diagrams (ASCII art flow diagrams)
- Decision tables (scale selection, projection choice, layout flowcharts)
- **All pitfalls** — never cut, shorten, or limit the pitfalls list
- References section
- Cross-skill `Related:` links at the top

### Skill map for cross-references

When classifying sections as "reference," point to the right owner. Consult CLAUDE.md for the full map. Common ownership boundaries:
- Zoom/pan → `navigation` · DPR/resize → `responsive` · Quadtree/typed arrays → `canvas`
- Color/palettes/CVD → `color` · Brushing/lasso → `brushing` · ARIA/keyboard → `canvas-accessibility`
- Tooltips/leaders → `annotation` · Data loading/reshape → `data-gathering` · Transitions → `motion`

## Phase 2 — Compress

Apply to sections classified as "compress," ordered by typical impact:

1. **Collapse variants.** Show one canonical form in full. Describe each variant's delta in 2-3 lines of code + 1 line of prose.
2. **Extract shared infrastructure.** Define repeated state/Worker/DOM scaffolding once, reference it elsewhere.
3. **Strip code boilerplate.** Remove SVG/container creation, `role`/`aria-label`, style resets. Show only the D3 pattern.
4. **Remove wrapper functions** unless the wrapper IS the pattern (reusable chart closure).
5. **Tighten prose.** One line of context before a code block is enough. Cut "Note that..." filler.
6. **Use terse D3 v7 syntax.** `d3.scaleLinear([0,1], [0,w])` shorthand. Chain ≤3 `.attr()` on one line.

## Phase 3 — Verify

### Coverage diff

List every implementable pattern from the original. Verify each is still present or explicitly cross-referenced. A developer should be able to implement any pattern from the compressed version alone (or by following one pointer).

### Audit checks

Scan the file for errors introduced by compression:

**Undefined variables.** For each variable in a code block, verify it's defined in the same block, a prior block in the same section, or is a clearly external input (`data`, `svg`, `width`, `height`, `d3.*`). Each section's code blocks are independent — variables from other sections don't carry over. Watch for: helper variables (`n`, `gap`, `r`) from removed wrappers, scale variables referenced across sections, unstored return values.

**Dangling function references.** Functions called but not defined. Two patterns: wrapper removed but call remains; function inlined but old name persists elsewhere. Fix by inlining the body, restoring the definition, or replacing with equivalent code.

**Cryptic one-liners.** API calls with non-obvious argument patterns or techniques described by name only without showing how. Fine if cross-referenced; flag only genuinely opaque ones.

**Incorrect URLs.** Data file paths missing CDN prefix, broken Observable/GitHub links. Use WebFetch to verify if unsure.

**Code/prose mismatch.** Prose says "X" but code shows "Y". Section headers that no longer match content.

For each issue found:
```
Line N: [category] description
  Fix: what to change
```

If no issues: "Clean — no issues found." Then apply all fixes.

### Report

Original lines → compressed lines, compression ratio, sections triaged as reference/cut.
