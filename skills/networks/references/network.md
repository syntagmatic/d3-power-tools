# Network forms

Absorbed from the v2 `network` skill. Open when building a matrix, arc, chord, sankey or hive plot, or when a node-link graph needs weighted edges, arrowheads, hairball reduction or a time slider.

## Adjacency matrix

Ordering is everything. Sort by community, then degree within community, and clusters show up as dense diagonal blocks:

```js
order.sort((a, b) => d3.ascending(nodes[a].group, nodes[b].group)
  || d3.descending(nodes[a].degree, nodes[b].degree));
```

Animate reorders (row `transform` and cell `x`, ~500ms) so the viewer can track which rows moved. Undirected graphs must produce a symmetric matrix; if yours isn't, half the edges are missing.

## Arc diagram ordering

- By cluster: same-group arcs get short and visually group.
- By degree: hubs move to the center, and the tallest arcs are the bridges.
- Minimize crossings: NP-hard in general; greedy barycenter heuristics work under ~500 nodes.

Labels go below the axis, rotated 45°, `text-anchor: start`, staggered when neighbors collide.

## Chord

`d3.chord()` takes a square matrix; data usually arrives as `[{source, target, value}]`:

```js
const names = Array.from(new Set(edges.flatMap(d => [d.source, d.target])));
const index = new Map(names.map((name, i) => [name, i]));
const matrix = names.map(() => new Array(names.length).fill(0));
const rolled = d3.rollup(edges, v => d3.sum(v, d => d.value), d => d.source, d => d.target);
for (const [s, targets] of rolled)
  for (const [t, value] of targets) matrix[index.get(s)][index.get(t)] = value;
const chords = d3.chord().padAngle(0.05)(matrix);
```

- Undirected data: symmetrize, `matrix[i][j] = matrix[j][i] = value`.
- Bipartite data (countries to products): one `(nSrc + nTgt)²` matrix, values in the cross quadrants, zeros in the same-type quadrants.
- Outer labels follow the circle and flip on the left half so they read left to right:

```js
const labelTransform = d => {
  const a = (d.startAngle + d.endAngle) / 2;
  return `rotate(${a * 180 / Math.PI - 90}) translate(${outerRadius + 10})${a > Math.PI ? " rotate(180)" : ""}`;
};
const labelAnchor = d => (d.startAngle + d.endAngle) / 2 > Math.PI ? "end" : "start";
```

- Hide labels on thin groups: visible only when `endAngle - startAngle > 0.1`.

## Sankey

Separate package: `https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js`. It wants `{nodes: [{name}], links: [{source, target, value}]}`. Tabular rows become links between adjacent columns:

```js
const columns = ["region", "product", "channel"];
const nodeSet = new Set(), linkMap = new Map();
for (const row of data) {
  for (let i = 0; i < columns.length - 1; i++) {
    const src = `${columns[i]}:${row[columns[i]]}`, tgt = `${columns[i + 1]}:${row[columns[i + 1]]}`;
    nodeSet.add(src); nodeSet.add(tgt);
    const key = `${src}→${tgt}`;
    linkMap.set(key, (linkMap.get(key) || 0) + +row.revenue);
  }
}
const nodes = Array.from(nodeSet, name => ({name}));
const nodeIndex = new Map(nodes.map((d, i) => [d.name, i]));
const links = Array.from(linkMap, ([key, value]) => {
  const [s, t] = key.split("→");
  return {source: nodeIndex.get(s), target: nodeIndex.get(t), value};
});
```

Prefixing names with the column keeps "Other" in two columns from collapsing into one node (which creates a cycle).

d3-sankey throws on cycles. Remove back edges first with a DFS (white/grey/black; an edge into a grey node is a back edge). When the loops are the story (session revisits), use `d3-sankey-circular`, which routes back edges as arcs under the diagram.

## Hive plot

Force layouts are non-deterministic, so any pattern might be an artifact. Hive plots (Krzywinski et al. 2012) put nodes on 2-5 radial axes by explicit rules: axis from a category (role, type, community), position along it from a quantity (degree, centrality); edges are curves between axes. Use them to compare two networks, answer role questions ("do high-degree A nodes link to low-degree B?"), draw k-partite graphs, or make reproducible figures. Use force when the grouping is unknown. Reference implementation: bost.ocks.org/mike/hive.

## Node-link details

**Arrowheads.** `refX` is set once per `<marker>`, so it can't vary per link. With uniform node radius, set `refX` to clear the radius and use `markerUnits="userSpaceOnUse"` (otherwise the marker scales with `stroke-width`). With variable radii, end the path at the target's boundary instead:

```js
function trimmedEnd(s, t, pad = 2) {
  const dx = t.x - s.x, dy = t.y - s.y, len = Math.hypot(dx, dy) || 1;
  const k = (len - t.r - pad) / len;
  return [s.x + dx * k, s.y + dy * k];
}
```

`orient="auto"`; check on curved edges, where orientation follows the path's end tangent.

**Weighted edges.** Stroke width on `scaleSqrt(extent, [0.5, 6])`, which keeps heavy edges from swamping the rest. Add a sequential color on the same domain for redundancy.

**Parallel edges.** Group by the sorted `source--target` key and give each an offset index. A lone edge stays straight; parallel ones fan out as arcs with curvature proportional to the offset.

**Labels.** Sparse (<50 nodes): offset right of the node, `x = d.x + d.r + 4`. Denser: label proxy objects in a second simulation, `forceX`/`forceY` anchored to their node plus rectangular collision (see legibility's annotation reference). Never move the nodes themselves to fit labels.

**Communities.** D3 has no graph algorithms. graphology + `graphology-communities-louvain` assigns community ids; its resolution parameter sets granularity and makes a good slider. Feed ids to color, to matrix ordering, and to `d3.polygonHull` overlays. Hulls only mean something if a cluster force pulls members together (see `force.md`).

## Hairball reduction

Transparency is not a fix. In order:

1. **Weight threshold** slider: `links.filter(d => d.weight >= min)`, reset the link force, `alpha(0.3).restart()`.
2. **Top-k edges per node**: keep each node's k strongest from both source and target sides, dedupe with a Set. No isolates, unlike a global threshold.
3. **Community aggregation**: `d3.group(nodes, d => d.community)` for meta-nodes sized by count, `d3.rollups` over inter-community links for summed meta-edges. 500 nodes become 10.
4. **Switch to a matrix**, or offer a sortable table.
5. **Fisheye** on the neighborhood under the cursor, keeping the whole graph.

## Temporal networks

Filter links to a time window and fade rather than remove, so positions stay stable:

```js
function updateTime(t0, t1) {
  const active = links.filter(d => d.timestamp >= t0 && d.timestamp <= t1);
  const activeLinks = new Set(active);
  const activeNodes = new Set(active.flatMap(d => [d.source.id, d.target.id]));
  linkSel.transition().duration(300)
    .attr("stroke-opacity", d => activeLinks.has(d) ? 0.6 : 0.02);
  nodeSel.transition().duration(300)
    .attr("fill-opacity", d => activeNodes.has(d.id) ? 1 : 0.15);
}
```

Playback: step with `d3.interval`, and reheat gently (`alpha(0.1)`) per step, not a full restart.

## Accessibility

- Matrix: `role="grid"` / `row` / `gridcell`. It's already a table.
- Node-link, arc, chord, sankey: `role="img"` with a summary `aria-label`, plus the edge list or flow matrix as a table. For keyboard focus on a canvas graph, `scripts/spatial-keyboard-nav.js`.

## Sources

Ghoniem, Fekete, Castagliola (2004) and Okoe, Jianu, Kobourov (2019): matrix vs node-link task performance. Krzywinski et al. (2012): hive plots. Henry, Fekete, McGuffin (2007): NodeTrix hybrid.
