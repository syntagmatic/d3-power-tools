# Projections

From the v2 `cartography` skill. Open when setting up a regional projection, fitting, handling pre-projected data, animating between projections, or building a draggable globe.

## Regional parameters

```js
const europe = d3.geoConicEqualArea().rotate([-15, 0]).center([0, 52]).parallels([35, 65]);
const conus  = d3.geoAlbers().rotate([96, 0]).center([0, 38]).parallels([29.5, 45.5]);
```

Rotation re-centers the sphere: to center on `[lon, lat]`, rotate `[-lon, -lat]`. The three angles are `[λ, φ, γ]`: yaw, pitch, roll. For conics, rotate to the region's central meridian and use `center` only for the latitude.

## Fitting

Fit to the merged outline (US) or the Sphere (world), not to a features array:

```js
const nation = topojson.merge(us, us.objects.states.geometries);
const usProj = d3.geoAlbersUsa().fitSize([width, height], nation);
const worldProj = d3.geoEqualEarth().fitExtent([[10, 10], [width - 10, height - 10]], { type: "Sphere" });
```

`fitSize`/`fitExtent` set scale and translate only, so set `rotate`, `center`, `parallels` first. Refit on resize.

## Pre-projected data

us-atlas ships two families. `counties-10m.json`, `states-10m.json`, `nation-10m.json` are lon/lat: use a projection. `counties-albers-10m.json` etc. are already projected by `geoAlbersUsa` into a 975×610 frame with y pointing down:

```js
const path = d3.geoPath();                                               // draw at 975×610
const fitted = d3.geoPath(d3.geoIdentity().fitSize([width, height], nation)); // rescale
```

Don't add `reflectY(true)` here: it flips the map upside down. `reflectY` is for planar data whose y grows northward (state-plane or UTM shapefile coordinates). To get lon/lat back from the albers files, invert with the projection they were made with: `d3.geoAlbersUsa().scale(1300).translate([487.5, 305])`.

## AlbersUsa limits

No `rotate()`, `center()` or `clipAngle()`. `projection(p)` and `invert()` return `null` outside Lower 48, Alaska and Hawaii (Puerto Rico is outside too). Not usable with tiles, which need Mercator.

## Transitions

Same projection type: interpolate parameters. No artifacts.

```js
function rotateTo(svg, projection, path, [lon, lat]) {
  const r0 = projection.rotate(), r1 = [-lon, -lat, 0];
  svg.transition().duration(1000).tween("rotate", () => {
    const interp = d3.interpolate(r0, r1);
    return t => { projection.rotate(interp(t)); svg.selectAll("path").attr("d", path); };
  });
}
```

Different types: interpolate projected points in screen space. Works for any pair, but where one projection clips a point the other shows, paths drop out. Pre-clip to the intersection of both visible regions, or cross-fade.

```js
const interpolateProjection = (proj0, proj1) => t => d3.geoTransform({
  point(x, y) {
    const p0 = proj0([x, y]), p1 = proj1([x, y]);
    if (!p0 || !p1) return;
    this.stream.point(p0[0] * (1 - t) + p1[0] * t, p0[1] * (1 - t) + p1[1] * t);
  }
});
```

For an orthographic reveal, animating `clipAngle` from 90 toward 180 softens the pop-in.

## Globe drag (versor)

A lon/lat drag (`λ += dx * .5; φ -= dy * .5`) works for demos and locks near the poles. Versor rotates by the quaternion between the grabbed point and the cursor. `versor.delta` takes **cartesian** vectors, so convert with `versor.cartesian`:

```js
import versor from "https://cdn.jsdelivr.net/npm/versor@0.2/+esm";

function globeDrag(projection, render) {
  let v0, q0, r0;
  return d3.drag()
    .on("start", event => {
      r0 = projection.rotate(); q0 = versor(r0);
      v0 = versor.cartesian(projection.invert(d3.pointer(event)));
    })
    .on("drag", event => {
      const p1 = projection.rotate(r0).invert(d3.pointer(event));
      if (!p1) return;
      projection.rotate(versor.rotation(versor.multiply(q0, versor.delta(v0, versor.cartesian(p1)))));
      render();
    });
}
```

Back hemisphere: a second orthographic with the same rotate and scale, `clipAngle(180)`, drawn first at `globalAlpha` ~0.1-0.15.
