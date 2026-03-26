---
name: robustness-contract
description: "Define a 'Sprint Contract' for D3.js visualizations to ensure robustness against edge cases and 'The Data of Death'. Use this skill BEFORE implementing a chart to pre-negotiate behavior, specify data validation contracts, and define interaction state-machines. Acts as a 'Red-Team' planning tool to prevent common failure modes like race conditions, memory leaks, and DOM explosions."
---

# Robustness Contract: The 'Data of Death' Defense

A "Sprint Contract" is a pre-negotiated agreement between the user (or the Designer agent) and the Implementation agent. It defines exactly what "success" looks like, particularly for edge cases that typically break AI-generated code.

Use this skill to "Red-Team" a visualization plan before writing any D3 code.

## 1. Defining 'The Data of Death'
Before implementing, define the exact set of "poisoned" inputs the chart **must** handle without crashing or visual corruption:

- **Empty State:** `data = []` (must show a "No Data" message, not an empty SVG).
- **Null/Undefined:** Data points with missing values (e.g., `{x: 10, y: null}`).
- **Outliers:** A single point 1,000x larger than others (must use log scales or clamping).
- **High Cardinality:** $10^6$ data points (must trigger a Canvas/WebGL fallback).
- **Categorical Explosion:** 50 categories for a color scale (must use a grouped approach or a different encoding than color).
- **Nan/Inf:** Data containing `NaN` or `Infinity` (must filter or provide a fallback position).

## 2. Interaction State Machine
Define how interactions transition from one state to another to prevent **Race Conditions**:

- **Brushing + Zooming:** What happens if the user zooms while a brush is active?
- **Debouncing:** High-frequency events (mousewheel, resize) must be debounced to 60fps or less.
- **Concurrent Overlays:** Can a tooltip and a context-menu be open at once?
- **State Handoff:** Does the "Zoom" state reset when the "Data Filter" changes?

## 3. The Resource Budget
Pre-negotiate the performance limits for the visualization:

- **Frame Rate:** Interaction must maintain > 30fps (ideally 60fps).
- **Memory:** No memory leaks during repeated data updates (selection-join cleanup).
- **DOM Size:** Maximum 2,000 SVG elements before switching to Canvas.

## 4. Contract Template (Pre-Implementation)

Before you code, output this contract:

| Requirement | Defense Strategy |
| :--- | :--- |
| **Missing Values** | `data.filter(d => d.value != null)` or `line.defined()` |
| **Outliers** | `d3.scaleLog()` with `clamp(true)` |
| **Scale Change** | Transitions must use key functions `d => d.id` |
| **Performance** | Use `d3.renderQueue()` for datasets > 10K |
| **Accessibility** | All interactive elements get `role="button"` and `tabindex` |

## 5. Adversarial Scenarios to Test

Ask these questions to "Red-Team" the proposed implementation:
1.  "If I click the 'Reset' button 10 times in one second, does the animation queue explode?"
2.  "If all data values are identical (e.g., all 0), do the axes show `NaN`?"
3.  "If the container width is 0px, does the chart throw a `ZeroDivisionError`?"

---

## Example Contract Proposal

**Requirement:** A real-time streaming line chart.

**Robustness Contract:**
> - **Input:** Data may arrive at 100ms intervals.
> - **Defense:** Use `canvas` for the lines; `svg` for axes. 
> - **Edge Case:** If the stream stops, the chart must show "Live: Paused".
> - **Data of Death:** Handle a "spike" value of `Number.MAX_VALUE` without breaking the axis range.
