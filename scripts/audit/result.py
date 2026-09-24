"""AuditResult — the load-bearing record.

A v2 AuditResult declares its schema, carries strict per-result provenance
(generator/judge/fixture/evaluator/block), and stores composite as a
self-describing snapshot. from_dict refuses missing provenance fields rather
than fabricating them — legacy v1 records do not round-trip and are not
expected to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Mapping

from .schema import (
    AuditSchema,
    CompositePolicy,
    CompositeSnapshot,
    SCHEMAS,
    get_schema,
)


Status = Literal["passed", "incomplete", "render_failed", "evaluator_failed"]

STATUS_VALUES: tuple[Status, ...] = (
    "passed",
    "incomplete",
    "render_failed",
    "evaluator_failed",
)


@dataclass(frozen=True)
class DimensionScore:
    value: float | None
    note: str = ""
    flags: tuple[str, ...] = ()
    source_tool: str = ""
    input_artifacts: tuple[str, ...] = ()
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "note": self.note,
            "flags": list(self.flags),
            "source_tool": self.source_tool,
            "input_artifacts": list(self.input_artifacts),
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, d: Mapping) -> "DimensionScore":
        return cls(
            value=d.get("value"),
            note=d.get("note", ""),
            flags=tuple(d.get("flags", [])),
            source_tool=d.get("source_tool", ""),
            input_artifacts=tuple(d.get("input_artifacts", [])),
            context=d.get("context", ""),
        )


REQUIRED_PROVENANCE_FIELDS = (
    "block_id",
    "fixture_id",
    "generator_model",
    "judge_model",
    "evaluator_id",
    "block_sha",
    "timestamp",
)


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

    def to_dict(self) -> dict:
        out: dict = {
            "block_id": self.block_id,
            "fixture_id": self.fixture_id,
            "generator_model": self.generator_model,
            "judge_model": self.judge_model,
            "evaluator_id": self.evaluator_id,
            "block_sha": self.block_sha,
            "timestamp": self.timestamp,
        }
        if self.skill_shas is not None:
            out["skill_shas"] = dict(self.skill_shas)
        return out

    @classmethod
    def from_dict(cls, d: Mapping) -> "AuditProvenance":
        missing = [f for f in REQUIRED_PROVENANCE_FIELDS if not d.get(f)]
        if missing:
            raise ValueError(
                f"AuditProvenance.from_dict: missing required fields {missing}"
            )
        return cls(
            block_id=d["block_id"],
            fixture_id=d["fixture_id"],
            generator_model=d["generator_model"],
            judge_model=d["judge_model"],
            evaluator_id=d["evaluator_id"],
            block_sha=d["block_sha"],
            timestamp=d["timestamp"],
            skill_shas=dict(d["skill_shas"]) if d.get("skill_shas") else None,
        )


@dataclass(frozen=True)
class AuditResult:
    schema_id: str
    status: Status
    provenance: AuditProvenance
    scores: Mapping[str, DimensionScore]
    result_flags: tuple[str, ...] = ()
    composite: CompositeSnapshot | None = None

    def schema(self) -> AuditSchema:
        return get_schema(self.schema_id)

    def is_complete(self) -> bool:
        return self.status == "passed" and (
            self.composite is not None and self.composite.complete
        )

    def with_composite(self, *, policy: CompositePolicy = "complete_only") -> "AuditResult":
        snap = self.schema().composite(self.scores, policy=policy)
        return AuditResult(
            schema_id=self.schema_id,
            status=self.status,
            provenance=self.provenance,
            scores=dict(self.scores),
            result_flags=self.result_flags,
            composite=snap,
        )

    def to_dict(self) -> dict:
        return {
            "schema_id": self.schema_id,
            "status": self.status,
            "provenance": self.provenance.to_dict(),
            "scores": {k: v.to_dict() for k, v in self.scores.items()},
            "result_flags": list(self.result_flags),
            "composite": self.composite.to_dict() if self.composite is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Mapping) -> "AuditResult":
        schema_id = d["schema_id"]
        if schema_id not in SCHEMAS:
            raise ValueError(f"unknown schema_id {schema_id!r}")
        status = d["status"]
        if status not in STATUS_VALUES:
            raise ValueError(f"unknown status {status!r}")
        prov = AuditProvenance.from_dict(d["provenance"])
        scores = {k: DimensionScore.from_dict(v) for k, v in d["scores"].items()}

        schema = get_schema(schema_id)
        errors = schema.validate_scores(scores)
        # missing required is allowed if status != passed (e.g. incomplete);
        # unknown-dimension errors are always fatal.
        unknown = [e for e in errors if e.startswith("unknown dimension")]
        if unknown:
            raise ValueError("; ".join(unknown))
        if status == "passed":
            missing = [e for e in errors if e.startswith("missing required")]
            if missing:
                raise ValueError(
                    "passed result rejects missing required dimensions: "
                    + "; ".join(missing)
                )

        composite_raw = d.get("composite")
        composite = (
            CompositeSnapshot.from_dict(composite_raw)
            if composite_raw is not None
            else None
        )
        if composite is not None:
            if composite.schema_id != schema_id:
                raise ValueError(
                    f"composite.schema_id {composite.schema_id!r} ≠ "
                    f"AuditResult.schema_id {schema_id!r}"
                )
            recomputed = schema.composite(scores, policy=composite.policy)
            if (
                recomputed.value != composite.value
                or recomputed.complete != composite.complete
                or set(recomputed.missing_dimensions) != set(composite.missing_dimensions)
            ):
                raise ValueError(
                    "stored composite snapshot does not match recomputation: "
                    f"stored={composite.to_dict()} recomputed={recomputed.to_dict()}"
                )

        return cls(
            schema_id=schema_id,
            status=status,
            provenance=prov,
            scores=scores,
            result_flags=tuple(d.get("result_flags", [])),
            composite=composite,
        )
