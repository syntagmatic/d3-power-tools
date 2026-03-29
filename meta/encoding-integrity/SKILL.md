---
name: encoding-integrity
description: "Audit D3.js visualizations for honest and robust data encoding — like a builder's level, checks if the representation is straight. Trigger words: 'level', 'check encoding', 'audit honesty', 'lie factor', 'metamorphic test'. Combines static honesty checks (zero baselines, lie factor, area encoding, dual-axis risk, binning bias) with metamorphic robustness testing (do visual properties scale correctly when data changes?)."
---

# Encoding Integrity

A visualization has encoding integrity when it faithfully represents data now AND would continue to do so with different data. This skill audits both dimensions in a single pass.

## Part 1: Static Honesty

Check the current encoding for mathematical deception.

### Zero Baseline (Bars & Areas)

**Check:** If bar or area chart, does the Y-scale domain start at 0?
**Rule:** Bar/area charts encode data as length from baseline — baseline must be zero. Exception: line charts and dot plots focused on variance.

### Lie Factor

**Check:** If size encodes data, is `d3.scaleSqrt` (area-correct) used instead of `d3.scaleLinear` (radius-based)?
**Rule:** Radius-based scaling for data is a major encoding violation. Doubling radius quadruples area — lie factor of 2.

### Quantile Trap (Choropleths)

**Check:** Are color bin boundaries mathematically honest for the data distribution?
**Rule:** Flag `scaleQuantile` on skewed data if it hides extreme outliers. Suggest `scaleThreshold` or `scaleLog`.

### Dual-Axis Correlation Risk

**Check:** Does the chart use dual-Y axes to compare different units?
**Rule:** Flag as risk. If demonstrating dual-axis technique, score on execution (clear labels, distinct channels). Suggest index charts or small multiples.

### Smoothing Deception (KDE)

**Check:** Does the KDE bandwidth hide important features (bimodality, gaps)?
**Rule:** Flag smoothing that hides structure. Suggest histogram alongside KDE.

### Silent Gaps

**Check:** Does `line.defined()` handle missing values? Missing data drawn as a straight line implies false continuity.

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

Test whether visual properties hold correct relationships when data changes. Violated relation = bug in scales, generators, or data joins.

### Scaling Relation

**Transform:** Multiply all values by constant $k$.
**Invariant:** Visual dimensions scale by $k$ (linear) or follow the scale's transform.
**Catches:** Hardcoded domains, fixed max values, magic numbers. With synthetic data: code quality issue, not correctness bug.

### Permutation Relation

**Transform:** Shuffle the data array.
**Invariant:** Set of visual element properties remains identical (DOM order may change).
**Catches:** Missing key functions in `.data(data, d => d.id)` causing visual corruption after sort.

### Subset Relation

**Transform:** Remove one data point.
**Invariant:** Remaining elements stay visually identical to their source state.
**Catches:** Scales that recalculate domains from current subset, causing jumping axes.

### Shift Relation

**Transform:** Add constant to all values.
**Invariant:** Relative visual differences stay identical.
**Catches:** Accidental dependencies on absolute values instead of relative differences.

## Scoring Guide

Score 1-10 on combined encoding integrity:

| Score | Meaning |
|:-----:|:--------|
| 1-3 | Active deception (lie factor > 2, fabricated correlation) or fundamental encoding breakdown |
| 4-5 | Multiple honesty violations or severe robustness failures |
| 6-7 | Structurally honest but brittle — hardcoded domains, minor baseline issues. Typical for synthetic-data demos |
| 8-9 | Honest encoding with data-driven domains, correct area scaling, proper joins where needed |
| 10 | Publication-grade — handles edge cases, documents encoding choices, correct under all transformations |

### Synthetic Data Caveat

Most generated blocks use synthetic data. Score on structural correctness (scale choices, baseline rules, encoding math, domain derivation). Hardcoded domains matching synthetic data are acceptable at 6-7. Reserve highest confidence for real datasets.

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
