---
name: webgl-rendering
description: "High-performance WebGL rendering patterns for D3.js visualizations. Use this skill whenever the user needs to render 100K–10M+ data points, build GPU-accelerated scatter plots or particle visualizations, use instanced rendering for large datasets, implement WebGL-based heatmaps or density plots, integrate D3 scales/layouts with WebGL rendering, or hit performance limits with Canvas 2D. Also use when the user mentions WebGL, GPU rendering, shaders, instanced drawing, vertex buffers, or wants to push a D3 visualization well beyond what Canvas 2D can handle."
---

# WebGL Rendering with D3

GPU-accelerated rendering for datasets too large for Canvas 2D. D3 handles data, scales, and layouts; WebGL handles the pixels.

## When to Use WebGL vs. Canvas 2D

| Scale | Renderer | Why |
|-------|----------|-----|
| < 10K | Canvas 2D | Simpler API, good enough perf |
| 10K–100K | Canvas 2D with batching | See `canvas` skill |
| 100K–1M | WebGL | Canvas draw calls become bottleneck |
| 1M–10M+ | WebGL + instanced rendering | One draw call for millions of shapes |

## Architecture: D3 + WebGL Hybrid

```
┌─────────────────────────────────────┐
│  SVG overlay (pointer-events)        │  ← axes, labels, tooltips, brushes
│  Canvas: interaction highlight       │  ← hover ring, selection
│  WebGL canvas (data layer)           │  ← 100K–10M points/shapes
│  Container div (position:relative)   │
└─────────────────────────────────────┘
```

SVG captures pointer events, WebGL has `pointer-events: none`. For DPR-aware canvas/SVG layer setup, see `canvas` skill.

```js
const gl = canvas.getContext("webgl2", { antialias: true, premultipliedAlpha: false, alpha: true });
gl.viewport(0, 0, width * devicePixelRatio, height * devicePixelRatio);
```

Use `webgl2` — all modern browsers support it, gives instanced rendering and VAOs without extensions.

## Shader Fundamentals

Most data viz needs just: position points, color them.

### Vertex + Fragment shader pair

```glsl
// vertex
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
// fragment — antialiased circle points
#version 300 es
precision mediump float;
in vec4 v_color;
out vec4 fragColor;

void main() {
  float dist = length(gl_PointCoord - 0.5);
  if (dist > 0.5) discard;
  fragColor = vec4(v_color.rgb, v_color.a * (1.0 - smoothstep(0.4, 0.5, dist)));
}
```

### Compile and link

```js
function createProgram(gl, vertSrc, fragSrc) {
  function compile(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.error(gl.getShaderInfoLog(s)); gl.deleteShader(s); return null; }
    return s;
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, compile(gl.VERTEX_SHADER, vertSrc));
  gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fragSrc));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { console.error(gl.getProgramInfoLog(prog)); return null; }
  return prog;
}
```

## Scatter Plot: The Core Pattern

### Step 1: D3 computes positions

```js
const x = d3.scaleLinear(d3.extent(data, d => d.x), [margin.left, width - margin.right]);
const y = d3.scaleLinear(d3.extent(data, d => d.y), [height - margin.bottom, margin.top]);
const color = d3.scaleOrdinal(d3.schemeTableau10);
```

### Step 2: Pack into typed arrays

```js
const n = data.length;
const positions = new Float32Array(n * 2), colors = new Float32Array(n * 4), sizes = new Float32Array(n);
for (let i = 0; i < n; i++) {
  positions[i*2] = x(data[i].x); positions[i*2+1] = y(data[i].y);
  const c = d3.rgb(color(data[i].category));
  colors[i*4] = c.r/255; colors[i*4+1] = c.g/255; colors[i*4+2] = c.b/255; colors[i*4+3] = 0.7;
  sizes[i] = 4;
}
```

### Step 3: Upload and draw — helper to reduce buffer boilerplate

```js
function attribBuffer(gl, program, name, data, size, usage = gl.STATIC_DRAW) {
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, data, usage);
  const loc = gl.getAttribLocation(program, name);
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
  return buf;
}

// Setup
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);
attribBuffer(gl, program, "a_position", positions, 2);
attribBuffer(gl, program, "a_color", colors, 4);
attribBuffer(gl, program, "a_size", sizes, 1);

// Draw — one GPU call for all n points
gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
gl.useProgram(program); gl.bindVertexArray(vao);
gl.uniform2f(gl.getUniformLocation(program, "u_resolution"), width, height);
gl.uniform1f(gl.getUniformLocation(program, "u_dpr"), devicePixelRatio);
gl.drawArrays(gl.POINTS, 0, n);
```

## Instanced Rendering: Beyond Points

`gl.POINTS` has size limits (~64–256px depending on GPU). For arbitrary shapes, use instanced rendering: define a template quad once, draw it N times.

### Instance vertex shader

```glsl
#version 300 es
in vec2 a_quad;     // template: [-0.5, 0.5] unit square
in vec2 a_offset;   // per-instance: center position
in vec2 a_scale;    // per-instance: width, height
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

### Setup — template quad + per-instance attributes

```js
const vao = gl.createVertexArray();
gl.bindVertexArray(vao);

// Template quad (two triangles)
attribBuffer(gl, program, "a_quad", new Float32Array([
  -0.5,-0.5, 0.5,-0.5, 0.5,0.5, -0.5,-0.5, 0.5,0.5, -0.5,0.5
]), 2);

// Per-instance attributes — use vertexAttribDivisor(loc, 1) for each
for (const [name, data, size] of [["a_offset", offsets, 2], ["a_scale", scales, 2], ["a_color", colors, 4]]) {
  const buf = attribBuffer(gl, program, name, data, size, gl.DYNAMIC_DRAW);
  gl.vertexAttribDivisor(gl.getAttribLocation(program, name), 1); // ← per instance
}

gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, instanceCount);
```

### Interleaved buffers — better GPU cache performance

Pack all per-instance data into one buffer `[x, y, w, h, r, g, b, a]` (8 floats = 32 bytes stride), use `vertexAttribPointer` with stride/offset.

```js
const STRIDE = 8, byteStride = STRIDE * 4;
const buf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buf);
gl.bufferData(gl.ARRAY_BUFFER, interleaved, gl.DYNAMIC_DRAW);
gl.vertexAttribPointer(offsetLoc, 2, gl.FLOAT, false, byteStride, 0);
gl.vertexAttribPointer(scaleLoc,  2, gl.FLOAT, false, byteStride, 8);
gl.vertexAttribPointer(colorLoc,  4, gl.FLOAT, false, byteStride, 16);
```

## Zoom and Pan

D3 zoom on SVG overlay, pass transform to WebGL as uniforms:

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
  draw();
});
```

## Hit Detection

### Quadtree — same as canvas

```js
const qt = d3.quadtree().x(d => x(d.x)).y(d => y(d.y)).addAll(data);
svg.on("pointermove", event => {
  const [mx, my] = d3.pointer(event);
  const tx = (mx - transform.x) / transform.k, ty = (my - transform.y) / transform.k;
  highlight(qt.find(tx, ty, 20 / transform.k));
});
```

### GPU picking — render unique color IDs to offscreen framebuffer

```js
function setupPickingFB(gl, w, h) {
  const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w * devicePixelRatio, h * devicePixelRatio, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  return fb;
}

// Encode index as RGB (supports 16M elements)
const indexToColor = i => [((i+1)&0xFF)/255, (((i+1)>>8)&0xFF)/255, (((i+1)>>16)&0xFF)/255, 1.0];

// Read pixel at pointer
function pick(gl, fb, mx, my, h) {
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  const px = new Uint8Array(4);
  gl.readPixels(mx * devicePixelRatio, (h - my) * devicePixelRatio, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  const id = px[0] | (px[1] << 8) | (px[2] << 16);
  return id > 0 ? id - 1 : -1;
}
```

Re-render picking buffer on position changes, not every mousemove.

## Dynamic Buffer Updates

```js
gl.bindBuffer(gl.ARRAY_BUFFER, buf);
gl.bufferSubData(gl.ARRAY_BUFFER, 0, newData);  // partial update, same size
gl.bufferData(gl.ARRAY_BUFFER, newData, gl.DYNAMIC_DRAW);  // full rewrite, size change
```

### Brush-linked filtering — update visibility attribute instead of rebuilding buffers

```js
// Add a per-instance visibility attribute (1.0 = visible, 0.1 = dimmed)
const visibility = new Float32Array(n).fill(1.0);
const visBuf = attribBuffer(gl, program, "a_visibility", visibility, 1, gl.DYNAMIC_DRAW);

function onBrush([x0, x1]) {
  for (let i = 0; i < n; i++) visibility[i] = (data[i].x >= x0 && data[i].x <= x1) ? 1.0 : 0.1;
  gl.bindBuffer(gl.ARRAY_BUFFER, visBuf);
  gl.bufferSubData(gl.ARRAY_BUFFER, 0, visibility);
  draw();
}
// Vertex shader: in float a_visibility; out float v_visibility; ... v_visibility = a_visibility;
// Fragment shader: fragColor.a *= v_visibility;
```

## Lines and Polylines

`gl.lineWidth` is capped at 1px on most hardware. For thick lines, use instanced quads rotated along segments:

```glsl
// Per-instance: a_p0 (start), a_p1 (end), a_color
// In vertex shader:
vec2 dir = a_p1 - a_p0; float len = length(dir);
vec2 unit = dir / max(len, 0.001), normal = vec2(-unit.y, unit.x);
vec2 pos = a_p0 + unit * (a_quad.x + 0.5) * len + normal * a_quad.y * u_lineWidth;
```

For polylines (N points → N-1 segments), pack consecutive point pairs as instance data.

## Texture Atlases for Glyphs

Draw D3 symbols to a canvas, upload as texture. Sample by per-instance `a_glyphIndex`:

```js
function createGlyphAtlas(gl, symbols, size = 32) {
  const canvas = document.createElement("canvas");
  canvas.width = symbols.length * size; canvas.height = size;
  const ctx = canvas.getContext("2d");
  symbols.forEach((sym, i) => {
    ctx.save(); ctx.translate(i * size + size/2, size/2);
    ctx.fill(new Path2D(d3.symbol().type(sym).size(size * size * 0.4)()));
    ctx.restore();
  });
  const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
  gl.generateMipmap(gl.TEXTURE_2D);
  return tex;
}
```

## Cleanup

```js
function cleanup(gl, { buffers, textures, framebuffers, program }) {
  buffers.forEach(b => gl.deleteBuffer(b));
  textures.forEach(t => gl.deleteTexture(t));
  framebuffers.forEach(f => gl.deleteFramebuffer(f));
  gl.deleteProgram(program);
  gl.getExtension("WEBGL_lose_context")?.loseContext();
}
```

## Regl: Pragmatic Shortcut

[regl](http://regl.party/) wraps buffer management, shader compilation, and state tracking:

```js
const regl = createRegl(glCanvas);
const drawPoints = regl({
  vert: `...`, frag: `...`,  // same shaders as above
  attributes: { position: regl.prop("positions"), color: regl.prop("colors"), size: regl.prop("sizes") },
  uniforms: { resolution: [width, height] },
  count: regl.prop("count"), primitive: "points",
  blend: { enable: true, func: { srcRGB: "src alpha", dstRGB: "one minus src alpha" } },
});
drawPoints({ positions, colors, sizes, count: n });
```

Use regl when you want WebGL perf without managing raw GL state. Skip for fine-grained framebuffer or compute-like passes.

## Accessibility

WebGL is invisible to assistive technology. See `canvas-accessibility` for hidden DOM mirrors and keyboard nav. See `data-table` for data table alternatives.

## Common Pitfalls

1. **Y-axis flip** — WebGL Y-up, CSS/D3 Y-down. Always `clip.y = -clip.y` in vertex shader.

2. **Forgetting DPR** — point sizes and line widths must scale by `devicePixelRatio` in shader, or half-size on Retina.

3. **Blending order** — `SRC_ALPHA, ONE_MINUS_SRC_ALPHA` requires back-to-front for correct transparency. Usually doesn't matter with uniform alpha.

4. **`gl.POINTS` size limit** — varies by GPU (64–255). Use instanced quads for large shapes.

5. **Context loss** — GPU reset or too many contexts. Handle:
   ```js
   canvas.addEventListener("webglcontextlost", e => e.preventDefault());
   canvas.addEventListener("webglcontextrestored", () => reinitialize());
   ```

6. **Too many contexts** — browsers limit to ~8–16. One per viz, not per layer. Use scissor rects for multiple views.

7. **Premultiplied alpha mismatch** — set `premultipliedAlpha: false` in `getContext` options.

8. **Buffer upload during animation** — `bufferSubData` can stall if GPU is still reading. Double-buffer: alternate between two GPU buffers.

9. **Integer attribute precision** — floats lose precision above 2^24. Use texture lookups or encode IDs across multiple components.

## References

- [WebGL Fundamentals](https://webglfundamentals.org/) — Gregg Tavares
- [regl](https://github.com/regl-project/regl) — Mikola Lysenko's functional WebGL wrapper
- [deck.gl](https://deck.gl/) — Uber's WebGL viz framework
- [WebGL2 Spec](https://registry.khronos.org/webgl/specs/latest/2.0/)
- [The Book of Shaders](https://thebookofshaders.com/) — Patricio Gonzalez Vivo & Jen Lowe
- [Instanced Rendering tutorial](https://webgl2fundamentals.org/webgl/lessons/webgl-instanced-drawing.html)
