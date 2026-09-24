"""Audit schemas — declared as data, not implicit tuples.

A schema names a set of weighted dimensions and the rules for collapsing them
into a composite. Two schemas exist at v2: GENERAL (the four-dim inspection
suite) and TRANSITION (transition + visual_critic for animation-heavy blocks).

Composites are not cross-schema comparable. compare() refuses; this module
makes the schema explicit so that refusal is well-defined.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

CompositePolicy = Literal["complete_only", "renormalize_partial"]


@dataclass(frozen=True)
class Dimension:
    id: str
    weight: float
    required: bool = True


@dataclass(frozen=True)
class CompositeSnapshot:
    """Self-describing composite: value plus the rules used to compute it."""
    value: float | None
    policy: CompositePolicy
    schema_id: str
    complete: bool
    missing_dimensions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "policy": self.policy,
            "schema_id": self.schema_id,
            "complete": self.complete,
            "missing_dimensions": list(self.missing_dimensions),
        }

    @classmethod
    def from_dict(cls, d: Mapping) -> "CompositeSnapshot":
        return cls(
            value=d.get("value"),
            policy=d["policy"],
            schema_id=d["schema_id"],
            complete=bool(d["complete"]),
            missing_dimensions=tuple(d.get("missing_dimensions", [])),
        )


@dataclass(frozen=True)
class AuditSchema:
    id: str
    dimensions: tuple[Dimension, ...]

    def dimension_ids(self) -> tuple[str, ...]:
        return tuple(d.id for d in self.dimensions)

    def required_ids(self) -> tuple[str, ...]:
        return tuple(d.id for d in self.dimensions if d.required)

    def weight_of(self, dim_id: str) -> float:
        for d in self.dimensions:
            if d.id == dim_id:
                return d.weight
        raise KeyError(f"{dim_id!r} not in schema {self.id!r}")

    def validate_scores(self, scores: Mapping[str, "DimensionScore"]) -> list[str]:
        """Return list of validation errors. Empty = valid."""
        errors: list[str] = []
        declared = set(self.dimension_ids())
        for dim_id in scores:
            if dim_id not in declared:
                errors.append(f"unknown dimension {dim_id!r} for schema {self.id!r}")
        for d in self.dimensions:
            if d.required and d.id not in scores:
                errors.append(f"missing required dimension {d.id!r}")
        return errors

    def composite(
        self,
        scores: Mapping[str, "DimensionScore"],
        *,
        policy: CompositePolicy = "complete_only",
    ) -> CompositeSnapshot:
        present_with_value = {
            d.id: scores[d.id].value
            for d in self.dimensions
            if d.id in scores and scores[d.id].value is not None
        }
        missing = tuple(
            d.id
            for d in self.dimensions
            if d.id not in scores or scores[d.id].value is None
        )
        complete = len(missing) == 0

        if policy == "complete_only":
            if not complete:
                return CompositeSnapshot(
                    value=None,
                    policy=policy,
                    schema_id=self.id,
                    complete=False,
                    missing_dimensions=missing,
                )
            value = sum(present_with_value[d.id] * d.weight for d in self.dimensions)
            return CompositeSnapshot(
                value=round(value, 3),
                policy=policy,
                schema_id=self.id,
                complete=True,
                missing_dimensions=(),
            )

        if policy == "renormalize_partial":
            if not present_with_value:
                return CompositeSnapshot(
                    value=None,
                    policy=policy,
                    schema_id=self.id,
                    complete=False,
                    missing_dimensions=missing,
                )
            present_weight = sum(self.weight_of(dim_id) for dim_id in present_with_value)
            if present_weight == 0:
                return CompositeSnapshot(
                    value=None,
                    policy=policy,
                    schema_id=self.id,
                    complete=False,
                    missing_dimensions=missing,
                )
            value = sum(
                v * self.weight_of(dim_id) for dim_id, v in present_with_value.items()
            ) / present_weight
            return CompositeSnapshot(
                value=round(value, 3),
                policy=policy,
                schema_id=self.id,
                complete=complete,
                missing_dimensions=missing,
            )

        raise ValueError(f"unknown composite policy {policy!r}")


GENERAL = AuditSchema(
    id="general",
    dimensions=(
        Dimension("visual_critic", 0.30),
        Dimension("encoding_integrity", 0.25),
        Dimension("cognitive_load", 0.25),
        Dimension("stress_test", 0.20),
    ),
)

TRANSITION = AuditSchema(
    id="transition",
    dimensions=(
        Dimension("transition", 0.60),
        Dimension("visual_critic", 0.40),
    ),
)

SCHEMAS: Mapping[str, AuditSchema] = {GENERAL.id: GENERAL, TRANSITION.id: TRANSITION}


def get_schema(schema_id: str) -> AuditSchema:
    if schema_id not in SCHEMAS:
        raise KeyError(f"unknown schema {schema_id!r}; known: {list(SCHEMAS)}")
    return SCHEMAS[schema_id]
