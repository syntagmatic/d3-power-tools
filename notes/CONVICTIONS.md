# Principles

What we believe, and what we'd need to see to believe it more.

---

**Teach judgment, not APIs.**
Models know `d3.scaleLinear`. They don't know when to break the axis.
*Test whether stripping all API docs changes output quality. We think it won't.*

**Compress until it hurts, then stop.**
Four passes cut 40% with no quality loss. The floor exists but we haven't hit it.
*Rank sections by teaching-value-per-token. Cut from the bottom.*

**Interaction is the point.**
A static chart is a statement. A brushable chart is a question.
*Evaluate by viewer task, not code structure. "Can the user find outliers?" not "does it have a brush?"*

**Exploration before explanation.**
You can't explain what you haven't discovered. The viewer is a detective, not a reader — open a thinking space, don't guide to an answer.
*Compare blocks built exploration-first vs explanation-first. The exploration-first ones should surface structure the prompt didn't anticipate.*

**The bitter lesson applies to skills.**
Don't encode what models already know or patch current failure modes. Encode process that shapes reasoning regardless of model capability.
*Strip API patterns and warnings from a skill, keep only process. If quality holds, the patterns were dead weight.*

**Complexity matches the data.**
A bar chart for high-dimensional data is lossy, not clean. The right complexity is whatever makes the data's structure perceptible.
*Run the same prompt with and without a "keep it simple" instruction. The unconstrained version should match the data's dimensionality.*

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
