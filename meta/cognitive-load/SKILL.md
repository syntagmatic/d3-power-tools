---
name: cognitive-load
description: "Audit D3.js visualizations for cognitive overload. Use when the user says 'cognitive load', 'check clarity', 'too complex', or wants to verify a visualization is readable. Checks working memory limits, color overload, network density, animation congruence, small multiples fatigue. Evaluates execution, not chart type — a complex chart done well scores high. Does NOT evaluate design polish or encoding honesty."
---

# Cognitive Load

A visualization can be technically perfect but fail because it exceeds the viewer's cognitive bandwidth. This skill audits whether the viewer can actually extract insights from the visualization without being overwhelmed.

## How to Evaluate

**Screenshot + code review.** Use code to count structural elements (views, categories, nodes, animation targets). Use the screenshot to assess whether the result is actually overwhelming. A 16-cell scatterplot matrix is not inherently a perceptual failure — it depends on whether the cells are readable, the colors are distinguishable, and the layout guides the eye.

**Evaluate execution, not chart type.** Don't penalize a visualization for choosing a complex form. Penalize it if the complexity is unmanaged. A force layout with 80 nodes can be clear if clusters are well-separated and colors are restrained. A bar chart with 3 bars can be confusing if the labels overlap and the colors clash. Judge what the viewer actually sees.

The thresholds below are warning signs, not automatic failures. Exceeding a threshold means "look harder at whether this works" — not "score it low."

## Perceptual Risks

### 1. Cognitive Overload (Working Memory)
Humans hold 4-7 chunks in working memory. Dashboards with many independent linked views can exceed this.

- **Warning sign:** 5+ independent views that all update on every interaction
- **But it depends:** Are the views truly independent, or do they form natural groups? A SPLOM's 16 cells are one conceptual unit, not 16 separate views. A crossfilter with 3 histograms is manageable. A dashboard with 8 unrelated charts is not.
- **What to check in the screenshot:** Can you track a brushing change across all views without losing your place? Does the layout group related views together?

### 2. Animation Congruence
Transitions should help the viewer maintain object constancy, not create visual noise.

- **Warning sign:** 100+ elements moving in different directions simultaneously; force layouts that reheat on every filter
- **But it depends:** Staged transitions (exit → update → enter) can handle large element counts. The question is whether the animation helps you track what changed or just looks like a swarm of bees.
- **What to check in the screenshot:** N/A for static screenshots. Note when a block is animation-heavy and flag that perceptual evaluation is limited without seeing it in motion.

### 3. Network Density (Spaghetti Threshold)
Node-link diagrams are the most common perceptual failure in D3.

- **Warning sign:** Force layout with 50+ nodes and high edge density
- **But it depends:** Are there visible clusters? Does edge bundling or opacity manage the density? Can you identify a hub or community without hovering every node? A 100-node network with clear clusters reads fine. A 30-node network where every node connects to every other is a hairball.
- **What to check in the screenshot:** Can you identify structure (clusters, hubs, paths) at a glance, or does it read as a tangle?

### 4. Color Overload
Too many categorical colors makes visual search slow and error-prone.

- **Warning sign:** 8+ distinct hues in a categorical palette
- **But it depends:** Are all categories visible simultaneously, or does interaction highlight one at a time? Are the colors perceptually distinct? A 12-color legend where you hover to highlight one category at a time is fine. A 12-color scatter with no interaction is not.
- **What to check in the screenshot:** Can you match a legend entry to its marks in under 3 seconds?

### 5. Small Multiples Overload
Too many panels shifts from comparison to lookup.

- **Warning sign:** 20+ panels on screen simultaneously
- **But it depends:** Are the panels small enough that the grid reads as a pattern? Do they share axes so comparison is easy? Sparkline grids can work at 50+. Full charts with independent axes break at 8.
- **What to check in the screenshot:** Can you compare adjacent panels, or do you need to memorize values to compare?

## Reporting Format

For each visualization:

1. **Structural counts:** views, categories, nodes/edges, animation targets (from code)
2. **Screenshot assessment:** Does it actually feel overwhelming? One sentence.
3. **Score:** 1-10. A perceptually clear visualization scores high regardless of complexity. A confusing one scores low regardless of simplicity.
4. **Risks identified:** Specific perceptual risks with enough detail to act on
5. **Note limitations:** Flag when animation/interaction quality can't be assessed from a static screenshot

## Example Critique

**Block: linked-scatterplot-matrix (screenshot reviewed)**

> **Structural counts:** 16 cells (4×4 SPLOM), 3 categories, ~150 points per cell, brush linking across all cells.
> **Screenshot assessment:** Readable. The three-color palette separates cleanly, cells are large enough to see point distributions, and the diagonal KDE panels break up the grid.
> **Score: 7** — The 16-cell count is high but the SPLOM is a single conceptual unit with consistent encoding across cells. The viewer compares adjacent cells, not all 16 simultaneously. Color separation is strong enough for the 3-category case. Would break down with more categories or smaller cells.
> **Risks:** At smaller viewport sizes the cells would become too small to read point positions — this is near the minimum viable cell size for a scatter.
