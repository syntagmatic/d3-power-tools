---
slug: linked-scatterplot-matrix
mode: single-shot
schema: flat-tabular
render-load: light-svg
interactivity: [brush, link]
skills: [coordination, encoding]
provenance: v1-fixture
ablate-skill: interaction
---

Linked scatterplot matrix (SPLOM) for four biometric measurements across
three species. The dataset (`data/iris-synthetic.json`) is 150 synthetic
observations with columns `species` (setosa, versicolor, virginica),
`sepal_length`, `sepal_width`, `petal_length`, and `petal_width`. All
four numeric dimensions appear on both axes of a 4×4 panel grid. Brushing
in any panel selects the corresponding observations in all other panels.
Points are colored by species throughout.

The diagonal cells show the dimension label or a distribution summary
(histogram or density) rather than a scatter. Off-diagonal cells are
scatter plots with both axes labeled. A live count badge reports the
number of brushed observations.

Render-load is **light-svg**: 150 observations × up to 12 scatter panels
is at most 1800 circles, well within the light-SVG band.

## Expected output

A 4×4 panel grid fills the viewport. The grid's row and column dimensions
are sepal_length, sepal_width, petal_length, petal_width in order. Each
off-diagonal cell shows a scatter plot of the column dimension (x-axis)
against the row dimension (y-axis), 150 points per panel. Points use
three categorically distinct colors (one per species); a legend is visible
somewhere in the layout.

Diagonal cells show the dimension label or a distribution summary
(histogram or density estimate) for that variable. Axis tick labels are
small but legible on the outer edges of the grid. Interior axes are
optional.

A brush overlay sits on each scatter panel. When the user drags to create
a selection in any panel, the same observations are highlighted across all
other panels: matching points stay at full opacity while non-matching
points fade. The live count badge updates to report how many observations
fall inside the current selection. When no brush is active the badge reads
150.

Petal dimensions separate species clearly (setosa clusters low-left,
virginica high-right, versicolor in between). Sepal dimensions overlap
more. This structure should be visible in the rendered output.

The expected-output sketch is a *visual contract*, not a pixel target.
The rubric (dossier 04) scores aesthetics; this sketch gives the matrix
author and the harness fingerprint shared vocabulary about what the
chart *looks like*.
