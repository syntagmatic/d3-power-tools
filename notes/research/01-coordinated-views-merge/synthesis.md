---
role: synthesizer
model: TBD
harness: TBD
date: TBD
status: skeleton
---

# Synthesis: coordinated-views merge proposal

> This file is a skeleton. The synthesizer fills in each section. The skeleton's headers and order are load-bearing — critics expect to find the same sections in every dossier's synthesis.

## Decision

> One sentence. Which of the three options (full merge / move-and-keep / status quo) is being proposed, and on what evidence?

## Proposed shape

> Concretely: which skills exist after this dossier graduates? List them with their new descriptions (frontmatter `description` field) and one-line summaries.

```
skills/<name>/    description: "..."
                 covers: <bullet list of major sections>
                 size:   ~XXX lines
```

## What changes

### Files moved

> Source path → destination path. List every move.

### Files deleted

> Any skill whose entire content is absorbed.

### Files left as redirect stubs

> Per the refactor protocol, deleted skill paths get 3-line stubs pointing to the new home. List which.

### Cross-references updated

> Other skills that mention these three. Search `skills/*/SKILL.md` and `meta/*/SKILL.md` for occurrences and list each one with its required edit.

## What stays out

> Brush mechanics (intersection, lasso, fisheye, spatial indexing, keyboard) — these don't merge into `coordinated-views`. State explicitly where they live in the proposed shape.

## Pre-refactor baseline

> Run the audit pipeline on the current ~107 blocks and freeze the composite scores. Cite the run ID. The graduation criteria (`±0.5 of baseline`) reference this number.

```
baseline-run: <evals/runs/NN-baseline-coordinated-views-merge.json>
mean composite: X.X
median: X.X
n: NN blocks
```

## Why this shape, not the alternatives

> Address each of the three options from `findings.md` in 1–2 sentences. Why is the chosen option better, and what would change your mind?

## Risks

> What's the worst-case outcome if this merge is wrong? Which blocks are most exposed? What's the rollback path?

## Open questions deferred to critique / test

> List the questions you don't expect to answer alone. Critics get first crack at them.
