---
name: metamorphic-tester
description: "Apply Metamorphic Testing (MT) to validate D3.js visualizations without a fixed 'oracle'. Use this skill when you need to verify if a chart's visual properties (height, position, color) correctly reflect data changes, test scale robustness, or identify 'silent' visual bugs that standard tests miss. Defines Metamorphic Relations (MRs) like Permutation, Scaling, Subset, and Shifting to ensure visual consistency across data transformations."
---

# Metamorphic Testing for D3

Metamorphic Testing (MT) is a technique for validating visualizations where the "correct" output is hard to define in absolute pixels, but the **relationship** between inputs and outputs must follow strict logic.

Use this skill to create "Adversarial Evaluators" that break charts by transforming data and checking for visual invariants.

## The Core Concept: Metamorphic Relations (MRs)

An MR defines how the output should change (or stay the same) when the input is transformed. If the relation is violated, you've found a bug in the scales, generators, or data join.

### 1. The Scaling Relation (Scale Robustness)
**Transformation:** Multiply all data values by a constant $k$.
**Invariant:** Visual dimensions (bar height, circle radius, Y-position) must scale by $k$ (for linear scales) or follow the scale's mathematical transform (log, power).

*   **Logic:** `Output(k * Data) == k * Output(Data)`
*   **Common Bug caught:** Hardcoded margins, fixed "max" values in scales, or magic numbers in the drawing loop.
*   **Severity:** This is a code quality issue, not a correctness bug in blocks with synthetic data. Flag hardcoded domains as "won't adapt to different data" — the code works but teaches a brittle pattern.

### 2. The Permutation Relation (Identity Robustness)
**Transformation:** Shuffle the order of the data array.
**Invariant:** The set of visual elements (rects, circles) must remain identical in properties, even if their DOM order or X-position changes.

*   **Logic:** `Set(Output(Shuffle(Data))) == Set(Output(Data))`
*   **Common Bug caught:** Missing key functions in `.data(data, d => d.id)`, causing "visual corruption" where elements represent the wrong data after a sort.

### 3. The Subset Relation (Isolation Robustness)
**Transformation:** Remove one data point from the input.
**Invariant:** The remaining elements must stay visually identical to their "Source" state.

*   **Logic:** `Output(Data - {x})` should be visually identical to `Output(Data)` minus element `x`.
*   **Common Bug caught:** Scales that recalculate domains based on the *current* visible subset without considering the global domain, causing "jumping" axes.

### 4. The Invariance Relation (Metadata Robustness)
**Transformation:** Change a non-visual property (e.g., a "description" field not used in the chart).
**Invariant:** The visualization must be byte-for-byte or pixel-for-pixel identical.

*   **Logic:** `Output(Data{meta: A}) == Output(Data{meta: B})`
*   **Common Bug caught:** Accidental dependencies on data indices or hash-keys that change when metadata is modified.

## Implementation Guide for Evaluators

When evaluating a D3 skill, perform these checks mentally or via a test script:

### Step 1: Identify the Visual Encodings
List what data fields map to what visual attributes:
- `d.value` -> `rect.height`
- `d.date` -> `circle.cx`
- `d.category` -> `path.fill`

### Step 2: Apply a Transformation
"If I were to double `d.value` for all points..."
- Does the code use `d3.max(data, d => d.value)` for the scale domain? (Pass)
- Does it use `.domain([0, 100])`? (Fail - will clip or overflow if doubled)

### Step 3: Check the Data Join
Key functions (`d => d.id`) tell D3 which datum maps to which DOM element. Without them, D3 joins by index — which is correct in some cases and silently wrong in others.

**Key functions are necessary when:**
- The chart transitions between data states (sort, filter, add/remove) — without keys, bars morph into unrelated values (Bostock's "Object Constancy" problem)
- Force layouts or hierarchies add/remove nodes — without keys, existing nodes lose their simulation positions and jump
- `attrTween` reads stashed state from `this` — key mismatch means the interpolator gets `undefined` and snaps instead of animating

**Key functions are unnecessary (don't flag) when:**
- The chart renders once and never updates — index join is identical to keyed join
- Inner/nested joins where position is the identity (e.g., cells in a table row)
- Canvas rendering — no DOM to join against
- Data has no natural unique identifier — fabricated composite keys (`d => d.name + d.date`) are fragile and worse than index

**Key functions are harmful when:**
- Keys are not unique — duplicates cause elements to be destroyed and recreated on every update
- The key function doesn't return a string — returning objects produces `"[object Object]"` for every datum

Only flag missing key functions as a permutation relation violation when the block has update or transition patterns where element identity matters.

## Example Adversarial Critique

**Generated Code:**
```js
const y = d3.scaleLinear()
  .domain([0, 100])
  .range([height, 0]);
```

**Metamorphic Critique:**
> **Violation of Scaling Relation:** The Y-scale domain is hardcoded to `[0, 100]`. If the input data is scaled (e.g., values up to 200), the visualization will fail to represent the data correctly (clipping). 
> **Fix:** Use `d3.extent` or `d3.max` to derive the domain from the data.

## Visual Invariants Checklist

| Relation | Check | Pass Signal |
| :--- | :--- | :--- |
| **Scaling** | Scale Domain | `d3.max(data)` used instead of magic numbers |
| **Permutation** | Key Functions | `.data(data, d => d.id)` present |
| **Subset** | Axis Stability | Margins and domain handling are consistent |
| **Shifting** | Margin Convention | `transform(translate(margin.left...))` used |
