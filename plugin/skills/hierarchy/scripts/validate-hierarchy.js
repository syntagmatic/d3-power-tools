/**
 * Validate tabular hierarchy data before passing to d3.stratify().
 * Detects duplicate IDs, orphaned nodes, cycles, multiple/missing roots.
 *
 * @param {Array<Object>} rows - flat array of row objects
 * @param {string} idField - property name for node ID
 * @param {string} parentField - property name for parent ID
 * @returns {{ valid: boolean, errors: Array<{type, node, detail}>, rows }}
 */
export function validateHierarchy(rows, idField = "id", parentField = "parent") {
  const errors = [];
  const ids = new Set();
  const byId = new Map();

  for (const row of rows) {
    const id = row[idField];
    if (ids.has(id)) {
      errors.push({ type: "duplicate", node: id, detail: `Duplicate ID: "${id}"` });
    } else {
      ids.add(id);
      byId.set(id, row);
    }
  }

  const roots = [];
  const orphans = [];
  for (const row of rows) {
    const pid = row[parentField];
    if (!pid || pid === "") {
      roots.push(row[idField]);
    } else if (!ids.has(pid)) {
      orphans.push(row[idField]);
      errors.push({ type: "orphan", node: row[idField], detail: `Parent "${pid}" not found` });
    }
  }

  if (roots.length === 0) {
    errors.push({ type: "no-root", node: null, detail: "No root node found" });
  } else if (roots.length > 1) {
    errors.push({ type: "multiple-roots", node: roots, detail: `${roots.length} roots: ${roots.join(", ")}` });
  }

  // Cycle detection via DFS with gray/black coloring
  const WHITE = 0, GRAY = 1, BLACK = 2;
  const color = new Map();
  for (const id of ids) color.set(id, WHITE);

  for (const id of ids) {
    if (color.get(id) !== WHITE) continue;
    const stack = [{ id, phase: "enter" }];
    while (stack.length) {
      const { id: cur, phase } = stack.pop();
      if (phase === "exit") { color.set(cur, BLACK); continue; }
      color.set(cur, GRAY);
      stack.push({ id: cur, phase: "exit" });
      const pid = byId.get(cur)?.[parentField];
      if (pid && ids.has(pid)) {
        if (color.get(pid) === GRAY) {
          errors.push({ type: "cycle", node: cur, detail: `Cycle: "${cur}" → "${pid}"` });
        } else if (color.get(pid) === WHITE) {
          stack.push({ id: pid, phase: "enter" });
        }
      }
    }
  }

  return { valid: errors.length === 0, errors, rows };
}

/**
 * Clean a hierarchy table so d3.stratify() can process it.
 * Deduplicates IDs, breaks cycles, grafts orphans onto a root.
 *
 * @param {Array<Object>} rows
 * @param {string} idField
 * @param {string} parentField
 * @returns {Array<Object>} cleaned rows
 */
export function cleanHierarchy(rows, idField = "id", parentField = "parent") {
  const { errors } = validateHierarchy(rows, idField, parentField);
  if (errors.length === 0) return rows;

  // Deduplicate — keep first occurrence
  let cleaned = rows.filter((row, i, arr) =>
    arr.findIndex(r => r[idField] === row[idField]) === i
  );

  // Break cycles by grafting onto root (determined below) instead of detaching
  const cycleNodes = new Set(errors.filter(e => e.type === "cycle").map(e => e.node));
  const orphanIds = new Set(errors.filter(e => e.type === "orphan").map(e => e.node));

  // Find original roots (before cycle-breaking)
  const originalRoots = cleaned.filter(r => !r[parentField] || r[parentField] === "");

  // Determine graft target
  let graftTarget;
  if (originalRoots.length === 1) {
    graftTarget = originalRoots[0][idField];
  } else {
    graftTarget = "__root__";
    cleaned.unshift({ [idField]: "__root__", [parentField]: "" });
    // Reparent original roots under synthetic root
    cleaned = cleaned.map(r =>
      originalRoots.includes(r) ? { ...r, [parentField]: "__root__" } : r
    );
  }

  // Graft cycle nodes and orphans onto the root
  cleaned = cleaned.map(r => {
    if (cycleNodes.has(r[idField]) || orphanIds.has(r[idField])) {
      return { ...r, [parentField]: graftTarget };
    }
    return r;
  });

  return cleaned;
}
