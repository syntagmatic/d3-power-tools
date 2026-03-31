#!/usr/bin/env python3
"""Iterate on a single block to reduce code size while preserving quality.

Autoresearch-style loop: propose compaction → audit → keep/discard → repeat.
Uses a git worktree so the main working tree stays on its current branch.

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
    PROJ, append_tsv, check_convergence, compute_diff, decide_block,
    ensure_iterations_dir, generate_progress_html, git_commit, git_sha,
    git_squash_merge, next_experiment_id, render_block, update_best,
    worktree_create, worktree_is_active, worktree_remove, write_experiment,
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

    # Clear previous audit tmp files for this block to force re-audit
    audit_tmp = PROJ / "temp" / "audit-screenshots" / "audit-tmp" / "iterate"
    if audit_tmp.exists():
        for f in audit_tmp.glob(f"{block_id}-*.json"):
            f.unlink()

    r = subprocess.run(
        ["python3", str(audit_script),
         "--blocks", block_id,
         "--block-set", "iterate",
         "--block-dir", str(block_dir),
         "--model", model],
        capture_output=True, text=True, timeout=600, cwd=str(PROJ))

    if r.returncode != 0 or "FAIL" in (r.stdout or ""):
        print(f"  Audit pipeline output: {(r.stdout or '')[-300:]}")
        if r.stderr:
            print(f"  Audit pipeline stderr: {r.stderr[-300:]}")

    # Find the most recent run file
    runs_dir = PROJ / "evals" / "runs"
    if not runs_dir.exists():
        return None

    run_files = sorted(runs_dir.glob("*iterate*.json"), reverse=True)
    if not run_files:
        return None

    run_data = json.loads(run_files[0].read_text())
    scores = run_data.get("blocks", {}).get(block_id)

    # If composite is None (e.g. one audit dimension failed), compute from available scores
    if scores and scores.get("composite") is None:
        weights = {"visual_critic": 0.30, "encoding_integrity": 0.25,
                   "cognitive_load": 0.25, "stress_test": 0.20}
        available = {k: scores[k] for k in weights if scores.get(k) is not None}
        if available:
            total_w = sum(weights[k] for k in available)
            scores["composite"] = round(sum(scores[k] * weights[k] / total_w for k in available), 1)

    return scores


def build_proposer_prompt(html_path, lines, scores, history_lines, last_discard_scores=None):
    """Fill in the proposer template."""
    notes = []
    for dim in ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load"):
        note = scores.get(f"{dim}_note", "")
        if note:
            notes.append(f"  {dim} ({scores.get(dim, '?')}/10): {note}")
    flags = scores.get("flags", [])
    if flags:
        notes.append(f"  flags: {'; '.join(flags)}")
    audit_notes = "\n".join(notes) if notes else "  (no notes)"

    # If the last experiment was discarded, show why
    discard_context = ""
    if last_discard_scores:
        discard_notes = []
        for dim in ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load"):
            before = scores.get(dim, "?")
            after = last_discard_scores.get(dim, "?")
            if before != after:
                note = last_discard_scores.get(f"{dim}_note", "")
                discard_notes.append(f"  {dim}: {before}→{after}" + (f" — {note}" if note else ""))
        if discard_notes:
            discard_context = "\n\nLast experiment was DISCARDED (quality regression):\n" + "\n".join(discard_notes)

    history = "\n".join(history_lines[-10:]) if history_lines else "(first experiment)"

    return PROPOSER_TEMPLATE.replace("{{html_path}}", str(html_path)) \
        .replace("{{lines_before}}", str(lines)) \
        .replace("{{composite}}", str(scores.get("composite", "?"))) \
        .replace("{{visual_critic}}", str(scores.get("visual_critic", "?"))) \
        .replace("{{encoding_integrity}}", str(scores.get("encoding_integrity", "?"))) \
        .replace("{{stress_test}}", str(scores.get("stress_test", "?"))) \
        .replace("{{cognitive_load}}", str(scores.get("cognitive_load", "?"))) \
        .replace("{{audit_notes}}", audit_notes + discard_context) \
        .replace("{{history}}", history)


def run_proposer(prompt, html_path):
    """Call claude -p to propose a block compaction. Returns explanation string."""
    r = subprocess.run(
        [CLAUDE_BIN, "-p", prompt,
         "--allowedTools", "Read,Edit,Write",
         "--max-turns", "10",
         "--output-format", "json"],
        capture_output=True, text=True, timeout=300,
        cwd=str(html_path.parent))
    try:
        return json.loads(r.stdout).get("result", "")
    except (json.JSONDecodeError, ValueError):
        return ""


def main():
    ap = argparse.ArgumentParser(description="Iterate on a block for compaction")
    ap.add_argument("--target", required=True, help="Block ID, e.g. 47-hierarchical-edge-bundling")
    ap.add_argument("--block-set", default=None, help="Source block set (default: flat blocks/ dir)")
    ap.add_argument("--max-experiments", type=int, default=15)
    ap.add_argument("--model", default="sonnet", help="Model for auditing")
    ap.add_argument("--convergence-discards", type=int, default=3)
    ap.add_argument("--delay", type=float, default=5.0, help="Seconds between API calls")
    args = ap.parse_args()

    block = find_block(args.target)
    if not block:
        print(f"Block {args.target} not found in manifest"); sys.exit(1)

    if args.block_set:
        source_html = PROJ / "blocks" / args.block_set / f"{args.target}.html"
    else:
        source_html = PROJ / "blocks" / f"{args.target}.html"
    if not source_html.exists():
        print(f"Source block not found: {source_html}"); sys.exit(1)

    wait_for = block.get("wait_for", "svg")

    # Abort if another run is already iterating this target
    branch = f"iterate/block-{args.target}"
    existing = worktree_is_active(branch)
    if existing:
        print(f"ERROR: Target {args.target} is already being iterated at {existing}")
        print(f"If the previous run crashed, clean up with: git worktree remove {existing}")
        sys.exit(1)

    # Create isolated worktree for this iteration
    wt_path = worktree_create(branch)

    # source_html in the worktree (where git commits will land)
    if args.block_set:
        wt_source = wt_path / "blocks" / args.block_set / f"{args.target}.html"
    else:
        wt_source = wt_path / "blocks" / f"{args.target}.html"

    # Working copy in temp/ (not tracked, used by proposer and auditor)
    iter_dir = PROJ / "temp" / "iterate" / f"block-{args.target}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    work_html = iter_dir / f"{args.target}.html"
    shutil.copy2(source_html, work_html)

    ensure_iterations_dir()

    print(f"=== Block Iteration: {args.target} ===")
    print(f"Source: {args.block_set or 'blocks/'}")
    print(f"Branch: {branch}")
    print(f"Worktree: {wt_path}")
    print()

    # Establish baseline
    print("Phase 0: Baseline audit")
    baseline_scores = get_audit_scores(work_html, args.target, wait_for, args.model)
    if not baseline_scores or baseline_scores.get("composite") is None:
        print("Failed to get baseline scores. Aborting.")
        worktree_remove(wt_path)
        sys.exit(1)

    baseline_composite = baseline_scores["composite"]
    baseline_lines = len(work_html.read_text().splitlines())

    exp_id = next_experiment_id()
    append_tsv(exp_id, "block", args.target, baseline_lines, 0, "baseline", "Initial baseline")
    write_experiment(exp_id, "block", args.target, {
        "lines": baseline_lines,
        "composite": baseline_composite,
        "scores": {k: baseline_scores.get(k) for k in
                   ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load", "composite",
                    "visual_critic_note", "encoding_integrity_note", "stress_test_note", "cognitive_load_note")
                   if baseline_scores.get(k) is not None},
        "decision": "baseline",
        "git_sha": git_sha(),
    })

    print(f"  Baseline: {baseline_lines} lines, composite {baseline_composite}")
    print()

    # Collect history for proposer context
    history_lines = [f"exp {exp_id}: baseline, {baseline_lines} lines, composite {baseline_composite}"]

    current_composite = baseline_composite
    current_lines = baseline_lines
    keeps = 0
    last_discard_scores = None

    # Main loop
    for exp_num in range(args.max_experiments):
        if check_convergence("block", args.target, args.convergence_discards):
            print(f"\nConverged ({args.convergence_discards} consecutive discards). Stopping.")
            break

        exp_id = next_experiment_id()
        print(f"--- Experiment {exp_id} (#{exp_num + 1}/{args.max_experiments}) ---")

        # Save current state for potential rollback
        backup = work_html.read_text()

        # Build and run proposer
        prompt = build_proposer_prompt(work_html, current_lines, baseline_scores, history_lines, last_discard_scores)
        t0 = time.time()
        print("  Proposing change...", end=" ", flush=True)
        proposer_explanation = run_proposer(prompt, work_html)
        propose_time = time.time() - t0
        print(f"({propose_time:.0f}s)")

        # Check if file actually changed
        new_content = work_html.read_text()
        new_lines = len(new_content.splitlines())
        if new_content == backup:
            print("  No change made. Skipping.")
            append_tsv(exp_id, "block", args.target, new_lines, 0, "discard", "No change")
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
            append_tsv(exp_id, "block", args.target, new_lines, 0, "discard", "Audit failed")
            history_lines.append(f"exp {exp_id}: discard, audit failed")
            continue

        new_composite = new_scores["composite"]

        # Decide
        decision, reason = decide_block(current_composite, new_composite, current_lines, new_lines)

        delta = new_lines - current_lines
        description = f"{reason} (composite {current_composite}→{new_composite})"

        # Compute diff for history regardless of decision
        diff_text = compute_diff(backup, new_content, f"{args.target}.html")

        append_tsv(exp_id, "block", args.target, new_lines, delta, decision, description)
        write_experiment(exp_id, "block", args.target, {
            "lines_before": current_lines,
            "lines_after": new_lines,
            "composite_before": current_composite,
            "composite_after": new_composite,
            "scores": {k: new_scores.get(k) for k in
                       ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load", "composite",
                        "visual_critic_note", "encoding_integrity_note", "stress_test_note", "cognitive_load_note",
                        "flags")
                       if new_scores.get(k) is not None},
            "propose_time_s": round(propose_time, 1),
            "audit_time_s": round(audit_time, 1),
            "decision": decision,
            "reason": reason,
            "diff": diff_text,
            "proposer": proposer_explanation,
            "git_sha": git_sha(),
        })

        if decision == "keep":
            print(f"  KEEP: {reason}")
            # Copy improved block to worktree source (committed later)
            shutil.copy2(work_html, wt_source)
            current_composite = new_composite
            current_lines = new_lines
            baseline_scores = new_scores  # update for next proposer prompt
            keeps += 1
            last_discard_scores = None  # clear discard context on keep

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
            last_discard_scores = new_scores  # tell proposer what went wrong

        history_lines.append(f"exp {exp_id}: {decision}, {new_lines} lines, composite {new_composite}, {reason}")

        if args.delay > 0:
            time.sleep(args.delay)

    # Generate index
    progress = generate_progress_html()

    # Commit in worktree and squash-merge back to main
    if keeps > 0:
        # Commit the modified block in the worktree
        wt_rel_source = f"blocks/{args.block_set}/{args.target}.html"
        git_commit(
            f"iterate-block {args.target}: {baseline_lines}→{current_lines} lines, {keeps} keeps",
            [wt_rel_source], cwd=str(wt_path))

        # Squash-merge to main (operates from PROJ)
        merge_msg = (f"Iterate block {args.target}: {baseline_lines}→{current_lines} lines "
                     f"({keeps} keeps, composite {baseline_composite}→{current_composite})")
        print(f"\n  Squash-merging to main...")
        if git_squash_merge(branch, "main", merge_msg):
            print(f"  Merged: {merge_msg}")
        else:
            print(f"  Squash-merge failed. Changes remain on branch: {branch}")

        # Commit evals artifacts on main
        artifacts = []
        evals_dir = PROJ / "evals"
        for pattern in ["iterations/", "runs/", "best-blocks.json"]:
            p = evals_dir / pattern
            if p.exists():
                artifacts.append(str(p))
        if progress:
            artifacts.append(str(progress))
        if artifacts:
            git_commit(f"Add iteration artifacts for {args.target}", artifacts)

    # Clean up worktree
    worktree_remove(wt_path)

    print(f"\n=== Done ===")
    print(f"Final: {current_lines} lines (was {baseline_lines}), composite {current_composite}")
    if progress:
        print(f"Progress: {progress}")


if __name__ == "__main__":
    main()
