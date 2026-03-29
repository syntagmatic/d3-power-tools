# Generate Blocks

A block is a standalone HTML file that demonstrates a visualization worth stopping to look at. Not a demo of an API — a demonstration of *judgment*: which encoding reveals the pattern, which interaction lets the viewer ask the right question, which transition helps them track what changed.

Each block combines 2–4 skills from this repo. The skills contain the judgment calls — read them before building.

## Workflow

Read `blocks/manifest.json`. For each block:

1. **Skip** if `blocks/{version}-{model}/{id}.html` already exists.
2. **Read the skills.** For each skill listed in the block entry, read `skills/{skill}/SKILL.md`. These encode the tradeoffs, failure modes, and perceptual reasoning behind each technique. The block should embody that knowledge, not just use the API. Pay attention to:
   - "When not to use this" — respect the boundaries
   - Pitfall sections — avoid the documented traps
   - Architecture patterns — Canvas+SVG layering, hit detection, state management
   - Interaction patterns — brush semantics, hover timing, transition choreography
3. **Write** `blocks/{version}-{model}/{id}.html` following the prompt and the standards below.
4. **Test**: `python3 scripts/test-viz.py blocks/{version}-{model}/{id}.html --wait-for {wait_for} --out temp/blocks/{id}.png --timeout 15000`
5. **If the test fails**, read the error, fix the HTML, re-test. Up to 2 fix attempts.
6. **Running tally** after each: `[N/42] PASS/FAIL/SKIP — block name`

Work sequentially. A failure on one block doesn't stop the others. Print a summary at the end.

## What Makes a Block Good

A block is not a code sample with a chart on top. It's a small, complete tool for seeing something in data. The difference:

**Weak:** A bar chart that renders 15 countries sorted by GDP.
**Strong:** A bar chart race where the viewer watches China overtake Japan, watches India accelerate, watches the story of 30 years unfold through motion and rank changes — and the animation answers "what changed?" at every frame.

**Weak:** A scatterplot matrix that brushes.
**Strong:** A scatterplot matrix where brushing one panel reveals a cluster that was invisible in any single view — where the linked highlighting is the *reason the chart exists*, not a feature bolted on after rendering works.

The bar is: someone who understands data visualization would find this worth examining.

### Interaction is the point

A static chart is a statement. An interactive chart is a question the viewer can ask. Every block should have interaction that reveals structure the static view hides. Brushing, hover, zoom, drag — these aren't enhancements. They're the reason the visualization exists.

### Data should feel real

Generate synthetic data inline, but make it structurally interesting. Correlations, clusters, outliers, seasonal patterns, skewed distributions. The data should have enough texture that the visualization has something to reveal. Flat random noise makes every chart look the same.

### The skills are the knowledge base

Each SKILL.md encodes hard-won insight about its domain. A block that uses the `force` skill should know that forceCollide needs radius + 1 for padding, that 5K nodes is the performance cliff, that force layout is wrong for trees. A block that uses `color` should use Tol palettes, boost small-area chroma by 20%, and never rely on color alone to encode critical distinctions.

Read the skills. Build with what they teach.

## Technical Standards

### File structure
- `<!DOCTYPE html>`, complete valid HTML document.
- Inline `<style>` and `<script>` — no external files except D3 v7.
- `<script src="https://d3js.org/d3.v7.min.js"></script>`
- Synthetic data generated inline in JS. Never fetch external URLs.
- `<title>` matching the block name.

### D3 patterns
- Margin convention: `const margin = {top, right, bottom, left}`, derive width/height from container minus margins.
- `const`, arrow functions, modern ES6+.
- Canvas for data layers with >500 elements. SVG for axes, labels, interaction overlays. This is a proven pattern — D3 handles data (scales, layouts), Canvas handles pixels.
- Pointer events (`pointermove`, `pointerdown`, `pointerup`), not mouse events.
- `viewBox` for SVG-only responsive. `ResizeObserver` for Canvas/hybrid.
- Quadtree for Canvas hit detection — don't loop through all points on every mousemove.

### Color
- Tol colorblind-safe palettes by default: `["#4477AA","#EE6677","#228833","#CCBB44","#66CCEE","#AA3377","#BBBBBB"]`
- Sequential: `d3.interpolateBlues` or Tol-derived ramps.
- Never rely on color alone — use position, size, texture, or labels as redundant channels.
- For small marks (< 5px), boost chroma ~20% — small areas appear less saturated.

### Interaction quality
- Hover: pointer-events-aware targets, `cursor: pointer`, visible feedback within 50ms.
- Brushing: use D3's brush module. "All selected if none selected" semantics where appropriate.
- Transitions: 300ms for state changes, 750ms for layout morphs. `d3.easeCubicOut` unless there's a reason not to.
- Linked views: coordinate via `d3.dispatch` or shared state object. Debounce if updating is expensive.

### Visual quality
- Must look polished at 1200×800. No overlapping labels, no clipped content.
- Font: `system-ui, -apple-system, sans-serif`. Monospace for numbers: `"SF Mono", Monaco, "Cascadia Code", monospace`.
- White or near-white background (`#fafafa`). Subtle borders. No heavy shadows.
- Axis ticks: readable, not crowded. Responsive tick count based on available space.
- Legends where there are encodings to decode. No legend for single-series charts.
