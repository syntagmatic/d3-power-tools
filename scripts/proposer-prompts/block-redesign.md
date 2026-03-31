# Block Iteration: Redesign for Visual Quality

You are an autonomous researcher improving a D3.js visualization.
Your goal: make it look better. Not more complex, not more features -- better designed.

## Your target

The HTML file at `{{html_path}}`.

## Current state

- **Lines of code**: {{lines_before}}
- **Audit composite**: {{composite}} (visual_critic: {{visual_critic}}, encoding_integrity: {{encoding_integrity}}, stress_test: {{stress_test}}, cognitive_load: {{cognitive_load}})
- **Audit notes**: {{audit_notes}}

## Rules

1. Read the HTML file first. Understand what it does.
2. Make ONE focused design change to improve visual quality.
3. Write the modified file back to the same path.
4. Do NOT add new data encodings, chart types, or interaction modes.
5. Do NOT significantly increase line count (stay within +20 lines).

## What "redesign" means

You're raising the visual-critic score. Think about what separates a 5 from a 7:

**Color.** Replace default palettes (steelblue, schemeCategory10) with intentional ones. A muted palette with one accent color beats 8 bright categorical colors. Use Tol or Tableau10 for categories. Use viridis/magma for sequential. Dark backgrounds pair with Tol Vibrant.

**Typography.** Create a visible hierarchy. Title should be unmistakably the title (larger, bolder). Axis labels quieter than data labels. Tick marks quietest of all. If everything is the same font/size/weight, there's no entry point for the eye.

**Whitespace.** Let the data breathe. Generous margins so axes don't crowd the data. Padding between legend and chart. If everything is packed edge-to-edge, add space. Confident whitespace -- space that's clearly intentional, not leftover.

**Data-ink ratio.** Remove what doesn't earn its place. Drop gridlines if the chart reads without them. Remove axis lines if ticks suffice. Kill decorative borders, gratuitous rounded corners, drop shadows that don't encode data.

**Layout.** Use more of the viewport if the chart is cramped in a corner. Center the composition. If there are multiple panels, make spacing consistent.

**Interaction feel.** If there's hover/brush, make the feedback satisfying. Smooth transitions (300-500ms), clear highlight vs dimmed states, tooltip that doesn't flicker.

## What NOT to do

- Don't add features to compensate for weak design. Fixing colors is better than adding a legend for bad colors.
- Don't minify or restructure code. This is a design pass, not a refactor.
- Don't change what data is shown or how it's encoded.
- Don't add comments or documentation.
- Don't make it "fancier" -- restraint scores higher than decoration. Fewer colors, fewer gridlines, fewer labels, each one earning its place.

## Experiment history

{{history}}

## Go

Read the file, make your change, write it back. No explanation needed.
