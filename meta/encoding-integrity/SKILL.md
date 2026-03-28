---
name: encoding-integrity
description: "Audit D3.js visualizations for honest and robust data encoding. Use this skill as an adversarial auditor that checks both static honesty (zero baselines, lie factor, area encoding, dual-axis risk, binning bias) and metamorphic robustness (do visual properties scale correctly when data changes? do data joins preserve identity?). Combines the deception detector and metamorphic tester into a single encoding integrity evaluation."
---

# Encoding Integrity: Honest and Robust Data Encoding

A visualization has encoding integrity when it faithfully represents data now AND would continue to do so with different data. This skill audits both dimensions in a single pass.

## Part 1: Static Honesty

Check the current encoding for mathematical deception.

### Zero Baseline (Bars & Areas)

A bar chart starting at 50 instead of 0 makes a 5% difference look 500%. Bar and area charts encode data as length/area from a baseline — that baseline must be zero.

**Check:** If bar or area chart, does the Y-scale domain start at 0?
**Exception:** Line charts and dot plots focused on variance don't need zero baselines.

### Lie Factor (Visual vs Data Ratio)

Tufte: `Lie Factor = Size of effect shown in graphic / Size of effect in data`.

Doubling a data value by doubling the *radius* of a circle quadruples the area — a lie factor of 2.

**Check:** If size encodes data, is `d3.scaleSqrt` (area-correct) used instead of `d3.scaleLinear` (radius-based)?
**Rule:** Radius-based scaling for data is a major encoding violation.

### Quantile Trap (Choropleths)

`d3.scaleQuantile` forces any distribution into equal-count bins, hiding skew and outliers.

**Check:** Are color bin boundaries mathematically honest for the data distribution?
**Rule:** For skewed data, flag `scaleQuantile` if it hides extreme outliers. Suggest `scaleThreshold` or `scaleLog`.

### Dual-Axis Correlation Risk

Two Y-scales can force unrelated lines to align, implying false correlation.

**Check:** Does the chart use dual-Y axes to compare different units?
**Rule:** Flag as a risk. If the block is *demonstrating* dual-axis technique, score on execution (clear labels, distinct channels, no implied false correlation). Suggest index charts or small multiples as alternatives.

### Smoothing Deception (KDE)

High bandwidth in a KDE can smooth bimodal distributions into unimodal ones.

**Check:** Does the KDE bandwidth hide important features (bimodality, gaps)?
**Rule:** Flag smoothing that hides structure. Suggest histogram alongside KDE.

### Silent Gaps

Missing data drawn as a straight line implies continuity that doesn't exist.

**Check:** Does `line.defined()` handle missing values?

### Honesty Checklist

| Pattern | Trigger | Fix |
|:---|:---|:---|
| Truncated baseline | Bar/area starts non-zero | `yScale.domain([0, ...])` |
| Radius deception | `scaleLinear` for circle size | `scaleSqrt` |
| Dual-axis fabrication | Two Y-scales, one chart | Index chart or small multiples |
| Binning bias | Arbitrary histogram bins | Sturges' or Scott's rule |
| Hidden outliers | `scaleQuantile` on skewed data | `scaleLog` or `scaleThreshold` |
| Silent gap | Missing data = straight line | `line.defined()` |

## Part 2: Metamorphic Robustness

Test whether visual properties hold correct relationships when data changes. If a relation is violated, there's a bug in scales, generators, or data joins.

### Scaling Relation

**Transform:** Multiply all values by constant $k$.
**Invariant:** Visual dimensions must scale by $k$ (linear) or follow the scale's transform (log, power).

- `Output(k * Data) == k * Output(Data)`
- **Catches:** Hardcoded domains, fixed max values, magic numbers in drawing logic.
- **Severity for synthetic data:** Code quality issue, not correctness bug. Flag as "won't adapt to different data."

### Permutation Relation

**Transform:** Shuffle the data array.
**Invariant:** The set of visual elements must remain identical in properties (even if DOM order changes).

- `Set(Output(Shuffle(Data))) == Set(Output(Data))`
- **Catches:** Missing key functions in `.data(data, d => d.id)` causing visual corruption after sort.

### Subset Relation

**Transform:** Remove one data point.
**Invariant:** Remaining elements stay visually identical to their source state.

- **Catches:** Scales that recalculate domains from current subset, causing jumping axes.

### Shift Relation

**Transform:** Add constant to all values.
**Invariant:** Relative visual differences stay identical.

- **Catches:** Accidental dependencies on absolute values instead of relative differences.

### Data Join Evaluation

Key functions (`d => d.id`) tell D3 which datum maps to which element. Evaluate whether they're needed:

**Necessary when:**
- Chart transitions between data states (sort, filter, add/remove)
- Force layouts or hierarchies add/remove nodes
- `attrTween` reads stashed state from `this`

**Unnecessary (don't flag) when:**
- Render-once, never updates — index join is equivalent
- Inner/nested joins where position is identity
- Canvas rendering — no DOM to join
- No natural unique identifier — fabricated composite keys are fragile

**Harmful when:**
- Keys aren't unique — causes destroy/recreate on every update
- Key function returns non-string — `"[object Object]"` for every datum

Only flag missing keys as a permutation violation when the block has update/transition patterns where element identity matters.

## Scoring Guide

Score 1-10 on combined encoding integrity:

| Score | Meaning |
|:-----:|:--------|
| 1-3 | Active deception (lie factor > 2, fabricated correlation) or fundamental encoding breakdown |
| 4-5 | Multiple honesty violations or severe robustness failures (all domains hardcoded + no keys where needed) |
| 6-7 | Structurally honest but brittle — hardcoded domains, minor baseline issues. Typical for synthetic-data demos |
| 8-9 | Honest encoding with data-driven domains, correct area scaling, proper joins where needed |
| 10 | Publication-grade — handles edge cases, documents encoding choices, correct under all transformations |

### Synthetic Data Caveat

Most generated blocks use synthetic data tailored to the chart. With synthetic data:
- Score based on structural correctness (scale choices, baseline rules, encoding math, domain derivation)
- Hardcoded domains that match synthetic data are acceptable at 6-7 (not lower)
- Reserve highest confidence for blocks with real datasets where deception is actually possible

## Invariants Checklist

| Check | Pass Signal |
|:---|:---|
| Zero baseline | Bars/areas start at 0 |
| Area encoding | `scaleSqrt` for size, not `scaleLinear` |
| Scale domain | `d3.max(data)` or `d3.extent` used, not magic numbers |
| Key functions | `.data(data, d => d.id)` present where updates happen |
| Gap handling | `line.defined()` for missing values |
| Binning | Data-driven bin thresholds |
| Dual-axis | Labeled, distinct channels, or avoided |

## References

- Tufte, Edward. *The Visual Display of Quantitative Information* (Lie Factor)
- Cairo, Alberto. *How Charts Lie* (Deception taxonomy)
- Segura, Sergio et al. "Metamorphic Testing: A Review of Challenges and Opportunities" (MT framework)
- Bostock, Mike. "Object Constancy" (Key functions and identity)
