# Canvas accessibility

Absorbed from the v2 `canvas-accessibility` skill. Open when a canvas chart needs keyboard navigation, screen reader output, or a focus ring.

## Enhanced canvas vs DOM mirror

| Approach | Use when |
|---|---|
| Live region only | one-at-a-time browsing; the canvas holds focus and announces the current item |
| DOM mirror | browsable list/grid/tree over ~20 items, where screen reader users want to read the structure with their own commands |
| Both | complex interactive viz: mirror for structure, live region for state changes |

Container setup: `tabindex="0"`, a role from the SKILL.md table, an `aria-label`, and fallback text inside the `<canvas>` with usage instructions ("…Use arrow keys to navigate, Enter to select."). `aria-roledescription="scatter plot"` names the thing better than "application".

## Tree keys (WAI-ARIA APG)

The v2 skill mapped Down=child, Up=parent. With `role="tree"`, screen readers tell users the APG keys, so use these:

```js
function handleTreeKey(e, node, state, announce) {
  const vis = state.visibleNodes, i = vis.indexOf(node);
  const open = node.children && !state.isCollapsed(node);
  let next;
  switch (e.key) {
    case 'ArrowDown': next = vis[i + 1]; break;
    case 'ArrowUp': next = vis[i - 1]; break;
    case 'ArrowRight':
      if (node.children && !open) { state.toggleCollapse(node.id); announce(node, `expanded, ${node.children.length} children`); }
      else next = node.children?.[0];
      break;
    case 'ArrowLeft':
      if (open) { state.toggleCollapse(node.id); announce(node, 'collapsed'); }
      else next = node.parent;
      break;
    case 'Home': next = vis[0]; break;
    case 'End': next = vis.at(-1); break;
    case 'Enter': case ' ': state.setSelection(node.id); announce(node, 'selected'); break;
    case 'Escape': state.clearSelection(); announce(node, 'Selection cleared'); break;
    default: return;
  }
  if (next) { state.setFocus(next.id); announce(next); }
  e.preventDefault();
}
```

## Grid keys (heatmap)

APG grid: Home/End stay in the row; Ctrl+Home/End go to the corners.

```js
function handleGridKey(e, state, { rows, cols, data, announce }) {
  const idx = data.findIndex(d => d.id === state.focusedId);
  let row = Math.floor(idx / cols), col = idx % cols;
  switch (e.key) {
    case 'ArrowRight': col = Math.min(col + 1, cols - 1); break;
    case 'ArrowLeft': col = Math.max(col - 1, 0); break;
    case 'ArrowDown': row = Math.min(row + 1, rows - 1); break;
    case 'ArrowUp': row = Math.max(row - 1, 0); break;
    case 'Home': if (e.ctrlKey) row = 0; col = 0; break;
    case 'End': if (e.ctrlKey) row = rows - 1; col = cols - 1; break;
    default: return;
  }
  const next = row * cols + col;
  if (next !== idx && next < data.length) {
    state.setFocus(data[next].id);
    announce(data[next], `row ${row + 1}, column ${col + 1}`);
  }
  e.preventDefault();
}
```

## Spatial navigation (scatter, force, map)

Nearest neighbor inside a 90° cone in the arrow's direction. The quadtree visit prunes cells farther than the current best.

```js
function buildSpatialNav(data, xAcc, yAcc) {
  const qt = d3.quadtree().x(xAcc).y(yAcc).addAll(data);
  return function findNearest(current, dir) {
    const cx = xAcc(current), cy = yAcc(current);
    let best = null, bestDist = Infinity;
    qt.visit((quad, x0, y0, x1, y1) => {
      if (best && pointRectDist(cx, cy, x0, y0, x1, y1) > bestDist) return true;
      if (!quad.length) {
        let p = quad;
        do {
          if (p.data === current) continue;
          const px = xAcc(p.data), py = yAcc(p.data);
          if (!inDirection(cx, cy, px, py, dir)) continue;
          const dist = Math.hypot(px - cx, py - cy);
          if (dist < bestDist) { bestDist = dist; best = p.data; }
        } while ((p = p.next));
      }
    });
    return best;
  };
}

// Target lies in the 90° cone around the arrow: |off-axis| <= on-axis distance.
function inDirection(ox, oy, tx, ty, dir) {
  const dx = tx - ox, dy = ty - oy;
  if (!dx && !dy) return false;
  switch (dir) {
    case 'right': return dx > 0 && Math.abs(dy) <= dx;
    case 'left': return dx < 0 && Math.abs(dy) <= -dx;
    case 'down': return dy > 0 && Math.abs(dx) <= dy;
    case 'up': return dy < 0 && Math.abs(dx) <= -dy;
  }
}

function pointRectDist(px, py, x0, y0, x1, y1) {
  return Math.hypot(Math.max(x0 - px, 0, px - x1), Math.max(y0 - py, 0, py - y1));
}
```

## Focus ring

Draw last. Blue dashed stroke over a white shadow reads on light and dark marks.

```js
function drawFocusRing(ctx, shape, p, pad = 4) {
  ctx.save();
  Object.assign(ctx, { strokeStyle: '#1a73e8', lineWidth: 2.5, shadowColor: 'rgba(255,255,255,0.9)', shadowBlur: 3 });
  ctx.setLineDash([4, 3]);
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) ctx.lineDashOffset = -performance.now() / 50;
  ctx.beginPath();
  if (shape === 'circle') ctx.arc(p.cx, p.cy, p.r + pad, 0, 2 * Math.PI);
  else if (shape === 'rect') ctx.roundRect(p.x - pad, p.y - pad, p.w + 2 * pad, p.h + 2 * pad, (p.cornerRadius ?? 0) + pad / 2);
  else if (shape === 'arc') {
    ctx.arc(p.cx, p.cy, p.outerR + pad, p.startAngle, p.endAngle);
    ctx.arc(p.cx, p.cy, Math.max(0, p.innerR - pad), p.endAngle, p.startAngle, true);
    ctx.closePath();
  } else ctx.arc(p.cx, p.cy, 8, 0, 2 * Math.PI); // tiny point: fixed-size ring
  ctx.stroke();
  ctx.restore();
}
```

An animated dash offset needs a rAF loop while focused; stop it on blur.

## Announce builder

```js
function makeAnnounce(liveRegion, fields) {
  return (datum, stateText) => {
    const parts = fields.map(({ key, label, format }) => {
      const v = datum[key];
      if (v == null) return null;
      const s = format ? format(v) : v;
      return label ? `${label} ${s}` : s;
    }).filter(Boolean);
    if (stateText) parts.push(stateText);
    liveRegion.textContent = parts.join(', ');
  };
}
// makeAnnounce(region, [{ key: 'name' }, { key: 'value', label: 'value', format: d3.format('.3s') }])
//   → "California, value 39.5M, selected"
```

## DOM mirror

Put the mirror **inside the `<canvas>`** as fallback content. Canvas children aren't painted but are exposed to assistive tech and are real descendants, so `aria-activedescendant` on the canvas resolves without `aria-owns` and without clip-rect CSS. (The v2 version set `aria-owns` to a separate `role="listbox"` div, nesting a listbox inside the canvas's listbox.)

```js
function renderMirror(canvas, data, { itemRole = 'option', labelFn = d => d.name ?? d.id, descFn } = {}) {
  d3.select(canvas).selectAll(`[role="${itemRole}"]`).data(data, d => d.id).join('div')
    .attr('role', itemRole)
    .attr('id', d => `mirror-node-${d.id}`)
    .attr('aria-label', labelFn)
    .attr('aria-description', descFn ?? null);
}
// on focus change: canvas.setAttribute('aria-activedescendant', `mirror-node-${state.focusedId}`)
```

Call it in the same pass that redraws the canvas, so filters and brushes update both.

## System preferences

```js
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const moreContrast = matchMedia('(prefers-contrast: more)');
const forcedColors = matchMedia('(forced-colors: active)');
const a11y = () => ({
  skipTransitions: reducedMotion.matches,
  strokeBoost: moreContrast.matches ? 1 : 0,
  fontBoost: moreContrast.matches ? 2 : 0,
  preferTable: forcedColors.matches,
});
for (const mq of [reducedMotion, moreContrast, forcedColors]) mq.addEventListener('change', () => render(a11y()));
```

Forced-colors mode repaints SVG and HTML with system colors; a canvas bitmap is untouched, so switch to the table.

## Pitfalls

- Focus ring drawn before the data: hidden under marks.
- Unhandled keys prevented: Tab stops leaving the canvas. Prevent only the keys you handle.
- Held arrow keys: announcements pile up. Debounce 100-200ms.
- Light backgrounds swallow a single-color ring: keep the white halo.
- Mirror built at init and never rejoined after filtering.

Sources: WAI-ARIA APG TreeView, Grid and Listbox patterns; Chartability (Elavsky); WCAG 2.2.
