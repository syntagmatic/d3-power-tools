"""Shared utilities for autoresearch-style iteration scripts.

Provides TSV logging, keep/discard decisions, cost tracking,
git helpers, and progress HTML generation.
"""
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
    """Create and checkout a new branch. No-op if already on it."""
    current = git_branch_name(cwd)
    if current == name:
        return
    subprocess.run(["git", "checkout", "-b", name],
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


# === Keep/discard decisions ===

def decide_block(composite_before, composite_after, lines_before, lines_after):
    """Block track: optimize LOC, constrain composite."""
    composite_delta = composite_after - composite_before
    if composite_delta < -0.3:
        return "discard", "quality regression"
    if lines_after >= lines_before:
        return "discard", "didn't get shorter"
    return "keep", f"-{lines_before - lines_after} lines"


def decide_prompt(time_before, time_after, features_pass):
    """Prompt track: optimize gen time, constrain features."""
    if not features_pass:
        return "discard", "missing required features"
    if time_after >= time_before * 0.85:
        return "discard", "not meaningfully faster"
    return "keep", f"-{time_before - time_after:.0f}s"


# === Cost tracking ===

class CostTracker:
    def __init__(self, budget_usd):
        self.budget_usd = budget_usd
        self.spent_usd = 0.0

    def add(self, cost_usd):
        self.spent_usd += cost_usd

    def remaining(self):
        return self.budget_usd - self.spent_usd

    def over_budget(self):
        return self.spent_usd >= self.budget_usd

    def summary(self):
        return f"${self.spent_usd:.2f} / ${self.budget_usd:.2f}"


# === TSV logging ===

def ensure_iterations_dir():
    ITERATIONS_DIR.mkdir(parents=True, exist_ok=True)


def tsv_path():
    return ITERATIONS_DIR / "history.tsv"


TSV_HEADER = "exp\ttrack\ttarget\tmetric\tdelta\tdecision\tcost\tdescription\n"


def append_tsv(exp_id, track, target, metric, delta, decision, cost, description):
    ensure_iterations_dir()
    path = tsv_path()
    if not path.exists():
        path.write_text(TSV_HEADER)
    with open(path, "a") as f:
        delta_str = f"{delta:+.1f}" if isinstance(delta, float) else str(delta)
        f.write(f"{exp_id}\t{track}\t{target}\t{metric}\t{delta_str}\t{decision}\t{cost:.2f}\t{description}\n")


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
        return "PASS" in r.stdout
    except subprocess.TimeoutExpired:
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


# === Progress HTML ===

def generate_progress_html():
    """Generate progress.html from history.tsv."""
    ensure_iterations_dir()
    path = tsv_path()
    if not path.exists():
        return

    lines = path.read_text().strip().split("\n")
    if len(lines) <= 1:
        return

    # Parse TSV into records
    records = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) >= 8:
            records.append({
                "exp": int(parts[0]),
                "track": parts[1],
                "target": parts[2],
                "metric": float(parts[3]) if parts[3].replace(".", "").replace("-", "").isdigit() else 0,
                "delta": parts[4],
                "decision": parts[5],
                "cost": float(parts[6]),
                "description": parts[7],
            })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Iteration Progress</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 32px; background: #fafafa; color: #222; }}
  h1 {{ font-size: 22px; font-weight: 400; margin: 0 0 4px; }} h1 b {{ font-weight: 600; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 20px; }}
  .target-section {{ margin-bottom: 40px; }}
  .target-title {{ font-size: 16px; font-weight: 600; margin: 0 0 12px; }}
  .target-meta {{ font-size: 12px; color: #888; margin-bottom: 8px; }}
  svg {{ overflow: visible; }}
  .dot-keep {{ fill: #2e7d32; }}
  .dot-discard {{ fill: #bbb; }}
  .dot-baseline {{ fill: #1565c0; }}
  .best-line {{ stroke: #2e7d32; stroke-width: 1.5; fill: none; }}
  .axis text {{ font-size: 11px; fill: #666; }}
  .axis line, .axis path {{ stroke: #ddd; }}
  table {{ border-collapse: collapse; font-size: 12px; margin-top: 12px; }}
  th, td {{ padding: 4px 10px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ font-weight: 600; color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; }}
  .keep {{ color: #2e7d32; font-weight: 600; }}
  .discard {{ color: #999; }}
  .baseline {{ color: #1565c0; }}
</style>
</head>
<body>
<h1><b>Iteration Progress</b></h1>
<p class="meta">{len(records)} experiments &middot; generated {time.strftime("%Y-%m-%d %H:%M")}</p>
<script>
const records = {json.dumps(records, ensure_ascii=False)};

// Group by track+target
const groups = d3.group(records, d => `${{d.track}}/${{d.target}}`);

for (const [key, data] of groups) {{
  const [track, target] = key.split("/", 2);
  const section = d3.select("body").append("div").attr("class", "target-section");

  const keeps = data.filter(d => d.decision === "keep");
  const totalCost = d3.sum(data, d => d.cost);
  section.append("div").attr("class", "target-title").text(`${{track}}: ${{target}}`);
  section.append("div").attr("class", "target-meta")
    .text(`${{data.length}} experiments, ${{keeps.length}} kept, $${{totalCost.toFixed(2)}} spent`);

  // Chart
  const margin = {{top: 12, right: 20, bottom: 28, left: 50}};
  const width = 600, height = 180;
  const svg = section.append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

  const x = d3.scaleLinear()
    .domain([0, data.length - 1]).range([0, width]);
  const y = d3.scaleLinear()
    .domain(d3.extent(data, d => d.metric)).nice().range([height, 0]);

  svg.append("g").attr("class", "axis")
    .attr("transform", `translate(0,${{height}})`)
    .call(d3.axisBottom(x).ticks(Math.min(data.length, 10)).tickFormat(d3.format("d")));
  svg.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5));

  // Running best line
  let best = data[0]?.metric || 0;
  const isLowerBetter = track === "prompt"; // gen time: lower better. LOC: lower better for blocks too.
  const bestPoints = [];
  for (let i = 0; i < data.length; i++) {{
    const d = data[i];
    if (d.decision === "keep" || d.decision === "baseline") {{
      best = d.metric;
    }}
    bestPoints.push({{ i, best }});
  }}

  svg.append("path").attr("class", "best-line")
    .attr("d", d3.line().x((d, i) => x(d.i)).y(d => y(d.best))(bestPoints));

  // Dots
  svg.selectAll(".dot").data(data).join("circle")
    .attr("cx", (d, i) => x(i)).attr("cy", d => y(d.metric)).attr("r", 4)
    .attr("class", d => d.decision === "keep" ? "dot-keep" : d.decision === "baseline" ? "dot-baseline" : "dot-discard");

  // Table
  const table = section.append("table");
  table.append("thead").append("tr").selectAll("th")
    .data(["#", "Decision", "Metric", "Delta", "Cost", "Description"])
    .join("th").text(d => d);
  const rows = table.append("tbody").selectAll("tr").data(data).join("tr");
  rows.each(function(d) {{
    const tr = d3.select(this);
    const cls = d.decision === "keep" ? "keep" : d.decision === "baseline" ? "baseline" : "discard";
    tr.append("td").text(d.exp);
    tr.append("td").attr("class", cls).text(d.decision);
    tr.append("td").text(d.metric);
    tr.append("td").text(d.delta);
    tr.append("td").text(`$${{d.cost.toFixed(2)}}`);
    tr.append("td").text(d.description);
  }});
}}
</script>
</body>
</html>"""

    out = ITERATIONS_DIR / "progress.html"
    out.write_text(html)
    return out
