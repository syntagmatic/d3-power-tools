/**
 * Morph between arbitrary SVG paths via point resampling.
 *
 * Usage:
 *   morphPaths(selection, targetPathStr, { n: 128, duration: 800 })
 *
 * Resamples source and target paths to N evenly-spaced points,
 * aligns rotation to minimize travel distance, then interpolates
 * the point arrays per frame via attrTween.
 */

/**
 * Resample any SVG path to N evenly-spaced points.
 * Uses getPointAtLength — call once before the transition, not per frame.
 */
export function resamplePath(pathStr, n = 128) {
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", pathStr);
  const len = path.getTotalLength();
  return d3.range(n).map(i => {
    const pt = path.getPointAtLength((i / n) * len);
    return [pt.x, pt.y];
  });
}

/**
 * Rotate source point array to minimize total squared distance to target.
 * O(n^2) but only runs once per morph (not per frame).
 * Prevents the "spinning" artifact from naive point interpolation.
 */
export function bestRotation(source, target) {
  const n = source.length;
  let bestOffset = 0, bestDist = Infinity;
  for (let offset = 0; offset < n; offset++) {
    let dist = 0;
    for (let i = 0; i < n; i++) {
      const j = (i + offset) % n;
      const dx = source[j][0] - target[i][0];
      const dy = source[j][1] - target[i][1];
      dist += dx * dx + dy * dy;
    }
    if (dist < bestDist) { bestDist = dist; bestOffset = offset; }
  }
  return source.map((_, i) => source[(i + bestOffset) % n]);
}

/** Convert point array back to SVG path string. */
export function pointsToPath(pts) {
  return "M" + pts.map(p => `${p[0].toFixed(2)},${p[1].toFixed(2)}`).join("L") + "Z";
}

/**
 * Morph a D3 selection's path "d" attribute to a target path string.
 *
 * @param {d3.Selection} selection - selection of <path> elements
 * @param {string} targetPathStr - SVG path string to morph to
 * @param {Object} [options]
 * @param {number} [options.n=128] - sample points (64-128 usually enough)
 * @param {number} [options.duration=800] - transition duration in ms
 * @returns {d3.Transition}
 */
export function morphPaths(selection, targetPathStr, { n = 128, duration = 800 } = {}) {
  const toPts = resamplePath(targetPathStr, n);

  return selection.transition().duration(duration)
    .attrTween("d", function() {
      const fromPts = resamplePath(d3.select(this).attr("d"), n);
      const aligned = bestRotation(fromPts, toPts);
      return t => {
        const pts = aligned.map((p, j) => [
          p[0] * (1 - t) + toPts[j][0] * t,
          p[1] * (1 - t) + toPts[j][1] * t,
        ]);
        return pointsToPath(pts);
      };
    });
}
