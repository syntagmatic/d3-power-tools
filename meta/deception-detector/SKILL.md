---
name: deception-detector
description: "Audit D3.js visualizations for mathematical deception and 'The Lie Factor'. Use this skill as an adversarial auditor for ethical data visualization. Flags truncated Y-axes, inconsistent binning in histograms, 'The Quantile Trap' in choropleths, dual-axis correlation fabrications, and non-zero baselines in bar charts. Ensures the 'Visual Distortion' of a chart matches its 'Data Distortion'."
---

# Deception Detector: Auditing Ethical Visualization

Data visualization is as much about what you hide as what you show. A "Deceptive Design" in D3 can confidently lie while technically having "no bugs." This skill acts as a moral and mathematical auditor.

## 1. The 'Zero Baseline' Rule (Bars & Areas)
- **The Deception:** A bar chart with a Y-axis that starts at 50 instead of 0, making a 5% difference look like a 500% difference.
- **Data Distortion:** The ratio of visual lengths must match the ratio of data values.
- **Deception-Detector Check:** "If this is a Bar or Area chart, does the Y-scale start at 0?"
- **Rule:** Flag any non-zero-baselined bar/area chart. (Exceptions: Dot plots or Line charts focused on small variances).

## 2. The 'Lie Factor' (Visual vs. Data)
Inspired by Tufte: `Lie Factor = Size of effect shown in graphic / Size of effect in data`.
- **The Deception:** Doubling a data value by doubling the *radius* of a circle (which quadruples the area).
- **Deception-Detector Check:** "If size is encoding data, are you using `d3.scaleSqrt` (area-based) or `d3.scaleLinear` (radius-based)?"
- **Rule:** Radius-based scaling for data is a "Major Deception." Force the use of `scaleSqrt`.

## 3. The 'Quantile Trap' (Choropleths)
- **The Deception:** Using `d3.scaleQuantile` to make a skewed dataset look like a uniform distribution, hiding the true outliers.
- **Deception-Detector Check:** "Are the color bin boundaries mathematically honest for the data distribution?"
- **Rule:** For skewed data (e.g., income), flag `scaleQuantile` if it hides extreme outliers. Suggest `scaleThreshold` or `scaleLog`.

## 4. Fabricated Correlation (Dual-Y Axis)
- **The Deception:** Using two different Y-scales to "force" two lines to line up, implying a correlation that doesn't exist.
- **Deception-Detector Check:** "Does this chart use a dual-Y axis to compare two different units?"
- **Rule:** Flag dual-axis as a deception risk and suggest alternatives (**Index Charts** or **Small Multiples**). But if the block is *demonstrating* dual-axis technique, score based on execution quality — does it label both axes clearly, use distinct visual channels, avoid implying false correlation? A well-executed dual-axis demo is not deceptive; a sloppy one is.

## 5. The 'Smoothing' Deception (KDE & Histograms)
- **The Deception:** Using a high bandwidth in a KDE (Density Plot) that "smooths over" a bimodal distribution, making it look unimodal.
- **Deception-Detector Check:** "Does the KDE bandwidth hide important bimodal features in the data?"
- **Rule:** If the data is bimodal (peaks at two values), flag any smoothing that hides it. Suggest a histogram alongside the KDE.

## Deception-Detector Checklist

| Deceptive Pattern | Red-Team Trigger | Adversarial Fix |
| :--- | :--- | :--- |
| **Truncated Baseline** | Bar chart starts at non-zero | `yScale.domain([0, ...])` |
| **Radius Deception** | `d3.scaleLinear()` for circle radius | Switch to `d3.scaleSqrt()` |
| **Dual-Y Fabrication** | Two Y-scales on one chart | Index Chart or Small Multiples |
| **Binning Bias** | Arbitrary histogram bins | Use Sturges' or Scott's rule |
| **Hidden Outliers** | `d3.scaleQuantile` on skewed data | Use `d3.scaleLog` or `d3.scaleThreshold` |
| **Silent Gap** | Missing data drawn as a straight line | Use `line.defined()` to show gaps |

## Synthetic Data Caveat

Most generated blocks use synthetic data tailored to the chart. With synthetic data, there's no real opportunity for deception — the data was made to fit. A high deception score on synthetic data means the code *structures* are honest (zero baselines, sqrt scaling, proper binning), but says nothing about whether the chart would deceive with real data.

When evaluating blocks with synthetic data:
- Score based on structural correctness (scale choices, baseline rules, encoding math)
- Note that the data is synthetic — don't treat a 9/10 as proof the chart is trustworthy
- Reserve the highest confidence for blocks using real datasets where deception is actually possible

## Example Critique

**Generated Code:**
```js
const y = d3.scaleLinear()
  .domain([50, 100]) // Focus on the interesting range
  .range([height, 0]);

svg.selectAll("rect")
  .attr("height", d => height - y(d.value));
```

**Deception-Detector Critique:**
> **Violation of Zero-Baseline Rule (High Lie Factor):** This bar chart starts the Y-axis at 50. In a bar chart, the *length* of the bar encodes the value. By starting at 50, a value of 60 is visually twice as tall as 55, while only being ~9% larger in data. This is a severe visual distortion.
> **Fix:** Set the Y-scale domain to start at 0: `d3.scaleLinear().domain([0, d3.max(data, d => d.value)])`.
