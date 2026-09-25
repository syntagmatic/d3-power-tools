# D3 idioms

Absorbed from the v2 `d3-idioms` meta skill. Open when writing or reviewing D3 code for style: chaining, joins, composition, reusable charts, naming, events.

Conventional D3 is code others can read and extend. Each rule below says what breaks without it.

## Chaining indentation

Two spaces for a method that returns a **new** selection, four for one that returns the **same** selection. The indent shows which element each `.attr` targets.

```js
const svg = d3.select("#chart")
  .append("svg")
    .attr("viewBox", [0, 0, width, height]);

svg.selectAll("rect")
  .data(data, d => d.id)
  .join("rect")
    .attr("x", d => x(d.name))
    .attr("y", d => y(d.value))
    .attr("height", d => y(0) - y(d.value))
    .attr("width", x.bandwidth());
```

Short chains and project formatters override this; consistency within a project wins.

## Margin convention

`width`/`height` are the outer SVG size; `margin = {top, right, bottom, left}`; one `g` translated by `(margin.left, margin.top)`; scale ranges use the inner size. Without it, magic offsets (`x + 40`, `height - 25`) scatter and all break when a label grows.

## Joins

- A key function whenever data can reorder, filter, or update: `.data(data, d => d.id)`. Index joins silently re-assign elements after a sort, and transitions morph bars into unrelated values. Static one-shot charts can skip it.
- `.join("rect")` for the common case. Pass `enter`/`update`/`exit` callbacks only when they differ (enter from zero, exit to zero). `.enter().append().merge()` is only for v4/v5 code.
- `data.forEach(d => svg.append(...))` bypasses the join: no exit, no keys, no transitions. The exception is Canvas, where there's no DOM to join.

## selection.call

`.call(fn, ...args)` runs `fn(selection, ...args)` and returns the original selection, so chains continue. Axes, brush, zoom, and drag all attach this way. Factor repeated styling into a function and `.call` it:

```js
function grid(g, scale, innerHeight) {
  g.call(d3.axisBottom(scale))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").clone()
        .attr("y2", -innerHeight)
        .attr("stroke-opacity", 0.1));
}
```

## Scales and accessors

`d => x(d.date)`, never `d => d.date * pxPerDay + 40`: inline arithmetic has to be rewritten everywhere when the scale type changes. Pass accessors to `d3.max(data, d => d.value)` instead of mapping first.

## Reusable chart closure

Bostock's closure with getter-setters (`chart.width = function(_) { return arguments.length ? (width = _, chart) : width; }`) earns its boilerplate for components rendered many times: small multiples, dashboard widgets. Render with `selection.each` so each container gets its own datum. For one-off charts it hides state from the console and doubles code size; inline code with clear names is idiomatic there.

## Names

| Name | Meaning |
|---|---|
| `d`, `i` | datum, index |
| `x`, `y` | position scales (`y1`/`y2` for dual-y, `xBand`/`xLinear` when both exist) |
| `color` | color scale, named for its output |
| `svg`, `g` | root, margin-translated group |
| `t` | shared transition |
| `line`, `area`, `arc` | shape generators |
| `path` | `d3.geoPath(projection)` |

## Events

- `function (event, d)` gets the element as `this`; an arrow function doesn't, so use `event.currentTarget`. `d3.select(this)` inside an arrow selects the wrong thing (or nothing) silently.
- Namespace listeners: `.on("click.tooltip", ...)`. An un-namespaced second `.on("click", ...)` replaces the first, which bites when zoom, brush, and custom handlers share an element.
- `.transition()` returns a transition. `transition.on` accepts only `start`, `end`, `interrupt`, `cancel`; attach pointer handlers before calling `.transition()`.
- Transitions of the same name on the same element interrupt each other. Share one `t` across a coordinated update, or name them.

## Frameworks

React/Vue and D3 fighting over the same nodes produces ghosts. Give D3 exclusive ownership of an `<svg>` ref, or use D3 only for math (scales, generators, layouts) and let the framework render.

## Review checklist

| Check | Flag |
|---|---|
| Indentation | flat chains |
| Joins | `.join()` without keys on updating data |
| Margins | magic pixel offsets |
| Scales | inline arithmetic in `.attr` |
| Axes | hand-built ticks |
| Reuse | copy-pasted styling blocks |
| Events | arrow function + `this` |
| Transitions | several unnamed transitions fighting |
| DOM | `getElementById`/jQuery mixed with selections |
| Renderer | SVG at 50K, or WebGL at 5K |
| State | brush handlers mutating data |
| Render loop | drawing directly in event handlers |
| `.each` | used where chained `.attr` would do |
