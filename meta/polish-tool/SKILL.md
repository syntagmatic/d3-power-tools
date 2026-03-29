---
name: polish-tool
description: "Evaluate the visual design quality of D3.js visualizations through holistic judgment, not checklists. Trigger words: 'polish', 'check design', 'visual quality'. Screenshot the output and assess whether it looks crafted or generic. Scores reflect design intentionality: color harmony, typographic hierarchy, whitespace, data-ink ratio, and overall feel. Does NOT evaluate accessibility (ARIA, keyboard nav) — that belongs to separate agents."
---

# Polish Tool

A chart that renders without errors is not a well-designed chart. Most AI-generated visualizations are technically correct but visually generic — default colors, flat typographic hierarchy, cramped layouts, no sense of restraint. This skill evaluates whether a visualization looks *designed*.

The standard is publication-quality work: NYT Graphics, Observable notebooks, Nadieh Bremer, Maarten Lambrechts. Not every chart needs to reach that level, but the score should reflect how close it gets.

## How to Evaluate

**Screenshot first.** Before scoring, render the visualization and look at it. Code review alone cannot catch: elements rendering too small to read, labels overlapping data, colors that clash, layouts that feel cramped, or proportions that are off. If you can't screenshot, say so — a code-only review is incomplete and should be flagged.

Use cached screenshots from `temp/blocks/` when the block HTML hasn't changed (compare file modification times). Screenshots are shared across all auditing skills — don't regenerate what already exists.

**Score holistically.** The dimensions below are lenses, not a checklist. A visualization with perfect typography but clashing colors is not a 7. A visualization with default styling but excellent proportions and restraint might be. Trust your overall impression, then use the dimensions to explain it.

**Note the context.** Not everything is a data visualization. State what the block is trying to be, and evaluate it on those terms. See "Scoring Tech Demos" below.

## Scoring Scale

| Score | Meaning | Example |
|:-----:|---------|---------|
| **1-2** | **Visually broken.** Renders too small to read, elements overlap catastrophically, layout is clearly buggy, missing or garbled content. | A violin plot that's barely visible. A choropleth with broken geometry. |
| **3-4** | **Renders but undesigned.** Default colors (SteelBlue, schemeCategory10), flat typographic hierarchy, no whitespace, everything the same size and weight. It works, but nobody made design choices. | Most first-draft AI-generated charts. |
| **5-6** | **Functional and readable but generic.** The chart communicates its data, spacing is adequate, nothing is broken — but nothing is intentional either. Competent baseline. | A working crossfilter dashboard with adequate margins but no color harmony or typographic craft. |
| **7-8** | **Deliberately designed.** Color harmony, clear typographic hierarchy, confident whitespace, good proportions. Every element feels considered. Interaction feels good. | A linked scatterplot matrix with intentional palette, readable labels, and satisfying brushing. |
| **9-10** | **Publication quality.** Restraint — fewer colors, fewer gridlines, fewer labels — and every remaining element earns its place. Clear visual argument without reading the title. | Work you'd expect from a dedicated graphics desk. |

"Generic but working" is a **5**, not a 7. Be honest, not generous.

## Evaluation Dimensions

### Does it work at its rendered size?
This is the prerequisite — a hard gate, not one factor among many. If the visualization fails here, the score ceiling is 2 regardless of how clever the code is.

**Broken means broken, not bold.** A dark background with data fills that are indistinguishable from the background is not a design choice — it's a bug. A choropleth where states blend into the ocean is broken. A chart where the data encoding is invisible at the rendered size is broken. Do not rationalize visual failures as intentional design. Ask: "can a viewer extract the data this is supposed to show?" If no, score 1-2.

Specific failure modes:
- Elements too small to read or distinguish (violins that look like dashes, labels smaller than 8px)
- Data encoding indistinguishable from background or chrome
- Labels or legends overlapping data they're supposed to annotate
- Layout using a fraction of the viewport while the rest is empty
- Content clipped or overflowing its container

### Color
Not contrast ratios — *harmony and intentionality*. Does the palette feel chosen or default? Do the colors work together? Is there a reason for each color, or did someone just map categories to schemeCategory10? Deliberate use of a muted palette with one accent color shows more design sense than 8 bright categorical colors.

### Layout and Whitespace
Does the data breathe? Are margins generous enough that axes don't crowd the data? Is there negative space, or is everything packed edge-to-edge? Confident whitespace — space that's clearly intentional, not leftover — is a hallmark of polished design.

### Typography
Is there a visual hierarchy? The title should be unmistakably the title. Axis labels should be quieter than data labels. Tick marks should be the quietest of all. If everything is the same font, size, and weight, there's no hierarchy — the eye has no entry point.

### Data-Ink Ratio
Does every visual element earn its place? Gridlines, borders, axis lines, tick marks, legends — each one should justify its existence. A chart with no gridlines that's still readable is better than one with a full grid. Decorative elements (gradients, drop shadows, rounded corners) that don't encode data are noise.

### Feel
Does the interaction feel good? Is the hover feedback satisfying? Does brushing feel responsive? Is the overall impression polished or sloppy? This is subjective and that's fine — "feels good to use" is a real signal of design quality.

## Scoring Tech Demos

Shape morphing galleries, hit-detection demos, performance benchmarks, and interaction prototypes are not data visualizations. Don't score them on axis labels, data-ink ratio, or whether they make a "visual argument." Score them on what they're trying to do.

What matters for a tech demo:
- **Layout and presentation** — is the gallery/grid clean, well-proportioned, consistently spaced?
- **Color coordination** — do the colors across panels/elements feel like a palette, or are they random defaults?
- **Visual clarity** — can you see what the demo is demonstrating? Does the technique read clearly?
- **Interaction quality** — does it feel good to use? Is the feedback satisfying?
- **Polish** — does it feel finished, or like a code sketch?

| Score | For a tech demo |
|:-----:|-----------------|
| **3-4** | It runs, but looks like a code example. Random colors, no layout thought, placeholder feel. |
| **5-6** | Clean layout, the technique is visible, but no design refinement. A competent demo. |
| **7-8** | Polished presentation. Coordinated colors, satisfying interaction, the demo showcases the technique well. Feels finished. |
| **9-10** | Beautiful enough to be an exhibit piece. The presentation elevates the technique. |

A shape morphing gallery with clean cards, varied but harmonious colors, and smooth animations is a 7-8 regardless of whether it has axes. A particle demo that feels delightful to interact with — responsive, visually pleasing, good use of color and density — can score a 6+ even without a legend.

## Reporting Format

For each visualization, output:

1. **Context:** What is this? (data visualization, tech demo, interactive tool, tutorial)
2. **First impression:** One sentence on the overall visual feel from the screenshot
3. **Score:** Single number, 1-10, calibrated to the scale above
4. **What works:** 1-2 specific things done well (if any)
5. **What doesn't:** 1-2 specific issues, with enough detail to act on (e.g., "legend overlaps Alaska" not "layout needs work")

## Example Critique

**Block: stippled-density-map (screenshot reviewed)**

> **Context:** Choropleth with stipple-density encoding — a data visualization.
> **First impression:** Clean cartographic style with an unusual encoding technique, but the legend placement collides with the map geometry.
> **Score: 6** — Intentional technique and restrained palette elevate it above generic, but the legend overlapping Alaska is a concrete layout bug, and the stipple density is hard to compare across non-adjacent regions.
> **What works:** Deliberate choice of stipple over fill creates a print-friendly, distinctive look. Muted land/water contrast keeps focus on the data layer.
> **What doesn't:** Legend directly overlaps Alaska — a layout bug that should floor the "does it work" check. Stipple density comparison across distant regions relies on memory rather than spatial adjacency.
