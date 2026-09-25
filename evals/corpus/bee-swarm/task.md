---
slug: bee-swarm
mode: single-shot
schema: flat-tabular
render-load: medium-svg
interactivity: [hover, filter]
skills: [distributions, encoding]
provenance: v1-fixture
ablate-skill: patterns
---

Salary distribution bee-swarm chart across six job categories. The
dataset (`data/job-salaries.json`) is 300 synthetic employees with
columns `id`, `category` (Engineer, Designer, Manager, Analyst, Sales,
Support), `salary_k` (annual salary in thousands), and `years_exp`
(years of experience 0–25). Each observation is a circle positioned
along a shared numeric axis (salary_k) and placed within its category
band using a beeswarm layout that avoids overlap.

On hover, a tooltip appears near the circle showing the category, salary,
and years of experience. The hovered circle gains a visible highlight
class. Category filter buttons or checkboxes toggle each job category on
and off; toggling removes or restores that category's circles with a
smooth transition.

Render-load is **medium-svg**: 300 circles positioned by a beeswarm
algorithm, each interactive.

## Expected output

Six horizontal category bands stack vertically. A shared numeric
salary_k axis runs horizontally across all bands, labeled with tick
values. Each category band is labeled on the left (Engineer, Designer,
Manager, Analyst, Sales, Support). Within each band, circles are
arranged to avoid overlap while staying as close to their true salary
position as possible — this is the bee-swarm layout.

Managers cluster at higher salaries; Support clusters lower; the other
categories fan out across the middle range. A modest color or size
encoding may distinguish categories or encode years_exp, but is not
required — position along the numeric axis is the primary encoding.

Filter controls (buttons or checkboxes, one per category) sit above or
beside the chart. Toggling a category off removes those circles; toggling
it back on restores them. Transitions are smooth (0.2–0.4 s).

Hovering a circle shows a tooltip with category, salary_k, and years_exp.
The hovered circle gains a class (`active`, `hover`, or `highlight`) that
makes it visually distinct from neighbors.

The expected-output sketch is a *visual contract*, not a pixel target.
The rubric (dossier 04) scores aesthetics; this sketch gives the matrix
author and the harness fingerprint shared vocabulary about what the
chart *looks like*.
