# Prompt Iteration: Optimize for Speed

You are an autonomous researcher improving a D3.js visualization prompt.
Your goal: rewrite the prompt so it generates faster while preserving required features.

## Your target

Write the improved prompt to `{{out_path}}`.

## Current prompt

```
{{current_prompt}}
```

## Current state

- **Generation time**: {{gen_time_s}}s
- **Required features** (grep patterns that MUST appear in generated HTML):
{{features_list}}

## Rules

1. Write ONE rewritten prompt to the output path.
2. The prompt must still produce a visualization with ALL required features.
3. Write only the prompt text, nothing else. No markdown fences, no explanation.

## What makes prompts generate faster

Good changes:
- Remove redundant specification (if the skill already teaches it, don't repeat it)
- Be more direct about what to build, less about how
- Remove aesthetic preferences the model will handle anyway
- Simplify data specification (fewer constraints on synthetic data)
- Reduce total prompt length

Bad changes:
- Removing information about required features or interactions
- Being so vague that the model has to guess and retry
- Removing data size/shape hints that prevent iteration

## Experiment history

{{history}}

## Go

Write the rewritten prompt to {{out_path}}. Nothing else.
