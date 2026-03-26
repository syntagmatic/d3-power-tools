---
name: visual-critic
description: "Review D3.js visualizations for 'taste', visual polish, and technical craft. Use this skill when evaluating the design quality of a chart, checking for accessibility (WCAG), typographic hierarchy, spacing consistency, and 'visual logic'. Implements a 'Critique-and-Fix' loop to push AI-generated visualizations beyond 'generic' defaults toward bespoke, high-quality design."
---

# Visual Critic: Evaluating Taste & Craft

"Taste" in data visualization is the difference between a functional chart and a clear, professional communication. High quality D3 code should go beyond being "bug-free" and demonstrate **Design Intentionality**.

Use this skill to perform "Design Jury" evaluations on D3 output.

## Pillars of Design Evaluation

Break your critique into these four gradable dimensions:

### 1. Visual Logic (Encoding Choice)
Does the visual encoding (color, size, position) match the data type and communication goal?
- **Nominal Data:** Are the colors distinct but not imply an order?
- **Ordinal Data:** Does the color intensity or size follow the rank?
- **Quantitative Data:** Are scales zero-baselined for bar charts? Does the aspect ratio correctly represent the data's rate of change?
- **Signal-to-Noise:** Is there redundant ink? (e.g., unnecessary gridlines, excessive axis ticks).

### 2. Craft & Polish (Technical Execution)
Look for "rookie" AI-generated design patterns:
- **Typographic Hierarchy:** Are labels, titles, and legends distinct in weight or size? Is the font choice readable (sans-serif usually preferred)?
- **Spacing (The 8px Grid):** Is padding consistent? Are margins large enough to prevent axis label clipping?
- **Anti-Pattern (Generic Defaults):** Does it use standard "SteelBlue" and default fonts? High-quality D3 should use a deliberate color palette.
- **Micro-Interactions:** Does the hover state provide visual feedback (e.g., color shift, stroke-width change)?

### 3. Visual Accessibility (A11y)
D3 charts are often "opaque" to assistive technology.
- **Color Contrast:** Does the color palette pass WCAG AA (4.5:1 for text, 3:1 for graphical elements)?
- **Keyboard Nav:** Can you tab through elements or use the arrow keys to explore data?
- **ARIA:** Are `aria-label` or `title` tags present on critical elements? Does the SVG have a `<title>` and `<desc>`?
- **Redundancy:** Is color the *only* way to distinguish data? (Use texture, symbols, or labels as a secondary signal).

### 4. Cohesion & Identity
Does the visualization feel like a single, unified system?
- **Axis Styling:** Do X and Y axes share the same styling (stroke, tick length)?
- **Tooltip Design:** Is the tooltip consistently styled with the chart's aesthetic?
- **Responsiveness:** Does it use `viewBox` and `preserveAspectRatio` to scale correctly across screen sizes?

## The Critique-and-Fix Loop

When reviewing code, generate a **Polish Report** with specific, actionable instructions for the "Generator" agent:

1.  **Identify the Issue:** "The X-axis labels are overlapping on small screens."
2.  **State the Design Rule:** "Typography should never overlap; readability is paramount."
3.  **Provide the D3 Fix:** "Rotate the labels by 45 degrees or use `d3.axisBottom(x).ticks(5)` to reduce density."

## Visual Critic's Checklist

| Dimension | Critical Check | Pass Signal |
| :--- | :--- | :--- |
| **Hierarchy** | Title & Axis Labels | Title is 1.5x larger and bold |
| **Contrast** | Foreground/Background | All visual encodings have contrast > 3:1 |
| **Grid** | Spacing Consistency | Consistent `margin` object and internal padding |
| **Clutter** | Data-to-Ink Ratio | Minimalist axes; no 'box' around the chart |
| **A11y** | Screen Reader | `<title>` in SVG and `role="graphics-document"` |
| **Polish** | Overlap Check | No overlapping text or visual elements |

## Example Critique

**Generated Code:**
```js
svg.selectAll("text").attr("fill", "#ccc"); // Grey on White background
```

**Visual Critique:**
> **Violation of Accessibility (Contrast):** The color `#ccc` on a white background has a contrast ratio of ~1.6:1, which is below the WCAG AA threshold of 4.5:1. 
> **Fix:** Use a darker shade like `#666` for labels and `#222` for primary text.
