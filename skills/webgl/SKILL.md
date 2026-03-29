---
name: webgl
description: "High-performance WebGL rendering patterns for D3.js visualizations. Use this skill whenever the user needs to render 100K–10M+ data points, build GPU-accelerated scatter plots or particle visualizations, use instanced rendering for large datasets, implement WebGL-based heatmaps or density plots, integrate D3 scales/layouts with WebGL rendering, or hit performance limits with Canvas 2D. Also use when the user mentions WebGL, GPU rendering, shaders, instanced drawing, vertex buffers, or wants to push a D3 visualization well beyond what Canvas 2D can handle."
---

# WebGL Rendering with D3

You probably don't need WebGL. Canvas 2D with batched drawing handles 100K points at 60fps on most hardware (see `canvas` skill). WebGL becomes worth its complexity when Canvas genuinely can't keep up — animated 500K+ point clouds, real-time updates to millions of elements, or rendering where per-frame buffer uploads to the GPU are cheaper than per-element Canvas draw calls.

## When WebGL Earns Its Complexity

| Scale | Renderer | Why |
|-------|----------|-----|
| < 50K | Canvas 2D | Simpler API, easy debugging, good enough perf |
| 50K–500K | Canvas 2D with batching | Tight draw loop + quadtree. See `canvas` skill |
| 500K+ static | WebGL | Canvas draw calls become the bottleneck — each one crosses the JS→GPU boundary separately, while WebGL uploads all positions in one buffer and draws them in a single call |
| 500K+ animated | WebGL + instanced rendering | One draw call for millions of shapes. The GPU does per-element work in parallel that Canvas does sequentially |
| Shaped marks at scale | WebGL instanced | `gl.POINTS` is limited to circles and has GPU-dependent size caps (~64–256px). Instanced quads give you arbitrary shapes |

The cost of WebGL: shader debugging is painful (no breakpoints, cryptic errors), buffer management is manual, and every visualization needs a compile-link-upload cycle that Canvas doesn't. Only pay this cost when you've measured Canvas falling below your frame budget.

## When Not to Use WebGL

- **Under 500K elements** — Canvas 2D handles this fine. Profile before reaching for WebGL.
- **Complex per-element styling** — gradients, text, dashed lines are trivial in Canvas, painful in shaders.
- **Accessibility matters** — WebGL is invisible to screen readers. Both Canvas and WebGL need a hidden DOM mirror (see `canvas-accessibility`), but WebGL makes it harder.
- **Quick prototyping** — the boilerplate-to-insight ratio is terrible for exploration. Start with Canvas, port to WebGL only if you hit a wall.
- **Small multiples** — browsers limit you to ~8–16 WebGL contexts. Use Canvas for trellis layouts; use scissor rects if you must have WebGL.

## Architecture: D3 + WebGL Hybrid

```
┌─────────────────────────────────────┐
│  SVG overlay (pointer-events)        │  ← axes, labels, tooltips, brushes
│  Canvas: interaction highlight       │  ← hover ring, selection
│  WebGL canvas (data layer)           │  ← 500K–10M points/shapes
│  Container div (position:relative)   │
└─────────────────────────────────────┘
```

SVG captures pointer events, WebGL has `pointer-events: none`. For DPR-aware canvas/SVG layer setup, see `canvas` skill. Use `webgl2` — all modern browsers support it. Gives instanced rendering and VAOs natively, without the extension juggling WebGL1 required.

## The Minimal Shader Pair

Most data viz needs just: position points, color them. This vertex+fragment pair is the starting point for nearly every WebGL D3 visualization.

```glsl
// vertex — converts D3 CSS-pixel positions to WebGL clip space
#version 300 es
in vec2 a_position;  // CSS pixels, pre-scaled by D3
in vec4 a_color;     // RGBA [0,1]
in float a_size;     // point radius in pixels
uniform vec2 u_resolution;
uniform float u_dpr;
out vec4 v_color;

void main() {
  vec2 clip = (a_position / u_resolution) * 2.0 - 1.0;
  clip.y = -clip.y;  // CSS Y-down → WebGL Y-up
  gl_Position = vec4(clip, 0.0, 1.0);
  gl_PointSize = a_size * u_dpr;
  v_color = a_color;
}
```

```glsl
// fragment — antialiased circle via SDF on gl_PointCoord
#version 300 es
precision mediump float;
in vec4 v_color;
out vec4 fragColor;

void main() {
  float dist = length(gl_PointCoord - 0.5);
  if (dist > 0.5) discard;
  // smoothstep gives 1px antialiased edge without MSAA cost
  fragColor = vec4(v_color.rgb, v_color.a * (1.0 - smoothstep(0.4, 0.5, dist)));
}
```

## Scatter Plot: The Core Pattern

D3 computes positions with scales, you pack them into typed arrays, upload once, draw in a single GPU call.

```js
// D3 scales → typed arrays → GPU
const x = d3.scaleLinear(d3.extent(data, d => d.x), [margin.left, width - margin.right]);
const y = d3.scaleLinear(d3.extent(data, d => d.y), [height - margin.bottom, margin.top]);
const color = d3.scaleOrdinal(d3.schemeTableau10);

const n = data.length;
const positions = new Float32Array(n * 2), colors = new Float32Array(n * 4), sizes = new Float32Array(n);
for (let i = 0; i < n; i++) {
  positions[i*2] = x(data[i].x); positions[i*2+1] = y(data[i].y);
  const c = d3.rgb(color(data[i].category));
  colors[i*4] = c.r/255; colors[i*4+1] = c.g/255; colors[i*4+2] = c.b/255; colors[i*4+3] = 0.7;
  sizes[i] = 4;
}

// Helper — reduces the repetitive bind/upload/attribPointer cycle
function attribBuffer(gl, program, name, data, size, usage = gl.STATIC_DRAW) {
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, data, usage);
  const loc = gl.getAttribLocation(program, name);
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
  return buf;
}

// VAO groups all attribute bindings; one draw call for all n points
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);
attribBuffer(gl, program, "a_position", positions, 2);
attribBuffer(gl, program, "a_color", colors, 4);
attribBuffer(gl, program, "a_size", sizes, 1);

gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
gl.useProgram(program); gl.bindVertexArray(vao);
gl.uniform2f(gl.getUniformLocation(program, "u_resolution"), width, height);
gl.uniform1f(gl.getUniformLocation(program, "u_dpr"), devicePixelRatio);
gl.drawArrays(gl.POINTS, 0, n);
```

## Instanced Rendering: Beyond Points

`gl.POINTS` has GPU-dependent size limits (~64–256px) and only draws circles. Instanced rendering defines a template shape once and draws it N times with per-instance attributes — still a single draw call.

```glsl
#version 300 es
in vec2 a_quad;     // template: [-0.5, 0.5] unit square (6 vertices, 2 triangles)
in vec2 a_offset;   // per-instance: center position from D3 scale
in vec2 a_scale;    // per-instance: width, height in CSS pixels
in vec4 a_color;    // per-instance
uniform vec2 u_resolution;
out vec4 v_color;

void main() {
  vec2 pos = a_quad * a_scale + a_offset;
  vec2 clip = (pos / u_resolution) * 2.0 - 1.0;
  clip.y = -clip.y;
  gl_Position = vec4(clip, 0.0, 1.0);
  v_color = a_color;
}
```

```js
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);
attribBuffer(gl, program, "a_quad", new Float32Array([
  -0.5,-0.5, 0.5,-0.5, 0.5,0.5, -0.5,-0.5, 0.5,0.5, -0.5,0.5
]), 2);
// Per-instance attributes — divisor(1) advances once per instance, not per vertex
for (const [name, data, size] of [["a_offset", offsets, 2], ["a_scale", scales, 2], ["a_color", colors, 4]]) {
  attribBuffer(gl, program, name, data, size, gl.DYNAMIC_DRAW);
  gl.vertexAttribDivisor(gl.getAttribLocation(program, name), 1);
}
gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, instanceCount);
```

## Zoom and Pan

D3 zoom on SVG overlay, pass transform to WebGL as uniforms. No buffer re-upload needed.

```glsl
uniform vec2 u_translate;
uniform float u_scale;
// In main(): pos = pos * u_scale + u_translate; before clip conversion
```

```js
d3.zoom().scaleExtent([0.5, 100]).on("zoom", ({ transform }) => {
  gl.useProgram(program);
  gl.uniform2f(gl.getUniformLocation(program, "u_translate"), transform.x, transform.y);
  gl.uniform1f(gl.getUniformLocation(program, "u_scale"), transform.k);
  draw();  // Just re-render, no data re-upload
});
```

## Hit Detection

### Quadtree — same as Canvas, works up to ~1M points

```js
const qt = d3.quadtree().x(d => x(d.x)).y(d => y(d.y)).addAll(data);
svg.on("pointermove", event => {
  const [mx, my] = d3.pointer(event);
  const tx = (mx - transform.x) / transform.k, ty = (my - transform.y) / transform.k;
  highlight(qt.find(tx, ty, 20 / transform.k));
});
```

### GPU picking — for when quadtree is too slow or shapes overlap

Render each element with a unique color ID to an offscreen framebuffer, read back the pixel under the pointer. Supports 16M elements via RGB encoding.

```js
const indexToColor = i => [((i+1)&0xFF)/255, (((i+1)>>8)&0xFF)/255, (((i+1)>>16)&0xFF)/255, 1.0];

function pick(gl, fb, mx, my, h) {
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  const px = new Uint8Array(4);
  gl.readPixels(mx * devicePixelRatio, (h - my) * devicePixelRatio, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  return (px[0] | (px[1] << 8) | (px[2] << 16)) - 1;  // -1 = no hit
}
```

Re-render the picking buffer when positions change (zoom, filter), not on every mousemove.

## Brush-Linked Filtering

Update a per-element visibility attribute via `bufferSubData` instead of rebuilding the entire buffer — one float per element instead of repacking all positions and colors.

```js
const visibility = new Float32Array(n).fill(1.0);
const visBuf = attribBuffer(gl, program, "a_visibility", visibility, 1, gl.DYNAMIC_DRAW);

function onBrush([x0, x1]) {
  for (let i = 0; i < n; i++) visibility[i] = (data[i].x >= x0 && data[i].x <= x1) ? 1.0 : 0.1;
  gl.bindBuffer(gl.ARRAY_BUFFER, visBuf);
  gl.bufferSubData(gl.ARRAY_BUFFER, 0, visibility);
  draw();
}
// Vertex shader: v_visibility = a_visibility;
// Fragment shader: fragColor.a *= v_visibility;
```

## Lines and Polylines

`gl.lineWidth` is capped at 1px on most hardware. For thick lines, use instanced quads rotated along each segment:

```glsl
// Per-instance: a_p0 (start), a_p1 (end), a_color
vec2 dir = a_p1 - a_p0; float len = length(dir);
vec2 unit = dir / max(len, 0.001), normal = vec2(-unit.y, unit.x);
vec2 pos = a_p0 + unit * (a_quad.x + 0.5) * len + normal * a_quad.y * u_lineWidth;
```

## Regl

[regl](http://regl.party/) wraps buffer management, shader compilation, and state tracking in a functional API. Removes boilerplate without hiding the mental model. Use when you want WebGL performance without managing raw GL state; skip when you need fine-grained control over framebuffers or multi-pass rendering.

## Accessibility

WebGL is invisible to assistive technology. See `canvas-accessibility` for hidden DOM mirrors and keyboard nav. See `data-table` for data table alternatives.

## WebGPU

As of March 2026, WebGPU ships in Chrome, Firefox 141+, Safari 26+, and Edge; mobile remains fragmented. The key upgrade is **compute shaders** for GPU-side data processing (binning, aggregation, force simulation) without round-tripping to JS. For draw-call bottlenecks (the common case this skill addresses), WebGL 2 with instanced rendering is already sufficient. Stay on WebGL 2 unless you need GPU-side data transformation; if you do, consider luma.gl v9 for a portable abstraction or raw WebGPU for compute shaders.

## Common Pitfalls

1. **Y-axis flip** — WebGL is Y-up, CSS/D3 is Y-down. Always `clip.y = -clip.y`. Forgetting this produces upside-down charts that look plausible until you check axis alignment.

2. **Forgetting DPR** — point sizes and line widths must scale by `devicePixelRatio` in the shader. Canvas handles this with `ctx.scale(dpr, dpr)`; in WebGL you do it yourself.

3. **Context loss** — GPU reset or tab backgrounding can destroy your context silently:
   ```js
   canvas.addEventListener("webglcontextlost", e => e.preventDefault());
   canvas.addEventListener("webglcontextrestored", () => reinitialize());
   ```

4. **Too many contexts** — browsers limit WebGL contexts to ~8–16 total. One per visualization, never per layer. For small multiples, use scissor rects within a single context.

5. **Buffer upload stalls** — `bufferSubData` can block if the GPU is still reading the buffer. For animated data, double-buffer: alternate between two GPU buffers so you're never writing to one the GPU is reading.

## References

- [WebGL Fundamentals](https://webglfundamentals.org/) — Gregg Tavares
- [regl](https://github.com/regl-project/regl) — Mikola Lysenko's functional WebGL wrapper
- [deck.gl](https://deck.gl/) — Uber's WebGL/WebGPU viz framework (good for seeing patterns, overkill as a dependency for custom D3 work)
- [WebGPU Fundamentals](https://webgpufundamentals.org/) — Gregg Tavares
