---
name: motion
description: "Animate D3 charts only when motion shows a real correspondence: enter/update/exit transitions, object constancy, easing, stagger and duration budgets, staged sequencing, interruption and named transitions, prefers-reduced-motion, canvas animation loops, color tweens, View Transitions, scrollytelling and steppers (sticky graphic, Scrollama), and shape morphing (circle to rect, bar to pie, path resampling, flubber, d3-interpolate-path, layout and projection transitions)."
---

# Motion

Animation earns its frames by answering "which thing became which thing?" Models add transitions by reflex, let them fight each other on rapid input, and morph shapes that share no identity. This skill is about when to move, in what order, and how to survive interruption.

Decide in order: should it animate, how is it staged, and what does the shape do in between.

## Should it animate?

| If... | Do | Not |
|---|---|---|
| the same marks change position/size and each has a stable id | transition with a key function `d => d.id` (object constancy) | the default index key: "first stays first" is a false correspondence |
| the data changed category (revenue → headcount) or marks have no shared identity | cut or crossfade | a morph, which claims continuity that isn't there |
| the viewer needs to compare two states precisely | small multiples side by side | sequential animation they must remember |
| marks would pass through each other or occlude mid-flight | stage it (below) or cut | a single tween with invalid intermediate frames |
| everything reorders at once (sorted bars → unsorted treemap) | keep order, or stagger so a few can be followed | 30+ shapes swarming |
| the swap is container-level (chart type, chart ↔ table) | View Transitions API crossfade | D3 transitions on the same content (VT animates a snapshot) |
| the user has `prefers-reduced-motion: reduce` | duration 0, jump to the final state | shorter animation; listen for `change` at runtime |
| the transition will be seen on every hover or tick | skip it | animation that becomes friction |

Every intermediate frame should be a valid chart (congruence).

## Budgets

| Motion | Duration |
|---|---|
| Simple position change | 300-500ms |
| Complex multi-element transition | ~1000ms total |
| Dwell between stages of one transition | 200-400ms |
| Stagger per element | 20-80ms, total stagger < 500ms |
| Scrollytelling step | 400-800ms |
| Rest before an auto-advancing narrative stage | ~1.5s |

| Elements | Technique |
|---|---|
| < 100 | SVG transitions |
| 100-1,000 | SVG with 10-30ms stagger |
| 1,000+ | Canvas + `d3.timer`, redraw every frame |

Easing: `easeCubicInOut` for position changes, out-easing for entrances, in-easing for exits, `easeLinear` only for continuous processes. Elastic/back overshoot sparingly.

Stagger order says something: by index (reading order), by value (largest first), by distance from a point (ripple). Move at most 2-3 major groups at once.

## Staging: exit → update → enter

Departing marks clear first, survivors move, newcomers appear into the freed space. Use coordinated delays:

```js
const moveDelay = joined.exit().empty() ? 0 : exitDur;
const enterDelay = moveDelay + moveDur;
```

- Enter sets *every* start attribute (x, width, y, opacity) before its transition, or it animates from 0,0.
- Update asserts every property enter or exit animates, `opacity` especially. An element interrupted mid-enter lands in update half-transparent.
- `transition.end()` works for promise-chained stages but rejects on any interruption, so wrap it in try/catch. An empty selection resolves immediately.

## Interruption

This is where generated code breaks most often.

- A transition, when it starts, interrupts the active transition **of the same name** on that element and cancels earlier-scheduled ones of that name. Unnamed transitions all share the name `null`.
- Independent properties need separate names (`.transition("move")`, `.transition("color")`), or the color change kills the move.
- Rapid clicks and slider drags: call `sel.interrupt()` (or `interrupt(name)`) before scheduling. Otherwise delayed stages from old clicks fire after the new one.
- When the next target depends on the previous one, read it from a cached target Map, not the DOM. Mid-transition attributes are interpolated values.
- Canvas: the new animation reads the *current render state* as its source, so interruption is free if render state is kept separately from target state.
- Scroll-up and Back need idempotent stage functions: each sets the full scene regardless of the previous stage.

## Scrollytelling

- Sticky graphic: chart `position: sticky; top: 0`, step text scrolling in a sibling column. IntersectionObserver (threshold ~0.5) or Scrollama maps step index → `goToStage(i)`.
- Discrete shifts use **step triggers** (a transition fires on enter). Continuous changes use **progress scrub**: the property is a direct function of scroll fraction 0-1, with no transition.
- One stage manager: an array of idempotent stage functions and a single index. Raise active elements at the start of each stage.

## Which morph technique

| Shapes | Technique |
|---|---|
| Share numeric params: rect `rx`/size, arc angles/radii, positions | Attribute/parameter tween: true curves, cheapest |
| Different closed geometry (star → circle, rect → wedge, treemap → pack) | Point resampling: N points, rotation-aligned, lerp arrays (`scripts/morph-paths.js`) |
| Open lines with different point counts | `d3-interpolate-path` |
| Holes, multiple subpaths, winding mismatch | `flubber` |
| Two map projections | lerp raw projection output inside `d3.geoProjection` |

Circle ↔ rect: a `<rect>` with `w == h` and `rx = w/2` is a circle. If `w != h` it's a pill. Bar ↔ pie: tween `d3.arc` parameter objects stashed on the element (`this`), not the datum.

## Traps

- `d3.interpolateString` on paths with different commands → garbage frames. Parametric or resample.
- Arc params stored on the datum → lost on `.data()` rebind; `interpolate(undefined, next)` snaps.
- No rotation alignment → shape spins or pinches mid-morph. Tweening rect ↔ wedge parameters → near-zero area at t = 0.5; resample instead.
- `getPointAtLength()` per frame → jank. Resample once. Below ~64 points circles look polygonal; 128 is safe.
- Color tweens in RGB → muddy midpoints. Use `interpolateLab`; on domain change, tween from `oldScale.copy()` to the new scale in `attrTween`.
- `d3.timer` ignores the callback's return value → stop it with `timer.stop()`.
- rAF-backed timers stop in hidden tabs. If it must finish, fall back to `setTimeout` when `document.hidden`.
- No `clearRect` per canvas frame → trails.
- Unhandled `end()` rejection when the user clicks Next mid-stage.

## References

- `references/motion.md`: staged join code, easing table, interruption, canvas lerp loop and multi-property state machine, color tweens, View Transitions, reduced motion.
- `references/choreography.md`: promise sequencing with catch, stage manager, IntersectionObserver/Scrollama, step vs scrub, pacing.
- `references/shape-morphing.md`: technique table and libraries, bar ↔ pie arc tween, resampling steps, cross-layout morphs, projection transition code, when not to morph.
- `scripts/morph-paths.js`: `resamplePath`, `bestRotation`, `pointsToPath`, `morphPaths`.
- `examples/`: animated transitions, shape morph (circle/rect), arc morph (bar/pie/donut).
