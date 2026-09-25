# Choreography

Absorbed from the v2 `choreography` skill. Open when a scene evolves through several stages: stepper stories, scrollytelling, back/next controls.

Transitions describe how one element changes; choreography is the order the scene changes in. The judgment is sequencing: guide the eye from one state to the next without an update storm.

## Sequencing

**Promise stages.** `transition.end()` resolves when every selected element finishes and *rejects* if any is interrupted or cancelled. An empty selection resolves immediately. Wrap chains so a Next click mid-stage doesn't throw an unhandled rejection:

```js
async function playStory() {
  try {
    await d3.selectAll(".mark").transition("story").duration(800).attr("opacity", 1).end();
    await d3.selectAll(".mark").transition("story").duration(1000).attr("x", d => xScale(d.value)).end();
    d3.select(".annotation").transition("story").style("opacity", 1);
  } catch {
    // interrupted by a newer stage; that stage owns the scene now
  }
}
```

**Stagger** by index or a data property (`.delay((d, i) => i * 50)`) so the eye can follow instead of seeing everything flash at once.

**Stage manager.** One index, one array of stage functions. Every stage function is idempotent: it sets the full scene for that stage regardless of which stage came before. That's what makes Back, scroll-up, and jumping to a step work.

```js
const stages = [
  { name: "intro", fn: showInitialCluster },
  { name: "split", fn: splitByCategory },
  { name: "highlight", fn: highlightOutliers },
];
function goToStage(i) {
  stages[i].fn();
  updateCaptions(stages[i].name);
}
```

## Scrollytelling

Sticky graphic: the chart is `position: sticky; top: 0` and the step text scrolls past in a sibling column. Detect steps with IntersectionObserver or Scrollama (built on it):

```js
const observer = new IntersectionObserver(
  entries => entries.forEach(e => { if (e.isIntersecting) goToStage(+e.target.dataset.step); }),
  { threshold: 0.5 }
);
document.querySelectorAll(".step").forEach(el => observer.observe(el));
```

With Scrollama: `scrollama().setup({ step: ".step", offset: 0.5 }).onStepEnter(({ index, direction }) => goToStage(index))`.

| Change | Mode |
|---|---|
| Discrete shift ("now look at 2024") | **Step trigger**: transition fires once on step enter |
| Continuous change (globe rotating, line drawing) | **Progress scrub**: property tied directly to scroll fraction 0-1, no transition |

## Pacing

- Move at most 2-3 major groups at once. If everything must move, give it a shared motion vector (everything shifts right).
- Let the result sit (~1.5s) before the next *narrative* sequence starts on its own. That's reading time, distinct from the 200-400ms dwell between stages of one transition.
- Raise the active elements (`selection.raise()`) at the start of a stage so they're not occluded mid-flight.

## Pitfalls

- **Update storms**: Stage 2 starts before Stage 1's join settles, leaving orphaned elements. Await `end()` or guard with a state flag.
- **Jump on scroll-up**: non-idempotent stage functions assume the previous stage. Make each set its full state.
- **Stale stages**: a delayed transition from the old stage fires after navigation. Give story transitions one name and call `selection.interrupt(name)` before running the new stage.
