# Principles

What we believe, and what we'd need to see to believe it more.

---

**The bitter lesson applies to skills.**
Don't encode what models already know or patch current failure modes. Encode process that shapes reasoning regardless of model capability.
*Strip API patterns and warnings from a skill, keep only process. If quality holds, the patterns were dead weight.*

**Exploration before explanation.**
You can't explain what you haven't discovered. The viewer is a detective, not a reader — open a thinking space, don't guide to an answer.
*Compare blocks built exploration-first vs explanation-first. The exploration-first ones should surface structure the prompt didn't anticipate.*

**Complexity matches the data.**
A bar chart for high-dimensional data is lossy, not clean. The right complexity is whatever makes the data's structure perceptible.
*Run the same prompt with and without a "keep it simple" instruction. The unconstrained version should match the data's dimensionality.*

**Floors, not ceilings.**
Strong conventions, light constraints. The best outcome is someone building what the skill's author wouldn't have — and it works.
*Measure output diversity across runs. Flexible skills should produce more valid variety.*

**Judge and maker must not share a room.**
Calibrating an auditor and running it in the same context produces dishonest scores. We learned this the hard way.
*Separate further: different models, symbolic checkers, asymmetric evaluation.*

**Every skill is a bet.**
"If a model reads this, it will make better decisions." Some bets pay. Some don't. Treat skills as experiments.
*Run evals on every skill commit. If scores drop, the commit is a regression.*
