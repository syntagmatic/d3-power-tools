# Canvas 2D

Absorbed from the v2 `canvas` skill. Open when drawing 1K-1M marks on Canvas: layer setup, hit detection, batching, progressive rendering, pixel work, workers.

D3 does the data (scales, layouts, binning); Canvas does the pixels. There's no join: compute positions into arrays, loop, draw.

## Layers

Stack canvases by update frequency so a hover ring doesn't repaint 100K background points: background (full data, dimmed) → foreground (selected subset) → interaction (hover ring) → SVG overlay (axes, brush, pointer events). A color-picking canvas is created offscreen and never appended.

```js
function addCanvas(div, width, height) {
  const dpr = devicePixelRatio;
  const canvas = div.append("canvas")
      .attr("width", Math.round(width * dpr)).attr("height", Math.round(height * dpr))
      .style("width", `${width}px`).style("height", `${height}px`)
      .style("position", "absolute").style("top", 0).style("left", 0)
    .node();
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr); // draw in CSS pixels from here on
  return ctx;
}
```

- `willReadFrequently: true` on a canvas you read with `getImageData` keeps it in CPU memory: faster reads, no GPU acceleration. Use it only for the hidden picking canvas.
- `ctx.reset()` clears state *including* the DPR scale. Re-apply it.

## Hit detection

| Marks | Method |
|---|---|
| Points, circles, nodes | `d3.quadtree().x(...).y(...).addAll(data)`, `find(mx, my, radius)`. Finds nearest center, not the shape edge |
| Points, need nearest-always or Voronoi cells | `d3.Delaunay.from(...).find(mx, my)` |
| Rectangles (treemap, icicle) | bounding-box test, keep the deepest hit by `node.depth` |
| Arcs (sunburst) | convert to polar; test radius against inner/outer and angle against start/end |
| Lines, paths, irregular or overlapping shapes | color picking: redraw each mark in a unique color on a hidden canvas, read one pixel |

D3 arc angles start at 12 o'clock and run clockwise; `atan2` on screen coords starts at 3 o'clock. Normalize:

```js
const arcAngle = (x, y) => (Math.atan2(y, x) + Math.PI / 2 + 2 * Math.PI) % (2 * Math.PI);
```

Always pass a search radius to `quadtree.find`. Rebuild the quadtree when data or scales change; it doesn't update itself. For color picking, draw IDs fully opaque with no shadows, and treat a decoded index with no matching mark as a miss: antialiased edge pixels blend two IDs.

## Typed arrays and batching

For 100K+ points, flat `Float32Array`s avoid GC churn. One `beginPath`/`fill` per style, not per point:

```js
function drawPoints(ctx, xs, ys, n, r = 2) {
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    ctx.moveTo(xs[i] + r, ys[i]); // without this, arc draws a line from the previous point
    ctx.arc(xs[i], ys[i], r, 0, 2 * Math.PI);
  }
  ctx.fill();
}
```

State changes (`fillStyle`, `lineWidth`, `globalAlpha`) are the expensive part. Group by style (`d3.group` by category, or pre-sort indices by category for very large data) and set style once per group. Typed-array buffers transfer to workers at zero copy: `postMessage(msg, [arr.buffer])`, and the sender's copy is detached.

## Progressive rendering

When one full redraw blows the 16ms budget, draw shuffled chunks across frames so every frame is a representative sample:

```js
function createRenderQueue(drawFn, { rate = 500, onComplete } = {}) {
  let queue = [], animId = null;
  function render(data) {
    cancel();
    queue = d3.shuffle(data.slice());
    animId = requestAnimationFrame(drain);
  }
  function drain() {
    queue.splice(0, rate).forEach(drawFn);
    animId = queue.length ? requestAnimationFrame(drain) : (onComplete?.(), null);
  }
  function cancel() { if (animId) cancelAnimationFrame(animId); animId = null; queue = []; }
  return Object.assign(render, { cancel });
}
```

Clear once before starting, not between chunks. Cancel the queue on interaction and redraw immediately.

## Pixels (ImageData)

| Approach | For |
|---|---|
| `ImageData` writes | heatmaps, density, continuous fields |
| `fillRect` per cell | grids under ~100×100 |
| batched `arc`/paths | scatter, bubble, node-link up to ~500K |

`putImageData` ignores the transform and the clip, writing 1:1 into the backing store. Size the ImageData at physical pixels (`width*dpr × height*dpr`), or put it on an offscreen canvas and `drawImage` it back so margins and DPR apply.

## Workers and OffscreenCanvas

Move binning, contours, and force ticks to a Worker first. If the draw loop itself is the bottleneck (visible jank at 50K+), `canvas.transferControlToOffscreen()`:

- Forward `devicePixelRatio` to the worker; it scales its own context. DPR changes must be posted too.
- After transfer, `getContext()` on the original canvas throws.
- Bridge zoom by posting `{type: "zoom", transform: {x, y, k}}` from the SVG overlay.
- Keep the quadtree on the main thread so hover has no round trip.
- Workers have no `document.fonts`; preload fonts or use a text atlas.

## Zoom, culling, LOD

Apply the zoom transform with `ctx.translate(t.x, t.y); ctx.scale(t.k, t.k)`. Visible bounds are the inverted viewport (`x0 = -t.x / t.k`, `x1 = (width - t.x) / t.k`); `quadtree.visit()` enumerates only visible points.

| Visible points | Draw |
|---|---|
| < 500 | sized circles, labels, tooltips |
| 500-10K | 2-4px dots, hover to identify |
| 10K-100K | 1px dots, batched, alpha scaled |
| 100K-1M | density raster or hex bins |
| 1M+ | aggregated tiles, progressive refinement |

## Text and sprites

`fillText` rasterizes per call; cap at ~50 labels. For repeated custom markers, draw each shape once into cells of an offscreen atlas and stamp with `drawImage(atlas, col*cell, 0, cell, cell, x - s/2, y - s/2, s, s)`. Build the atlas at DPR and rebuild on DPR change. `shadowBlur` is very expensive; use pre-rendered sprites.

## Pitfalls

- Clear in the coordinate system you're in. With only the DPR scale applied, `clearRect(0, 0, width, height)` in CSS pixels. After a margin `translate`, that misses a strip; clear under `setTransform(1, 0, 0, 1, 0, 0)` with `canvas.width, canvas.height` instead.
- 10K translucent circles saturate to a solid blob and cost fill time. Bin or use density instead.
- `ctx.fillText` in a 100K loop. Labels are for the top few.
