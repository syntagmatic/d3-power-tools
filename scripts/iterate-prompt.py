#!/usr/bin/env python3
"""Iterate on a prompt to improve generation time and/or quality.

Autoresearch-style loop: rewrite prompt → generate → audit → keep/discard → repeat.

Usage:
  # Speed only (original behavior)
  python3 scripts/iterate-prompt.py --target hierarchy-bundles --block-set v2-claude-opus-4-6 \
    --features "d3.pack" "d3.treemap" "curveBundle"

  # Speed + quality (audits each generation)
  python3 scripts/iterate-prompt.py --target hierarchy-bundles --block-set v2-claude-opus-4-6 \
    --features "d3.pack" "d3.treemap" "curveBundle" --quality

  # Resume with a custom prompt file
  python3 scripts/iterate-prompt.py --target hierarchy-bundles --block-set v2-claude-opus-4-6 \
    --features "d3.pack" "curveBundle" --quality --prompt-file temp/iterate/prompt-hierarchy-bundles/current-prompt.txt
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from iterate_lib import (
    PROJ, append_tsv, check_convergence, check_features, compute_diff,
    decide_prompt, decide_prompt_quality, ensure_iterations_dir,
    generate_progress_html, git_commit, git_sha, next_experiment_id,
    render_block, update_best, write_experiment,
)
from staging import create_staging_dir, cleanup_staging_dir

MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
CLAUDE_BIN = shutil.which("claude") or "/usr/local/share/npm-global/bin/claude"


def find_block(target):
    for b in MANIFEST["blocks"]:
        if b["id"] == target:
            return b
    return None


def get_audit_scores(html_path, block_id, model="sonnet"):
    """Render + audit a single block. Returns scores dict or None."""
    ss_dir = PROJ / "temp" / "audit-screenshots" / "iterate"
    ss_dir.mkdir(parents=True, exist_ok=True)
    ss_path = ss_dir / f"{block_id}.png"

    if not render_block(html_path, ss_path, "svg"):
        print("  Render failed")
        return None

    audit_script = PROJ / "scripts" / "run-audit-pipeline.py"
    block_dir = html_path.parent

    # Clear previous audit tmp files to force re-audit
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
        print(f"  Audit output: {(r.stdout or '')[-300:]}")

    runs_dir = PROJ / "evals" / "runs"
    if not runs_dir.exists():
        return None

    run_files = sorted(runs_dir.glob("*iterate*.json"), reverse=True)
    if not run_files:
        return None

    run_data = json.loads(run_files[0].read_text())
    scores = run_data.get("blocks", {}).get(block_id)

    if scores and scores.get("composite") is None:
        weights = {"visual_critic": 0.30, "encoding_integrity": 0.25,
                   "cognitive_load": 0.25, "stress_test": 0.20}
        available = {k: scores[k] for k in weights if scores.get(k) is not None}
        if available:
            total_w = sum(weights[k] for k in available)
            scores["composite"] = round(sum(scores[k] * weights[k] / total_w for k in available), 1)

    return scores


def format_audit_notes(scores):
    """Format audit scores into a string for the proposer."""
    if not scores:
        return "  (no audit data)"
    notes = []
    for dim in ("visual_critic", "encoding_integrity", "stress_test", "cognitive_load"):
        val = scores.get(dim, "?")
        note = scores.get(f"{dim}_note", "")
        if note:
            notes.append(f"  {dim} ({val}/10): {note}")
        elif val != "?":
            notes.append(f"  {dim}: {val}/10")
    flags = scores.get("flags", [])
    if flags:
        notes.append(f"  flags: {'; '.join(flags)}")
    return "\n".join(notes) if notes else "  (all dimensions scored, no notes)"


def generate_block(prompt_text, block, iter_dir, model=None, exp_id=None):
    """Generate a block from a prompt. Returns (html_path, elapsed_s) or (None, elapsed)."""
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
            "--verbose",
        ]
        if model:
            cmd.extend(["--model", model])

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(staging))
        elapsed = time.time() - t0

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        cleanup_staging_dir(staging)
        return None, elapsed
    finally:
        cleanup_staging_dir(staging)

    if outfile.exists() and outfile.stat().st_size > 100:
        # Save a copy per experiment so no generation is lost
        if exp_id is not None:
            archive = iter_dir / f"{bid}-exp{exp_id}.html"
            shutil.copy2(outfile, archive)
            prompt_archive = iter_dir / f"{bid}-exp{exp_id}-prompt.txt"
            prompt_archive.write_text(prompt_text)
            # Permanent copy alongside experiment JSONs
            proto_dir = PROJ / "evals" / "iterations" / "prototypes"
            proto_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(outfile, proto_dir / f"{exp_id:03d}-prompt-{bid}.html")
        return outfile, elapsed
    return None, elapsed


def load_proposer_template(quality_mode):
    """Load the appropriate proposer template."""
    name = "prompt-quality.md" if quality_mode else "prompt.md"
    return (PROJ / "scripts" / "proposer-prompts" / name).read_text()


def run_proposer(current_prompt, gen_time, features, history_lines, out_path,
                 quality_mode=False, audit_notes=""):
    """Call claude -p to propose a rewritten prompt."""
    template = load_proposer_template(quality_mode)

    features_list = "\n".join(f"  - `{f}`" for f in features) if features else "  (none)"
    history = "\n".join(history_lines[-10:]) if history_lines else "(first experiment)"

    prompt = template \
        .replace("{{current_prompt}}", current_prompt) \
        .replace("{{gen_time_s}}", f"{gen_time:.0f}") \
        .replace("{{features_list}}", features_list) \
        .replace("{{history}}", history) \
        .replace("{{out_path}}", str(out_path)) \
        .replace("{{audit_notes}}", audit_notes)

    r = subprocess.run(
        [CLAUDE_BIN, "-p", prompt,
         "--allowedTools", "Read,Edit,Write",
         "--max-turns", "10",
         "--output-format", "json"],
        capture_output=True, text=True, timeout=300,
        cwd=str(out_path.parent))
    return r


def main():
    ap = argparse.ArgumentParser(description="Iterate on a prompt for speed and quality")
    ap.add_argument("--target", required=True, help="Block ID, e.g. hierarchy-bundles")
    ap.add_argument("--block-set", required=True, help="Source block set for reference")
    ap.add_argument("--features", nargs="+", default=[], help="Required feature grep patterns")
    ap.add_argument("--max-experiments", type=int, default=10)
    ap.add_argument("--model", default=None, help="Model for generation")
    ap.add_argument("--audit-model", default="sonnet", help="Model for auditing")
    ap.add_argument("--convergence-discards", type=int, default=3)
    ap.add_argument("--delay", type=float, default=5.0)
    ap.add_argument("--quality", action="store_true",
                    help="Enable quality mode: audit each generation, optimize for both speed and quality")
    ap.add_argument("--prompt-file", default=None,
                    help="Path to initial prompt file (overrides manifest prompt)")
    args = ap.parse_args()

    block = find_block(args.target)
    if not block:
        print(f"Block {args.target} not found in manifest"); sys.exit(1)

    # Set up iteration directory
    iter_dir = PROJ / "temp" / "iterate" / f"prompt-{args.target}"
    iter_dir.mkdir(parents=True, exist_ok=True)

    ensure_iterations_dir()

    # Load initial prompt
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        if not prompt_path.is_absolute():
            prompt_path = PROJ / prompt_path
        current_prompt = prompt_path.read_text().strip()
        print(f"Using prompt from {prompt_path}")
    else:
        current_prompt = block["prompt"]

    prompt_file = iter_dir / "current-prompt.txt"
    prompt_file.write_text(current_prompt)

    mode_label = "speed+quality" if args.quality else "speed"
    print(f"=== Prompt Iteration ({mode_label}): {args.target} ===")
    print(f"Features: {args.features}")
    print()

    # Establish baseline: generate with current prompt
    print("Phase 0: Baseline generation")
    baseline_exp_id = next_experiment_id()
    html_path, baseline_time = generate_block(current_prompt, block, iter_dir, args.model, exp_id=baseline_exp_id)

    if not html_path:
        print("Baseline generation failed. Aborting."); sys.exit(1)

    features_pass = check_features(html_path, args.features)
    if not features_pass:
        print(f"WARNING: Baseline block missing required features. Continuing anyway.")

    # Audit baseline if in quality mode
    baseline_scores = None
    current_composite = None
    audit_notes_str = ""
    if args.quality:
        print("  Auditing baseline...", end=" ", flush=True)
        t0 = time.time()
        baseline_scores = get_audit_scores(html_path, args.target, model=args.audit_model)
        audit_time = time.time() - t0
        if baseline_scores:
            current_composite = baseline_scores.get("composite")
            audit_notes_str = format_audit_notes(baseline_scores)
            print(f"composite={current_composite} ({audit_time:.0f}s)")
        else:
            print(f"failed ({audit_time:.0f}s)")

    exp_data = {
        "gen_time_s": round(baseline_time, 1),
        "prompt_len": len(current_prompt),
        "features_pass": features_pass,
        "prompt": current_prompt,
        "decision": "baseline",
        "git_sha": git_sha(),
    }
    if baseline_scores:
        exp_data["scores"] = baseline_scores
        exp_data["composite"] = current_composite
        exp_data["audit_time_s"] = round(audit_time, 1)

    append_tsv(baseline_exp_id, "prompt", args.target, round(baseline_time, 1), 0, "baseline",
               f"Initial baseline ({len(current_prompt)} chars)" +
               (f", composite={current_composite}" if current_composite else ""))
    write_experiment(baseline_exp_id, "prompt", args.target, exp_data)

    baseline_label = f"{baseline_time:.0f}s, {len(current_prompt)} chars, features={'pass' if features_pass else 'FAIL'}"
    if current_composite:
        baseline_label += f", composite={current_composite}"
    print(f"  Baseline: {baseline_label}")
    print()

    history_lines = [f"exp {baseline_exp_id}: baseline, {baseline_label}"]
    current_time = baseline_time
    keeps = 0

    # Main loop
    for exp_num in range(args.max_experiments):
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
        run_proposer(current_prompt, current_time, args.features, history_lines,
                     proposed_file, quality_mode=args.quality, audit_notes=audit_notes_str)
        propose_time = time.time() - t0
        print(f"({propose_time:.0f}s)")

        if not proposed_file.exists() or proposed_file.stat().st_size < 10:
            print("  No prompt produced. Skipping.")
            append_tsv(exp_id, "prompt", args.target, 0, 0, "discard", "No prompt produced")
            history_lines.append(f"exp {exp_id}: discard, no prompt produced")
            continue

        new_prompt = proposed_file.read_text().strip()
        if new_prompt == current_prompt:
            print("  Prompt unchanged. Skipping.")
            append_tsv(exp_id, "prompt", args.target, 0, 0, "discard", "Prompt unchanged")
            history_lines.append(f"exp {exp_id}: discard, unchanged")
            continue

        print(f"  Prompt: {len(current_prompt)} → {len(new_prompt)} chars ({len(new_prompt) - len(current_prompt):+d})")

        # Generate with new prompt
        print("  Generating...", end=" ", flush=True)
        html_path, new_time = generate_block(new_prompt, block, iter_dir, args.model, exp_id=exp_id)
        print(f"({new_time:.0f}s)")

        if not html_path:
            print("  Generation failed. Discarding.")
            append_tsv(exp_id, "prompt", args.target, 0, 0, "discard", "Generation failed")
            history_lines.append(f"exp {exp_id}: discard, generation failed")
            continue

        # Check features
        features_pass = check_features(html_path, args.features)
        if not features_pass:
            print(f"  Missing required features. Discarding.")

        # Audit if in quality mode
        new_scores = None
        new_composite = None
        if args.quality and features_pass:
            print("  Auditing...", end=" ", flush=True)
            t0 = time.time()
            new_scores = get_audit_scores(html_path, args.target, model=args.audit_model)
            audit_time = time.time() - t0
            if new_scores:
                new_composite = new_scores.get("composite")
                print(f"composite={new_composite} ({audit_time:.0f}s)")
            else:
                print(f"failed ({audit_time:.0f}s)")

        # Decide
        if args.quality:
            decision, reason = decide_prompt_quality(
                current_time, new_time,
                current_composite or 0, new_composite or 0,
                features_pass)
        else:
            decision, reason = decide_prompt(current_time, new_time, features_pass)

        delta = new_time - current_time
        description = f"{reason} ({current_time:.0f}s→{new_time:.0f}s, {len(new_prompt)} chars)"

        # Compute diff
        diff_text = compute_diff(current_prompt, new_prompt, "prompt.txt")

        exp_data = {
            "gen_time_before": round(current_time, 1),
            "gen_time_after": round(new_time, 1),
            "prompt_len_before": len(current_prompt),
            "prompt_len_after": len(new_prompt),
            "features_pass": features_pass,
            "prompt": new_prompt,
            "decision": decision,
            "reason": reason,
            "diff": diff_text,
            "git_sha": git_sha(),
            "propose_time_s": round(propose_time, 1),
        }
        if new_scores:
            exp_data["scores"] = new_scores
            exp_data["composite_before"] = current_composite
            exp_data["composite_after"] = new_composite
            exp_data["audit_time_s"] = round(audit_time, 1)

        append_tsv(exp_id, "prompt", args.target, round(new_time, 1), round(delta, 1),
                   decision, description)
        write_experiment(exp_id, "prompt", args.target, exp_data)

        if decision == "keep":
            print(f"  KEEP: {reason}")
            current_prompt = new_prompt
            current_time = new_time
            if new_composite is not None:
                current_composite = new_composite
                audit_notes_str = format_audit_notes(new_scores)
            prompt_file.write_text(current_prompt)
            keeps += 1

            best_data = {
                "gen_time_s": round(new_time, 1),
                "features_pass": features_pass,
                "prompt": new_prompt,
                "prompt_len": len(new_prompt),
                "iteration": f"exp-{exp_id}",
                "git_sha": git_sha(),
            }
            if new_composite is not None:
                best_data["composite"] = new_composite
            update_best("prompt", args.target, best_data)
        else:
            print(f"  DISCARD: {reason}")

        history_lines.append(f"exp {exp_id}: {decision}, {new_time:.0f}s, {len(new_prompt)} chars, {reason}")

        if args.delay > 0:
            time.sleep(args.delay)

    # Generate progress
    progress = generate_progress_html()

    print(f"\n=== Done ===")
    final_label = f"{current_time:.0f}s (was {baseline_time:.0f}s), {len(current_prompt)} chars"
    if current_composite:
        final_label += f", composite={current_composite}"
    print(f"Final: {final_label}")
    if progress:
        print(f"Progress: {progress}")


if __name__ == "__main__":
    main()
