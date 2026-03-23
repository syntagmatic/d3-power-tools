// Alpha/opacity math for overlapping translucent elements.
// Standard Porter-Duff source-over compositing: each layer contributes
// (1 - accumulated_alpha) * element_alpha to the result.

/**
 * Resulting opacity when n elements at the same alpha overlap.
 * Formula: 1 - (1 - a)^n
 *
 * @param {number} alpha - Per-element alpha (0-1)
 * @param {number} n - Number of overlapping elements
 * @returns {number} Combined opacity (0-1)
 */
export function resultingOpacity(alpha, n) {
  return 1 - Math.pow(1 - alpha, n);
}

/**
 * Solve for per-element alpha to achieve a target opacity with n overlaps.
 * Inverse of resultingOpacity: a = 1 - (1 - target)^(1/n)
 *
 * Example: "I expect up to 50 overlapping points and want the densest
 * region to be 90% opaque" → alphaFromOverlap(0.9, 50) ≈ 0.045
 *
 * @param {number} targetOpacity - Desired combined opacity (0-1)
 * @param {number} n - Expected number of overlapping elements
 * @returns {number} Per-element alpha (0-1)
 */
export function alphaFromOverlap(targetOpacity, n) {
  return 1 - Math.pow(1 - targetOpacity, 1 / n);
}

/**
 * Generate a reference table of resulting opacities.
 *
 * @param {number[]} alphas - Alpha values for rows
 * @param {number[]} counts - Overlap counts for columns
 * @returns {{ alphas: number[], counts: number[], table: number[][] }}
 */
export function alphaTable(
  alphas = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20],
  counts = [1, 5, 10, 25, 50, 100]
) {
  const table = alphas.map(a => counts.map(n => resultingOpacity(a, n)));
  return { alphas, counts, table };
}
