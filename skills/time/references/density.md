# Density: downsampling and windowing

Absorbed from the v2 `time-series` skill. Open when a series has more points than the chart has pixel columns.

## Which reducer

| Need | Use | Budget |
|---|---|---|
| Line that looks like the original | LTTB | ~`2 * width` points |
| Exact extremes (alerting, spikes must survive) | M4: first, last, min, max per pixel column | 4 per column |
| Fast overview of 10M points | min-max per pixel column | 2 per column |
| Values the viewer will read or aggregate | a real aggregate (`d3.rollups` by interval), labeled | per interval |

LTTB picks real points by maximizing triangle area against the next bucket's average, so it keeps shape but can skip a bucket's true min or max. It's a rendering optimization, not a data transformation: never compute statistics on its output. M4 (Jugel et al., VLDB 2014) renders a line identical to the full-data line at that pixel width, because within a column only the entry, exit, top and bottom points affect the pixels drawn.

Downsample each series independently. Shared indices distort series whose peaks fall at different times.

## LTTB (Steinarsson 2013)

```js
function lttb(data, threshold) {
  if (threshold >= data.length || threshold < 3) return data;
  const sampled = [data[0]], bSize = (data.length - 2) / (threshold - 2);
  let prevIdx = 0;
  for (let i = 0; i < threshold - 2; i++) {
    const bStart = Math.floor(i * bSize) + 1, bEnd = Math.floor((i + 1) * bSize) + 1,
          nEnd = Math.min(Math.floor((i + 2) * bSize) + 1, data.length);
    let avgX = 0, avgY = 0; // next bucket's mean is the triangle's third vertex
    for (let j = bEnd; j < nEnd; j++) { avgX += +data[j].date; avgY += data[j].value; }
    avgX /= nEnd - bEnd; avgY /= nEnd - bEnd;
    const prev = data[prevIdx];
    let maxArea = -1, maxIdx = bStart;
    for (let j = bStart; j < bEnd; j++) {
      const area = Math.abs(
        (+prev.date - avgX) * (data[j].value - prev.value) -
        (+prev.date - +data[j].date) * (avgY - prev.value));
      if (area > maxArea) { maxArea = area; maxIdx = j; }
    }
    sampled.push(data[maxIdx]); prevIdx = maxIdx;
  }
  sampled.push(data[data.length - 1]);
  return sampled;
}
```

Don't run it over gap sentinels: `null` coerces to 0 in the bucket averages. Split the series at gaps, downsample each run, and rejoin with sentinels.

## Virtual windowing

Render only the visible range: `d3.bisector(d => d.date).left` for start and end indices on sorted data, slice (include one point past each edge so the line reaches the frame), then downsample the slice. Re-run after every brush or zoom so point count tracks `2 * width`, not the zoom level.

At 100K+ points, store timestamps and values in parallel `Float64Array`s rather than objects, and draw the line to Canvas.
