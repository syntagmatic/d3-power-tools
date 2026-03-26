---
name: perceptual-red-team
description: "Audit D3.js visualizations for cognitive overload and perceptual failure modes. Use this skill to 'Red-Team' complex dashboards, linked views, and animations. Flags 'Chart Fatigue', working memory violations, and 'Congruence' breaks where transitions confuse the viewer instead of helping them. Ensures visualizations stay within human cognitive limits (e.g., < 4-7 linked views, < 20 small multiple panels)."
---

# Perceptual Red-Team: Auditing Cognitive Load

A visualization can be technically perfect (no bugs, fast rendering) but fail because it exceeds the viewer's cognitive bandwidth. This skill acts as an adversarial auditor for "Analytical Usability."

## 1. The 'Working Memory' Audit
Humans can typically hold only 4–7 "chunks" of information in working memory simultaneously.
- **Violation:** A dashboard with 8+ independent linked views.
- **Adversarial Check:** "Can a viewer reasonably track a change in Chart A across all other charts without losing focus?"
- **Red-Team Rule:** If view count > 5, suggest **aggregation**, **faceting**, or **progressive disclosure** (show/hide) over simultaneous display.

## 2. Congruence & Animation Fatigue
Animations must follow the **Congruence Principle**: the structure of the transition must match the structure of the data change.
- **Violation:** "Spaghetti Transitions" where 100+ elements move in different directions simultaneously (e.g., a force layout re-heating on every filter).
- **Adversarial Check:** "Does the animation help the viewer maintain 'Object Constancy', or does it just look like a swarm of bees?"
- **Red-Team Rule:** Use **Staged Transitions** (e.g., move X, then move Y) or **Highlight-by-Desaturation** instead of full-canvas movement.

## 3. The 'Spaghetti' vs. 'Matrix' Threshold
Node-link diagrams are the most common perceptual failure in D3.
- **Violation:** A node-link force diagram with > 50 nodes and high edge density (a "hairball").
- **Adversarial Check:** "Can I identify a single community or 'hub' without hovering every node?"
- **Red-Team Rule:** If density is high, force the agent to justify why an **Adjacency Matrix** or **Arc Diagram** wasn't used instead.

## 4. Visual Search Efficiency
- **Violation:** Using 10+ distinct colors for a categorical scale (color-mapping explosion).
- **Adversarial Check:** "How long does it take to find 'Category K' in the legend and then locate it in the chart?"
- **Red-Team Rule:** Limit categorical colors to < 8. For high cardinality, use **Interactive Highlighting** (hover one, dim the rest) or **Small Multiples**.

## Perceptual Red-Team Checklist

| Perceptual Trap | Red-Team Trigger | Adversarial Fix |
| :--- | :--- | :--- |
| **Chart Fatigue** | > 5 views on screen | Consolidate or use a 'View Switcher' |
| **Change Blindness** | Instant data swaps without transitions | Add a 250ms-750ms D3 transition |
| **Spaghetti Hairball** | Force layout with > 50 nodes | Switch to Matrix or add Edge Bundling |
| **Color Explosion** | > 8 colors in a palette | Use group-level colors or text labels |
| **Jumpy Scrolly** | Graphic jumps during scroll | Use 'Sticky-Graphic' pattern with interpolation |

## Example Critique

**Generated Design:** A dashboard with a Scatterplot, 4 Histograms, a Heatmap, and a 20-row Data Table, all linked via brushing.

**Perceptual Red-Team Critique:**
> **Violation of Working Memory (Overload):** This dashboard contains 7 active views. Brushing in the scatterplot requires the viewer to monitor 6 other charts simultaneously, which exceeds the ~4-chunk cognitive limit. This will lead to 'Change Blindness' where the viewer misses insights in peripheral charts.
> **Fix:** Group the 4 histograms into a single 'Small Multiples' view with a shared X-axis, or use a dropdown to select which attribute is shown in a single histogram.
