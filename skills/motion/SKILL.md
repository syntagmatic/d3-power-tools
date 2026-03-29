---
name: motion
description: "Build fluid, purposeful D3.js animated transitions. Use this skill whenever the user wants to animate data changes, add enter/update/exit transitions, create staggered animations, build scrollytelling narratives, animate on canvas, or make any D3 visualization transition smoothly between states. Also use when the user mentions animation, tweening, easing, or wants to make a visualization feel alive. For shape morphing (circle↔rect, bar↔pie, arbitrary path morphing), use the shape-morphing skill instead."
---

# Animated Transitions

Build fluid, purposeful D3 transitions that communicate data changes clearly. Covers enter/update/exit, staggering, interruption handling, canvas animation, and scrollytelling.

## Core Principle

Animation should answer: **"What changed?"** If a transition doesn't help the viewer track changes, remove it.

### When Animation Helps (Heer & Robertson 2007)

- **Tracking identity**: viewer sees which elements moved where (object constancy)
- **Revealing causation**: temporal sequence shows this-caused-that
- **Sequential storytelling**: scrollytelling, steppers, guided narratives
- **Aggregation/disaggregation**: seeing how points roll up into summaries

### When to Use Small Multiples Instead

- Viewer needs to **compare** two states precisely -- side-by-side beats sequential
- More than ~4 elements move simultaneously without staggering
- Animation creates **occluded intermediate states** where elements overlap mid-flight
- Users will see the transition **repeatedly** (it becomes annoying fast)

### Duration Guidelines

| Motion type | Duration |
|---|---|
| Simple position change | 300-500ms |
| Complex multi-element transition | ~1000ms total |
| Dwell time between stages | 200-400ms |
| Stagger gap per element | 20-80ms (total stagger < 500ms) |
| Scrollytelling step transition | 400-800ms |

**Congruence Principle**: maintain valid data graphics during transitions. No nonsensical intermediate states -- if bars pass through each other mid-animation, stage the transition instead.

## SVG Transitions

### Enter / Update / Exit with `.join()`

Always use a key function so D3 can track identity:

```js
svg.selectAll("circle")
  .data(data, d => d.id)  // key function -- critical for object constancy
  .join(
    enter => enter.append("circle")
      .attr("r", 0).attr("cx", d => xScale(d.x)).attr("cy", d => yScale(d.y))
      .call(e => e.transition().duration(500).attr("r", d => rScale(d.value))),
    update => update
      .call(u => u.transition().duration(500)
        .attr("cx", d => xScale(d.x)).attr("cy", d => yScale(d.y))
        .attr("r", d => rScale(d.value))),
    exit => exit
      .call(e => e.transition().duration(300).attr("r", 0).remove())
  );
```

## Staggered Animations

**Strategies**: index-based `i * 20` (left-to-right), value-based `(maxVal - d.value) / maxVal * 500` (largest first), spatial `Math.hypot(d.x - cx, d.y - cy) * 2` (ripple from center), random `Math.random() * 300` (organic feel), or group-then-item (exit all, transition layout, enter all).

```js
svg.selectAll("rect").transition().duration(400)
  .delay((d, i) => i * 20)  // 20ms offset per element
  .attr("y", d => yScale(d.value));
```

## Easing Functions

Choose easing based on the semantic of the motion:

```js
.ease(d3.easeCubicOut)      // responsive UI -- fast start, gentle stop
.ease(d3.easeElasticOut.amplitude(1).period(0.4))  // bouncy -- use sparingly
.ease(d3.easeBackOut.overshoot(1.5))   // anticipation -- pulls back first
.ease(d3.easeLinear)        // only for continuous processes (loading, progress)
.ease(d3.easeCubicInOut)    // smooth start and stop -- default, most cases
```

**Rule of thumb**: Out-easing for entrances, in-easing for exits, in-out for position changes.

## Staged Exit, Update, Enter

Run exit first so departing marks clear before remaining marks reposition. Use coordinated delays -- more robust than `transition.end()` promises, which reject on interruption or empty selections:

```js
function render(data) {
  const joined = svg.selectAll(".bar").data(data, d => d.id);
  const exitDur = 300, moveDur = 400, enterDur = 400;
  const moveDelay = joined.exit().empty() ? 0 : exitDur;
  const enterDelay = moveDelay + moveDur;

  joined.join(
    enter => enter.append("rect").attr("class", "bar")
      .attr("y", height).attr("height", 0)
      .call(e => e.transition().delay(enterDelay).duration(enterDur)
        .attr("y", d => yScale(d.value))
        .attr("height", d => height - yScale(d.value))),
    update => update
      .call(u => u.transition().delay(moveDelay).duration(moveDur)
        .attr("x", d => xScale(d.id)).attr("width", xScale.bandwidth())
        .attr("y", d => yScale(d.value))
        .attr("height", d => height - yScale(d.value))),
    exit => exit
      .call(e => e.transition().duration(exitDur)
        .attr("height", 0).attr("y", height).attr("opacity", 0).remove())
  );
}
```

**Interruption safety:** The update handler must assert every visual property that enter or exit animates -- especially `opacity`. If an enter transition is interrupted by a new render, the element moves to update at whatever mid-transition opacity it had.

## Handling Interruptions

When a new transition starts before the old one finishes, D3 interrupts. **Cache targets, not mid-interpolation values.** Reading DOM attributes mid-transition produces jittery restarts. Store intended targets in a Map:

```js
const targets = new Map();
function moveTo(sel, x, y) {
  targets.set(sel.node(), { x, y });
  sel.interrupt().transition().duration(300).attr("x", x).attr("y", y);
}
```

## Canvas Animations

SVG transitions don't work on Canvas. Use `d3.timer` or `requestAnimationFrame`.

### Lerp Animation Loop

```js
function animate(data, targets) {
  const speed = 0.05, current = data.map(d => ({ ...d }));

  d3.timer(() => {
    ctx.clearRect(0, 0, width, height);
    let settled = true;
    current.forEach((d, i) => {
      d.x += (targets[i].x - d.x) * speed;
      d.y += (targets[i].y - d.y) * speed;
      if (Math.abs(targets[i].x - d.x) > 0.5 || Math.abs(targets[i].y - d.y) > 0.5)
        settled = false;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, 2 * Math.PI);
      ctx.fill();
    });
    return settled; // true stops timer
  });
}
```

### Multi-Property State Machine

For complex layout morphs (e.g., Circle Pack to Treemap) where properties change shape (radius vs. width/height), separate three concerns: (1) **Render State** -- Map of current drawn values per node; (2) **Target State** -- desired layout from D3; (3) **Transition Manager** -- builds `d3.interpolateNumber` interpolators per node/property, runs `d3.timer` loop applying `easeCubicInOut(elapsed / duration)`. For shape type switches (circle to rect), flip at `t = 0.5`. Handles interruption gracefully since it reads current render state (possibly mid-flight) as the new source.

**Background tab safety:** `d3.timer` pauses when a tab is hidden. If transitions must complete while hidden, add a `setTimeout(tick, 16)` fallback when `document.hidden` is true.

## Color Transitions

Never interpolate in RGB -- it produces muddy intermediate colors. Use `d3.interpolateLab` (perceptually uniform) or `d3.interpolateHcl` (best for hue rotation). When the data domain changes, transition the color mapping with `attrTween`:

```js
const oldScale = colorScale.copy();
colorScale.domain(newDomain);
selection.transition().duration(600)
  .attrTween("fill", d => d3.interpolateLab(oldScale(d.value), colorScale(d.value)));
```

## Animated Data Storytelling

### Scrollytelling: Sticky-Graphic Pattern

A chart stays fixed (`position: sticky`) while narrative text scrolls past. Each step triggers a D3 transition. Use IntersectionObserver to detect step crossings:

```js
const observer = new IntersectionObserver(
  entries => entries.forEach(e => {
    if (e.isIntersecting) updateChart(states[e.target.dataset.step]);
  }),
  { threshold: 0.5 }
);
document.querySelectorAll(".step").forEach(el => observer.observe(el));
```

**Layout**: graphic container uses `position: sticky; top: 0`, step text scrolls in a sibling column. For step-sequenced annotations, see the **annotation** skill.

### Stepper / Slideshow

Maintain a steps array (`[{ data, layout, title }]`) and an index. On advance, clamp the index and call your D3 transition function with the new step's data and layout.

## View Transitions API

Browser-native cross-fade between DOM states (Baseline 2025). Use for container-level view changes (switching chart types, toggling chart vs. data table), not data-level animation where D3 interpolation produces valid intermediate states.

```js
if (document.startViewTransition) document.startViewTransition(() => renderChart(newData));
else renderChart(newData);
```

**Don't combine with D3 transitions** -- View Transitions animate a snapshot, not the live DOM.

## Choosing an Animation Approach

| Need | Tool |
|---|---|
| Data-driven element animation | D3 `.transition()` |
| Container-level view swap | View Transitions API |
| Scroll-triggered data updates | IntersectionObserver + D3 |
| Canvas animation (500+ elements) | `requestAnimationFrame` loop with state interpolation |
| Complex multi-stage choreography | Coordinated delays (preferred) or `transition.end()` promises |
| Reduced-motion fallback | `prefers-reduced-motion`: instant state change, no interpolation |

## Performance Guidelines

| Elements | Technique | Duration |
|----------|-----------|----------|
| < 100 | SVG transitions | 300-800ms |
| 100-1,000 | SVG with stagger | 400-1000ms, 10-30ms stagger |
| 1,000-10,000 | Canvas + d3.timer | 500-1000ms |
| 10,000+ | Canvas + Web Worker | 500ms, skip frames if needed |

At 60fps you have 16ms per frame. See the **canvas** skill for `createRenderQueue` and frame profiling.

## Accessibility: prefers-reduced-motion

```js
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const safeDur = ms => reducedMotion.matches ? 0 : ms;

selection.transition().duration(safeDur(600)).attr("y", d => yScale(d.value));
```

For canvas animations, skip straight to the final frame. Listen for runtime changes with `reducedMotion.addEventListener("change", ...)` since users can toggle this while the page is open.

## Common Pitfalls

1. **Animating from undefined**: If an element has no initial position, the transition starts from 0,0. Always set initial attributes before transitioning.
2. **Key function returning index**: `(d, i) => i` is the default and means "first element stays first." Use a data ID for object constancy.
3. **Transition name collisions**: Unnamed transitions on the same element interrupt each other. Name them: `.transition("move")`, `.transition("color")`.
4. **Interpolating path strings directly**: `d3.interpolateString` on SVG paths produces garbage when paths have different commands. See the **shape-morphing** skill.
5. **Canvas not clearing**: Forgetting `clearRect` causes trails. Sometimes intentional for effect, but usually a bug.

## References

- [Object Constancy](https://bost.ocks.org/mike/constancy/) -- foundational article on key-based transitions
- [Animated Transitions in Statistical Data Graphics](https://idl.cs.washington.edu/papers/motion/) -- Heer & Robertson (IEEE InfoVis 2007)
- [D3 Easing Functions](https://observablehq.com/@d3/easing) -- visual reference for all `d3-ease` curves
- [Scrollama](https://github.com/russellsamora/scrollama) -- IntersectionObserver-based scrollytelling library
- [View Transitions API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API) -- browser-native view transitions (Baseline 2025)
