"""Shared utilities for autoresearch-style iteration scripts.

Provides TSV logging, keep/discard decisions, cost tracking,
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
    """Squash-merge branch onto base. Returns True on success."""
    d = cwd or str(PROJ)
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
            print(f"    render stderr: {r.stderr.strip()}" if r.stderr.strip() else "")
            print(f"    render stdout: {r.stdout.strip()}" if r.stdout.strip() else "")
        return "PASS" in r.stdout
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
            "json_file": exp_file if (ITERATIONS_DIR / exp_file).exists() else None,
        })

    # Linked resources for the nav
    resources = {
        "history_tsv": "history.tsv",
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
  .target-title {{ font-size: 17px; font-weight: 600; margin: 0; }}
  .target-badge {{ font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }}
  .badge-block {{ background: #e3f2fd; color: #1565c0; }}
  .badge-prompt {{ background: #fce4ec; color: #c62828; }}
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

  .score-bar {{ display: inline-flex; gap: 2px; align-items: center; }}
  .score-pip {{ width: 6px; height: 14px; border-radius: 1px; }}

  .diff-toggle {{ cursor: pointer; color: #1565c0; font-size: 11px; user-select: none; }}
  .diff-toggle:hover {{ text-decoration: underline; }}
  .diff-row {{ display: none; }}
  .diff-row.open {{ display: table-row; }}
  .diff-cell {{ padding: 0; }}
  .diff-pre {{ margin: 0; padding: 8px 12px; background: #f5f5f5; font-family: "SF Mono", "Consolas", monospace;
    font-size: 11px; line-height: 1.5; overflow-x: auto; max-height: 400px; overflow-y: auto; white-space: pre; border-top: 1px solid #eee; }}
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

// --- Group by track/target ---
const groups = d3.group(experiments, d => `${{d.track}}/${{d.target}}`);
const content = d3.select("#content");

for (const [key, data] of groups) {{
  const [track, target] = key.split("/", 2);
  const section = content.append("div").attr("class", "target-section");

  // Header
  const header = section.append("div").attr("class", "target-header");
  header.append("div").attr("class", "target-title").text(target);
  header.append("span").attr("class", `target-badge badge-${{track}}`).text(track);

  const keeps = data.filter(d => d.decision === "keep");
  const discards = data.filter(d => d.decision === "discard");
  const totalCost = d3.sum(data, d => d.cost);
  const first = data[0], last = data[data.length - 1];
  const metricLabel = track === "block" ? "lines" : "time";
  section.append("div").attr("class", "target-meta")
    .text(`${{data.length}} experiments · ${{keeps.length}} kept · ${{discards.length}} discarded · $${{totalCost.toFixed(2)}} · ${{metricLabel}}: ${{first.metric}}→${{last.decision === "keep" || last.decision === "baseline" ? last.metric : keeps.length ? keeps[keeps.length-1].metric : first.metric}}`);

  // --- Sparkline chart ---
  const margin = {{top: 10, right: 16, bottom: 24, left: 44}};
  const width = 520, height = 120;
  const svg = section.append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

  const x = d3.scaleLinear().domain([0, data.length - 1]).range([0, width]);
  const yExtent = d3.extent(data, d => d.metric);
  const y = d3.scaleLinear().domain(yExtent).nice().range([height, 0]);

  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${{height}})`)
    .call(d3.axisBottom(x).ticks(Math.min(data.length, 8)).tickFormat(d3.format("d")));
  svg.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(4));

  let best = data[0]?.metric || 0;
  const bestPts = data.map((d, i) => {{
    if (d.decision === "keep" || d.decision === "baseline") best = d.metric;
    return {{ i, best }};
  }});
  svg.append("path").attr("class", "best-line")
    .attr("d", d3.line().x(d => x(d.i)).y(d => y(d.best))(bestPts));

  svg.selectAll(".dot").data(data).join("circle")
    .attr("cx", (d, i) => x(i)).attr("cy", d => y(d.metric)).attr("r", 4)
    .attr("class", d => `dot-${{d.decision === "keep" ? "keep" : d.decision === "baseline" ? "baseline" : "discard"}}`);

  // --- Experiment table ---
  const table = section.append("table");
  const cols = ["#", "Decision", metricLabel, "Δ", "Composite", "Scores", "Cost", "Description", "Diff", "JSON"];
  table.append("thead").append("tr").selectAll("th").data(cols).join("th").text(d => d);
  const tbody = table.append("tbody");

  const scoreDims = ["visual_critic", "encoding_integrity", "stress_test", "cognitive_load"];
  const scoreColor = d3.scaleLinear().domain([1, 5, 10]).range(["#c62828", "#f9a825", "#2e7d32"]);

  data.forEach((d, idx) => {{
    const cls = d.decision === "keep" ? "keep" : d.decision === "baseline" ? "baseline" : "discard";
    const tr = tbody.append("tr");
    tr.append("td").text(d.exp);
    tr.append("td").attr("class", cls).text(d.decision);
    tr.append("td").attr("class", "mono").text(d.metric || "–");
    tr.append("td").attr("class", "mono").text(d.delta || "–");

    // Composite
    const comp = d.composite_after ?? d.scores?.composite;
    tr.append("td").attr("class", "mono").text(comp != null ? comp.toFixed(1) : "–");

    // Score pips
    const scoreCell = tr.append("td");
    if (d.scores && Object.keys(d.scores).length) {{
      const bar = scoreCell.append("span").attr("class", "score-bar");
      scoreDims.forEach(dim => {{
        const v = d.scores[dim];
        if (v != null) bar.append("span").attr("class", "score-pip")
          .attr("title", `${{dim}}: ${{v}}`).style("background", scoreColor(v));
      }});
    }} else scoreCell.text("–");

    tr.append("td").attr("class", "mono").text(`$${{d.cost.toFixed(2)}}`);
    tr.append("td").text(d.description);

    // Diff toggle
    const diffCell = tr.append("td");
    if (d.diff) {{
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

    // Diff row (hidden by default)
    if (d.diff) {{
      const diffRow = tbody.append("tr").attr("class", "diff-row").attr("id", `diff-${{d.track}}-${{d.exp}}`);
      const pre = diffRow.append("td").attr("class", "diff-cell").attr("colspan", cols.length)
        .append("pre").attr("class", "diff-pre");
      // Syntax-highlight the diff
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
  }});
}}
</script>
</body>
</html>"""

    out = ITERATIONS_DIR / "index.html"
    out.write_text(html)
    return out
