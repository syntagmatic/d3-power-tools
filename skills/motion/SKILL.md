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

Staggering helps the eye track individual elements in large groups:

```js
svg.selectAll("rect").transition().duration(400)
  .delay((d, i) => i * 20)  // 20ms offset per element
  .attr("y", d => yScale(d.value))
  .attr("height", d => height - yScale(d.value));
```

**Stagger strategies**: index-based `i * 20` (left-to-right), value-based `(maxVal - d.value) / maxVal * 500` (largest first), spatial `Math.hypot(d.x - cx, d.y - cy) * 2` (ripple from center), random `Math.random() * 300` (organic feel), or group-then-item (exit all, transition layout, enter all).

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

## Chaining and Sequencing

### Sequential Transitions

Chain `.transition()` on a transition to create a sequence:

```js
selection
  .transition().duration(300).attr("opacity", 0)
  .transition().duration(500).attr("transform", "translate(100, 0)").attr("opacity", 1);
```

### Staged Exit, Update, Enter

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

When nothing is entering or exiting, delays collapse to zero so the update plays immediately.

**Interruption safety:** The update handler must assert every visual property that enter or exit animates -- especially `opacity`. If an enter transition (fading from 0 to 1) is interrupted by a new render, the element moves to update at whatever mid-transition opacity it had.

### Handling Interruptions

When a new transition starts before the old one finishes, D3 interrupts. Cancel explicitly when needed:

```js
selection.interrupt()
  .transition().duration(300).attr("x", newValue);
```

**Cache targets, not mid-interpolation values.** Reading DOM attributes mid-transition produces jittery restarts. Store intended targets in a Map:

```js
const targets = new Map();

function moveTo(sel, x, y) {
  targets.set(sel.node(), { x, y });
  sel.interrupt().transition().duration(300).attr("x", x).attr("y", y);
}

function recover(sel) {
  const t = targets.get(sel.node());
  if (t) moveTo(sel, t.x, t.y);
}
```

## Morphing Between Shapes

See the **shape-morphing** skill for comprehensive coverage: parametric interpolation (cornerRadius, arc parameters), arbitrary path morphing via point resampling, and map projection transitions.

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

### FLIP Animation Pattern

Compute First and Last positions, then Invert and Play with precomputed interpolators:

```js
function flipTransition(data, oldLayout, newLayout, duration = 800) {
  const interps = data.map((d, i) => ({
    x: d3.interpolateNumber(oldLayout[i].x, newLayout[i].x),
    y: d3.interpolateNumber(oldLayout[i].y, newLayout[i].y),
    r: d3.interpolateNumber(oldLayout[i].r, newLayout[i].r),
    color: d3.interpolateRgb(oldLayout[i].color, newLayout[i].color),
  }));

  d3.timer((elapsed) => {
    const t = d3.easeCubicInOut(Math.min(1, elapsed / duration));
    ctx.clearRect(0, 0, width, height);
    interps.forEach(interp => {
      ctx.fillStyle = interp.color(t);
      ctx.beginPath();
      ctx.arc(interp.x(t), interp.y(t), interp.r(t), 0, 2 * Math.PI);
      ctx.fill();
    });
    return elapsed >= duration;
  });
}
```

### Multi-Property State Machine

For complex layout morphs (e.g., Circle Pack to Treemap) where properties change shape (radius vs. width/height), separate three concerns:

1. **Render State:** Map of current drawn values per node (`x, y, r, w, h, opacity, shapeType`)
2. **Target State:** Desired layout computed by D3
3. **Transition Manager:** Builds a Map of `d3.interpolateNumber` interpolators per node/property from render state to target, then runs a `d3.timer` loop applying `easeCubicInOut(elapsed / duration)` to all interpolators each frame. For shape type switches (circle to rect), flip at `t = 0.5`.

This pattern handles interruption gracefully -- when a new transition starts, it reads current render state (which may be mid-flight) as the new source.

**Background tab safety:** `d3.timer` pauses when a tab is hidden. If layout transitions must complete while hidden, add a `setTimeout(tick, 16)` fallback when `document.hidden` is true.

## Color Transitions

See the **color** skill for perceptual color space theory (Lab, HCL, OKLCH). Key rule for animation: never interpolate in RGB -- it produces muddy intermediate colors.

```js
d3.interpolateLab("steelblue", "orange")  // perceptually uniform
d3.interpolateHcl("steelblue", "orange")  // best for hue rotation
```

When the data domain changes, transition the color mapping with `attrTween`:

```js
const oldScale = colorScale.copy();
colorScale.domain(newDomain);
selection.transition().duration(600)
  .attrTween("fill", d => d3.interpolateLab(oldScale(d.value), colorScale(d.value)));
```

## Animated Data Storytelling

### Scrollytelling: Sticky-Graphic Pattern

A chart stays fixed (`position: sticky`) while narrative text scrolls past. Each step triggers a D3 transition. Use IntersectionObserver (or scrollama, which wraps it) to detect step crossings:

```js
// scrollama v3+ (IntersectionObserver internally)
scrollama().setup({ step: ".step", offset: 0.5 })
  .onStepEnter(({ index }) => updateChart(states[index]));
```

Without scrollama, raw IntersectionObserver:

```js
const observer = new IntersectionObserver(
  entries => entries.forEach(e => {
    if (e.isIntersecting) updateChart(states[e.target.dataset.step]);
  }),
  { threshold: 0.5 }
);
document.querySelectorAll(".step").forEach(el => observer.observe(el));
```

**Layout**: graphic container uses `position: sticky; top: 0`, step text scrolls in a sibling column. CSS grid or flexbox for the two-column layout.

**Progress-driven interpolation**: scrollama's `progress: true` mode fires events with a 0-1 value you can feed to `d3.interpolate` for smooth continuous animation.

For step-sequenced annotations, see the **annotation** skill.

### CSS Scroll-Driven Animations

CSS `animation-timeline: view()` animates CSS properties based on viewport visibility -- GPU-accelerated, off the main thread. Use for visual polish (fade-in, slide-up) alongside scrollama for D3 data updates. Only animates CSS properties, not SVG attributes or D3 data joins.

```css
.step {
  animation: fade-in linear both;
  animation-timeline: view();
  animation-range: entry 20% entry 80%;
}
@keyframes fade-in { from { opacity: 0.3; } to { opacity: 1; } }
```

### Stepper / Slideshow

For button/keyboard-driven narratives, maintain a steps array (`[{ data, layout, title }]`) and an index. On advance, clamp the index and call your D3 transition function with the new step's data and layout.

## View Transitions API

Browser-native cross-fade between DOM states (Baseline 2025). Use for container-level view changes (switching chart types, toggling chart vs. data table), not data-level animation where D3 interpolation produces valid intermediate states.

```js
if (document.startViewTransition) document.startViewTransition(() => renderChart(newData));
else renderChart(newData);
```

**Don't combine with D3 transitions** -- View Transitions animate a snapshot, not the live DOM. Pick one per update.

## Choosing an Animation Approach

| Need | Tool |
|---|---|
| Data-driven element animation | D3 `.transition()` |
| Container-level view swap | View Transitions API |
| Scroll-triggered data updates | IntersectionObserver / scrollama + D3 |
| Scroll-linked visual polish (opacity, transform) | CSS `animation-timeline: view()` |
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

At 60fps you have 16ms per frame. When animation frames exceed the budget, see the **canvas** skill for the `createRenderQueue` pattern and frame profiling.

## Accessibility: prefers-reduced-motion

Check the media query and skip or zero-out transitions:

```js
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const safeDur = ms => reducedMotion.matches ? 0 : ms;

selection.transition().duration(safeDur(600)).attr("y", d => yScale(d.value));
```

For canvas animations, skip straight to the final frame. Listen for runtime changes with `reducedMotion.addEventListener("change", ...)` since users can toggle this while the page is open.

## Common Pitfalls

1. **Animating from undefined**: If an element has no initial position, the transition starts from 0,0. Always set initial attributes before transitioning.
2. **Key function returning index**: `(d, i) => i` is the default and means "first element stays first." Use a data ID instead so elements track properly across data updates.
3. **Transition name collisions**: Unnamed transitions on the same element interrupt each other. Name them: `.transition("move")`, `.transition("color")`.
4. **Duration too long**: >1 second feels sluggish for UI transitions. Reserve longer durations for storytelling or complex morphs.
5. **Forgetting `.merge()`**: In the old enter/update pattern, new elements don't get update attrs without `.merge()`. The `.join()` pattern avoids this.
6. **Interpolating path strings directly**: `d3.interpolateString` on SVG paths produces garbage when paths have different commands. See the **shape-morphing** skill for the right approaches.
7. **Canvas not clearing**: Forgetting `clearRect` causes trails. Sometimes intentional for effect, but usually a bug.

## References

- [D3 Transition documentation](https://d3js.org/d3-transition) -- API reference for `d3-transition`
- [General Update Pattern](https://observablehq.com/@d3/selection-join) -- canonical enter/update/exit with `.join()`
- [Object Constancy](https://bost.ocks.org/mike/constancy/) -- foundational article on key-based transitions
- [Animated Transitions in Statistical Data Graphics](https://idl.cs.washington.edu/papers/motion/) -- Heer & Robertson (IEEE InfoVis 2007)
- [D3 Easing Functions](https://observablehq.com/@d3/easing) -- visual reference for all `d3-ease` curves
- [Staggered Transitions](https://observablehq.com/@d3/staggered-transitions) -- staggered delay patterns
- [prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) -- MDN reference
- [Scrollama](https://github.com/russellsamora/scrollama) -- IntersectionObserver-based scrollytelling library
- [View Transitions API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API) -- browser-native view transitions (Baseline 2025)
- [CSS Scroll-Driven Animations](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations) -- declarative scroll-linked effects
