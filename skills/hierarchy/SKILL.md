---
name: hierarchy
description: "Tree-structured and nested data in D3: choosing treemap, sunburst, icicle, flame graph, circle packing, tree, cluster, dendrogram or radial tree; d3.stratify, sum/count, tiling (squarify, resquarify, sliceDice, Marimekko), radial labels; collapsible trees, zoomable treemap/sunburst/pack, drill-down, breadcrumbs, focus+context; hierarchical edge bundling with d3.curveBundle beta, LCA routing, dependency wheels, bundled layout transitions."
---

# Hierarchy

Every table with a parent column is a tree, but the layout decides which question the viewer can answer: leaf sizes, depth, grouping, or paths. Models pick sunbursts because they look good and treemaps because they're familiar. This skill is about picking by question, then making the result navigable, then drawing cross-links over it.

## Which layout

| If the viewer needs... | Use | Channel | Not |
|---|---|---|---|
| to compare leaf sizes ("where is the budget going?") | **treemap** | area of rectangles | sunburst or pack: angle and circle area are judged worse |
| every level at once, deep tree (5+ levels) | **icicle** | width on a common baseline | treemap: inner levels get crushed into slivers |
| every level, shallow and wide, compact or radial look | **sunburst** | angle; radius through `scaleSqrt` | sunburst for size comparison |
| which code paths cost the most | **flame graph** (partition, y flipped, frames sorted so stacks merge) | width = total time | a time-ordered flame *chart* if you meant aggregate |
| grouping and containment over exact size | **pack** | enclosure (wastes a lot of space) | pack for reading values |
| parent-child paths, topology | **tree** | position and links | any space-filling layout: they hide edges |
| paths with leaves compared side by side, or a ring for bundling | **cluster** (dendrogram) | leaves aligned at one depth | tree when leaf alignment matters |

Don't use a hierarchy layout when:
- the data is flat (bar chart);
- exact comparison matters (position on a common scale beats area beats angle);
- there's no size variable: space-filling layouts become uniform grids. Use `.count()` deliberately or switch to tree/cluster;
- there are 500+ leaves and no interaction: add drill-down or aggregate into "Other."

### Tiling

| Situation | Tile |
|---|---|
| Static, sizes are the point | `treemapSquarify` (default) |
| Values change and cells animate | `treemapResquarify`: keeps the arrangement so cells resize instead of jumping |
| Order or position means something; Marimekko | `treemapSliceDice` |
| Deterministic balanced splits | `treemapBinary` |

## Layout traps

- `stratify` throws `missing: X` / `ambiguous: X` on orphan or duplicate ids. Common causes: trailing whitespace, `""` vs `null` for the root's parent, a header row in the data. Validate first with `scripts/validate-hierarchy.js`.
- `.sum(f)` **adds** `f(node)` for internal nodes to their children's total. Leaf-only: `root.sum(d => d.children ? 0 : d.value)`.
- `.sum()` does **not** clamp negatives: they subtract from ancestors and yield zero or negative cells. Size by `Math.abs`, encode sign with color.
- `.sum()` before `.sort()`: sort reads `.value`.
- All cells the same size: `.count()` where `.sum()` was meant.
- tree/cluster `.size([cross, depth])`: a horizontal tree is `.size([height, width])` drawn at `(d.y, d.x)`. Radial: `d.x` is angle in radians, `d.y` is radius, 0 at 12 o'clock: `[d.y * Math.cos(d.x - Math.PI / 2), d.y * Math.sin(d.x - Math.PI / 2)]`.
- Radial labels on the left half read upside down unless flipped with an extra `rotate(180)` and `text-anchor: end`.
- Sunburst root disc swallows the center: filter `depth > 0` or keep it as the zoom-out target.
- `paddingTop` with no label drawn leaves a gap viewers try to interpret.
- Treemap labels: measure, truncate, hide below ~16px cell height. Measure only after the text is in the DOM.

## Interaction

| If the task is... | Use | Avoid when |
|---|---|---|
| finding a node in a big tree | collapsible tree (`_children` toggle) | branches must be compared, or a level has 50+ siblings (every toggle shifts all of them) |
| drilling into nested sizes, 3+ meaningful levels | zoomable treemap | 2 levels: a static treemap with group labels shows everything |
| drilling by level, radial | zoomable sunburst | size comparison matters: stretched arcs lose part-to-whole |
| drilling into groups | zoomable pack with `d3.interpolateZoom` | |
| panning over a huge hierarchy | Canvas + geometric zoom, semantic detail by `k` | |

Rules that make the animation legible:
- **Collapsible tree**: enter children at the clicked node's *old* position, exit them to its *new* one, then stash `d.x0 = d.x; d.y0 = d.y`. Re-run `.sum()` and the layout after every toggle.
- **Zoomable treemap**: lay out once and zoom by setting the x/y scale domains to the focus node's `[x0, x1]`, `[y0, y1]`. Clip each cell or children overshoot mid-transition. Breadcrumbs from `focus.ancestors().reverse()` are required.
- **Zoomable sunburst**: tween numeric `{x0, x1, y0, y1}` on `d.current` and call the arc generator per frame (`attrTween`). Never interpolate path strings.
- Re-fit labels on transition end, not per frame.

### Interaction traps

- Two unnamed transitions on the same element (transform, then opacity): the second interrupts the first and nodes never move. Chain on one transition or name them.
- Enter and update not merged: new nodes jump while old ones animate.
- `dblclick` fires two `click`s first. Use a ~250ms timer or modifier+click.
- Canvas collapse: rebuild the hit-test quadtree when the animation ends, not when it starts.
- Touch: aim for 44×44px targets (WCAG 2.5.5; the AA floor in 2.5.8 is 24×24). For smaller cells, first tap selects, second tap zooms.
- SVG up to ~500 nodes for animated trees; beyond that, Canvas for the marks.

## Edge bundling

For leaf-to-leaf links over a hierarchy (imports, dependencies). Each link follows `source.path(target)`, up through the lowest common ancestor and down, drawn with `d3.curveBundle`. Links sharing ancestry merge into bundles: group-level pattern at the cost of edge-level accuracy.

**`d3.curveBundle.beta(β)` is bundling strength.** Each control point is pulled toward the straight chord by `(1 − β)`:

| β | Result |
|---|---|
| 0 | straight line between endpoints, no bundling |
| 0.85 | d3's default; clear group bundles |
| 1 | B-spline through the full LCA path, maximum bundling |

Higher β is tighter. Map a "tension" slider straight to β. `beta(1 - tension)` is backwards, and it shipped that way in the v2 examples (now fixed).

- Start at 0.85. If unrelated clusters merge into one river, drop β toward 0.5-0.7 until they separate.
- Tight bundles create false connections: viewers follow a merged bundle and read paths that don't exist. Static output gets less bundling. Interactive output gets a β slider and hover highlighting (raise the highlighted links above the faded ones).
- Layout: `d3.cluster` (every leaf on one ring), not `d3.tree`. Draw leaves only; internal nodes are invisible waypoints.
- Unmatched source/target ids drop edges silently. Log misses.
- Canvas past ~2,000 links (`line.context(ctx)`).
- Skip bundling when the question is "does A link to B" (adjacency matrix), when the hierarchy is flat or arbitrary, when most links stay inside one parent, or under ~30 links.
- Layout transitions: interpolate every node's position, internal ones included, and redraw the curves each frame. `node.path()` doesn't change, so the bundles deform smoothly.

## References

- `references/hierarchy-layouts.md`: stratify and validation, sum/count details, coordinate table, partition variants, label fitting and radial label code, color by branch/depth/change.
- `references/hierarchy-interaction.md`: `_children` toggle, Canvas collapse, zoomable treemap domain swap, sunburst target math and visibility thresholds, pack `interpolateZoom`, semantic zoom.
- `references/edge-bundling.md`: β math, link builder with miss logging, rendering tiers, layout-transition tween, other bundling families (edge-path, divided).
- `scripts/`: `validate-hierarchy.js` (`validateHierarchy`, `cleanHierarchy`) with tests; `test-hierarchy-logic.js` (hit-testing tests).
- `examples/`: layout switcher, collapsible tree, zoomable treemap, zoomable sunburst, edge bundling (β slider), edge bundling with layout transitions. Tested by `tests/test.config.json`.
