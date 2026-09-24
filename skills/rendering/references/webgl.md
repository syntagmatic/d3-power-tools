# WebGL

Absorbed from the v2 `webgl` skill. Open when Canvas 2D has been measured below frame budget: 500K+ marks, animated point clouds, per-frame updates to millions of elements.

You probably don't need it. Batched Canvas 2D handles ~100K points at 60fps on most hardware. WebGL costs shader debugging with no breakpoints, manual buffer management, and a compile-link-upload cycle. Pay only after profiling.

## When, and when not

| Situation | Renderer |
|---|---|
| < 500K, static or lightly interactive | Canvas 2D (typed arrays, batching, quadtree) |
| 500K+ static | WebGL, one buffer upload, one `drawArrays` |
| 500K+ animated | WebGL instanced rendering |
| Shaped marks or large sizes at scale | instanced quads (`gl.POINTS` is capped by `ALIASED_POINT_SIZE_RANGE`, often 64-256px, and can only be shaped in the fragment shader) |
| Gradients, text, dashes per mark | Canvas: trivial there, painful in shaders |
| Small multiples | Canvas. Browsers cap live WebGL contexts (~8-16); if you must, one context with scissor rects |
| GPU-side aggregation (binning, density, force) | WebGPU compute shaders; otherwise WebGL 2 is enough |

Use `webgl2`: instancing and VAOs are core, no extensions. [regl](https://github.com/regl-project/regl) removes the boilerplate without hiding the model; skip it when you need fine control of framebuffers or multi-pass.

## Layer stack

WebGL canvas (data, `pointer-events: none`) → 2D canvas (hover ring) → SVG overlay (axes, brush, all pointer events). One WebGL context per visualization, never per layer.

## Shaders

D3 scales produce CSS-pixel positions; the vertex shader maps them to clip space and flips Y.

```glsl
#version 300 es
in vec2 a_position;   // CSS px from D3 scales
in vec4 a_color;      // RGBA 0-1
in float a_size;      // diameter, CSS px
uniform vec2 u_resolution;
uniform float u_dpr;
uniform vec2 u_translate;  // zoom transform
uniform float u_scale;
out vec4 v_color;
void main() {
  vec2 pos = a_position * u_scale + u_translate;
  vec2 clip = (pos / u_resolution) * 2.0 - 1.0;
  clip.y = -clip.y;                   // CSS y-down -> GL y-up
  gl_Position = vec4(clip, 0.0, 1.0);
  gl_PointSize = a_size * u_dpr;
  v_color = a_color;
}
```

```glsl
#version 300 es
precision mediump float;
in vec4 v_color;
out vec4 fragColor;
void main() {
  float dist = length(gl_PointCoord - 0.5);
  if (dist > 0.5) discard;          // square point -> circle
  fragColor = vec4(v_color.rgb, v_color.a * (1.0 - smoothstep(0.4, 0.5, dist)));
}
```

Zoom updates `u_translate`/`u_scale` and redraws; no buffer re-upload.

## Buffers

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
```

Bind a VAO first; it records every attribute binding. Pack positions (`n*2`), colors (`n*4`, from `d3.rgb(color(d)).r / 255` etc.) and sizes into `Float32Array`s. Enable `gl.BLEND` with `SRC_ALPHA, ONE_MINUS_SRC_ALPHA`.

Instancing: a 6-vertex unit quad as the template, per-instance `a_offset`, `a_scale`, `a_color` with `gl.vertexAttribDivisor(loc, 1)`, then `gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, count)`. In the vertex shader: `pos = a_quad * a_scale + a_offset`.

Brush filtering: keep a per-element `a_visibility` float buffer (`DYNAMIC_DRAW`), rewrite it and `bufferSubData` it on brush, multiply alpha by it in the fragment shader. Compare against the brush in the same units as the data you test (invert the pixel selection first).

## Thick lines

`gl.lineWidth` is effectively capped at 1px. Draw each segment as an instanced quad:

```glsl
// per instance: a_p0, a_p1; template a_quad in [-0.5, 0.5]
vec2 dir = a_p1 - a_p0; float len = length(dir);
vec2 unit = dir / max(len, 0.001), normal = vec2(-unit.y, unit.x);
vec2 pos = a_p0 + unit * (a_quad.x + 0.5) * len + normal * a_quad.y * u_lineWidth;
```

## Hit detection

Quadtree works to ~1M points. Build it in base (unzoomed) pixel coords and inverse-transform the pointer:

```js
function nearest(qt, [mx, my], t, radius = 20) {
  return qt.find((mx - t.x) / t.k, (my - t.y) / t.k, radius / t.k);
}
```

GPU picking for overlapping shapes or when the quadtree is too slow: render each mark with its ID as a color (`i + 1` split across R, G, B bytes, 16M IDs) into an offscreen framebuffer with blending off, and `readPixels` one pixel. GL's origin is bottom-left, so read at `x = floor(mx*dpr)`, `y = floor((h - my)*dpr) - 1`. Decode `r | g<<8 | b<<16`, minus 1; -1 is no hit. Re-render the pick buffer when positions change, not on every pointermove.

## Pitfalls

- **Y flip.** Forget `clip.y = -clip.y` and the chart is upside down but plausible until checked against the axis.
- **DPR.** Point sizes and line widths need `* u_dpr`; the backing store is `width*dpr`, and `gl.viewport(0, 0, canvas.width, canvas.height)` after every resize.
- **Context loss.** `webglcontextlost` → `e.preventDefault()`; `webglcontextrestored` → recreate programs and buffers.
- **Upload stalls.** Writing a buffer the GPU is still reading blocks. For animation, alternate between two buffers.
- **Screen readers see nothing.** Same fallback as Canvas: hidden DOM mirror or data table.
