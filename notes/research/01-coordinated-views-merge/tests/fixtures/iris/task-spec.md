# Task Spec — iris

## Data

`data.csv` contains the classic iris dataset: 150 rows, columns `sepal_length, sepal_width, petal_length, petal_width, species`. Species is one of `setosa`, `versicolor`, `virginica` (50 rows each).

If `data.csv` is not yet in this directory, fetch it once:

```bash
curl -L -o data.csv 'https://gist.githubusercontent.com/curran/a08a1080b88344b0c8a7/raw/0e7a9b0a9bd9be3b5f3c2c94fee8b7c6f4e9e8e6/iris.csv'
```

(Or any equivalent source — the column names must match.)

## Build

A self-contained HTML block that:

1. Loads `./data.csv` via `d3.csv`.
2. Shows **at least two views** of the data. Examples (pick whatever fits the SKILL.md you're given):
   - Two scatterplots on different pairs of dimensions
   - A scatterplot + a parallel coordinates plot
   - A scatterplot + a small histogram per dimension
   - A table + a chart
3. **Coordinates the views.** Selecting or brushing in any view highlights or filters the same flowers in all other views. The user must be able to brush a continuous-valued region in at least one view.
4. Uses ONLY the patterns in `tests/skill-under-test/SKILL.md`. No patterns lifted from other skills.
5. Is self-contained: inline CSS, inline JS, D3 v7 from CDN, no build step.
6. Renders without console errors.

## Constraints

- **Don't add features the spec doesn't ask for.** No legend with click-to-filter unless the SKILL.md prescribes it. No tooltips unless prescribed.
- **Don't pre-aggregate.** The data is 150 rows; show them all.
- **Pick reasonable defaults** for size, color, layout. Don't agonize over them — pick something defensible in 30 seconds and move on.
- **Reset behavior:** clicking outside any selection or pressing escape clears all selections. (This is universal coordinated-views behavior; if your SKILL.md doesn't address it, note that in your log.)

## Out of scope

- Server-side rendering or workers.
- Performance optimization (iris is 150 rows; any reasonable approach is fast).
- Custom data wrangling.
- Animation or scrollytelling.
- Accessibility beyond what the SKILL.md prescribes (judges score it; you don't have to over-engineer).

## What this fixture tests

The simplest possible case for the merged skill. Two-view linked iris is the "hello world" of coordinated views — every linked-views tutorial in existence builds a version of it. If the merged SKILL.md can't reliably produce a working two-view linked iris across three independent generators, the merge is underspecified.

If two views feel ambiguous to disambiguate from the SKILL.md, document the ambiguity in your generator log. Don't paper over it.
