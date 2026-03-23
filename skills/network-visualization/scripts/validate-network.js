/**
 * Validate network/graph data before passing to D3 force simulation,
 * chord, Sankey, or other graph layouts.
 * Detects missing node references, self-loops, duplicate edges,
 * disconnected components, and invalid weights.
 *
 * @param {Object} graph - { nodes: Array<{id, ...}>, links: Array<{source, target, ...}> }
 * @param {Object} options
 * @param {string} options.nodeId - node ID accessor property, default "id"
 * @param {string} options.linkSource - link source accessor property, default "source"
 * @param {string} options.linkTarget - link target accessor property, default "target"
 * @param {string} options.weightField - optional weight property for numeric checks
 * @param {boolean} options.directed - treat as directed graph, default false
 * @returns {{ valid: boolean, errors: Array<{type, detail, data}>, graph }}
 */
export function validateNetwork(
  graph,
  {
    nodeId = "id",
    linkSource = "source",
    linkTarget = "target",
    weightField = null,
    directed = false,
  } = {}
) {
  const errors = [];
  const { nodes = [], links = [] } = graph;

  // Build node ID set
  const nodeIds = new Set();
  const duplicateNodes = new Set();
  for (const node of nodes) {
    const id = node[nodeId];
    if (id == null || id === "") {
      errors.push({ type: "missing-node-id", detail: "Node with missing or empty ID", data: node });
    } else if (nodeIds.has(id)) {
      duplicateNodes.add(id);
      errors.push({ type: "duplicate-node", detail: `Duplicate node ID: "${id}"`, data: { id } });
    } else {
      nodeIds.add(id);
    }
  }

  // Validate links
  const edgeSet = new Set();
  for (let i = 0; i < links.length; i++) {
    const link = links[i];
    const src = typeof link[linkSource] === "object" ? link[linkSource]?.[nodeId] : link[linkSource];
    const tgt = typeof link[linkTarget] === "object" ? link[linkTarget]?.[nodeId] : link[linkTarget];

    // Missing endpoints
    if (src == null || src === "") {
      errors.push({ type: "missing-source", detail: `Link ${i}: missing source`, data: link });
    } else if (!nodeIds.has(src)) {
      errors.push({ type: "dangling-source", detail: `Link ${i}: source "${src}" not in nodes`, data: link });
    }
    if (tgt == null || tgt === "") {
      errors.push({ type: "missing-target", detail: `Link ${i}: missing target`, data: link });
    } else if (!nodeIds.has(tgt)) {
      errors.push({ type: "dangling-target", detail: `Link ${i}: target "${tgt}" not in nodes`, data: link });
    }

    // Self-loops
    if (src != null && src === tgt) {
      errors.push({ type: "self-loop", detail: `Link ${i}: self-loop on "${src}"`, data: link });
    }

    // Duplicate edges
    const edgeKey = directed ? `${src}->${tgt}` : [src, tgt].sort().join("--");
    if (edgeSet.has(edgeKey)) {
      errors.push({ type: "duplicate-edge", detail: `Link ${i}: duplicate edge ${edgeKey}`, data: link });
    } else {
      edgeSet.add(edgeKey);
    }

    // Weight validation
    if (weightField && link[weightField] != null) {
      const w = link[weightField];
      if (typeof w !== "number" || !isFinite(w)) {
        errors.push({ type: "invalid-weight", detail: `Link ${i}: weight "${w}" is not a finite number`, data: link });
      } else if (w < 0) {
        errors.push({ type: "negative-weight", detail: `Link ${i}: negative weight ${w}`, data: link });
      }
    }
  }

  // Disconnected components — BFS from first node
  if (nodes.length > 0 && links.length > 0) {
    const adj = new Map();
    for (const id of nodeIds) adj.set(id, []);
    for (const link of links) {
      const src = typeof link[linkSource] === "object" ? link[linkSource]?.[nodeId] : link[linkSource];
      const tgt = typeof link[linkTarget] === "object" ? link[linkTarget]?.[nodeId] : link[linkTarget];
      if (adj.has(src) && adj.has(tgt)) {
        adj.get(src).push(tgt);
        if (!directed) adj.get(tgt).push(src);
      }
    }
    const visited = new Set();
    const queue = [nodeIds.values().next().value];
    while (queue.length) {
      const cur = queue.shift();
      if (visited.has(cur)) continue;
      visited.add(cur);
      for (const neighbor of adj.get(cur) || []) {
        if (!visited.has(neighbor)) queue.push(neighbor);
      }
    }
    const isolated = [...nodeIds].filter(id => !visited.has(id));
    if (isolated.length > 0) {
      errors.push({
        type: "disconnected",
        detail: `${isolated.length} node(s) not reachable from "${[...nodeIds][0]}": ${isolated.slice(0, 5).join(", ")}${isolated.length > 5 ? "..." : ""}`,
        data: { components: 2, isolated },
      });
    }
  }

  // Isolated nodes (no edges at all)
  if (links.length > 0) {
    const linkedNodes = new Set();
    for (const link of links) {
      const src = typeof link[linkSource] === "object" ? link[linkSource]?.[nodeId] : link[linkSource];
      const tgt = typeof link[linkTarget] === "object" ? link[linkTarget]?.[nodeId] : link[linkTarget];
      linkedNodes.add(src);
      linkedNodes.add(tgt);
    }
    const unlinked = [...nodeIds].filter(id => !linkedNodes.has(id));
    if (unlinked.length > 0) {
      errors.push({
        type: "isolated-nodes",
        detail: `${unlinked.length} node(s) with no edges: ${unlinked.slice(0, 5).join(", ")}${unlinked.length > 5 ? "..." : ""}`,
        data: { nodes: unlinked },
      });
    }
  }

  return { valid: errors.length === 0, errors, graph };
}

/**
 * Clean network data so D3 layouts can process it.
 * Removes self-loops, deduplicates edges, adds missing nodes,
 * removes dangling references, and clamps weights.
 *
 * @param {Object} graph - { nodes, links }
 * @param {Object} options - same as validateNetwork
 * @returns {Object} cleaned { nodes, links }
 */
export function cleanNetwork(
  graph,
  {
    nodeId = "id",
    linkSource = "source",
    linkTarget = "target",
    weightField = null,
    directed = false,
  } = {}
) {
  let { nodes, links } = graph;
  nodes = nodes.map(n => ({ ...n }));
  links = links.map(l => ({ ...l }));

  // Deduplicate nodes — keep first occurrence
  const seenNodes = new Set();
  nodes = nodes.filter(n => {
    const id = n[nodeId];
    if (id == null || id === "" || seenNodes.has(id)) return false;
    seenNodes.add(id);
    return true;
  });

  // Resolve link source/target to string IDs
  const resolveId = (val) => typeof val === "object" ? val?.[nodeId] : val;

  // Add missing nodes referenced by links
  for (const link of links) {
    const src = resolveId(link[linkSource]);
    const tgt = resolveId(link[linkTarget]);
    if (src && !seenNodes.has(src)) { nodes.push({ [nodeId]: src }); seenNodes.add(src); }
    if (tgt && !seenNodes.has(tgt)) { nodes.push({ [nodeId]: tgt }); seenNodes.add(tgt); }
  }

  // Remove self-loops
  links = links.filter(l => {
    const src = resolveId(l[linkSource]);
    const tgt = resolveId(l[linkTarget]);
    return src !== tgt;
  });

  // Remove links with missing endpoints
  links = links.filter(l => {
    const src = resolveId(l[linkSource]);
    const tgt = resolveId(l[linkTarget]);
    return src && tgt;
  });

  // Deduplicate edges — keep first occurrence
  const edgeSeen = new Set();
  links = links.filter(l => {
    const src = resolveId(l[linkSource]);
    const tgt = resolveId(l[linkTarget]);
    const key = directed ? `${src}->${tgt}` : [src, tgt].sort().join("--");
    if (edgeSeen.has(key)) return false;
    edgeSeen.add(key);
    return true;
  });

  // Clamp negative weights
  if (weightField) {
    links = links.map(l => {
      if (l[weightField] != null && (typeof l[weightField] !== "number" || !isFinite(l[weightField]) || l[weightField] < 0)) {
        return { ...l, [weightField]: 0 };
      }
      return l;
    });
  }

  return { nodes, links };
}
