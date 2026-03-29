---
name: linked-views
description: "Design patterns for multi-chart dashboards. Use this skill to choose the right layout (Overview+Detail, Cross-filtering), manage scale consistency, and handle visual feedback (Ghost/Active patterns). Covers cognitive load limits, complementarity, and state serialization for shareable views."
---

# Linked Views

A single chart answers one question; linked views let the viewer ask a question in one chart and see the answer ripple across others. The power is combinatorial: N views provide N simultaneous angles on the same data. The judgment is ensuring these views coalesce into a single "instrument" rather than a fragmented cockpit of disconnected widgets.

For the technical "wiring" (d3.dispatch, stores, framework bridges), see `coordination`. For brush mechanics, see `brushing`. For faceted layouts of the same chart type, see `small-multiples`.

## When Not to Link

Linking has a cognitive cost. Every view splits attention. Follow the principles of **Parsimony** and **Complementarity**:

- **Parsimony (Cowan's 4-chunk limit):** Use the fewest views necessary. Beyond 3–4 simultaneously active views, viewers struggle to track which interaction caused which update. Group 6+ views into hierarchical clusters (one "driver" panel + several "detail" panels).
- **Complementarity:** Link views only when different encodings reveal correlations or disparities invisible in any single view. If a link doesn't answer "what does this selection look like from *that* angle?", remove it.
- **Attention Management:** Guide the user. Render the "source" chart instantly; let linked "target" charts follow 1–2 frames later (see `coordination` for render priority). This maintains the user's focus on the chart they are touching.

## Design Patterns

### 1. Overview + Detail (Focus + Context)
One chart shows the "big picture" (e.g., a timeline of 10 years), while another shows a high-resolution "detail" (e.g., a specific month). Brushing the overview updates the detail chart's scale domain.

### 2. Cross-filtering
Multiple histograms or charts acting as simultaneous filters. Brushing any dimension filters the data shown in **all** other dimensions. See the `coordination` skill for high-performance bitmap indexing to handle large datasets.

### 3. Ghost + Active Layering
Show the filtered subset against the full dataset to maintain context.
- **Background (Ghost):** The full dataset, rendered in light gray. Static.
- **Foreground (Active):** The filtered subset, rendered in accent colors. Dynamic.
- **Density Scaling:** When selection is small, KDE/Density curves will naturally "spike." Scale the active curve height by `subset.length / total.length` to keep it visually comparable to the ghost.

## Scale Domain Strategies

- **Fixed Domain (Stable):** Compute once from the full dataset. This preserves the viewer's spatial memory (e.g., "high values are at the top"). Best for fast-moving brushes.
- **Auto-rescale (Responsive):** Recompute the scale domain on filter change to reveal local structure. **Pitfall:** Rescaling *during* a brush drag is jarring. **Strategy:** Use fixed domains during the "drag" and only trigger the transition to the auto-rescaled domain on the brush "end."

## User Experience

### State Serialization (Shareable Views)
Encode the dashboard state in the URL. Serialize filters, selection keys, and zoom transforms (`k, x, y`). Use `history.replaceState` so users can share a specific "slice" of the data simply by copying the link.

### Tooltip Coordination
Multiple charts showing tooltips simultaneously is "noisy." Use a single shared tooltip element. When the pointer is over Chart A, hide any tooltips from Chart B and anchor the shared tooltip to the cursor.

### Animation and Feedback
- **Highlighting:** Use a color flash or subtle scale boost on linked elements within 50ms of an interaction.
- **Transitions:** Use 300ms transitions on brush *end*. Avoid transitions during the *drag* itself to maintain 60fps responsiveness.

## Scaling to Large Data

If your dataset exceeds browser memory (>10M rows) or requires complex SQL aggregation, consider **Mosaic + DuckDB-WASM**. Mosaic routes filter predicates as SQL WHERE clauses, allowing D3 to act as the rendering layer for a database-backed dashboard.
