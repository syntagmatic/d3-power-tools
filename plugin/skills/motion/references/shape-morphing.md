# Shape morphing

Absorbed from the v2 `shape-morphing` skill. Open when the start and end shapes differ in geometry: circle ↔ rect, bar ↔ pie, layout switches, arbitrary paths, projection changes.

A morph says "these are the same data, seen differently." When source and target are categorically different things, the continuity is a lie.

## Choosing a technique

| Shapes | Technique | Notes |
|---|---|---|
| Share numeric parameters (rx, arc angles, position) | **Parametric**: tween the parameters | True curves every frame, cheapest, works on canvas without path parsing |
| Different geometry, closed, simple (star → circle, rect → wedge) | **Point resampling** (`scripts/morph-paths.js`) | Always a polygon; smooth at 128 points. O(n²) rotation alignment once |
| Open lines with different point counts | `d3-interpolate-path` | Extends the shorter path, then interpolates |
| Holes, multiple subpaths, winding mismatch | `flubber` | Handles topology that raw resampling doesn't |
| Bundle size tight | `polymorph` (~6KB) | Lighter flubber alternative |
| App already uses GSAP | MorphSVG plugin | Most robust edge cases |

Resampling approximates circles as 128-gons, so prefer parametric whenever both ends share parameters.

## Parametric

**Circle ↔ rect.** Tween `width`, `height`, `rx`, `ry` on a `<rect>`. With `w == h` and `rx = w/2` it's a circle; with `w != h` and `rx = min(w,h)/2` it's a pill, not a circle. Canvas: `ctx.roundRect(x, y, w, h, r)` behaves the same.

**Bar ↔ pie.** Express both states as `d3.arc` parameters and tween the parameter object. The bar state is radial bars: equal angular slices, value → `outerRadius`. The pie state: value → angle, constant radius. Mid-morph frames encode value as neither length nor angle, so this morph shows *which wedge was which bar*, not value. Keep it short.

```js
const arc = d3.arc();
function morphTo(targetFn) {
  const pieData = d3.pie().value(d => d.value).sortValues(null)(data);
  svg.selectAll(".shape")
    .data(pieData, d => d.data.id)
    .transition().duration(800)
    .attrTween("d", function(d, i) {
      const interp = d3.interpolate(this.__arcParams, targetFn(d, i, data.length));
      return t => arc(this.__arcParams = interp(t));
    });
}
```

Stash params on the element (`this`), not the datum: `.data()` replaces the datum, and `d3.interpolate(undefined, next)` snaps instead of animating. Initialize `this.__arcParams` on first render.

## Point resampling

1. **Resample** both paths to N evenly spaced `[x, y]` via `getPointAtLength()`, once, never per frame.
2. **Rotate** the source array to minimize total squared distance to the target (`bestRotation`). Without it the shape spins or collapses mid-morph.
3. **Interpolate** the aligned arrays in `attrTween`.

`morphPaths(selection, targetPathStr, { n: 128, duration: 800 })` in `scripts/morph-paths.js` does all three. Below ~64 points circles look polygonal.

### Cross-layout morphs (treemap ↔ pack ↔ pie)

Tweening parameters between a rect and an arc wedge pinches the shape to near-zero area around `t = 0.5`. Instead, resample every layout's shape to the same N points in the same absolute coordinate space and lerp arrays; each point travels straight, so area never collapses. 48 points is enough for rects, circles and wedges at thumbnail size; 96-128 for large or complex outlines. Pie arcs are centered at the origin, so add the center offset back. On canvas, skip path strings and draw the point arrays as polygons. The hierarchy skill's `layout-switcher.html` example is a working version.

## Projection transitions

Lerp the pixel output of two projections inside a raw projection:

```js
function projectTransition(paths, projA, projB, duration = 1500) {
  const path = d3.geoPath();
  const timer = d3.timer(elapsed => {
    const t = Math.min(1, d3.easeCubicInOut(elapsed / duration));
    const deg = 180 / Math.PI;
    const interpolated = d3.geoProjection((lon, lat) => {
      const a = projA([lon * deg, lat * deg]), b = projB([lon * deg, lat * deg]);
      if (!a || !b) return [0, 0];
      return [a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t];
    }).scale(1).translate([0, 0]).reflectY(true); // raw output is already screen pixels
    path.projection(interpolated);
    paths.attr("d", path);
    if (t === 1) timer.stop();
  });
}
```

Raw projections take radians; `reflectY(true)` undoes `geoProjection`'s y-negation.

## When not to morph

- **Categorically different data** (revenue bars → headcount bars): cut or crossfade. The discontinuity is the honest signal.
- **No shared identity** (France's outline → Brazil's): no point on one "becomes" a point on the other. Eye candy.
- **Order destroyed** (sorted bars → unsorted treemap): everything travels in different directions and nothing can be tracked. Keep order, or stagger.
- **More than ~30 shapes at once**: a swarm. Morph a highlighted subset, crossfade the rest.

## Pitfalls

1. `interpolateString` on paths with different commands: garbage.
2. State stashed on the datum: lost on rebind, morph snaps.
3. No rotation alignment: spinning artifact.
4. Resampling per frame: `getPointAtLength()` is slow.
5. Too few samples (<64): visible polygon edges.
