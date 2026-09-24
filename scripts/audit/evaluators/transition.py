"""Transition evaluator — fixture-driven, not block-id-driven.

Schema: TRANSITION (transition + visual_critic, weights 0.6/0.4).

The evaluator accepts a fixture describing the transition probe (layout
buttons, capture timings, expected structures). The single first-class
fixture is "hierarchy-bundles-default", which delegates to the existing
scripts/eval-hierarchy-bundles.py. Adding more transition blocks is a
matter of adding a fixture, not branching on block_id.

Stub mode produces a structurally-valid AuditResult without launching
playwright; the tracer uses this to exercise the data layer.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from ..result import AuditProvenance, AuditResult, DimensionScore
from ..schema import TRANSITION


PROJ = Path(__file__).resolve().parent.parent.parent.parent
HIERARCHY_BUNDLES_RUNNER = PROJ / "scripts" / "eval-hierarchy-bundles.py"
EXPERIMENTS_DIR = PROJ / "evals" / "experiments"


id = "transition"
schema = TRANSITION


# Fixture registry. Fixture name → static config and runner. New transition
# blocks register a fixture here; no block_id branching anywhere else.
FIXTURES: Mapping[str, dict] = {
    "hierarchy-bundles-default": {
        "runner_script": str(HIERARCHY_BUNDLES_RUNNER),
        "expected_layouts_min": 5,
        "capture_times_ms": [100, 350, 700],
        "vc_gate": 5,  # only run visual_critic when transition_score > vc_gate
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stubbed_scores(ctx) -> dict[str, DimensionScore]:
    return {
        "transition": DimensionScore(
            value=7.0,
            note="Stubbed transition score for tracer-bullet validation.",
            source_tool="transition_judge",
            input_artifacts=("evals/iterations/filmstrips/tracer-stub.png",),
            context="stub-mode tracer; not a real transition probe",
        ),
        "visual_critic": DimensionScore(
            value=7.0,
            note="Stubbed final-state score for tracer-bullet validation.",
            source_tool="visual_critic",
            input_artifacts=("evals/iterations/filmstrips/tracer-stub-final.png",),
            context="stub-mode tracer; post-transition final state",
        ),
    }


def _run_real_fixture(html_path: Path, fixture: dict, judge_model: str) -> dict | None:
    """Invoke scripts/eval-hierarchy-bundles.py and parse its emitted JSON.

    Returns the per-experiment results dict on success, None on failure.
    """
    runner = fixture["runner_script"]
    if not Path(runner).exists():
        return None
    out_dir = EXPERIMENTS_DIR / "v2-tracer"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["python3", runner, str(html_path),
             "--out-dir", str(out_dir),
             "--exp-id", "v2-tracer",
             "--model", judge_model],
            capture_output=True, text=True, timeout=180, cwd=str(PROJ),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    # Runner writes <tag>-results.json; find latest matching tracer file
    matches = sorted(out_dir.glob("*v2-tracer*-results.json"))
    if not matches:
        return None
    try:
        return json.loads(matches[-1].read_text())
    except json.JSONDecodeError:
        return None


def evaluate(html_path: Path, ctx) -> AuditResult:
    fixture_id = ctx.fixture_id or "hierarchy-bundles-default"
    if fixture_id not in FIXTURES:
        prov = AuditProvenance(
            block_id=ctx.block_id, fixture_id=fixture_id,
            generator_model=ctx.generator_model, judge_model=ctx.judge_model,
            evaluator_id=id, block_sha=ctx.block_sha, timestamp=_now_iso(),
            skill_shas=ctx.skill_shas,
        )
        return AuditResult(
            schema_id=schema.id,
            status="evaluator_failed",
            provenance=prov,
            scores={},
            result_flags=("unknown-fixture",),
        )

    prov = AuditProvenance(
        block_id=ctx.block_id,
        fixture_id=fixture_id,
        generator_model=ctx.generator_model,
        judge_model=ctx.judge_model,
        evaluator_id=id,
        block_sha=ctx.block_sha,
        timestamp=_now_iso(),
        skill_shas=ctx.skill_shas,
    )

    if ctx.stub:
        result = AuditResult(
            schema_id=schema.id,
            status="passed",
            provenance=prov,
            scores=_stubbed_scores(ctx),
            result_flags=(),
        )
        return result.with_composite(policy="complete_only")

    fixture = FIXTURES[fixture_id]
    raw = _run_real_fixture(html_path, fixture, ctx.judge_model)
    if raw is None:
        return AuditResult(
            schema_id=schema.id,
            status="evaluator_failed",
            provenance=prov,
            scores={},
            result_flags=("fixture-runner-failed",),
        )

    t_score = raw.get("transition_score")
    vc_score = raw.get("visual_critic_score")
    scores: dict[str, DimensionScore] = {}
    if t_score is not None:
        scores["transition"] = DimensionScore(
            value=float(t_score),
            note=str(raw.get("transition_note", "")),
            source_tool="transition_judge",
            input_artifacts=tuple(raw.get("filmstrips", [])),
            context="filmstrips plus programmatic transition report",
        )
    if vc_score is not None:
        scores["visual_critic"] = DimensionScore(
            value=float(vc_score),
            note=str(raw.get("visual_critic_note", "")),
            source_tool="visual_critic",
            input_artifacts=(str(raw.get("final_screenshot", "")),),
            context="post-transition final state",
        )

    if len(scores) == len(schema.dimensions):
        result = AuditResult(
            schema_id=schema.id, status="passed",
            provenance=prov, scores=scores, result_flags=(),
        )
        return result.with_composite(policy="complete_only")

    result = AuditResult(
        schema_id=schema.id, status="incomplete",
        provenance=prov, scores=scores, result_flags=("incomplete-audit",),
    )
    return result.with_composite(policy="renormalize_partial")
