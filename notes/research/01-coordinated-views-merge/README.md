# Dossier 01 — Coordinated Views Merge

**Status:** draft
**Created:** 2026-04-29
**Question:** Should `brushing`, `linked-views`, and `coordination` merge into a single `coordinated-views` skill?

## Why this dossier

These three skills currently overlap on activation triggers and produce discriminator-indistinguishable blocks (CV R² ≈ -0.33). This is the highest-confidence merge candidate from the broader skill-taxonomy refactor — contained blast radius, clear empirical question, three independent skills to compare against.

## Layout

```
01-coordinated-views-merge/
├── README.md                  ← this file
├── PROMPT.md                  ← the question, fully stated
├── findings.md                ← empirical comparison of the three skills
├── synthesis.md               ← proposed shape (skeleton — synthesizer fills)
├── library-implications.md    ← checkboxed migration plan
├── decision.md                ← graduate / iterate / revert (filled at graduation)
├── critique/
│   └── PROMPT.md              ← role brief for critic agents
└── tests/
    ├── PROMPT.md              ← role brief for alt-generators
    ├── BLIND-JUDGE-PROMPT.md  ← role brief for blind-judge agents
    ├── skill-under-test/      ← synthesizer drops merged SKILL.md here
    ├── fixtures/iris/         ← task spec + data
    ├── blocks/                ← alt-generators write outputs here (by model)
    └── audit/                 ← blind-judges write scores here
```

## Lifecycle

```
draft → populated → synthesized → critiqued → tested → graduated
         (here once findings.md is reviewed)
```

## Adversarial pairing

Each role records its model in frontmatter. No model may play two roles for this dossier. Recommended assignments (subject to availability):

- **synthesizer** — Claude (Opus or Sonnet)
- **critic** — Gemini Pro and one OpenAI model, independently
- **alt-generator** — three different models, one each (e.g., Claude Sonnet, Gemini Flash, GPT-5/Codex)
- **blind-judge** — a model that didn't generate or synthesize (rotate as needed)

## Graduation criteria

A merge graduates iff:
- ≥2 critics signed off, or all blockers resolved in `critique/responses.md`
- Cross-model audit composites in `tests/audit/` are within ±0.5 of the pre-refactor baseline (baseline declared in `synthesis.md`)
- No `render-error` flags on any tested block
- All checkboxes in `library-implications.md` ticked

If any fails, `decision.md` records `iterate` or `revert`.

## Templates

The role briefs in `critique/`, `tests/PROMPT.md`, and `tests/BLIND-JUDGE-PROMPT.md` are adapted from `notes/research/_templates/`. Update those upstream first if the role contracts evolve.
