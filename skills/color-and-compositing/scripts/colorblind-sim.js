// Colorblind simulation using Brettel, Viénot & Mollon (1997) dichromacy transforms.
// Simulates how colors appear to viewers with protanopia, deuteranopia, or tritanopia.

// sRGB → linear RGB
function linearize(c) {
  c /= 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

// linear RGB → sRGB
function delinearize(c) {
  c = Math.max(0, Math.min(1, c));
  return Math.round((c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055) * 255);
}

// Simulation matrices (Viénot, Brettel & Mollon 1999 — simplified 3x3 form)
const matrices = {
  protanopia: [
    0.152286, 1.052583, -0.204868,
    0.114503, 0.786281,  0.099216,
   -0.003882, -0.048116, 1.051998
  ],
  deuteranopia: [
    0.367322, 0.860646, -0.227968,
    0.280085, 0.672501,  0.047413,
   -0.011820, 0.042940,  0.968881
  ],
  tritanopia: [
    1.255528, -0.076749, -0.178779,
   -0.078411,  0.930809,  0.147602,
    0.004733,  0.691367,  0.303900
  ]
};

/**
 * Simulate dichromatic vision for a single pixel.
 * @param {number} r - Red (0-255)
 * @param {number} g - Green (0-255)
 * @param {number} b - Blue (0-255)
 * @param {"protanopia"|"deuteranopia"|"tritanopia"} type
 * @returns {[number, number, number]} Simulated [r, g, b] (0-255)
 */
export function simulateDichromacy(r, g, b, type) {
  const m = matrices[type];
  if (!m) throw new Error(`Unknown type: ${type}`);
  const lr = linearize(r), lg = linearize(g), lb = linearize(b);
  return [
    delinearize(m[0] * lr + m[1] * lg + m[2] * lb),
    delinearize(m[3] * lr + m[4] * lg + m[5] * lb),
    delinearize(m[6] * lr + m[7] * lg + m[8] * lb)
  ];
}

/**
 * Apply dichromacy simulation to an entire ImageData buffer in-place.
 * @param {ImageData} imageData
 * @param {"protanopia"|"deuteranopia"|"tritanopia"} type
 */
export function applySimulationToImageData(imageData, type) {
  const m = matrices[type];
  if (!m) throw new Error(`Unknown type: ${type}`);
  const d = imageData.data;
  for (let i = 0; i < d.length; i += 4) {
    const lr = linearize(d[i]), lg = linearize(d[i + 1]), lb = linearize(d[i + 2]);
    d[i]     = delinearize(m[0] * lr + m[1] * lg + m[2] * lb);
    d[i + 1] = delinearize(m[3] * lr + m[4] * lg + m[5] * lb);
    d[i + 2] = delinearize(m[6] * lr + m[7] * lg + m[8] * lb);
    // alpha unchanged
  }
}

/**
 * Render a colorblind simulation of one canvas onto another.
 * @param {HTMLCanvasElement} srcCanvas
 * @param {HTMLCanvasElement} dstCanvas
 * @param {"protanopia"|"deuteranopia"|"tritanopia"} type
 */
export function colorblindPreview(srcCanvas, dstCanvas, type) {
  dstCanvas.width = srcCanvas.width;
  dstCanvas.height = srcCanvas.height;
  const srcCtx = srcCanvas.getContext("2d");
  const dstCtx = dstCanvas.getContext("2d");
  const imageData = srcCtx.getImageData(0, 0, srcCanvas.width, srcCanvas.height);
  applySimulationToImageData(imageData, type);
  dstCtx.putImageData(imageData, 0, 0);
}
