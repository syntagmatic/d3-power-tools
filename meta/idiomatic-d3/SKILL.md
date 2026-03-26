---
name: idiomatic-d3
description: "D3.js idiomatic style patterns and code review guidance. Use this skill when reviewing D3 code for style, refactoring D3 code toward community conventions, or writing new D3 code that follows Bostock's established patterns. Covers method chaining indentation (2-space for new selection, 4-space for same selection), the margin convention, selection.call() for reuse, modern .join() data joins with key functions, the reusable chart closure pattern, scales-as-functions composition, accessor conventions, event handling (this vs arrow functions), generator patterns (axes, brushes, zoom), naming conventions (d, i, x, y, color, svg, g), and anti-patterns to flag (jQuery-style DOM manipulation, missing key functions, d3.select(this) in arrow functions, manual for-loops, over-abstraction). Also use when the user asks about D3 best practices, D3 code style, D3 conventions, or wants to make D3 code more idiomatic. Related skills: `scales` (axis generators via .call()), `motion` (.join() with enter/update/exit), `data-gathering` (accessor patterns), `cross-skill-composition` (structural patterns for larger apps)."
---

# Idiomatic D3

D3 code that follows the library's conventions is code that other D3 developers can read, debug, and extend. Break these conventions and you lose the visual structure that makes chains parseable, the data binding that makes updates correct, and the composition patterns that keep charts maintainable. Every rule here explains what goes wrong when you ignore it — and when ignoring it is the right call.

Related skills: `motion` (`.join()` with enter/update/exit callbacks), `data-gathering` (accessor patterns), `cross-skill-composition` (structural patterns for multi-layer apps).

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

**What breaks without it:** flat indentation hides which `.attr()` calls apply to which element. In a chain that appends a `<g>`, calls an axis, then styles tick labels, flat indent makes it look like everything targets the same node. A reviewer can't spot misplaced attributes without tracing every method's return type.

**The quick rule:** `.append()`, `.select()`, `.selectAll()`, `.data()`, `.join()`, `.enter()`, `.filter()`, `.merge()`, and `.transition()` return a new selection — indent 2. Everything else (`.attr()`, `.style()`, `.on()`, `.call()`, `.each()`, `.text()`, `.classed()`) returns the same selection — indent 4.

When a chain mixes both, the indentation staircase reveals exactly which `.attr()` calls apply to which element:

```js
svg.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
  .call(d3.axisBottom(x))
  .selectAll("text")
    .attr("font-size", 12);
```

**When to break it:** in very short chains (2-3 methods), flat indent is fine — `d3.select("#tip").style("opacity", 1)`. The convention pays off when chains exceed 4-5 lines or mix selection contexts. Also break it when your team uses a formatter (Prettier) that enforces a different style — consistency within a project beats adherence to D3 convention.

## Margin Convention

```js
const width = 928, height = 500;
const margin = {top: 20, right: 30, bottom: 30, left: 40};

const svg = d3.create("svg")
    .attr("viewBox", [0, 0, width, height]);

const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);
```

`width` and `height` are outer SVG dimensions. Inner drawing area: `width - margin.left - margin.right` by `height - margin.top - margin.bottom`. Scales use inner dimensions for range; axes render at margin edges.

**What breaks without it:** ad-hoc padding numbers (`x + 40`, `height - 25`) scatter throughout the code. When axis labels change size or you add a title, you hunt for every magic number. The margin object centralizes that and makes the relationship between outer size and drawing area explicit.

**When to break it:** `viewBox` with percentage-based container sizing handles most responsive needs. But when a Canvas overlay must align pixel-for-pixel with SVG axes, use explicit `width`/`height` attributes on the SVG instead of `viewBox` — the browser's `viewBox` scaling can introduce sub-pixel misalignment.

## Data Joins & Key Functions

Always provide a key function when data can reorder, filter, or update:

```js
svg.selectAll("circle")
  .data(data, d => d.id)    // key function → identity by id, not index
  .join("circle")
    .attr("cx", d => x(d.date))
    .attr("cy", d => y(d.value));
```

**What breaks without a key:** D3 joins by index. Sort the data and every element silently represents a different datum — the third bar now shows the fifth row's value, but nothing visually signals the swap. Transitions are worse: bars morph into unrelated values, and the viewer infers a relationship that doesn't exist. This is visual corruption that's invisible in code review and nearly impossible to catch without animation testing.

**When to skip the key:** static charts that render once and never update. If you call `.data().join()` exactly once and never re-render, index-based join is harmless and avoids the need for a unique identifier in your data.

### .join() — simple and full form

Simple form handles enter, updates in place, removes exit:

```js
g.selectAll("rect")
  .data(data, d => d.id)
  .join("rect")
    .attr("x", d => x(d.name))
    .attr("y", d => y(d.value))
    .attr("height", d => y(0) - y(d.value))
    .attr("width", x.bandwidth());
```

Full form for animated transitions:

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

**When to use the old `.enter().append()...merge()` pattern:** almost never. `.join()` is shorter and handles all three phases. The only case is legacy codebases where `.merge()` is already established and consistency matters more than modernization.

## selection.call() for Composition

`.call(fn)` invokes `fn(selection, ...args)` and returns the original selection. This is D3's primary composition mechanism — axes, brushes, zoom, and drag all work through it.

```js
// Extract repeated axis customization into a reusable function
function grid(g, scale, innerHeight) {
  g.call(d3.axisBottom(scale))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").clone()
        .attr("y2", -innerHeight)
        .attr("stroke-opacity", 0.1));
}

svg.append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(g => grid(g, x, height - margin.top - margin.bottom));
```

**What breaks without it:** copy-pasted `.attr()` blocks for the same axis styling across multiple charts. When the styling changes, you update one and miss the others. `.call()` makes the configuration a named, testable function.

**Key subtlety:** `.call()` returns the **original selection**, not the function's return value. You can chain after it — `.call(d3.axisLeft(y)).attr("font-family", "sans-serif")` applies the font to the axis `<g>`, not to something the axis function returned.

**When to skip it:** single-use configuration that won't be repeated. Wrapping three `.attr()` calls in a named function for a one-off chart adds indirection without reuse benefit.

## Scales as Functions

Scales are callable mappings, not configuration objects. The pattern `d => scale(d.field)` composes an accessor with a scale and appears everywhere in D3:

```js
const x = d3.scaleUtc(d3.extent(data, d => d.date), [margin.left, width - margin.right]);

.attr("cx", d => x(d.date))
.attr("cy", d => y(d.value))
.attr("fill", d => color(d.category))
```

**What breaks when you inline arithmetic instead:** `.attr("cx", d => d.date * pixelsPerDay + margin.left)` embeds the domain-to-range mapping at every call site. Change the scale (log, time, band) and you rewrite every attribute. With a scale function, you change one line.

Prefer accessor arguments over `.map()` in D3 utilities — `d3.max(data, d => d.value)` avoids creating an intermediate array that `d3.max(data.map(d => d.value))` would allocate.

## The Reusable Chart Pattern

Bostock's closure-with-getter-setters — use for shared components or charts instantiated multiple times:

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

**What breaks when you over-apply it:** the closure pattern hides state, makes debugging harder (you can't inspect `width` from the console), and the getter-setter boilerplate doubles the code size. For a chart used exactly once, it's pure overhead. Worse, it creates a false sense of reusability — the chart's internal layout assumptions often break when you change the data shape.

**When to use it:** components rendered in multiple places with different data or dimensions (small multiples, dashboard widgets). When to skip: one-off charts, prototypes, exploratory notebooks. Inline code with clear variable names is perfectly idiomatic for single-use visualizations.

## Naming Conventions

D3 has strong naming conventions. Breaking them doesn't cause bugs, but it causes confusion — a reviewer who sees `colorScale` instead of `color` wastes time checking whether it's something custom.

| Variable | Convention | Why this name |
|----------|-----------|---------------|
| `d`, `i` | Datum, index | Universal in D3 callbacks — `(d, i, nodes)` |
| `x`, `y` | Positional scales | Short because they appear in every `.attr()` call |
| `color` | Color scale | Not `colorScale` — scales are functions, the name says what it maps *to* |
| `svg`, `g` | Root SVG, inner group | `g` is the margin-translated drawing area |
| `t` | Transition | `const t = svg.transition().duration(750)` |
| `line`, `area`, `arc` | Shape generators | Named by output shape, not by input data |
| `path` | Geo path generator | `const path = d3.geoPath(projection)` |

**When to break it:** when a chart has multiple scales on the same axis (e.g., dual-y), `y1` and `y2` are clearer than trying to make both `y`. Similarly, `xBand` vs `xLinear` when you have overlapping scale types for the same dimension.

## Event Handling

### The this Binding

```js
// Regular function — this = current DOM element
.on("mouseover", function(event, d) {
  d3.select(this).attr("fill", "orange");
})

// Arrow function — this is lexical, use event.currentTarget
.on("mouseover", (event, d) => {
  d3.select(event.currentTarget).attr("fill", "orange");
})
```

**What breaks:** `d3.select(this)` inside an arrow function selects `window` or `undefined`, not the element. The highlight applies to nothing (silent failure) or throws. This is the single most common D3 bug in code written by developers coming from modern JS where arrow functions are the default.

Both forms are idiomatic. Pick one per project. Arrow functions with `event.currentTarget` are slightly more explicit about what gets selected.

### Namespaced Events

```js
selection
  .on("click.highlight", highlightFn)
  .on("click.tooltip", tooltipFn);
```

**What breaks without namespaces:** `.on("click", tooltipFn)` silently replaces the highlight handler. D3 allows only one handler per event type per element unless you namespace. With zoom + brush + custom click all on the same element, namespaces prevent handlers from clobbering each other.

## Common Pitfalls

1. **Manual for-loops instead of selections.** `data.forEach(d => svg.append("rect")...)` bypasses D3's data join — no exit handling, no transitions, no key-based identity. The chart renders once and can never update. Use `.selectAll().data().join()`. **Exception:** Canvas rendering, where there's no DOM to join against and a loop over data is the correct pattern.

2. **Mixing framework DOM with D3 DOM.** React/Vue manage their own DOM tree. If D3 also mutates those elements, they fight — React re-renders and wipes D3's changes, or D3 appends elements React doesn't know about. Let D3 own a `<svg>` ref and nothing above it, or use D3 only for math (scales, generators, layouts) and let the framework render. **Exception:** using D3 for pure computation (scales, shapes, layouts) with framework rendering is clean — the conflict is only in DOM mutation.

3. **Breaking chains to store unused selections.** `const bars = g.selectAll("rect")...` is fine when you need the reference later (for transitions, event handlers). But storing every intermediate selection breaks the visual flow of the chain and obscures which operations depend on each other. Chain when the result is used once; name it when referenced again.

4. **Overusing `.each()` when chained `.attr()` suffices.** `.each(function(d) { d3.select(this).attr("x", ...).attr("y", ...); })` is a verbose rewrite of `.attr("x", ...).attr("y", ...)`. Reserve `.each()` for side effects (updating an external data structure) or when you need to compute multiple local variables per element that share an expensive intermediate value.

5. **Forgetting `.transition()` returns a transition, not a selection.** You can't `.on("click", ...)` on a transition — the handler silently doesn't attach. Attach event handlers before `.transition()`, or store the selection reference separately. This is especially subtle when a chain starts with a selection and then calls `.transition()` partway through — everything after that line is on the transition, not the selection.

6. **Using `.enter().append()...merge()` when `.join()` works.** The old general update pattern is four lines where `.join()` is one. `.join()` handles enter, update, and exit in a single call. Use the old pattern only for compatibility with D3 v4/v5 codebases that predate `.join()`.

## Code Review Checklist

| Check | Idiomatic | Flag | What breaks |
|-------|-----------|------|-------------|
| Indentation | 2-space new, 4-space same | Flat indent | Can't tell which attrs apply to which element |
| Data join | `.join()` + key function | Missing keys | Silent data-element mismatch on update |
| Margins | `{top, right, bottom, left}` | Magic numbers | Layout breaks when axes or labels change |
| Scales | Scale functions in `.attr()` | Inline arithmetic | Can't change scale type without rewriting attrs |
| Axes | `.call(d3.axisBottom(x))` | Manual ticks | Lose automatic tick formatting, transition |
| Reuse | `.call(fn)` for repeated config | Copy-pasted blocks | Styling drifts between copies |
| Events | `event.currentTarget` or `function` | Arrow fn + `this` | Handler targets wrong element or throws |
| Transitions | `.join()` callbacks, shared `t` | Unnamed transitions | Transitions on same element cancel each other |
| DOM | D3 selections throughout | `getElementById`, jQuery | Bypasses data binding, breaks update pattern |

## References

- [Towards Reusable Charts](https://bost.ocks.org/mike/chart/) — Bostock's closure pattern and its tradeoffs
- [Thinking with Joins](https://bost.ocks.org/mike/join/) — the core data join philosophy
- [Object Constancy](https://bost.ocks.org/mike/constancy/) — key functions and why index-based join breaks
- [selection.join](https://observablehq.com/@d3/selection-join) — the modern data join pattern
- [Observable Plot](https://observablehq.com/plot/) — when D3 is overkill and a higher-level API is the right call
