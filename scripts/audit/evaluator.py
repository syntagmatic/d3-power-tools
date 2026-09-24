"""Evaluator protocol and minimal dispatch registry.

An Evaluator is a callable that turns (html_path, ctx) into an AuditResult.
It declares its schema. Dispatch is an explicit dict — no self-registration,
no plugin system, no config loader. Callers select an evaluator by reading
the block's audit_schema field from blocks/manifest.json (or its successor).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol, runtime_checkable

from .result import AuditResult
from .schema import AuditSchema


PROJ = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = PROJ / "blocks" / "manifest.json"


@dataclass(frozen=True)
class EvaluationContext:
    """Per-call context. Pure data; serialisable; no callbacks."""
    block_id: str
    fixture_id: str = "default"
    generator_model: str = "unknown-generator"
    judge_model: str = "unknown-judge"
    block_sha: str = "unknown"
    skill_shas: Mapping[str, str] | None = None
    stub: bool = False
    """When True, evaluators may produce structurally-valid stubbed results
    without invoking the underlying audit machinery. The tracer uses this;
    production graduation must run with stub=False."""


@runtime_checkable
class Evaluator(Protocol):
    id: str
    schema: AuditSchema

    def __call__(self, html_path: Path, ctx: EvaluationContext) -> AuditResult: ...


# Lazy imports so registry construction doesn't pull playwright etc. at module load.
def _general_evaluate(html_path: Path, ctx: EvaluationContext) -> AuditResult:
    from .evaluators import general
    return general.evaluate(html_path, ctx)


def _transition_evaluate(html_path: Path, ctx: EvaluationContext) -> AuditResult:
    from .evaluators import transition
    return transition.evaluate(html_path, ctx)


REGISTRY: Mapping[str, Callable[[Path, EvaluationContext], AuditResult]] = {
    "general": _general_evaluate,
    "transition": _transition_evaluate,
}


def evaluator_for_block(block_id: str) -> str:
    """Read blocks/manifest.json and return the evaluator id for block_id.

    Defaults to "general" when audit_schema is not set on the block. Raises
    KeyError if block_id is not in the manifest.
    """
    manifest = json.loads(MANIFEST_PATH.read_text())
    for entry in manifest["blocks"]:
        if entry["id"] == block_id:
            return entry.get("audit_schema", "general")
    raise KeyError(f"block {block_id!r} not found in {MANIFEST_PATH}")


def evaluate(html_path: Path, ctx: EvaluationContext) -> AuditResult:
    """Convenience: dispatch to the right evaluator by manifest lookup."""
    schema_id = evaluator_for_block(ctx.block_id)
    if schema_id not in REGISTRY:
        raise KeyError(
            f"manifest declares audit_schema={schema_id!r} for {ctx.block_id!r} "
            f"but it is not in REGISTRY ({list(REGISTRY)})"
        )
    return REGISTRY[schema_id](html_path, ctx)
