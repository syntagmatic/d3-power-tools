# Motion Skill Research

Research date: 2026-03-25

## Current Coverage

The motion SKILL.md (538 lines) covers:

- **SVG Transitions**: enter/update/exit with key functions, `.join()` pattern (D3 v7+)
- **Staggered Animations**: delay-based staggering strategies
- **Easing Functions**: built-in easing options
- **Chaining and Sequencing**: sequential transitions, staged exit-update-enter, interruption handling (TransitionManager pattern)
- **Shape Morphing**: deferred to the `shape-morphing` skill
- **Canvas Animations**: basic animation loop, FLIP pattern, multi-property state machine architecture, background-tab fallback (`setTimeout` when `requestAnimationFrame` throttled)
- **Color Transitions**: perceptually uniform interpolation, animated color scales
- **Scrollytelling**: basic scrollytelling transitions, stepper/slideshow pattern
- **Performance Guidelines**: frame budget considerations
- **Accessibility**: `prefers-reduced-motion` support

### Gaps identified

1. No mention of the View Transitions API (browser-native, shipped 2024-2025)
2. No mention of CSS scroll-driven animations (`animation-timeline`, `scroll()`, `view()`)
3. Scrollytelling section is brief; no mention of scrollama or IntersectionObserver patterns
4. No coverage of perception research (Heer & Robertson principles, when animation helps vs hurts)
5. No guidance on transition choreography design principles beyond basic chaining

---

## View Transitions API (browser-native, cross-document, D3 integration)

The View Transitions API provides browser-native animated transitions between DOM states. It became Baseline Newly Available in October 2025 (Chrome 111+, Edge 111+, Firefox 133+, Safari 18+).

### How it works

1. Browser screenshots the current state
2. Your callback updates the DOM (D3 selections, data joins, attribute changes)
3. Browser screenshots the new state
4. Browser animates from old to new using CSS-customizable pseudo-elements

### Core API

```js
document.startViewTransition(async () => {
  // Perform D3 DOM updates here
  svg.selectAll("rect")
    .data(newData, d => d.id)
    .join("rect")
    .attr("x", d => xScale(d.category))
    .attr("height", d => height - yScale(d.value));
});
```

### Naming elements for targeted transitions

```css
.bar-group { view-transition-name: bar-group; }
/* Or auto-naming in Level 2: */
.bar { view-transition-name: match-element; }
```

### 2025 additions (Interop 2025 focus area)

- `view-transition-class`: apply shared animation styles to groups of transitioning elements
- `view-transition-name: match-element`: auto-naming so each element gets its own transition without manual naming
- `:active-view-transition` selector: style elements differently during transitions
- Nested view transition groups: restore clipping/hierarchy during transitions
- `document.activeViewTransition`: access current transition without manual tracking
- Cross-document view transitions: animate between page navigations (MPA support)

### D3 integration considerations

- View Transitions animate the *visual snapshot*, not the DOM elements. D3's interpolation-based transitions animate actual DOM attributes frame-by-frame.
- View Transitions are best for *view-level* changes (switching chart types, navigating between dashboard panels) rather than *data-level* changes (updating bar heights).
- For data-driven animation where intermediate states must be valid data representations, D3 transitions remain the right tool.
- View Transitions can wrap D3 updates to provide a cross-fade or morph effect at the container level, complementing D3's element-level transitions.

### When to use View Transitions vs D3 transitions

| Scenario | Recommendation |
|---|---|
| Switching between chart types (bar to line) | View Transitions for container-level morph |
| Updating data within same chart | D3 `.transition()` for data-driven interpolation |
| Dashboard panel navigation | View Transitions |
| Sorting/reordering elements | D3 transitions (need valid intermediate positions) |
| Chart to data table toggle | View Transitions |

Sources:
- [Chrome blog: View Transitions in 2025](https://developer.chrome.com/blog/view-transitions-in-2025)
- [MDN: View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API)
- [MDN: startViewTransition()](https://developer.mozilla.org/en-US/docs/Web/API/Document/startViewTransition)
- [web.dev: Same-document view transitions Baseline](https://web.dev/blog/same-document-view-transitions-are-now-baseline-newly-available)
- [Smashing Magazine: View Transitions API Part 2](https://www.smashingmagazine.com/2024/01/view-transitions-api-ui-animations-part2/)

---

## Scrollytelling Frameworks (scrollama, CSS scroll-timeline, step patterns)

### Scrollama (v3.2.0)

Scrollama is the de facto standard for scrollytelling, using IntersectionObserver instead of scroll events. Three capabilities:

1. **Step triggers**: fire event when element crosses visibility threshold
2. **Step progress**: fire events continuously from 0-100% through a step
3. **Sticky graphic**: convenience functions for the "sticky graphic with scrolling text" pattern

```js
import scrollama from "scrollama";

const scroller = scrollama();
scroller
  .setup({
    step: ".step",
    offset: 0.5,        // trigger at 50% viewport
    progress: true       // enable continuous progress events
  })
  .onStepEnter(({ element, index, direction }) => {
    updateChart(index);  // D3 update driven by scroll position
  })
  .onStepProgress(({ element, index, progress }) => {
    // Continuous 0-1 progress for smooth interpolation
    interpolateState(index, progress);
  });
```

### Integration with D3

The step-enter pattern works well with D3's data join: each step triggers a data swap and transition. The progress pattern enables continuous interpolation — useful for smoothly animating between states rather than snapping.

### Framework variants

- **react-scrollama**: React wrapper with `<Scrollama>` and `<Step>` components
- **vue-scrollama**: Vue component adaptation
- Scrollama is also used in Quarto websites for academic/data journalism publishing

### Key architectural pattern: "Sticky graphic"

```
+---------------------------+
| Scrolling text steps      |  <-- .step elements
|                           |
| +---------------------+   |
| | Fixed/sticky chart  |   |  <-- position: sticky
| +---------------------+   |
|                           |
| More scrolling steps      |
+---------------------------+
```

The chart stays fixed while text scrolls past. Each text step triggers a chart state change. This is the dominant scrollytelling pattern used by NYT, Pudding, and other data journalism outlets.

Sources:
- [Scrollama GitHub](https://github.com/russellsamora/scrollama)
- [Pudding: Introducing Scrollama](https://pudding.cool/process/introducing-scrollama/)
- [Scrollama in Quarto (2025)](https://liamdbailey.com/posts/2025-03-28-scrollyqmd/)

---

## Animation Perception Research (when motion helps vs hurts comprehension)

### Heer & Robertson (2007): Foundational framework

The seminal paper "Animated Transitions in Statistical Data Graphics" established two core principles and 10 design recommendations:

#### The Congruence Principle
The external representation (what's shown) should match the desired internal representation (what the viewer should understand). Applied to animation:
- Maintain valid data graphics during transitions (no nonsensical intermediate states)
- Keep axes and data relationships consistent throughout
- Animated paths should reflect meaningful data relationships

#### The Apprehension Principle
The representation should be readily and accurately perceived. Applied to animation:
- Transitions should be easily trackable by the human visual system
- Complex transitions should be staged (broken into simpler sub-transitions)
- Duration should be long enough for tracking but short enough to maintain engagement

#### Key findings

- **Recommended duration**: ~1 second for most transitions. Minimal-movement transitions can be faster.
- **Staging helps**: breaking complex transitions into sequential stages reduces cognitive load
- **Object constancy matters**: viewers need to track individual elements across states

### When animation helps

- **Tracking identity**: showing which elements moved where (object constancy)
- **Understanding aggregation**: seeing how individual points roll up into summary statistics
- **Trend inference**: animated uncertainty visualizations outperform static ones
- **Causal reasoning**: showing cause-and-effect relationships through temporal sequence

### When animation hurts

- **Occlusion during transition**: if elements overlap mid-animation, tracking fails
- **Too many simultaneous movements**: the human visual system can track ~4 objects; beyond that, staggering may actually harm tracking of the group
- **Error-prone designs**: poorly designed animations perform worse than static small multiples
- **Speed-accuracy tradeoff**: animation can improve understanding but increase task completion time

### Design guidance from research

1. **Stage complex transitions** into sequential sub-steps
2. **Use trajectory traces** when elements move long distances
3. **Limit simultaneous movements** to what the visual system can track
4. **Prefer position changes over color/size changes** for animation (position is tracked pre-attentively)
5. **Consider small multiples** as an alternative — sometimes static comparison outperforms animation
6. **Test with real users** — animation effectiveness is highly task-dependent

### Gemini grammar (2020)

Kim & Heer developed Gemini, a grammar and recommender system for animated transitions in statistical graphics, formalizing transition design into composable primitives. This provides a theoretical framework for decomposing complex transitions.

Sources:
- [Heer & Robertson: Animated Transitions in Statistical Data Graphics (2007)](https://idl.cs.washington.edu/files/2007-AnimatedTransitions-InfoVis.pdf)
- [Stanford Vis Group: Animated Transitions](http://vis.stanford.edu/papers/animated-transitions)
- [Robertson et al: Effectiveness of Animation in Trend Visualization](https://www.semanticscholar.org/paper/Effectiveness-of-Animation-in-Trend-Visualization-Robertson-Fernandez/7a5f745b8f162fa5a2a25acafc4845b65d3f6410)
- [Studies and design considerations for animated transitions (2023)](https://link.springer.com/article/10.1007/s12650-023-00937-z)
- [Gemini: A Grammar for Animated Transitions (2020)](https://ar5iv.labs.arxiv.org/html/2009.01429)
- [A Design Space of Animating Data-Driven Transitions in Data Videos (2025)](https://link.springer.com/article/10.1007/s12650-025-01066-5)

---

## CSS Scroll-Driven Animations (new spec, declarative scroll-linked effects)

CSS scroll-driven animations replace JavaScript scroll listeners with declarative, GPU-accelerated, off-main-thread animations tied to scroll position.

### Browser support

- Chrome: shipped (stable since 2024)
- Firefox: behind flag, shipping progressively
- Safari 26: shipped September 2025
- Baseline status: approaching wide availability

### Two timeline types

#### Scroll Progress Timeline (`scroll()`)
Tracks overall scroll position of a container. Progress goes from 0% (top) to 100% (bottom).

```css
.progress-bar {
  animation: grow linear;
  animation-timeline: scroll(block nearest);
}

@keyframes grow {
  from { width: 0%; }
  to { width: 100%; }
}
```

#### View Progress Timeline (`view()`)
Tracks when a specific element enters/exits the viewport. 0% = entering, 100% = leaving.

```css
.chart-section {
  animation: fade-in linear both;
  animation-timeline: view();
  animation-range: entry 0% entry 100%;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### `animation-range` for precise control

```css
/* Only animate during the entry phase */
animation-range: entry 0% entry 100%;

/* Animate during the middle 50% of visibility */
animation-range: contain 25% contain 75%;

/* Custom inset: start when 10% from bottom, end when 50% from top */
animation-range: view(10%) view(50%);
```

### Named scroll timelines

```css
.scroll-container {
  scroll-timeline-name: --chart-scroll;
  scroll-timeline-axis: block;
}

.animated-element {
  animation-timeline: --chart-scroll;
}
```

### Performance advantage

Scroll-driven animations run on the compositor thread, not the main thread. This means:
- No jank from JavaScript scroll listeners
- No `requestAnimationFrame` needed
- GPU-accelerated by default
- Works even when main thread is busy

### Data visualization applications

- **Scroll-reveal charts**: fade/slide chart sections into view as user scrolls
- **Progress indicators**: reading progress bars
- **Parallax data layers**: background data context that moves at different scroll rates
- **Scrollytelling annotations**: annotations that appear/disappear based on scroll position
- **Continuous state interpolation**: using `view()` progress to drive CSS custom properties that D3 reads

### Limitation for D3

CSS scroll-driven animations can only animate CSS properties. They cannot directly drive D3 data joins or SVG attribute changes. The bridge pattern: use scroll-driven animations for visual effects (opacity, transform) and IntersectionObserver/scrollama for triggering D3 data updates.

Sources:
- [MDN: CSS scroll-driven animations](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations)
- [MDN: animation-timeline](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/animation-timeline)
- [Smashing Magazine: Introduction to CSS Scroll-Driven Animations](https://www.smashingmagazine.com/2024/12/introduction-css-scroll-driven-animations/)
- [Chrome for Developers: Scroll-driven animations](https://developer.chrome.com/docs/css-ui/scroll-driven-animations)
- [Codrops: Practical Introduction to scroll() and view()](https://tympanus.net/codrops/2024/01/17/a-practical-introduction-to-scroll-driven-animations-with-css-scroll-and-view/)
- [CSS-Tricks: Scroll-Driven Animations](https://css-tricks.com/unleash-the-power-of-scroll-driven-animations/)

---

## Transition Choreography (orchestrating multi-stage, multi-element sequences)

### D3's built-in choreography tools

#### Staggered delay

```js
bars.transition()
  .delay((d, i) => i * 50)  // 50ms between each element
  .duration(400)
  .attr("y", d => yScale(d.value));
```

#### Chained transitions (sequential stages)

```js
bars.transition("stage1")
    .duration(300)
    .attr("width", newWidth)
  .transition("stage2")
    .duration(300)
    .attr("y", newY)
    .attr("height", newHeight);
```

#### Staged exit-update-enter

The classic choreography pattern: exit first, then update, then enter. This prevents visual clutter from simultaneous movements.

```js
// Stage 1: Exit
const t0 = svg.transition().duration(400);
bars.exit().transition(t0).attr("opacity", 0).remove();

// Stage 2: Update (after exit completes)
const t1 = t0.transition().duration(600);
bars.transition(t1).attr("x", d => xScale(d.category));

// Stage 3: Enter (after update completes)
const t2 = t1.transition().duration(400);
entering.transition(t2).attr("opacity", 1);
```

### Advanced choreography patterns

#### Stagger strategies beyond linear delay

```js
// Center-out stagger
.delay((d, i, nodes) => Math.abs(i - nodes.length / 2) * 30)

// Random stagger (organic feel)
.delay(() => Math.random() * 300)

// Data-driven stagger (larger values animate first)
.delay(d => (1 - d.value / maxValue) * 500)

// Spatial stagger (animate from a focal point)
.delay(d => Math.hypot(d.x - focalX, d.y - focalY) * 0.5)
```

#### The Heer & Robertson staging decomposition

For complex transitions (e.g., stacked-to-grouped bars):
1. **Stage 1**: Transform axis/scale (reposition grid lines)
2. **Stage 2**: Move elements to new positions (with stagger)
3. **Stage 3**: Resize elements to final dimensions

Each stage should be independently comprehensible. Dwell time between stages: 200-400ms.

#### Multi-stage transition IDs

D3 internally uses monotonically-increasing IDs for transitions. Multi-stage transitions created during `"end"` events inherit the same "age" as the original, preventing interruption conflicts.

#### Transition event coordination

```js
transition.on("end", function(d, i) {
  if (i === nodes.length - 1) {
    // Last element finished — trigger next stage
    startNextStage();
  }
});

// Or use transition.end() promise (D3 v6+)
await bars.transition().duration(400).attr("opacity", 0).end();
startNextStage();
```

#### `transition.end()` promise for async choreography

```js
async function animateUpdate(data) {
  // Exit
  await bars.exit()
    .transition().duration(400)
    .attr("opacity", 0).remove()
    .end();

  // Update
  await bars.transition().duration(600)
    .attr("x", d => xScale(d.category))
    .end();

  // Enter
  await entering.transition().duration(400)
    .attr("opacity", 1)
    .end();
}
```

Sources:
- [Mike Bostock: Working with Transitions](https://bost.ocks.org/mike/transition/)
- [D3 Transition docs](https://d3js.org/d3-transition)
- [D3 Transition timing](https://d3js.org/d3-transition/timing)

---

## Decision Guidance

### When to animate

- The viewer needs to track **what changed** between states (object constancy)
- The transition reveals a **causal relationship** (this caused that)
- You are **telling a story** with sequential reveals (scrollytelling, stepper)
- The data has a **natural temporal dimension** (time series playback)

### When NOT to animate

- The viewer needs to **compare** two states precisely (use small multiples instead)
- More than ~4 elements are moving simultaneously without staggering
- The animation is purely **decorative** (violates the core principle)
- The transition creates **occluded intermediate states** where elements overlap
- Users will see the transition **repeatedly** (it becomes annoying)
- The audience may have **vestibular disorders** (always respect `prefers-reduced-motion`)

### Technology selection

| Need | Tool |
|---|---|
| Data-driven element animation | D3 `.transition()` |
| Container-level view changes | View Transitions API |
| Scroll-triggered data updates | Scrollama + D3 |
| Scroll-linked visual effects (opacity, transform) | CSS `animation-timeline: scroll()` / `view()` |
| Canvas animation (500+ elements) | `requestAnimationFrame` loop with state interpolation |
| Complex multi-stage choreography | `transition.end()` promises or chained transitions |
| Reduced-motion fallback | `prefers-reduced-motion` media query: instant state change |

### Duration guidelines (from research)

- Simple position change: 300-500ms
- Complex multi-element transition: ~1000ms total
- Staged transition dwell time: 200-400ms between stages
- Stagger gap: 20-80ms per element (total stagger should not exceed ~500ms)
- Scrollytelling step transition: 400-800ms

---

## Code Patterns

### View Transitions API wrapping D3 updates

```js
function updateChart(newData) {
  if (!document.startViewTransition) {
    renderChart(newData);  // fallback: instant update
    return;
  }
  document.startViewTransition(() => renderChart(newData));
}

function renderChart(data) {
  const bars = svg.selectAll("rect")
    .data(data, d => d.id)
    .join("rect")
    .attr("x", d => xScale(d.category))
    .attr("y", d => yScale(d.value))
    .attr("height", d => height - yScale(d.value))
    .attr("width", xScale.bandwidth());
}
```

### CSS scroll-driven animation for chart reveal

```css
.chart-container {
  animation: reveal linear both;
  animation-timeline: view();
  animation-range: entry 0% entry 80%;
}

@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .chart-container {
    animation: none;
    opacity: 1;
  }
}
```

### Scrollama + D3 integration

```js
import scrollama from "scrollama";

const states = [
  { filter: d => true, title: "All data" },
  { filter: d => d.year >= 2020, title: "Recent" },
  { filter: d => d.category === "A", title: "Category A" },
];

const scroller = scrollama();
scroller.setup({
  step: ".step",
  offset: 0.5,
}).onStepEnter(({ index }) => {
  const filtered = data.filter(states[index].filter);
  updateChart(filtered);  // D3 transition inside
});

function updateChart(subset) {
  const bars = svg.selectAll("rect")
    .data(subset, d => d.id);

  bars.exit()
    .transition().duration(400)
    .attr("opacity", 0).remove();

  bars.transition().duration(600)
    .attr("x", d => xScale(d.category))
    .attr("y", d => yScale(d.value));

  bars.enter().append("rect")
    .attr("opacity", 0)
    .attr("x", d => xScale(d.category))
    .attr("y", height)
    .transition().duration(600)
    .attr("y", d => yScale(d.value))
    .attr("height", d => height - yScale(d.value))
    .attr("opacity", 1);
}
```

### Hybrid: CSS scroll-driven + Scrollama

Use CSS scroll-driven animations for visual polish (transforms, opacity) and Scrollama for data-driven D3 updates:

```css
/* CSS handles the visual entrance */
.step {
  animation: step-enter linear both;
  animation-timeline: view();
  animation-range: entry 20% entry 80%;
}

@keyframes step-enter {
  from { opacity: 0.3; }
  to { opacity: 1; }
}
```

```js
// Scrollama handles the D3 data update
scroller.setup({ step: ".step", offset: 0.5 })
  .onStepEnter(({ index }) => {
    // D3 transitions for the chart
    updateChart(stateForStep[index]);
  });
```

### Async choreography with transition.end()

```js
async function fullTransition(oldData, newData) {
  const bars = svg.selectAll("rect").data(oldData, d => d.id);

  // Stage 1: exit with stagger
  if (!bars.exit().empty()) {
    await bars.exit()
      .transition().duration(300)
      .delay((d, i) => i * 30)
      .attr("opacity", 0)
      .remove()
      .end();
  }

  // Stage 2: rebind and update
  const updated = svg.selectAll("rect").data(newData, d => d.id);

  if (!updated.empty()) {
    await updated
      .transition().duration(500)
      .attr("x", d => xScale(d.category))
      .attr("y", d => yScale(d.value))
      .attr("height", d => height - yScale(d.value))
      .end();
  }

  // Stage 3: enter with stagger
  const entering = updated.enter().append("rect")
    .attr("x", d => xScale(d.category))
    .attr("y", height)
    .attr("height", 0)
    .attr("opacity", 0);

  if (!entering.empty()) {
    await entering
      .transition().duration(400)
      .delay((d, i) => i * 40)
      .attr("y", d => yScale(d.value))
      .attr("height", d => height - yScale(d.value))
      .attr("opacity", 1)
      .end();
  }
}
```
