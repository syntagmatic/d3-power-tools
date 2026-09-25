---
slug: sunburst
mode: single-shot
schema: hierarchical
render-load: medium-svg
interactivity: [hover, tooltip]
skills: [hierarchy, encoding, tooltip]
provenance: new-2026-05
ablate-skill: hierarchy
---

Org budget and headcount sunburst. The dataset (`data/org-budget.json`) is
24 flat records with `division`, `department`, `team`, `headcount`, and
`budget_k`. The three levels — division → department → team — form a
containment hierarchy; arc angles partition by `budget_k`.

An outer concentric ring overlays the leaf level: one arc per team, radial
width proportional to that team's headcount normalized within its division
(the highest-headcount team per division fills the full outer band; others
scale proportionally). This dual encoding makes budget-heavy vs
headcount-heavy teams visually legible: a wide outer arc with a narrow
inner arc signals many people with a small budget share.

On hover, the chart shows a tooltip near the cursor with team name,
headcount, and budget_k. The hovered arc and its ancestors (department,
division) gain an `active` class; sibling arcs dim. Depth-1 and depth-2
arcs display a truncated label when their arc is wide enough (roughly:
midpoint angle span > 15°).

Render-load is **medium-svg**: all arcs, outer-ring arcs, and labels are
SVG paths and text.

## Expected output

A centered sunburst fills most of the viewport. Three concentric bands:

- **Depth 1** — four division arcs (Engineering, Product, Sales,
  Operations), each a distinct categorical color, labeled.
- **Depth 2** — twelve department arcs, tinted from their division color,
  labeled when wide enough.
- **Depth 3** — twenty-four team arcs, deeper tints of their division.

Beyond the main three bands an additional outer ring sits flush against
the outermost sunburst band. Each of the 24 teams has one arc in this
ring; radial width spans from 0 to a fixed maximum proportional to
headcount within the division. Engineering's Core (18) and Infra (14)
arcs are wider than NetSec (5); Sales' Americas (22) and Outbound (20)
are wider than Retention (11). The ring lets a reader compare
budget-share (arc angle) against labor-intensity (ring width) within each
division at a glance.

A tooltip appears near the cursor on mouseenter showing: team name,
headcount (e.g. "14 people"), and budget (e.g. "$2,100k"). The hovered
arc and its depth-1 and depth-2 ancestors gain an `active` CSS class;
all other arcs dim (lower opacity). Mouseleave restores full opacity and
removes `active`.

Depth-1 labels are always shown. Depth-2 labels appear when the arc's
midpoint angle span is wide enough to fit. Depth-3 labels are optional.
