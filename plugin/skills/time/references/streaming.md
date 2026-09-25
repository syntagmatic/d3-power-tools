# Real-time streaming

Absorbed from the v2 `time-series` skill. Open when points arrive on a timer or socket and the chart must keep up.

## Decide first

| Arrival rate | Architecture |
|---|---|
| < 1 Hz | none: re-render on each point |
| 1-60 Hz | fixed window + ring buffer + one redraw per frame |
| > 60 Hz or many series | same, plus Canvas for the line and downsampling per frame |

## Fixed window

The x domain is `[now - W, now]`, not `d3.extent(buffer)`. Extent-based domains jump when a point is late or the buffer is still filling, and the line appears to stretch. Keep the y domain fixed or change it only with hysteresis, or the line rescales every frame.

Evict by time, not only by count: drop points older than `now - W` plus one point, so the line still enters from the left edge.

## Shift vs redraw

- **Redraw** (default): each frame, set the domain from `performance.now()`-derived time, recompute the path, redraw the axis. Motion is smooth because the domain moves continuously. Simple and correct.
- **Transform shift**: redraw the path in the old coordinates with the new point appended, then transition the path's `transform` from `translate(0)` to `translate(-dx)` with `d3.easeLinear` over the arrival interval, and remove the offscreen point at the end. Cheaper for SVG at steady rates, but it assumes points arrive at a fixed interval: jittered arrival makes the line stutter. Clip the plot area so the shifted path doesn't draw over the y-axis.

## Buffering

Ring buffer: write `buf[head % capacity]`, advance `head`, iterate oldest to newest. `Array.shift()` is O(n) per point, and unbounded `push()` on a timer is a memory leak.

Coalesce bursts to one redraw per animation frame:

```js
let pending = [], rafId = null;
function onData(point) {
  pending.push(point);
  if (!rafId) rafId = requestAnimationFrame(flush);
}
function flush() {
  rafId = null;
  for (const p of pending) buffer.push(p);
  pending = [];
  redraw();
}
```

## Traps

- Teardown: `cancelAnimationFrame(rafId)`, `ws.close()`, `ro.disconnect()`, stop timers. A chart that outlives its element keeps rendering to nowhere.
- Background tabs pause rAF but not sockets: `pending` grows unbounded. Cap it, or drop to the latest window on `visibilitychange`.
- Don't close over a growing array in handlers; read the buffer through one reference.
