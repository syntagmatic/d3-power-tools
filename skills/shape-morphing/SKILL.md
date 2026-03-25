---
name: shape-morphing
description: "Morph between shapes in D3.js visualizations. Use this skill when the user wants to smoothly transition between different shape types — circle to rectangle, bar to pie, star to circle, icon morphing, or any shape-to-shape animation. Covers parametric interpolation (cornerRadius, arc parameters), arbitrary path morphing via point resampling, and map projection transitions. Also use when the user mentions shape interpolation, path morphing, or wants to animate between different geometries."
---

# Shape Morphing

A smooth morph between two shapes tells the viewer "these are the same data, seen differently." When that claim is false — when the source and target represent categorically different things — the animation misleads by implying a continuity that does not exist.

## Choosing an Approach

Use the simplest technique that fits. Each tier trades generality for fidelity and performance.

| Approach | When to use | Fidelity | Cost |
|---|---|---|---|
| **Parametric** | Both shapes share numeric parameters (cornerRadius, arc angles, position) | Perfect curves, no polygonal artifacts | Cheapest — standard D3 transitions |
| **Point resampling** | Shapes have different geometry (star→circle, rect→arc wedge) | Smooth at 128 pts, always polygonal | Moderate — O(n^2) rotation alignment once, then array lerps per frame |
| **Topology-aware** (flubber, d3-interpolate-path) | Shapes with holes, multiple subpaths, or winding-order mismatches | Handles holes and subpaths | Library dependency; heavier than hand-rolled resampling |

**Why not just always resample?** Parametric morphs preserve true curves — a circle stays a perfect circle at every frame. Resampled morphs approximate curves as 128-gons, which is visually fine but mathematically imprecise. Parametric also runs on Canvas without path parsing.

**Why not just use flubber?** Flubber handles edge cases (holes, subpaths, winding order) that raw resampling does not. But it is a dependency, and for the common cases — cornerRadius morphs, arc parameter morphs, simple path-to-path — the built-in approaches here are lighter and give you full control.

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

On Canvas, `ctx.roundRect(x, y, w, h, cornerRadius)` — when `cornerRadius >= min(w, h) / 2`, it draws a circle.

### Bar Chart ↔ Pie Chart

Represent both states as arcs so you can interpolate arc parameters directly. Bars become arcs with equal-width angles and value-driven radius; pie wedges use value-driven angles and constant radius.

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

**Stash state on the DOM element (`this`), not the datum (`d`).** When `.data()` rebinds, D3 replaces each element's datum with the new object — any state stored on the old datum is lost, and `d3.interpolate(undefined, next)` snaps instantly instead of animating.

## Arbitrary Path Morphing via Point Resampling

For shapes that don't share numeric parameters, resample both paths to N evenly-spaced points via `getPointAtLength()`, align the rotation to minimize travel distance, and interpolate the point arrays per frame. See [`scripts/morph-paths.js`](scripts/morph-paths.js) for the full implementation.

```js
// Morph a selection of <path> elements to a target shape
morphPaths(d3.selectAll("path.shape"), starPathStr, { n: 128, duration: 800 });
```

The three steps:
1. **Resample** both paths to N evenly-spaced `[x, y]` points (once, not per frame — `getPointAtLength()` is expensive)
2. **Rotate** the source points to minimize total squared distance to target — prevents the "spinning" artifact from misaligned start points
3. **Interpolate** the aligned point arrays per frame via `attrTween`

**Tradeoffs:** The output is always a polygon (straight segments between sample points). At 128 points this is visually smooth for most shapes. For true curves (circles, arcs), parametric gives mathematically perfect results. Use resampling only when the shapes genuinely differ in topology.

## Cross-Layout Morphing

Transitioning between different chart layouts (treemap→pack→pie) where each layout produces shapes with different geometry — rects, circles, arc wedges. Parametric interpolation breaks down here because a rect has 4 corners while an arc wedge has 2 straight edges and a curve; interpolating between their parameters produces a shape that collapses to near-zero area at `t=0.5` — the "pinch" artifact.

**The fix:** resample all layout shapes to the same point count in the same coordinate space, then lerp the arrays. Each point travels in a straight line to its target, so area is preserved throughout.

The recipe (see `examples/layout-morph.html` for the full working version):
1. Compute each layout (treemap, pack, pie) to get path strings in absolute coordinates
2. Resample each shape to N points via a temporary hidden `<path>` element
3. Align rotations via `bestRotation()` to prevent spinning
4. Cache the point arrays — the animation loop does zero path parsing, just array lerps

**Sample count:** 48 points is enough for rects, circles, and pie wedges at thumbnail scale. Use 96-128 for larger shapes or complex outlines.

**Absolute coordinates:** All layouts must produce paths in the same coordinate space. Pie arcs are generated relative to their center, so sample them from a translated `<g>` and add the offset back.

**Canvas variant:** Skip path strings entirely. Store point arrays and draw as polygons:

```js
ctx.beginPath();
ctx.moveTo(pts[0][0], pts[0][1]);
for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
ctx.closePath();
ctx.fill();
```

## Map Projection Transitions

Interpolate between projection functions by lerping their raw output point-by-point. For general geographic map patterns, see the `cartography` skill.

```js
function projectTransition(projA, projB, duration = 1500) {
  const path = d3.geoPath();

  const timer = d3.timer((elapsed) => {
    const t = Math.min(1, d3.easeCubicInOut(elapsed / duration));

    // Interpolate raw projection output, wrap via d3.geoProjection
    // so .stream works correctly for path generation.
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

## When Not to Morph

Morphing implies "this is the same thing, changing form." When that is false, the animation misleads.

**Categorically different data.** Morphing a bar chart of revenue into a bar chart of headcount suggests a continuous relationship between them. Use a cut (crossfade or instant swap) instead — the discontinuity correctly signals that the data changed.

**Unrelated geometries with no shared identity.** Morphing one country's outline into another's is eye candy, not communication. There is no meaningful correspondence between the points. Each point on France does not "become" a point on Brazil.

**Layout changes that destroy ordering.** Morphing a sorted bar chart into an unsorted treemap makes every element travel simultaneously in different directions. The viewer cannot track any single element, so the animation communicates nothing. Either maintain sort order across layouts or use staggered transitions so the eye can follow a few elements.

**Encoding changes that reverse meaning.** If bars encode value as height and then morph to a pie where value is encoded as angle, the intermediate state encodes value as neither — it is visual noise. The morph works when the encoding is consistent (bar height → arc radius, both are length).

**Too many elements.** Beyond ~30 shapes morphing simultaneously, the viewer cannot track correspondences. The animation becomes a swarm. Consider morphing a highlighted subset while crossfading the rest.

## Common Pitfalls

1. **Interpolating path strings directly**: `d3.interpolateString` on SVG paths produces garbage when paths have different commands. Use parametric interpolation or point resampling.
2. **Stashing state on datum instead of element**: When `.data()` rebinds, D3 replaces each element's datum. Stash arc params on `this` so they survive rebinding.
3. **Missing rotation alignment**: Without `bestRotation`, point-resampled morphs produce a spinning/collapsing artifact. Always align before interpolating.
4. **Resampling per frame**: `getPointAtLength()` is expensive. Resample once, then interpolate cached arrays.
5. **Too few sample points**: Below ~64 points, resampled circles look polygonal. 128 is a safe default.

## References

- [flubber](https://github.com/veltman/flubber) — Noah Veltman's library for smooth shape interpolation, handles topology mismatches and winding order
- [d3-interpolate-path](https://github.com/pbeshai/d3-interpolate-path) — Peter Beshai's plugin for interpolating SVG paths with mismatched commands
- [Animated Transitions in Statistical Data Graphics](https://idl.cs.washington.edu/papers/motion/) — Heer & Robertson's research on when transitions help vs. hinder comprehension (IEEE InfoVis 2007)
