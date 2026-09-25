# Transitions

Absorbed from the v2 `motion` skill. Open when writing the actual transition code: staged joins, interruption, canvas animation loops, color tweens, reduced motion.

## When animation helps (Heer & Robertson 2007)

- **Tracking identity**: the viewer sees which element moved where (object constancy).
- **Revealing causation**: temporal order shows this-caused-that.
- **Sequential storytelling**: scrollytelling, steppers, guided narratives.
- **Aggregation/disaggregation**: points rolling up into summaries.

Prefer small multiples when the viewer must compare two states precisely, when many elements would move at once without staggering, when marks occlude each other mid-flight, or when the same transition will be seen over and over.

**Congruence**: every intermediate frame should be a valid chart. If bars pass through each other mid-animation, stage the transition.

## Easing

| Motion | Ease |
|---|---|
| Position change (default) | `d3.easeCubicInOut` |
| Entrance, responsive UI | `d3.easeCubicOut` |
| Exit | in-easing (`d3.easeCubicIn`) |
| Overshoot/bounce | `easeBackOut.overshoot(1.5)`, `easeElasticOut.amplitude(1).period(0.4)`: sparingly |
| Continuous process (progress, loading) | `d3.easeLinear` only |

## Staged exit → update → enter

Coordinated delays are more robust than chained `transition.end()` promises, which reject when any element's transition is interrupted.

```js
function render(data) {
  const joined = svg.selectAll(".bar").data(data, d => d.id);
  const exitDur = 300, moveDur = 400, enterDur = 400;
  const moveDelay = joined.exit().empty() ? 0 : exitDur;
  const enterDelay = moveDelay + moveDur;

  joined.join(
    enter => enter.append("rect").attr("class", "bar")
      .attr("x", d => xScale(d.id)).attr("width", xScale.bandwidth())
      .attr("y", height).attr("height", 0).attr("opacity", 1)
      .call(e => e.transition().delay(enterDelay).duration(enterDur)
        .attr("y", d => yScale(d.value))
        .attr("height", d => height - yScale(d.value))),
    update => update
      .call(u => u.transition().delay(moveDelay).duration(moveDur)
        .attr("x", d => xScale(d.id)).attr("width", xScale.bandwidth())
        .attr("y", d => yScale(d.value))
        .attr("height", d => height - yScale(d.value))
        .attr("opacity", 1)),
    exit => exit
      .call(e => e.transition().duration(exitDur)
        .attr("height", 0).attr("y", height).attr("opacity", 0).remove())
  );
}
```

The update branch asserts every property enter or exit animates, `opacity` especially. An element interrupted mid-enter lands in update at whatever opacity it had.

## Interruption

- A transition, when it starts, interrupts the active transition *of the same name* on the same element and cancels earlier-scheduled ones of that name. Independent properties need separate names: `.transition("move")`, `.transition("color")`.
- For rapid input (clicks, slider drags), call `sel.interrupt()` (or `interrupt(name)`) before scheduling, so stale delayed transitions don't fire later.
- If the next target is computed from the previous one, keep intended targets in a `Map` keyed by node. Reading attributes back from the DOM mid-transition gives the interpolated value and a jittery restart.

## Canvas animation

SVG transitions don't drive canvas. Use `d3.timer` (rAF-backed) and redraw every frame.

```js
function animate(data, targets) {
  const speed = 0.05, current = data.map(d => ({ ...d }));
  const timer = d3.timer(() => {
    ctx.clearRect(0, 0, width, height);
    let settled = true;
    current.forEach((d, i) => {
      d.x += (targets[i].x - d.x) * speed;
      d.y += (targets[i].y - d.y) * speed;
      if (Math.abs(targets[i].x - d.x) > 0.5 || Math.abs(targets[i].y - d.y) > 0.5) settled = false;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, 2 * Math.PI);
      ctx.fill();
    });
    if (settled) timer.stop(); // d3.timer ignores the callback's return value
  });
}
```

**Multi-property layout morphs** (pack → treemap on canvas): keep three things apart. Render state (a Map of currently drawn values per node), target state (the new layout), and a transition manager that builds `d3.interpolateNumber` per node/property and runs one `d3.timer` applying `easeCubicInOut(elapsed / duration)`. Flip shape type (circle → rect) at `t = 0.5`. Interruption is free: the new transition reads the current render state as its source.

**Hidden tabs**: rAF, and so `d3.timer`, stops in background tabs. If an animation must finish while hidden, fall back to `setTimeout(tick, 16)` when `document.hidden`.

## Color transitions

Interpolate in Lab (or HCL for hue sweeps), not RGB. When the color scale's domain changes, tween from the old mapping to the new:

```js
const oldScale = colorScale.copy();
colorScale.domain(newDomain);
selection.transition().duration(600)
  .attrTween("fill", d => d3.interpolateLab(oldScale(d.value), colorScale(d.value)));
```

## View Transitions API

`document.startViewTransition(() => render())` cross-fades snapshots. Use it for container-level swaps (chart type, chart ↔ table), not data-level animation. Don't combine with D3 transitions on the same content: it animates a snapshot, not the live DOM. Feature-detect and fall back to a plain render.

## Choosing a tool

| Need | Tool |
|---|---|
| Data-driven element animation | `selection.transition()` |
| Container-level view swap | View Transitions API |
| Scroll-triggered updates | IntersectionObserver (or Scrollama) + D3 |
| Canvas, 500+ elements | `d3.timer` with state interpolation |
| Multi-stage choreography | coordinated delays, or `transition.end()` with a catch |
| Reduced motion | duration 0, final state |

| Elements | Technique | Duration |
|---|---|---|
| < 100 | SVG transitions | 300-800ms |
| 100-1,000 | SVG with stagger | 400-1000ms, 10-30ms stagger |
| 1,000-10,000 | Canvas + `d3.timer` | 500-1000ms |
| 10,000+ | Canvas (layout in a Worker) | ~500ms, skip frames if needed |

## Reduced motion

```js
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const safeDur = ms => reducedMotion.matches ? 0 : ms;
selection.transition().duration(safeDur(600)).attr("y", d => yScale(d.value));
```

Canvas: draw the final frame directly. Listen for `reducedMotion.addEventListener("change", ...)`; users toggle it with the page open.

## Pitfalls

1. **Animating from nothing**: an element with no initial attributes animates from 0,0. Set start attributes on enter.
2. **Index keys**: the default key is the index, meaning "first stays first." Key by id.
3. **Path strings via `interpolateString`**: garbage when commands differ. See `shape-morphing.md`.
4. **No `clearRect`** on canvas: trails.
5. **Delays on rapid input** without `interrupt()`: old staged transitions fire after the new ones.

Sources: Bostock, "Object Constancy"; Heer & Robertson, "Animated Transitions in Statistical Data Graphics" (InfoVis 2007).
