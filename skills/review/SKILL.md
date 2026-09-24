---
name: review
description: "Review a D3 visualization with three independent critics in parallel: viz-critic (screenshot-only design judgment), encoding-auditor (honest encodings and robust scales/joins), interaction-tester (headless hover, brush, storms, resize, keyboard). Use after building or changing a chart, before calling it done, or when asked to review, critique, audit, or stress-test a visualization."
---

# Review

The maker shouldn't grade its own work. Each critic runs in its own context and sees a different slice of the artifact, so they can't talk each other into a score and none of them has your reasons for the choices you made.

| Critic | Gets | Never gets |
|---|---|---|
| `viz-critic` | the original request + a screenshot | source, conversation |
| `encoding-auditor` | the HTML path (+ data file) | conversation, screenshots of your intent |
| `interaction-tester` | the file path or URL | source, conversation |

## Run it

1. **Render once.** `node <plugin-root>/scripts/probe.mjs <file> --checks load,nan --out <tmp>/review`. If this reports errors, fix them first. There's no point asking for taste on a broken page.
2. **Launch all three critics in one message**, so they run in parallel. Give each exactly its column above, and pass the request the way the user phrased it, not your summary of it. Don't tell a critic what you were going for, what you already fixed, or what you're worried about.
   - viz-critic: `Request: <verbatim>. Screenshot: <tmp>/review/load.png`
   - encoding-auditor: `Audit <abs path to html>`
   - interaction-tester: `Test <abs path or URL>`
3. **Merge** the three JSON results into one report:

```
Design       6/10  <impression>
Encoding     8/10  <note>
Interaction  5/10  <note>   flags: storm, resize

Fix first:
1. <highest-impact issue, which critic, where>
2. ...
3. ...
```

Rank "fix first" by what the viewer would hit soonest: broken rendering and NaN, then errors under interaction, dishonest encodings, layout and legibility, then polish. At most five items.

4. **Fix, then re-run only the critics whose findings you addressed.** Stop when no critic reports an error-severity finding and the design score is where the request needs it. A 5 is fine for a quick exploratory plot and not fine for a publication graphic.

## Rules

- Don't argue with a critic's score in your summary. If you think a finding is wrong, say so separately and say why. The user decides.
- Report scores as the critics gave them. Don't average them into one number: a gorgeous chart with a truncated baseline isn't a 7.
- If a critic can't run (no Playwright, no screenshot), say which one and why, and report the other two.
- Playwright setup, if missing: `npm install` in the plugin root, then `npx playwright install chromium`.
