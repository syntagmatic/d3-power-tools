---
name: choreography
description: "Orchestrate multi-stage transitions and scrollytelling narratives. Use this skill to sequence complex animations using async/await with transition.end(), manage staggered entry/exit effects, and implement 'Sticky Graphic' scroll-driven storytelling. Covers stage management, timing logic, and coordinating multi-element transitions."
---

# Choreography

Transitions (`motion`) describe how a single element changes; choreography describes how an entire scene evolves over time or scroll. The judgment is in the **sequencing**: ensuring the viewer's eye is guided from one state to the next without cognitive overload. A well-choreographed visualization feels like a directed narrative rather than a chaotic update storm.

For atomic transition details (enter/update/exit), see `motion`. For morphing between different geometries, see `shape-morphing`. For coordinating multiple charts, see `coordination`.

## Sequencing Strategies

### 1. Promise-based Sequencing (`async/await`)
The most robust way to handle "Stage 1 → Stage 2 → Stage 3" logic. Use `transition.end()` (D3 v6+) to wait for **all** elements in a selection to finish before starting the next stage.

```js
async function playStory() {
  // Stage 1: Entrance
  await d3.selectAll(".mark")
    .transition().duration(800)
    .attr("opacity", 1)
    .end();

  // Stage 2: Transform
  await d3.selectAll(".mark")
    .transition().duration(1000)
    .attr("x", d => xScale(d.value))
    .end();

  // Stage 3: Annotation
  d3.select(".annotation").transition().style("opacity", 1);
}
```

### 2. Functional Staggering
Guide the eye by animating elements one by one. This prevents the "flash of change" where everything moves at once. Use a functional `delay` based on index or data properties (e.g., staggering by value).

```js
d3.selectAll(".bar")
  .transition()
  .delay((d, i) => i * 50) // Stagger by 50ms per bar
  .duration(500)
  .attr("width", d => xScale(d.value));
```

### 3. The "Stage Manager" Pattern
For complex stories with "Back/Next" controls or scrollytelling, use a centralized index to manage the state of the scene. Each index maps to a "Stage" function that transitions the chart to that specific configuration.

```js
const stages = [
  { name: "intro", fn: showInitialCluster },
  { name: "split", fn: splitByCategory },
  { name: "highlight", fn: highlightOutliers }
];

function goToStage(index) {
  stages[index].fn();
  updateCaptions(stages[index].name);
}
```

## Scrollytelling (Scroll-Driven Choreography)

The industry standard is the **"Sticky Graphic"** pattern. The chart stays fixed (`position: sticky`) while text "steps" scroll past it, triggering transitions.

### 1. The Scrollama Pattern
Use an `IntersectionObserver`-based library (like Scrollama) to detect when a text step enters the viewport. Map the `stepIndex` to your Stage Manager.

```js
const scroller = scrollama();
scroller.setup({ step: ".step", offset: 0.5 })
  .onStepEnter(({ index, direction }) => {
    // direction tells you if the user is scrolling up or down
    goToStage(index);
  });
```

### 2. Transition vs. Progress
- **Step-based (Trigger):** Transitions fire once when a step enters. Best for discrete shifts (e.g., "now look at the 2024 data").
- **Progress-based (Scrub):** Properties (like opacity or rotation) are tied directly to the scroll percentage (`0–1`). Best for continuous changes (e.g., a globe rotating as you scroll).

## Visual Judgment in Choreography

- **The "Eye-Tracking" Rule:** Never move more than 2–3 major groups at once. If you need to move everything, use a shared motion vector (everything moves right) to maintain context.
- **Pacing:** Give the viewer time to "read" the result of a transition (at least 1500ms) before starting the next sequence.
- **Interruptibility:** If the user clicks "Next" while Stage 1 is still animating, D3's default behavior is to kill the active transition and start the new one. This is usually what you want, but ensure your `async` functions handle rejected promises from `transition.end()`.

## Common Pitfalls

- **Update Storms:** Triggering Stage 2 before Stage 1 has finished its data-join logic, leading to "orphaned" elements that don't transition correctly. **Fix:** Use `transition.end()` or a state guard.
- **The "Jump" on Scroll Up:** When a user scrolls backward, they expect the choreography to play in reverse. Ensure your `goToStage` functions are **idempotent**—they should work regardless of which stage the chart was in previously.
- **Z-Index Fighting:** During transitions, elements might overlap in unexpected ways. Use `selection.raise()` or `selection.lower()` at the start of a stage to ensure the "active" elements are on top.
