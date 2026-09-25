---
slug: choropleth
mode: single-shot
schema: geographic
render-load: medium-svg
interactivity: [hover]
skills: [cartography, encoding]
provenance: new
ablate-skill: maps
---

US states choropleth colored by a synthetic economic index. The dataset
(`data/us-states.json`) is a GeoJSON FeatureCollection of all 50 states
with simplified rectangular geometries. Each feature's `properties`
carries `name` (full state name), `abbr` (two-letter code), and
`economic_index` (integer 0–100). Use d3.geoAlbersUsa for the
projection so Alaska and Hawaii are inset automatically. A sequential
color scale maps economic_index to fill color; lower values use a lighter
or cooler hue, higher values a darker or warmer hue.

On hover, a tooltip appears near the cursor showing the state name,
abbreviation, and economic_index. The hovered state path gains a visible
highlight class or stroke treatment. A color-scale legend sits somewhere
in the layout.

Render-load is **medium-svg**: 50 state paths, each interactive.

## Expected output

A standard US map centered in the viewport using the Albers USA
projection. Alaska sits in the lower-left inset; Hawaii in the
lower-center inset. All 50 states are filled according to a sequential
color scale: the key visual contrast separates high-index states (MA,
CA, CT, NJ — dark) from low-index states (MS, WV, KY, AR — light).
State boundaries are visible as thin strokes separating fills.

A legend (horizontal gradient bar or discrete steps) sits below or
beside the map, labeled "Economic Index" with the low (0) and high (100)
endpoints marked.

Hovering a state shows a tooltip with the state name (e.g. "California"),
two-letter abbreviation, and economic_index value. The hovered state gains
a visible treatment — thicker border, different stroke color, or a subtle
lightening/darkening of its fill — that distinguishes it from its
neighbors. The tooltip disappears on mouseleave and the state reverts to
its normal fill.

The expected-output sketch is a *visual contract*, not a pixel target.
The rubric (dossier 04) scores aesthetics; this sketch gives the matrix
author and the harness fingerprint shared vocabulary about what the
chart *looks like*.
