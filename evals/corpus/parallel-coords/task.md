---
slug: parallel-coords
mode: single-shot
schema: flat-tabular
render-load: hybrid
interactivity: [brush, link]
skills: [coordination, performance, encoding]
provenance: v1-fixture
ablate-skill: patterns
---

Parallel coordinates with six numeric axes plus a sparkline summary
table. The dataset (`data/cities-synthetic.json`) is 150 synthetic
cities with correlated metrics — population, temp, elevation,
rainfall, gdp, density — and a region label spanning six regions.
Axes line up left-to-right; brushing on either the axes view or
the table view filters both.

The summary table shows, per axis, the brushed subset's min /
median / max plus a distribution sparkline. A live count badge
reports the brushed-row count. The view stays readable when only
three or four cities pass the brush.

Render-load is **hybrid**: axis lines and brushes are SVG (so the
brush rectangles are interaction-bearing DOM elements the rubric
can locate); the polylines through the axes are Canvas (each row
is one path; 150 rows × 6 axes is in the band where Canvas wins
on hover-redraw cost).

## Expected output

A horizontally-laid-out parallel-coordinates chart spans the
upper two-thirds of the viewport. Six numeric axes sit
left-to-right, each labeled (population, temp, elevation,
rainfall, gdp, density). Axis ticks are visible; tick labels are
small and spaced. Polylines connect the six axes per city, each
colored by region (six colors, categorically distinct). Brush
groups overlay each axis as draggable rectangles.

The summary table sits in the lower third, six rows (one per
axis). Each row has the axis name, three numeric cells (min,
median, max for the brushed subset), and a small inline
sparkline showing the brushed subset's distribution. A live
count badge ("23 cities") sits at the table's top-right corner
and updates as the brush changes.

When no brush is active, the count badge reads 150 and all
polylines render at default opacity. When a brush is active, the
count badge updates; non-matching polylines fade (lower opacity
or grey); matching polylines stay at full opacity. The summary
table's min/median/max and sparkline update to reflect the
brushed subset only. When only three or four cities pass the
brush, the chart and table both stay legible — sparklines
degrade gracefully to thin marks, and polylines remain visible
above the faded background.

The expected-output sketch is a *visual contract*, not a pixel
target. The rubric (dossier 04) scores aesthetics; this sketch
gives the matrix author and the harness fingerprint shared
vocabulary about what the chart *looks like*.
