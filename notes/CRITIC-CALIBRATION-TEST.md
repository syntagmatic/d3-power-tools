# Visual Critic Calibration Test

Evaluated 2026-03-26 using meta/visual-critic/SKILL.md scoring criteria.

---

## Block 02: Linked Scatterplot Matrix

**Context:** Data visualization — a scatterplot matrix (SPLOM) of the Iris dataset with kernel density estimates on the diagonal, colored by species.

**First impression:** A compact, well-organized grid with a pleasant three-color palette that reads clearly against the white background.

**Score: 7** — Deliberately designed. The soft green/blue/pink palette is harmonious and avoids default schemeCategory10. The diagonal KDE panels are a smart use of the matrix space. Typographic hierarchy is present: column headers at the top, axis labels on the sides, legend at the bottom. Whitespace between cells is tight but functional. The overall impression is a considered, competent SPLOM that feels intentional rather than generated.

**What works:** The three-class color palette is muted and harmonious — the colors separate clearly without clashing. Using density curves on the diagonal instead of empty or mirrored cells adds information without clutter.

**What doesn't:** The axis tick labels are very small and hard to read at this rendered size — they're at the threshold of legibility. The legend at the bottom is cramped and could use more breathing room from the last row of plots.

---

## Block 03: Violin Plot Orchestra

**Context:** Data visualization — a small-multiples grid of violin plots showing daily temperature distributions by city (rows) and month (columns).

**First impression:** The violins are rendered far too small to read — the entire visualization occupies roughly the top quarter of the viewport, leaving the bottom three-quarters as dead whitespace.

**Score: 3** — Renders but is functionally broken at this size. The violins are tiny dashes — you can see that something is there, colored in blue/pink, but you cannot compare distributions across cities or months because the shapes are indistinguishable at this scale. The y-axis labels on the left are barely legible. The layout wastes enormous viewport space. The title and subtitle show some typographic intention, and the two-color encoding (min/max?) is a reasonable concept, but none of it lands because you simply cannot see the data.

**What works:** The grid structure is logically organized (cities x months), and the title/subtitle pairing shows some typographic hierarchy. The two-color encoding is a reasonable design choice.

**What doesn't:** The violins are too small to read — the core "does it work at its rendered size?" gate fails. The visualization needs to either fill the viewport or use a larger cell size. The bottom 75% of the page is empty gray background.

---

## Block 05: Crossfilter Flight Explorer

**Context:** Interactive tool — a crossfilter dashboard with three linked histograms (departure hour, delay, distance) for exploring 2,000 flights.

**First impression:** Clean, functional, and well-spaced — a competent crossfilter implementation with good proportions but no visual refinement beyond the defaults.

**Score: 5** — Generic but working. The layout is good: three charts stacked vertically with generous margins, clear axis labels, and a useful "Showing X of Y flights" counter. The typographic hierarchy works — bold title, lighter subtitle count, chart headers in a smaller weight. But the single SteelBlue fill is pure default D3. There's no color variation to distinguish the three dimensions, no subtle background or gridlines to guide the eye, and the bars have no rounding or styling. It communicates its data clearly but looks like a first draft.

**What works:** Proportions and spacing are excellent — each histogram has room to breathe, axes are legible, the title bar with record count and reset button is well-placed. The vertical stacking makes the brushing interaction intuitive.

**What doesn't:** SteelBlue everywhere is the canonical "I didn't choose a color" signal. The charts would benefit from even subtle differentiation — a muted palette across the three dimensions, or at minimum a selected/unselected color pair for the brush interaction.

---

## Block 21: US Choropleth

**Context:** Data visualization — a choropleth map of broadband access by state with a sequential blue color scheme on a dark blue background.

**First impression:** Bold cartographic choice with the dark blue background, but the state fills blend into the ocean, making lower-value states nearly invisible.

**Score: 4** — The dark blue background creates a serious legibility problem. States with low broadband access values are encoded in dark blue, which is nearly indistinguishable from the dark blue background/ocean. This means a significant portion of the data encoding is invisible — the "does it work?" gate is partially failed. You can see the high-value states (white/light blue), but the low end of the scale disappears. The state borders (thin lighter lines) help somewhat but don't rescue the problem. The legend at the bottom is readable, and the Albers projection with inset Alaska/Hawaii is correct. The title and subtitle show typographic care. But the fundamental color-background interaction undermines the chart's purpose.

**What works:** The title/subtitle typographic pairing is clean. The legend is well-formatted with clear breakpoints. The projection and state geometry render correctly.

**What doesn't:** Dark-blue-on-dark-blue: states in the lowest broadband bracket are nearly invisible against the ocean/background, defeating the purpose of a choropleth. The border strokes are the only way to find those states, which means the color encoding has failed for that data range. Either the background needs to contrast with the low end of the scale, or the scale needs to avoid the background hue.

---

## Block 32: Shape Morphing Gallery

**Context:** Tech demo — a 3x3 grid of shape morphing demonstrations (circle-to-rectangle, bar-to-pie, star-to-circle, etc.).

**First impression:** Clean card layout with varied colors, but most cards are empty — only 4 of 9 panels show visible shapes, and the remaining 5 are blank white cards with labels.

**Score: 4** — The gallery layout is well-structured: consistent card sizes, subtle border/shadow, centered labels below each card. The four visible shapes (blue square, pink pie slice, green star, cyan area chart) use distinct colors that feel somewhat coordinated. But five of nine cards are completely empty — they show only the label text with no shape rendered. For a gallery meant to showcase morphing techniques, having more than half the panels blank makes it look unfinished. The shapes that do render are static (this is a screenshot, so animations aren't visible), but they're clear and well-sized within their cards.

**What works:** The 3x3 card grid is clean and well-proportioned with consistent spacing. The four visible shapes are clearly rendered and use distinct, non-default colors.

**What doesn't:** Five of nine cards are empty — the gallery looks incomplete. Whether this is a rendering bug or a timing issue (shapes haven't animated into view yet), the static screenshot reads as a half-finished demo. The cards also lack any visual hint that they're interactive (no hover affordance, no "click to play" cue).

---

## Block 39: Quadtree Hit Detection

**Context:** Tech demo — a Canvas-based scatter of 5,000 points with quadtree-based hit detection, Voronoi overlay toggle, and FPS counter.

**First impression:** A confetti-like spray of pastel dots on white — colorful but without clear purpose or visual structure.

**Score: 4** — The points render correctly and the UI controls (point count slider, Voronoi checkbox, FPS counter) are cleanly positioned in the corners. But the color assignment appears random — each point has an arbitrary pastel hue with no relationship to position, density, or any data dimension. This makes the scatter look like noise rather than a demonstration of spatial structure. For a quadtree hit-detection demo, you'd want the visualization to make the spatial indexing *visible* — perhaps showing the quadtree partitions, or highlighting nearby points on hover, or using color to encode density. Instead, it's a uniform random spray. The points are also quite small and faint (low opacity pastels on white), which reduces visual impact.

**What works:** The UI controls are minimal and well-placed — slider top-left, FPS top-right, unobtrusive. The point rendering is performant at 5,000 points.

**What doesn't:** The random pastel colors convey no information and give the demo a generic "confetti" look. The technique being demonstrated (quadtree hit detection) is invisible in the static screenshot — there's no visual evidence of spatial structure, hover response, or the quadtree itself. A static screenshot of this demo communicates almost nothing about what it does.

---

## Summary

| # | Block | Context | Score |
|---|-------|---------|:-----:|
| 02 | Linked Scatterplot Matrix | Data visualization | 7 |
| 03 | Violin Plot Orchestra | Data visualization | 3 |
| 05 | Crossfilter Flight Explorer | Interactive tool | 5 |
| 21 | US Choropleth | Data visualization | 4 |
| 32 | Shape Morphing Gallery | Tech demo | 4 |
| 39 | Quadtree Hit Detection | Tech demo | 4 |
