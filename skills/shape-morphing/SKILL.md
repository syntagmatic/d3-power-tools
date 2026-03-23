---
name: shape-morphing
description: "Morph between shapes in D3.js visualizations. Use this skill when the user wants to smoothly transition between different shape types — circle to rectangle, bar to pie, star to circle, icon morphing, or any shape-to-shape animation. Covers parametric interpolation (cornerRadius, arc parameters), arbitrary path morphing via point resampling, and map projection transitions. Also use when the user mentions shape interpolation, path morphing, or wants to animate between different geometries."
---

# Shape Morphing

Smoothly transition between different shapes in D3 visualizations. Three tiers of approach, from simplest to most general.

## Strategy

Prefer parametric interpolation over path-string manipulation:

1. **Parametric** — If both shapes can be described by shared numeric parameters (position, size, corner radius, arc angles), interpolate the numbers directly. No path parsing needed, works on both SVG and Canvas.
2. **Point resampling** — For arbitrary paths (star→circle, icons, map outlines), resample both shapes to equal-length point arrays via `getPointAtLength()`, then lerp the arrays per frame. ~40 lines, no libraries.

Avoid `d3.interpolateString` on SVG path strings — it produces garbage when paths have different command counts. The point resampling approach below is inspired by Noah Veltman's Flubber.

## Parametric Morphing

### Circle ↔ Rectangle via cornerRadius

A rounded rectangle with `rx = min(width, height) / 2` is visually identical to a circle. Morph between them by interpolating `rx`, `ry`, `width`, and `height` — standard D3 transitions, no plugins:

```js
const shapeStates = {
  circles: { w: 40, h: 40, rx: 20 },  // rx = w/2 → circle
  rounded: { w: 52, h: 40, rx: 8 },   // small rx → rounded rect
  rects:   { w: 52, h: 40, rx: 0 },   // rx = 0 → sharp rect
};

function morphTo(state) {
  const s = shapeStates[state];
  svg.selectAll("rect")
    .transition().duration(600)
    .attr("width", s.w)
    .attr("height", s.h)
    .attr("rx", s.rx)
    .attr("ry", s.rx);
}
```

On Canvas, the same idea works with `ctx.roundRect(x, y, w, h, cornerRadius)` — when `cornerRadius >= min(w, h) / 2`, it draws a circle.

### Bar Chart ↔ Pie Chart

Represent both states as arcs so you can interpolate arc parameters directly. Bars become arcs with a very large radius and narrow angle; pie wedges are normal arcs.

```js
const arc = d3.arc();

// Bar state: tall thin arc segments (visually rectangular)
function barAngles(d, i, n) {
  const barWidth = (2 * Math.PI) / n;
  return {
    innerRadius: 0,
    outerRadius: yScale(d.value),
    startAngle: i * barWidth,
    endAngle: (i + 1) * barWidth,
  };
}

// Pie state: standard wedges
function pieAngles(d) {
  return {
    innerRadius: 0,
    outerRadius: r,
    startAngle: d.startAngle,
    endAngle: d.endAngle,
  };
}

function morphTo(targetFn) {
  const pie = d3.pie().value(d => d.value).sortValues(null);
  const pieData = pie(data);

  svg.selectAll(".shape")
    .data(pieData, d => d.data.id)
    .transition().duration(800)
    .attrTween("d", function(d, i) {
      const prev = this.__arcParams;
      const next = targetFn(d, i, data.length);
      const interp = d3.interpolate(prev, next);
      return t => {
        const params = interp(t);
        this.__arcParams = params;  // stash on element, not datum
        return arc(params);
      };
    });
}
```

**Important:** Stash transition state on the DOM element (`this`), not the datum (`d`).
When `.data()` rebinds, D3 replaces each element's datum with the new object — any state
stored on the old datum is lost, and `d3.interpolate(undefined, next)` will snap instantly
instead of animating.

## Arbitrary Path Morphing via Point Resampling

For shapes that don't share numeric parameters, resample both paths to N evenly-spaced points via `getPointAtLength()`, align the rotation to minimize travel distance, and interpolate the point arrays per frame. See [`scripts/morph-paths.js`](scripts/morph-paths.js) for the full implementation with `resamplePath`, `bestRotation`, `pointsToPath`, and `morphPaths`.

```js
// Morph a selection of <path> elements to a target shape
morphPaths(d3.selectAll("path.shape"), starPathStr, { n: 128, duration: 800 });
```

The three steps composing `morphPaths`:
1. **Resample** both paths to N evenly-spaced `[x, y]` points (once, not per frame)
2. **Rotate** the source points to minimize total squared distance to target — this prevents the "spinning" artifact from misaligned start points
3. **Interpolate** the aligned point arrays per frame via `attrTween`

**Tradeoffs:** The output is always a polygon (straight line segments between sample points). At 128 points this is visually smooth for most shapes. For shapes with true curves (circles, arcs), the parametric approach above gives mathematically perfect results. Use point resampling only when the shapes are genuinely different and can't share parameters.

## Cross-Layout Morphing

The hardest morphing problem: transitioning between fundamentally different chart layouts (treemap→pie, bar→radial, scatter→line). Each layout produces shapes with different geometry — rects, circles, arcs — and naive interpolation loses area mid-transition.

### Why Parametric Interpolation Fails Here

The parametric approach (interpolating `rx` to round a rect into a circle, or interpolating arc angles) breaks down when source and target shapes have different topology. A rect has 4 corners; an arc wedge has 2 straight edges and a curve. Interpolating between their parameters produces a shape that collapses to near-zero area at `t=0.5` before re-expanding — the "pinch" artifact.

### Point Resampling Preserves Area

The fix: resample both shapes to the same number of evenly-spaced points, then lerp the point arrays. Each point on the source travels in a straight line to its corresponding point on the target. Area is preserved throughout because no dimension collapses to zero.

```js
// Resample any shape path to N points, once before animation starts
const nPts = 48;

function sampleShape(pathEl, n) {
  const len = pathEl.getTotalLength();
  return d3.range(n).map(i => {
    const p = pathEl.getPointAtLength(i / n * len);
    return [p.x, p.y];
  });
}

function pointsToPath(pts) {
  return "M" + pts.map(p => p[0].toFixed(2) + "," + p[1].toFixed(2)).join("L") + "Z";
}
```

### Recipe: Treemap ↔ Pack ↔ Pie

Generate all layout paths in absolute coordinates, sample each to the same point count, then interpolate between the cached point arrays. The animation loop does zero path parsing — just array lerps.

```js
const nPts = 48;
const data = {children: d3.range(10).map(i => ({id: i, value: 10 + Math.random() * 90}))};
const values = data.children.map(d => d.value);

// --- Generate path strings for each layout ---

// Treemap: rounded rects in absolute coords
const root1 = d3.hierarchy(data).sum(d => d.value);
d3.treemap().size([width, height]).padding(2)(root1);
const treemapPaths = root1.leaves().map(d => {
  // Use a rounded rect path
  return roundedRectPath(d.x0, d.y0, d.x1 - d.x0, d.y1 - d.y0, 2);
});

// Pack: circles as SVG path arcs
const root2 = d3.hierarchy(data).sum(d => d.value);
d3.pack().size([width, height]).padding(2)(root2);
const packPaths = root2.leaves().map(d => {
  const r = d.r;
  return `M${d.x+r},${d.y}A${r},${r} 0 1,1 ${d.x-r},${d.y}A${r},${r} 0 1,1 ${d.x+r},${d.y}Z`;
});

// Pie: arc wedges, offset to absolute coords
const pieR = Math.min(width, height) / 2 - 8;
const cx = width / 2, cy = height / 2;
const arcGen = d3.arc().innerRadius(0).outerRadius(pieR);
const pieSlices = d3.pie().sort(null)(values);
// Sample pie arcs from a translated <g> to get absolute coords
const piePts = pieSlices.map(d => {
  const g = svg.append("g").attr("transform", `translate(${cx},${cy})`);
  const el = g.append("path").attr("d", arcGen(d));
  const pts = sampleShape(el.node(), nPts);
  // Transform to absolute coordinates
  const absPts = pts.map(p => [p.x + cx, p.y + cy]);
  g.remove();
  return absPts;
});

// --- Sample treemap and pack paths to point arrays ---
const treemapPts = treemapPaths.map(d => {
  const tmp = svg.append("path").attr("d", d).style("opacity", 0);
  const pts = sampleShape(tmp.node(), nPts);
  tmp.remove();
  return pts;
});
// same for packPts...

// --- Animate between layouts ---
const layouts = [treemapPts, packPts, piePts];
const transDur = 2000, holdDur = 2500;

d3.timer(t => {
  const cycleDur = (transDur + holdDur) * layouts.length;
  const cycleT = t % cycleDur;
  const segment = Math.floor(cycleT / (transDur + holdDur));
  const segT = cycleT - segment * (transDur + holdDur);
  const p = segT < transDur ? d3.easeCubicInOut(segT / transDur) : 1;

  const from = layouts[segment];
  const to = layouts[(segment + 1) % layouts.length];

  paths.each(function(d, i) {
    const interp = from[i].map((fp, j) => [
      fp[0] + (to[i][j][0] - fp[0]) * p,
      fp[1] + (to[i][j][1] - fp[1]) * p
    ]);
    d3.select(this).attr("d", pointsToPath(interp));
  });
});
```

### Key Details

**Sample count:** 48 points is enough for smooth rects, circles, and pie wedges at thumbnail scale. Use 96–128 for larger shapes or complex outlines.

**Rotation alignment:** When morphing between similar shapes (star→star, circle→circle), use `bestRotation()` from `morph-paths.js` to prevent the spinning artifact. For cross-layout morphs (rect→arc), rotation alignment is less critical because the shapes are already roughly co-located.

**Absolute coordinates:** All layouts must produce paths in the same coordinate space. Pie arcs are generated relative to their center, so sample them from a translated `<g>` element and add the offset back.

**Canvas variant:** On Canvas, skip the path strings entirely. Store the point arrays and draw them as polygons:

```js
ctx.beginPath();
ctx.moveTo(pts[0][0], pts[0][1]);
for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
ctx.closePath();
ctx.fill();
```

## Map Projection Transitions

Interpolate between projection functions — a technique from syntagmatic's projection comparison work. For general geographic map patterns (projections, choropleth, TopoJSON, zoom-to-feature), see the `geographic-maps` skill.

```js
function projectTransition(projA, projB, duration = 1500) {
  const path = d3.geoPath();

  const timer = d3.timer((elapsed) => {
    const t = Math.min(1, d3.easeCubicInOut(elapsed / duration));

    // Interpolate the raw projection point-by-point, then wrap as a
    // full projection via d3.geoProjection so .stream works correctly.
    const interpolated = d3.geoProjection((lon, lat) => {
      const a = projA([lon * 180 / Math.PI, lat * 180 / Math.PI]);
      const b = projB([lon * 180 / Math.PI, lat * 180 / Math.PI]);
      if (!a || !b) return [0, 0];
      return [
        a[0] * (1 - t) + b[0] * t,
        a[1] * (1 - t) + b[1] * t
      ];
    })
      .scale(1)       // raw output is already in pixels
      .translate([0, 0]);

    path.projection(interpolated);
    paths.attr("d", path);
    if (t === 1) timer.stop();
  });
}
```

## Common Pitfalls

1. **Interpolating path strings directly**: `d3.interpolateString` on SVG paths produces garbage when paths have different commands. Use parametric interpolation (arc parameters, cornerRadius) or point resampling.
2. **Stashing state on datum instead of element**: When `.data()` rebinds, D3 replaces each element's datum. Stash arc params or morph state on `this` (the DOM element) so it survives rebinding.
3. **Missing rotation alignment**: Without `bestRotation`, point-resampled morphs produce a spinning/collapsing artifact. Always align before interpolating.
4. **Too few sample points**: Below ~64 points, resampled circles and curves look polygonal. 128 is a safe default.
5. **Resampling per frame**: `getPointAtLength()` is expensive. Resample once before the transition starts, then interpolate the cached point arrays per frame.

## References

- [flubber](https://github.com/veltman/flubber) — Noah Veltman's library for smooth shape interpolation, handling topology mismatches and winding order
- [d3-interpolate-path](https://github.com/pbeshai/d3-interpolate-path) — Peter Beshai's plugin for interpolating SVG paths with mismatched commands
- [Animated Transitions in Statistical Data Graphics](https://idl.cs.washington.edu/papers/animated-transitions/) — Jeffrey Heer & George Robertson's research on shape transition perception (IEEE InfoVis 2007)
- [D3 Interpolate documentation](https://d3js.org/d3-interpolate) — Mike Bostock's core interpolation module
- [D3 Geo Projection](https://d3js.org/d3-geo/projection) — API reference for map projection transitions via `d3.geoProjection`
- [Shape Tweening](https://en.wikipedia.org/wiki/Morphing#Shape_tweening) — overview of morphing techniques from simple interpolation to topology-aware methods
