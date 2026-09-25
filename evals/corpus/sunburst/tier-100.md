---
mode: single-shot
slug: sunburst
tier: tier-100
cl100k-tokens: 93
author: kai
---
Org budget and headcount sunburst. Dataset: 24 flat records — division, department, team, headcount, budget_k. Three-level hierarchy (division → department → team); arc angles partition by budget_k. Outer concentric ring: one arc per leaf, radial width ∝ headcount within division. Hover: tooltip with team, headcount, budget; `active` on arc and ancestors; dim siblings. Label depth-1 and depth-2 arcs when wide enough.
