#!/usr/bin/env python3
"""
Eval runner for D3 Power Tools skills.

Measures whether skills improve Claude's D3 output by running each prompt
with and without skills, then comparing render success and structural quality.

Usage:
  python3 evals/run-evals.py                           # run all evals
  python3 evals/run-evals.py --id scatter-10k-brush    # run one eval
  python3 evals/run-evals.py --baseline-only           # skip with-skill runs
  python3 evals/run-evals.py --skill-only              # skip baseline runs
  python3 evals/run-evals.py --runs 3                  # multiple runs for variance

Results go to evals/results/ (configurable in eval.config.json).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
TEST_SCRIPT = PROJECT_ROOT / "scripts" / "test-viz.py"


def load_config(path):
    with open(path) as f:
        return json.load(f)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def run_claude(prompt, output_file, *, cwd, model="sonnet", timeout=120):
    """Run a prompt through claude -p and extract the HTML output."""
    # Instruct Claude to write the file directly
    full_prompt = (
        f"Create a file at {output_file}. "
        f"{prompt} "
        f"Write ONLY the HTML file — no explanation, no follow-up."
    )

    cmd = [
        "claude", "-p", full_prompt,
        "--output-format", "json",
        "--model", model,
        "--permission-mode", "bypassPermissions",
        "--max-turns", "25",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "duration_ms": timeout * 1000}

    # Parse JSON output
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return {
            "ok": False,
            "error": "json_parse_failed",
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500],
        }

    ok = not data.get("is_error", True) and Path(output_file).exists()

    return {
        "ok": ok,
        "duration_ms": data.get("duration_ms", 0),
        "cost_usd": data.get("total_cost_usd", 0),
        "num_turns": data.get("num_turns", 0),
        "error": data.get("result", "")[:300] if not ok else None,
    }


def run_test_viz(html_file, *, wait_for="svg", interactions=None,
                 screenshot=None, width=1200, height=800, timeout=10000):
    """Run test-viz.py on a generated HTML file. Returns check results."""
    cmd = [
        sys.executable, str(TEST_SCRIPT),
        str(html_file),
        "--width", str(width),
        "--height", str(height),
        "--timeout", str(timeout),
    ]

    if wait_for:
        cmd += ["--wait-for", wait_for]
    if screenshot:
        cmd += ["--out", str(screenshot)]
    if interactions:
        cmd += ["--interactions", ",".join(interactions)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        passed = result.returncode == 0
        # Extract check counts from output like "PASS  7/7"
        match = re.search(r"(\d+)/(\d+)", result.stdout)
        checks_passed = int(match.group(1)) if match else 0
        checks_total = int(match.group(2)) if match else 0
    except (subprocess.TimeoutExpired, Exception) as e:
        passed = False
        checks_passed = 0
        checks_total = 0

    return {
        "passed": passed,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
    }


def run_structural_checks(html_file, checks):
    """Grep the HTML file for expected patterns. Returns dict of check → bool."""
    if not Path(html_file).exists():
        return {name: False for name in checks}

    content = Path(html_file).read_text(errors="replace")
    results = {}
    for name, pattern in checks.items():
        # Support | for OR patterns
        if "|" in pattern and not pattern.startswith("<"):
            results[name] = bool(re.search(pattern, content, re.IGNORECASE))
        else:
            results[name] = pattern.lower() in content.lower()
    return results


def create_bare_project(output_dir):
    """Create a minimal project dir with no skills for baseline runs."""
    bare = Path(output_dir) / "_bare_project"
    if bare.exists():
        shutil.rmtree(bare)
    bare.mkdir(parents=True)

    # Minimal CLAUDE.md so Claude knows it's a D3 project
    claude_md = bare / ".claude"
    claude_md.mkdir()
    (claude_md / "CLAUDE.md").write_text(
        "# Project\nBuild D3.js visualizations. Use D3 v7 from CDN. "
        "Produce self-contained HTML files.\n"
    )
    return bare


def run_single_eval(eval_cfg, defaults, output_dir, model, mode="with-skill"):
    """Run one eval prompt. mode is 'with-skill' or 'baseline'."""
    eval_id = eval_cfg["id"]
    run_dir = Path(output_dir) / eval_id / mode
    ensure_dir(run_dir)

    html_file = run_dir / "output.html"
    screenshot = run_dir / "screenshot.png"

    # Choose working directory
    if mode == "with-skill":
        cwd = PROJECT_ROOT
    else:
        cwd = create_bare_project(output_dir)

    timeout = eval_cfg.get("timeout", defaults.get("timeout", 120))

    # Step 1: Generate
    print(f"  generating ({mode})...", end=" ", flush=True)
    gen_result = run_claude(
        eval_cfg["prompt"], str(html_file),
        cwd=cwd, model=model, timeout=timeout,
    )

    if not gen_result["ok"]:
        print(f"FAIL ({gen_result.get('error', 'unknown')[:60]})")
        return {
            "mode": mode,
            "generated": False,
            "error": gen_result.get("error", "unknown"),
            "duration_ms": gen_result.get("duration_ms", 0),
            "cost_usd": gen_result.get("cost_usd", 0),
            "render": None,
            "structural": {},
        }

    duration = gen_result["duration_ms"]
    cost = gen_result.get("cost_usd", 0)
    print(f"ok ({duration / 1000:.1f}s, ${cost:.3f})", flush=True)

    # Step 2: Render test
    wait_for = eval_cfg.get("wait_for", defaults.get("wait_for", "svg"))
    interactions = eval_cfg.get("interactions", [])
    width = eval_cfg.get("width", defaults.get("width", 1200))
    height = eval_cfg.get("height", defaults.get("height", 800))

    print(f"  testing render...", end=" ", flush=True)
    render = run_test_viz(
        html_file, wait_for=wait_for, interactions=interactions,
        screenshot=str(screenshot), width=width, height=height,
    )
    status = "PASS" if render["passed"] else "FAIL"
    print(f"{status} ({render['checks_passed']}/{render['checks_total']})")

    # Step 3: Structural checks
    checks_cfg = eval_cfg.get("structural_checks", {})
    structural = run_structural_checks(html_file, checks_cfg)
    hit = sum(structural.values())
    total = len(structural)
    if total > 0:
        print(f"  structural: {hit}/{total}", end="")
        missed = [k for k, v in structural.items() if not v]
        if missed:
            print(f"  (missing: {', '.join(missed)})", end="")
        print()

    return {
        "mode": mode,
        "generated": True,
        "duration_ms": duration,
        "cost_usd": cost,
        "render": render,
        "structural": structural,
    }


def print_report(results, output_dir):
    """Print a summary report and save as JSON."""
    print("\n" + "=" * 64)
    print("  EVAL RESULTS")
    print("=" * 64)

    total_cost = 0
    summary_rows = []

    for eval_id, runs in results.items():
        print(f"\n  {eval_id}")
        print(f"  {'─' * 58}")

        for run in runs:
            mode = run["mode"]
            total_cost += run.get("cost_usd", 0)

            if not run["generated"]:
                print(f"    {mode:14s}  GENERATION FAILED: {run.get('error', '')[:50]}")
                continue

            render_ok = run["render"]["passed"] if run["render"] else False
            render_str = "PASS" if render_ok else "FAIL"
            checks = run["render"]["checks_passed"] if run["render"] else 0
            total = run["render"]["checks_total"] if run["render"] else 0

            struct = run.get("structural", {})
            struct_hit = sum(struct.values())
            struct_total = len(struct)

            duration_s = run["duration_ms"] / 1000

            print(
                f"    {mode:14s}  render: {render_str} ({checks}/{total})  "
                f"structural: {struct_hit}/{struct_total}  "
                f"({duration_s:.0f}s, ${run.get('cost_usd', 0):.3f})"
            )

        # Compute delta if both modes present
        with_skill = next((r for r in runs if r["mode"] == "with-skill"), None)
        baseline = next((r for r in runs if r["mode"] == "baseline"), None)

        if with_skill and baseline and with_skill["generated"] and baseline["generated"]:
            ws = sum(with_skill.get("structural", {}).values())
            bs = sum(baseline.get("structural", {}).values())
            delta = ws - bs
            sign = "+" if delta > 0 else ""
            wr = with_skill["render"]["passed"] if with_skill["render"] else False
            br = baseline["render"]["passed"] if baseline["render"] else False

            verdict = "BETTER" if (ws > bs or (wr and not br)) else \
                      "SAME" if (ws == bs and wr == br) else "WORSE"

            print(f"    {'delta':14s}  structural: {sign}{delta}  → {verdict}")

    print(f"\n  Total cost: ${total_cost:.3f}")
    print(f"  Results saved to: {output_dir}")
    print()

    # Save raw results
    report_path = Path(output_dir) / "results.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Run D3 skill evals")
    parser.add_argument("--config", default=str(SCRIPT_DIR / "eval.config.json"),
                        help="Eval config file")
    parser.add_argument("--id", help="Run only this eval ID")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Only run baseline (no-skill) evals")
    parser.add_argument("--skill-only", action="store_true",
                        help="Only run with-skill evals")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of runs per eval (for variance measurement)")
    parser.add_argument("--model", help="Override model (default from config)")
    args = parser.parse_args()

    config = load_config(args.config)
    config_dir = Path(args.config).parent
    output_dir = ensure_dir(config_dir / config.get("output_dir", "results"))
    model = args.model or config.get("model", "sonnet")
    defaults = config.get("defaults", {})

    evals = config["evals"]
    if args.id:
        evals = [e for e in evals if e["id"] == args.id]
        if not evals:
            print(f"No eval found with id '{args.id}'")
            sys.exit(1)

    modes = []
    if not args.baseline_only:
        modes.append("with-skill")
    if not args.skill_only:
        modes.append("baseline")

    print(f"Running {len(evals)} eval(s) × {len(modes)} mode(s) × {args.runs} run(s)")
    print(f"Model: {model}")
    print(f"Output: {output_dir}")
    print()

    all_results = {}

    for eval_cfg in evals:
        eval_id = eval_cfg["id"]
        print(f"[{eval_id}]")
        runs = []

        for run_num in range(args.runs):
            for mode in modes:
                run_label = f"{mode}" if args.runs == 1 else f"{mode}-run{run_num + 1}"

                # For multiple runs, use separate directories
                effective_mode = run_label if args.runs > 1 else mode

                result = run_single_eval(eval_cfg, defaults, output_dir, model, effective_mode)
                result["run_num"] = run_num
                runs.append(result)

        all_results[eval_id] = runs
        print()

    print_report(all_results, output_dir)


if __name__ == "__main__":
    main()
