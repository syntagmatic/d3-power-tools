---
name: rendering
description: "Choose and build the rendering layer for a D3 chart: SVG vs Canvas vs WebGL, Canvas+SVG layer stacks, HiDPI/DPR setup, hit detection (quadtree, Delaunay, color picking), dirty-flag render loops, typed arrays, workers, OffscreenCanvas, shaders and instancing, ResizeObserver, viewBox vs redraw, container queries, touch, iframes, print, multi-view composition (jig), and idiomatic D3 code review: margin convention, .join(), selection.call, reusable charts."
---

# Rendering

Pick the cheapest renderer that holds the frame budget, then structure the code so every event ends in one draw per frame. Models default to SVG for everything, or jump to WebGL for 20K points. Both are wrong. Most of the bugs here look fine in code and show up as blur, jank, or a hover that hits the wrong mark.

## Which renderer

| If... | Use | Why |
|---|---|---|
| < ~500 marks, any interaction | SVG | DOM events, CSS, accessibility for free |
| 500-5K, rarely updates (hover, click) | SVG or Canvas | SVG still fine for hover; Canvas once it redraws often |
| 500-5K, continuous updates (drag, animation, force ticks) | Canvas + SVG overlay | per-frame DOM reflow stutters; 2K SVG circles hover fine but drag badly |
| 5K-500K | Canvas data layer + SVG overlay (hybrid) | the d3.parcoords pattern: Canvas pixels, SVG axes/brush/pointer |
| 50K+ with a highlighted subset | + separate highlight canvas | hover repaints the ring, not 100K points |
| 500K+ static | Canvas progressive render, or WebGL | one GPU draw call |
| 500K+ animated, or millions | WebGL 2 instanced | GPU does per-mark work in parallel |
| GPU-side binning or simulation | WebGPU compute | WebGL 2 is enough for draw-call bottlenecks |
| Small multiples | Canvas (or SVG) | browsers cap live WebGL contexts at ~8-16 |

Count isn't everything: 500 complex geo paths are slower in SVG than 5K circles. **Profile before escalating.** WebGL costs shader debugging and manual buffers, and text, dashes, and gradients get painful.

Hybrid stack: container `position: relative`; every layer `position: absolute`, same size. From the bottom: data canvas (`pointer-events: none`) → highlight canvas → SVG overlay (axes, brush, all pointer events) → HTML (controls, legend). `ctx.translate(margin.left, margin.top)` once so canvas and SVG `g` share coordinates. Animate on Canvas and settle into SVG when the resting state needs interaction.

## Canvas traps

- **Blurry canvas.** Backing store `Math.round(w * dpr)`, CSS size `w px`, `ctx.scale(dpr, dpr)`. Miss any one and it's soft on retina.
- **Resize resets state.** Setting `canvas.width`/`height` (and `ctx.reset()`) wipes the transform. Re-apply the DPR scale every time.
- **DPR changes** when a window crosses monitors. The `(resolution: Ndppx)` media query is tied to the current value, so re-register it after each change.
- **Stray lines between circles.** `ctx.moveTo(x + r, y)` before each `ctx.arc` in a batched path.
- **Clearing.** With only the DPR scale, `clearRect(0, 0, width, height)` in CSS px. After a margin translate, clear under `setTransform(1,0,0,1,0,0)`.
- **`putImageData` ignores transform and clip.** Size ImageData at physical pixels, or go through an offscreen canvas + `drawImage`.
- **State changes are the cost**, not shapes. One `beginPath`/`fill` per style group, never per point.
- **`fillText` and `shadowBlur` are slow.** ~50 labels max; sprites for shadows and custom markers.
- **Translucent overdraw.** 10K circles at alpha saturate into a blob. Bin or draw density instead.
- **Memory.** A 1200×800 canvas at 2× is ~15MB. Merge layers that always redraw together.

## Hit detection

| Marks | Method | Trap |
|---|---|---|
| Points, nodes | `d3.quadtree` + `find(mx, my, r)` | always pass a radius; rebuild on data, scale, or resize change |
| Points, want nearest-always or cells | `d3.Delaunay.from(...).find` | recompute on scale change |
| Rects (treemap, icicle) | bounding box, keep the deepest by `depth` | |
| Arcs (sunburst) | polar test: radius, then `(atan2(y,x) + π/2 + 2π) % 2π` | D3 angles start at 12 o'clock, `atan2` at 3 |
| Lines, paths, overlaps | color picking on a hidden canvas (`willReadFrequently: true`) | opaque IDs; antialiased edges decode to a wrong ID, so treat unknowns as misses |
| WebGL | quadtree to ~1M, else GPU picking via `readPixels` | GL origin is bottom-left: flip y |

Under zoom, keep the index in base coordinates and inverse-transform the pointer: `find((mx - t.x) / t.k, (my - t.y) / t.k, r / t.k)`.

## Render loop

Never draw in an event handler. Mark dirty; draw once per frame:

```js
const DATA = 1, HIGHLIGHT = 2, AXES = 4;
let dirty = 0;
const markDirty = layers => { if (!dirty) requestAnimationFrame(flush); dirty |= layers; };
function flush() { const d = dirty; dirty = 0; if (d & DATA) drawData(); if (d & HIGHLIGHT) drawHighlight(); if (d & AXES) drawAxes(); }
```

A brush that updates three views then costs one frame, not three redraws with stale intermediates. Over budget: highlight now and rebin later; progressive shuffled chunks (`d3.shuffle`, cancel on interaction); skip transitions until brush `end`; move binning and layout to a Worker.

## Typed arrays and workers

- 100K+ points: `Float32Array` xs/ys, no per-point objects. Transfer buffers to workers with `postMessage(msg, [arr.buffer])`, zero copy, and the sender's copy is detached.
- Draw-loop jank at 50K+: `transferControlToOffscreen()`. Forward DPR and zoom as messages. Keep the quadtree on the main thread for instant hover. Workers have no `document.fonts`.
- LOD by visible count: <500 full detail with labels; 500-10K 2-4px dots; 10K-100K 1px batched; 100K+ density or hex bins.

## WebGL traps

- Y flip: `clip.y = -clip.y`, or the chart is upside down and still plausible.
- DPR is manual: `gl_PointSize = size * dpr`, `gl.viewport(0, 0, canvas.width, canvas.height)` after resize.
- `gl.POINTS` has a GPU size cap and `lineWidth` is stuck at 1px. Use instanced quads for shapes and thick lines.
- Zoom through uniforms; never re-upload buffers. Brush filtering through a `bufferSubData` visibility attribute.
- Handle `webglcontextlost` (`preventDefault`) and rebuild on `webglcontextrestored`.

## Sizing and resize

| Chart | Approach |
|---|---|
| Decorative, no meaningful text | `viewBox`, no JS |
| Axes, labels, or interaction | ResizeObserver + redraw: ticks `innerWidth / 80`, margins from measured labels |
| Legend placement, font size, hiding notes | `@container` queries |
| Embedded in unknown pages | both |
| Static export, fixed cell | fixed size, no observer |

- **Observe a wrapper sized by CSS**, with `overflow: hidden`. If the chart's content sets the size, render → resize → render loops.
- Guard `width > 0` (hidden tabs measure 0) and skip height-only changes (mobile address bar).
- `container-type: inline-size` can't size itself from its children; its parent layout must.
- Brush selections are pixels: store them in data space and `brush.move` them back after a resize. Rebuild quadtrees; recompute `translateExtent`.
- `<svg width="100%">` without viewBox or height is 150px tall.
- Disconnect observers and cancel rAFs in `destroy()`.

**Touch:** WCAG 2.2 AA target is 24×24px; aim for 44. On `(pointer: coarse)`, enlarge invisible hit areas and search radii, not the marks. Brushes under ~400px wide become a range input. Use `pointer*` events throughout. Honor `prefers-reduced-motion` with duration 0.

## Code structure

- **Margin convention**: outer `width`/`height`, a `margin` object, one translated `g`, scales on the inner size.
- **Joins**: `.data(data, d => d.id).join("circle")`. A key whenever data can reorder or filter, or transitions morph marks into the wrong data. Enter/update/exit callbacks only when they behave differently.
- **Composition**: repeated config goes in `fn(g, ...)` and is applied with `.call(fn, ...)`, which returns the original selection.
- **Indent**: 2 spaces when a method returns a new selection, 4 when it's the same one.
- **Events**: arrow handlers use `event.currentTarget`, not `this`. Namespace listeners (`click.tooltip`) or the second replaces the first.
- **State → render**: data (frozen), view (scales, layout: derived from data + size), interaction (selection, brush, zoom: references data **by key**). Events update state, then `markDirty`. Init order: measure → layers → scales → layout → chrome → marks → bind interactions → a11y. Binding before the views exist fires handlers into nothing.
- **Frameworks**: let D3 own its `<svg>` exclusively, or use D3 only for math.

## References

- `references/canvas.md`: layer setup, hit-detection table, batched and typed-array drawing, progressive render queue, ImageData, OffscreenCanvas, culling and LOD, sprite atlases.
- `references/webgl.md`: when not to, shader pair with zoom uniforms, buffer helper, instancing, thick lines, GPU picking math, pitfalls.
- `references/responsive.md`: viewBox vs redraw, ResizeObserver guards, container queries, tick/margin rules, brush restore, DPR watcher, touch, iframe height, print.
- `references/jig-template.md`: layer stack table, init order and what re-runs, state kinds, dirty bits, archetypes, resize contract, `remapBrush`.
- `references/d3-idioms.md`: indentation, joins, `.call`, reusable chart closure, naming, events, review checklist.
- `examples/`: `canvas-rendering.html`, `webgl-rendering.html`, `responsive.html`, `composition-explorer.html`. Tested by `tests/test.config.json`.
