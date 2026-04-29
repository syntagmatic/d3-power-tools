# Test Prompt

You are producing tracer-bullet blocks for d3-power-tools. Your role is **alt-generator** — you are validating whether a proposed (or merged) skill produces good output across models. Your blocks will be audited by a blind judge that did not see your generation.

## Inputs

- `<dossier>/synthesis.md` — the proposed shape of the skill under test
- `<dossier>/tests/skill-under-test/SKILL.md` — the merged/proposed SKILL.md (the actual artifact we're testing)
- `<dossier>/tests/fixtures/<fixture-name>/data.{csv,json,...}` — data fixtures
- `<dossier>/tests/fixtures/<fixture-name>/task-spec.md` — what to build for that fixture
- `notes/CONVICTIONS.md` — project principles (read once, then forget)

`<dossier>` is the parent directory you were invoked in.

## Adversarial pairing rule

You may not play this role if your model wrote `synthesis.md` or wrote `tests/skill-under-test/SKILL.md`. Check those frontmatters. If your model is listed, abort and report.

You also may not consult, view, or be given access to:
- Other generators' blocks for this dossier (`tests/blocks/<other-model>/`)
- Audit results from any prior round
- Existing reference blocks in `/blocks/*.html`

If you find yourself reaching for `/blocks/`, stop. Read `tests/skill-under-test/SKILL.md` instead. The test is whether the SKILL.md alone produces good blocks; reference blocks would contaminate that signal.

## Task

For each fixture in `tests/fixtures/`, produce one self-contained HTML block. Each block:

- Loads its fixture file from a relative path
- Uses ONLY the skill under test (no patterns from other skills)
- Inlines all CSS and JS
- Loads D3 v7 from a CDN
- Opens in a browser with no build step
- Implements the visualization described in the fixture's `task-spec.md`

Write each block to `<dossier>/tests/blocks/<your-model-id>/<fixture-name>.html`.

## Anti-cheat constraints

- **One skill only.** If the skill under test is `coordinated-views`, your block uses coordinated-views patterns and nothing borrowed from `scales`, `color`, `brushing`, etc. Use whatever scale/color choices come naturally to you, but don't reference other skills' SKILL.md files.
- **No prompt expansion.** Use the task spec as written. Don't add features it doesn't ask for. Don't make it "nicer" than asked.
- **No iteration loops.** Produce one block per fixture, one shot. The point of cross-model testing is to see what each model does first-pass, not what each model does after self-correction.

## What this measures

If three independent generators produce blocks that audit to similar scores, the skill is well-defined. If scores diverge wildly across models, the skill is underspecified — that's the signal we're after, and the divergence pattern itself is data.

If the SKILL.md is ambiguous, **note it in your log instead of making the ambiguity disappear**. Specific ambiguities you encountered are more valuable than a polished block.

## Output

Per fixture:
```
<dossier>/tests/blocks/<your-model-id>/<fixture-name>.html
```

Plus a generator log:
```
<dossier>/tests/blocks/<your-model-id>/log.md
```

With this frontmatter:

```
---
role: alt-generator
model: <your model id>
harness: <claude-code | gemini-cli | codex-cli | opencode>
date: <YYYY-MM-DD>
skill-under-test: <skill name>
skill-rev: <git sha of skill-under-test/SKILL.md, or N/A>
fixtures: [<fixture-1>, <fixture-2>, ...]
---
```

Body of `log.md`: brief notes per fixture — what was easy, what the SKILL.md was ambiguous about, what you had to decide unilaterally. Maximum 300 words total. This feeds synthesis revisions; specific ambiguities are gold.

Do not produce audit scores yourself. The blind-judge role does that separately, with its own prompt.
