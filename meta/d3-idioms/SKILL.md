---
name: d3-idioms
description: "D3.js code style and convention review. Use when the user says 'check style', 'review code', 'idiomatic D3', 'd3 idioms', or wants D3 code to follow community conventions. Covers chaining indentation, margin convention, .join() data joins, selection.call() composition, reusable chart pattern, naming, event handling. Related: scales, motion, data-gathering, jig-template."
---

# D3 Idioms

D3 code that follows the library's conventions is code others can read, debug, and extend. Break them and you lose the visual structure that makes chains parseable, the data binding that makes updates correct, and the composition patterns that keep charts maintainable. Every rule here explains what goes wrong when you ignore it — and when ignoring it is the right call.

Related skills: `motion` (`.join()` with enter/update/exit callbacks), `data-gathering` (accessor patterns), `jig-template` (structural patterns for multi-layer apps).

## Method Chaining & Indentation

Methods that return the **same selection** get 4-space indent; methods that return a **new selection** get 2-space indent. This makes context switches visible:

```js
const svg = d3.select("#chart")
  .append("svg")                                    // new selection → 2-space
    .attr("viewBox", [0, 0, width, height]);        // same selection → 4-space

g.selectAll("rect")
  .data(data, d => d.id)
  .join("rect")
    .attr("x", d => x(d.name))
    .attr("y", d => y(d.value))
    .attr("height", d => y(0) - y(d.value))
    .attr("width", x.bandwidth())
    .attr("fill", "steelblue");
```

**What breaks without it:** flat indentation hides which `.attr()` calls apply to which element. In a chain that appends a `<g>`, calls an axis, then styles tick labels, flat indent makes it look like everything targets the same node.

**When to break it:** very short chains (2-3 methods) or when a project formatter enforces a different style — consistency within a project beats adherence to D3 convention.

## Margin Convention

```js
const width = 928, height = 500;
const margin = {top: 20, right: 30, bottom: 30, left: 40};
const svg = d3.create("svg").attr("viewBox", [0, 0, width, height]);
const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);
```

`width`/`height` are outer SVG dimensions. Inner drawing area: `width - margin.left - margin.right` by `height - margin.top - margin.bottom`. Scales use inner dimensions for range; axes render at margin edges.

**What breaks without it:** ad-hoc padding numbers (`x + 40`, `height - 25`) scatter throughout the code. When axis labels change size or you add a title, you hunt for every magic number. The margin object centralizes that.

## Data Joins & Key Functions

Always provide a key function when data can reorder, filter, or update:

```js
svg.selectAll("circle")
  .data(data, d => d.id)    // key function → identity by id, not index
  .join("circle")
    .attr("cx", d => x(d.date))
    .attr("cy", d => y(d.value));
```

**What breaks without a key:** D3 joins by index. Sort the data and every element silently represents a different datum. Transitions are worse: bars morph into unrelated values. This is visual corruption invisible in code review. **When to skip:** static charts that render once and never update.

### .join() — simple and full form

Simple form (`.join("rect")`) handles enter, updates in place, removes exit. Use for static or immediately-set attributes.

Full form for animated transitions — pass enter/update/exit callbacks:

```js
.join(
  enter => enter.append("rect")
      .attr("y", y(0)).attr("height", 0)
    .call(e => e.transition(t)
      .attr("y", d => y(d.value))
      .attr("height", d => y(0) - y(d.value))),
  update => update.call(u => u.transition(t)
      .attr("y", d => y(d.value))),
  exit => exit.call(e => e.transition(t)
      .attr("height", 0).attr("y", y(0)).remove())
);
```

The old `.enter().append()...merge()` pattern is almost never needed — `.join()` handles all three phases. Only use for D3 v4/v5 compatibility.

## selection.call() for Composition

`.call(fn)` invokes `fn(selection, ...args)` and returns the **original selection**. D3's primary composition mechanism — axes, brushes, zoom, and drag all work through it.

```js
function grid(g, scale, innerHeight) {
  g.call(d3.axisBottom(scale))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").clone()
        .attr("y2", -innerHeight).attr("stroke-opacity", 0.1));
}
svg.append("g").call(g => grid(g, x, innerHeight));
```

**What breaks without it:** copy-pasted axis styling across charts. When the styling changes, you update one and miss the others. **When to skip:** single-use configuration that won't be repeated.

## Scales as Functions

Scales are callable mappings: `d => scale(d.field)` composes accessor + scale. Inline arithmetic like `.attr("cx", d => d.date * pxPerDay + margin.left)` embeds domain-to-range at every call site — change scale type (log, time, band) and you rewrite every attribute. Prefer accessor arguments too: `d3.max(data, d => d.value)` avoids the intermediate array `.map()` creates.

## The Reusable Chart Pattern

Bostock's closure-with-getter-setters — use for components rendered in multiple places (small multiples, dashboard widgets):

```js
function barChart() {
  let width = 640, height = 400;
  let x = d => d.name, y = d => d.value;

  function chart(selection) {
    selection.each(function(data) {
      const xS = d3.scaleBand(data.map(x), [0, width]).padding(0.1);
      const yS = d3.scaleLinear([0, d3.max(data, y)], [height, 0]);
      d3.select(this).selectAll("svg").data([data]).join("svg")
          .attr("viewBox", [0, 0, width, height])
        .selectAll("rect").data(d => d, x).join("rect")
          .attr("x", d => xS(x(d))).attr("y", d => yS(y(d)))
          .attr("height", d => height - yS(y(d))).attr("width", xS.bandwidth());
    });
  }

  chart.width = function(_) { return arguments.length ? (width = _, chart) : width; };
  chart.height = function(_) { return arguments.length ? (height = _, chart) : height; };
  chart.x = function(_) { return arguments.length ? (x = _, chart) : x; };
  chart.y = function(_) { return arguments.length ? (y = _, chart) : y; };
  return chart;
}
d3.select("#viz").datum(data).call(barChart().width(800));
```

**What breaks when over-applied:** the closure hides state (can't inspect from console), getter-setter boilerplate doubles code size, and internal layout assumptions often break with different data shapes. **When to skip:** one-off charts, prototypes, exploratory notebooks. Inline code with clear variable names is perfectly idiomatic for single-use visualizations.

## Naming Conventions

| Variable | Convention | Why |
|----------|-----------|-----|
| `d`, `i` | Datum, index | Universal in D3 callbacks |
| `x`, `y` | Positional scales | Short because they appear in every `.attr()` call |
| `color` | Color scale | Not `colorScale` — name says what it maps *to* |
| `svg`, `g` | Root SVG, inner group | `g` is the margin-translated drawing area |
| `t` | Transition | `const t = svg.transition().duration(750)` |
| `line`, `area`, `arc` | Shape generators | Named by output shape |
| `path` | Geo path generator | `d3.geoPath(projection)` |

Break convention for multiple scales on the same axis: `y1`/`y2` for dual-y, `xBand`/`xLinear` for overlapping types.

## Event Handling

**The this binding** — the most common D3 bug:

```js
// Regular function — this = DOM element
.on("mouseover", function(event, d) { d3.select(this).attr("fill", "orange"); })
// Arrow function — this is lexical, use event.currentTarget
.on("mouseover", (event, d) => { d3.select(event.currentTarget).attr("fill", "orange"); })
```

`d3.select(this)` inside an arrow function selects `window` or `undefined` — the highlight silently applies to nothing or throws. Both forms are idiomatic; pick one per project.

**Namespaced events:** `.on("click.highlight", fn1).on("click.tooltip", fn2)` — without namespaces, the second handler silently replaces the first. Essential when zoom + brush + custom click share an element.

## Common Pitfalls

1. **Manual for-loops instead of selections.** `data.forEach(d => svg.append("rect")...)` bypasses data join — no exit, no transitions, no key identity. Use `.selectAll().data().join()`. Exception: Canvas rendering where there's no DOM to join against.

2. **Mixing framework DOM with D3 DOM.** React/Vue and D3 fight over the same elements. Let D3 own a `<svg>` ref exclusively, or use D3 only for math (scales, generators, layouts) and let the framework render.

3. **Breaking chains to store unused selections.** Only name a selection when referenced later (transitions, event handlers). Otherwise chain — it keeps the dependency flow visible.

4. **Overusing `.each()` when chained `.attr()` suffices.** Reserve `.each()` for side effects or when multiple attributes share an expensive intermediate value.

5. **Forgetting `.transition()` returns a transition, not a selection.** You can't `.on("click", ...)` on a transition — it silently doesn't attach. Attach handlers before `.transition()`.

6. **Using `.enter().append()...merge()` when `.join()` works.** The old pattern is four lines where `.join()` is one. Use old pattern only for D3 v4/v5 compatibility.

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
