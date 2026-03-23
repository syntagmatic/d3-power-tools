---
name: color-themes
description: "Theming systems for D3.js visualizations: defining and applying cohesive visual themes (light, dark, high-contrast, brand, print), CSS custom properties for runtime theme switching, semantic color tokens, theme-aware D3 scales, prefers-color-scheme auto dark mode, smooth theme transitions, multi-chart theme consistency, Canvas theming without CSS cascade, WCAG contrast compliance across themes, and common pitfalls (hardcoded colors, opacity in dark mode, SVG filter interactions). Use this skill when the user needs dark mode charts, theme switching, CSS variable-driven D3 colors, semantic design tokens for visualization, brand-themed dashboards, or accessible multi-theme chart systems."
---

# Color Themes

Cohesive visual theming for D3 charts — light mode, dark mode, brand themes, high-contrast, print. This skill covers the **system** for mapping abstract color roles to concrete values and switching between them at runtime.

Related: `color-and-compositing` (color science, palettes, compositing), `canvas-rendering` (Canvas setup), `canvas-accessibility` (ARIA).

```
theme definition (tokens)
        ↓
CSS custom properties ←→ theme switcher (JS/media query)
        ↓
D3 scales + rendering (SVG uses cascade, Canvas reads computed values)
        ↓
consistent multi-chart appearance
```

---

## Semantic Color Tokens

Define abstract roles, not concrete colors. A token like `--color-primary` means "the main data encoding color" — its value changes per theme.

### Token taxonomy for data visualization

| Token | Role | Light default | Dark default |
|-------|------|:---:|:---:|
| `--color-bg` | Chart background | `#ffffff` | `#1a1a2e` |
| `--color-surface` | Card/panel surface | `#f8f9fa` | `#16213e` |
| `--color-text` | Primary text, labels | `#212529` | `#e8e8e8` |
| `--color-text-muted` | Secondary text, annotations | `#6c757d` | `#9a9ab0` |
| `--color-axis` | Axis lines, domain | `#333333` | `#555577` |
| `--color-tick` | Tick marks | `#666666` | `#666688` |
| `--color-grid` | Grid lines | `#e9ecef` | `#2a2a4a` |
| `--color-primary` | Main data series | `#4e79a7` | `#6fa8dc` |
| `--color-secondary` | Second series | `#e15759` | `#ea8385` |
| `--color-tertiary` | Third series | `#76b7b2` | `#8fd4cf` |
| `--color-accent` | Highlights, selections | `#f28e2b` | `#f5a623` |
| `--color-danger` | Negative values, errors | `#d32f2f` | `#ef5350` |
| `--color-success` | Positive values | `#388e3c` | `#66bb6a` |
| `--color-muted` | De-emphasized elements | `#adb5bd` | `#4a4a6a` |
| `--color-annotation` | Annotation lines/text | `#e57373` | `#ef9a9a` |
| `--color-tooltip-bg` | Tooltip background | `#ffffff` | `#2d2d50` |
| `--color-tooltip-border` | Tooltip border | `#dee2e6` | `#444466` |

### Categorical series tokens

For multi-series charts, define a sequence:

```css
:root {
  --color-cat-1: #4e79a7; --color-cat-2: #f28e2b; --color-cat-3: #e15759;
  --color-cat-4: #76b7b2; --color-cat-5: #59a14f; --color-cat-6: #edc948;
  --color-cat-7: #b07aa1; --color-cat-8: #9c755f;
}
```

Access in JS:

```js
const cats = Array.from({ length: 8 }, (_, i) =>
  getComputedStyle(document.documentElement).getPropertyValue(`--color-cat-${i + 1}`).trim()
);
const color = d3.scaleOrdinal(cats);
```

---

## Theme Definitions with CSS Custom Properties

### Structure — one `:root` block per theme

```css
:root, [data-theme="light"] {
  --color-bg: #ffffff;
  --color-text: #212529;
  --color-axis: #333333;
  --color-grid: #e9ecef;
  --color-primary: #4e79a7;
  --color-secondary: #e15759;
  /* ... all tokens */
}

[data-theme="dark"] {
  --color-bg: #1a1a2e;
  --color-text: #e8e8e8;
  --color-axis: #555577;
  --color-grid: #2a2a4a;
  --color-primary: #6fa8dc;
  --color-secondary: #ea8385;
}

[data-theme="high-contrast"] {
  --color-bg: #000000;
  --color-text: #ffffff;
  --color-axis: #ffffff;
  --color-grid: #333333;
  --color-primary: #ffff00;
  --color-secondary: #00ffff;
}
```

### Applying theme

```js
document.documentElement.setAttribute("data-theme", "dark");
```

SVG elements automatically pick up custom properties via `fill`, `stroke` in CSS. But SVG attribute values (`attr("fill", ...)`) in D3 require reading the computed value — see "Theme-Aware Scales" below.

---

## Theme-Aware D3 Scales

D3 scales use JS strings, not CSS cascade. Bridge the gap by reading computed properties and rebuilding scales when the theme changes.

### Reading tokens into scales

```js
function getToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function buildColorScale(categories) {
  const colors = categories.map((_, i) => getToken(`--color-cat-${i + 1}`));
  return d3.scaleOrdinal().domain(categories).range(colors);
}

function buildAxisColors() {
  return {
    axis: getToken("--color-axis"),
    grid: getToken("--color-grid"),
    text: getToken("--color-text"),
    muted: getToken("--color-text-muted"),
  };
}
```

### Reactive theme updates

```js
function applyTheme(themeName) {
  document.documentElement.setAttribute("data-theme", themeName);

  // Rebuild scales from new token values
  const color = buildColorScale(categories);
  const { axis, grid, text } = buildAxisColors();

  // Update all SVG elements
  svg.selectAll(".bar").attr("fill", d => color(d.category));
  svg.selectAll(".axis text").attr("fill", text);
  svg.selectAll(".axis .domain, .axis line").attr("stroke", axis);
  svg.selectAll(".grid line").attr("stroke", grid);
}
```

### Alternative — CSS-driven SVG (no JS scale rebuild)

If you set SVG `fill`/`stroke` via CSS classes instead of D3 `.attr()`, the cascade handles theme switching automatically:

```css
.bar-primary { fill: var(--color-primary); }
.bar-secondary { fill: var(--color-secondary); }
.axis-line { stroke: var(--color-axis); }
.label { fill: var(--color-text); }
```

```js
svg.selectAll(".bar").data(data).join("rect")
  .attr("class", d => d.type === "A" ? "bar-primary" : "bar-secondary")
  .attr("x", d => x(d.name)).attr("width", x.bandwidth())
  .attr("y", d => y(d.value)).attr("height", d => y(0) - y(d.value));
```

Theme switches now require zero JS — just change `data-theme`. Preferred for SVG-only charts.

---

## Auto Dark Mode

### Detecting `prefers-color-scheme`

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    --color-bg: #1a1a2e;
    --color-text: #e8e8e8;
    /* ... dark tokens */
  }
}
```

The `:not([data-theme])` selector lets the media query apply only when no explicit theme is set — manual override always wins.

### JS detection for Canvas and scale rebuilds

```js
const darkMQ = matchMedia("(prefers-color-scheme: dark)");

function onSchemeChange(e) {
  if (!document.documentElement.hasAttribute("data-theme")) {
    // No manual override — follow system
    rebuildCharts(e.matches ? "dark" : "light");
  }
}

darkMQ.addEventListener("change", onSchemeChange);
// Initial
onSchemeChange(darkMQ);
```

---

## Theme Transitions

### CSS transitions on custom properties

As of 2024+, `@property`-registered custom properties can transition. For broad support, transition the elements directly:

```css
svg text, svg .domain, svg line, svg rect, svg path, svg circle {
  transition: fill 0.3s ease, stroke 0.3s ease, opacity 0.3s ease;
}
body, .chart-container {
  transition: background-color 0.3s ease, color 0.3s ease;
}
```

### D3 transitions for attribute-set colors

When D3 `.attr("fill", ...)` drives color (not CSS), animate the switch:

```js
function applyThemeAnimated(themeName, duration = 400) {
  const oldColors = readAllTokens();
  document.documentElement.setAttribute("data-theme", themeName);
  const newColors = readAllTokens();

  const t = d3.transition().duration(duration).ease(d3.easeCubicInOut);

  svg.selectAll(".bar").transition(t)
    .attr("fill", d => newColors.cat[d.category]);
  svg.selectAll(".axis text").transition(t)
    .attr("fill", newColors.text);
  svg.selectAll(".grid line").transition(t)
    .attr("stroke", newColors.grid);
}
```

### Canvas cross-fade

Canvas has no CSS cascade. Cross-fade between themes by rendering both frames and interpolating:

```js
function crossFadeCanvas(ctx, drawFn, oldTheme, newTheme, duration = 400) {
  const offscreen = new OffscreenCanvas(ctx.canvas.width, ctx.canvas.height);
  const offCtx = offscreen.getContext("2d");

  const start = performance.now();
  function frame(now) {
    const t = Math.min((now - start) / duration, 1);
    // Draw old theme at (1-t) opacity
    ctx.globalAlpha = 1;
    drawFn(ctx, oldTheme);
    ctx.globalAlpha = t;
    drawFn(offCtx, newTheme);
    ctx.drawImage(offscreen, 0, 0);
    ctx.globalAlpha = 1;
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
```

---

## Multi-Chart Consistency

### Theme context object

Share a single theme context across all charts on a page:

```js
class ThemeContext {
  constructor() {
    this._listeners = new Set();
    this._theme = "light";
  }

  get theme() { return this._theme; }

  set theme(name) {
    this._theme = name;
    document.documentElement.setAttribute("data-theme", name);
    for (const fn of this._listeners) fn(name);
  }

  subscribe(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  getToken(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  getTokens(...names) {
    return Object.fromEntries(names.map(n => [n, this.getToken(n)]));
  }
}

const theme = new ThemeContext();

// Each chart subscribes
theme.subscribe(() => barChart.update());
theme.subscribe(() => lineChart.update());
theme.subscribe(() => donutChart.update());

// Switch all at once
theme.theme = "dark";
```

### Shared scale factory

```js
function makeOrdinalScale(ctx, domain) {
  const range = domain.map((_, i) => ctx.getToken(`--color-cat-${i + 1}`));
  return d3.scaleOrdinal(domain, range);
}
```

---

## Canvas Theming

Canvas elements don't participate in the CSS cascade. Every color must be explicitly read and applied in JS.

### Pattern — read tokens before each render

```js
function drawCanvasChart(ctx, data) {
  const bg = getToken("--color-bg");
  const text = getToken("--color-text");
  const primary = getToken("--color-primary");
  const grid = getToken("--color-grid");
  const axis = getToken("--color-axis");

  // Background
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, width, height);

  // Grid
  ctx.strokeStyle = grid;
  ctx.lineWidth = 1;
  yScale.ticks(5).forEach(tick => {
    const yy = yScale(tick);
    ctx.beginPath();
    ctx.moveTo(marginLeft, yy);
    ctx.lineTo(width - marginRight, yy);
    ctx.stroke();
  });

  // Data
  ctx.fillStyle = primary;
  for (const d of data) {
    ctx.fillRect(xScale(d.name), yScale(d.value), xScale.bandwidth(), height - marginBottom - yScale(d.value));
  }

  // Axis labels
  ctx.fillStyle = text;
  ctx.font = "12px sans-serif";
  ctx.textAlign = "center";
  // ... draw tick labels
}
```

### Cache tokens to avoid layout thrash

`getComputedStyle` triggers layout. Cache tokens at theme-switch time, not per frame:

```js
let cachedTokens = {};
function cacheTokens() {
  const style = getComputedStyle(document.documentElement);
  for (const name of tokenNames) {
    cachedTokens[name] = style.getPropertyValue(name).trim();
  }
}
// Call cacheTokens() once per theme switch, then use cachedTokens in render loops.
```

---

## Accessible Theme Design

### Contrast requirements (WCAG 2.1)

| Element | Minimum ratio | Standard |
|---------|:-:|----------|
| Body text, axis labels | 4.5:1 | AA normal |
| Large text (≥18px / ≥14px bold) | 3:1 | AA large |
| UI components, data marks against bg | 3:1 | AA non-text |
| Enhanced (AAA) | 7:1 | Prefer for critical data |

### Checking contrast at theme-switch time

```js
function checkContrast(fg, bg, minRatio = 4.5) {
  const lum = hex => {
    const [r, g, b] = [1, 3, 5].map(i => {
      const c = parseInt(hex.slice(i, i + 2), 16) / 255;
      return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const l1 = lum(fg), l2 = lum(bg);
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  return { ratio, passes: ratio >= minRatio };
}

// Validate all text tokens against background on theme switch
function validateTheme() {
  const bg = getToken("--color-bg");
  const textTokens = ["--color-text", "--color-text-muted", "--color-axis", "--color-tick"];
  for (const t of textTokens) {
    const { ratio, passes } = checkContrast(getToken(t), bg);
    if (!passes) console.warn(`${t} contrast ${ratio.toFixed(1)}:1 fails WCAG AA against bg`);
  }
}
```

### High-contrast theme design

- Background: pure black `#000000`
- Text: pure white `#ffffff`
- Data colors: saturated, high-lightness — yellow `#ffff00`, cyan `#00ffff`, magenta `#ff00ff`, green `#00ff00`
- Grid: `#333333` (subtle but visible)
- Minimum stroke width: 2px (thin lines vanish on high-DPI)
- No reliance on opacity for differentiation — use solid colors

### Print theme

```css
@media print {
  :root {
    --color-bg: #ffffff;
    --color-text: #000000;
    --color-axis: #000000;
    --color-grid: #cccccc;
    --color-primary: #000000;
    --color-secondary: #666666;
    --color-tertiary: #999999;
  }
}
```

Print themes should use high contrast, minimal color (grayscale or limited palette), and heavier stroke widths. Pair with `patterned-fills` skill for color-free data encoding.

---

## Brand Themes

### Mapping brand colors to data roles

Never use brand colors directly for all data marks — they often lack sufficient differentiation. Instead:

1. **Primary brand color** → `--color-primary` (main series, key metric)
2. **Secondary brand color** → `--color-accent` (highlights)
3. **Derive remaining palette** — adjust hue, saturation, lightness in HCL space:

```js
function derivePalette(brandHex, n) {
  const base = d3.hcl(brandHex);
  return Array.from({ length: n }, (_, i) => {
    const hueShift = (i * 360 / n) % 360;
    return d3.hcl((base.h + hueShift) % 360, base.c * 0.8, base.l).formatHex();
  });
}
```

4. **Validate** every derived color for contrast against both light and dark backgrounds.

### Multiple brand themes

```js
const brands = {
  brandA: { "--color-primary": "#0066cc", "--color-accent": "#ff6600", /* ... */ },
  brandB: { "--color-primary": "#2e7d32", "--color-accent": "#ffd600", /* ... */ },
};

function applyBrand(name) {
  const tokens = brands[name];
  const root = document.documentElement.style;
  for (const [prop, value] of Object.entries(tokens)) root.setProperty(prop, value);
}
```

---

## Theme Switcher UI

### Minimal toggle (light/dark)

```js
const toggle = document.createElement("button");
toggle.textContent = "Toggle Theme";
toggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  document.documentElement.setAttribute("data-theme", current === "light" ? "dark" : "light");
  updateCharts();
});
```

### Multi-theme selector

```html
<select id="theme-select">
  <option value="light">Light</option>
  <option value="dark">Dark</option>
  <option value="high-contrast">High Contrast</option>
</select>
```

```js
document.getElementById("theme-select").addEventListener("change", e => {
  document.documentElement.setAttribute("data-theme", e.target.value);
  updateCharts();
});
```

### Persisting preference

```js
// Save
localStorage.setItem("chart-theme", themeName);

// Restore (run before chart init to prevent flash)
const saved = localStorage.getItem("chart-theme");
if (saved) document.documentElement.setAttribute("data-theme", saved);
```

Place the restore script in `<head>` (blocking) to avoid flash of wrong theme (FOWT).

---

## SVG-Specific Techniques

### CSS-only theme switching

Set SVG properties via CSS custom properties — zero JS on theme change:

```css
.chart-bg { fill: var(--color-bg); }
.axis .domain { stroke: var(--color-axis); }
.axis text { fill: var(--color-text); }
.grid line { stroke: var(--color-grid); stroke-dasharray: 2 2; }
```

### SVG filters and dark mode

SVG filters (`<feDropShadow>`, `<feGaussianBlur>`) compose against a transparent or white implicit background. In dark mode:

- Drop shadows become invisible on dark backgrounds — invert shadow color or increase opacity
- `feFlood` filters need their `flood-color` updated per theme
- `feColorMatrix` desaturation works in any theme but check that the desaturated color still has sufficient contrast

```css
[data-theme="dark"] .shadow-filter feDropShadow {
  flood-color: rgba(0, 0, 0, 0.6); /* stronger shadow on dark bg */
}
```

### Tooltip theming

```css
.tooltip {
  background: var(--color-tooltip-bg);
  border: 1px solid var(--color-tooltip-border);
  color: var(--color-text);
  box-shadow: 0 2px 8px rgba(0, 0, 0, calc(var(--shadow-alpha, 0.1)));
}
[data-theme="dark"] { --shadow-alpha: 0.4; }
```

---

## Dark Mode Design Rules

1. **Don't invert — redesign.** Simply inverting colors produces garish results. Dark backgrounds need lower-chroma, lighter-value data colors.

2. **Reduce color saturation.** Full-saturation colors on dark backgrounds cause eye strain. Shift lightness up and chroma down in HCL:

```js
function adjustForDark(hex) {
  const c = d3.hcl(hex);
  c.l = Math.min(c.l + 15, 90);    // lighter
  c.c = Math.max(c.c - 10, 20);    // less saturated
  return c.formatHex();
}
```

3. **Increase opacity for overlapping elements.** Alpha values tuned for white backgrounds become invisible on dark. Multiply alpha by 1.5–2x.

4. **Lighten grid lines, don't just darken.** Grid on dark bg should be `#2a2a4a` (slightly lighter than bg), not `#cccccc` (jarring).

5. **Text shadow for labels over data.** On dark backgrounds, add subtle text shadow: `text-shadow: 0 1px 2px rgba(0,0,0,0.8);`

6. **Borders become more important.** Elements that relied on white-space separation need visible borders in dark mode.

---

## Common Pitfalls

1. **Hardcoded colors in D3 `.attr()` calls.** The most common theming bug. Every `attr("fill", "#333")` ignores themes. Use CSS classes or read tokens.

2. **`getComputedStyle` before DOM update.** Setting `data-theme` and immediately reading tokens may return stale values. Use `requestAnimationFrame` or read after a microtask:
```js
document.documentElement.setAttribute("data-theme", "dark");
requestAnimationFrame(() => {
  const bg = getToken("--color-bg"); // now correct
  redraw();
});
```

3. **Opacity that works on white, fails on dark.** `rgba(0,0,0,0.1)` grid lines are subtle on white but invisible on `#1a1a2e`. Use tokens for grid colors, not raw rgba.

4. **SVG `fill` attribute vs CSS `fill` property.** Inline SVG attributes have higher specificity than CSS. If D3 sets `attr("fill", "steelblue")`, a CSS rule with `fill: var(--color-primary)` won't override it. Choose one approach: all-CSS or all-JS.

5. **Canvas ignores CSS entirely.** Setting `--color-primary` does nothing for Canvas draws. Must explicitly read tokens and pass to `ctx.fillStyle`.

6. **Flash of wrong theme (FOWT).** If theme detection runs after page render, users see a flash. Set `data-theme` in a `<script>` in `<head>` before any rendering:
```html
<script>
  const saved = localStorage.getItem("chart-theme");
  const prefersDark = matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.setAttribute("data-theme", saved || (prefersDark ? "dark" : "light"));
</script>
```

7. **Multiple `getComputedStyle` calls cause layout thrashing.** Read all tokens once, cache in an object, pass to render functions.

8. **Transitioning `background-color` on `<body>` without `color-scheme`.** Set `color-scheme: light dark` on `:root` so scrollbars and form controls follow the theme:
```css
:root { color-scheme: light; }
[data-theme="dark"] { color-scheme: dark; }
```

9. **Forgetting SVG `<text>` inherits `color` but needs explicit `fill`.** SVG text color is controlled by `fill`, not CSS `color`. Use `fill: var(--color-text)` in CSS or read the token.

10. **Z-index of theme transition.** Transitioning `background-color` on the chart container but not the body creates a visible seam during animation. Transition all background layers together.

## References

- [Designing Dark Mode](https://material.io/design/color/dark-theme.html) — Material Design dark theme guidelines
- [Prefers-color-scheme (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme) — media query reference
- [CSS Custom Properties (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties) — custom property reference
- [WCAG 2.1 Contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) — minimum contrast requirements
- [Design Tokens W3C](https://tr.designtokens.org/format/) — emerging design token standard
- [D3 Color](https://d3js.org/d3-color) — HCL/Lab color manipulation
- [color-scheme CSS property (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/color-scheme) — browser chrome adaptation
