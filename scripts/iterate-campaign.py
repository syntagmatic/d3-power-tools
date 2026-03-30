#!/usr/bin/env python3
"""Campaign orchestrator: runs iterate scripts sequentially from a config file.

Usage:
  python3 scripts/iterate-campaign.py evals/campaigns/hierarchy-overnight.json
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from iterate_lib import PROJ, CostTracker, generate_progress_html

SCRIPTS = {
    "block": PROJ / "scripts" / "iterate-block.py",
    "prompt": PROJ / "scripts" / "iterate-prompt.py",
}


def run_track(track_config, remaining_budget, global_config):
    """Run a single track. Returns estimated cost spent."""
    track = track_config["track"]
    script = SCRIPTS.get(track)
    if not script or not script.exists():
        print(f"  Unknown or unimplemented track: {track}. Skipping.")
        return 0

    target = track_config["target"]
    max_exp = track_config.get("max_experiments", 15)
    budget = min(remaining_budget, track_config.get("budget_usd", remaining_budget))

    cmd = [
        "python3", str(script),
        "--target", target,
        "--max-experiments", str(max_exp),
        "--budget", str(budget),
        "--convergence-discards", str(global_config.get("convergence_discards", 3)),
        "--delay", str(global_config.get("delay_between_calls_s", 5)),
    ]

    # Track-specific args
    if track == "block":
        cmd.extend(["--block-set", track_config["block_set"]])
        if global_config.get("model"):
            cmd.extend(["--model", global_config["model"]])

    elif track == "prompt":
        cmd.extend(["--block-set", track_config.get("block_set", "v2-claude-opus-4-6")])
        for feat in track_config.get("features", []):
            cmd.extend(["--features", feat])
        if global_config.get("model"):
            cmd.extend(["--model", global_config["model"]])

    print(f"\n{'='*60}")
    print(f"Track: {track} | Target: {target}")
    print(f"Max experiments: {max_exp} | Budget: ${budget:.0f}")
    print(f"{'='*60}\n")

    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(PROJ))
    elapsed = time.time() - t0

    # Rough cost estimate based on time (will be refined as we gather data)
    est_cost = max_exp * 1.0  # $1/experiment rough estimate
    print(f"\nTrack {track}/{target} finished in {elapsed:.0f}s")
    return est_cost


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/iterate-campaign.py <campaign-config.json>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"Config not found: {config_path}"); sys.exit(1)

    config = json.loads(config_path.read_text())
    total_budget = config.get("budget_usd", 80)
    tracks = config.get("tracks", [])

    if not tracks:
        print("No tracks in config."); sys.exit(1)

    cost = CostTracker(total_budget)

    print(f"=== Campaign: {config_path.name} ===")
    print(f"Budget: ${total_budget:.0f}")
    print(f"Tracks: {len(tracks)}")
    for i, t in enumerate(tracks):
        print(f"  {i+1}. {t['track']}: {t['target']}")
    print()

    for i, track_config in enumerate(tracks):
        if cost.over_budget():
            print(f"\nGlobal budget exhausted ({cost.summary()}). Stopping.")
            break

        remaining = cost.remaining()
        spent = run_track(track_config, remaining, config)
        cost.add(spent)

    # Final progress
    progress = generate_progress_html()

    print(f"\n{'='*60}")
    print(f"Campaign complete")
    print(f"Cost: {cost.summary()}")
    if progress:
        print(f"Progress: {progress}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
