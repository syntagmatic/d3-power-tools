Audit the D3 power-tools skill at `$ARGUMENTS` for errors introduced by compression.

Read the full SKILL.md file and check for every issue below. Report each finding with the line number and a fix. Then apply all fixes.

## Checks

### 1. Undefined variables in code examples

Scan every code block. For each variable used, verify it is either:
- Defined earlier in the same code block
- Defined in a prior code block in the same section
- A clearly external input (like `data`, `svg`, `width`, `height`, `margin*`)
- A D3 API (`d3.*`)

Common problems from compression:
- Helper variables (`n`, `gap`, `r`, `barW`, `mid`) that were in a removed wrapper function
- Scale variables (`xScale`, `yScale`) referenced but defined in a different section
- Return values from factory functions not stored in a variable

### 2. Dangling function references

Functions that were removed during compression but still called elsewhere:
- `sparkline(this, data)` → the wrapper was removed but embedding examples still call it
- `reset()` → referenced in click handlers but the function body was cut
- Factory functions whose return value is used but the call was removed

Fix: either inline the function body, show the call with a stored result, or replace with the equivalent inline code.

### 3. Cryptic one-liners

Tips or techniques compressed to a single mention that wouldn't be clear to a developer who hasn't seen the full version:
- API calls with non-obvious argument patterns (e.g., `d3.bisector((d, i) => i).center`)
- Techniques described by name only without showing HOW (e.g., "use LTTB" without any hint of the algorithm)

These are fine if the skill cross-references where to learn more. Flag only genuinely opaque ones.

### 4. Incorrect URLs or paths

- Data file paths missing CDN prefix (e.g., `"us-atlas@3/..."` should be `"https://cdn.jsdelivr.net/npm/us-atlas@3/..."`)
- Broken Observable/GitHub URLs

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
