"""Shared utilities for autoresearch-style iteration scripts.

Provides TSV logging, keep/discard decisions,
git helpers, and progress HTML generation.
"""
import difflib
import json
import os
import subprocess
import time
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
ITERATIONS_DIR = PROJ / "evals" / "iterations"
BEST_DIR = PROJ / "evals"


# === Git helpers ===

def git_sha(cwd=None):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, cwd=cwd or str(PROJ))
        return r.stdout.strip()
    except Exception:
        return "unknown"


def git_branch_name(cwd=None):
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, cwd=cwd or str(PROJ))
        return r.stdout.strip()
    except Exception:
        return "unknown"


def git_create_branch(name, cwd=None):
    """Create and checkout a new branch, or switch to it if it already exists."""
    current = git_branch_name(cwd)
    if current == name:
        return
    r = subprocess.run(["git", "checkout", "-b", name],
                       capture_output=True, text=True, cwd=cwd or str(PROJ))
    if r.returncode != 0:
        # Branch already exists — just check it out
        subprocess.run(["git", "checkout", name],
                       capture_output=True, text=True, cwd=cwd or str(PROJ))


def git_checkout_branch(name, cwd=None):
    subprocess.run(["git", "checkout", name],
                   capture_output=True, text=True, cwd=cwd or str(PROJ))


def git_commit(message, files, cwd=None):
    """Stage specific files and commit."""
    d = cwd or str(PROJ)
    subprocess.run(["git", "add"] + [str(f) for f in files],
                   capture_output=True, text=True, cwd=d)
    subprocess.run(["git", "commit", "-m", message],
                   capture_output=True, text=True, cwd=d)


def git_discard(files, cwd=None):
    """Discard changes to specific files."""
    d = cwd or str(PROJ)
    subprocess.run(["git", "checkout", "--"] + [str(f) for f in files],
                   capture_output=True, text=True, cwd=d)


def git_diff_stat(files, cwd=None):
    """Return short diff stat for files."""
    d = cwd or str(PROJ)
    r = subprocess.run(["git", "diff", "--stat"] + [str(f) for f in files],
                       capture_output=True, text=True, cwd=d)
    return r.stdout.strip()


def git_squash_merge(branch, base, message, cwd=None):
    """Squash-merge branch onto base. Returns True on success.

    Always operates from PROJ (the main worktree) so it's safe to call
    while a secondary worktree is checked out on a different branch.
    """
    d = str(PROJ)
    subprocess.run(["git", "checkout", base], capture_output=True, text=True, cwd=d)
    r = subprocess.run(["git", "merge", "--squash", branch],
                       capture_output=True, text=True, cwd=d)
    if r.returncode != 0:
        return False
    r = subprocess.run(["git", "commit", "-m", message],
                       capture_output=True, text=True, cwd=d)
    if r.returncode != 0:
        return False
    # Clean up the branch
    subprocess.run(["git", "branch", "-D", branch],
                   capture_output=True, text=True, cwd=d)
    return True


# === Worktree helpers ===

WORKTREES_DIR = PROJ / "temp" / "worktrees"


def worktree_is_active(branch):
    """Check if a worktree for this branch already exists and is active.

    Returns the worktree path if active, None otherwise.
    """
    wt_path = WORKTREES_DIR / branch.replace("/", "-")
    if not wt_path.exists():
        return None
    r = subprocess.run(["git", "worktree", "list", "--porcelain"],
                       capture_output=True, text=True, cwd=str(PROJ))
    if str(wt_path) in r.stdout:
        return wt_path
    return None


def worktree_create(branch):
    """Create a git worktree on a new branch. Returns worktree path.

    If the branch/worktree already exists, reuses it.
    """
    wt_path = WORKTREES_DIR / branch.replace("/", "-")
    if wt_path.exists():
        # Already exists — verify it's valid
        r = subprocess.run(["git", "worktree", "list", "--porcelain"],
                           capture_output=True, text=True, cwd=str(PROJ))
        if str(wt_path) in r.stdout:
            return wt_path
        # Stale directory — remove and recreate
        import shutil
        shutil.rmtree(wt_path, ignore_errors=True)

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "worktree", "add", "-b", branch, str(wt_path)],
                       capture_output=True, text=True, cwd=str(PROJ))
    if r.returncode != 0:
        # Branch may already exist
        r = subprocess.run(["git", "worktree", "add", str(wt_path), branch],
                           capture_output=True, text=True, cwd=str(PROJ))
        if r.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {r.stderr}")
    return wt_path


def worktree_remove(wt_path):
    """Remove a git worktree and clean up."""
    subprocess.run(["git", "worktree", "remove", "--force", str(wt_path)],
                   capture_output=True, text=True, cwd=str(PROJ))
    # Prune in case of stale entries
    subprocess.run(["git", "worktree", "prune"],
                   capture_output=True, text=True, cwd=str(PROJ))


# === Keep/discard decisions ===

def decide_block(composite_before, composite_after, lines_before, lines_after):
    """Block track: optimize LOC, constrain composite."""
    composite_delta = composite_after - composite_before
    if composite_delta < -0.3:
        return "discard", "quality regression"
    if lines_after >= lines_before:
        return "discard", "didn't get shorter"
    return "keep", f"-{lines_before - lines_after} lines"


def decide_redesign(composite_before, composite_after, lines_before, lines_after):
    """Redesign track: optimize composite, constrain LOC growth."""
    line_growth = lines_after - lines_before
    if line_growth > 20:
        return "discard", f"+{line_growth} lines (max +20)"
    composite_delta = composite_after - composite_before
    if composite_delta < 0.1:
        return "discard", "no quality improvement"
    return "keep", f"+{composite_delta:.1f} composite"


def decide_prompt(time_before, time_after, features_pass):
    """Prompt track: optimize gen time, constrain features."""
    if not features_pass:
        return "discard", "missing required features"
    if time_after >= time_before * 0.85:
        return "discard", "not meaningfully faster"
    return "keep", f"-{time_before - time_after:.0f}s"


# === TSV logging ===

def ensure_iterations_dir():
    ITERATIONS_DIR.mkdir(parents=True, exist_ok=True)


def tsv_path():
    return ITERATIONS_DIR / "history.tsv"


TSV_HEADER = "exp\ttrack\ttarget\tmetric\tdelta\tdecision\tdescription\n"


def append_tsv(exp_id, track, target, metric, delta, decision, description):
    ensure_iterations_dir()
    path = tsv_path()
    if not path.exists():
        path.write_text(TSV_HEADER)
    with open(path, "a") as f:
        delta_str = f"{delta:+.1f}" if isinstance(delta, float) else str(delta)
        f.write(f"{exp_id}\t{track}\t{target}\t{metric}\t{delta_str}\t{decision}\t{description}\n")


# === Diff utilities ===

def compute_diff(before_text, after_text, filename="file"):
    """Compute a unified diff between two strings. Returns diff string."""
    before_lines = before_text.splitlines(keepends=True)
    after_lines = after_text.splitlines(keepends=True)
    diff = difflib.unified_diff(before_lines, after_lines,
                                fromfile=f"a/{filename}", tofile=f"b/{filename}")
    return "".join(diff)


# === Per-experiment JSON ===

def write_experiment(exp_id, track, target, data):
    ensure_iterations_dir()
    filename = f"{exp_id:03d}-{track}-{target}.json"
    path = ITERATIONS_DIR / filename
    data["experiment_id"] = exp_id
    data["track"] = track
    data["target"] = target
    data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


# === Best-of tracking ===

def update_best(track, target, entry):
    """Update best-{track}s.json with a new best entry."""
    filename = f"best-{track}s.json"
    path = BEST_DIR / filename
    if path.exists():
        best = json.loads(path.read_text())
    else:
        best = {}
    best[target] = entry
    path.write_text(json.dumps(best, indent=2, ensure_ascii=False) + "\n")


# === Next experiment ID ===

def next_experiment_id():
    """Read TSV to find the next experiment number."""
    path = tsv_path()
    if not path.exists():
        return 1
    lines = path.read_text().strip().split("\n")
    if len(lines) <= 1:  # header only
        return 1
    last_id = 0
    for line in lines[1:]:
        parts = line.split("\t")
        try:
            last_id = max(last_id, int(parts[0]))
        except (ValueError, IndexError):
            pass
    return last_id + 1


# === Convergence check ===

def check_convergence(track, target, max_discards=3):
    """Check if the last N decisions for this track+target were all discards."""
    path = tsv_path()
    if not path.exists():
        return False
    decisions = []
    for line in path.read_text().strip().split("\n")[1:]:
        parts = line.split("\t")
        if len(parts) >= 6 and parts[1] == track and parts[2] == target:
            decisions.append(parts[5])
    if len(decisions) < max_discards:
        return False
    return all(d == "discard" for d in decisions[-max_discards:])


# === Audit helpers ===

def run_audit(block_id, block_dir, block_set_name, model="sonnet", wait_for="svg"):
    """Run the audit pipeline on a single block. Returns composite + per-dimension scores."""
    audit_script = PROJ / "scripts" / "run-audit-pipeline.py"
    bid_num = block_id.split("-")[0]

    r = subprocess.run(
        ["python3", str(audit_script),
         "--blocks", bid_num,
         "--block-set", block_set_name,
         "--block-dir", str(block_dir),
         "--model", model,
         "--skip-render"],
        capture_output=True, text=True, timeout=600, cwd=str(PROJ))

    # Find the most recent run file for this block set
    runs_dir = PROJ / "evals" / "runs"
    if not runs_dir.exists():
        return None

    run_files = sorted(runs_dir.glob(f"*{block_set_name}*.json"), reverse=True)
    if not run_files:
        return None

    run_data = json.loads(run_files[0].read_text())
    block_scores = run_data.get("blocks", {}).get(block_id, {})
    return block_scores if block_scores.get("composite") is not None else None


def render_block(html_path, screenshot_path, wait_for="svg"):
    """Render a block and take a screenshot. Returns True on success."""
    test_script = PROJ / "scripts" / "test-viz.py"
    try:
        r = subprocess.run(
            ["python3", str(test_script), str(html_path),
             "--out", str(screenshot_path), "--wait-for", wait_for],
            capture_output=True, text=True, timeout=30, cwd=str(PROJ))
        if "PASS" not in r.stdout:
            # Tolerate broken external images (common in blocks that load thumbnails)
            failed_checks = [l.strip() for l in r.stdout.splitlines()
                             if l.strip().startswith("[x]")]
            only_broken_images = (
                failed_checks
                and all("no_broken_resources" in c for c in failed_checks)
            )
            if not only_broken_images:
                print(f"    render stderr: {r.stderr.strip()}" if r.stderr.strip() else "")
                print(f"    render stdout: {r.stdout.strip()}" if r.stdout.strip() else "")
                return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    render timed out after 30s")
        return False


# === Feature checking (prompt track) ===

def check_features(html_path, features):
    """Check if all feature patterns (grep regexes) are present in the HTML."""
    if not features:
        return True
    content = Path(html_path).read_text()
    import re
    for pattern in features:
        if not re.search(pattern, content, re.IGNORECASE):
            return False
    return True


# === Index HTML ===

def _json_for_html(obj):
    """Serialize to JSON safe for embedding in <script> blocks."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _load_experiments():
    """Load all experiment JSONs. Returns list of dicts sorted by exp id."""
    experiments = []
    for f in sorted(ITERATIONS_DIR.glob("*.json")):
        try:
            experiments.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, ValueError):
            pass
    return experiments


def _load_tsv_records():
    """Parse history.tsv into records list."""
    path = tsv_path()
    if not path.exists():
        return []
    records = []
    for line in path.read_text().strip().split("\n")[1:]:
        parts = line.split("\t")
        if len(parts) >= 7:
            records.append({
                "exp": int(parts[0]),
                "track": parts[1],
                "target": parts[2],
                "metric": float(parts[3]) if parts[3].replace(".", "").replace("-", "").isdigit() else 0,
                "delta": parts[4],
                "decision": parts[5],
                "description": parts[6],
            })
    return records


def generate_progress_html():
    """Generate iterations/index.html — master list of all experiments.

    Includes: summary cards per target with sparkline chart, full experiment
    table with expandable diffs, links to experiment JSONs and audit runs.
    """
    ensure_iterations_dir()
    records = _load_tsv_records()
    experiments = _load_experiments()
    if not records:
        return None

    # Build a lookup from (track, target, exp_id) -> experiment data
    exp_lookup = {}
    for e in experiments:
        key = (e.get("track", ""), e.get("target", ""), e.get("experiment_id", 0))
        exp_lookup[key] = e

    # Collect linked resources
    runs_dir = PROJ / "evals" / "runs"
    run_files = sorted(runs_dir.glob("*.json"), reverse=True) if runs_dir.exists() else []
    best_blocks = BEST_DIR / "best-blocks.json"
    best_prompts = BEST_DIR / "best-prompts.json"

    # Build experiments array for JS (records + diffs + scores + links)
    js_experiments = []
    for r in records:
        key = (r["track"], r["target"], r["exp"])
        e = exp_lookup.get(key, {})
        exp_file = f"{r['exp']:03d}-{r['track']}-{r['target']}.json"
        js_experiments.append({
            **r,
            "scores": e.get("scores", {}),
            "diff": e.get("diff", ""),
            "timestamp": e.get("timestamp", ""),
            "composite_before": e.get("composite_before"),
            "composite_after": e.get("composite_after", e.get("composite")),
            "lines_before": e.get("lines_before", e.get("lines")),
            "lines_after": e.get("lines_after", e.get("lines")),
            "git_sha": e.get("git_sha", ""),
            "proposer": e.get("proposer", ""),
            "propose_time_s": e.get("propose_time_s"),
            "audit_time_s": e.get("audit_time_s"),
            "flags": e.get("scores", {}).get("flags", []),
            "json_file": exp_file if (ITERATIONS_DIR / exp_file).exists() else None,
        })

    # Block set lookup for linking to source blocks
    block_sets = {}
    if best_blocks.exists():
        for tid, entry in json.loads(best_blocks.read_text()).items():
            block_sets[tid] = entry.get("block_set", "")

    # Detect GitHub remote for source links
    github_url = ""
    try:
        r = subprocess.run(["git", "remote", "get-url", "origin"],
                           capture_output=True, text=True, cwd=str(PROJ))
        remote = r.stdout.strip()
        if "github.com" in remote:
            # git@github.com:user/repo.git or https://github.com/user/repo.git
            remote = remote.replace("git@github.com:", "https://github.com/")
            if remote.endswith(".git"):
                remote = remote[:-4]
            github_url = remote
    except Exception:
        pass

    # Linked resources for the nav
    resources = {
        "history_tsv": "history.tsv",
        "block_sets": block_sets,
        "github_url": github_url,
        "best_blocks": "../../evals/best-blocks.json" if best_blocks.exists() else None,
        "best_prompts": "../../evals/best-prompts.json" if best_prompts.exists() else None,
        "audit_runs": [f.name for f in run_files[:20]],
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Iterations Index</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; padding: 32px 40px; background: #fafafa; color: #222; max-width: 1100px; }}
  h1 {{ font-size: 22px; font-weight: 400; margin: 0 0 2px; }} h1 b {{ font-weight: 600; }}
  .page-meta {{ color: #888; font-size: 13px; margin-bottom: 8px; }}
  .nav {{ display: flex; gap: 16px; font-size: 12px; margin-bottom: 28px; flex-wrap: wrap; }}
  .nav a {{ color: #1565c0; text-decoration: none; }} .nav a:hover {{ text-decoration: underline; }}
  .nav .sep {{ color: #ccc; }}

  .target-section {{ margin-bottom: 48px; }}
  .target-header {{ display: flex; align-items: baseline; gap: 12px; margin-bottom: 4px; }}
  .target-title {{ font-size: 17px; font-weight: 600; margin: 0; color: #222; text-decoration: none; }}
  a.target-title:hover {{ text-decoration: underline; }}
  .target-badge {{ font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }}
  .badge-block {{ background: #e3f2fd; color: #1565c0; }}
  .badge-prompt {{ background: #fce4ec; color: #c62828; }}
  .badge-refactor {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-redesign {{ background: #fff3e0; color: #e65100; }}
  .target-meta {{ font-size: 12px; color: #888; margin-bottom: 12px; }}

  svg {{ overflow: visible; display: block; margin-bottom: 8px; }}
  .dot-keep {{ fill: #2e7d32; cursor: pointer; }} .dot-keep:hover {{ r: 6; }}
  .dot-discard {{ fill: #bbb; cursor: pointer; }} .dot-discard:hover {{ r: 6; }}
  .dot-baseline {{ fill: #1565c0; cursor: pointer; }} .dot-baseline:hover {{ r: 6; }}
  .best-line {{ stroke: #2e7d32; stroke-width: 1.5; fill: none; }}
  .axis text {{ font-size: 11px; fill: #666; }}
  .axis line, .axis path {{ stroke: #ddd; }}

  table {{ border-collapse: collapse; font-size: 12px; margin-top: 4px; width: 100%; }}
  th, td {{ padding: 5px 10px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ font-weight: 600; color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; position: sticky; top: 0; background: #fafafa; }}
  .keep {{ color: #2e7d32; font-weight: 600; }}
  .discard {{ color: #999; }}
  .baseline {{ color: #1565c0; }}
  td.mono {{ font-family: "SF Mono", "Consolas", monospace; font-size: 11px; }}
  td a {{ color: #1565c0; text-decoration: none; }} td a:hover {{ text-decoration: underline; }}
  .proposer-cell {{ max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; color: #555; }}

  .score-cell {{ position: relative; cursor: default; }}
  .score-bar {{ display: inline-flex; gap: 3px; align-items: center; }}
  .score-num {{ display: inline-block; min-width: 18px; height: 18px; line-height: 18px; border-radius: 3px;
    text-align: center; font-size: 10px; font-weight: 600; color: #fff; }}

  .score-tip {{ display: none; position: absolute; left: 0; top: 100%; z-index: 10;
    background: #fff; border: 1px solid #ddd; border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,.12);
    padding: 10px 14px; width: 380px; font-size: 12px; line-height: 1.5; color: #333; pointer-events: none; }}
  .score-cell:hover .score-tip, .score-cell:focus-within .score-tip {{ display: block; }}
  .score-tip .tip-dim {{ margin-bottom: 8px; }}
  .score-tip .tip-dim:last-child {{ margin-bottom: 0; }}
  .score-tip .tip-label {{ font-weight: 600; font-size: 11px; }}
  .score-tip .tip-score {{ display: inline-block; min-width: 16px; height: 16px; line-height: 16px;
    border-radius: 3px; text-align: center; font-size: 10px; font-weight: 600; color: #fff;
    vertical-align: middle; margin-left: 4px; }}
  .score-tip .tip-note {{ color: #555; margin-top: 2px; }}

  .diff-toggle {{ cursor: pointer; color: #1565c0; font-size: 11px; user-select: none; }}
  .diff-toggle:hover {{ text-decoration: underline; }}
  .diff-row {{ display: none; }}
  .diff-row.open {{ display: table-row; }}
  .diff-cell {{ padding: 0; }}
  .diff-pre {{ margin: 0; padding: 8px 12px; background: #f5f5f5; font-family: "SF Mono", "Consolas", monospace;
    font-size: 11px; line-height: 1.5; overflow-x: auto; max-height: 400px; overflow-y: auto; white-space: pre; border-top: 1px solid #eee; }}
  .proposer-note {{ padding: 10px 14px; background: #f0f4ff; border-top: 1px solid #e0e4ee;
    font-size: 12px; line-height: 1.6; color: #333; white-space: pre-wrap; }}
  .flags-cell {{ max-width: 180px; }}
  .flag-tag-sm {{ display: inline-block; font-size: 10px; padding: 1px 5px; border-radius: 3px; background: #fff3cd; color: #856404;
    border: 1px solid #f0dca0; margin: 1px 2px; cursor: default; white-space: nowrap; }}
  .flags-row {{ padding: 6px 14px; background: #fff8e1; border-top: 1px solid #f0e4b8; display: flex; flex-wrap: wrap; gap: 6px; }}
  .flag-tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #fff3cd; color: #856404; border: 1px solid #f0dca0; }}
  .diff-pre .add {{ color: #2e7d32; background: #e8f5e9; display: inline; }}
  .diff-pre .del {{ color: #c62828; background: #ffebee; display: inline; }}
  .diff-pre .hunk {{ color: #6a1b9a; font-weight: 600; }}
</style>
</head>
<body>
<h1><b>Iterations</b></h1>
<p class="page-meta">{len(records)} experiments across {len(set((r['track'], r['target']) for r in records))} targets &middot; generated {time.strftime("%Y-%m-%d %H:%M")}</p>
<div class="nav" id="nav"></div>
<div id="content"></div>
<script>
const experiments = {_json_for_html(js_experiments)};
const resources = {_json_for_html(resources)};

// --- Nav ---
const nav = d3.select("#nav");
nav.append("a").attr("href", "history.tsv").text("history.tsv");
if (resources.best_blocks) nav.append("span").attr("class","sep").text("·"),
  nav.append("a").attr("href", resources.best_blocks).text("best-blocks.json");
if (resources.best_prompts) nav.append("span").attr("class","sep").text("·"),
  nav.append("a").attr("href", resources.best_prompts).text("best-prompts.json");
if (resources.audit_runs.length) {{
  nav.append("span").attr("class","sep").text("·");
  const dd = nav.append("details").style("display","inline");
  dd.append("summary").style("cursor","pointer").style("font-size","12px").text(`${{resources.audit_runs.length}} audit runs`);
  const ul = dd.append("div").style("padding","4px 0 0 8px");
  resources.audit_runs.forEach(f => ul.append("a").attr("href", `../runs/${{f}}`).text(f).append("br"));
}}

// --- Group by track/target, reverse chronological ---
const groups = d3.group(experiments, d => `${{d.track}}/${{d.target}}`);
const groupEntries = [...groups.entries()].reverse();
const content = d3.select("#content");

for (const [key, data] of groupEntries) {{
  data.reverse();
  const [track, target] = key.split("/", 2);
  const section = content.append("div").attr("class", "target-section");

  // Header
  const header = section.append("div").attr("class", "target-header");
  header.append("a").attr("class", "target-title")
    .attr("href", `../../blocks/${{target}}.html`).text(target);

  // Infer run type from keep reasons: "+X composite" = redesign, "-X lines" = refactor
  const keepReasons = data.filter(d => d.decision === "keep").map(d => d.description || "");
  const isRedesign = keepReasons.some(r => /composite/.test(r) && !/lines/.test(r));
  const runType = isRedesign ? "redesign" : "refactor";
  header.append("span").attr("class", `target-badge badge-${{track}}`).text(track);
  header.append("span").attr("class", `target-badge badge-${{runType}}`).text(runType);

  // data is reversed (newest first) for the table; chrono is oldest-first for the chart
  const chrono = [...data].reverse();
  const keeps = data.filter(d => d.decision === "keep");
  const discards = data.filter(d => d.decision === "discard");
  const oldest = chrono[0], newest = chrono[chrono.length - 1];
  const metricLabel = track === "block" ? "lines" : "time";
  const currentBest = newest.decision === "keep" || newest.decision === "baseline" ? newest.metric : keeps.length ? keeps[0].metric : oldest.metric;
  const meta = section.append("div").attr("class", "target-meta");
  meta.append("span")
    .text(`${{data.length}} experiments · ${{keeps.length}} kept · ${{discards.length}} discarded · ${{metricLabel}}: ${{oldest.metric}}→${{currentBest}}`);
  if (isRedesign && keeps.length > 0) {{
    meta.append("span").text(" · ");
    meta.append("a")
      .attr("href", `baselines/${{target}}.html`)
      .attr("target", "_blank").text("before");
    meta.append("span").text(" → ");
    meta.append("a")
      .attr("href", `../../blocks/${{target}}.html`)
      .attr("target", "_blank").text("after");
  }}

  // --- Sparkline chart (chronological: oldest left, newest right) ---
  const margin = {{top: 10, right: 16, bottom: 24, left: 44}};
  const width = 520, height = 120;
  const svg = section.append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

  const x = d3.scaleLinear().domain([0, chrono.length - 1]).range([0, width]);
  const yExtent = d3.extent(chrono, d => d.metric);
  const y = d3.scaleLinear().domain(yExtent).nice().range([height, 0]);

  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${{height}})`)
    .call(d3.axisBottom(x).ticks(Math.min(chrono.length, 8)).tickFormat(d3.format("d")));
  svg.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(4));

  let best = chrono[0]?.metric || 0;
  const bestPts = chrono.map((d, i) => {{
    if (d.decision === "keep" || d.decision === "baseline") best = d.metric;
    return {{ i, best }};
  }});
  svg.append("path").attr("class", "best-line")
    .attr("d", d3.line().x(d => x(d.i)).y(d => y(d.best))(bestPts));

  svg.selectAll(".dot").data(chrono).join("circle")
    .attr("cx", (d, i) => x(i)).attr("cy", d => y(d.metric)).attr("r", 4)
    .attr("class", d => `dot-${{d.decision === "keep" ? "keep" : d.decision === "baseline" ? "baseline" : "discard"}}`);

  // --- Experiment table ---
  const table = section.append("table");
  const cols = ["#", "Decision", metricLabel, "Δ", "Composite", "Scores", "Propose", "Audit", "Flags", "Proposer", "Diff", "JSON"];
  table.append("thead").append("tr").selectAll("th").data(cols).join("th").text(d => d);
  const tbody = table.append("tbody");

  const scoreDims = ["visual_critic", "encoding_integrity", "stress_test", "cognitive_load"];
  const scoreColor = d3.scaleLinear().domain([1, 5, 10]).range(["#c62828", "#f9a825", "#2e7d32"]);

  // Per-block numbering: baseline=1, ascending in chronological order
  const blockNum = new Map();
  chrono.forEach((d, i) => blockNum.set(d.exp, i + 1));

  data.forEach((d, idx) => {{
    const cls = d.decision === "keep" ? "keep" : d.decision === "baseline" ? "baseline" : "discard";
    const tr = tbody.append("tr");
    tr.append("td").text(blockNum.get(d.exp));
    const decisionCell = tr.append("td").attr("class", cls);
    if (d.decision === "baseline" && resources.github_url && d.git_sha) {{
      decisionCell.append("a")
        .attr("href", `${{resources.github_url}}/blob/${{d.git_sha}}/blocks/${{target}}.html`)
        .attr("target", "_blank").text("baseline ↗");
    }} else {{
      decisionCell.text(d.decision);
    }}
    tr.append("td").attr("class", "mono").text(d.metric || "–");
    tr.append("td").attr("class", "mono").text(d.delta || "–");

    // Composite
    const comp = d.composite_after ?? d.scores?.composite;
    tr.append("td").attr("class", "mono").text(comp != null ? comp.toFixed(1) : "–");

    // Scores: numerical badges with rich tooltip showing auditor feedback
    const scoreCell = tr.append("td").attr("class", "score-cell").attr("tabindex", "0");
    const hasScores = d.scores && scoreDims.some(dim => d.scores[dim] != null);
    if (hasScores) {{
      const bar = scoreCell.append("span").attr("class", "score-bar");
      scoreDims.forEach(dim => {{
        const v = d.scores[dim];
        if (v != null) bar.append("span").attr("class", "score-num")
          .style("background", scoreColor(v))
          .style("color", v >= 4 && v <= 6 ? "#333" : "#fff").text(v);
      }});
      // Rich tooltip
      const tip = scoreCell.append("div").attr("class", "score-tip");
      scoreDims.forEach(dim => {{
        const v = d.scores[dim];
        if (v == null) return;
        const note = d.scores[dim + "_note"] || "";
        const label = dim.split("_").map(w => w[0].toUpperCase() + w.slice(1)).join(" ");
        const dd = tip.append("div").attr("class", "tip-dim");
        const hdr = dd.append("div");
        hdr.append("span").attr("class", "tip-label").text(label);
        hdr.append("span").attr("class", "tip-score")
          .style("background", scoreColor(v))
          .style("color", v >= 4 && v <= 6 ? "#333" : "#fff").text(v);
        if (note) dd.append("div").attr("class", "tip-note").text(note);
      }});
    }} else scoreCell.text("–");

    // Propose / Audit durations
    tr.append("td").attr("class", "mono").text(d.propose_time_s != null ? `${{Math.round(d.propose_time_s)}}s` : "–");
    tr.append("td").attr("class", "mono").text(d.audit_time_s != null ? `${{Math.round(d.audit_time_s)}}s` : "–");

    // Flags (inline)
    const flagsCell = tr.append("td").attr("class", "flags-cell");
    if (d.flags && d.flags.length) {{
      d.flags.forEach(f => {{
        const short = f.split(/\\s[—–-]\\s|:\\s|\\(/)[0].trim();
        flagsCell.append("span").attr("class", "flag-tag-sm").attr("title", f).text(short);
      }});
    }} else flagsCell.text("–");

    // Proposer summary (truncated)
    const propCell = tr.append("td").attr("class", "proposer-cell");
    const propText = d.proposer || "–";
    propCell.attr("title", propText).text(propText.length > 80 ? propText.slice(0, 77) + "…" : propText);

    // Diff toggle (show if there's a diff, proposer, or flags)
    const hasDiffContent = d.diff || d.proposer;
    const hasFlags = d.flags && d.flags.length;
    const diffCell = tr.append("td");
    if (hasDiffContent || hasFlags) {{
      diffCell.append("span").attr("class", "diff-toggle").text("show")
        .on("click", function() {{
          const row = d3.select(`#diff-${{d.track}}-${{d.exp}}`);
          const open = row.classed("open");
          row.classed("open", !open);
          d3.select(this).text(open ? "show" : "hide");
        }});
    }} else diffCell.text("–");

    // JSON link
    const jsonCell = tr.append("td");
    if (d.json_file) jsonCell.append("a").attr("href", d.json_file).text("json");
    else jsonCell.text("–");

    // Detail row (hidden by default): proposer explanation + flags + diff
    const hasFlagsOrContent = hasDiffContent || (d.flags && d.flags.length);
    if (hasFlagsOrContent) {{
      const diffRow = tbody.append("tr").attr("class", "diff-row").attr("id", `diff-${{d.track}}-${{d.exp}}`);
      const container = diffRow.append("td").attr("class", "diff-cell").attr("colspan", cols.length);

      // Proposer explanation
      if (d.proposer) {{
        container.append("div").attr("class", "proposer-note").text(d.proposer);
      }}

      // Stress test flags
      if (d.flags && d.flags.length) {{
        const flagsDiv = container.append("div").attr("class", "flags-row");
        d.flags.forEach(f => flagsDiv.append("span").attr("class", "flag-tag").text(f));
      }}

      // Syntax-highlighted diff
      if (d.diff) {{
        const pre = container.append("pre").attr("class", "diff-pre");
        d.diff.split("\\n").forEach(line => {{
          if (line.startsWith("+") && !line.startsWith("+++"))
            pre.append("span").attr("class", "add").text(line + "\\n");
          else if (line.startsWith("-") && !line.startsWith("---"))
            pre.append("span").attr("class", "del").text(line + "\\n");
          else if (line.startsWith("@@"))
            pre.append("span").attr("class", "hunk").text(line + "\\n");
          else pre.append("span").text(line + "\\n");
        }});
      }}
    }}
  }});
}}
</script>
</body>
</html>"""

    out = ITERATIONS_DIR / "index.html"
    out.write_text(html)
    return out
