---
name: idiomatic-d3
description: "D3.js idiomatic style patterns and code review guidance. Use this skill when reviewing D3 code for style, refactoring D3 code toward community conventions, or writing new D3 code that follows Bostock's established patterns. Covers method chaining indentation (2-space for new selection, 4-space for same selection), the margin convention, selection.call() for reuse, modern .join() data joins with key functions, the reusable chart closure pattern, scales-as-functions composition, accessor conventions, event handling (this vs arrow functions), generator patterns (axes, brushes, zoom), naming conventions (d, i, x, y, color, svg, g), import strategies, and anti-patterns to flag (jQuery-style DOM manipulation, missing key functions, d3.select(this) in arrow functions, manual for-loops, over-abstraction). Also use when the user asks about D3 best practices, D3 code style, D3 conventions, or wants to make D3 code more idiomatic. Related skills: `scales` (axis generators via .call()), `motion` (.join() with enter/update/exit), `data-gathering` (accessor patterns), `cross-skill-composition` (structural patterns for larger apps)."
---

# Idiomatic D3

D3 has strong conventions that emerged from Mike Bostock's Observable notebooks and the library's functional design. Idiomatic D3 code is recognizable by its chaining style, data-driven joins, and use of D3's own abstractions over manual DOM work. This skill codifies those conventions for code review and authoring.

Related skills: `scales` (axis generators via `.call()`), `motion` (`.join()` with enter/update/exit callbacks), `data-gathering` (accessor patterns for loading/cleaning), `cross-skill-composition` (structural patterns for multi-layer apps).

## Method Chaining & Indentation

The single most distinctive D3 convention. Methods that return the **same selection** get 4-space indent; methods that return a **new selection** get 2-space indent. This makes context switches visible:

```js
const svg = d3.select("#chart")
  .append("svg")                                    // new selection → 2-space
    .attr("viewBox", [0, 0, width, height]);        // same selection → 4-space

const g = svg.append("g")                           // new selection → 2-space
    .attr("transform", `translate(${margin.left},${margin.top})`);

g.selectAll("rect")                                 // new selection → 2-space
  .data(data, d => d.id)                            // new (update) → 2-space
  .join("rect")                                     // new (enter+update) → 2-space
    .attr("x", d => x(d.name))                      // same selection → 4-space
    .attr("y", d => y(d.value))
    .attr("height", d => y(0) - y(d.value))
    .attr("width", x.bandwidth())
    .attr("fill", "steelblue");
```

### Which Methods Return What

| Returns **new** selection | Returns **same** selection |
|--------------------------|---------------------------|
| `.append()`, `.insert()` | `.attr()`, `.style()`, `.classed()` |
| `.select()` | `.text()`, `.html()`, `.property()` |
| `.selectAll()` | `.on()`, `.each()`, `.call()` |
| `.data()` | `.datum()`, `.sort()`, `.order()` |
| `.join()`, `.enter()` | `.raise()`, `.lower()` |
| `.filter()`, `.merge()` | `.interrupt()` |
| `.transition()` | `.delay()`, `.duration()`, `.ease()` |

When a chain mixes both, the indentation staircase reveals exactly which `.attr()` calls apply to which element:

```js
svg.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
  .call(d3.axisBottom(x))
  .selectAll("text")
    .attr("font-size", 12);
```

## Margin Convention

The standard layout pattern — shields all drawing code from edge math:

```js
const width = 928;
const height = 500;
const margin = {top: 20, right: 30, bottom: 30, left: 40};

const svg = d3.create("svg")
    .attr("viewBox", [0, 0, width, height]);

const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);
```

Inner drawing area: `width - margin.left - margin.right` by `height - margin.top - margin.bottom`. Scales use the inner dimensions for their range; axes render at the margin edges. `width` and `height` are outer (total SVG) dimensions.

### viewBox vs Fixed Dimensions

Prefer `viewBox` for responsive charts — the SVG scales to its container. Use explicit `width`/`height` attributes only when you need pixel-precise control (Canvas overlay alignment, fixed-size exports).

## Data Joins

### Key Functions for Object Constancy

Always provide a key function when data can reorder, filter, or update:

```js
svg.selectAll("circle")
  .data(data, d => d.id)    // key function → identity by id, not index
  .join("circle")
    .attr("cx", d => x(d.date))
    .attr("cy", d => y(d.value));
```

Without a key, D3 joins by index — sorting or filtering data causes elements to silently represent the wrong datum. Transitions become meaningless because elements morph into unrelated values instead of tracking their data.

### Modern .join()

Simple form — handles enter, updates in place, removes exit:

```js
g.selectAll("rect")
  .data(data, d => d.id)
  .join("rect")
    .attr("x", d => x(d.name))
    .attr("y", d => y(d.value))
    .attr("height", d => y(0) - y(d.value))
    .attr("width", x.bandwidth());
```

Full form — customize enter/update/exit for transitions:

```js
g.selectAll("rect")
  .data(data, d => d.id)
  .join(
    enter => enter.append("rect")
        .attr("x", d => x(d.name))
        .attr("y", y(0))
        .attr("height", 0)
        .attr("width", x.bandwidth())
      .call(enter => enter.transition(t)
        .attr("y", d => y(d.value))
        .attr("height", d => y(0) - y(d.value))),
    update => update
      .call(update => update.transition(t)
        .attr("x", d => x(d.name))
        .attr("y", d => y(d.value))
        .attr("height", d => y(0) - y(d.value))),
    exit => exit
      .call(exit => exit.transition(t)
        .attr("height", 0).attr("y", y(0)).remove())
  );
```

The old `.enter().append()...merge()...exit().remove()` pattern is equivalent but more verbose. Use `.join()` unless you have a specific reason not to.

## selection.call() for Reuse

`.call(fn)` invokes `fn(selection, ...args)` and returns the selection — the chain continues. This is D3's primary composition mechanism. Axes, brushes, zoom, and drag all work this way.

### Extracting Custom Components

When you repeat the same configuration:

```js
// Before — duplicated
svg.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
  .call(d3.axisBottom(x))
  .call(g => g.select(".domain").remove())
  .call(g => g.selectAll(".tick line").clone()
      .attr("y2", -(height - margin.top - margin.bottom))
      .attr("stroke-opacity", 0.1));

// After — extracted
function grid(g, scale, height) {
  g.call(d3.axisBottom(scale))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").clone()
        .attr("y2", -height)
        .attr("stroke-opacity", 0.1));
}

svg.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(g => grid(g, x, height - margin.top - margin.bottom));
```

### Chaining Through .call()

`.call()` returns the **original selection**, not the function's return value. You can chain after it:

```js
svg.append("g")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y))
    .call(g => g.select(".domain").remove())
    .attr("font-family", "sans-serif");   // still applies to the g
```

## Scales as Functions

Scales are functions. This is the key insight — they're not configuration objects, they're callable mappings from data domain to visual range:

```js
const x = d3.scaleLinear([0, 100], [margin.left, width - margin.right]);
x(50);  // → midpoint pixel value
```

### Constructor Shorthand

D3 v7 accepts `(domain, range)` directly — no chained `.domain().range()`:

```js
// Preferred
const x = d3.scaleUtc(d3.extent(data, d => d.date), [margin.left, width - margin.right]);

// Also fine — needed when building incrementally
const x = d3.scaleUtc().domain(d3.extent(data, d => d.date)).range([margin.left, width - margin.right]);
```

### Accessor Composition

The pattern `d => scale(d.field)` composes an accessor with a scale. It appears everywhere:

```js
.attr("cx", d => x(d.date))
.attr("cy", d => y(d.value))
.attr("fill", d => color(d.category))
```

### Accessors in D3 Utilities

Prefer the accessor argument over `.map()`:

```js
// Idiomatic
d3.max(data, d => d.value)
d3.extent(data, d => d.date)
d3.sum(data, d => d.revenue)
d3.group(data, d => d.category)

// Avoid — creates an intermediate array
d3.max(data.map(d => d.value))
```

## The Reusable Chart Pattern

Bostock's closure-with-getter-setters — use for shared components or charts instantiated multiple times. Skip for one-off visualizations.

```js
function barChart() {
  let width = 640, height = 400;
  let x = d => d.name, y = d => d.value;

  function chart(selection) {
    selection.each(function(data) {
      const xScale = d3.scaleBand(data.map(x), [0, width]).padding(0.1);
      const yScale = d3.scaleLinear([0, d3.max(data, y)], [height, 0]);

      const svg = d3.select(this)
        .selectAll("svg")
        .data([data])
        .join("svg")
          .attr("viewBox", [0, 0, width, height]);

      svg.selectAll("rect")
        .data(d => d, x)
        .join("rect")
          .attr("x", d => xScale(x(d)))
          .attr("y", d => yScale(y(d)))
          .attr("height", d => height - yScale(y(d)))
          .attr("width", xScale.bandwidth());
    });
  }

  chart.width = function(_) { return arguments.length ? (width = _, chart) : width; };
  chart.height = function(_) { return arguments.length ? (height = _, chart) : height; };
  chart.x = function(_) { return arguments.length ? (x = _, chart) : x; };
  chart.y = function(_) { return arguments.length ? (y = _, chart) : y; };

  return chart;
}

// Usage
const myChart = barChart().width(800).x(d => d.label);
d3.select("#viz").datum(data).call(myChart);
```

When to skip: one-off charts, prototypes, Observable notebooks. Inline code with clear variable names is perfectly idiomatic for single-use visualizations. Don't over-abstract.

## Naming Conventions

| Variable | Convention | Notes |
|----------|-----------|-------|
| `d` | Current datum | Callback signature: `(d, i, nodes)` |
| `i` | Index within group | Second callback parameter |
| `x`, `y` | Positional scales | `const x = d3.scaleLinear(...)` |
| `color` | Color scale | Not `colorScale`, `c`, or `fill` |
| `r` | Radius scale | Bubble/circle charts |
| `svg` | Root SVG selection | The outermost SVG element |
| `g` | Inner group | The margin-translated drawing group |
| `data` | The dataset | After loading and preparation |
| `margin` | Margin object | `{top, right, bottom, left}` — CSS property order |
| `width`, `height` | Outer SVG dimensions | Inner = subtract margins |
| `line`, `area`, `arc` | Shape generators | Named by the shape they produce |
| `t` | Transition | `const t = svg.transition().duration(750)` |
| `path` | Path generator | `const path = d3.geoPath(projection)` |

Avoid Hungarian notation (`strName`, `arrData`), `Chart` suffixes on functions, and single-letter variables beyond the conventions above.

## Event Handling

### The this Binding

```js
// Regular function — this = current DOM element
.on("mouseover", function(event, d) {
  d3.select(this).attr("fill", "orange");
})

// Arrow function — this is lexical (probably undefined or window)
// Use event.currentTarget instead
.on("mouseover", (event, d) => {
  d3.select(event.currentTarget).attr("fill", "orange");
})
```

Both forms are idiomatic. Arrow functions are fine as long as you use `event.currentTarget` instead of `this`. Pick one style per project and be consistent.

### Namespaced Events

Prevent handler collision when multiple behaviors listen to the same event:

```js
selection
  .on("click.highlight", highlightFn)
  .on("click.tooltip", tooltipFn);

// Remove only the highlight handler
selection.on("click.highlight", null);
```

### Pointer Coordinates

```js
const [px, py] = d3.pointer(event);           // relative to event.currentTarget
const [px, py] = d3.pointer(event, svg.node()); // relative to specific element
```

## Import Patterns

### Standalone HTML

```html
<script type="module">
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";
// all of d3 in one import — fine for standalone files
</script>
```

### Bundled Applications

```js
import {select, selectAll, scaleLinear, axisBottom, line, csv} from "d3";
```

Named imports from `d3` tree-shake with modern bundlers. Importing from submodules (`d3-selection`, `d3-scale`) is unnecessary — the `d3` package re-exports everything.

### Observable Notebooks

`d3` is a built-in global — no import needed. For specific versions: `d3 = require("d3@7")`.

## Modern JS in D3 Context

**`const` over `let`** — scales, selections, generators, and dimensions are assigned once. Use `let` only for state that truly mutates (e.g., a current filter value).

**`async/await` for data loading:**

```js
const data = await d3.csv("data.csv", d => ({
  date: new Date(d.date),
  value: +d.value
}));
```

**`Promise.all` for multiple files:**

```js
const [cities, borders] = await Promise.all([
  d3.csv("cities.csv", d3.autoType),
  d3.json("borders.geojson")
]);
```

**Template literals** for transforms and paths — never concatenate strings:

```js
.attr("transform", `translate(${margin.left},${margin.top})`)
```

**Nullish coalescing** for defaults: `d.value ?? 0`. Prefer over `|| 0` which also catches `0` and `""`.

## Code Review Checklist

Quick-scan reference for reviewing D3 code:

| Check | Idiomatic | Flag |
|-------|-----------|------|
| Indentation | 2-space new selection, 4-space same | Flat or inconsistent indent |
| Data join | `.join()` with key function | Manual enter/exit/merge, missing keys |
| Margins | `{top, right, bottom, left}` object | Ad-hoc padding, magic pixel numbers |
| Scales | Constructor shorthand, accessors | Inline arithmetic for positioning |
| Axes | `.call(d3.axisBottom(x))` | Manual tick rendering in SVG |
| Reuse | `.call(fn)` for repeated config | Copy-pasted `.attr()` blocks |
| Events | `event.currentTarget` or regular `function` | Arrow fn + `d3.select(this)` |
| Data loading | `async/await`, explicit row accessor | Nested `.then()`, `autoType` in production |
| Transitions | `.join()` callbacks, shared `t` | Unnamed transitions that collide |
| DOM access | D3 selections throughout | `document.getElementById`, jQuery, `innerHTML` |

## Common Pitfalls

1. **`d3.select(this)` inside arrow functions.** Arrow functions don't bind `this` to the DOM element — you get `undefined` or `window`. Use `event.currentTarget` or a regular `function`.

2. **Missing key function on data joins.** Without `.data(data, d => d.id)`, D3 joins by index. Sorting, filtering, or streaming data causes elements to silently represent the wrong datum — visual corruption that's invisible in code review.

3. **Breaking chains to store unused selections.** `const bars = g.selectAll("rect")...` is fine when you need the reference later. But storing every intermediate selection obscures the data flow. Chain when the result is used once.

4. **Manual for-loops instead of selections.** `data.forEach(d => svg.append("rect")...)` bypasses D3's data join — no exit handling, no transitions, no key-based identity. Use `.selectAll().data().join()`.

5. **Mixing framework DOM with D3 DOM.** React/Vue manage their own DOM tree. If D3 also mutates those elements, they fight. Let D3 own a `<svg>` ref and nothing above it, or use D3 only for math (scales, generators, layouts) and let the framework render.

6. **Overusing `.each()` when chained `.attr()` suffices.** `.each(function(d) { d3.select(this).attr("x", ...).attr("y", ...); })` is a verbose rewrite of `.attr("x", ...).attr("y", ...)`. Reserve `.each()` for side effects or when you need multiple local variables per element.

7. **Flat indentation hiding selection context.** When every line is indented the same, you can't tell which `.attr()` calls apply to which element. The 2/4-space convention makes context switches visible — it's the first thing to fix in unclear D3 code.

8. **Over-abstracting one-off charts.** The reusable chart pattern adds real complexity. For a single visualization that nobody will instantiate twice, inline code with clear variable names beats a closure with getter-setters.

9. **Using `.enter().append()...merge()` when `.join()` works.** The old general update pattern is four lines where `.join()` is one. Use `.join()` unless you need behavior that its callbacks can't express (extremely rare in practice).

10. **Forgetting that `.transition()` returns a transition, not a selection.** You can't `.on("click", ...)` on a transition. Attach event handlers before `.transition()`, or store the selection reference separately.

## References

- [D3 Selection API](https://d3js.org/d3-selection) — `.join()`, `.call()`, `.each()`, method chaining
- [Towards Reusable Charts](https://bost.ocks.org/mike/chart/) — Bostock's closure pattern
- [Thinking with Joins](https://bost.ocks.org/mike/join/) — the core data join philosophy
- [Object Constancy](https://bost.ocks.org/mike/constancy/) — key functions and visual continuity
- [Let's Make a Bar Chart](https://observablehq.com/@d3/lets-make-a-bar-chart) — canonical D3 example
- [selection.join](https://observablehq.com/@d3/selection-join) — the modern data join pattern
- [Observable Plot](https://observablehq.com/plot/) — higher-level API when D3 is overkill
