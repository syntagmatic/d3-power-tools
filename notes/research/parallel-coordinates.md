# Parallel Coordinates: Geometric Foundations

Research into Alfred Inselberg's mathematical foundations for parallel coordinates, focusing on point-line duality, hyperplane representation, and duality-based interactions.

Primary sources: Inselberg, "The Plane with Parallel Coordinates" (1985), "Parallel Coordinates: Visual Multidimensional Geometry and Its Applications" (Springer, 2009).

---

## Point-Line Duality

### The Fundamental Theorem

In a parallel coordinate system with two vertical axes X1 and X2 separated by distance d:

**Point to polyline**: A point P = (p1, p2) in Cartesian 2-space maps to a line segment in PC connecting position p1 on axis X1 to position p2 on axis X2. The equation of this line (treating the PC plane as having horizontal coordinate x and vertical coordinate y) is:

```
y = ((p2 - p1) / d) * x + p1
```

This generalizes to N dimensions: a point P = (p1, p2, ..., pN) maps to a **polyline** connecting the N values on N parallel axes.

**Line to point (convergence)**: A line in Cartesian space x2 = m*x1 + b maps to a **point** in the PC plane. All points on this Cartesian line produce PC line segments that converge at a single point. With d = 1 (unit axis spacing), the convergence point is:

```
rho = (1/(1-m), b/(1-m))
```

This is the **indexed point** representing the line.

### Derivation

Consider two points on the Cartesian line x2 = m*x1 + b: point A = (a1, m*a1 + b) and point B = (b1, m*b1 + b). Their PC representations are two line segments:
- Segment A connects (0, a1) to (d, m*a1 + b)
- Segment B connects (0, b1) to (d, m*b1 + b)

These segments intersect at a point whose position depends only on m and b, not on the particular points chosen. Setting the two line equations equal and solving:

```
((m*a1 + b - a1)/d) * x + a1 = ((m*b1 + b - b1)/d) * x + b1
```

The a1 and b1 terms cancel from the coefficient of x (both give (m-1)/d), leaving the intersection at x = d/(1-m), y = b/(1-m). With d = 1: rho = (1/(1-m), b/(1-m)).

### Geometric Interpretation of the Convergence Point

The **horizontal position** of the convergence point depends only on the slope m:
- **m < 0** (negative correlation): convergence falls **between the axes** (0 < 1/(1-m) < 1). At m = -1, exactly at the midpoint.
- **m = 0**: convergence is on the right axis (x = 1). The line is horizontal; all PC segments fan from different heights on X1 to the same height b on X2.
- **0 < m < 1**: convergence is **right of X2** (x > 1).
- **m = 1**: segments are **parallel** (no intersection; convergence at infinity). This is the projective case -- the line x2 = x1 + b maps to a family of parallel segments in PC.
- **m > 1**: convergence is **left of X1** (x < 0).
- **m = -infinity or +infinity**: convergence approaches the left axis.

The **vertical position** b/(1-m) encodes the intercept.

This is why the foundations are projective rather than Euclidean: the m = 1 case (parallel segments) corresponds to a point at infinity, which projective geometry handles naturally.

### Rotation-Translation Duality

Under this mapping:
- **Rotation** in Cartesian space (changing slope m) corresponds to **translation** of the convergence point horizontally in PC.
- **Translation** in Cartesian space (changing intercept b) corresponds to **vertical movement** of the convergence point.

This is a remarkable swap: rigid motions in one space become different rigid motions in the other.

---

## Lines and Hyperplanes in Parallel Coordinates

### Lines in R^N

A line in N-dimensional space is determined by a direction and a point. Its representation in PC with N axes:

**A set of points on a line in N-space transforms to a set of polylines in PC, all intersecting at exactly N-1 points** -- one indexed point between each pair of adjacent axes.

These N-1 indexed points fully characterize the line. The i-th indexed point (between axes Xi and Xi+1) is the convergence of the projected relationship between dimensions i and i+1 along the line.

A line in R^N has 2(N-1) degrees of freedom in general (direction + point), and N-1 indexed points each with 2 coordinates gives 2(N-1) parameters -- a perfect encoding.

### Planes and p-Flats

A **plane** (2-flat) in R^N is detected visually: for all pairs of points on the plane, compute the two-point line representations (each giving N-1 indexed points connected by line segments). If the plane exists, these indexed-point line segments between each adjacent axis pair will all pass through a common point.

More generally, a **p-flat** (p-dimensional plane) in N-space is represented by indexed points where the number of indices and their arrangement depends on p and N. The key visual signature is the structure of convergences:
- Line (1-flat): N-1 fixed indexed points
- Plane (2-flat): indexed line segments between each axis pair, all passing through common indexed points
- Hyperplane ((N-1)-flat): a characteristic pattern of constrained indexed points

### Hyperplane Representation

An N-dimensional hyperplane (defined by a0 + a1*x1 + a2*x2 + ... + aN*xN = 0) creates a specific pattern: because the hyperplane imposes one linear constraint on N variables, the polylines of points on the hyperplane are constrained. Between each adjacent pair of axes, the convergence points of all 2D projected lines lie along a curve (specifically, along lines in the indexed-point space). The visual signature is that polylines, rather than filling the full space, form a structured pattern with N-1 constraints visible as convergence alignments.

### Envelope Representation of Curves and Surfaces

A smooth curve in R^2 is represented in PC not by a single line but by the **envelope** of the family of lines representing its tangent lines. Each tangent line at each point maps to a convergence point; as the point moves along the curve, the convergence point traces a curve in the PC plane. The original curve's shape is encoded in this envelope curve.

Key duality properties of envelopes:
- **Cusp in Cartesian <-> inflection point in PC** (and vice versa). This is independent of the curve's orientation.
- **Inflection point in Cartesian <-> cusp in PC**
- A **convex curve** in Cartesian maps to a specific envelope pattern (no cusps in the envelope between the axes)

For higher dimensions, the representation of a smooth hypersurface in R^N is obtained as the envelope of its tangent hyperplanes. A 3D surface is represented by two linked planar regions consisting of the pairs of indexed points representing all its tangent planes.

---

## Angular Brushing via Duality

### What Angular Brushing Is

Standard axis brushing selects a **range on one axis** -- this selects data points whose value on that dimension falls in the range. It exploits no duality.

**Angular brushing** selects a **region between two adjacent axes** -- typically a wedge or triangular region. This selects all polyline segments that pass through the region. Because of point-line duality, this is equivalent to selecting a set of **lines** (relationships between two variables) in the dual Cartesian space.

### The Geometric Mechanism

Between axes Xi and Xi+1, each data row's polyline segment has a slope determined by the ratio (xi+1 - xi)/d. The slope of the segment encodes the relationship between the two variables.

Angular brushing selects segments by their **angle** (slope). When a user defines an angular range [theta1, theta2] between two axes:
1. This selects all polyline segments whose slope falls in the corresponding range
2. In the dual Cartesian space, this selects all points that lie on lines with slopes in a specific range
3. The selected region in the dual scatterplot is a **wedge-shaped** region emanating from the convergence point

This is precisely the "pinch" or "strum" interaction.

### The Pinch/Strum Interaction

The **strum** (as implemented in d3.parcoords) works by drawing a line segment between two axes. A data polyline is selected if its segment between those axes **intersects** the strum line.

Geometrically: the strum line defines a point in the dual Cartesian space (by the convergence formula). All data polylines that intersect the strum line correspond to data points that are "near" this dual point in a specific sense -- they lie on lines that pass near the strum line's endpoints.

The **pinch** variant uses **two** strum lines (or a triangular/trapezoidal region), defining a wedge between two axes. This selects polyline segments that pass through the wedge. In the dual space, this selects points in a bounded region -- the intersection of the half-planes defined by the two boundary lines.

### Why Duality Makes It Work

1. **Range brush on one axis**: selects a slab in data space (all points where xi is in [a, b]). No duality needed.
2. **Strum/intersection brush between axes**: selects points based on the **relationship** between two variables. A single strum line selects lines (in the dual) that pass through a point -- equivalently, data rows where a specific linear combination of xi and xi+1 is constrained.
3. **Angular brush (wedge)**: selects points based on the **slope** of the relationship -- i.e., the ratio xi+1/xi falls in a range. This is a "rational data property" (depends on two dimensions inseparably).

Without duality, you would need two separate range brushes and would only get rectangular selections in the (xi, xi+1) scatterplot. Angular brushing gives you wedge-shaped selections -- selecting by slope/angle rather than by range -- which is strictly more expressive for identifying correlations and trends.

### Multi-Touch Angular Brushing

The natural gesture mapping (Kosara, 2010):
- **Two fingers on one axis**: range brush
- **Three fingers spanning two adjacent axes**: angular brush (one finger on each axis defines the range endpoints; the angle between them defines the slope constraint)
- **Four fingers**: simultaneous brushing on two axes

The three-finger angular brush is the "pinch" -- the physical gesture mirrors the geometric operation of constraining the wedge between two axes.

### Angular Brush in the SVM Explorer Pattern

The SVM hyperplane explorer demonstrates angular brushing with a linked scatterplot:
1. In the PC view, an angular brush between axes Xi and Xi+1 selects a wedge region
2. In the linked scatterplot of (xi, xi+1), the selected region appears as a wedge/sector emanating from a point
3. This point is the **dual** of the strum line -- computed via the convergence formula
4. The angular brush's boundaries in PC map to lines through the dual point in the scatterplot

This demonstrates the duality concretely: an angular region in PC (selecting segments by slope) corresponds to a wedge in the scatterplot (selecting points by direction from a center).

---

## Convexity and Topology

### Convexity-Hstar Duality

Inselberg's 1985 paper establishes a duality between:
- **Bounded convex sets** in Cartesian space <-> **hstars** (a generalization of hyperbolas) in PC
- **Unbounded convex sets** <-> bounded hstars

An **hstar** is a family of curves in the PC plane that generalizes the hyperbola. When a bounded convex region (e.g., a disk or ellipse) is represented in PC, its boundary maps to an envelope that forms an hstar pattern between adjacent axes.

### Visual Signatures of Convexity

The boundary of a convex set, being a convex curve, maps to an envelope in PC with specific properties:
- No cusps in the envelope between the axes (since cusps correspond to inflection points, and convex curves have none)
- The envelope is "one-sided" -- all polylines from interior points pass on one side of the envelope

This means **convexity is visually recognizable** in PC: look for envelope patterns without cusps.

### Union-Intersection Duality

- **Convex union** in Cartesian <-> **intersection** of regions in PC
- **Convex intersection** in Cartesian <-> **union** of regions in PC

This is useful for set operations on clusters.

### Ellipse-Hyperbola Correspondence

A specific and practically important case: an **elliptical cluster** in (xi, xi+1) scatterplot space appears as a **hyperbolic pattern** in the PC plane between axes Xi and Xi+1. This is because the ellipse boundary (a convex curve) maps to an hstar (generalized hyperbola) via the envelope construction.

This means: when you see hyperbolic "bowtie" patterns between adjacent axes in PC, you are looking at elliptical clusters in the projected 2D subspace. Tight bowties = tight clusters; wide bowties = dispersed clusters.

### Normal Distribution Signature

Normally distributed data in two dimensions forms an elliptical concentration contour. In PC, this produces the characteristic **hyperbolic envelope** pattern -- the bowtie shape. The width of the bowtie at the waist corresponds to the correlation strength; the orientation of the bowtie indicates the sign of correlation.

### Topological Properties

Crossing patterns between axes encode relationships:
- **Parallel segments** (no crossings): strong positive correlation
- **X-pattern crossings**: negative correlation (lines cross between axes)
- **Random crossings**: no correlation
- **Convergence to a point**: all data lies on a line (perfect linear relationship)

These are not just visual heuristics -- they are consequences of the duality theory. The crossing pattern is determined by the slope distribution, which is determined by the joint distribution of the two variables.

---

## Intersection Points as Edge Representation

### The 24-Cell Pattern

The 24-cell is a regular 4-polytope with 24 vertices, 96 edges, 96 triangular faces, and 24 octahedral cells. When its vertices are displayed in PC (4 axes for 4 dimensions), each vertex becomes a polyline through 4 axes.

**Each edge** of the 24-cell connects two vertices. The two endpoint polylines intersect at specific points between adjacent axes. These intersection points **are** the edge's representation in the dual -- each edge (a line segment in 4D) is fully characterized by its 3 indexed points (N-1 = 3 for N = 4 dimensions).

This is a direct application of the line representation theorem: a line in N-space is represented by N-1 indexed points. An edge is a line segment, so its line is represented by 3 indexed points. To identify which edges exist, you look for intersections of vertex polylines.

### Why This Works

For two vertex polylines to intersect between axes Xi and Xi+1, the projected relationship between their coordinates in dimensions i and i+1 must satisfy a specific linear constraint. If vertices A and B are connected by an edge, then the line through A and B in R^4 projects to a convergence point between each pair of adjacent axes. The polylines of A and B must pass through these convergence points.

The visual result: edges appear as clusters of intersection points between vertex polylines. For a regular polytope like the 24-cell, the symmetry means these intersection points form regular patterns.

### Generalization to Arbitrary Graphs in N-Space

For any graph embedded in N-dimensional space (vertices at points, edges as line segments):
1. Each vertex maps to a polyline (N values on N axes)
2. Each edge maps to N-1 indexed points (intersections of endpoint polylines)
3. To **find** edges: look for polyline intersections between adjacent axes
4. To **highlight** an edge: draw the N-1 indexed points or highlight the two endpoint polylines

This makes PC a natural tool for visualizing graph structure in high-dimensional embeddings.

---

## Implications for Interaction Design

### Duality-Enabled Interactions Beyond Standard Brushing

The duality theory suggests several interactions that standard PC implementations rarely provide:

**1. Convergence Point Brushing (Line Selection)**
Instead of selecting ranges on axes (which selects by value), select regions in the **space between axes** (which selects by relationship). This is the angular/strum brush, but it can be generalized:
- Click a point between axes to select all lines passing through it (all data rows with that specific linear relationship)
- Drag to define a region between axes to select a family of related linear relationships

**2. Dual View Linking**
Show a scatterplot alongside the PC. Regions selected in PC (angular brush) should highlight the corresponding wedge in the scatterplot. Regions selected in the scatterplot should highlight the corresponding convergence pattern in PC. The mapping is the convergence formula rho = (d/(1-m), b/(1-m)).

**3. Envelope Visualization**
For each pair of adjacent axes, compute and display the envelope of the line family. This shows the boundary of the data distribution's support in the dual representation. Tight envelopes = strong linear relationship; no envelope structure = independence.

**4. Intersection Point Overlay**
For datasets where rows represent vertices of a graph (e.g., polytope vertices), compute and display intersection points. Each intersection point between axes Xi and Xi+1 represents a potential edge. Color or size-code by whether the edge exists in the graph.

**5. Hyperplane Detection**
Given a suspected hyperplane in the data (e.g., from a classifier), compute its indexed-point representation and overlay it on the PC. This shows the decision boundary as a structured pattern among the convergence points, making it visually comparable to the data distribution.

**6. Slope Histogram Between Axes**
For each pair of adjacent axes, compute the distribution of slopes. Display as a histogram or density in the margin between axes. Peaks correspond to common linear relationships; the histogram is the marginal of the convergence point distribution.

---

## Code Patterns

### Computing the Convergence Point

```js
/**
 * Given a line x2 = m * x1 + b in Cartesian space,
 * compute its convergence (indexed) point in parallel coordinates.
 *
 * @param {number} m - slope of the Cartesian line
 * @param {number} b - intercept of the Cartesian line
 * @param {number} d - distance between the two parallel axes (default 1)
 * @returns {{ x: number, y: number }} convergence point in PC plane
 */
function convergencePoint(m, b, d = 1) {
  if (Math.abs(m - 1) < 1e-10) {
    // m = 1: parallel segments, convergence at infinity
    return { x: Infinity, y: Infinity };
  }
  return {
    x: d / (1 - m),
    y: b / (1 - m)
  };
}
```

### Computing Indexed Points from Two Data Points

```js
/**
 * Given two data points (polylines in PC), compute the intersection
 * (indexed point) between each pair of adjacent axes.
 * This represents the line through the two points in data space.
 *
 * @param {number[]} a - first data point [a1, a2, ..., aN]
 * @param {number[]} b - second data point [b1, b2, ..., bN]
 * @param {Function[]} scales - array of N y-scales (data -> pixel)
 * @param {number[]} axisX - array of N x-positions of axes
 * @returns {{ x: number, y: number }[]} N-1 indexed points
 */
function indexedPoints(a, b, scales, axisX) {
  const points = [];
  for (let i = 0; i < a.length - 1; i++) {
    const x1 = axisX[i], x2 = axisX[i + 1];
    const ya1 = scales[i](a[i]), ya2 = scales[i + 1](a[i + 1]);
    const yb1 = scales[i](b[i]), yb2 = scales[i + 1](b[i + 1]);

    // Line A: from (x1, ya1) to (x2, ya2)
    // Line B: from (x1, yb1) to (x2, yb2)
    const denom = (ya1 - ya2) - (yb1 - yb2);
    if (Math.abs(denom) < 1e-10) {
      // Parallel segments (same slope in this axis pair)
      points.push(null);
    } else {
      const t = (ya1 - yb1) / denom;
      points.push({
        x: x1 + t * (x2 - x1),
        y: ya1 + t * (ya2 - ya1)
      });
    }
  }
  return points;
}
```

### Strum (Intersection) Brush

```js
/**
 * Test whether a data row's polyline segment between two axes
 * intersects a user-drawn strum line.
 *
 * @param {number} x1 - x position of left axis
 * @param {number} x2 - x position of right axis
 * @param {number} ya - data value on left axis (pixel y)
 * @param {number} yb - data value on right axis (pixel y)
 * @param {{ x1: number, y1: number, x2: number, y2: number }} strum
 * @returns {boolean}
 */
function intersectsStrum(x1, x2, ya, yb, strum) {
  // Segment P: (x1, ya) -> (x2, yb)
  // Segment Q: (strum.x1, strum.y1) -> (strum.x2, strum.y2)
  return segmentsIntersect(
    x1, ya, x2, yb,
    strum.x1, strum.y1, strum.x2, strum.y2
  );
}

/**
 * Standard 2D segment-segment intersection test.
 * Returns true if segments (ax1,ay1)-(ax2,ay2) and (bx1,by1)-(bx2,by2) cross.
 */
function segmentsIntersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2) {
  const d1 = cross(bx2 - bx1, by2 - by1, ax1 - bx1, ay1 - by1);
  const d2 = cross(bx2 - bx1, by2 - by1, ax2 - bx1, ay2 - by1);
  const d3 = cross(ax2 - ax1, ay2 - ay1, bx1 - ax1, by1 - ay1);
  const d4 = cross(ax2 - ax1, ay2 - ay1, bx2 - ax1, by2 - ay1);
  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
      ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
    return true;
  }
  // Collinear cases omitted for brevity
  return false;
}

function cross(ux, uy, vx, vy) {
  return ux * vy - uy * vx;
}
```

### Angular Brush (Wedge Selection)

```js
/**
 * Angular brush: select polyline segments whose slope between
 * two adjacent axes falls in [slopeMin, slopeMax].
 *
 * The slope of a polyline segment between axes at x-positions
 * axX1 and axX2, with y-values y1 and y2, is (y2 - y1) / (axX2 - axX1).
 *
 * In the dual scatterplot, this selects a wedge of angles.
 */
function angularBrush(data, dim1, dim2, scales, axisX, slopeRange) {
  const [slopeMin, slopeMax] = slopeRange;
  const dx = axisX[dim2] - axisX[dim1];

  return data.filter(d => {
    const y1 = scales[dim1](d[dim1]);
    const y2 = scales[dim2](d[dim2]);
    const slope = (y2 - y1) / dx;
    return slope >= slopeMin && slope <= slopeMax;
  });
}
```

### Convergence Point Visualization (Dual Overlay)

```js
/**
 * For each pair of adjacent axes, compute the convergence point
 * from a fitted line. Render as circles between axes.
 * Shows where linear relationships "focus" in the PC plane.
 */
function renderConvergencePoints(svg, regressions, scales, axisX, dimensions) {
  const points = [];

  for (let i = 0; i < dimensions.length - 1; i++) {
    const { slope, intercept } = regressions[i]; // from data space
    // Map the Cartesian line to a convergence in pixel space
    // Need to compose with the scales: the PC "line" for data point (v1, v2)
    // goes from (axisX[i], scales[i](v1)) to (axisX[i+1], scales[i+1](v2))
    // The convergence is where all these segments meet.

    // Compute two data-space points on the regression line
    const v1a = 0, v2a = slope * v1a + intercept;
    const v1b = 1, v2b = slope * v1b + intercept;

    const indexed = indexedPoints(
      [v1a, v2a], [v1b, v2b],
      [scales[i], scales[i + 1]],
      [axisX[i], axisX[i + 1]]
    );

    if (indexed[0]) {
      points.push({ ...indexed[0], axisLeft: i, axisRight: i + 1 });
    }
  }

  svg.selectAll(".convergence-point")
    .data(points)
    .join("circle")
      .attr("class", "convergence-point")
      .attr("cx", d => d.x)
      .attr("cy", d => d.y)
      .attr("r", 4)
      .attr("fill", "red")
      .attr("opacity", 0.7);
}
```

### Edge Visualization via Indexed Points (Polytope Pattern)

```js
/**
 * Given vertices of a polytope and an edge list, compute and render
 * indexed points (edge representations) between adjacent axes.
 *
 * Each edge (pair of vertices) produces N-1 indexed points.
 * These are the intersection points of the two vertex polylines.
 */
function renderEdgeIndexedPoints(ctx, vertices, edges, scales, axisX, dims) {
  ctx.fillStyle = "rgba(255, 80, 80, 0.5)";

  for (const [vi, vj] of edges) {
    const a = dims.map(d => vertices[vi][d]);
    const b = dims.map(d => vertices[vj][d]);
    const pts = indexedPoints(a, b, scales, axisX);

    for (const pt of pts) {
      if (pt) {
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
}
```

---

## Sources

- [Inselberg, "The Plane with Parallel Coordinates" (1985)](https://link.springer.com/article/10.1007/BF01898350)
- [Inselberg, "Parallel Coordinates: Visual Multidimensional Geometry and Its Applications" (Springer, 2009)](https://link.springer.com/book/10.1007/978-0-387-68628-8)
- [Inselberg, "Parallel Coordinates for Visualizing Multi-Dimensional Geometry"](https://link.springer.com/chapter/10.1007/978-4-431-68057-4_3)
- [Inselberg Lecture Notes (2012)](https://data.scitevents.org/Documents/Previous_Invited_Speakers/2012/DATA2012_Inselberg.pdf)
- [Inselberg project page (Cornell)](https://people.ece.cornell.edu/land/PROJECTS/Inselberg/)
- [Parallel Coordinates - Wikipedia](https://en.wikipedia.org/wiki/Parallel_coordinates)
- [Thill, "Visualizing High-Dimensional Data Using Parallel Coordinates" (2025)](https://markusthill.github.io/blog/2025/visualizing-high-dimensional-data-with-parallel-coordinates/)
- [Point-Line Duality tutorial (parallelcoordinates.de)](http://www.parallelcoordinates.de/blog/tutorial/2015/08/01/point-line-duality/)
- [Hauser, Ledermann, Doleisch, "Angular Brushing of Extended Parallel Coordinates" (InfoVis 2002)](https://ieeexplore.ieee.org/document/1173157/)
- [Stitz et al., "Selective Angular Brushing of Parallel Coordinate Plots" (2021)](https://www.vrvis.at/publications/pdfs/PB-VRVis-2021-016.pdf)
- [Kosara, "Multi-touch Brushing for Parallel Coordinates" (2010)](https://eagereyes.org/blog/2010/multi-touch-brushing-for-parallel-coordinates)
- [d3.parcoords intersection brushing discussion](https://github.com/syntagmatic/parallel-coordinates/issues/57)
- [Heinrich & Weiskopf, "State of the Art of Parallel Coordinates" (2013)](https://joules.de/files/heinrich_state_2013.pdf)
