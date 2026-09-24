"""compare(baseline, treatment, …) → ComparisonResult.

Pairs results across two runs by a strict identity tuple, computes per-
dimension and composite diffs, tracks flag-set changes, and refuses
silently incommensurate comparisons. compare() is fact-producing only —
keep/discard policy lives in scripts/iterate/, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Mapping

from .result import AuditResult
from .run import Run
from .schema import SCHEMAS


Verdict = Literal["pass", "fail", "inconclusive"]


@dataclass(frozen=True)
class ResultKey:
    block_id: str
    fixture_id: str
    schema_id: str
    generator_model: str
    judge_model: str
    evaluator_id: str

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "fixture_id": self.fixture_id,
            "schema_id": self.schema_id,
            "generator_model": self.generator_model,
            "judge_model": self.judge_model,
            "evaluator_id": self.evaluator_id,
        }

    @classmethod
    def of(cls, r: AuditResult) -> "ResultKey":
        p = r.provenance
        return cls(
            block_id=p.block_id,
            fixture_id=p.fixture_id,
            schema_id=r.schema_id,
            generator_model=p.generator_model,
            judge_model=p.judge_model,
            evaluator_id=p.evaluator_id,
        )


@dataclass(frozen=True)
class FlagChange:
    added: tuple[str, ...]
    removed: tuple[str, ...]

    def is_empty(self) -> bool:
        return not self.added and not self.removed

    def to_dict(self) -> dict:
        return {"added": list(self.added), "removed": list(self.removed)}


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

    def to_dict(self) -> dict:
        return {
            "key": self.key.to_dict(),
            "schema_id": self.schema_id,
            "per_dimension_diff": dict(self.per_dimension_diff),
            "composite_diff": self.composite_diff,
            "dimension_flags_changed": {
                k: v.to_dict()
                for k, v in self.dimension_flags_changed.items()
                if not v.is_empty()
            },
            "result_flags_changed": self.result_flags_changed.to_dict(),
            "status_change": list(self.status_change),
            "render_error_count": self.render_error_count,
        }


@dataclass(frozen=True)
class PairingPolicy:
    """Only strict pairing is implemented at v2 minimum-viable."""
    mode: Literal["strict"] = "strict"

    @classmethod
    def strict(cls) -> "PairingPolicy":
        return cls(mode="strict")


ToleranceMap = Mapping[str, float] | float


@dataclass(frozen=True)
class ComparisonResult:
    verdict: Verdict
    tolerance: Mapping[str, float]
    diffs: tuple[ResultDiff, ...]
    missing_baseline: tuple[ResultKey, ...]
    missing_treatment: tuple[ResultKey, ...]
    failures: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "tolerance": dict(self.tolerance),
            "diffs": [d.to_dict() for d in self.diffs],
            "missing_baseline": [k.to_dict() for k in self.missing_baseline],
            "missing_treatment": [k.to_dict() for k in self.missing_treatment],
            "failures": list(self.failures),
        }


def _normalize_tolerance(tolerance: ToleranceMap) -> dict[str, float]:
    if isinstance(tolerance, (int, float)):
        return {"composite": float(tolerance)}
    return dict(tolerance)


def _flag_change(before: Iterable[str], after: Iterable[str]) -> FlagChange:
    a, b = set(before), set(after)
    return FlagChange(added=tuple(sorted(b - a)), removed=tuple(sorted(a - b)))


def _diff_pair(baseline: AuditResult, treatment: AuditResult) -> ResultDiff:
    if baseline.schema_id != treatment.schema_id:
        raise ValueError(
            f"compare(): paired results have mismatched schemas "
            f"({baseline.schema_id!r} vs {treatment.schema_id!r}); "
            f"cross-schema composite comparison is forbidden"
        )
    schema = SCHEMAS[baseline.schema_id]

    per_dim: dict[str, float | None] = {}
    flag_diffs: dict[str, FlagChange] = {}
    for dim in schema.dimensions:
        bv = baseline.scores.get(dim.id)
        tv = treatment.scores.get(dim.id)
        bvalue = bv.value if bv is not None else None
        tvalue = tv.value if tv is not None else None
        if bvalue is None or tvalue is None:
            per_dim[dim.id] = None
        else:
            per_dim[dim.id] = round(tvalue - bvalue, 3)
        flag_diffs[dim.id] = _flag_change(
            bv.flags if bv is not None else (),
            tv.flags if tv is not None else (),
        )

    bcomp = baseline.composite.value if baseline.composite else None
    tcomp = treatment.composite.value if treatment.composite else None
    composite_diff = (
        round(tcomp - bcomp, 3) if (bcomp is not None and tcomp is not None) else None
    )

    rb = "render-error" in baseline.result_flags
    rt = "render-error" in treatment.result_flags
    render_error_count = int(rb) + int(rt)

    return ResultDiff(
        key=ResultKey.of(baseline),
        schema_id=baseline.schema_id,
        per_dimension_diff=per_dim,
        composite_diff=composite_diff,
        dimension_flags_changed=flag_diffs,
        result_flags_changed=_flag_change(baseline.result_flags, treatment.result_flags),
        status_change=(baseline.status, treatment.status),
        render_error_count=render_error_count,
    )


def _verdict(
    diffs: Iterable[ResultDiff],
    tolerance: Mapping[str, float],
    *,
    has_unpaired: bool,
    failures: Iterable[str],
) -> Verdict:
    if list(failures):
        return "fail"
    composite_tol = tolerance.get("composite")
    diffs = list(diffs)
    if any(d.render_error_count > 0 for d in diffs):
        return "fail"
    if composite_tol is not None and any(
        d.composite_diff is not None and d.composite_diff < -composite_tol
        for d in diffs
    ):
        return "fail"
    inconclusive = has_unpaired or any(d.composite_diff is None for d in diffs)
    return "inconclusive" if inconclusive else "pass"


def compare(
    baseline: Run,
    treatment: Run,
    *,
    tolerance: ToleranceMap = 0.5,
    allow_unpaired: bool = False,
    pairing_policy: PairingPolicy = PairingPolicy.strict(),
) -> ComparisonResult:
    """Compare two Runs. Strict pairing on the full ResultKey tuple.

    Refuses (raises ValueError) if cross-schema pairing would be implied.
    Returns inconclusive when unpaired results exist and allow_unpaired=True;
    raises if allow_unpaired=False.
    """
    if pairing_policy.mode != "strict":
        raise NotImplementedError(
            f"pairing policy {pairing_policy.mode!r} not yet implemented"
        )
    tol = _normalize_tolerance(tolerance)

    base_index = {ResultKey.of(r): r for r in baseline.results}
    treat_index = {ResultKey.of(r): r for r in treatment.results}

    paired_keys = sorted(
        set(base_index) & set(treat_index),
        key=lambda k: (k.block_id, k.fixture_id, k.schema_id),
    )
    only_baseline = sorted(
        set(base_index) - set(treat_index),
        key=lambda k: (k.block_id, k.fixture_id, k.schema_id),
    )
    only_treatment = sorted(
        set(treat_index) - set(base_index),
        key=lambda k: (k.block_id, k.fixture_id, k.schema_id),
    )

    failures: list[str] = []
    diffs: list[ResultDiff] = []
    for key in paired_keys:
        try:
            diffs.append(_diff_pair(base_index[key], treat_index[key]))
        except ValueError as e:
            failures.append(str(e))

    if not allow_unpaired and (only_baseline or only_treatment):
        raise ValueError(
            f"compare(): unpaired results "
            f"(missing_baseline={[k.to_dict() for k in only_treatment]}, "
            f"missing_treatment={[k.to_dict() for k in only_baseline]}); "
            f"pass allow_unpaired=True to receive a structured result instead"
        )

    has_unpaired = bool(only_baseline or only_treatment)
    verdict = _verdict(
        diffs, tol, has_unpaired=has_unpaired, failures=failures,
    )

    return ComparisonResult(
        verdict=verdict,
        tolerance=tol,
        diffs=tuple(diffs),
        missing_baseline=tuple(only_treatment),  # baseline lacks; treatment has
        missing_treatment=tuple(only_baseline),  # treatment lacks; baseline has
        failures=tuple(failures),
    )
