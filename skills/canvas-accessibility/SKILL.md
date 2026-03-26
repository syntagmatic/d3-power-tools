---
name: canvas-accessibility
description: "Make D3.js canvas visualizations accessible to keyboard and screen reader users. Use this skill when the user needs canvas accessibility, keyboard navigation, ARIA attributes, focus management, screen reader support, live region announcements, focus ring rendering, data table fallback, or hidden DOM mirror for any canvas-based D3 visualization — scatter plots, force layouts, treemaps, hierarchies, heatmaps, bar charts, or network graphs."
---

# Canvas Accessibility for D3 Visualizations

Make canvas-rendered D3 visualizations navigable by keyboard and perceivable by screen readers.

Related: `canvas` (DPR, batching), `data-table` (data table alternative).

**When to just use SVG**: <500 elements with simple interactions — SVG gives accessibility for free. Canvas accessibility is worth the effort when you need canvas for performance.

## Two Strategies

1. **Enhanced canvas** — ARIA on canvas, keyboard handlers, live region announces focused point. Simpler, one-at-a-time navigation.
2. **Hidden DOM mirror** — parallel tree of focusable elements. Screen readers traverse mirror, canvas renders visually. More complex, browsable.

| Approach | Best for |
|----------|----------|
| Live region only | Simple, one-at-a-time browsing |
| DOM mirror | Browsable lists/grids/trees with >20 elements |
| Both | Complex interactive viz — live region for state, mirror for structure |

## ARIA Role Selection

| Viz Type | Role | Why |
|----------|------|-----|
| Static chart | `img` | Single image with alt text |
| Tree / hierarchy | `tree` | Parent/child/sibling nav |
| Bar chart, ranked list | `listbox` | Linear ordered items |
| Heatmap, matrix | `grid` | Row/column movement |
| Scatter, force, map | `application` | Spatial — passes all keys through |

```js
canvas.setAttribute('tabindex', '0');
canvas.setAttribute('role', role);
canvas.setAttribute('aria-label', label);
canvas.textContent = `${label} with ${n} data points. Use arrow keys to navigate, Enter to select.`;
```

## Navigation Models

All share: `Home`=first, `End`=last, `Enter`/`Space`=select, `Escape`=clear, `Tab`=exit canvas.

### Tree: Down=child, Up=parent, Left/Right=sibling

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

### Spatial (scatter, force) — quadtree nearest-neighbor with 90° cone

```js
function buildSpatialNav(data, xAcc, yAcc) {
  const qt = d3.quadtree().x(xAcc).y(yAcc).addAll(data);

  return function findNearest(current, direction) {
    const cx = xAcc(current), cy = yAcc(current);
    let best = null, bestDist = Infinity;

    qt.visit((quad, x0, y0, x1, y1) => {
      // Prune: skip quads farther than current best
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

// 90° cone check — the key geometry
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

### Grid (heatmap) — row/column arithmetic

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

## Focus Ring Rendering

Draw LAST in render loop so it's on top. Per-shape drawing:

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

Respect `prefers-reduced-motion`:
```js
if (!matchMedia('(prefers-reduced-motion: reduce)').matches)
  ctx.lineDashOffset = -performance.now() / 50;
```

## System Accessibility Preferences

Canvas ignores CSS — you must query media features and adapt rendering yourself.

| Media query | What to do in Canvas | Browser support |
|-------------|---------------------|-----------------|
| `prefers-reduced-motion: reduce` | Skip transitions, show final state immediately. Disable animated focus ring dash offset. | 93%+ (as of March 2026) |
| `prefers-contrast: more` | Increase stroke widths (+1px), switch to higher-contrast palette, enlarge text by ~2px. | ~85% |
| `forced-colors` (Windows High Contrast) | Canvas is a bitmap — forced-colors has **no effect**. The hidden DOM mirror becomes the only accessible representation. If you skip the mirror, high-contrast users see nothing meaningful. | Chromium + Firefox |

```js
// Query once at init, listen for changes
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const highContrast = matchMedia('(prefers-contrast: more)');

function getA11ySettings() {
  return {
    skipTransitions: reducedMotion.matches,
    strokeBoost: highContrast.matches ? 1 : 0,
    fontBoost: highContrast.matches ? 2 : 0
  };
}

// Re-render when preference changes (e.g., user toggles system setting)
reducedMotion.addEventListener('change', render);
highContrast.addEventListener('change', render);
```

The `forced-colors` gap is unique to canvas. SVG elements respond to forced-colors automatically; canvas does not. This is the strongest argument for always providing a DOM mirror or data table toggle alongside canvas visualizations.

## Announce Function with Field Config

```js
function makeAnnounce(liveRegion, fields) {
  return function announce(datum, stateText) {
    const parts = fields.map(({ key, label, format }) => {
      const v = datum[key];
      if (v == null) return null;
      return label ? `${label} ${format ? format(v) : v}` : (format ? format(v) : v);
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
announce(datum);             // "California, value 39.5M"
announce(datum, 'selected'); // "California, value 39.5M, selected"
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
| Focus change (arrows) | Identity + value + context |
| Selection (Enter) | Identity + "selected" |
| Deselection (Escape) | "Selection cleared" |
| Collapse/Expand | Element + state + child count |
| Data update | Summary: "Data updated, N items" |
| Layout change | "Switched to [layout] view" |

## Hidden DOM Mirror

```js
function createDOMMirror(canvas, data, { role = 'listbox', itemRole = 'option', labelFn } = {}) {
  const mirror = document.createElement('div');
  mirror.setAttribute('role', role);
  mirror.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;';
  canvas.setAttribute('aria-owns', mirror.id = 'canvas-mirror');

  d3.select(mirror).selectAll(`[role="${itemRole}"]`).data(data, d => d.id).join('div')
    .attr('role', itemRole).attr('id', d => `mirror-node-${d.id}`)
    .attr('aria-label', labelFn || (d => d.name || d.id));

  canvas.parentElement.appendChild(mirror);
  return mirror;
}
```

For richer descriptions without a separate `aria-describedby` target, use `aria-description` (ARIA 1.3, as of March 2026 supported in Chrome and Firefox):
```js
.attr('aria-description', d => `${d.category}, revenue ${fmt(d.revenue)}`)
```
This is lighter than creating a described-by element for each mirror node — one attribute instead of two elements plus an ID link.

Track focus with `aria-activedescendant`:
```js
canvas.setAttribute('aria-activedescendant', `mirror-node-${state.focusedId}`);
```

Update mirror on data changes with D3 join.

## Blur Behavior

Two strategies:
- **Preserve focus (recommended)**: keep `focusedId` on blur, hide ring. User resumes on Tab-back. Track `canvasHasFocus` flag.
- **Clear focus**: appropriate for standalone charts where re-entry should start fresh.

## Common Pitfalls

1. **Focus ring drawn under data** — always draw last in render loop.

2. **Announcing too much** — rapid-fire from held arrow keys. Debounce 100–200ms.

3. **Forgetting `e.preventDefault()`** — arrow keys scroll page. Prevent for handled keys, let unhandled (Tab) pass through.

4. **Canvas blur on click** — reconcile with hit detection:
    ```js
    canvas.addEventListener('pointerdown', e => {
      canvas.focus();
      const hit = hitDetect(e.offsetX, e.offsetY);
      if (hit) { state.setFocus(hit.id); announce(hit); render(); }
    });
    ```

5. **Missing skip link** — keyboard users trapped in dense canvas. Handle `Escape` to blur. Consider `<a href="#after-viz" class="sr-only">Skip visualization</a>`.

6. **Testing only with keyboard** — screen reader behavior differs. Test with VoiceOver (macOS) / NVDA (Windows). VoiceOver interacts with `role="application"` differently.

7. **Invisible focus ring on light backgrounds** — use white shadow behind ring or double ring (white outer, blue inner).

8. **Stale DOM mirror after filter** — built at init, never updated when brush/filter changes visible data. Update in same render pass.

9. **Ignoring `forced-colors` mode** — Windows High Contrast users get a raw bitmap with no color adaptation. Always pair canvas with a DOM mirror or table toggle. Test with `matchMedia('(forced-colors: active)')` — if true, consider auto-switching to the table view.

## References

- [WAI-ARIA APG — TreeView](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)
- [WAI-ARIA APG — Grid](https://www.w3.org/WAI/ARIA/apg/patterns/grid/)
- [WAI-ARIA APG — Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/)
- [Chartability](https://chartability.fizz.studio/) — Frank Elavsky
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
