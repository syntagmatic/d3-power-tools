---
name: canvas
description: "High-performance Canvas 2D rendering patterns for D3.js visualizations. Use this skill whenever the user needs to render large datasets (1K–1M+ points) on canvas, build fast interactive canvas visualizations with D3, implement quadtree hit detection, optimize canvas draw calls, use typed arrays for visualization data, do pixel-level operations like heatmaps or density plots, set up multi-layer canvas architectures, or profile and optimize canvas rendering performance. Also use when the user mentions canvas performance, frame budget, batched rendering, spatial indexing for hover, ImageData manipulation, or wants to scale a D3 visualization to handle significantly more data."
---

# High-Performance Canvas Rendering with D3

D3 handles data (scales, layouts, binning). Canvas handles pixels. No data join — compute positions into arrays, iterate and draw. No DOM overhead, just a tight loop painting pixels.

```
data → d3.scales/layouts → position arrays → canvas draw loop → pixels
```

## Layer Architecture

Stack multiple canvases for different update frequencies. Editing a tooltip highlight doesn't repaint 100K background points.

```
┌──────────────────────────────────┐
│  SVG overlay (pointer-events)    │  ← axes, labels, tooltips, brushes
│  Canvas: interaction (top)       │  ← hover highlight, selection ring
│  Canvas: foreground              │  ← selected/filtered subset
│  Canvas: background              │  ← full dataset, dimmed
│  Canvas: hit detection (hidden)  │  ← color-picking or quadtree lookup
│  Container div (position:rel)    │
└──────────────────────────────────┘
```

### Setup

```js
function addCanvas(div, width, height) {
  const dpr = devicePixelRatio;
  const canvas = div.append("canvas")
    .attr("width", width * dpr).attr("height", height * dpr)
    .style("width", `${width}px`).style("height", `${height}px`)
    .style("position", "absolute").style("top", 0).style("left", 0)
    .node();
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  return ctx;
}
```

After `ctx.scale(dpr, dpr)`, all drawing uses CSS pixels. Re-run setup on display changes:

```js
matchMedia(`(resolution: ${devicePixelRatio}dppx)`)
  .addEventListener("change", () => resize());
```

Hit detection canvas: create offscreen (never append to DOM), use `willReadFrequently: true` for fast `getImageData` reads. This keeps the backing store in CPU memory — cuts read time ~3x but **disables GPU acceleration** (35+ms draw penalty). Only use on canvases you draw once and read often (color-picking, heatmap generation).

Modern Canvas 2D APIs: `ctx.roundRect()` for rounded bars/cards. `ctx.reset()` clears canvas and resets all state in one call.

## Quadtree Hit Detection

O(log n) nearest-neighbor lookup for point-based visualizations.

```js
const quadtree = d3.quadtree()
  .x(d => xScale(d.x)).y(d => yScale(d.y))
  .addAll(data);

svg.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event);
  const nearest = quadtree.find(mx, my, 20); // 20px search radius
  nearest ? highlightPoint(nearest) : clearHighlight();
});
```

Rebuild when scales change (zoom, resize). Always set a search radius rather than searching the entire space.

### Radius Search (All Points Within Distance)

```js
function findWithinRadius(quadtree, qx, qy, radius, xAcc, yAcc) {
  const results = [], r2 = radius * radius;
  quadtree.visit((node, x0, y0, x1, y1) => {
    if (x0 > qx + radius || x1 < qx - radius ||
        y0 > qy + radius || y1 < qy - radius) return true; // prune
    if (!node.length) {
      let d = node;
      do {
        const dx = xAcc(d.data) - qx, dy = yAcc(d.data) - qy;
        if (dx * dx + dy * dy <= r2) results.push(d.data);
      } while (d = d.next);
    }
  });
  return results;
}
```

### When to Use Which Hit Detection

| Approach | Best for | Limitations |
|----------|----------|-------------|
| Quadtree | Points, circles, nodes | Finds nearest center, not shape boundary |
| Geometric math | Rectangles, arcs, grids | Custom logic per shape type |
| Color-picking | Lines, paths, irregular shapes | Needs hidden canvas redraw |

## Geometric Hit Detection

For rectangles (treemaps, icicles): test `mouseX/Y` against bounding box, keep deepest hit by `node.depth`. For arcs (sunbursts): convert mouse `(x, y)` to polar `(distance, angle)`, test against `innerR`/`outerR` and `startAngle`/`endAngle`. Adjust angle for D3's 12-o'clock origin: `atan2(y, x) + PI/2`.

## Typed Arrays for Large Data

For 100K+ points, flat typed arrays avoid GC pressure and are cache-friendly.

```js
const xs = new Float32Array(n), ys = new Float32Array(n);
data.forEach((d, i) => { xs[i] = xScale(d.x); ys[i] = yScale(d.y); });

function drawPoints(ctx, xs, ys, n) {
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    ctx.moveTo(xs[i] + 2, ys[i]);
    ctx.arc(xs[i], ys[i], 2, 0, Math.PI * 2);
  }
  ctx.fill(); // one beginPath/fill for ALL points
}
```

Typed arrays transfer to Web Workers at zero copy cost via `postMessage(data, [buffer])`. After transfer the original is neutered (length 0).

## Batched Rendering

Canvas state changes (`fillStyle`, `strokeStyle`, `lineWidth`, `globalAlpha`) are expensive. Group draw calls by visual style — 5 draw calls instead of 100K:

```js
const groups = d3.group(data, d => d.category);
for (const [cat, points] of groups) {
  ctx.fillStyle = colorScale(cat);
  ctx.beginPath();
  for (const d of points) {
    ctx.moveTo(d.x + 3, d.y);
    ctx.arc(d.x, d.y, 3, 0, Math.PI * 2);
  }
  ctx.fill();
}
```

For very large datasets, pre-sort indices by style attribute to iterate in batch order without `d3.group`.

## Frame Budgeting

16.6ms per frame at 60fps. Coalesce events into a single render:

```js
let dirty = false;
function markDirty() {
  if (!dirty) { dirty = true; requestAnimationFrame(render); }
}
function render() {
  dirty = false;
  drawBackground(bgCtx, data);
  drawForeground(fgCtx, selected);
}
```

Call `markDirty()` from event handlers instead of drawing directly.

### Progressive Rendering

When a full redraw exceeds the frame budget, render in shuffled chunks across frames:

```js
function createRenderQueue(drawFn, { rate = 500, onComplete } = {}) {
  let queue = [], animId = null;
  function render(data) {
    cancel();
    queue = d3.shuffle(data.slice()); // shuffle for representative partial renders
    animId = requestAnimationFrame(drain);
  }
  function drain() {
    queue.splice(0, rate).forEach(drawFn);
    if (queue.length > 0) animId = requestAnimationFrame(drain);
    else if (onComplete) onComplete();
  }
  function cancel() { if (animId) cancelAnimationFrame(animId); queue = []; }
  render.cancel = cancel;
  return render;
}
```

Shuffle ensures every frame shows a representative sample. Clear canvas before starting, not between chunks.

## ImageData: Pixel-Level Operations

For heatmaps and density plots, writing pixels directly is faster than thousands of small rectangles. `putImageData` bypasses the canvas transform and ignores clipping — draw to an offscreen canvas first, then `ctx.drawImage()` back to respect margins and DPR.

| Approach | Best for |
|----------|----------|
| ImageData pixel writes | Heatmaps, density, continuous fields |
| `ctx.fillRect` per cell | Small grids (<100x100) |
| `ctx.arc` / path batching | Scatter, bubble, node-link (<500K) |

## Web Workers

Move expensive computation off main thread: binning, clustering, layout, force ticks, contours.

```js
// Main: post data, receive positions
worker.postMessage({ data, width, height });
worker.onmessage = ({ data: { positions } }) => drawPoints(ctx, positions);

// Worker: compute layout, transfer result (zero copy)
self.postMessage({ positions }, [positions.buffer]);
```

### OffscreenCanvas: Off-Main-Thread Rendering

When the draw loop itself is heavy (100K+ complex shapes), move rendering to a worker. `transferControlToOffscreen()` is supported in all modern browsers (Chrome 69+, Firefox 105+, Safari 16.4+).

D3 challenge: `d3.zoom` needs the DOM, but the worker owns the canvas. Bridge with messages:

```js
// Main thread: transfer canvas, forward zoom transforms
const offscreen = canvas.transferControlToOffscreen();
const worker = new Worker("render-worker.js");
worker.postMessage({ canvas: offscreen, dpr: devicePixelRatio }, [offscreen]);

d3.select("svg.overlay").call(d3.zoom().on("zoom", ({ transform }) => {
  worker.postMessage({ type: "zoom", transform: { x: transform.x, y: transform.y, k: transform.k } });
}));
// Keep quadtree on main thread for instant hover — no round-trip latency
```

```js
// render-worker.js: receives canvas, draws on zoom messages
self.onmessage = ({ data }) => {
  if (data.canvas) { ctx = data.canvas.getContext("2d"); ctx.scale(data.dpr, data.dpr); return; }
  if (data.type === "zoom") { /* clear, translate, scale, batch-draw from typed arrays */ }
};
```

**Use when**: 50K+ points with visible interaction jank, or dashboards with multiple heavy canvases. **Don't use** if you need synchronous `getImageData` — the main thread can't read a transferred canvas. Gotchas: after transfer, `getContext()` on the original throws. DPR changes must be forwarded via message. No `document.fonts` in workers — pre-load fonts or use a text atlas.

## Zoom and Pan

Use `d3.zoom` on the SVG overlay, apply the transform to canvas coordinates:

```js
const zoom = d3.zoom().scaleExtent([0.5, 100]).on("zoom", ({ transform }) => {
  currentTransform = transform;
  markDirty();
});

function drawWithZoom(ctx, transform) {
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  drawAllPoints(ctx);
  ctx.restore();
}
```

Cull off-screen elements by inverting the transform to get the visible viewport in data coordinates: `x0 = -transform.x / transform.k`, etc. For quadtree-indexed data, `quadtree.visit()` efficiently enumerates only visible points. See `navigation` skill for semantic zoom, constraints, and minimap patterns.

## Level of Detail (LOD)

| Visible Points | Technique |
|---------------|-----------|
| < 500 | Full detail: sized circles, labels, tooltips |
| 500-10K | Colored dots, 2-4px, hover to identify |
| 10K-100K | 1px dots, batch-rendered, opacity scaled |
| 100K-1M | Density heatmap or binned hexagons |
| 1M+ | Aggregated tiles, progressive refinement |

Combine with zoom: zooming in reduces visible count, automatically increasing detail.

## Canvas Text and Texture Atlases

`ctx.fillText` is slow — each call rasterizes the font. Only label visible/selected items, cap at ~50 labels. For a fixed set of labels rendered many times, pre-render to a text atlas canvas and `drawImage` sub-regions.

Same pattern works for custom markers — pre-render each shape into cells of one offscreen canvas, stamp with `drawImage()`:

```js
function buildMarkerAtlas(categories, colorScale, size = 16) {
  const dpr = devicePixelRatio, cell = size * dpr;
  const atlas = new OffscreenCanvas(cell * categories.length, cell);
  const ctx = atlas.getContext("2d");
  categories.forEach((cat, i) => {
    ctx.fillStyle = colorScale(cat);
    ctx.beginPath();
    // Draw shape (circle, triangle, etc.) centered at (i*cell + cell/2, cell/2)
    ctx.arc(i * cell + cell / 2, cell / 2, cell * 0.35, 0, Math.PI * 2);
    ctx.fill();
  });
  return { atlas, cell, cssSize: size };
}
// Stamp: ctx.drawImage(atlas, col*cell, 0, cell, cell, x-half, y-half, size, size)
```

3-10x faster for custom markers; smaller gain for plain circles (`arc()` is already optimized). Rebuild on DPR change. Set `imageSmoothingEnabled = false` for pixel-perfect stamps. For 100K+ with custom markers, WebGL instanced rendering is the better path.

## GPU Escalation: When to Leave Canvas 2D

Canvas 2D is the right default for 1K-500K elements. When batching + culling + LOD can't hold 60fps:

| Data Scale | First Try | Escalate To | Why |
|-----------|-----------|-------------|-----|
| < 50K | Canvas 2D | — | Simple, debuggable, universal |
| 50K-500K | Canvas 2D + typed arrays + LOD | OffscreenCanvas if UI jank | Frees main thread |
| 500K-5M | Canvas 2D progressive render | regl / WebGL | GPU instanced draw, one draw call for all points |
| 5M+ | — | WebGPU | Compute shaders for GPU-side aggregation |

**regl** (~15KB): functional WebGL without the state machine. `regl-scatterplot` handles up to 20M points with D3 scale integration. **d3fc** provides D3-idiomatic WebGL series renderers. **WebGPU** (Chrome, Edge, Firefox, Safari 26+; ~70% global support) enables compute shaders for GPU-side binning/density and 10M+ point rendering. See `webgl` skill for shader patterns. **Observable Plot** uses Canvas internally for its raster mark — worth considering before hand-rolling a heatmap.

The escalation rule: **profile first, escalate only when measured performance requires it.**

## Accessibility

Canvas is a black box for screen readers. See `canvas-accessibility` for hidden DOM mirrors, `aria-activedescendant`, keyboard navigation, focus rings. See `data-table` for data table alternatives.

## Common Pitfalls

1. **Forgetting `moveTo` before `arc`** — without it, `arc` draws a connecting line from the previous point. Always `ctx.moveTo(x + r, y)` before `ctx.arc(x, y, r, ...)`.

2. **Clearing with wrong dimensions** — after DPR scaling, use CSS dimensions: `clearRect(0, 0, width, height)`, not `canvas.width, canvas.height`.

3. **Stale quadtree after data change** — `d3.quadtree` doesn't auto-update. Rebuild when data or scales change.

4. **Event coordinates mismatch** — always use `d3.pointer(event, canvas)` to get coordinates relative to the canvas.

5. **Overdrawing transparent shapes** — 10K translucent circles saturate to solid and kill performance. Use density heatmaps or bin first.

6. **Image smoothing for pixel art/heatmaps** — set `ctx.imageSmoothingEnabled = false` when drawing scaled ImageData.

7. **Leaking animation frames** — always `cancelAnimationFrame` before starting a new loop.

8. **`putImageData` ignores canvas transform** — writes pixels 1:1 to backing store. Create ImageData at physical pixel dimensions (`width * dpr x height * dpr`), not CSS dimensions.

9. **Too many `beginPath`/`fill` pairs** — batch shapes by style. One `beginPath`/`fill` per category, not per point.

10. **`ctx.save()`/`ctx.restore()` in tight loops** — pushes/pops the full state stack. Manually set only the properties you need.

11. **Shadow effects** — `ctx.shadowBlur` is extremely expensive. Fake shadows with pre-rendered sprites.

12. **Single path with 100K+ segments** — slower than breaking into chunks of ~10K.

## References

- [Canvas 2D API](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D) — MDN reference
- [D3 Quadtree](https://d3js.org/d3-quadtree) — spatial indexing for hit detection
- [d3.parcoords](https://github.com/syntagmatic/parallel-coordinates) — Canvas-for-data, SVG-for-interaction pattern at scale
- [Canvas Optimization](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas) — MDN performance guide
- [OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas) — worker-thread rendering
- [High-DPI Canvas](https://web.dev/articles/canvas-hidipi) — crisp rendering on Retina/HiDPI
- [It's always been you, Canvas2D](https://developer.chrome.com/blog/canvas2d) — modern Canvas 2D API additions
- [regl](https://github.com/regl-project/regl) — functional WebGL wrapper for GPU-accelerated rendering
- [regl-scatterplot](https://github.com/flekschas/regl-scatterplot) — D3-compatible WebGL scatter for up to 20M points
