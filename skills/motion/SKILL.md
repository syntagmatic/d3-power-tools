---
name: motion
description: "Build fluid, purposeful D3.js animated transitions. Use this skill whenever the user wants to animate data changes, add enter/update/exit transitions, create staggered animations, build scrollytelling narratives, animate on canvas, or make any D3 visualization transition smoothly between states. Also use when the user mentions animation, tweening, easing, or wants to make a visualization feel alive. For shape morphing (circle↔rect, bar↔pie, arbitrary path morphing), use the shape-morphing skill instead."
---

# Animated Transitions

Build fluid, purposeful D3 transitions that communicate data changes clearly. Covers enter/update/exit, morphing between chart types, staggering, interruption handling, and canvas animation.

## Core Principle

Animation should answer: **"What changed?"** If a transition doesn't help the viewer track changes, remove it. Gratuitous animation is worse than no animation.

## SVG Transitions (D3 Built-in)

### Enter / Update / Exit with Key Functions

The foundation of D3 animation. Always use a key function so D3 can track identity:

```js
const bars = svg.selectAll("rect")
  .data(data, d => d.id);  // key function — critical

// EXIT: fade out removed elements
bars.exit()
  .transition().duration(400)
  .attr("opacity", 0)
  .attr("width", 0)
  .remove();

// UPDATE: move existing elements
bars.transition().duration(600)
  .attr("x", d => xScale(d.category))
  .attr("y", d => yScale(d.value))
  .attr("height", d => height - yScale(d.value));

// ENTER: grow in new elements
bars.enter().append("rect")
  .attr("x", d => xScale(d.category))
  .attr("y", height)           // start from baseline
  .attr("height", 0)            // start collapsed
  .attr("width", xScale.bandwidth())
  .attr("opacity", 0)
  .transition().duration(600)
  .attr("y", d => yScale(d.value))
  .attr("height", d => height - yScale(d.value))
  .attr("opacity", 1);
```

### The Join Pattern (D3 v7+)

Modern D3 uses `.join()` which handles enter/update/exit in one call:

```js
svg.selectAll("circle")
  .data(data, d => d.id)
  .join(
    enter => enter.append("circle")
      .attr("r", 0)
      .attr("cx", d => xScale(d.x))
      .attr("cy", d => yScale(d.y))
      .call(enter => enter.transition().duration(500)
        .attr("r", d => rScale(d.value))),
    update => update
      .call(update => update.transition().duration(500)
        .attr("cx", d => xScale(d.x))
        .attr("cy", d => yScale(d.y))
        .attr("r", d => rScale(d.value))),
    exit => exit
      .call(exit => exit.transition().duration(300)
        .attr("r", 0)
        .remove())
  );
```

## Staggered Animations

Staggering helps the eye track individual elements in large groups:

```js
bars.transition()
  .duration(400)
  .delay((d, i) => i * 20)  // 20ms offset per element
  .attr("y", d => yScale(d.value))
  .attr("height", d => height - yScale(d.value));
```

### Stagger Strategies

- **Index-based**: `delay((d, i) => i * 20)` — simple left-to-right
- **Value-based**: `delay(d => (maxVal - d.value) / maxVal * 500)` — largest first
- **Spatial**: `delay(d => Math.hypot(d.x - cx, d.y - cy) * 2)` — ripple from center
- **Random**: `delay(() => Math.random() * 300)` — organic feel
- **Group-then-item**: exit all → transition layout → enter all (three-phase)

## Easing Functions

Choose easing based on the semantic of the motion:

```js
// Responsive UI feel — fast start, gentle stop
.ease(d3.easeCubicOut)

// Bouncy/playful — use sparingly
.ease(d3.easeElasticOut.amplitude(1).period(0.4))

// Anticipation — pulls back before moving forward
.ease(d3.easeBackOut.overshoot(1.5))

// Linear — only for continuous processes (loading, progress)
.ease(d3.easeLinear)

// Smooth start and stop — default, good for most cases
.ease(d3.easeCubicInOut)
```

**Rule of thumb**: Out-easing for entrances, in-easing for exits, in-out for position changes.

## Chaining and Sequencing

### Sequential Transitions

```js
selection
  .transition("phase1").duration(300)
    .attr("opacity", 0)
  .transition("phase2").duration(500)
    .attr("transform", "translate(100, 0)")
    .attr("opacity", 1);
```

### Staged Exit → Update → Enter

When adding or removing elements, run exit animations first so departing marks clear out before
remaining marks slide to their new positions, then enter new marks last. This prevents overlap
where marks pass through each other.

The simplest approach is coordinated delays — more robust than `transition.end()` promises,
which reject on interruption or empty selections:

```js
function render(data) {
  const joined = svg.selectAll(".bar").data(data, d => d.id);
  const hasExit = !joined.exit().empty();
  const hasEnter = !joined.enter().empty();

  const exitDur = 300, moveDur = 400, enterDur = 400;
  const moveDelay = hasExit ? exitDur : 0;
  const enterDelay = hasEnter ? moveDelay + moveDur : 0;

  joined.join(
    enter => enter.append("rect").attr("class", "bar")
      .attr("y", height).attr("height", 0)
      .call(e => e.transition().delay(enterDelay).duration(enterDur)
        .attr("y", d => yScale(d.value))
        .attr("height", d => height - yScale(d.value))),
    update => update
      .call(u => u.transition().delay(moveDelay).duration(moveDur)
        .attr("x", d => xScale(d.id))
        .attr("width", xScale.bandwidth())
        .attr("y", d => yScale(d.value))
        .attr("height", d => height - yScale(d.value))),
    exit => exit
      .call(e => e.transition().duration(exitDur)
        .attr("height", 0).attr("y", height).attr("opacity", 0)
        .remove())
  );
}
```

When nothing is entering or exiting (e.g. a value update or sort), the delays collapse to zero
so the update plays immediately with no dead time.

**Interruption safety:** The update handler must assert every visual property that enter or exit
animates — especially `opacity`. If an enter transition (fading from 0→1) is interrupted by
a new render, the element moves to the update selection at whatever mid-transition opacity it
had. Without `.attr("opacity", 1)` in the update handler, it stays semi-transparent.

### Handling Interruptions

When a new transition starts before the old one finishes, D3 interrupts. Handle gracefully:

```js
selection
  .interrupt()  // cancel any in-progress transition
  .transition().duration(300)
  .attr("x", newValue);
```

For elements that might be mid-transition, read the current computed value:

```js
selection.each(function(d) {
  const current = d3.select(this);
  const currentX = parseFloat(current.attr("x"));
  // use currentX as the starting point
});
```

**Interrupted transition recovery tip:** Cache the *target* values, not mid-interpolation values. If a transition is interrupted and you read the current DOM attribute, you get a mid-interpolation snapshot that produces jittery restarts. Instead, store intended targets in a data property or Map:

```js
const targets = new Map();

function moveTo(sel, x, y) {
  targets.set(sel.node(), { x, y });
  sel.interrupt()
    .transition().duration(300)
    .attr("x", x).attr("y", y);
}

// On interruption, restart from wherever DOM is, toward the cached target
function recover(sel) {
  const t = targets.get(sel.node());
  if (t) moveTo(sel, t.x, t.y);
}
```

## Morphing Between Shapes

See the **shape-morphing** skill for comprehensive coverage: parametric interpolation (cornerRadius, arc parameters), arbitrary path morphing via point resampling, and map projection transitions.

## Canvas Animations

SVG transitions don't work on Canvas. Use `d3.timer` or `requestAnimationFrame`:

### Basic Canvas Animation Loop

```js
function animate(data, targets) {
  const speed = 0.05; // interpolation factor per frame

  // current positions (mutable, updated each frame)
  const current = data.map(d => ({ ...d }));

  d3.timer(() => {
    ctx.clearRect(0, 0, width, height);

    let settled = true;
    current.forEach((d, i) => {
      // lerp toward target
      d.x += (targets[i].x - d.x) * speed;
      d.y += (targets[i].y - d.y) * speed;

      if (Math.abs(targets[i].x - d.x) > 0.5) settled = false;
      if (Math.abs(targets[i].y - d.y) > 0.5) settled = false;

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, 2 * Math.PI);
      ctx.fill();
    });

    return settled; // return true to stop timer
  });
}
```

### FLIP Animation Pattern (Canvas)

For layout changes, compute First and Last positions, then Invert and Play:

```js
function flipTransition(data, oldLayout, newLayout, duration = 800) {
  const start = performance.now();

  // precompute interpolators
  const interps = data.map((d, i) => ({
    x: d3.interpolateNumber(oldLayout[i].x, newLayout[i].x),
    y: d3.interpolateNumber(oldLayout[i].y, newLayout[i].y),
    r: d3.interpolateNumber(oldLayout[i].r, newLayout[i].r),
    color: d3.interpolateRgb(oldLayout[i].color, newLayout[i].color),
  }));

  d3.timer((elapsed) => {
    const t = d3.easeCubicInOut(Math.min(1, elapsed / duration));
    ctx.clearRect(0, 0, width, height);

    interps.forEach((interp, i) => {
      ctx.fillStyle = interp.color(t);
      ctx.beginPath();
      ctx.arc(interp.x(t), interp.y(t), interp.r(t), 0, 2 * Math.PI);
      ctx.fill();
    });

    return elapsed >= duration;
  });
}
```

### Multi-Property Canvas Architecture (State Machine)

For complex visualizations that morph between entirely different layouts (e.g., Circle Pack to Treemap), the simple FLIP loop breaks down because properties change shape (radius vs. width/height).

The robust pattern separates Data, Target State, and Render State:

1. **Render State:** A Map holding the *current* drawn values for every node (`x, y, r, w, h, opacity, shapeType`). This is what the Renderer draws.
2. **Target State:** The desired layout computed by D3.
3. **Transition Manager:** A class that orchestrates interpolating from the Render State toward the Target State.

#### The Interpolator Map

Instead of interpolating array elements, create a map of interpolators for every numeric property. This allows graceful interruption:

```js
class TransitionManager {
  startTransition(targets, renderState, duration) {
    this.interpolators = new Map();
    
    for (const [nodeId, target] of targets) {
      const rs = renderState.get(nodeId); // Current mid-flight or rested state
      if (!rs) continue;
      
      const nodeInterps = {};
      // Dynamically create interpolators for all numeric properties
      for (const key of ['x', 'y', 'r', 'w', 'h', 'opacity', 'startAngle', 'endAngle']) {
        if (target[key] !== undefined && rs[key] !== undefined) {
          nodeInterps[key] = d3.interpolateNumber(rs[key], target[key]);
        }
      }
      
      this.interpolators.set(nodeId, {
        props: nodeInterps,
        sourceShape: rs.shapeType,
        targetShape: target.shapeType
      });
    }
    
    this.runLoop(renderState, duration);
  }

  runLoop(renderState, duration) {
    const ease = d3.easeCubicInOut;
    
    d3.timer((elapsed) => {
      const t = Math.min(1, elapsed / duration);
      const easedT = ease(t);
      
      // Update Render State
      for (const [nodeId, data] of this.interpolators) {
        const rs = renderState.get(nodeId);
        
        // Update all numbers
        for (const [key, interp] of Object.entries(data.props)) {
          rs[key] = interp(easedT);
        }
        
        // Handle Shape Morphing logic (e.g., wait until halfway to switch shape type)
        if (data.sourceShape !== data.targetShape) {
           rs.shapeType = easedT < 0.5 ? data.sourceShape : data.targetShape;
        }
      }
      
      triggerRender(); // Tell canvas to draw current renderState
      return t >= 1;
    });
  }
}
```

#### Handling Background Tabs (setTimeout Fallback)

`requestAnimationFrame` and `d3.timer` pause when a browser tab is hidden. If a user clicks a button to change layouts and switches tabs, the transition halts.

To ensure state consistency, implement a timeout fallback:

```js
_scheduleFrame(callback) {
  if (!document.hidden) {
    this._animFrameId = requestAnimationFrame(callback);
    
    // Safety fallback: if rAF doesn't fire within 100ms, switch to timeout
    this._timeoutId = setTimeout(() => {
      if (this.isTransitioning && this.frameCount === 0) {
        this._useTimeoutFallback(callback);
      }
    }, 100);
  } else {
    this._useTimeoutFallback(callback);
  }
}

_useTimeoutFallback(callback) {
  cancelAnimationFrame(this._animFrameId);
  const tick = () => {
    if (!this.isTransitioning) return;
    callback(performance.now());
    if (this.isTransitioning) {
      setTimeout(tick, 16); // Simulate 60fps
    }
  };
  setTimeout(tick, 16);
}
```

## Color Transitions

### Perceptually Uniform Interpolation

Never interpolate in RGB — it produces muddy intermediate colors. Use Lab or HCL:

```js
// Bad: RGB interpolation
d3.interpolateRgb("steelblue", "orange")

// Good: Lab interpolation (perceptually uniform)
d3.interpolateLab("steelblue", "orange")

// Best for hue rotation: HCL
d3.interpolateHcl("steelblue", "orange")
```

### Animating Color Scales

When the data domain changes, transition the color mapping:

```js
const oldScale = colorScale.copy();
colorScale.domain(newDomain);

selection.transition().duration(600)
  .attrTween("fill", function(d) {
    const from = oldScale(d.value);
    const to = colorScale(d.value);
    return d3.interpolateLab(from, to);
  });
```

## Animated Data Storytelling

### Scrollytelling Transitions

Trigger transitions based on scroll position:

```js
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const step = entry.target.dataset.step;
        transitionTo(step);
      }
    });
  },
  { threshold: 0.5 }
);

document.querySelectorAll(".step").forEach(el => observer.observe(el));
```

### Stepper / Slideshow

For presentation-style narratives:

```js
const steps = [
  { data: step1Data, layout: "bar", title: "Overview" },
  { data: step2Data, layout: "scatter", title: "By region" },
  { data: step3Data, layout: "tree", title: "Hierarchy" },
];

let currentStep = 0;

function advance() {
  currentStep = Math.min(currentStep + 1, steps.length - 1);
  const step = steps[currentStep];
  transitionToLayout(step.layout, step.data);
  updateTitle(step.title);
}
```

## Performance Guidelines

| Elements | Technique | Duration |
|----------|-----------|----------|
| < 100 | SVG transitions | 300-800ms |
| 100-1,000 | SVG with stagger | 400-1000ms, 10-30ms stagger |
| 1,000-10,000 | Canvas + d3.timer | 500-1000ms |
| 10,000+ | Canvas + Web Worker | 500ms, skip frames if needed |

### Frame Budget

At 60fps you have 16ms per frame. Canvas draw calls are fast, but complex compositing or filters eat into that budget. When animation frames exceed the budget, use progressive rendering (see the `canvas` skill for the `createRenderQueue` pattern and frame profiling techniques).

## Accessibility: prefers-reduced-motion

Respect users who have reduced-motion enabled at the OS level. Check the media query and shorten or disable transitions:

```js
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function safeDuration(ms) {
  return prefersReducedMotion ? 0 : ms;
}

// Usage
selection.transition()
  .duration(safeDuration(600))
  .attr("y", d => yScale(d.value));
```

For canvas animations with `d3.timer`, skip straight to the final frame:

```js
if (prefersReducedMotion) {
  drawFinalFrame(targets);
} else {
  d3.timer((elapsed) => { /* ... */ });
}
```

Listen for changes at runtime — users can toggle this while the page is open:

```js
window.matchMedia("(prefers-reduced-motion: reduce)")
  .addEventListener("change", (e) => {
    prefersReducedMotion = e.matches;
  });
```

## Common Pitfalls

1. **Animating from undefined**: If an element has no initial position, the transition starts from 0,0. Always set initial attributes before transitioning.
2. **Key function returning index**: `(d, i) => i` is the default and means "first element stays first." Use a data ID instead so elements track properly across data updates.
3. **Transition name collisions**: Unnamed transitions on the same element interrupt each other. Name them: `.transition("move")`, `.transition("color")`.
4. **Duration too long**: >1 second feels sluggish for UI transitions. Reserve longer durations for storytelling or complex morphs.
5. **Forgetting `.merge()`**: In the old enter/update pattern, new elements don't get update attrs without `.merge()`. The `.join()` pattern avoids this.
6. **Interpolating path strings directly**: `d3.interpolateString` on SVG paths produces garbage when paths have different commands. See the **shape-morphing** skill for the right approaches (parametric interpolation or point resampling).
7. **Canvas not clearing**: Forgetting `clearRect` causes trails. Sometimes intentional for effect, but usually a bug.

## References

- [D3 Transition documentation](https://d3js.org/d3-transition) — Mike Bostock's API reference for `d3-transition`
- [General Update Pattern](https://observablehq.com/@d3/selection-join) — canonical enter/update/exit with `.join()`
- [Object Constancy](https://bost.ocks.org/mike/constancy/) — foundational article on key-based transitions
- [Animated Transitions in Statistical Data Graphics](https://idl.cs.washington.edu/papers/motion/) — Jeffrey Heer & George Robertson's research on how animation aids perception of data changes (IEEE InfoVis 2007)
- [D3 Easing Functions](https://observablehq.com/@d3/easing) — visual reference for all `d3-ease` curves
- [Staggered Transitions](https://observablehq.com/@d3/staggered-transitions) — staggered delay patterns
- [prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) — MDN reference for respecting user motion preferences
