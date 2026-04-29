---
role: synthesizer
model: gpt-5-codex
harness: codex-cli
date: 2026-04-29
status: proposed
---

# Synthesis: audit architecture and protocol

## Decision

Build a new v2 audit layer under `scripts/audit/` and write v2 artifacts to `evals/audit-runs/`. The invariant is dossier graduation, not backwards compatibility with v1 iteration artifacts. Existing `evals/runs/`, `evals/iterations/`, and `evals/experiments/hierarchy-bundles-runs.json` are preserved as v1 evidence, then archived after the tracer proves the v2 package.

The new core separates three concerns:

- `scripts/audit/`: pure data types, schema rules, result/run JSON, evaluator registry, and `compare()`.
- `scripts/iterate/`: shared iteration loop that consumes audit facts and applies objective-specific keep/discard policies.
- dossier metadata/validation: baseline declarations, role separation, sample plan, and graduation criteria.

## Architecture

### `scripts/audit/schema.py`

Defines schemas as data, not implicit tuples.

```python
@dataclass(frozen=True)
class Dimension:
    id: str
    weight: float
    required: bool = True

@dataclass(frozen=True)
class AuditSchema:
    id: str
    dimensions: tuple[Dimension, ...]

    def validate_scores(self, scores: Mapping[str, DimensionScore]) -> list[str]: ...
    def composite(self, scores: Mapping[str, DimensionScore], *, policy: CompositePolicy = "complete_only") -> CompositeSnapshot: ...
```

Declared schemas:

```python
GENERAL = AuditSchema("general", (
    Dimension("visual_critic", 0.30),
    Dimension("encoding_integrity", 0.25),
    Dimension("cognitive_load", 0.25),
    Dimension("stress_test", 0.20),
))

TRANSITION = AuditSchema("transition", (
    Dimension("transition", 0.60),
    Dimension("visual_critic", 0.40),
))
```

`complete_only` is the default composite policy. Partial renormalized composites require an explicit `policy="renormalize_partial"`. This preserves the iteration loop's practical fallback without letting graduation accidentally consume partial scores.

### `scripts/audit/result.py`

`AuditResult` is the load-bearing record. New v2 results must carry strict provenance; production `from_dict` rejects missing `schema_id`, `fixture_id`, `generator_model`, `judge_model`, or `block_id`.

```python
@dataclass(frozen=True)
class DimensionScore:
    value: float | None
    note: str = ""
    flags: tuple[str, ...] = ()
    source_tool: str = ""
    input_artifacts: tuple[str, ...] = ()
    context: str = ""

@dataclass(frozen=True)
class AuditProvenance:
    block_id: str
    fixture_id: str
    generator_model: str
    judge_model: str
    evaluator_id: str
    block_sha: str
    timestamp: str
    skill_shas: Mapping[str, str] | None = None

@dataclass(frozen=True)
class AuditResult:
    schema_id: str
    status: Literal["passed", "incomplete", "render_failed", "evaluator_failed"]
    provenance: AuditProvenance
    scores: Mapping[str, DimensionScore]
    result_flags: tuple[str, ...] = ()
    composite: CompositeSnapshot | None = None
```

Dimension flags stay beside the dimension that emitted them. Top-level `result_flags` are execution or result conditions such as `render-error`, `incomplete-audit`, or `missing-fixture`. Reporting can derive a top-level flag from `status`, but render failure is not a score dimension.

Stored composites are structured snapshots:

```json
"composite": {
  "value": 7.2,
  "policy": "complete_only",
  "schema_id": "general",
  "complete": true,
  "missing_dimensions": []
}
```

`from_dict` validates the stored snapshot against the schema. It raises on mismatched value/policy/schema rather than silently recomputing away bad evidence.

### `scripts/audit/run.py`

`Run` is allowed to contain mixed schemas. Summaries and comparisons must group by schema and never average composites across schemas.

```python
@dataclass(frozen=True)
class Run:
    run_id: str
    timestamp: str
    git_sha: str
    default_skill_shas: Mapping[str, str]
    results: tuple[AuditResult, ...]

    def write(self, path: Path) -> None: ...
    @classmethod
    def read(cls, path: Path) -> "Run": ...
```

Effective provenance is run defaults plus per-result overrides. This keeps JSON compact while supporting mixed evaluator runs.

### `scripts/audit/compare.py`

`compare()` is the measurement primitive for both dossier graduation and iteration policy wrappers.

```python
def compare(
    baseline: Run,
    treatment: Run,
    *,
    tolerance: float | ToleranceMap = 0.5,
    allow_unpaired: bool = False,
    pairing_policy: PairingPolicy = PairingPolicy.strict(),
) -> ComparisonResult: ...
```

Pairing is by explicit policy over:

```text
(block_id, fixture_id, schema_id, generator_model, judge_model, evaluator_id)
```

Graduation uses strict pairing unless dossier metadata says otherwise. Research dashboards may pass `allow_unpaired=True`; the result is then `inconclusive` and lists `missing_baseline` / `missing_treatment`. Silent dropping of unpaired blocks is forbidden.

`ComparisonResult` contains:

```python
@dataclass(frozen=True)
class ResultDiff:
    key: ResultKey
    schema_id: str
    per_dimension_diff: Mapping[str, float | None]
    composite_diff: float | None
    dimension_flags_changed: Mapping[str, FlagChange]
    result_flags_changed: FlagChange
    status_change: tuple[str, str]
    render_error_count: int

@dataclass(frozen=True)
class ComparisonResult:
    verdict: Literal["pass", "fail", "inconclusive"]
    tolerance: ToleranceMap
    diffs: tuple[ResultDiff, ...]
    missing_baseline: tuple[ResultKey, ...]
    missing_treatment: tuple[ResultKey, ...]
    failures: tuple[str, ...]
```

Composite comparisons are refused for mismatched paired schemas. Shared dimensions, such as `visual_critic`, may be compared only when fixture/context matches. Cross-schema composite aggregation is forbidden.

### `scripts/audit/evaluator.py`

Evaluator dispatch is an explicit minimal registry:

```python
class Evaluator(Protocol):
    id: str
    schema: AuditSchema
    def evaluate(self, html_path: Path, *, block_id: str, fixture_id: str, ctx: EvaluationContext) -> AuditResult: ...

REGISTRY = {
    "general": general.evaluate,
    "transition": transition.evaluate,
}
```

No self-registration, plugin system, event bus, or config loader. Callers select evaluator from `blocks/manifest.json`, defaulting to `"general"`:

```json
{
  "id": "hierarchy-bundles",
  "audit_schema": "transition",
  "audit_fixture": "hierarchy-bundles-default"
}
```

Caller override is allowed for tracer/testing only.

### `scripts/audit/evaluators/general.py`

Wraps the current four inspection tools. It may call Claude CLI, but only inside the evaluator implementation. Core modules remain pure Python and unit-testable without model access.

The evaluator records each dimension's `source_tool`, `input_artifacts`, and `context`. `stress_test` flags are dimension flags, not top-level execution flags.

### `scripts/audit/evaluators/transition.py`

Generalize the interface, not the first implementation. The evaluator accepts a transition fixture/config describing layout buttons, capture timings, expected structures, and sliders. The only required first config is `hierarchy-bundles-default`; no package code should branch on `block_id == "hierarchy-bundles"`.

`visual_critic` remains the same dimension identity as in `GENERAL`, but its context must record that it judged a final state after transition evidence. Shared-dimension comparison is allowed only when the fixture/context matches.

## JSON examples

### Mixed-schema run

```json
{
  "schema_version": 2,
  "run_id": "2026-04-29T1200-tracer",
  "timestamp": "2026-04-29T12:00:00Z",
  "git_sha": "abc1234",
  "default_skill_shas": {
    "visual_critic": "111aaaa",
    "encoding_integrity": "222bbbb",
    "stress_test": "333cccc",
    "cognitive_load": "444dddd"
  },
  "results": [
    {
      "schema_id": "general",
      "status": "passed",
      "provenance": {
        "block_id": "02-linked-scatterplot-matrix",
        "fixture_id": "default",
        "generator_model": "claude-opus-4-6",
        "judge_model": "claude-sonnet-4-6",
        "evaluator_id": "general",
        "block_sha": "def5678",
        "timestamp": "2026-04-29T12:01:00Z"
      },
      "scores": {
        "visual_critic": {
          "value": 7,
          "note": "Readable coordinated scatterplot matrix.",
          "flags": [],
          "source_tool": "visual_critic",
          "input_artifacts": ["temp/audit-screenshots/02-linked-scatterplot-matrix.png"],
          "context": "single rendered screenshot"
        },
        "encoding_integrity": {"value": 8, "note": "", "flags": [], "source_tool": "encoding_integrity"},
        "cognitive_load": {"value": 7, "note": "", "flags": [], "source_tool": "cognitive_load"},
        "stress_test": {"value": 7, "note": "", "flags": ["Update Storm"], "source_tool": "stress_test"}
      },
      "result_flags": [],
      "composite": {
        "value": 7.25,
        "policy": "complete_only",
        "schema_id": "general",
        "complete": true,
        "missing_dimensions": []
      }
    },
    {
      "schema_id": "transition",
      "status": "passed",
      "provenance": {
        "block_id": "hierarchy-bundles",
        "fixture_id": "hierarchy-bundles-default",
        "generator_model": "claude-opus-4-6",
        "judge_model": "claude-sonnet-4-6",
        "evaluator_id": "transition",
        "block_sha": "987fedc",
        "timestamp": "2026-04-29T12:05:00Z"
      },
      "scores": {
        "transition": {
          "value": 7,
          "note": "Layout morphs are mostly stable.",
          "flags": [],
          "source_tool": "transition_judge",
          "input_artifacts": ["evals/iterations/filmstrips/tracer-pack.png"],
          "context": "filmstrips plus programmatic transition report"
        },
        "visual_critic": {
          "value": 7,
          "note": "Final state is readable.",
          "flags": [],
          "source_tool": "visual_critic",
          "input_artifacts": ["evals/iterations/filmstrips/tracer-final.png"],
          "context": "post-transition final state"
        }
      },
      "result_flags": [],
      "composite": {
        "value": 7.0,
        "policy": "complete_only",
        "schema_id": "transition",
        "complete": true,
        "missing_dimensions": []
      }
    }
  ]
}
```

### Comparison artifact

```json
{
  "verdict": "pass",
  "tolerance": {"composite": 0.5},
  "diffs": [
    {
      "key": {
        "block_id": "02-linked-scatterplot-matrix",
        "fixture_id": "default",
        "schema_id": "general",
        "generator_model": "claude-opus-4-6",
        "judge_model": "claude-sonnet-4-6",
        "evaluator_id": "general"
      },
      "per_dimension_diff": {
        "visual_critic": 0,
        "encoding_integrity": -0.2,
        "cognitive_load": 0.1,
        "stress_test": 0
      },
      "composite_diff": -0.1,
      "dimension_flags_changed": {
        "stress_test": {"added": [], "removed": ["Update Storm"]}
      },
      "result_flags_changed": {"added": [], "removed": []},
      "status_change": ["passed", "passed"],
      "render_error_count": 0
    }
  ],
  "missing_baseline": [],
  "missing_treatment": [],
  "failures": []
}
```

## Iteration rewrite

Dossier 02 may rewrite the iteration path, but the boundary is strict: do not rewrite generation, staging, or report design in the same pass.

Add `scripts/iterate/` with:

- `loop.py`: shared baseline → propose → generate/edit → audit → compare → decide → log loop.
- `policies.py`: objective-specific wrappers such as `decide_block_compaction`, `decide_prompt_quality`, and future `decide_skill`.
- `adapters.py`: bridges existing block and prompt generation/editing functions into the shared loop.

Iteration policies consume `ComparisonResult`; `compare()` remains fact-producing, not policy-producing. This removes the current drift between `iterate-block.py` and `iterate-prompt.py` without turning `compare()` into an objective-specific decision engine.

## Dossier protocol

Create `notes/EVALUATION-PROTOCOL.md` at ≤1000 words. It should document only rules enforced by code:

- Dossier metadata declares baseline run, treatment runs, dossier type, affected schemas, fixture set, sample plan, tolerance, and role assignments.
- Required pre-registration fields must exist before synthesis/tracer artifacts.
- `compare()` is the only graduation comparison primitive.
- New v2 audit records require strict per-result provenance.
- Cross-schema composite aggregation is forbidden.
- Partial composites may support iteration but are not graduation-eligible unless explicitly accepted in `decision.md`.
- Stable accepted judge-bias classes: position bias, verbosity/length bias, model-family self-preference, screenshot-only blind spots, and rubric drift.
- The discriminator is archived by default and is never a graduation gate unless a later dossier repairs its dataset and validation story.

Add a small dossier validator, preferably `scripts/dossier/check.py`, that reads dossier metadata and role-file frontmatter. It should fail if `synthesis.md` exists while required pre-registration fields are absent. Role separation belongs here, not in `scripts/audit/`.

Suggested dossier metadata:

```json
{
  "dossier_id": "02-audit-architecture",
  "dossier_type": "architecture",
  "baseline_run": "evals/audit-runs/2026-04-29-baseline.json",
  "treatment_runs": [],
  "affected_schemas": ["general", "transition"],
  "fixtures": ["default", "hierarchy-bundles-default"],
  "sample_plan": {
    "generators": 3,
    "judges": 2,
    "fixtures_per_schema": 1,
    "rationale": "default pragmatic floor"
  },
  "tolerance": {"composite": 0.5},
  "roles": {
    "synthesizer": "gpt-5-codex",
    "critics": [],
    "tracer_bullet_runner": null
  }
}
```

Future templates should include `dossier_type`. Merge, split, and delete dossiers share primitives but not evidence requirements:

- merge: treatment must match baseline across representative tasks for the combined surface
- split: each new skill must preserve the subset it claims and avoid accidental co-activation
- delete: replacement or no-skill baseline must not regress owned tasks, or the loss must be explicitly accepted

## Migration order

1. Land this synthesis and maintainer review.
2. Implement `scripts/audit/` and tracer outputs in `notes/research/02-audit-architecture/tests/tracer/`.
3. Add minimal unit tests for round-trip JSON, composite policies, schema mismatch, flag changes, and `compare()` unpaired behavior.
4. Add `scripts/dossier/check.py` and `notes/EVALUATION-PROTOCOL.md`.
5. Rewrite iteration audit consumption around `ComparisonResult`; then consolidate the duplicated loop into `scripts/iterate/`.
6. Archive v1: tag `v1-pre-research`, populate `archive/v1/scripts/`, and move v1 evals only after dossier 02 no longer reads them.
7. Backfill dossier 01 gates to use `Run`, `ComparisonResult`, and `evals/audit-runs/`.

## Tracer bullet

The tracer must run one general block and one transition block:

- general: `blocks/02-linked-scatterplot-matrix.html`, schema `general`, fixture `default`
- transition: `blocks/hierarchy-bundles.html`, schema `transition`, fixture `hierarchy-bundles-default`

It must write:

- `notes/research/02-audit-architecture/tests/tracer/run.json`
- `notes/research/02-audit-architecture/tests/tracer/comparison.json`
- `notes/research/02-audit-architecture/tests/tracer/by-runner-<model>.md`

Allowed tracer stubs:

- `general.evaluate()` may run only `visual_critic` initially, but then result status must be `incomplete`, composite policy must be `renormalize_partial`, and the result is not graduation-eligible.
- `transition.evaluate()` may support only the `hierarchy-bundles-default` fixture.
- No production provenance fields may be `"unknown"`; use real simple values such as `fixture_id: "default"`.

The tracer must demonstrate schema mismatch refusal, per-dimension diffs, composite diffs, dimension and result flag changes, render-error accounting, and unpaired behavior.

## Cuts and defenses

### Literature review depth

This dossier does not need a survey of LLM-as-judge literature. The project already accepts model-judge risk as a practical constraint; the architectural failure is that current results cannot represent provenance, schema, or comparison. The protocol names stable bias classes and makes them visible, but the deliverable is enforceable data shape and comparison code.

### Sample-size methodology

The default `3 generators × 2 judges × 1 fixture` is a pragmatic floor, not a power calculation. Dossier metadata must declare the sample plan and rationale. The validator enforces explicitness, not a universal N. Future high-risk dossiers can raise the fixture count or judge count; low-risk dossiers can justify smaller samples.

### Discriminator role

The discriminator remains archived and non-gating. Current documented performance makes it unsuitable as a decision threshold. It may appear as diagnostic evidence only when a dossier states a concrete role and accepts that it is not a graduation criterion.

## Consequences

This makes old audit data archive-only unless explicitly migrated or rerun. That is acceptable. The old shape cannot answer the claims dossier 01 needs to make. Preserving it as historical evidence is honest; pretending it can be upgraded by inference would reproduce the ambiguity this dossier is removing.
