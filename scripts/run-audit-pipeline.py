#!/usr/bin/env python3
"""
Audit pipeline for D3 Power Tools blocks.

Renders blocks, runs 4 inspection tools in isolated subprocesses,
writes one compact JSON per run to evals/runs/.

Usage:
  python3 scripts/run-audit-pipeline.py                       # v1 blocks 85-93
  python3 scripts/run-audit-pipeline.py --blocks 1-105        # all blocks
  python3 scripts/run-audit-pipeline.py --block-set v0        # v0 blocks
  python3 scripts/run-audit-pipeline.py --model opus          # different model
  python3 scripts/run-audit-pipeline.py --skip-render         # reuse temp screenshots
  python3 scripts/run-audit-pipeline.py --report              # regenerate report from runs/
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJ = Path(__file__).resolve().parent.parent
TEST_SCRIPT = PROJ / "scripts" / "test-viz.py"
ANCHORS_FILE = PROJ / "evals" / "anchors.json"
RUNS_DIR = PROJ / "evals" / "runs"
SCREENSHOT_BASE = PROJ / "temp" / "audit-screenshots"
REPORT_FILE = PROJ / "evals" / "report.html"

TOOLS = {
    "visual_critic":       PROJ / "meta" / "visual-critic" / "SKILL.md",
    "encoding_integrity":  PROJ / "meta" / "encoding-integrity" / "SKILL.md",
    "stress_test":         PROJ / "meta" / "stress-test" / "SKILL.md",
    "cognitive_load":      PROJ / "meta" / "cognitive-load" / "SKILL.md",
}

WEIGHTS = {"visual_critic": 0.30, "encoding_integrity": 0.25, "cognitive_load": 0.25, "stress_test": 0.20}

MODEL_IDS = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())


def git_sha():
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, cwd=str(PROJ))
        return r.stdout.strip()
    except Exception:
        return "unknown"


def git_skill_shas():
    shas = {}
    for name, path in TOOLS.items():
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%h", "--", str(path)],
                               capture_output=True, text=True, cwd=str(PROJ))
            shas[name] = r.stdout.strip()
        except Exception:
            shas[name] = "unknown"
    return shas


def cli_version():
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True)
        return r.stdout.strip().split("\n")[0]
    except Exception:
        return "unknown"


def run_tag(block_set, model):
    """Generate a filename-safe tag: 2026-03-29T08-v1-sonnet."""
    ts = time.strftime("%Y-%m-%dT%H%M")
    return f"{ts}-{block_set.replace('/', '-')}-{model}"


def parse_block_range(spec):
    parts = spec.split("-", 1) if "-" in spec and not spec.startswith("0") else None
    if parts and len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        lo, hi = int(parts[0]), int(parts[1])
        return [b for b in MANIFEST["blocks"] if lo <= int(b["id"].split("-")[0]) <= hi]
    if spec.isdigit():
        num = int(spec)
        return [b for b in MANIFEST["blocks"] if int(b["id"].split("-")[0]) == num]
    # Match by full ID or ID prefix
    return [b for b in MANIFEST["blocks"] if b["id"] == spec or b["id"].startswith(spec)]


# === Phase 1: Render ===

def run_render(blocks, block_set, ss_dir, block_dir=None):
    ss_dir.mkdir(parents=True, exist_ok=True)
    bdir = Path(block_dir) if block_dir else PROJ / "blocks" / block_set
    results = {}
    for b in blocks:
        bid = b["id"]
        html = bdir / f"{bid}.html"
        ss = ss_dir / f"{bid}.png"
        wait = b.get("wait_for", "svg")
        print(f"  render {bid}...", end=" ", flush=True)
        try:
            r = subprocess.run(
                ["python3", str(TEST_SCRIPT), str(html), "--out", str(ss), "--wait-for", wait],
                capture_output=True, text=True, timeout=30, cwd=str(PROJ))
            passed = "PASS" in r.stdout
        except subprocess.TimeoutExpired:
            passed = False
        results[bid] = passed
        print("PASS" if passed else "FAIL")
    ok = sum(results.values())
    print(f"  Render: {ok}/{len(results)} passed\n")
    return results


# === Phase 2: Audit ===

def build_prompt(tool_name, skill_content, ss_path, html_path, out_path):
    if tool_name == "stress_test":
        fmt = '{"score":<1-10>,"flags":["<failed_check_names>"],"note":"<1 sentence>"}'
    else:
        fmt = '{"score":<1-10>,"note":"<1 sentence what works or doesn\'t>"}'
    return f"""Evaluate this D3.js visualization.

## Criteria
{skill_content}

## Task
1. Read the screenshot at {ss_path}
2. Read the HTML source at {html_path}
3. Score 1-10 per the criteria. Write JSON to {out_path}

Format: {fmt}
Write the file now. No markdown, no explanation."""


CLAUDE_BIN = "/usr/local/share/npm-global/bin/claude"


def run_one_audit(bid, tool, skill_path, ss_path, html_path, out_path, model):
    skill_content = skill_path.read_text()
    prompt = build_prompt(tool, skill_content, ss_path, html_path, out_path)
    bare = tempfile.mkdtemp(prefix="audit-")
    try:
        subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--allowedTools", "Read,Write",
             "--max-turns", "25", "--model", model, "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=120, cwd=bare)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    finally:
        try: os.rmdir(bare)
        except OSError: pass

    if out_path.exists() and out_path.stat().st_size > 5:
        try:
            return json.loads(out_path.read_text())
        except json.JSONDecodeError:
            pass
    return None


def run_audits(blocks, render_results, block_set, model, parallel, ss_dir, block_dir=None):
    tmp_dir = ss_dir.parent / "audit-tmp" / block_set
    tmp_dir.mkdir(parents=True, exist_ok=True)
    bdir = Path(block_dir) if block_dir else PROJ / "blocks" / block_set
    results = {}  # bid -> {tool: audit_data}
    tasks = []
    stats = {"pass": 0, "fail": 0}

    for b in blocks:
        bid = b["id"]
        if not render_results.get(bid):
            continue
        ss = ss_dir / f"{bid}.png"
        html = bdir / f"{bid}.html"
        if not ss.exists():
            continue
        results[bid] = {}
        for tool, skill_path in TOOLS.items():
            out = tmp_dir / f"{bid}-{tool}.json"
            # Resume: skip if already done
            if out.exists() and out.stat().st_size > 5:
                try:
                    data = json.loads(out.read_text())
                    if "score" in data:
                        results[bid][tool] = data
                        stats["pass"] += 1
                        continue
                except json.JSONDecodeError:
                    pass
            tasks.append((bid, tool, skill_path, str(ss), str(html), out, model))

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {pool.submit(run_one_audit, *t): (t[0], t[1]) for t in tasks}
        for f in as_completed(futures):
            bid, tool = futures[f]
            data = f.result()
            if data and "score" in data:
                results[bid][tool] = data
                stats["pass"] += 1
                print(f"  {bid}/{tool}: {data['score']}")
            else:
                stats["fail"] += 1
                print(f"  {bid}/{tool}: FAIL")

    print(f"\n  Audits: {stats['pass']} pass, {stats['fail']} fail\n")
    return results


# === Phase 3: Compact run file ===

def write_run(blocks, render_results, audit_results, block_set, model, tag):
    anchors = {}
    if ANCHORS_FILE.exists():
        anchors = json.loads(ANCHORS_FILE.read_text()).get("anchors", {})

    block_scores = {}
    for b in blocks:
        bid = b["id"]
        rendered = render_results.get(bid, False)
        entry = {"render": rendered}

        audits = audit_results.get(bid, {})
        for tool in TOOLS:
            if tool in audits:
                entry[tool] = audits[tool]["score"]
                if tool == "stress_test":
                    flags = audits[tool].get("flags", [])
                    if flags:
                        entry["flags"] = flags
                note = audits[tool].get("note", "")
                if note:
                    entry[f"{tool}_note"] = note
            else:
                entry[tool] = None

        # Composite
        if rendered and all(entry.get(t) is not None for t in TOOLS):
            entry["composite"] = round(sum(entry[t] * WEIGHTS[t] for t in TOOLS), 1)
        else:
            entry["composite"] = None

        block_scores[bid] = entry

    run_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_sha": git_sha(),
        "skill_shas": git_skill_shas(),
        "block_set": block_set,
        "model": MODEL_IDS.get(model, model),
        "cli_version": cli_version(),
        "blocks": block_scores,
    }

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"{tag}.json"
    out.write_text(json.dumps(run_data, indent=2, ensure_ascii=False))

    # Summary
    composites = [s["composite"] for s in block_scores.values() if s["composite"] is not None]
    if composites:
        print(f"  Composite avg: {sum(composites)/len(composites):.1f} (n={len(composites)})")

    # Calibration drift
    drifts = []
    for bid, s in block_scores.items():
        if bid in anchors:
            for t in TOOLS:
                if s.get(t) is not None and t in anchors[bid]:
                    d = abs(s[t] - anchors[bid][t])
                    drifts.append(d)
    if drifts:
        over2 = sum(1 for d in drifts if d > 2)
        print(f"  Calibration: {len(drifts)} comparisons, {over2} beyond ±2")

    print(f"  Run file: {out}")
    return out


# === Report generation ===

def generate_report():
    """Read all run files, generate a comparative heatmap."""
    run_files = sorted(RUNS_DIR.glob("*.json"))
    if not run_files:
        print("No run files found"); return

    runs = []
    for f in run_files:
        try:
            runs.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            pass

    report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Audit Report</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 32px; background: #fafafa; color: #222; }}
  h1 {{ font-size: 22px; font-weight: 400; margin: 0 0 4px; }} h1 b {{ font-weight: 600; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 20px; }}
  .run-selector {{ margin-bottom: 16px; font-size: 13px; }}
  select {{ font-size: 13px; padding: 4px 8px; }}
  .cell {{ stroke: #fff; stroke-width: 1.5; }}
  .label {{ font-size: 11px; fill: #333; }}
  .score {{ font-size: 11px; fill: #333; font-weight: 500; text-anchor: middle; dominant-baseline: central; }}
  .col-hdr {{ font-size: 10px; fill: #666; text-anchor: middle; text-transform: uppercase; letter-spacing: 0.04em; }}
</style>
</head>
<body>
<h1><b>Audit Report</b></h1>
<p class="meta">{len(runs)} run(s) · generated {time.strftime("%Y-%m-%d %H:%M")}</p>
<div class="run-selector">
  Run: <select id="run-select"></select>
</div>
<div id="chart"></div>
<script>
const runs = {json.dumps(runs, ensure_ascii=False)};
const dims = ["render","visual_critic","encoding_integrity","stress_test","cognitive_load","composite"];
const labels = ["Render","Visual Critic","Encoding","Stress","Cognitive","Comp"];
const sel = document.getElementById("run-select");
runs.forEach((r,i) => {{
  const o = document.createElement("option");
  o.value = i;
  const d = r.timestamp.slice(0,16).replace("T"," ");
  o.textContent = `${{d}} · ${{r.block_set}} · ${{r.model}}`;
  sel.appendChild(o);
}});
sel.value = runs.length - 1;

const margin = {{top: 36, right: 16, bottom: 16, left: 200}};
const cellW = 62, cellH = 26;
const color = d3.scaleSequential(d3.interpolateRdYlGn).domain([1, 10]);

function draw(idx) {{
  const run = runs[idx];
  const bids = Object.keys(run.blocks).sort();
  const w = margin.left + dims.length * cellW + margin.right;
  const h = margin.top + (bids.length + 1) * cellH + margin.bottom;

  d3.select("#chart").selectAll("*").remove();
  const svg = d3.select("#chart").append("svg").attr("width", w).attr("height", h);
  const g = svg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

  g.selectAll(".col-hdr").data(labels).join("text").attr("class","col-hdr")
    .attr("x",(d,i) => i*cellW+cellW/2).attr("y",-10).text(d=>d);

  bids.forEach((bid,row) => {{
    const s = run.blocks[bid];
    const short = bid.replace(/^\\d+-/,"").replace(/-/g," ");
    g.append("text").attr("class","label")
      .attr("x",-6).attr("y",row*cellH+cellH/2)
      .attr("text-anchor","end").attr("dominant-baseline","central")
      .text(`${{bid.split("-")[0]}} ${{short}}`);
    dims.forEach((dim,col) => {{
      const v = dim==="render" ? (s.render?10:1) : s[dim];
      const x=col*cellW, y=row*cellH;
      g.append("rect").attr("class","cell")
        .attr("x",x).attr("y",y).attr("width",cellW).attr("height",cellH)
        .attr("fill",v!=null?color(v):"#eee").attr("rx",2);
      if (v!=null) {{
        const lbl = dim==="render"?(s.render?"✓":"✗"):dim==="composite"?v.toFixed(1):v;
        g.append("text").attr("class","score")
          .attr("x",x+cellW/2).attr("y",y+cellH/2).text(lbl);
      }}
    }});
  }});

  // Average row
  const ay = bids.length * cellH + 4;
  g.append("text").attr("class","label").attr("x",-6).attr("y",ay+cellH/2)
    .attr("text-anchor","end").attr("dominant-baseline","central")
    .attr("font-weight",600).text("Average");
  dims.forEach((dim,col) => {{
    if (dim==="render") return;
    const vals = bids.map(b=>run.blocks[b][dim]).filter(v=>v!=null);
    if (!vals.length) return;
    const avg = (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1);
    const x=col*cellW;
    g.append("rect").attr("class","cell")
      .attr("x",x).attr("y",ay).attr("width",cellW).attr("height",cellH)
      .attr("fill",color(+avg)).attr("rx",2).attr("stroke-width",2);
    g.append("text").attr("class","score").attr("x",x+cellW/2).attr("y",ay+cellH/2)
      .attr("font-weight",600).text(avg);
  }});
}}

sel.addEventListener("change", () => draw(+sel.value));
draw(runs.length - 1);
</script>
</body>
</html>"""

    REPORT_FILE.write_text(report)
    print(f"  Report: {REPORT_FILE} ({len(runs)} runs)")


# === Main ===

def main():
    ap = argparse.ArgumentParser(description="Audit pipeline")
    ap.add_argument("--blocks", default="85-93")
    ap.add_argument("--block-set", default="v1", help="e.g. v1-claude-sonnet-4-6")
    ap.add_argument("--block-dir", default=None, help="Override block directory (default: blocks/{block-set})")
    ap.add_argument("--model", default="sonnet", help="sonnet, opus, or haiku")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--report", action="store_true", help="Just regenerate report from existing runs")
    args = ap.parse_args()

    if args.report:
        generate_report()
        return

    blocks = parse_block_range(args.blocks)
    if not blocks:
        print(f"No blocks match '{args.blocks}'"); sys.exit(1)

    block_dir = Path(args.block_dir) if args.block_dir else PROJ / "blocks" / args.block_set
    if not block_dir.is_dir():
        print(f"Not found: {block_dir}"); sys.exit(1)

    blocks = [b for b in blocks if (block_dir / f"{b['id']}.html").exists()]
    tag = run_tag(args.block_set, args.model)

    print(f"=== Audit: {tag} ===")
    print(f"Blocks: {args.blocks} ({len(blocks)}, set: {args.block_set})")
    if args.block_dir:
        print(f"Block dir: {block_dir}")
    print(f"Model: {MODEL_IDS.get(args.model, args.model)}")
    print(f"Git: {git_sha()}\n")

    ss_dir = SCREENSHOT_BASE / args.block_set

    # Phase 1
    if args.skip_render and ss_dir.exists() and any(ss_dir.glob("*.png")):
        render_results = {b["id"]: (ss_dir / f"{b['id']}.png").exists() for b in blocks}
        print(f"Phase 1: Reusing {sum(render_results.values())} screenshots\n")
    else:
        print("Phase 1: Render")
        render_results = run_render(blocks, args.block_set, ss_dir, block_dir=str(block_dir))

    # Phase 2
    print("Phase 2: Audit")
    audit_results = run_audits(blocks, render_results, args.block_set, args.model, args.parallel, ss_dir, block_dir=str(block_dir))

    # Phase 3
    print("Phase 3: Write run")
    write_run(blocks, render_results, audit_results, args.block_set, args.model, tag)

    # Phase 4
    print("\nPhase 4: Report")
    generate_report()

    print(f"\n=== Done: {tag} ===")


if __name__ == "__main__":
    main()
