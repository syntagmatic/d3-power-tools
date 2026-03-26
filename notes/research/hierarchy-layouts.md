# Hierarchy Layouts Research

Research into hierarchy visualization techniques not well covered (or only lightly mentioned) in the current `hierarchy-layouts` skill.

## Current Coverage

The skill (`skills/hierarchy-layouts/SKILL.md`) covers:
- **Layout selection table**: treemap, sunburst, icicle, pack, tree, cluster with viewer-question framing
- **When NOT to use hierarchies**: flat data, exact comparison, too many leaves, no size variable
- **Data validation**: stratify pitfalls, cycle detection
- **`.sum()` vs `.count()`**: accessor semantics, internal-node gotcha
- **Tiling strategies**: squarify, resquarify, binary, sliceDice (brief descriptions)
- **Coordinate systems**: tree/cluster vs radial vs space-filling vs pack
- **Radial labels**: rotation, flipping, arc-length hiding
- **Layout transitions**: radial-to-Cartesian jump-free interpolation
- **Link generators**: swapping x/y, radial links
- **Common pitfalls**: paddingTop, label overlap (4 strategies), sunburst root, squarify animation

**Gaps identified:**
1. Icicle mentioned in the layout table but no dedicated implementation section
2. Flame charts/graphs not mentioned at all
3. Marimekko/mosaic as hierarchy-derived layout not mentioned
4. No Observable Plot tree mark comparison
5. Tiling algorithm section is brief -- lacks visual tradeoff guidance and the slice/dice primitives

---

## Icicle Plots (horizontal partition, when it beats sunburst)

An icicle plot is the Cartesian equivalent of a sunburst. Both use `d3.partition()`, but icicles render rectangles instead of arcs.

### When icicle beats sunburst

- **Size comparison**: Rectangles sharing a common baseline allow direct width comparison. Arc angles require the viewer to estimate angular extent, which is perceptually harder.
- **Label placement**: Horizontal rectangles accommodate text labels naturally. Sunburst labels need rotation, flipping, and arc-length filtering.
- **Deep hierarchies**: Sunburst outer rings get disproportionate area (area grows with r^2, even with `scaleSqrt` correction). Icicle rectangles at every depth have the same height, so depth doesn't distort proportional width.
- **Print / static output**: No rotation means icicle labels work in PDFs and screenshots without interactive hover fallbacks.

### When sunburst beats icicle

- **Compact**: Sunburst uses radial space efficiently for wide-but-shallow trees (many siblings at depth 1).
- **Aesthetic / engagement**: The radial form is more visually distinctive and draws attention in dashboards.
- **Center navigation**: The sunburst center is a natural "zoom out" target.

### D3 implementation pattern

The key insight is that `d3.partition()` lays out in x/y but icicle **swaps them** to get a horizontal flow:

```js
const partition = d3.partition()
  .size([height, width])   // note: height first, width second
  .padding(1);

const root = partition(d3.hierarchy(data).sum(d => d.value).sort((a, b) => b.value - a.value));

// Rectangles: width comes from y-dimension, height from x-dimension
cell.append("rect")
  .attr("x", d => d.y0)
  .attr("y", d => d.x0)
  .attr("width", d => d.y1 - d.y0)
  .attr("height", d => d.x1 - d.x0);
```

For a **top-down icicle** (vertical, roots at top), use the normal coordinate mapping without swapping:

```js
const partition = d3.partition()
  .size([width, height])
  .padding(1);

cell.append("rect")
  .attr("x", d => d.x0)
  .attr("y", d => d.y0)
  .attr("width", d => d.x1 - d.x0)
  .attr("height", d => d.y1 - d.y0);
```

### Zoomable icicle

Observable's zoomable icicle shows only 3 layers at a time. On click, it transitions the partition view to re-root at the clicked node, using `d3.interpolate` on the x and y scales. This is the same pattern as zoomable sunburst but without the arc interpolation complexity.

### Sources

- [Icicle / D3 - Observable](https://observablehq.com/@d3/icicle)
- [Zoomable Icicle / D3 - Observable](https://observablehq.com/@d3/zoomable-icicle)
- [vasturiano/icicle-chart](https://github.com/vasturiano/icicle-chart) -- web component wrapper supporting 4 orientations

---

## Flame Charts (inverted icicle for profiling data, call stacks)

Flame charts and flame graphs are hierarchy visualizations invented by Brendan Gregg (Netflix) for performance profiling. They are conceptually **inverted icicle plots** where the root is at the bottom and children grow upward.

### Flame graph vs flame chart

These terms are often confused. The critical difference:

| | Flame Graph | Flame Chart |
|---|---|---|
| **X-axis** | Alphabetical (no time meaning) | Time-ordered (chronological) |
| **Merging** | Identical stack frames merged | Each call instance is separate |
| **Question** | "Which functions consume the most CPU?" | "When did this function execute?" |
| **Width meaning** | Total sampled time across all calls | Duration of a single call |
| **Used in** | Linux perf, Brendan Gregg's tools | Chrome DevTools, Firefox Profiler |

### Why this matters for hierarchy visualization

Flame graphs are one of the most widely-used hierarchy visualizations in practice -- every developer encounters them in browser devtools. They demonstrate:
- **Inverted partition layout** (root at bottom, leaves at top)
- **Alphabetical vs temporal x-ordering** as a design choice
- **Frame merging** as data aggregation on hierarchies
- **Search highlighting** (dimming non-matching frames) as an interaction pattern
- **Zoom by re-rooting** (click a frame to make it the new root, same as zoomable icicle)

### D3 implementations

- **[d3-flame-graph](https://github.com/spiermar/d3-flame-graph)** (Martin Spier, Netflix): The canonical D3 implementation. Supports zoom, search, tooltips, color schemes, differential flame graphs (comparing two profiles). Built as a reusable D3 component.
- **[d3-flame-graphs](https://github.com/cimi/d3-flame-graphs)**: Optimized for large profiles -- only renders visible frames, yielding 10-20x performance improvement for very large traces.

### Implementation with d3.partition

A flame graph is literally a partition layout with `y` inverted:

```js
const partition = d3.partition()
  .size([width, height])
  .padding(0);  // no padding -- frames are contiguous

// Invert y so root is at bottom
cell.append("rect")
  .attr("x", d => d.x0)
  .attr("y", d => height - d.y1)  // flip y
  .attr("width", d => d.x1 - d.x0)
  .attr("height", d => d.y1 - d.y0);
```

For flame **charts** (time-ordered), you need to set x positions from timing data rather than letting partition compute them proportionally. This typically means a custom layout rather than `d3.partition()`.

### Potential skill coverage

Could be added as a subsection of icicle/partition, or referenced from a future `profiling-visualization` skill. The key teaching points are: partition orientation options, alphabetical vs time ordering, and the search/highlight interaction pattern.

### Sources

- [Brendan Gregg - Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- [The Flame Graph - ACM Queue](https://queue.acm.org/detail.cfm?id=2927301)
- [Flame Chart vs Flame Graph](https://medium.com/performance-engineering-for-the-ordinary-barbie/profiling-flame-chart-vs-flame-graph-7b212ddf3a83)
- [d3-flame-graph (spiermar)](https://github.com/spiermar/d3-flame-graph)
- [Flame Charts: The Time-Aware Sibling](https://www.polarsignals.com/blog/posts/2025/05/28/flamecharts-the-time-aware-sibling-of-flame-graphs)

---

## Marimekko/Mosaic (variable-width bars, 2D proportional area)

A Marimekko (or mosaic) chart is a two-dimensional stacked bar chart where both column widths and segment heights encode data values. It is functionally a **two-level slice-and-dice treemap**.

### When to use

- **Two categorical dimensions + one quantitative**: e.g., market segments (columns) by product categories (rows), sized by revenue.
- **Fewer than ~7 columns**: More than that and the variable widths become hard to read. For many categories, use a treemap instead.
- **Part-to-whole with two groupings**: Shows both how a total breaks down by one dimension (column width) and how each group breaks down by another (segment height).

### Relationship to treemap

A Marimekko chart is exactly `d3.treemapSliceDice` applied to a two-level hierarchy:
- Level 1 (depth=1): sliced horizontally into columns of variable width
- Level 2 (depth=2): diced vertically into segments within each column

This means the D3 implementation is trivially a treemap with a specific tiling strategy.

### D3 implementation pattern

```js
const treemap = d3.treemap()
  .round(true)
  .tile(d3.treemapSliceDice)
  .size([width, height]);

// Group flat data into 2-level hierarchy
const root = d3.hierarchy(
    d3.group(data, d => d.market, d => d.segment)
  )
  .sum(d => d.value);

treemap(root);

// Render leaves as colored rectangles
// Render depth-1 nodes as column headers with totals
```

### Perceptual limitations

Stephen Few (Perceptual Edge) has criticized Marimekko charts because:
- Variable column widths make vertical comparison across columns unreliable (no shared baseline for segments at the same categorical level)
- Area encoding is less accurate than position encoding
- A grouped bar chart often communicates the same data more clearly

Use Marimekko when the **part-to-whole composition** is the primary message, not when precise cross-group comparison matters.

### Sources

- [Marimekko / D3 - Observable](https://observablehq.com/@d3/marimekko-chart)
- [Perceptual Edge - Marimekko critique](https://www.perceptualedge.com/example13.php)
- [6 examples of Marimekko charts with D3 code](https://medium.com/visual-analytics-field-notes/6-examples-of-beautiful-marimekko-charts-a-k-a-mosaic-plots-2-examples-with-d3-code-34b73f2396c7)

---

## Observable Plot Tree Patterns

Observable Plot provides a high-level `tree` mark that wraps D3's tree and cluster layouts with a declarative API. Understanding Plot's approach is useful for identifying what the low-level D3 skill should teach vs what Plot already handles.

### What Plot handles automatically

- **Path-based data**: Pass an array of slash-separated strings (like file paths) and Plot calls `d3.stratify` internally
- **Link generation**: The composite `tree` mark renders both nodes and links automatically
- **Label placement**: Text anchoring and mirrored labels (left side reads right-to-left) are built in
- **Layout algorithm**: Defaults to Reingold-Tilford tidy tree; `Plot.cluster()` variant aligns leaves

### API surface

```js
// Simplest form -- array of path strings
Plot.tree(["a/b/c", "a/b/d", "a/e"], { textStroke: "white" })

// With options
Plot.tree(data, {
  path: "name",           // accessor for slash-separated path
  delimiter: ".",          // custom delimiter
  treeLayout: d3.cluster,  // or custom layout function
  text: d => d.name,       // label accessor
  dot: true,               // show node dots
  stroke: "#999",          // link color
  textStroke: "white"      // label halo
})
```

### Custom layout support

Plot accepts any function with the `d3.tree()` signature as `treeLayout`, enabling indent layouts, radial layouts, or entirely custom positioning:

```js
function indent() {
  return (root) => {
    root.eachBefore((node, i) => {
      node.y = node.depth;
      node.x = i;
    });
  };
}
Plot.tree(data, { treeLayout: indent })
```

### What Plot does NOT handle

- **Space-filling layouts** (treemap, partition, pack) -- Plot has no marks for these
- **Canvas rendering** for large hierarchies
- **Interaction** (expand/collapse, zoom, drill-down)
- **Custom link shapes** (only straight links via the mark system)

### Implications for the skill

The D3 skill should focus on what Plot cannot do: space-filling layouts, Canvas rendering, interaction patterns, custom link generators, and the coordinate-system subtleties that Plot abstracts away. For simple node-link trees, pointing users to Plot is reasonable.

### Sources

- [Plot Tree Mark](https://observablehq.com/plot/marks/tree)
- [Plot Tree Transform](https://observablehq.com/plot/transforms/tree)

---

## Tiling Algorithm Selection (deeper comparison)

The current skill lists four tiling strategies with one-line descriptions. Here is a deeper comparison.

### Algorithm mechanics

| Algorithm | How it subdivides | Aspect ratio | Order preservation | Animation stability |
|---|---|---|---|---|
| **treemapSquarify** | Greedy row-packing to minimize worst aspect ratio | Best (targets phi ~1.618) | None -- reorders freely | Poor -- nodes jump on data change |
| **treemapResquarify** | Same as squarify but caches topology | Good (first layout optimal, degrades on updates) | Preserved after first layout | Best -- only sizes change |
| **treemapBinary** | Recursive median-split, alternates H/V by container shape | Moderate | Partial -- binary partitioning is deterministic | Good |
| **treemapSlice** | Top-to-bottom strips | Poor (elongated horizontal) | Preserved (input order) | Perfect -- positions are stable |
| **treemapDice** | Left-to-right strips | Poor (elongated vertical) | Preserved (input order) | Perfect |
| **treemapSliceDice** | Alternates slice/dice by depth | Moderate (better than pure slice or dice) | Preserved | Good |

### Visual characteristics

**Squarify** produces the most readable static layouts. Cells are close to square, making area comparison easier (Kong et al. showed that aspect ratios near 1 minimize area judgment error). The tradeoff: it completely reorders nodes to achieve good aspect ratios. If you animate between two data states, cells teleport to new positions.

**Resquarify** solves the animation problem by caching the initial topology. On the first call it produces identical output to squarify. On subsequent calls with changed data, it changes cell sizes but preserves positions. Aspect ratios degrade over time as the cached topology diverges from what squarify would choose.

**Binary** is a good middle ground. It recursively splits nodes near the median value, choosing horizontal splits for wide containers and vertical for tall ones. Aspect ratios are worse than squarify but better than slice-dice. The recursive binary split means small data changes produce small layout changes.

**SliceDice** is the only algorithm where spatial position is fully deterministic from input order. This makes it the right choice when:
- Position encodes a second variable (e.g., time along x-axis)
- The viewer needs to track a specific node across data updates
- You are building a Marimekko chart (2-level slice-dice is exactly a Marimekko)

**Slice and Dice** (the primitives) are rarely used directly, but are the building blocks. `treemapSlice` creates horizontal strips (top-to-bottom), `treemapDice` creates vertical strips (left-to-right). Use them when you want single-direction subdivision at a specific level.

### Custom aspect ratio

Squarify and resquarify accept a custom target ratio:

```js
d3.treemapSquarify.ratio(2)  // wider rectangles
d3.treemapSquarify.ratio(1)  // perfect squares (tighter packing)
```

The default `(1 + Math.sqrt(5)) / 2` (golden ratio, ~1.618) is based on perceptual research. Changing it is rarely beneficial unless you have a specific visual constraint.

### Decision flowchart

```
Is the treemap animated (data transitions)?
  YES -> treemapResquarify
  NO  -> Does spatial position encode meaning (e.g., time)?
           YES -> treemapSliceDice (or slice/dice primitives)
           NO  -> Is the hierarchy exactly 2 levels?
                    YES -> Is it a Marimekko? -> treemapSliceDice
                           Otherwise -> treemapSquarify
                    NO  -> treemapSquarify (best aspect ratios)
                           Consider treemapBinary if stability matters
                             more than aspect ratio quality
```

### Sources

- [D3 Treemap Tiling](https://d3js.org/d3-hierarchy/treemap)
- [Squarified Treemaps - Bruls et al.](https://www.win.tue.nl/~vanwijk/stm.pdf)
- [Perceptual Guidelines for Treemaps - Kong et al.](https://doi.org/10.1109/TVCG.2010.186)

---

## Decision Guidance

### Adding to the layout selection table

The existing skill's layout table should be expanded:

| Layout | Emphasizes | Viewer question |
|---|---|---|
| **Icicle** | Depth + proportion (comparison-friendly) | "How does this break down, and which parts are biggest?" |
| **Flame graph** | Aggregated call frequency | "Which code paths consume the most CPU?" |
| **Flame chart** | Temporal call sequence | "When did each function execute, and how long?" |
| **Marimekko** | 2D part-to-whole | "How does market share break down by segment and region?" |

### When to add these to the skill

**Icicle**: Should get a dedicated implementation subsection. It's already mentioned in the layout table but there's no code showing the x/y swap pattern or the zoomable variant. This is a gap -- icicle is a first-class partition layout used in Observable's own examples.

**Flame graph/chart**: Worth a brief "Partition Orientation Variants" subsection showing that icicle (top-down), flame graph (bottom-up), and horizontal icicle (left-to-right) are all the same partition layout with different coordinate mappings. The flame chart (time-ordered x-axis) is a different beast that deserves a mention but may belong more in `time-series` or a dedicated profiling skill.

**Marimekko**: Worth a one-paragraph mention in the tiling strategies section, since it's literally `treemapSliceDice` on a 2-level hierarchy. Not worth a full section -- it's a specialized application of existing concepts.

**Observable Plot tree**: Worth a brief note in a "See Also" or "Alternatives" section. The skill should acknowledge that for simple node-link trees, Plot is often sufficient, and the D3 skill's value is in space-filling layouts, Canvas, and interaction.

---

## Code Patterns

### Partition orientation variants (unified pattern)

All four orientations use the same `d3.partition()` layout with different coordinate mapping:

```js
const partition = d3.partition().size([width, height]).padding(1);
const root = partition(hierarchy);

// Top-down icicle (root at top, children below)
rect.attr("x", d => d.x0).attr("y", d => d.y0);

// Bottom-up flame graph (root at bottom, children above)
rect.attr("x", d => d.x0).attr("y", d => height - d.y1);

// Left-to-right icicle (root at left)
// Use .size([height, width]) and swap:
rect.attr("x", d => d.y0).attr("y", d => d.x0)
    .attr("width", d => d.y1 - d.y0).attr("height", d => d.x1 - d.x0);

// Sunburst (radial)
// Use scaleSqrt for radius, scaleLinear for angle
```

### Marimekko as treemap

```js
const treemap = d3.treemap()
  .tile(d3.treemapSliceDice)
  .size([width, height])
  .round(true);

const root = d3.hierarchy(
  d3.group(data, d => d.category, d => d.subcategory)
).sum(d => d.value);

treemap(root);

// depth-1 nodes are variable-width columns
// depth-2 nodes are segments within columns
```

### Flame graph search/highlight

```js
function searchFlame(root, query) {
  root.each(d => {
    d.data._matched = d.data.name.toLowerCase().includes(query);
  });
  // Dim non-matching, highlight matching
  cells.attr("opacity", d => d.data._matched ? 1 : 0.3);
}
```

### Plot tree (for comparison)

```js
// Plot equivalent of a D3 tidy tree
Plot.tree(paths, {
  textStroke: "white",
  treeLayout: d3.tree,  // default
  // or d3.cluster for dendrogram
})
```
