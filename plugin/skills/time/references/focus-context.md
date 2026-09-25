# Focus + context and temporal zoom

Absorbed from the v2 `time-series` skill. Open when building an overview brush over a detail chart, or zoom that changes aggregation level.

## Overview + detail

A short overview (full range, faint area) with `d3.brushX`; the detail chart's x domain follows the brush.

```js
const xOverview = d3.scaleUtc(d3.extent(data, d => d.date), [0, width]);
const xMain = xOverview.copy();
const brush = d3.brushX()
  .extent([[0, 0], [width, overviewHeight]])
  .on("brush end", ({ selection, sourceEvent }) => {
    if (sourceEvent?.type === "zoom") return; // moved by zoom sync, not the user
    xMain.domain(selection ? selection.map(xOverview.invert) : xOverview.domain());
    renderMain(); // axis + downsampled visible slice
  });
```

- A cleared brush (`selection === null`) should restore the full range, not leave the last window.
- Buttons ("Last 6 months") call `brushG.transition().call(brush.move, [xOverview(t0), xOverview(t1)])`. `brush.move` emits brush events, so don't also call the render function.
- Snap to calendar units in `end`: `interval.floor(t0)`, `interval.ceil(t1)`, then `brush.move` again. Snap only when `sourceEvent` is set, or the snap's own `end` event re-enters forever.
- Brush plus zoom on the same chart: convert with `transform.rescaleX(x).invert`, not `x.invert`. When each updates the other, guard both handlers with `sourceEvent` checks or they loop.
- Re-downsample the visible slice on every change (`references/density.md`).
- Throttle `renderMain` to one call per animation frame if it's heavy; `brush` fires on every pointermove.

## Semantic temporal zoom

Geometric zoom stretches marks. Semantic zoom changes what a mark means: at a year span, monthly bars; at a day, hourly lines.

```js
function temporalLevel([t0, t1]) {
  const span = t1 - t0, day = 864e5;
  if (span > 365 * day) return { interval: d3.utcMonth, format: "%b %Y" };
  if (span > 30 * day) return { interval: d3.utcWeek, format: "%b %d" };
  if (span > 7 * day) return { interval: d3.utcDay, format: "%a %d" };
  if (span > day) return { interval: d3.utcHour, format: "%H:%M" };
  return { interval: d3.utcMinute, format: "%H:%M:%S" };
}
```

Pre-compute `d3.rollups` per level once; re-rolling on every zoom frame stalls. Axis ticks: `.ticks(interval).tickFormat(d3.utcFormat(format))`. If the viewer needs macro and micro at once, use overview+detail instead.
