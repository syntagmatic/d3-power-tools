---
name: stress-test
description: "Stress-test D3.js visualization interactions for race conditions, update storms, and stale closures. Use when the user says 'stress test', 'check interactions', 'race conditions', or wants to verify interaction robustness. Flags un-throttled redraws, infinite feedback loops, mid-transition conflicts, and mouse/touch fights."
---

# Stress Test

Interactive D3 visualizations are prone to subtle bugs that only appear during rapid user input. This skill acts as an adversarial auditor for **Interaction Robustness**.

## 1. The 'Update Storm' Audit
- **The Failure:** Brushing in Chart A triggers a full re-render of Charts B, C, and D on every mousemove event (60+ times per second), leading to "jank" and dropped frames.
- **Adversarial Check:** "Does the chart perform expensive DOM mutation or data joins *during* the drag event without debouncing or throttling?"
- **Rule:** Flag any un-throttled re-render in `brush` or `zoom` events. Require the use of `requestAnimationFrame` (RAF) or a "Dirty Flag" pattern.

## 2. Infinite Feedback Loops
- **The Failure:** Chart A updates Chart B, which then triggers an event that updates Chart A again, causing a stack overflow or infinite loop.
- **Adversarial Check:** "Does your event dispatcher include a `source` parameter to prevent a view from updating itself?"
- **Rule:** All cross-view update functions must include a check: `if (event.source === this) return;`.

## 3. Stale Closure Trap
- **The Failure:** An event listener (like `zoom` or `brush`) captures an old version of a D3 scale, so interactions use the wrong coordinates after a data update or window resize.
- **Adversarial Check:** "Does the event listener reference the scale directly from a closure, or does it retrieve the 'current' scale from the selection state?"
- **Rule:** Listeners must always use the most recent scale. For `d3-zoom`, use `event.transform.rescaleX(xScale)` on the *original* scale.

## 4. The 'Handoff' Race Condition
- **The Failure:** A transition is mid-flight when the user starts a new interaction, leading to "jumping" elements or "NaN" attributes.
- **Adversarial Check:** "What happens if a user clicks or brushes *during* a 750ms transition?"
- **Rule:** Use `.interrupt()` on selections before starting a new transition, or use the **TransitionManager** pattern to handle concurrent animations.

## 5. Mouse-Touch Fight
- **The Failure:** Both `mousedown` and `touchstart` events fire, causing a double-trigger or "ghost" interaction.
- **Adversarial Check:** "Does the code handle both mouse and touch events without `event.preventDefault()` or a check for touch support?"
- **Rule:** Use D3's built-in event filtering (e.g., `!event.sourceEvent` checks) to ensure only one input method is processed.

## Interaction Stress-Test Checklist

| Interaction Trap | Red-Team Trigger | Adversarial Fix |
| :--- | :--- | :--- |
| **Update Storm** | > 100 DOM nodes updated per `brush` event | Use `requestAnimationFrame` coalescing |
| **Infinite Loop** | `dispatch` event without `source` parameter | Add `if (source === this) return;` |
| **Stale Scale** | Scale reference inside a static `.on()` call | Retrieve scale from a central state or `this` |
| **Mid-Flight Snap** | No `.interrupt()` call before new transition | Add `.interrupt()` or use `TransitionManager` |
| **Touch Jitter** | `scroll` and `zoom` fighting on mobile | Add `.filter(event => !event.ctrlKey && ...)` |

## Example Critique

**Generated Code:**
```js
brush.on("brush", (event) => {
  const selection = event.selection;
  // Re-rendering the entire histogram on every mousemove
  histogram.update(data.filter(d => x(d.value) > selection[0] && ...));
});
```

**Interaction Stress-Test Critique:**
> **Violation of Interaction Robustness (Update Storm):** This `brush` listener performs a full data filter and re-render on every mousemove. At 60fps, this will cause significant jank as the browser struggles to keep up with DOM mutations.
> **Fix:** Use a 'Dirty Flag' and `requestAnimationFrame` to coalesce updates. Only set `needsUpdate = true` in the brush event, and perform the actual `histogram.update()` inside a `requestAnimationFrame` loop.
