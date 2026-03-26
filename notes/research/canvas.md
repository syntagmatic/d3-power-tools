# Canvas Rendering Research

Research date: 2026-03-25

## Current Coverage

The `skills/canvas/SKILL.md` covers:

- **Layer architecture** — stacked canvases (background, foreground, interaction, hit detection) with SVG overlay for axes/labels/tooltips
- **DPR handling** — `devicePixelRatio` scaling, `matchMedia` for display changes
- **Quadtree hit detection** — `d3.quadtree().find()` with radius, plus `visit()` for range queries
- **Geometric hit detection** — rectangle bounds testing, polar coordinate testing for arcs
- **Color-picking** — hidden canvas approach for irregular shapes
- **Typed arrays** — `Float32Array` for 100K+ points, zero-copy transfer to workers
- **Batched rendering** — group draw calls by visual style, minimize state changes
- **Frame budgeting** — dirty flag + `requestAnimationFrame` coalescing
- **Progressive rendering** — shuffled chunk queue for datasets exceeding frame budget
- **ImageData pixel operations** — direct pixel writes for heatmaps/density
- **Web Workers** — compute offloading (binning, layout, force ticks)
- **OffscreenCanvas** — brief mention of `transferControlToOffscreen`
- **Zoom/pan** — `d3.zoom` on SVG overlay, transform canvas coordinate system
- **Culling** — viewport bounds in data coordinates, quadtree-accelerated visibility
- **LOD** — detail levels by visible point count
- **Text rendering** — label capping, text atlas for repeated labels
- **Accessibility** — cross-reference to `canvas-accessibility` skill
- **11 common pitfalls** — moveTo before arc, DPR clearing, stale quadtree, etc.

**Gaps identified**: OffscreenCanvas is mentioned but not developed into a full pattern. No texture atlas/sprite pattern for markers. No guidance on when to escalate to WebGL or WebGPU. No coverage of newer Canvas 2D APIs (`roundRect`, `createConicGradient`, `desynchronized`). No `willReadFrequently` guidance beyond hit detection canvas mention.

---

## OffscreenCanvas + Workers

### What it adds

Move the entire draw loop off the main thread. The main thread stays free for DOM events, layout, and UI updates even during heavy renders (100K+ shapes, complex path operations). Measured gains: 30-50% improvement in input-to-paint latency for complex scenes; eliminates jank during initial render of large datasets.

### Browser support

All modern browsers: Chrome 69+, Firefox 105+, Safari 16.4+, Edge 79+. `transferControlToOffscreen()` has the same support. Safe to use without fallback in 2026.

### Two modes

1. **`new OffscreenCanvas(w, h)`** in a worker — for pre-rendering sprites, computing ImageData, generating tiles. Transfer the resulting `ImageBitmap` back to main thread.
2. **`canvas.transferControlToOffscreen()`** — transfers ownership of a DOM canvas to a worker. The worker draws directly; the compositor displays the result. Main thread cannot touch the canvas after transfer.

### D3 integration approach

The challenge: `d3.zoom`, `d3.brush`, and event handling live on the main thread (they need DOM events). The worker owns the canvas. Solution is a message-passing bridge:

```
Main thread                          Worker thread
─────────────                        ─────────────
d3.zoom → transform event    ──msg──→  receives transform
                                       ctx.save/translate/scale
                                       drawAllPoints(ctx)
                                       ctx.restore()
                                       commit() or implicit
```

The main thread captures interaction state (zoom transform, brush extent, hover coordinates) and posts it to the worker. The worker renders and the compositor displays. For hover/hit detection, either:
- Keep a quadtree on the main thread (requires duplicated position data)
- Post mouse coordinates to worker, worker does hit test, posts result back (adds 1-2 frames of latency)

### When to use vs main-thread Canvas

| Scenario | Recommendation |
|----------|---------------|
| < 50K points, simple shapes | Main thread is fine |
| 50K-500K points, or complex per-element paths | OffscreenCanvas if interaction latency matters |
| Heavy computation + rendering combined | Worker for compute, main thread for render |
| Dashboard with multiple heavy canvases | Each canvas in its own worker |
| Need synchronous hit detection on hover | Keep quadtree on main thread |

### Gotchas

- After `transferControlToOffscreen()`, calling `getContext()` on the original canvas throws.
- `d3.select(canvas)` and `d3.pointer(event, canvas)` still work on the DOM element for event coordinates.
- DPR changes need forwarding to the worker via message.
- No access to `document.fonts` in workers — pre-load fonts or use bitmap text.

Sources:
- [MDN OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas)
- [web.dev OffscreenCanvas guide](https://web.dev/articles/offscreen-canvas)
- [chrisprice/offscreen-canvas examples](https://github.com/chrisprice/offscreen-canvas/)
- [Enhancing Graphics Performance with OffscreenCanvas and D3.js](https://dev.to/jeevankishore/enhancing-graphics-performance-with-offscreencanvas-and-d3js-19ka)

---

## WebGPU Status

### Current state (March 2026)

WebGPU ships by default in Chrome, Edge, Firefox, and Safari (Safari 26+). Approximately 70% global browser support. Linux and Android support in Firefox expected mid-2026. This is now viable for progressive enhancement.

### What it enables for dataviz

- **Compute shaders for data processing**: binning, histogram aggregation, density estimation, force simulation ticks — all on the GPU. A compute shader can bin 10M points into a heatmap grid in under 1ms.
- **Massive point rendering**: 10M-point scatter plots at 45+ FPS on consumer hardware. 15-30x over Canvas 2D for point-heavy visualizations.
- **Render bundles**: pre-record draw commands, replay without CPU overhead. Good for static or slowly-changing backgrounds.
- **Instanced rendering**: draw millions of identical shapes (circles, squares, custom markers) with per-instance position/color/size from a GPU buffer.

### D3 integration approach

D3 handles data transforms, scales, and interaction. WebGPU handles rendering:

```
data → d3.scales → Float32Array of positions/colors → GPU buffer → render pipeline
d3.zoom → transform → uniform buffer update → re-render (no data re-upload)
```

No established D3+WebGPU library yet. The pattern is:
1. Use D3 scales to compute positions into typed arrays
2. Upload to GPU buffers
3. Write a simple vertex+fragment shader for the shape type
4. On zoom/pan, update a transform uniform — no re-upload of point data

### When to reach for it

| Scenario | Use WebGPU? |
|----------|------------|
| < 100K points | No — Canvas 2D is simpler and fast enough |
| 100K-1M points | Maybe — if Canvas 2D can't hold 60fps |
| 1M-10M+ points | Yes — Canvas 2D can't keep up |
| GPU-side aggregation (binning, density) | Yes — compute shaders avoid CPU→GPU round-trip |
| Need broad compatibility including older devices | No — fall back to WebGL or Canvas 2D |

### Caution

- API is verbose: shaders, pipelines, bind groups, buffer management
- Debugging is harder than Canvas 2D
- For 2D dataviz, WebGL via regl is a more pragmatic middle ground today
- Consider WebGPU when you need compute shaders or when WebGL performance is insufficient

Sources:
- [WebGPU 2026: 70% Browser Support](https://byteiota.com/webgpu-2026-70-browser-support-15x-performance-gains/)
- [WebGPU supported in major browsers](https://web.dev/blog/webgpu-supported-major-browsers)
- [WebGPU for Scalable Client-Side Aggregate Visualization (TU Wien)](https://www.cg.tuwien.ac.at/research/publications/2023/webGPU_aggregateVis-2023/)
- [Chrome GPU Compute guide](https://developer.chrome.com/docs/capabilities/web-apis/gpu-compute)
- [Surma: WebGPU — All of the cores, none of the canvas](https://surma.dev/things/webgpu/)

---

## Texture Atlases

### What it adds

Pre-render custom markers (circles, triangles, stars, icons) to a single offscreen canvas, then stamp them with `drawImage()` instead of running path commands per point. Eliminates per-element `beginPath/arc/fill` overhead.

### Performance gain

For custom markers (anything beyond simple circles), texture atlases are 3-10x faster than path-based rendering. The gain comes from replacing path commands with a single `drawImage` blit per point. For simple filled circles, the gain is smaller since `arc()` is already well-optimized.

### Implementation pattern for dataviz

```js
// 1. Build atlas: one row of markers, each in a cell
const atlas = document.createElement("canvas");
const cellSize = 32; // pixels, at current DPR
const categories = ["circle", "triangle", "square", "star", "diamond"];
atlas.width = cellSize * categories.length;
atlas.height = cellSize;
const actx = atlas.getContext("2d");

categories.forEach((shape, i) => {
  const cx = i * cellSize + cellSize / 2;
  const cy = cellSize / 2;
  actx.fillStyle = colorScale(shape);
  drawMarkerShape(actx, shape, cx, cy, cellSize * 0.4);
});

// 2. Stamp markers from atlas
function drawPoints(ctx, data) {
  for (const d of data) {
    const col = categoryIndex.get(d.category);
    ctx.drawImage(atlas,
      col * cellSize, 0, cellSize, cellSize,       // source rect
      d.x - cellSize/2, d.y - cellSize/2, cellSize, cellSize  // dest rect
    );
  }
}
```

### When to use

- Multiple marker shapes (scatter plot with category encoding)
- Custom icons or glyphs as data points
- Text labels rendered many times (text atlas)
- Shadow or glow effects (pre-render the expensive effect once)

### When NOT to use

- Uniform circles — `arc()` in a batched path is faster than `drawImage` per point
- Points that vary continuously in size — would need many atlas entries or scaling (which re-enables smoothing overhead)
- Very few distinct markers — the atlas overhead isn't worth it

### Gotchas

- Rebuild atlas when DPR changes (display switch)
- `drawImage` respects `imageSmoothingEnabled` — set to `false` for pixel-perfect markers
- Each `drawImage` call is independent (can't batch like path operations) — for 100K+ points, WebGL instanced rendering is better

Sources:
- [Canvas renderer with texture atlas (GitHub gist)](https://gist.github.com/cool-Blue/ea9be02dff5b6c3a18e2)
- [Texture atlas (Wikipedia)](https://en.wikipedia.org/wiki/Texture_atlas)

---

## regl and Lightweight WebGL

### What regl is

A functional WebGL wrapper that removes shared state. Instead of the WebGL state machine (bindBuffer, bindTexture, useProgram...), you declare draw commands as objects. ~15KB gzipped. Much less ceremony than raw WebGL, much lighter than Three.js.

### Performance gain

Canvas 2D tops out around 100K-500K points at 60fps (depending on shape complexity). regl handles 1M+ points with smooth zoom/pan. The key: GPU instanced rendering draws all points in one draw call with per-instance attributes (position, color, size) from typed array buffers.

### regl-scatterplot

The most mature D3+regl integration for dataviz. Handles up to 20M points. Key features:
- Accepts D3 x/y scales, auto-synchronizes on zoom/pan
- Lasso selection
- Point connections (for trajectories)
- Performance mode for 2M+ points
- ~30KB gzipped

### D3 integration pattern

```js
// D3 for scales + data, regl for rendering
const xScale = d3.scaleLinear().domain(d3.extent(data, d => d.x)).range([0, width]);
const yScale = d3.scaleLinear().domain(d3.extent(data, d => d.y)).range([height, 0]);

// Compute positions into typed array
const positions = new Float32Array(data.length * 2);
data.forEach((d, i) => {
  positions[i * 2] = xScale(d.x);
  positions[i * 2 + 1] = yScale(d.y);
});

// regl draw command (simplified)
const drawPoints = regl({
  vert: `
    attribute vec2 position;
    uniform mat3 transform;
    void main() { gl_Position = vec4((transform * vec3(position, 1)).xy, 0, 1); gl_PointSize = 3.0; }
  `,
  frag: `void main() { gl_FragColor = vec4(0.2, 0.5, 0.8, 0.6); }`,
  attributes: { position: positions },
  count: data.length,
  primitive: "points"
});
```

### When to reach for WebGL/regl vs Canvas 2D

| Data size | Shape complexity | Recommendation |
|-----------|-----------------|---------------|
| < 50K | Any | Canvas 2D |
| 50K-500K | Simple (circles, rects) | Canvas 2D with batching |
| 50K-500K | Complex (custom paths, text) | Consider regl |
| 500K-5M | Any | regl or WebGL |
| 5M+ | Points/simple | regl with performanceMode, or WebGPU |
| 5M+ | Complex shapes | WebGPU compute + render |

### Alternatives to regl

- **d3fc** — D3-idiomatic components with WebGL renderers for series types (line, bar, scatter, candlestick). Uses D3 scales directly. Good if you want a higher-level API.
- **deck.gl** — layer-based, handles millions of points with built-in interaction. Heavier (~200KB). Best for geospatial.
- **PIXI.js** — 2D WebGL renderer with scene graph. Good for node-link diagrams. Adds abstraction overhead.
- **Raw WebGL** — maximum control, maximum boilerplate. Only if regl doesn't cover your shader needs.

Sources:
- [An Intro to regl for Data Visualization](https://vallandingham.me/regl_intro.html)
- [Rendering One Million Datapoints with D3 and WebGL](https://blog.scottlogic.com/2020/05/01/rendering-one-million-points-with-d3.html)
- [regl-scatterplot](https://github.com/flekschas/regl-scatterplot)
- [Beautifully Animate Points with WebGL and regl](https://peterbeshai.com/blog/2017-05-26-beautifully-animate-points-with-webgl-and-regl/)
- [regl (GitHub)](https://github.com/regl-project/regl)

---

## Canvas 2D Performance Updates

### `willReadFrequently`

```js
const ctx = canvas.getContext("2d", { willReadFrequently: true });
```

Tells the browser to keep the backing store in CPU memory for fast `getImageData()` reads. Cuts read time from ~3ms to ~1ms. **But**: disables GPU acceleration, adding 35+ms penalty to draw operations.

**Use it for**: hit-detection canvas (hidden, drawn once, read on every hover). Color-picking canvases. ImageData-based heatmap generation.

**Never use it for**: the main rendering canvas. The write penalty far outweighs the read benefit for anything that redraws frequently.

The current SKILL.md already mentions this for hit detection canvas but could be more explicit about the trade-off.

### `desynchronized`

```js
const ctx = canvas.getContext("2d", { desynchronized: true });
```

Bypasses the compositor, reducing input-to-display latency by 1-2 frames. The canvas paints directly to the screen buffer. May introduce tearing artifacts.

**Use it for**: drawing/inking applications, real-time cursor trails. Potentially useful for smooth panning of large datasets where latency matters more than perfect frame consistency.

**Not recommended for**: most dataviz. The tearing artifacts are distracting, and the latency improvement is marginal compared to good frame budgeting.

### `roundRect()`

```js
ctx.roundRect(x, y, width, height, [5]); // single radius
ctx.roundRect(x, y, width, height, [5, 10, 15, 20]); // per-corner
```

Native rounded rectangles — no more manual `arcTo` or `quadraticCurveTo` sequences. Supported in all modern browsers (Chrome 99+, Firefox 112+, Safari 15.4+). Useful for bar charts with rounded tops, card-style nodes, tooltip backgrounds.

### `createConicGradient()`

```js
const gradient = ctx.createConicGradient(0, cx, cy);
gradient.addColorStop(0, "red");
gradient.addColorStop(0.5, "blue");
gradient.addColorStop(1, "red");
ctx.fillStyle = gradient;
```

Conic (angular) gradients on Canvas, matching CSS `conic-gradient()`. Useful for gauge charts, radial heatmaps, and pie-chart-style continuous gradients. All modern browsers.

### `reset()`

```js
ctx.reset(); // clears canvas AND resets all state
```

Replaces the common `ctx.clearRect(0, 0, w, h)` + manual state reset pattern. Chrome 99+, Firefox 113+, Safari 15.4+.

### `context.letterSpacing` and `context.wordSpacing`

Fine-grained text spacing control, matching CSS properties. Useful for fitting labels into constrained spaces.

Sources:
- [Chrome blog: It's always been you, Canvas2D](https://developer.chrome.com/blog/canvas2d)
- [Browser lied, performance died (willReadFrequently deep dive)](https://stuff.tamius.net/sacred-texts/2025/04/27/browser-lied-performance-died-a-bit-about-html-canvas-2d-context-and-why-you-should-read-the-docs/)
- [willReadFrequently analysis](https://www.schiener.io/2024-08-02/canvas-willreadfrequently)
- [Canvas 2D spec: willReadFrequently](https://github.com/fserb/canvas2D/blob/master/spec/will-read-frequently.md)
- [MDN roundRect](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/roundRect)
- [MDN createConicGradient](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/createConicGradient)

---

## Decision Guidance

### Rendering technology ladder

```
Data size / complexity →

            Canvas 2D          OffscreenCanvas        WebGL/regl         WebGPU
           ┌─────────────────┬──────────────────────┬─────────────────┬──────────────┐
 < 1K      │ SVG is fine     │                      │                 │              │
           │                 │                      │                 │              │
 1K-50K    │ Canvas 2D       │                      │                 │              │
           │ batched paths   │                      │                 │              │
           │                 │                      │                 │              │
 50K-500K  │ Canvas 2D       │ + OffscreenCanvas    │                 │              │
           │ typed arrays    │   if UI jank         │                 │              │
           │ LOD + culling   │                      │                 │              │
           │                 │                      │                 │              │
 500K-5M   │ progressive     │ OffscreenCanvas      │ regl / d3fc     │              │
           │ render queue    │ for background       │ WebGL series    │              │
           │                 │                      │                 │              │
 5M+       │                 │                      │ regl perf mode  │ WebGPU       │
           │                 │                      │ instanced draw  │ compute +    │
           │                 │                      │                 │ render       │
           └─────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### Decision factors beyond data size

| Factor | Guidance |
|--------|----------|
| Custom marker shapes | Texture atlas (Canvas 2D) or instanced rendering (WebGL) |
| GPU-side aggregation | WebGPU compute shaders |
| Broad device support | Canvas 2D (universal) > WebGL (98%+) > WebGPU (~70%) |
| Interaction complexity | Canvas 2D easier; WebGL needs separate hit detection |
| Development speed | Canvas 2D >> regl > raw WebGL >> WebGPU |
| Team familiarity | Stay with Canvas 2D unless performance demands escalation |
| Multiple coordinated views | OffscreenCanvas per view, each in own worker |

### The escalation rule

Start with Canvas 2D. Profile. If you can't hold 60fps with batching + culling + LOD:
1. Try OffscreenCanvas to free the main thread
2. Try regl/WebGL for GPU-accelerated rendering
3. Try WebGPU if you need compute shaders or 10M+ points

Each step adds complexity. Only escalate when measured performance requires it.

---

## Code Patterns

### OffscreenCanvas with d3.zoom bridge

```js
// main.js
const canvas = document.querySelector("canvas");
const offscreen = canvas.transferControlToOffscreen();
const worker = new Worker("render-worker.js");
worker.postMessage({ canvas: offscreen, dpr: devicePixelRatio }, [offscreen]);

// D3 zoom on a transparent SVG overlay
const svg = d3.select("svg.overlay");
const zoom = d3.zoom().on("zoom", ({ transform }) => {
  worker.postMessage({ type: "zoom", transform: { x: transform.x, y: transform.y, k: transform.k } });
});
svg.call(zoom);

// Hover: main-thread quadtree for instant response
svg.on("pointermove", (event) => {
  const [mx, my] = d3.pointer(event);
  const nearest = quadtree.find(mx, my, 20);
  // highlight on a separate main-thread canvas or SVG element
});
```

```js
// render-worker.js
let ctx, width, height, dpr;

self.onmessage = ({ data }) => {
  if (data.canvas) {
    const canvas = data.canvas;
    dpr = data.dpr;
    width = canvas.width / dpr;
    height = canvas.height / dpr;
    ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    return;
  }
  if (data.type === "zoom") {
    render(data.transform);
  }
  if (data.type === "data") {
    positions = new Float32Array(data.positions);
    render(currentTransform);
  }
};

function render(transform) {
  currentTransform = transform;
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  // batch draw from typed arrays
  ctx.beginPath();
  for (let i = 0; i < positions.length; i += 2) {
    const x = positions[i], y = positions[i + 1];
    ctx.moveTo(x + 2, y);
    ctx.arc(x, y, 2, 0, Math.PI * 2);
  }
  ctx.fillStyle = "steelblue";
  ctx.fill();
  ctx.restore();
}
```

### Texture atlas for categorical markers

```js
function buildMarkerAtlas(categories, colorScale, size = 16) {
  const dpr = devicePixelRatio;
  const cell = size * dpr;
  const atlas = new OffscreenCanvas(cell * categories.length, cell);
  const ctx = atlas.getContext("2d");

  const shapes = {
    circle: (ctx, cx, cy, r) => { ctx.arc(cx, cy, r, 0, Math.PI * 2); },
    square: (ctx, cx, cy, r) => { ctx.rect(cx - r, cy - r, r * 2, r * 2); },
    triangle: (ctx, cx, cy, r) => {
      ctx.moveTo(cx, cy - r);
      ctx.lineTo(cx + r * 0.866, cy + r * 0.5);
      ctx.lineTo(cx - r * 0.866, cy + r * 0.5);
      ctx.closePath();
    },
    diamond: (ctx, cx, cy, r) => {
      ctx.moveTo(cx, cy - r); ctx.lineTo(cx + r, cy);
      ctx.lineTo(cx, cy + r); ctx.lineTo(cx - r, cy); ctx.closePath();
    }
  };

  const index = new Map();
  categories.forEach((cat, i) => {
    const cx = i * cell + cell / 2, cy = cell / 2, r = cell * 0.35;
    ctx.fillStyle = colorScale(cat);
    ctx.beginPath();
    (shapes[cat] || shapes.circle)(ctx, cx, cy, r);
    ctx.fill();
    index.set(cat, i);
  });

  return { atlas, cell, index, cssSize: size };
}

function drawWithAtlas(ctx, data, atlas, xScale, yScale) {
  const { atlas: img, cell, index, cssSize } = atlas;
  const half = cssSize / 2;
  for (const d of data) {
    const col = index.get(d.category);
    ctx.drawImage(img,
      col * cell, 0, cell, cell,
      xScale(d.x) - half, yScale(d.y) - half, cssSize, cssSize
    );
  }
}
```

### willReadFrequently for hit detection canvas

```js
// Dedicated hit-detection canvas — never displayed
const hitCanvas = document.createElement("canvas");
hitCanvas.width = width * dpr;
hitCanvas.height = height * dpr;
const hitCtx = hitCanvas.getContext("2d", { willReadFrequently: true });
hitCtx.scale(dpr, dpr);

// Assign unique color per element
const colorToData = new Map();
function uniqueColor(i) {
  const r = (i >> 16) & 0xFF, g = (i >> 8) & 0xFF, b = i & 0xFF;
  return `rgb(${r},${g},${b})`;
}
data.forEach((d, i) => {
  const color = uniqueColor(i + 1); // avoid black (0,0,0)
  colorToData.set(color, d);
  hitCtx.fillStyle = color;
  hitCtx.beginPath();
  // draw same shape as visible canvas
  hitCtx.arc(xScale(d.x), yScale(d.y), hitRadius, 0, Math.PI * 2);
  hitCtx.fill();
});

// Lookup on hover
canvas.addEventListener("pointermove", (e) => {
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) * dpr;
  const y = (e.clientY - rect.top) * dpr;
  const pixel = hitCtx.getImageData(x, y, 1, 1).data;
  const key = `rgb(${pixel[0]},${pixel[1]},${pixel[2]})`;
  const hit = colorToData.get(key);
});
```
