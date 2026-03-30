#!/usr/bin/env python3
"""Iterate on a single block to reduce code size while preserving quality.

Autoresearch-style loop: propose compaction → audit → keep/discard → repeat.

Usage:
  python3 scripts/iterate-block.py --target 47-hierarchical-edge-bundling --block-set v2-claude-opus-4-6
  python3 scripts/iterate-block.py --target 47-hierarchical-edge-bundling --block-set v2-claude-opus-4-6 --max-experiments 20
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from iterate_lib import (
    PROJ, CostTracker, append_tsv, check_convergence, decide_block,
    ensure_iterations_dir, generate_progress_html, git_branch_name,
    git_commit, git_create_branch, git_discard, git_sha, next_experiment_id,
    render_block, update_best, write_experiment,
)

MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
PROPOSER_TEMPLATE = (PROJ / "scripts" / "proposer-prompts" / "block.md").read_text()
CLAUDE_BIN = shutil.which("claude") or "/usr/local/share/npm-global/bin/claude"


def find_block(target):
    for b in MANIFEST["blocks"]:
        if b["id"] == target:
            return b
    return None


def get_audit_scores(html_path, block_id, wait_for="svg", model="sonnet"):
    """Render + audit a single block. Returns scores dict or None."""
    ss_dir = PROJ / "temp" / "audit-screenshots" / "iterate"
    ss_dir.mkdir(parents=True, exist_ok=True)
    ss_path = ss_dir / f"{block_id}.png"

    if not render_block(html_path, ss_path, wait_for):
        print(f"  Render failed for {block_id}")
        return None

    # Run audit pipeline
    audit_script = PROJ / "scripts" / "run-audit-pipeline.py"
    block_dir = html_path.parent
    bid_num = block_id.split("-")[0]

    # Clear previous audit tmp files for this block to force re-audit
    audit_tmp = PROJ / "temp" / "audit-screenshots" / "audit-tmp" / "iterate"
    if audit_tmp.exists():
        for f in audit_tmp.glob(f"{block_id}-*.json"):
            f.unlink()

    r = subprocess.run(
        ["python3", str(audit_script),
         "--blocks", bid_num,
         "--block-set", "iterate",
         "--block-dir", str(block_dir),
         "--model", model],
        capture_output=True, text=True, timeout=600, cwd=str(PROJ))

    # Find the most recent run file
    runs_dir = PROJ / "evals" / "runs"
    if not runs_dir.exists():
        return None

    run_files = sorted(runs_dir.glob("*iterate*.json"), reverse=True)
    if not run_files:
        return None

    run_data = json.loads(run_files[0].read_text())
    return run_data.get("blocks", {}).get(block_id)


def build_proposer_prompt(html_path, lines, scores, history_lines):
    """Fill in the proposer template."""
    notes = []
    for dim in ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load"):
        note = scores.get(f"{dim}_note", "")
        if note:
            notes.append(f"  {dim}: {note}")
    audit_notes = "\n".join(notes) if notes else "  (no notes)"

    history = "\n".join(history_lines[-10:]) if history_lines else "(first experiment)"

    return PROPOSER_TEMPLATE.replace("{{html_path}}", str(html_path)) \
        .replace("{{lines_before}}", str(lines)) \
        .replace("{{composite}}", str(scores.get("composite", "?"))) \
        .replace("{{visual_critic}}", str(scores.get("visual_critic", "?"))) \
        .replace("{{encoding_integrity}}", str(scores.get("encoding_integrity", "?"))) \
        .replace("{{stress_test}}", str(scores.get("stress_test", "?"))) \
        .replace("{{cognitive_load}}", str(scores.get("cognitive_load", "?"))) \
        .replace("{{audit_notes}}", audit_notes) \
        .replace("{{history}}", history)


def run_proposer(prompt, html_path):
    """Call claude -p to propose a block compaction."""
    r = subprocess.run(
        [CLAUDE_BIN, "-p", prompt,
         "--allowedTools", "Read,Write",
         "--max-turns", "10",
         "--output-format", "stream-json"],
        capture_output=True, text=True, timeout=300,
        cwd=str(html_path.parent))
    return r


def main():
    ap = argparse.ArgumentParser(description="Iterate on a block for compaction")
    ap.add_argument("--target", required=True, help="Block ID, e.g. 47-hierarchical-edge-bundling")
    ap.add_argument("--block-set", required=True, help="Source block set, e.g. v2-claude-opus-4-6")
    ap.add_argument("--max-experiments", type=int, default=15)
    ap.add_argument("--budget", type=float, default=80.0, help="Max spend in USD")
    ap.add_argument("--model", default="sonnet", help="Model for auditing")
    ap.add_argument("--convergence-discards", type=int, default=3)
    ap.add_argument("--delay", type=float, default=5.0, help="Seconds between API calls")
    args = ap.parse_args()

    block = find_block(args.target)
    if not block:
        print(f"Block {args.target} not found in manifest"); sys.exit(1)

    source_html = PROJ / "blocks" / args.block_set / f"{args.target}.html"
    if not source_html.exists():
        print(f"Source block not found: {source_html}"); sys.exit(1)

    wait_for = block.get("wait_for", "svg")

    # Set up iteration directory
    iter_dir = PROJ / "temp" / "iterate" / f"block-{args.target}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    work_html = iter_dir / f"{args.target}.html"

    # Copy source block to working location
    shutil.copy2(source_html, work_html)

    # Create git branch
    branch = f"iterate/block-{args.target}"
    git_create_branch(branch)

    cost = CostTracker(args.budget)
    ensure_iterations_dir()

    print(f"=== Block Iteration: {args.target} ===")
    print(f"Source: {args.block_set}")
    print(f"Branch: {branch}")
    print(f"Budget: ${args.budget:.0f}")
    print()

    # Establish baseline
    print("Phase 0: Baseline audit")
    baseline_scores = get_audit_scores(work_html, args.target, wait_for, args.model)
    if not baseline_scores or baseline_scores.get("composite") is None:
        print("Failed to get baseline scores. Aborting."); sys.exit(1)

    baseline_composite = baseline_scores["composite"]
    baseline_lines = len(work_html.read_text().splitlines())

    exp_id = next_experiment_id()
    append_tsv(exp_id, "block", args.target, baseline_lines, 0, "baseline", 0, "Initial baseline")
    write_experiment(exp_id, "block", args.target, {
        "lines": baseline_lines,
        "composite": baseline_composite,
        "scores": {k: baseline_scores.get(k) for k in
                   ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load", "composite")},
        "decision": "baseline",
        "git_sha": git_sha(),
    })

    print(f"  Baseline: {baseline_lines} lines, composite {baseline_composite}")
    print()

    # Collect history for proposer context
    history_lines = [f"exp {exp_id}: baseline, {baseline_lines} lines, composite {baseline_composite}"]

    current_composite = baseline_composite
    current_lines = baseline_lines

    # Main loop
    for exp_num in range(args.max_experiments):
        if cost.over_budget():
            print(f"\nBudget exhausted ({cost.summary()}). Stopping.")
            break

        if check_convergence("block", args.target, args.convergence_discards):
            print(f"\nConverged ({args.convergence_discards} consecutive discards). Stopping.")
            break

        exp_id = next_experiment_id()
        print(f"--- Experiment {exp_id} (#{exp_num + 1}/{args.max_experiments}) ---")

        # Save current state for potential rollback
        backup = work_html.read_text()

        # Build and run proposer
        prompt = build_proposer_prompt(work_html, current_lines, baseline_scores, history_lines)
        t0 = time.time()
        print("  Proposing change...", end=" ", flush=True)
        run_proposer(prompt, work_html)
        propose_time = time.time() - t0
        print(f"({propose_time:.0f}s)")

        # Check if file actually changed
        new_content = work_html.read_text()
        new_lines = len(new_content.splitlines())
        if new_content == backup:
            print("  No change made. Skipping.")
            append_tsv(exp_id, "block", args.target, new_lines, 0, "discard", 0, "No change")
            history_lines.append(f"exp {exp_id}: discard, no change")
            continue

        print(f"  Lines: {current_lines} → {new_lines} ({new_lines - current_lines:+d})")

        # Audit the modified block
        print("  Auditing...", end=" ", flush=True)
        t0 = time.time()
        new_scores = get_audit_scores(work_html, args.target, wait_for, args.model)
        audit_time = time.time() - t0
        print(f"({audit_time:.0f}s)")

        if not new_scores or new_scores.get("composite") is None:
            print("  Audit failed. Reverting.")
            work_html.write_text(backup)
            append_tsv(exp_id, "block", args.target, new_lines, 0, "discard", 0, "Audit failed")
            history_lines.append(f"exp {exp_id}: discard, audit failed")
            continue

        new_composite = new_scores["composite"]
        est_cost = 1.0  # rough per-experiment estimate
        cost.add(est_cost)

        # Decide
        decision, reason = decide_block(current_composite, new_composite, current_lines, new_lines)

        delta = new_lines - current_lines
        description = f"{reason} (composite {current_composite}→{new_composite})"

        append_tsv(exp_id, "block", args.target, new_lines, delta, decision, est_cost, description)
        write_experiment(exp_id, "block", args.target, {
            "lines_before": current_lines,
            "lines_after": new_lines,
            "composite_before": current_composite,
            "composite_after": new_composite,
            "scores": {k: new_scores.get(k) for k in
                       ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load", "composite")},
            "decision": decision,
            "reason": reason,
            "git_sha": git_sha(),
        })

        if decision == "keep":
            print(f"  KEEP: {reason}")
            # Copy improved block back to source and commit
            shutil.copy2(work_html, source_html)
            git_commit(f"iterate-block exp-{exp_id}: {reason}", [str(source_html)])
            current_composite = new_composite
            current_lines = new_lines
            baseline_scores = new_scores  # update for next proposer prompt

            # Update best-blocks.json
            update_best("block", args.target, {
                "block_set": args.block_set,
                "composite": new_composite,
                "lines": new_lines,
                "scores": {k: new_scores.get(k) for k in
                           ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load")},
                "iteration": f"exp-{exp_id}",
                "git_sha": git_sha(),
            })
        else:
            print(f"  DISCARD: {reason}")
            work_html.write_text(backup)

        history_lines.append(f"exp {exp_id}: {decision}, {new_lines} lines, composite {new_composite}, {reason}")

        if args.delay > 0:
            time.sleep(args.delay)

    # Generate progress
    progress = generate_progress_html()

    print(f"\n=== Done ===")
    print(f"Final: {current_lines} lines (was {baseline_lines}), composite {current_composite}")
    print(f"Cost: {cost.summary()}")
    if progress:
        print(f"Progress: {progress}")


if __name__ == "__main__":
    main()
