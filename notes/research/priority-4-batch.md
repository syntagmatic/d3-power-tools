# Priority 4 — Targeted Additions Research

Researched 2026-03-25. Each section identifies what's new or missing relative to the current SKILL.md.

## small-multiples

**Observable Plot faceting model.** Plot's `fx` and `fy` channels are the declarative answer to what D3 users build manually with grid math. Mark-level faceting (`mark.fx`, `mark.fy`) lets you control which marks facet vs. repeat across panels — useful for annotations that should appear in every panel. The `facet` option on marks accepts `auto | include | exclude | null`. Empty facets (when fx/fy domain includes values absent from data) are suppressed automatically.

**Facet wrapping is still manual.** Observable Plot issue [#277](https://github.com/observablehq/plot/issues/277) tracks auto-wrap for single-dimension facets (like ggplot's `facet_wrap`). The workaround: compute `fx = i % cols` and `fy = Math.floor(i / cols)` yourself. This is worth documenting as a recipe — it's the most common faceting question.

**What to add to SKILL.md:**
- Recipe for facet-wrap using computed fx/fy (the manual grid math the skill already teaches, but framed as Plot-compatible).
- Note on Plot's mark-level faceting as the declarative equivalent — readers working in Observable need to know when to reach for Plot vs. hand-rolled D3.
- Mention that Plot handles shared scales, axis deduplication, and empty facet suppression automatically — things the skill teaches manually.

## sparkcharts

**Grafana's sparkline-in-table pattern.** Grafana's stat panels embed sparklines showing recent history next to KPI values — the "big board" dashboard pattern. Their table visualization has a dedicated sparkline cell type: apply a "Time series to table" transformation and the column renders as a tiny line/bar/point chart. This is exactly the spark-in-table pattern the skill covers, but Grafana's implementation validates the design: sparklines are most effective when adjacent to the number they contextualize, not isolated in their own panel.

**Datadog and monitoring dashboards.** Monitoring tools universally adopted sparklines for metric cards — CPU, memory, request rate each get a word-sized trend line. The key design decision: these sparklines use a fixed time window (last 1h, 6h, 24h) rather than auto-scaling the x-axis, so the viewer builds intuition for "normal shape" over time.

**What to add to SKILL.md:**
- Fixed-window sparklines for monitoring contexts: always show the same time range so shape becomes recognizable. Contrast with auto-scaled sparklines where shape shifts with data extent.
- Grafana-style sparkline cell type as a reference implementation for the table-embedded pattern. The skill covers spark-in-table but could note this as the dominant real-world example.
- Dashboard KPI card layout recipe: large number + delta arrow + sparkline, the pattern every monitoring tool uses.

## data-table

**TanStack Virtual for large tables.** TanStack Virtual (formerly react-virtual) is the dominant virtualization solution: only render visible rows plus a small buffer, swap DOM elements as the user scrolls. The key architecture: TanStack Table manages data logic (sorting, filtering, column sizing), then passes its row model to a virtualizer that determines which rows to render. This separation of data logic from render logic maps well to D3's philosophy.

**Virtual scrolling without React.** The core concept is framework-agnostic: maintain a scroll container with a spacer element sized to total row height, compute visible range from scrollTop, render only those rows. With D3, this means a `div` scroll container + `table` positioned absolutely within it, rows joined to a sliding window of data. No library needed for <100K rows.

**AG Grid patterns.** AG Grid uses row virtualization by default plus column virtualization for wide tables. Their "viewport row model" is worth noting: it only requests data for the visible range from the server, enabling tables over datasets that don't fit in memory.

**What to add to SKILL.md:**
- Virtual scrolling recipe for D3: scroll container, spacer element, compute visible range, join rows to data slice. Pure DOM, no framework dependency.
- Server-side pagination as the alternative when datasets exceed browser memory (AG Grid's viewport model).
- Note that virtualization breaks Ctrl+F browser search — offer a search input as compensation.

## navigation

**Scroll-driven animations (CSS ScrollTimeline).** CSS now has native scroll-driven animations (shipped in Chrome, spec updated August 2025). `animation-timeline: scroll()` ties keyframes to scroll position — no JS needed. For D3, this is relevant for scrollytelling: instead of IntersectionObserver + imperative animation, you can bind CSS transitions to scroll progress. However, for zoom (which needs continuous transform state), d3-zoom remains the right tool — scroll-driven CSS can't manage the transform matrix that `rescaleX`/`rescaleY` depend on.

**LOD state machines.** The skill covers semantic zoom conceptually but could formalize the state machine pattern. Semantic zoom at its core is: define zoom-level thresholds, at each threshold change what's rendered (country labels -> state labels -> city labels). The state machine has discrete states with hysteresis (don't flicker at boundaries): zoom in triggers at k=4, zoom out triggers at k=3.5. Google Maps is the canonical example.

**What to add to SKILL.md:**
- Formal LOD state machine pattern: define states as zoom ranges with hysteresis bands, trigger enter/exit callbacks at transitions. Include a concrete example (e.g., scatter plot: k<2 shows density heatmap, 2<k<8 shows points as circles, k>8 shows points with labels).
- Mention CSS scroll-driven animations as the modern scrollytelling alternative, with a note on why it doesn't replace d3-zoom for interactive zoom.
- Scroll-hijack prevention: the skill should note `wheelDelta` filtering and the `scaleExtent` behavior where wheel events pass through to page scroll when at zoom limits.

## webgl

**WebGPU browser support reached critical mass.** As of November 2025, WebGPU ships by default in Chrome (since v113/2023), Firefox 141+ (Windows, July 2025; macOS with Firefox 145), Safari 26+ (macOS/iOS/iPadOS, September 2025), and Edge. Mobile remains fragmented: Chrome Android works on recent Qualcomm/ARM GPUs (Android 12+), Firefox Android still behind a flag, Safari iOS 26 requires latest OS.

**deck.gl v9 WebGPU support.** deck.gl v9 (March 2024) added WebGPU support via luma.gl v9, which provides a portable API across WebGL 2 and WebGPU. However, WebGPU support is explicitly "not production ready" — aimed at early adopters. v9.1 migrated all shaders to uniform buffers (required for WebGPU). v9.2 added preview WebGPU support and new widgets. deck.gl is likely the first geospatial viz library to adopt WebGPU.

**Practical implications for the skill.** WebGPU's compute shaders enable GPU-side data processing (binning, aggregation, force simulation) that WebGL can't do — data never round-trips to JS. But the API is substantially different from WebGL: no more `gl.bindBuffer`/`gl.bindTexture`, replaced by bind groups, render passes, and command encoders. The migration path is through abstraction layers like luma.gl, not direct porting.

**What to add to SKILL.md:**
- WebGPU status section: browser support table (Chrome/Firefox/Safari/Edge with version numbers), mobile caveats, the "not yet for production viz" assessment.
- Note deck.gl v9 as the reference for WebGPU-based viz, with luma.gl as the abstraction layer.
- Compute shaders as the killer feature for viz: GPU-side aggregation, binning, force layout ticks. This is what WebGPU offers that WebGL cannot.
- Migration guidance: don't port WebGL shaders directly, use an abstraction layer. The boilerplate difference is substantial.

## canvas-accessibility

**ARIA 1.3 new roles.** WAI-ARIA 1.3 (First Public Working Draft, January 2024) adds `comment`, `suggestion`, and `mark` roles, plus `aria-description`, `aria-braillelabel`, and `aria-brailleroledescription` attributes. `aria-details` now accepts multiple IDrefs. These aren't directly canvas-relevant, but `aria-description` is useful for hidden DOM mirrors — it provides a richer description than `aria-label` without requiring a separate described-by element.

**CSS media queries for accessibility.** Three CSS media features are now well-supported and relevant to canvas visualizations:
- `prefers-reduced-motion`: detect users who want minimal animation. Canvas animations should check `matchMedia('(prefers-reduced-motion: reduce)')` and skip/shorten transitions. 93%+ browser support.
- `prefers-contrast: more`: user wants higher contrast. Canvas should increase stroke widths, use higher-contrast palettes.
- `forced-colors`: Windows High Contrast mode. Canvas ignores forced-colors (it's a bitmap), so the hidden DOM mirror becomes the only accessible representation. The skill should note this gap.

**WCAG 2.2 legal pressure.** 4,605 ADA lawsuits in 2024 referenced WCAG 2.2. Canvas visualizations are particularly vulnerable because they're invisible to automated accessibility scanners.

**What to add to SKILL.md:**
- `prefers-reduced-motion` detection recipe for canvas: `matchMedia` query, skip transitions, show final state immediately.
- `prefers-contrast` handling: thicker strokes, higher-contrast palette, larger text.
- Note that `forced-colors` mode is invisible to canvas — the DOM mirror is the only fallback. This is a unique canvas vulnerability.
- `aria-description` (ARIA 1.3) as a lightweight alternative to `aria-describedby` for mirror elements.

## edge-bundling

**Edge-Path Bundling (Wallinger et al., 2022).** A fundamentally different approach: instead of routing edges through a spatial bundling field, edges are clustered along weighted shortest paths in the graph. This eliminates "independent edge ambiguity" — the false connections created when unrelated edges merge in traditional bundling. The level of bundling is tuned via shortest-path distance, Euclidean distance, or combinations.

**Faster Edge-Path Bundling via Graph Spanners (Wallinger, 2023).** The original algorithm had high computational cost. The follow-up paper exploits graph spanners to speed up the computation without reducing bundling quality. This makes Edge-Path Bundling practical for larger graphs.

**Divided Edge Bundling (Selassie et al.).** A separate technique for directional networks: edges in opposite directions are separated, revealing directional flow patterns that standard bundling merges. An extension of force-directed bundling.

**The skill already references CHI 2025 Wallinger research** on false connections from tight bundling (line 30 of SKILL.md). Good — the skill is already aware of this work.

**What to add to SKILL.md:**
- Edge-Path Bundling as an alternative algorithm: route edges along graph shortest paths instead of spatial proximity. Key advantage: eliminates independent edge ambiguity. Reference the 2023 spanner speedup for practical use.
- Divided Edge Bundling for directional networks: separate opposite-direction edges to reveal flow direction. Useful for import/export dependency visualization where direction matters.
- Comparison table: hierarchical (current skill focus) vs. force-directed vs. edge-path bundling — when each is appropriate.

## shape-morphing

**Flubber status.** Flubber (veltman/flubber) remains the go-to library for arbitrary shape morphing. It handles holes, subpaths, and winding-order mismatches. Still actively used (30K weekly npm downloads) but the repository has had minimal updates — it's stable/finished rather than abandoned. The skill already covers flubber appropriately as the topology-aware option.

**d3-interpolate-path.** 188K weekly npm downloads (6x flubber). Designed for unclosed line transitions where source and target have different point counts — it extends paths to match before linear interpolation. Better for line chart transitions; flubber is better for closed shape morphing.

**Polymorph.** A lighter alternative at 6KB. Works well for complex shapes but less reliable for simple ones. Worth mentioning as a size-conscious option.

**GSAP MorphSVG.** Commercial (GreenSock license). The most robust solution for production morphing — handles all edge cases, integrates with GSAP's timeline system. Not open source.

**Modern integration.** Flubber + Framer Motion is a common pattern in React/Next.js projects for SVG morph animations, showing the library's continued relevance outside the D3 ecosystem.

**What to add to SKILL.md:**
- d3-interpolate-path as the preferred tool for open path (line) transitions — it's what the skill should recommend when morphing between line charts with different data lengths. Distinct use case from flubber (closed shapes).
- Polymorph (6KB) as a lightweight alternative to flubber for size-constrained contexts.
- Note GSAP MorphSVG exists as commercial option for production apps that already use GSAP.
- Clarify the decision tree: parametric (skill's current focus) > d3-interpolate-path (open lines) > flubber (closed shapes with topology issues) > GSAP (commercial, full-featured).

## hierarchy-interaction

**Zoomable treemap implementation patterns.** The canonical Observable example (updated September 2024) uses the scale-domain-swap technique: x and y scales map the full treemap, clicking a node changes the scale domain to that node's coordinates, triggering an animated transition. This is simpler than recomputing the layout — the layout runs once, zoom is purely a scale transform.

**Breadcrumb navigation.** Modern zoomable treemaps consistently include breadcrumbs showing the path from root to current focus. This solves the "where am I?" problem that pure zoom creates. The skill covers breadcrumbs but could emphasize they're not optional — without them, users get lost after 2-3 zoom levels.

**Responsive zoomable treemaps.** Several implementations add dynamic text wrapping and mobile-friendly touch targets. Key pattern: at each zoom level, recalculate which labels fit their rectangles and hide those that don't. This is a layout-label coupling the skill should address.

**What to add to SKILL.md:**
- Scale-domain-swap as the preferred zoom technique: layout once, zoom via scale domain change. Simpler and faster than relayout.
- Breadcrumbs as mandatory (not optional) for zoomable treemaps/sunbursts. After 2+ zoom levels, users cannot reconstruct their path without them.
- Label fitting on zoom: recalculate label visibility at each zoom level based on available rect dimensions. Hide labels that don't fit rather than letting them overflow.
- Touch targets: minimum 44x44px tap areas for mobile zoomable treemaps. Small leaf nodes need an enlarged hit area or a tap-to-select-then-tap-to-zoom two-step.
