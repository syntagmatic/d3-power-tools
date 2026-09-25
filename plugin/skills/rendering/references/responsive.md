# Responsive

Absorbed from the v2 `responsive` skill. Open when a chart must resize with its container, reflow on phones, handle touch, print, or report its height out of an iframe.

A chart built at 960px breaks at 320px because ticks collide, the legend covers data, and text shrinks, not because the data changed. Responsive means re-deciding tick count, margins, and layout at each size.

## viewBox vs redraw

| | viewBox scaling | Redraw on resize |
|---|---|---|
| Text | shrinks with the chart (14px → 7px at half width) | stays readable |
| Ticks | fixed count, crowded narrow, sparse wide | `innerWidth / 80` |
| Layout | fixed | legend can move below |
| Hit targets | shrink, hard to tap | stay usable |
| Cost | none | a render per resize |

viewBox for decorative or iconic graphics without meaningful text. Redraw for anything with axes, labels, or interaction. Skip the observer entirely for static exports, fixed-size cells, and scrollytelling steps locked to the viewport.

## ResizeObserver

If the chart's own content sets the container's height, rendering changes the size, the observer fires, the chart renders again. Browsers break the cycle with a "ResizeObserver loop" error, but the chart oscillates first. Observe a wrapper whose size comes from CSS (grid, flex, explicit height) with `overflow: hidden`:

```js
let lastWidth = 0;
const ro = new ResizeObserver(([entry]) => {
  const { width, height } = entry.contentRect;
  if (width === 0 || Math.abs(width - lastWidth) < 1) return; // hidden, or height-only change
  lastWidth = width;
  render(width, height);
});
ro.observe(document.getElementById("chart-wrapper"));
```

The width guard also swallows the mobile address-bar show/hide, which changes height only. Debounce expensive renders (Canvas, WebGL, large data); plain SVG under ~100 elements doesn't need it.

## Container queries

Use `@container` for presentation (legend layout, font size, hiding annotations): declarative, no flash. Use ResizeObserver for anything D3 computes (tick count, ranges, radius, switching chart type). Components embedded in unknown pages want both.

`container-type: inline-size` applies size containment: the element can't take its width from its children, so it must be sized by its parent's layout. Same rule as the observer.

## Margins, ticks, labels

- Left margin from the widest tick label: render the formatted ticks into a hidden SVG, take the max `getBBox().width`, add ~12px.
- Numeric ticks: `Math.max(2, Math.floor(innerWidth / 80))`. Time: `Math.min(width / 100, 12)`.
- Rotate x labels 45° under ~500px and grow the bottom margin to match (~60px).
- Too many categories: hide every Nth label, `i % Math.ceil(n / (width / 60))`.

## Brushes across resize

Brush selections are pixels. Store the selection in data space and re-project after rebuilding the scale:

```js
let brushedDomain = null;
const onBrush = ({ selection }, x) => { if (selection) brushedDomain = selection.map(x.invert); };
function restoreBrush(brushG, brush, x) {
  if (brushedDomain) brushG.call(brush.move, brushedDomain.map(x));
}
```

Under ~400px, brush handles are hard to grab; swap in an `<input type="range">`.

## Canvas DPR

Three steps: backing store `Math.round(w * dpr)`, CSS size `w px`, `ctx.scale(dpr, dpr)`. Setting `canvas.width` or `height` resets all context state, so re-apply the scale after every resize.

DPR changes when a window moves between monitors. The media query is tied to the current value, so re-register after each change:

```js
function watchDpr(onChange) {
  matchMedia(`(resolution: ${devicePixelRatio}dppx)`)
    .addEventListener("change", () => { onChange(); watchDpr(onChange); }, { once: true });
}
```

## Touch and motion

- WCAG 2.2 minimum target is 24×24 CSS px (AA); 44×44 is the AAA / platform-guideline size. On `matchMedia("(pointer: coarse)")`, raise the hit radius (22 vs 8) without changing the drawn size: a transparent larger circle in SVG, a larger `quadtree.find` radius on Canvas.
- `prefers-reduced-motion: reduce` → transition duration 0 for data changes, decorative motion off.

## Iframe embedding

Inside: after each render, `parent.postMessage({type: "chart-resize", height}, "*")`, observing `document.body`. Host: on `message` with that type, set the iframe's height. Sandbox needs `allow-scripts`; `allow-same-origin` if the chart fetches from the host domain. Check `e.origin` on the host side.

## Print

- `@media print`: light theme tokens, hide tooltips/controls/brushes, `break-inside: avoid`.
- SVG prints as vectors. Canvas prints at screen resolution: on `beforeprint`, render to an offscreen canvas at `300/96` scale, swap in an `<img>` from `toDataURL`, swap back on `afterprint`.
- Grayscale printing of color-encoded data needs pattern fills (see the legibility skill).
- DevTools → Rendering → Emulate CSS media type: print.

## Pitfalls

- `<svg width="100%">` with no viewBox and no height gets the 150px default height.
- `display: none` containers measure 0×0. Guard `width > 0` and let the observer fire when the panel opens, rather than initializing blind.
- Starting a new transition on an element interrupts the running one of the same name. During resize, render with duration 0.
- Disconnect observers, matchMedia listeners, and pending rAFs in a `destroy()`, or they leak when the chart is removed.
