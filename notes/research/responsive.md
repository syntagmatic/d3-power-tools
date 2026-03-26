# Responsive Skill Research

## Current Coverage

The skill (`skills/responsive/SKILL.md`) already covers:

- **viewBox vs redraw** -- decision table, when viewBox breaks (text shrinks, ticks crowd, interaction targets shrink)
- **ResizeObserver** -- infinite loop bug (observe wrapper, not chart), mobile address bar height-only changes
- **Margins that respond to content** -- measuring tick label width, rotating labels at narrow widths
- **Tick density by width** -- `width / 80` heuristic, categorical label filtering
- **Brush/interaction at small sizes** -- domain-space brush persistence across resize, HTML range fallback < 400px
- **Canvas DPI** -- three-step setup (backing store, CSS size, ctx.scale), DPR change detection across monitors
- **Iframe embedding** -- postMessage height negotiation, sandbox permissions
- **Print styles** -- basic `@media print` block hiding controls, Canvas-to-image `beforeprint` workaround
- **Common pitfalls** -- `width="100%"` without viewBox, hidden tabs, transitions interrupted by resize, cleanup/destroy

**Gaps identified**: container queries, mobile-first progressive design, print beyond the basics, responsive accessibility (touch targets, reduced motion, screen reader), decision guidance for when to use which technique.

## Container Queries (CSS @container)

Container queries let chart CSS respond to the chart container's dimensions rather than the viewport. This matters because charts are often embedded as widgets/components where viewport width is irrelevant.

### Advantages over ResizeObserver

| | ResizeObserver | Container Queries |
|---|---|---|
| Layout changes | JS sets classes/attributes; FOUC risk | Pure CSS; no JS flash |
| Tick count, data density | Still needs JS (D3 scales) | Cannot control JS logic |
| CSS-only adaptations (legend position, margin, font size) | Overkill -- JS for a CSS job | Native and declarative |
| Browser support | Universal | Size queries: all major browsers since Feb 2023; style queries: partial |

### Practical guidance

Container queries handle **presentation-layer** adaptations (legend placement, font sizes, grid reflow, hiding secondary annotations). ResizeObserver remains necessary for **data-layer** adaptations (tick count, scale domain, point radius, layout algorithm changes) because those require JS/D3 recalculation.

**Best pattern: use both.** Container queries for CSS adaptations, ResizeObserver for D3 logic.

```css
.chart-wrapper { container-type: inline-size; }

@container (max-width: 500px) {
  .legend { flex-direction: column; font-size: 0.8rem; }
  .annotation { display: none; }
  .y-axis-label { writing-mode: horizontal-tb; }
}

@container (max-width: 350px) {
  .legend { display: none; }
  .chart-subtitle { display: none; }
}
```

### Caveat: container collapse

Setting `container-type: inline-size` applies `contain: inline-size` to the element, which means it cannot derive its size from its children. The container must get its width from CSS (grid, flex, percentage) -- not from content. This matches the existing ResizeObserver guidance ("observe a wrapper whose size is set by CSS, not by chart content").

Sources:
- [CSS Container Queries - MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_queries)
- [Container Queries in 2026 - LogRocket](https://blog.logrocket.com/container-queries-2026/)
- [Master CSS Container Queries - CSS Author](https://cssauthor.com/master-css-container-queries-a-hands-on-tutorial/)

## Mobile-First Chart Design

Desktop-first responsive design (build full chart, then hide things at small sizes) produces cramped, illegible charts on phones. Mobile-first means designing the small-screen version as the primary experience and progressively enhancing for larger screens.

### Core principles

1. **Start with the smallest useful representation.** A single KPI number, a sparkline, or a simplified bar chart. Add complexity (axes, legends, annotations, secondary series) as space permits.

2. **Vertical expansion over horizontal compression.** Mobile screens are tall and narrow. Horizontal bar charts outperform vertical ones. Scrollable lists of small multiples work better than cramming panels side by side.

3. **Declutter by default.** Grid lines, secondary axes, legends (use direct labels instead), subtle annotations -- all optional at small sizes. Add them via container queries or width-conditional JS at larger breakpoints.

4. **Thumb-zone interaction.** Filters, toggles, and controls belong in the bottom 40% of the screen. Top-of-screen controls require grip changes on tall phones.

5. **Orientation-aware layouts.** Portrait favors bar charts with few categories; landscape favors line charts and time series. `matchMedia("(orientation: landscape)")` or container query aspect-ratio can switch layouts.

### Progressive enhancement tiers

| Width | What to show |
|---|---|
| < 350px | KPI / sparkline / single metric |
| 350-500px | Simplified chart: fewer ticks, no legend (direct labels), minimal margins |
| 500-768px | Full chart with legend, annotations, brush interaction |
| 768px+ | Multi-panel layouts, overview+detail, linked views |

### Pattern: layout switching

```js
function render(width) {
  if (width < 400) return renderSparkline(width);
  if (width < 600) return renderSimpleBar(width);
  return renderFullChart(width);
}
```

Sources:
- [Mobile vs Desktop Dataviz - Visual Cinnamon](https://www.visualcinnamon.com/2019/04/mobile-vs-desktop-dataviz/)
- [Mobile-First Visualization - Towards Data Science](https://towardsdatascience.com/mobile-first-visualization-b64a6745e9fd/)
- [Mobile Data Visualization Design Guide - Boundev](https://www.boundev.com/blog/mobile-data-visualization-design-guide)

## Print Stylesheets

The current skill has a basic `@media print` block. Additional considerations for chart-specific print output:

### Color to monochrome

Screens use color to encode data; printers often produce grayscale. Charts need a print-safe fallback:

```css
@media print {
  /* Force high-contrast monochrome-safe palette */
  :root {
    --series-1: #000;
    --series-2: #666;
    --series-3: #aaa;
  }
  /* Add pattern fills for area/bar charts via CSS classes */
  .series-1 { fill: url(#hatch-dense); }
  .series-2 { fill: url(#hatch-sparse); }
}
```

This connects to the `visual-texture` skill -- pattern fills are the print-safe dual encoding.

### Page break control

```css
@media print {
  .chart-container {
    break-inside: avoid;
    page-break-inside: avoid; /* legacy browsers */
    max-height: 90vh; /* prevent chart from overflowing page */
  }
  /* Force each chart section to start on a new page */
  .chart-section { break-before: page; }
}
```

### SVG prints well, Canvas does not

SVG elements render as vectors in print -- sharp at any resolution. Canvas rasterizes at screen DPI (typically 96 DPI), producing blurry print output. The existing `beforeprint` Canvas-to-image workaround helps but produces a raster image. For print-critical charts, prefer SVG or generate a high-DPI Canvas snapshot:

```js
window.addEventListener("beforeprint", () => {
  // Render at 300 DPI equivalent for print
  const printDpr = 300 / 96;
  const printCanvas = document.createElement("canvas");
  printCanvas.width = width * printDpr;
  printCanvas.height = height * printDpr;
  // ... re-render at high DPI ...
});
```

### Debugging print styles

Chrome DevTools: Rendering panel > Emulate CSS media type > print. This avoids the print-preview-refresh cycle.

Sources:
- [Printing - CSS | MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Printing)
- [How to Set Up a Print Style Sheet - Smashing Magazine](https://www.smashingmagazine.com/2011/11/how-to-set-up-a-print-style-sheet/)
- [CSS: The Perfect Print Stylesheet - Jotform](https://www.jotform.com/blog/css-perfect-print-stylesheet-98272/)

## Responsive Accessibility

Responsive design and accessibility intersect in several ways the current skill does not cover.

### Touch target sizes (WCAG 2.5.8)

WCAG 2.2 Level AA requires interactive targets to be at least **24x24 CSS pixels**, with 44x44 recommended. This directly affects:

- **Data points**: Scatter plot dots < 24px need invisible enlarged hit areas (SVG: larger transparent circle behind visible one; Canvas: quadtree with expanded search radius)
- **Legend items**: Clickable legend swatches must meet minimum size
- **Brush handles**: The existing < 400px brush fallback is good; also ensure brush handle touch targets are at least 44px
- **Spacing between targets**: Adjacent interactive elements need enough spacing to prevent accidental activation

```js
// Enlarge touch targets on coarse-pointer devices
const isTouch = matchMedia("(pointer: coarse)").matches;
const hitRadius = isTouch ? 22 : 8; // 44px diameter vs 16px
```

### prefers-reduced-motion

Users with vestibular disorders or motion sensitivity set this OS preference. Charts must respect it:

```css
@media (prefers-reduced-motion: reduce) {
  svg * { transition-duration: 0s !important; animation: none !important; }
}
```

```js
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const duration = reduceMotion ? 0 : 750;

// Use for all D3 transitions
selection.transition().duration(duration)...
```

Functional animations (showing data changes, enter/exit) can use instant state changes instead of animated transitions. Decorative animations (loading spinners, ambient motion) should be fully disabled.

### Screen reader at small sizes

At narrow widths, charts often hide elements (legends, annotations, secondary axes). Ensure hidden elements that convey meaning are only visually hidden, not removed from the accessibility tree:

```css
/* Visually hidden but accessible to screen readers */
.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); border: 0;
}
```

When a chart degrades to a sparkline at small sizes, provide an accessible summary:

```html
<div role="img" aria-label="Revenue trend: $2.1M in Jan rising to $3.4M in Dec, peak $3.8M in Oct">
  <canvas><!-- sparkline --></canvas>
</div>
```

### High contrast mode

`forced-colors` media query detects Windows High Contrast Mode. SVG strokes and fills get overridden by system colors. Charts need explicit `forced-color-adjust: none` on data elements to preserve data encoding, or must adapt to system colors.

Sources:
- [WCAG 2.5.8: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [prefers-reduced-motion - MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion)
- [Do No Harm Guide: Centering Accessibility in Data Visualization - Urban Institute](https://www.urban.org/sites/default/files/2022-12/Do%20No%20Harm%20Guide%20Centering%20Accessibility%20in%20Data%20Visualization.pdf)
- [Supporting Reduced Motion - Esri](https://www.esri.com/arcgis-blog/products/js-api-arcgis/mapping/supporting-reduced-motion-enhancing-accessibility-in-web-apps/)

## Decision Guidance

### When to use what

| Technique | Use when | Skip when |
|---|---|---|
| **viewBox scaling** | Decorative/iconic graphics, logos, simple illustrations without text | Any chart with axes, labels, or interaction |
| **ResizeObserver + redraw** | Charts needing tick/label/layout adaptation, always for production charts | Static exports, fixed containers |
| **Container queries** | CSS-level adaptations (legend layout, font size, show/hide annotations) | Data-level changes (tick count, scale recalc) |
| **Both CQ + RO** | Production chart components embedded in unknown contexts | Quick prototypes |
| **Debounced redraw** | Charts with expensive render (Canvas, WebGL, large datasets) | Simple SVG charts (< 100 elements) |
| **Layout switching** | Charts viewed across phone-to-desktop range | Fixed-context dashboards |

### Responsive checklist

1. Container gets its size from CSS (grid/flex/percentage), not from chart content
2. ResizeObserver on wrapper with `overflow: hidden`
3. Container queries for CSS adaptations (legend, annotations, font size)
4. Debounce resize handler (100-150ms) for expensive renders
5. Width-adaptive tick count (`width / 80`)
6. Touch targets >= 24px (44px preferred) on coarse-pointer devices
7. `prefers-reduced-motion` respected (duration = 0)
8. Print styles: hide controls, `break-inside: avoid`, Canvas-to-image fallback
9. Canvas DPI: three-step setup, DPR change listener
10. Brush state stored in data domain, not pixel coordinates
11. Mobile address bar: skip height-only resize events
12. Cleanup: `destroy()` disconnects observers, listeners, rAF handles

## Code Patterns

### Combined container query + ResizeObserver pattern

```html
<style>
  .chart-wrapper {
    container-type: inline-size;
    overflow: hidden;
    width: 100%;
    height: 400px;
  }

  .legend { display: flex; gap: 1rem; flex-wrap: wrap; }
  .annotation { font-size: 0.85rem; }

  @container (max-width: 500px) {
    .legend { flex-direction: column; font-size: 0.75rem; }
    .annotation { display: none; }
  }

  @container (max-width: 350px) {
    .legend { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    svg * { transition-duration: 0s !important; }
  }

  @media print {
    .controls, .tooltip, .brush { display: none !important; }
    .chart-wrapper { break-inside: avoid; height: auto !important; }
  }
</style>

<div class="chart-wrapper" id="chart">
  <svg></svg>
  <div class="legend"></div>
</div>

<script type="module">
const wrapper = document.getElementById("chart");
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const isTouch = matchMedia("(pointer: coarse)").matches;

let lastWidth = 0;
function render(width, height) {
  const duration = reduceMotion ? 0 : 750;
  const tickTarget = Math.max(2, Math.floor(width / 80));
  const hitRadius = isTouch ? 22 : 8;

  // ... D3 chart logic using width, height, duration, tickTarget, hitRadius ...
}

let timer;
const ro = new ResizeObserver(([entry]) => {
  const { width, height } = entry.contentRect;
  if (width < 1 || Math.abs(width - lastWidth) < 1) return;
  lastWidth = width;
  clearTimeout(timer);
  timer = setTimeout(() => render(width, height), 100);
});
ro.observe(wrapper);
</script>
```

### Responsive render with progressive enhancement

```js
function render(width, height) {
  const margin = getResponsiveMargin(width);
  const inner = { w: width - margin.left - margin.right, h: height - margin.top - margin.bottom };

  // Tier 1: always show (works at 300px)
  renderAxes(inner.w, inner.h, Math.max(2, inner.w / 80));
  renderDataMarks(inner.w, inner.h);

  // Tier 2: show above 500px
  if (width >= 500) {
    renderLegend();
    renderAnnotations();
  }

  // Tier 3: show above 768px
  if (width >= 768) {
    renderBrush(inner.w, inner.h);
    renderSecondaryAxis();
  }
}
```

### Print-safe Canvas with high-DPI fallback

```js
function setupPrintFallback(canvas, renderFn, width, height) {
  window.addEventListener("beforeprint", () => {
    const printDpr = 300 / 96; // ~3.125x for 300 DPI print
    const img = document.createElement("img");
    const offscreen = document.createElement("canvas");
    offscreen.width = Math.round(width * printDpr);
    offscreen.height = Math.round(height * printDpr);
    const ctx = offscreen.getContext("2d");
    ctx.scale(printDpr, printDpr);
    renderFn(ctx, width, height); // reuse chart render logic
    img.src = offscreen.toDataURL("image/png");
    img.style.width = "100%";
    img.classList.add("print-fallback");
    canvas.parentNode.insertBefore(img, canvas);
    canvas.style.display = "none";
  });

  window.addEventListener("afterprint", () => {
    document.querySelector(".print-fallback")?.remove();
    canvas.style.display = "";
  });
}
```
