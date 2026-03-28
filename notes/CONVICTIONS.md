# Principles

What we believe, and what we'd need to see to believe it more.

---

**Teach judgment, not APIs.**
Models know `d3.scaleLinear`. They don't know when to break the axis.
*Test whether stripping all API docs changes output quality. We think it won't.*

**Every rule carries its reason.**
"Use sqrt for bubble area" is a rule. "Because the eye reads area, not radius" is why it survives edge cases.
*Test with prompts that should violate the rule. Rationale-bearing skills should bend; bare rules should snap.*

**Warnings outweigh examples.**
"Force layout is wrong for hierarchies" prevents more errors than any positive pattern.
*Remove one pitfall, measure error rate, restore it, measure again.*

**Compress until it hurts, then stop.**
Four passes cut 40% with no quality loss. The floor exists but we haven't hit it.
*Rank sections by teaching-value-per-token. Cut from the bottom.*

**Interaction is the point.**
A static chart is a statement. A brushable chart is a question.
*Evaluate by viewer task, not code structure. "Can the user find outliers?" not "does it have a brush?"*

**Things break at the seams.**
Complex visualizations fail between skills — state sync, resize contracts, event routing — not within them.
*Audit multi-skill blocks. If between-skill failures dominate, grow the composition skill.*

**Floors, not ceilings.**
Strong conventions, light constraints. The best outcome is someone building what the skill's author wouldn't have — and it works.
*Measure output diversity across runs. Flexible skills should produce more valid variety.*

**Judge and maker must not share a room.**
Calibrating an auditor and running it in the same context produces dishonest scores. We learned this the hard way.
*Separate further: different models, symbolic checkers, asymmetric evaluation.*

**Every skill is a bet.**
"If a model reads this, it will make better decisions." Some bets pay. Some don't. Treat skills as experiments.
*Run evals on every skill commit. If scores drop, the commit is a regression.*

**The project reads itself.**
Meta-skills audit skills. Blocks test blocks. When the project can't visualize its own structure, something is wrong with the skills.
*Self-referential blocks may catch more regressions than synthetic prompts. Test this.*
