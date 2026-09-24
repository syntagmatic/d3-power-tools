"""scripts/audit — audit data layer for dossier-graduation comparisons.

Public surface:
    AuditSchema, Dimension, GENERAL, TRANSITION
    DimensionScore, AuditProvenance, CompositeSnapshot, AuditResult
    Run
    compare, ComparisonResult, ResultDiff, FlagChange, ResultKey, PairingPolicy
    Evaluator, REGISTRY, evaluator_for_block
"""

from .schema import AuditSchema, Dimension, GENERAL, TRANSITION, SCHEMAS
from .result import (
    DimensionScore,
    AuditProvenance,
    CompositeSnapshot,
    AuditResult,
)
from .run import Run
from .compare import (
    compare,
    ComparisonResult,
    ResultDiff,
    FlagChange,
    ResultKey,
    PairingPolicy,
)
from .evaluator import Evaluator, REGISTRY, evaluator_for_block, EvaluationContext

__all__ = [
    "AuditSchema",
    "Dimension",
    "GENERAL",
    "TRANSITION",
    "SCHEMAS",
    "DimensionScore",
    "AuditProvenance",
    "CompositeSnapshot",
    "AuditResult",
    "Run",
    "compare",
    "ComparisonResult",
    "ResultDiff",
    "FlagChange",
    "ResultKey",
    "PairingPolicy",
    "Evaluator",
    "REGISTRY",
    "evaluator_for_block",
    "EvaluationContext",
]
