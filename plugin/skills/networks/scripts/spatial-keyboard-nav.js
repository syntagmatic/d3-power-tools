/**
 * Spatial keyboard navigation for force-directed layouts.
 * Uses arrow keys to move focus to the nearest node in the pressed direction.
 * Works with any layout where nodes have x/y positions that change over time.
 *
 * @param {HTMLCanvasElement} canvas - the canvas element to attach keyboard events to
 * @param {Array} nodes - array of node objects with x, y properties (mutated by simulation)
 * @param {Object} options
 * @param {Function} options.render - called after focus changes so the focus ring can be drawn
 * @param {Function} options.announce - called with the focused node for screen reader announcement
 * @param {Function} options.getId - returns a unique ID for a node, default d => d.id
 * @returns {{ destroy: Function, getFocused: Function }}
 */
export function spatialKeyboardNav(canvas, nodes, { render, announce, getId = d => d.id } = {}) {
  let focusedNode = null;

  const dirs = {
    ArrowRight: [1, 0],
    ArrowLeft:  [-1, 0],
    ArrowUp:    [0, -1],
    ArrowDown:  [0, 1],
  };

  function onKeydown(e) {
    // Enter focus on first node
    if (!focusedNode && (e.key in dirs || e.key === "Enter")) {
      focusedNode = nodes[0] || null;
      if (focusedNode && announce) announce(focusedNode);
      if (render) render();
      e.preventDefault();
      return;
    }

    // Escape clears focus
    if (e.key === "Escape") {
      focusedNode = null;
      if (render) render();
      e.preventDefault();
      return;
    }

    const dir = dirs[e.key];
    if (!dir || !focusedNode) return;

    // Find nearest node in the arrow direction
    let best = null, bestDist = Infinity;
    for (const n of nodes) {
      if (n === focusedNode) continue;
      const dx = n.x - focusedNode.x;
      const dy = n.y - focusedNode.y;
      const dot = dx * dir[0] + dy * dir[1];
      if (dot <= 0) continue; // wrong direction
      const dist = Math.hypot(dx, dy);
      if (dist < bestDist) { best = n; bestDist = dist; }
    }

    if (best) {
      focusedNode = best;
      if (announce) announce(focusedNode);
      if (render) render();
    }
    e.preventDefault();
  }

  canvas.setAttribute("tabindex", "0");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-roledescription", "interactive network graph");
  canvas.addEventListener("keydown", onKeydown);

  return {
    getFocused() { return focusedNode; },
    destroy() {
      canvas.removeEventListener("keydown", onKeydown);
      canvas.removeAttribute("tabindex");
      focusedNode = null;
    },
  };
}

/**
 * Draw a focus ring around a node on a canvas context.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} node - node with x, y, and optionally r (radius)
 * @param {Object} options
 * @param {string} options.color - ring color, default "#005fcc"
 * @param {number} options.lineWidth - ring width, default 2.5
 * @param {number} options.padding - gap between node and ring, default 4
 */
export function drawFocusRing(ctx, node, { color = "#005fcc", lineWidth = 2.5, padding = 4 } = {}) {
  if (!node) return;
  const r = (node.r || 5) + padding;
  ctx.save();
  ctx.beginPath();
  ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
  ctx.restore();
}
