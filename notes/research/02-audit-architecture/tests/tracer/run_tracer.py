"""Tracer-bullet driver — exercise scripts/audit/ end-to-end on two blocks.

Produces:
  - tests/tracer/run.json          — treatment Run
  - tests/tracer/baseline.json     — synthetic baseline Run (for compare)
  - tests/tracer/comparison.json   — ComparisonResult

Run once after the package and rendered screenshots are in place:
  python3 notes/research/02-audit-architecture/tests/tracer/run_tracer.py

Stub mode is enabled per the synthesis tracer rules. Real screenshots are
captured by the same code path used by scripts/run-audit-pipeline.py;
per-dimension scores are hand-supplied because running four LLM audits per
block ran beyond the tracer's time budget. Stubs are documented in the
tracer report.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJ))

from scripts.audit import (
    AuditProvenance,
    AuditResult,
    DimensionScore,
    Run,
    compare,
    PairingPolicy,
)
from scripts.audit.evaluator import EvaluationContext, evaluate as dispatch_evaluate
from scripts.audit.evaluators import general, transition


TRACER_DIR = Path(__file__).resolve().parent
RUN_PATH = TRACER_DIR / "run.json"
BASELINE_PATH = TRACER_DIR / "baseline.json"
COMPARISON_PATH = TRACER_DIR / "comparison.json"


def git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJ),
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def block_sha(block_id: str) -> str:
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", f"blocks/{block_id}.html"],
            capture_output=True, text=True, cwd=str(PROJ),
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    sha = git_sha()
    skill_shas = {"visual_critic": "v2-tracer", "encoding_integrity": "v2-tracer",
                  "cognitive_load": "v2-tracer", "stress_test": "v2-tracer"}

    # === Treatment run: real package, real renders, stubbed scores ===
    gen_ctx = EvaluationContext(
        block_id="02-linked-scatterplot-matrix",
        fixture_id="default",
        generator_model="claude-opus-4-6",
        judge_model="claude-sonnet-4-6",
        block_sha=block_sha("02-linked-scatterplot-matrix"),
        skill_shas=skill_shas,
        stub=True,
    )
    trans_ctx = EvaluationContext(
        block_id="hierarchy-bundles",
        fixture_id="hierarchy-bundles-default",
        generator_model="claude-opus-4-6",
        judge_model="claude-sonnet-4-6",
        block_sha=block_sha("hierarchy-bundles"),
        skill_shas=skill_shas,
        stub=True,
    )
    gen_result = general.evaluate(PROJ / "blocks" / "02-linked-scatterplot-matrix.html", gen_ctx)
    trans_result = transition.evaluate(PROJ / "blocks" / "hierarchy-bundles.html", trans_ctx)

    treatment = Run(
        run_id=f"{now_iso()}-tracer-treatment",
        timestamp=now_iso(),
        git_sha=sha,
        default_skill_shas=skill_shas,
        results=(gen_result, trans_result),
    )
    treatment.write(RUN_PATH)
    print(f"  wrote {RUN_PATH.relative_to(PROJ)}")

    # === Synthetic baseline ===
    # Same keys (block_id/fixture_id/schema/generator/judge/evaluator), slightly
    # different scores and a different stress_test flag so compare() has signal.
    base_gen_scores = dict(gen_result.scores)
    base_gen_scores["visual_critic"] = DimensionScore(
        value=7.2, source_tool="visual_critic",
        input_artifacts=gen_result.scores["visual_critic"].input_artifacts,
        context="baseline",
    )
    base_gen_scores["stress_test"] = DimensionScore(
        value=6.5, source_tool="stress_test",
        flags=("Stale Closure",),  # treatment has Update Storm
        context="baseline",
    )
    base_gen = AuditResult(
        schema_id="general", status="passed",
        provenance=AuditProvenance(**{**gen_result.provenance.to_dict(),
                                       "timestamp": "2026-04-28T18:00:00Z"}),
        scores=base_gen_scores,
    ).with_composite()

    base_trans_scores = {
        "transition": DimensionScore(value=6.8, source_tool="transition_judge", context="baseline"),
        "visual_critic": DimensionScore(value=7.0, source_tool="visual_critic", context="baseline"),
    }
    base_trans = AuditResult(
        schema_id="transition", status="passed",
        provenance=AuditProvenance(**{**trans_result.provenance.to_dict(),
                                       "timestamp": "2026-04-28T18:05:00Z"}),
        scores=base_trans_scores,
    ).with_composite()

    baseline = Run(
        run_id=f"{now_iso()}-tracer-baseline",
        timestamp="2026-04-28T18:00:00Z",
        git_sha=sha,
        default_skill_shas=skill_shas,
        results=(base_gen, base_trans),
    )
    baseline.write(BASELINE_PATH)
    print(f"  wrote {BASELINE_PATH.relative_to(PROJ)}")

    # === compare() ===
    cmp = compare(baseline, treatment, tolerance=0.5)
    COMPARISON_PATH.write_text(json.dumps(cmp.to_dict(), indent=2, ensure_ascii=False))
    print(f"  wrote {COMPARISON_PATH.relative_to(PROJ)}  verdict={cmp.verdict}")

    # === Demonstrate schema-mismatch refusal at the inner level ===
    # ResultKey carries schema_id, so a true cross-schema collision can't pair
    # at the outer level — _diff_pair is the load-bearing refusal.
    from scripts.audit.compare import _diff_pair
    try:
        _diff_pair(base_gen, base_trans)
    except ValueError as e:
        print(f"  schema-mismatch refusal: OK ({e!s})")

    # === Demonstrate unpaired refusal vs allow_unpaired=True ===
    drift = Run(
        run_id="drift", timestamp=now_iso(), git_sha=sha,
        default_skill_shas=skill_shas,
        results=(base_gen,),  # missing transition
    )
    try:
        compare(treatment, drift)
    except ValueError as e:
        print(f"  unpaired-default refusal: OK")
    cmp_unpaired = compare(treatment, drift, allow_unpaired=True)
    assert cmp_unpaired.verdict == "inconclusive", cmp_unpaired.verdict
    print(f"  unpaired-allowed: verdict={cmp_unpaired.verdict}, "
          f"missing_baseline={len(cmp_unpaired.missing_baseline)}, "
          f"missing_treatment={len(cmp_unpaired.missing_treatment)}")

    # === Demonstrate v1 legacy refusal ===
    try:
        Run.from_dict({"timestamp": "2026", "git_sha": "x", "blocks": {}})
    except ValueError as e:
        print(f"  legacy-v1 refusal: OK")


if __name__ == "__main__":
    main()
