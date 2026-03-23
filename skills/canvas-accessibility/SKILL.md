---
name: canvas-accessibility
description: "Make D3.js canvas visualizations accessible to keyboard and screen reader users. Use this skill when the user needs canvas accessibility, keyboard navigation, ARIA attributes, focus management, screen reader support, live region announcements, focus ring rendering, data table fallback, or hidden DOM mirror for any canvas-based D3 visualization — scatter plots, force layouts, treemaps, hierarchies, heatmaps, bar charts, or network graphs."
---

# Canvas Accessibility for D3 Visualizations

Make canvas-rendered D3 visualizations navigable by keyboard and perceivable by screen readers.

Related: `canvas-rendering` (DPR, batching), `fallback-table` (data table alternative).

**When to just use SVG**: <500 elements with simple interactions — SVG gives accessibility for free. Canvas accessibility is worth the effort when you need canvas for performance.

## Two strategies

1. **Enhanced canvas** — ARIA on canvas, keyboard handlers, live region announces focused point. Simpler, one-at-a-time navigation.
2. **Hidden DOM mirror** — parallel tree of focusable elements. Screen readers traverse mirror, canvas renders visually. More complex, browsable.

## Canvas ARIA Fundamentals

```js
canvas.setAttribute('tabindex', '0');
canvas.setAttribute('role', role);       // see table below
canvas.setAttribute('aria-label', label);
canvas.textContent = `${label} with ${n} data points. Use arrow keys to navigate, Enter to select.`;
```

| Viz Type | Role | Why |
|----------|------|-----|
| Static chart | `img` | Single image with alt text |
| Tree / hierarchy | `tree` | Parent/child/sibling nav |
| Bar chart, ranked list | `listbox` | Linear ordered items |
| Heatmap, matrix | `grid` | Row/column movement |
| Scatter, force, map | `application` | Spatial — passes all keys through |

Use `aria-activedescendant` with DOM mirror to point to the currently focused mirror element.

## Focus Ring Rendering

Draw it yourself — call LAST in the render loop so it's on top:

```js
function drawFocusRing(ctx, shape, params) {
  ctx.save();
  ctx.strokeStyle = '#1a73e8';
  ctx.lineWidth = 2.5;
  ctx.setLineDash([4, 3]);
  ctx.shadowColor = 'rgba(255, 255, 255, 0.9)';
  ctx.shadowBlur = 3;
  const pad = 4;

  switch (shape) {
    case 'circle': {
      const { cx, cy, r } = params;
      ctx.beginPath(); ctx.arc(cx, cy, r + pad, 0, Math.PI * 2); ctx.stroke(); break;
    }
    case 'rect': {
      const { x, y, w, h, cornerRadius = 0 } = params;
      ctx.beginPath();
      cornerRadius > 0 ? ctx.roundRect(x - pad, y - pad, w + pad*2, h + pad*2, cornerRadius + pad*0.5)
        : ctx.strokeRect(x - pad, y - pad, w + pad*2, h + pad*2);
      ctx.stroke(); break;
    }
    case 'arc': {
      const { cx, cy, innerR, outerR, startAngle, endAngle } = params;
      ctx.beginPath();
      ctx.arc(cx, cy, outerR + pad, startAngle, endAngle);
      ctx.arc(cx, cy, Math.max(0, innerR - pad), endAngle, startAngle, true);
      ctx.closePath(); ctx.stroke(); break;
    }
    case 'point': {
      const { cx, cy } = params;
      ctx.beginPath(); ctx.arc(cx, cy, 8, 0, Math.PI * 2); ctx.stroke(); break;
    }
  }
  ctx.restore();
}
```

Respect `prefers-reduced-motion` if animating the focus ring (marching ants):
```js
if (!matchMedia('(prefers-reduced-motion: reduce)').matches)
  ctx.lineDashOffset = -performance.now() / 50;
```

## Keyboard Navigation

| Viz Type | Navigation Model |
|----------|-----------------|
| Tree / hierarchy | Down=child, Up=parent, Left/Right=sibling |
| List (bar, ranked) | Up/Down through sorted items |
| Grid (heatmap) | Arrow keys = row/column |
| Spatial (scatter, force) | Arrow keys = nearest neighbor in direction |

All models share: `Home`=first, `End`=last, `Enter`/`Space`=select, `Escape`=clear, `Tab`=exit canvas.

### Focus entry

Auto-focus the first logical element when canvas receives focus:
```js
canvas.addEventListener('focus', () => {
  if (state.focusedId == null) {
    state.setFocus(state.root?.id ?? data[0]?.id);
    announce(state.getById(state.focusedId));
    render();
  }
});
```

### Tree navigation

```js
function handleTreeKey(e, node, state, announce) {
  let next;
  switch (e.key) {
    case 'ArrowDown':
      if (state.isCollapsed(node)) { announce(node, 'collapsed'); return; }
      next = node.children?.[0]; break;
    case 'ArrowUp': next = node.parent; break;
    case 'ArrowRight': case 'ArrowLeft': {
      if (!node.parent) break;
      const sibs = node.parent.children, idx = sibs.indexOf(node);
      next = sibs[idx + (e.key === 'ArrowRight' ? 1 : -1)]; break;
    }
    case 'Enter': case ' ':
      if (e.shiftKey && node.children) {
        state.toggleCollapse(node.id);
        announce(node, state.isCollapsed(node) ? 'collapsed' : 'expanded');
      } else { state.setSelection(node.id); announce(node, 'selected'); }
      break;
    case 'Home': next = state.root; break;
    case 'End': next = state.visibleNodes.filter(n => !n.children || state.isCollapsed(n)).at(-1); break;
    case 'Escape': state.clearSelection(); state.clearFocus(); e.target.blur(); break;
    default: return;
  }
  if (next) { state.setFocus(next.id); announce(next); }
  e.preventDefault();
}
```

### Spatial navigation (scatter, force) — quadtree nearest-neighbor

```js
function buildSpatialNav(data, xAcc, yAcc) {
  const qt = d3.quadtree().x(xAcc).y(yAcc).addAll(data);

  return function findNearest(current, direction) {
    const cx = xAcc(current), cy = yAcc(current);
    let best = null, bestDist = Infinity;

    qt.visit((quad, x0, y0, x1, y1) => {
      if (best && pointRectDist(cx, cy, x0, y0, x1, y1) > bestDist) return true;
      if (!quad.length) {
        let p = quad;
        do {
          if (p.data === current) continue;
          const px = xAcc(p.data), py = yAcc(p.data);
          if (!inDirection(cx, cy, px, py, direction)) continue;
          const dist = Math.hypot(px - cx, py - cy);
          if (dist < bestDist) { bestDist = dist; best = p.data; }
        } while ((p = p.next));
      }
    });
    return best;
  };
}

// 90° cone check
function inDirection(ox, oy, tx, ty, dir) {
  const dx = tx - ox, dy = ty - oy;
  if (!dx && !dy) return false;
  switch (dir) {
    case 'right': return dx > 0 && Math.abs(dy) <= dx;
    case 'left':  return dx < 0 && Math.abs(dy) <= -dx;
    case 'down':  return dy > 0 && Math.abs(dx) <= dy;
    case 'up':    return dy < 0 && Math.abs(dx) <= -dy;
  }
}

function pointRectDist(px, py, x0, y0, x1, y1) {
  return Math.hypot(Math.max(x0 - px, 0, px - x1), Math.max(y0 - py, 0, py - y1));
}
```

Wire to keyboard:
```js
const findNearest = buildSpatialNav(data, d => xScale(d.x), d => yScale(d.y));
canvas.addEventListener('keydown', e => {
  const dir = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right' }[e.key];
  if (dir && state.focusedId != null) {
    const next = findNearest(data.find(d => d.id === state.focusedId), dir);
    if (next) { state.setFocus(next.id); announce(next); render(); }
    e.preventDefault();
  }
});
```

### Linear navigation (bar chart, line chart) — step through sorted array

```js
function handleLinearKey(e, data, state, announce) {
  const idx = data.findIndex(d => d.id === state.focusedId);
  let next;
  switch (e.key) {
    case 'ArrowRight': case 'ArrowDown': next = Math.min(idx + 1, data.length - 1); break;
    case 'ArrowLeft': case 'ArrowUp': next = Math.max(idx - 1, 0); break;
    case 'Home': next = 0; break;
    case 'End': next = data.length - 1; break;
    default: return;
  }
  if (next !== idx) { state.setFocus(data[next].id); announce(data[next]); }
  e.preventDefault();
}
```

### Grid navigation (heatmap) — row/column arithmetic

```js
function handleGridKey(e, state, { rows, cols, data, announce }) {
  const idx = data.findIndex(d => d.id === state.focusedId);
  let row = Math.floor(idx / cols), col = idx % cols;
  switch (e.key) {
    case 'ArrowRight': col = Math.min(col + 1, cols - 1); break;
    case 'ArrowLeft': col = Math.max(col - 1, 0); break;
    case 'ArrowDown': row = Math.min(row + 1, rows - 1); break;
    case 'ArrowUp': row = Math.max(row - 1, 0); break;
    case 'Home': row = col = 0; break;
    case 'End': row = rows - 1; col = cols - 1; break;
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

## Screen Reader Announcements

### Live region setup

```js
function createLiveRegion(canvas) {
  const region = document.createElement('div');
  region.setAttribute('aria-live', 'polite');
  region.setAttribute('aria-atomic', 'true');
  region.setAttribute('role', 'status');
  region.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;';
  canvas.parentElement.appendChild(region);
  return region;
}
```

### Building an announce function

Navigation examples throughout this skill call `announce(datum)` or `announce(datum, stateText)` — a simple callback that closes over the live region and field config. Build one like this:

```js
function makeAnnounce(liveRegion, fields) {
  return function announce(datum, stateText) {
    const parts = fields.map(({ key, label, format }) => {
      const v = datum[key];
      if (v == null) return null;
      const f = format ? format(v) : v;
      return label ? `${label} ${f}` : f;
    }).filter(Boolean);
    if (stateText) parts.push(stateText);
    liveRegion.textContent = parts.join(', ');
  };
}

// Usage:
const announce = makeAnnounce(liveRegion, [
  { key: 'name' },
  { key: 'value', label: 'value', format: d3.format('.3s') }
]);
announce(datum);               // "California, value 39.5M"
announce(datum, 'selected');   // "California, value 39.5M, selected"
```

### Debouncing — when users hold arrow keys

```js
let timer;
function debouncedAnnounce(...args) {
  clearTimeout(timer);
  timer = setTimeout(() => announce(...args), 150);
}
```

Skip debounce for trees with short labels where each step matters.

### What to announce when

| Event | Announce |
|-------|----------|
| Focus change (arrow keys) | Identity + value + context |
| Selection (Enter) | Identity + "selected" |
| Deselection (Escape) | "Selection cleared" |
| Collapse/Expand (Shift+Enter) | Element + state + child count |
| Data update | Summary: "Data updated, N items" |
| Layout change | "Switched to [layout] view" |

## Hidden DOM Mirror

For complex canvases where users need to browse many elements:

```js
function createDOMMirror(canvas, data, { role = 'listbox', itemRole = 'option', labelFn } = {}) {
  const mirror = document.createElement('div');
  mirror.setAttribute('role', role);
  mirror.setAttribute('aria-label', canvas.getAttribute('aria-label'));
  mirror.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;';
  canvas.setAttribute('aria-owns', mirror.id = 'canvas-mirror');

  d3.select(mirror).selectAll(`[role="${itemRole}"]`).data(data, d => d.id).join('div')
    .attr('role', itemRole).attr('id', d => `mirror-node-${d.id}`)
    .attr('aria-label', labelFn || (d => d.name || d.id)).attr('aria-selected', 'false');

  canvas.parentElement.appendChild(mirror);
  return mirror;
}
```

Update on data changes with D3 join. Track focus with `aria-activedescendant`:
```js
canvas.setAttribute('aria-activedescendant', `mirror-node-${state.focusedId}`);
```

| Approach | Best for |
|----------|----------|
| Live region only | Simple, one-at-a-time browsing |
| DOM mirror | Browsable lists/grids/trees with >20 elements |
| Both | Complex interactive viz — live region for state, mirror for structure |

## Data Table Fallback

A "Show as table" toggle. See `fallback-table` skill for full sortable/filterable tables with linked highlighting.

```js
const btn = document.createElement('button');
btn.textContent = 'Show as table';
btn.setAttribute('aria-pressed', 'false');
container.insertBefore(btn, canvas);

btn.addEventListener('click', () => {
  const showing = btn.getAttribute('aria-pressed') === 'true';
  canvas.style.display = showing ? '' : 'none';
  canvas.setAttribute('aria-hidden', String(!showing));
  tableContainer.style.display = showing ? 'none' : '';
  tableContainer.setAttribute('aria-hidden', String(showing));
  btn.textContent = showing ? 'Show as table' : 'Show as chart';
  btn.setAttribute('aria-pressed', String(!showing));
  // See `fallback-table` skill for buildTable implementation
  if (!showing && !tableContainer.querySelector('table')) buildTable(tableContainer, data, columns);
});
```

## Cleanup

Tear down listeners and live region in SPAs:

```js
function setupKeyboardNav(canvas, data, state, announce, render) {
  // handleKey dispatches to handleTreeKey/handleLinearKey/handleGridKey based on viz type
  const onKey = e => handleTreeKey(e, state.getById(state.focusedId), state, announce);
  const onFocus = () => { if (state.focusedId == null) { state.setFocus(data[0]?.id); render(); } };
  canvas.addEventListener('keydown', onKey);
  canvas.addEventListener('focus', onFocus);
  const liveRegion = createLiveRegion(canvas);
  return () => { canvas.removeEventListener('keydown', onKey); canvas.removeEventListener('focus', onFocus); liveRegion.remove(); };
}
```

## Common Pitfalls

1. **Focus ring drawn under data** — always draw the focus ring last in your render loop.

2. **Announcing too much** — when a user holds an arrow key, rapid-fire announcements queue up. Debounce with 100–200ms delay.

3. **Forgetting `e.preventDefault()`** — arrow keys scroll the page. Always prevent for handled keys, but let unhandled keys (Tab) pass through.

4. **Canvas blur on click** — `pointerdown` on canvas moves DOM focus. Reconcile:
    ```js
    canvas.addEventListener('pointerdown', e => {
      canvas.focus();
      const hit = hitDetect(e.offsetX, e.offsetY); // your quadtree/bounds hit test
      if (hit) { state.setFocus(hit.id); announce(hit); render(); }
    });
    ```

5. **Blur behavior** — two strategies:
    - **Preserve focus (recommended)**: keep `focusedId` on blur, just hide ring. User resumes on Tab-back. Track `canvasHasFocus` flag for ring rendering.
    - **Clear focus**: appropriate for standalone charts where re-entry should start fresh.

6. **Missing skip link** — keyboard users trapped in dense canvas. Handle `Escape` to blur. Consider: `<a href="#after-viz" class="sr-only">Skip visualization</a>`.

7. **Testing only with keyboard** — screen reader behavior differs. Test with VoiceOver (macOS) / NVDA (Windows). VoiceOver interacts with `role="application"` differently.

8. **Invisible focus ring on light backgrounds** — use white shadow behind the ring or draw a double ring (white outer, blue inner).

## References

- [WAI-ARIA APG — TreeView](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)
- [WAI-ARIA APG — Grid](https://www.w3.org/WAI/ARIA/apg/patterns/grid/)
- [WAI-ARIA APG — Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/)
- [Chartability](https://chartability.fizz.studio/) — Frank Elavsky's accessibility heuristics
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Accessible Data Viz Design](https://fossheim.io/writing/posts/accessible-dataviz-design/) — Sarah Fossheim
