Audit the D3 power-tools skill at `$ARGUMENTS` for errors introduced by compression.

Read the full SKILL.md file and check for every issue below. Report each finding with the line number and a fix. Then apply all fixes.

## Checks

### 1. Undefined variables in code examples

Scan every code block. For each variable used, verify it is either:
- Defined earlier in the same code block
- Defined in a prior code block in the same section
- A clearly external input (like `data`, `svg`, `width`, `height`, `margin*`)
- A D3 API (`d3.*`)

**Each section's code blocks are independent.** Variables from other sections do NOT carry over — even if a variable like `zx` appears two sections up, it must be redefined if used in a new section's code block.

Common problems from compression:
- Helper variables (`n`, `gap`, `r`, `barW`, `mid`) that were in a removed wrapper function
- Scale variables (`xScale`, `yScale`) referenced but defined in a different section
- Return values from factory functions not stored in a variable

### 2. Dangling function references

Look for any function that is called but not defined in the visible code blocks. Two common patterns:

- **Wrapper removed, call remains:** A function like `fooChart(container, data)` was defined as a wrapper, the wrapper was removed during compression, but another section still calls it by name.
- **Function inlined, old name persists:** A named function was replaced with inline code during compression, but another section still calls the original name. Check every function call site against what's actually defined.

Fix: either inline the function body at the call site, restore the function definition, or replace with equivalent inline code.

### 3. Cryptic one-liners

Tips or techniques compressed to a single mention that wouldn't be clear to a developer who hasn't seen the full version:
- API calls with non-obvious argument patterns (e.g., `d3.bisector((d, i) => i).center`)
- Techniques described by name only without showing HOW (e.g., "use LTTB" without any hint of the algorithm)

These are fine if the skill cross-references where to learn more. Flag only genuinely opaque ones.

### 4. Incorrect URLs or paths

- Data file paths missing CDN prefix (e.g., `"us-atlas@3/..."` should be `"https://cdn.jsdelivr.net/npm/us-atlas@3/..."`)
- Broken Observable/GitHub URLs
- If unsure about a URL, use WebFetch to verify it resolves

### 5. Repeated computation in examples

- Generators or factories called multiple times when the result should be stored (e.g., `tile()` called 4 times instead of `const tiles = tile()`)
- Scales reconstructed unnecessarily

### 6. Code that doesn't match its description

- Prose says "X" but the code block shows "Y"
- Section headers that no longer match their content after compression

## Output format

For each issue found:
```
Line N: [category] description
  Fix: what to change
```

If no issues found, say "Clean — no dangling issues found."

Then apply all fixes to the file.
