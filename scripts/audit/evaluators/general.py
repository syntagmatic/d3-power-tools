"""General evaluator — wraps the four-dimension inspection suite.

Real mode: renders the block, captures a screenshot, and runs each
inspection skill (visual_critic, encoding_integrity, cognitive_load,
stress_test) via `claude -p` exactly as scripts/run-audit-pipeline.py does.

Stub mode (ctx.stub=True): returns a structurally-valid AuditResult with
hand-supplied scores. Used by the tracer to exercise the data layer
without the cost of four LLM calls per block. The synthesis explicitly
permits this for tracer-bullet validation; production graduation runs
must set stub=False.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from ..result import AuditProvenance, AuditResult, DimensionScore
from ..schema import GENERAL


PROJ = Path(__file__).resolve().parent.parent.parent.parent
TEST_SCRIPT = PROJ / "scripts" / "test-viz.py"
SCREENSHOT_DIR = PROJ / "temp" / "audit-screenshots" / "v2-tracer"

CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kai/.local/bin/claude"

TOOLS = {
    "visual_critic":      PROJ / "meta" / "visual-critic" / "SKILL.md",
    "encoding_integrity": PROJ / "meta" / "encoding-integrity" / "SKILL.md",
    "cognitive_load":     PROJ / "meta" / "cognitive-load" / "SKILL.md",
    "stress_test":        PROJ / "meta" / "stress-test" / "SKILL.md",
}


id = "general"
schema = GENERAL


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render(html_path: Path, ss_path: Path, *, wait_for: str = "svg") -> bool:
    ss_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            ["python3", str(TEST_SCRIPT), str(html_path),
             "--out", str(ss_path), "--wait-for", wait_for],
            capture_output=True, text=True, timeout=30, cwd=str(PROJ),
        )
    except subprocess.TimeoutExpired:
        return False
    return ss_path.exists() and ss_path.stat().st_size > 0


def _build_prompt(tool_name: str, skill_md: str, ss: Path, html: Path, out: Path) -> str:
    if tool_name == "stress_test":
        fmt = '{"score":<1-10>,"flags":["<failed_check_names>"],"note":"<1 sentence>"}'
    else:
        fmt = '{"score":<1-10>,"note":"<1 sentence what works or doesn\'t>"}'
    return (
        f"Evaluate this D3.js visualization.\n\n"
        f"## Criteria\n{skill_md}\n\n"
        f"## Task\n"
        f"1. Read the screenshot at {ss}\n"
        f"2. Read the HTML source at {html}\n"
        f"3. Score 1-10 per the criteria. Write JSON to {out}\n\n"
        f"Format: {fmt}\nWrite the file now. No markdown, no explanation."
    )


def _call_tool(tool: str, ss: Path, html: Path, model: str) -> dict | None:
    skill = TOOLS[tool].read_text()
    bare = tempfile.mkdtemp(prefix=f"v2-audit-{tool}-")
    out = Path(bare) / "out.json"
    prompt = _build_prompt(tool, skill, ss, html, out)
    try:
        subprocess.run(
            [CLAUDE_BIN, "-p", prompt,
             "--allowedTools", "Read,Write",
             "--max-turns", "25",
             "--model", model,
             "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=180, cwd=bare,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if not out.exists() or out.stat().st_size <= 5:
        return None
    try:
        return json.loads(out.read_text())
    except json.JSONDecodeError:
        return None


def _stubbed_scores(ctx) -> dict[str, DimensionScore]:
    return {
        "visual_critic": DimensionScore(
            value=7.0,
            note="Stubbed score for tracer-bullet validation.",
            flags=(),
            source_tool="visual_critic",
            input_artifacts=("temp/audit-screenshots/v2-tracer/" + ctx.block_id + ".png",),
            context="stub-mode tracer; not a real audit",
        ),
        "encoding_integrity": DimensionScore(
            value=8.0,
            note="Stubbed score for tracer-bullet validation.",
            source_tool="encoding_integrity",
            context="stub-mode tracer; not a real audit",
        ),
        "cognitive_load": DimensionScore(
            value=7.0,
            note="Stubbed score for tracer-bullet validation.",
            source_tool="cognitive_load",
            context="stub-mode tracer; not a real audit",
        ),
        "stress_test": DimensionScore(
            value=6.0,
            note="Stubbed score for tracer-bullet validation.",
            flags=("Update Storm",),
            source_tool="stress_test",
            context="stub-mode tracer; not a real audit",
        ),
    }


def evaluate(html_path: Path, ctx) -> AuditResult:
    """Produce an AuditResult for the four-dimension general schema.

    Real mode: render → audit each tool → assemble.
    Stub mode (ctx.stub): skip render and produce hand-supplied scores.
    Renders that fail produce status='render_failed' with a result_flag.
    """
    prov = AuditProvenance(
        block_id=ctx.block_id,
        fixture_id=ctx.fixture_id,
        generator_model=ctx.generator_model,
        judge_model=ctx.judge_model,
        evaluator_id=id,
        block_sha=ctx.block_sha,
        timestamp=_now_iso(),
        skill_shas=ctx.skill_shas,
    )

    if ctx.stub:
        scores = _stubbed_scores(ctx)
        result = AuditResult(
            schema_id=schema.id,
            status="passed",
            provenance=prov,
            scores=scores,
            result_flags=(),
        )
        return result.with_composite(policy="complete_only")

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ss = SCREENSHOT_DIR / f"{ctx.block_id}.png"
    rendered = _render(html_path, ss)
    if not rendered:
        return AuditResult(
            schema_id=schema.id,
            status="render_failed",
            provenance=prov,
            scores={},
            result_flags=("render-error",),
        )

    scores: dict[str, DimensionScore] = {}
    for tool in TOOLS:
        data = _call_tool(tool, ss, html_path, ctx.judge_model)
        if data is None or "score" not in data:
            continue
        scores[tool] = DimensionScore(
            value=float(data["score"]),
            note=str(data.get("note", "")),
            flags=tuple(data.get("flags", [])) if tool == "stress_test" else (),
            source_tool=tool,
            input_artifacts=(str(ss.relative_to(PROJ)),),
            context="single rendered screenshot",
        )

    if len(scores) == len(TOOLS):
        result = AuditResult(
            schema_id=schema.id,
            status="passed",
            provenance=prov,
            scores=scores,
            result_flags=(),
        )
        return result.with_composite(policy="complete_only")

    # Partial: status=incomplete, renormalize_partial
    result = AuditResult(
        schema_id=schema.id,
        status="incomplete",
        provenance=prov,
        scores=scores,
        result_flags=("incomplete-audit",),
    )
    return result.with_composite(policy="renormalize_partial")
