// Paul Tol's Colour Schemes — colorblind-safe palettes for data visualization
// Source: https://personal.sron.nl/~pault/ (Technical Note SRON/EPS/TN/09-002 3.2)
// Usage: import into self-contained HTML via <script> tag or copy the arrays directly.

// --- Qualitative schemes (use exact colors, no interpolation) ---

export const tolBright = [
  "#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"
];

export const tolHighContrast = ["#004488", "#DDAA33", "#BB5566"];

export const tolVibrant = [
  "#EE7733", "#0077BB", "#33BBEE", "#EE3377", "#CC3311", "#009988", "#BBBBBB"
];

export const tolMuted = [
  "#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE",
  "#882255", "#44AA99", "#999933", "#AA4499"
];

export const tolLight = [
  "#77AADD", "#EE8866", "#EEDD88", "#FFAABB", "#99DDFF",
  "#44BB99", "#BBCC33", "#AAAA00", "#DDDDDD"
];

export const tolPale = [
  "#BBCCEE", "#CCEEFF", "#CCDDAA", "#EEEEBB", "#FFCCCC", "#DDDDDD"
];

export const tolDark = [
  "#222255", "#225555", "#225522", "#666633", "#663333", "#555555"
];

// --- Diverging schemes (support interpolation via d3.piecewise) ---

export const tolSunset = [
  "#364B9A", "#4A7BB7", "#6EA6CD", "#98CAE1", "#C2E4EF",
  "#EAECCC",
  "#FEDA8B", "#FDB366", "#F67E4B", "#DD3D2D", "#A50026"
];

export const tolNightfall = [
  "#125A56", "#00767B", "#238F9D", "#42A7C6", "#60BCE9",
  "#9DCCEF", "#C6DBED", "#DEE6E7", "#ECEADA",
  "#F0E6B2", "#F9D576", "#FFB954", "#FD9A44", "#F57634",
  "#E94C1F", "#D11807", "#A01813"
];

export const tolBuRd = [
  "#2166AC", "#4393C3", "#92C5DE", "#D1E5F0", "#F7F7F7",
  "#FDDBC7", "#F4A582", "#D6604D", "#B2182B"
];

export const tolPRGn = [
  "#762A83", "#9970AB", "#C2A5CF", "#E7D4E8", "#F7F7F7",
  "#D9F0D3", "#ACD39E", "#5AAE61", "#1B7837"
];

// --- Sequential schemes (support interpolation via d3.piecewise) ---

export const tolYlOrBr = [
  "#FFFFE5", "#FFF7BC", "#FEE391", "#FEC44F", "#FB9A29",
  "#EC7014", "#CC4C02", "#993404", "#662506"
];

export const tolIridescent = [
  "#FEFBE9", "#FCF7D5", "#F5F3C1", "#EAF0B5", "#DDECBF",
  "#D0E7CA", "#C2E3D2", "#B5DDD8", "#A8D8DC", "#9BD2E1",
  "#8DCBE4", "#81C4E7", "#7BBCE7", "#7EB2E4", "#88A5DD",
  "#9398D2", "#9B8AC4", "#9D7DB2", "#9A709E", "#906388",
  "#805770", "#684957", "#46353A"
];

export const tolIncandescent = [
  "#CEFFFF", "#C6F7D6", "#A2F49B", "#BBE453", "#D5CE04",
  "#E7B503", "#F19903", "#F6790B", "#F94902", "#E40515",
  "#A80003"
];

// --- Bad-data colors (for missing/null values) ---

export const tolBadColor = {
  bright: "#BBBBBB",
  highContrast: "#BBBBBB",
  vibrant: "#BBBBBB",
  muted: "#DDDDDD",
  light: "#DDDDDD",
  pale: "#DDDDDD",
  dark: "#555555",
  sunset: "#FFFFFF",
  nightfall: "#FFFFFF",
  buRd: "#FFEE99",
  prGn: "#FFEE99",
  ylOrBr: "#888888",
  iridescent: "#999999",
  incandescent: "#888888",
};

// --- Bivariate palettes (Joshua Stevens, 2015) ---
// Curated 3×3 grids for bivariate choropleth maps. Row-major, low-low first.
// Grid: [low-low, mid-low, high-low, low-mid, mid-mid, high-mid, low-high, mid-high, high-high]

export const bivariatePinkBlue = [
  "#e8e8e8", "#ace4e4", "#5ac8c8",
  "#dfb0d6", "#a5add3", "#5698b9",
  "#be64ac", "#8c62aa", "#3b4994"
];

export const bivariateGreenBlue = [
  "#e8e8e8", "#b5c0da", "#6c83b5",
  "#b8d6be", "#90b2b3", "#567994",
  "#73ae80", "#5a9178", "#2a5a5b"
];

export const bivariatePurpleGold = [
  "#e8e8e8", "#e4d9ac", "#c8b35a",
  "#cbb8d7", "#c8ada0", "#af8e53",
  "#9972af", "#976b82", "#804d36"
];

export const bivariateBlueRed = [
  "#e8e8e8", "#e4acac", "#c85a5a",
  "#b0d5df", "#ad9ea5", "#985356",
  "#64acbe", "#627f8c", "#574249"
];

// --- Scheme lookup ---

const qualitativeSchemes = {
  bright: tolBright,
  highContrast: tolHighContrast,
  vibrant: tolVibrant,
  muted: tolMuted,
  light: tolLight,
  pale: tolPale,
  dark: tolDark,
};

const divergingSchemes = {
  sunset: tolSunset,
  nightfall: tolNightfall,
  buRd: tolBuRd,
  prGn: tolPRGn,
};

const sequentialSchemes = {
  ylOrBr: tolYlOrBr,
  iridescent: tolIridescent,
  incandescent: tolIncandescent,
};

// --- D3 scale constructors ---
// These require d3 to be available globally or passed as an argument.

/**
 * Create a d3.scaleOrdinal with a Tol qualitative scheme.
 * Returns null for missing/empty values using the scheme's bad-data color.
 *
 *   const color = tolOrdinal("bright");
 *   color("A") // "#4477AA"
 *   color(null) // "#BBBBBB"
 */
export function tolOrdinal(name, d3ref = globalThis.d3) {
  const scheme = qualitativeSchemes[name];
  if (!scheme) throw new Error(`Unknown qualitative scheme: ${name}`);
  const bad = tolBadColor[name];
  const scale = d3ref.scaleOrdinal(scheme);
  return Object.assign(
    (v) => (v == null || v === "") ? bad : scale(v),
    { ...scale, range: () => scheme, badColor: bad, copy: () => tolOrdinal(name, d3ref) }
  );
}

/**
 * Create a d3.scaleSequential from a Tol sequential scheme using Lab interpolation.
 *
 *   const color = tolSequential("iridescent", [0, 100]);
 *   color(50) // interpolated mid-value
 */
export function tolSequential(name, domain = [0, 1], d3ref = globalThis.d3) {
  const scheme = sequentialSchemes[name];
  if (!scheme) throw new Error(`Unknown sequential scheme: ${name}`);
  const interpolator = d3ref.piecewise(d3ref.interpolateLab, scheme);
  return d3ref.scaleSequential(interpolator).domain(domain);
}

/**
 * Create a d3.scaleDiverging from a Tol diverging scheme using Lab interpolation.
 *
 *   const color = tolDiverging("sunset", [-1, 0, 1]);
 *   color(0) // midpoint color
 */
export function tolDiverging(name, domain = [0, 0.5, 1], d3ref = globalThis.d3) {
  const scheme = divergingSchemes[name];
  if (!scheme) throw new Error(`Unknown diverging scheme: ${name}`);
  const interpolator = d3ref.piecewise(d3ref.interpolateLab, scheme);
  return d3ref.scaleDiverging(interpolator).domain(domain);
}
