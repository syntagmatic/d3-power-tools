#!/usr/bin/env python3
"""Iterate on a prompt to reduce generation time while preserving required features.

Autoresearch-style loop: rewrite prompt → generate → check features → keep/discard → repeat.

Usage:
  python3 scripts/iterate-prompt.py --target 47-hierarchical-edge-bundling --block-set v2-claude-opus-4-6 \
    --features "d3.cluster|d3.tree" "d3.curveBundle|bundle" "transition"
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from iterate_lib import (
    PROJ, CostTracker, append_tsv, check_convergence, check_features,
    decide_prompt, ensure_iterations_dir, generate_progress_html,
    git_commit, git_create_branch, git_sha, next_experiment_id,
    update_best, write_experiment,
)
from staging import create_staging_dir, cleanup_staging_dir

MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
PROPOSER_TEMPLATE = (PROJ / "scripts" / "proposer-prompts" / "prompt.md").read_text()
CLAUDE_BIN = shutil.which("claude") or "/usr/local/share/npm-global/bin/claude"


def find_block(target):
    for b in MANIFEST["blocks"]:
        if b["id"] == target:
            return b
    return None


def generate_block(prompt_text, block, iter_dir, model=None):
    """Generate a block from a prompt. Returns (html_path, elapsed_s, cost) or (None, elapsed, 0)."""
    bid = block["id"]
    outfile = iter_dir / f"{bid}.html"
    if outfile.exists():
        outfile.unlink()

    suffix = MANIFEST.get("defaults", {}).get("suffix", "")
    abs_outpath = str(outfile)
    full_prompt = (
        f"Build a standalone D3.js visualization as a single HTML file.\n\n"
        f"{prompt_text}\n\n"
        f"{suffix}\n"
        f"Generate ALL synthetic data inline. No external data files.\n"
        f"Write the complete file to {abs_outpath}"
    )

    skills_list = block.get("skills", [])
    staging = create_staging_dir(bid, skills_list, PROJ, prefix="iterate-prompt")

    t0 = time.time()
    try:
        cmd = [
            CLAUDE_BIN, "-p", full_prompt,
            "--allowedTools", "Write,Read",
            "--disallowedTools", "Bash,Glob,Grep,Agent",
            "--max-turns", "25",
            "--output-format", "stream-json",
        ]
        if model:
            cmd.extend(["--model", model])

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(staging))
        elapsed = time.time() - t0

        # Parse cost from stream-json
        cost = 0
        for line in (r.stdout or "").splitlines():
            try:
                event = json.loads(line)
                if event.get("type") == "result":
                    cost = event.get("total_cost_usd", 0) or 0
            except (json.JSONDecodeError, ValueError):
                pass

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        cleanup_staging_dir(staging)
        return None, elapsed, 0
    finally:
        cleanup_staging_dir(staging)

    if outfile.exists() and outfile.stat().st_size > 100:
        return outfile, elapsed, cost
    return None, elapsed, cost


def run_proposer(current_prompt, gen_time, features, history_lines, out_path):
    """Call claude -p to propose a rewritten prompt."""
    features_list = "\n".join(f"  - `{f}`" for f in features) if features else "  (none)"
    history = "\n".join(history_lines[-10:]) if history_lines else "(first experiment)"

    prompt = PROPOSER_TEMPLATE \
        .replace("{{current_prompt}}", current_prompt) \
        .replace("{{gen_time_s}}", f"{gen_time:.0f}") \
        .replace("{{features_list}}", features_list) \
        .replace("{{history}}", history) \
        .replace("{{out_path}}", str(out_path))

    r = subprocess.run(
        [CLAUDE_BIN, "-p", prompt,
         "--allowedTools", "Read,Write",
         "--max-turns", "10",
         "--output-format", "stream-json"],
        capture_output=True, text=True, timeout=300,
        cwd=str(out_path.parent))
    return r


def main():
    ap = argparse.ArgumentParser(description="Iterate on a prompt for speed")
    ap.add_argument("--target", required=True, help="Block ID, e.g. 47-hierarchical-edge-bundling")
    ap.add_argument("--block-set", required=True, help="Source block set for reference")
    ap.add_argument("--features", nargs="+", default=[], help="Required feature grep patterns")
    ap.add_argument("--max-experiments", type=int, default=10)
    ap.add_argument("--budget", type=float, default=80.0)
    ap.add_argument("--model", default=None, help="Model for generation")
    ap.add_argument("--convergence-discards", type=int, default=3)
    ap.add_argument("--delay", type=float, default=5.0)
    args = ap.parse_args()

    block = find_block(args.target)
    if not block:
        print(f"Block {args.target} not found in manifest"); sys.exit(1)

    # Set up iteration directory
    iter_dir = PROJ / "temp" / "iterate" / f"prompt-{args.target}"
    iter_dir.mkdir(parents=True, exist_ok=True)

    # Create git branch
    branch = f"iterate/prompt-{args.target}"
    git_create_branch(branch)

    cost = CostTracker(args.budget)
    ensure_iterations_dir()

    current_prompt = block["prompt"]
    prompt_file = iter_dir / "current-prompt.txt"
    prompt_file.write_text(current_prompt)

    print(f"=== Prompt Iteration: {args.target} ===")
    print(f"Features: {args.features}")
    print(f"Branch: {branch}")
    print(f"Budget: ${args.budget:.0f}")
    print()

    # Establish baseline: generate with original prompt
    print("Phase 0: Baseline generation")
    html_path, baseline_time, gen_cost = generate_block(current_prompt, block, iter_dir, args.model)
    cost.add(gen_cost)

    if not html_path:
        print("Baseline generation failed. Aborting."); sys.exit(1)

    features_pass = check_features(html_path, args.features)
    if not features_pass:
        print(f"WARNING: Baseline block missing required features. Continuing anyway.")

    exp_id = next_experiment_id()
    append_tsv(exp_id, "prompt", args.target, round(baseline_time, 1), 0, "baseline", gen_cost,
               f"Initial baseline ({len(current_prompt)} chars)")
    write_experiment(exp_id, "prompt", args.target, {
        "gen_time_s": round(baseline_time, 1),
        "prompt_len": len(current_prompt),
        "features_pass": features_pass,
        "prompt": current_prompt,
        "decision": "baseline",
        "git_sha": git_sha(),
    })

    print(f"  Baseline: {baseline_time:.0f}s, {len(current_prompt)} chars, features={'pass' if features_pass else 'FAIL'}")
    print()

    history_lines = [f"exp {exp_id}: baseline, {baseline_time:.0f}s, {len(current_prompt)} chars"]
    current_time = baseline_time

    # Main loop
    for exp_num in range(args.max_experiments):
        if cost.over_budget():
            print(f"\nBudget exhausted ({cost.summary()}). Stopping.")
            break

        if check_convergence("prompt", args.target, args.convergence_discards):
            print(f"\nConverged ({args.convergence_discards} consecutive discards). Stopping.")
            break

        exp_id = next_experiment_id()
        print(f"--- Experiment {exp_id} (#{exp_num + 1}/{args.max_experiments}) ---")

        # Run proposer to get a new prompt
        proposed_file = iter_dir / "proposed-prompt.txt"
        if proposed_file.exists():
            proposed_file.unlink()

        print("  Proposing rewrite...", end=" ", flush=True)
        t0 = time.time()
        run_proposer(current_prompt, current_time, args.features, history_lines, proposed_file)
        propose_time = time.time() - t0
        print(f"({propose_time:.0f}s)")

        if not proposed_file.exists() or proposed_file.stat().st_size < 10:
            print("  No prompt produced. Skipping.")
            append_tsv(exp_id, "prompt", args.target, 0, 0, "discard", 0, "No prompt produced")
            history_lines.append(f"exp {exp_id}: discard, no prompt produced")
            continue

        new_prompt = proposed_file.read_text().strip()
        if new_prompt == current_prompt:
            print("  Prompt unchanged. Skipping.")
            append_tsv(exp_id, "prompt", args.target, 0, 0, "discard", 0, "Prompt unchanged")
            history_lines.append(f"exp {exp_id}: discard, unchanged")
            continue

        print(f"  Prompt: {len(current_prompt)} → {len(new_prompt)} chars ({len(new_prompt) - len(current_prompt):+d})")

        # Generate with new prompt
        print("  Generating...", end=" ", flush=True)
        html_path, new_time, gen_cost = generate_block(new_prompt, block, iter_dir, args.model)
        cost.add(gen_cost)
        print(f"({new_time:.0f}s)")

        if not html_path:
            print("  Generation failed. Discarding.")
            append_tsv(exp_id, "prompt", args.target, 0, 0, "discard", gen_cost, "Generation failed")
            history_lines.append(f"exp {exp_id}: discard, generation failed")
            continue

        # Check features
        features_pass = check_features(html_path, args.features)
        if not features_pass:
            print(f"  Missing required features. Discarding.")

        # Decide
        decision, reason = decide_prompt(current_time, new_time, features_pass)
        delta = new_time - current_time
        description = f"{reason} ({current_time:.0f}s→{new_time:.0f}s, {len(new_prompt)} chars)"

        append_tsv(exp_id, "prompt", args.target, round(new_time, 1), round(delta, 1),
                   decision, gen_cost, description)
        write_experiment(exp_id, "prompt", args.target, {
            "gen_time_before": round(current_time, 1),
            "gen_time_after": round(new_time, 1),
            "prompt_len_before": len(current_prompt),
            "prompt_len_after": len(new_prompt),
            "features_pass": features_pass,
            "prompt": new_prompt,
            "decision": decision,
            "reason": reason,
            "git_sha": git_sha(),
        })

        if decision == "keep":
            print(f"  KEEP: {reason}")
            current_prompt = new_prompt
            current_time = new_time
            prompt_file.write_text(current_prompt)

            # Update best-prompts.json
            update_best("prompt", args.target, {
                "gen_time_s": round(new_time, 1),
                "features_pass": features_pass,
                "prompt": new_prompt,
                "prompt_len": len(new_prompt),
                "iteration": f"exp-{exp_id}",
                "git_sha": git_sha(),
            })

            git_commit(f"iterate-prompt exp-{exp_id}: {reason}",
                       [str(prompt_file)])
        else:
            print(f"  DISCARD: {reason}")

        history_lines.append(f"exp {exp_id}: {decision}, {new_time:.0f}s, {len(new_prompt)} chars, {reason}")

        if args.delay > 0:
            time.sleep(args.delay)

    # Generate progress
    progress = generate_progress_html()

    print(f"\n=== Done ===")
    print(f"Final: {current_time:.0f}s (was {baseline_time:.0f}s), {len(current_prompt)} chars")
    print(f"Cost: {cost.summary()}")
    if progress:
        print(f"Progress: {progress}")


if __name__ == "__main__":
    main()
