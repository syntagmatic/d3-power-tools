#!/usr/bin/env python3
"""
Audit pipeline for D3 Power Tools blocks.

Render-tests blocks, runs 4 inspection tools in isolated subprocesses,
aggregates scores, compares to human anchors, and generates a D3 heatmap report.

Usage:
  python3 scripts/run-audit-pipeline.py                  # blocks 85-93
  python3 scripts/run-audit-pipeline.py --blocks 85-105  # wider range
  python3 scripts/run-audit-pipeline.py --blocks 85-85   # single block
  python3 scripts/run-audit-pipeline.py --skip-render     # reuse screenshots
  python3 scripts/run-audit-pipeline.py --persist         # save to git-tracked file
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
ANCHORS_FILE = PROJ / "meta" / "evals" / "audit-anchors.json"
OUTPUT_DIR = PROJ / "temp" / "audit-pipeline"
PERSIST_FILE = PROJ / "meta" / "evals" / "audit-history.json"

TOOLS = {
    "polish": PROJ / "meta" / "polish-tool" / "SKILL.md",
    "level":  PROJ / "meta" / "level-tool" / "SKILL.md",
    "stress": PROJ / "meta" / "stress-tool" / "SKILL.md",
    "scope":  PROJ / "meta" / "scope-tool" / "SKILL.md",
}

WEIGHTS = {"polish": 0.30, "level": 0.25, "scope": 0.25, "stress": 0.20}

MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())


def parse_block_range(spec):
    """Parse '85-93' or '85-85' into list of block IDs."""
    parts = spec.split("-", 1) if "-" in spec and not spec.startswith("0") else None
    if parts and len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        lo, hi = int(parts[0]), int(parts[1])
        blocks = []
        for b in MANIFEST["blocks"]:
            num = int(b["id"].split("-")[0])
            if lo <= num <= hi:
                blocks.append(b)
        return blocks
    # Single block number
    if spec.isdigit():
        num = int(spec)
        return [b for b in MANIFEST["blocks"] if int(b["id"].split("-")[0]) == num]
    return []


# === Phase 1: Render Tests ===

def run_render_tests(blocks, round_dir):
    """Run test-viz.py on each block, collect screenshots and pass/fail."""
    ss_dir = round_dir / "screenshots"
    ss_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for b in blocks:
        bid = b["id"]
        html_path = PROJ / "blocks" / "v1" / f"{bid}.html"
        ss_path = ss_dir / f"{bid}.png"
        wait = b.get("wait_for", "svg")

        print(f"  render {bid}...", end=" ", flush=True)
        try:
            r = subprocess.run(
                ["python3", str(TEST_SCRIPT), str(html_path),
                 "--out", str(ss_path), "--wait-for", wait],
                capture_output=True, text=True, timeout=30, cwd=str(PROJ)
            )
            passed = "PASS" in r.stdout
            results[bid] = {"passed": passed, "screenshot": str(ss_path)}
            print("PASS" if passed else "FAIL")
        except subprocess.TimeoutExpired:
            results[bid] = {"passed": False, "screenshot": None}
            print("TIMEOUT")

    out = round_dir / "render-results.json"
    out.write_text(json.dumps(results, indent=2))
    passed = sum(1 for r in results.values() if r["passed"])
    print(f"  Render: {passed}/{len(results)} passed\n")
    return results


# === Phase 2: Isolated Audit Evaluations ===

def build_audit_prompt(tool_name, skill_content, screenshot_path, html_path, output_path):
    """Build the prompt for an isolated audit subprocess."""
    if tool_name == "stress":
        output_format = '{"score": <1-10>, "flags": {"update_storm": "pass|fail", "infinite_loop": "pass|fail", "stale_closure": "pass|fail", "handoff_race": "pass|fail", "mouse_touch_fight": "pass|fail"}, "details": "<1-2 sentences>"}'
    else:
        output_format = '{"score": <1-10>, "context": "<what is this viz>", "first_impression": "<1 sentence>", "what_works": "<1-2 specifics>", "what_doesnt": "<1-2 specifics>"}'

    return f"""You are evaluating a D3.js visualization. Read the criteria below, then analyze the visualization.

## Evaluation Criteria

{skill_content}

## Your Task

1. Read the screenshot at {screenshot_path}
2. Read the HTML source at {html_path}
3. Evaluate according to the criteria above
4. Write your evaluation as JSON to {output_path}

Output ONLY this JSON format (no markdown, no explanation):
{output_format}

Write the JSON file now."""


def run_single_audit(bid, tool_name, skill_path, screenshot_path, html_path, audit_dir, model):
    """Run one audit tool against one block in an isolated subprocess."""
    output_path = audit_dir / f"{tool_name}.json"
    if output_path.exists() and output_path.stat().st_size > 10:
        return ("skip", bid, tool_name)

    skill_content = skill_path.read_text()
    prompt = build_audit_prompt(
        tool_name, skill_content,
        screenshot_path, html_path, output_path
    )

    # Isolation: run from a bare temp directory
    bare_dir = tempfile.mkdtemp(prefix="audit-bare-")

    try:
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--allowedTools", "Read,Write",
             "--max-turns", "3",
             "--model", model,
             "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=120,
            cwd=bare_dir
        )
    except subprocess.TimeoutExpired:
        return ("fail", bid, tool_name, "timeout")
    finally:
        # Clean up bare dir
        try:
            os.rmdir(bare_dir)
        except OSError:
            pass

    if output_path.exists() and output_path.stat().st_size > 10:
        try:
            json.loads(output_path.read_text())
            return ("pass", bid, tool_name)
        except json.JSONDecodeError:
            return ("fail", bid, tool_name, "invalid json")

    return ("fail", bid, tool_name, "no output")


def run_audits(blocks, render_results, round_dir, parallel, model):
    """Run all audit tools on all blocks."""
    tasks = []
    for b in blocks:
        bid = b["id"]
        rr = render_results.get(bid, {})
        ss = rr.get("screenshot")
        html_path = PROJ / "blocks" / "v1" / f"{bid}.html"
        audit_dir = round_dir / "audits" / bid
        audit_dir.mkdir(parents=True, exist_ok=True)

        if not ss or not Path(ss).exists():
            print(f"  skip {bid} (no screenshot)")
            continue

        for tool_name, skill_path in TOOLS.items():
            tasks.append((bid, tool_name, skill_path, ss, str(html_path), audit_dir, model))

    results = {"pass": 0, "fail": 0, "skip": 0}

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {
            pool.submit(run_single_audit, *t): (t[0], t[1])
            for t in tasks
        }
        for f in as_completed(futures):
            bid, tool = futures[f]
            r = f.result()
            status = r[0]
            results[status] += 1
            if status == "pass":
                print(f"  {bid}/{tool}: PASS")
            elif status == "skip":
                print(f"  {bid}/{tool}: SKIP (exists)")
            else:
                reason = r[3] if len(r) > 3 else "unknown"
                print(f"  {bid}/{tool}: FAIL ({reason})")

    print(f"\n  Audits: {results['pass']} pass, {results['fail']} fail, {results['skip']} skip\n")
    return results


# === Phase 3: Aggregate Scores ===

def aggregate(blocks, render_results, round_dir, round_num):
    """Read audit JSONs, compute composites, compare to anchors."""
    anchors = {}
    if ANCHORS_FILE.exists():
        anchors = json.loads(ANCHORS_FILE.read_text()).get("anchors", {})

    scores = {}
    for b in blocks:
        bid = b["id"]
        entry = {"render": render_results.get(bid, {}).get("passed", False)}
        audit_dir = round_dir / "audits" / bid

        for tool in TOOLS:
            path = audit_dir / f"{tool}.json"
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    entry[tool] = data.get("score", None)
                    if tool == "stress":
                        entry["stress_flags"] = data.get("flags", {})
                except (json.JSONDecodeError, KeyError):
                    entry[tool] = None
            else:
                entry[tool] = None

        # Composite
        if entry["render"] and all(entry.get(t) is not None for t in TOOLS):
            entry["composite"] = round(sum(
                entry[t] * WEIGHTS[t] for t in TOOLS
            ), 2)
        else:
            entry["composite"] = None

        # Calibration drift
        if bid in anchors:
            drift = {}
            for t in TOOLS:
                if entry.get(t) is not None and t in anchors[bid]:
                    drift[t] = entry[t] - anchors[bid][t]
            entry["drift"] = drift

        scores[bid] = entry

    # Write round scores
    out = round_dir / "scores.json"
    out.write_text(json.dumps(scores, indent=2, ensure_ascii=False))

    # Append to history
    history_path = OUTPUT_DIR / "history.json"
    history = {"rounds": []}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text())
        except json.JSONDecodeError:
            pass

    history["rounds"].append({
        "round": round_num,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "blocks": scores
    })
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    # Summary
    composites = [s["composite"] for s in scores.values() if s["composite"] is not None]
    if composites:
        print(f"  Composite avg: {sum(composites)/len(composites):.1f} (n={len(composites)})")

    drifts = []
    for s in scores.values():
        if "drift" in s:
            drifts.extend(abs(v) for v in s["drift"].values())
    if drifts:
        over2 = sum(1 for d in drifts if d > 2)
        print(f"  Calibration: {len(drifts)} comparisons, {over2} beyond ±2")

    return scores


# === Phase 4: Report ===

def generate_report(round_dir, round_num):
    """Generate a D3 heatmap of audit results."""
    history_path = OUTPUT_DIR / "history.json"
    history = json.loads(history_path.read_text())

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Audit Pipeline — Round {round_num}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 32px; background: #fafafa; }}
  h1 {{ font-size: 22px; font-weight: 400; margin: 0 0 4px; }}
  h1 b {{ font-weight: 600; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 24px; }}
  .heatmap {{ font-size: 13px; }}
  .cell {{ stroke: #fff; stroke-width: 1.5; }}
  .label {{ font-size: 12px; fill: #333; }}
  .score {{ font-size: 11px; fill: #333; font-weight: 500; text-anchor: middle; dominant-baseline: central; }}
  .delta {{ font-size: 9px; fill: #666; text-anchor: middle; }}
  .col-header {{ font-size: 11px; fill: #666; text-anchor: middle; text-transform: uppercase; letter-spacing: 0.05em; }}
  .legend {{ font-size: 11px; fill: #666; }}
</style>
</head>
<body>
<h1><b>Audit Pipeline</b> — Round {round_num}</h1>
<p class="meta">Generated {time.strftime("%Y-%m-%d %H:%M")}</p>
<div id="chart"></div>
<script>
const history = {json.dumps(history, ensure_ascii=False)};
const current = history.rounds[history.rounds.length - 1];
const prev = history.rounds.length > 1 ? history.rounds[history.rounds.length - 2] : null;
const dims = ["render", "polish", "level", "stress", "scope", "composite"];
const dimLabels = ["Render", "Polish", "Level", "Stress", "Scope", "Composite"];
const blocks = Object.keys(current.blocks).sort();

const margin = {{top: 40, right: 20, bottom: 20, left: 220}};
const cellW = 70, cellH = 32;
const w = margin.left + dims.length * cellW + margin.right;
const h = margin.top + blocks.length * cellH + margin.bottom;

const color = d3.scaleSequential(d3.interpolateRdYlGn).domain([1, 10]);

const svg = d3.select("#chart").append("svg").attr("width", w).attr("height", h);
const g = svg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

// Column headers
g.selectAll(".col-header").data(dimLabels).join("text")
  .attr("class", "col-header")
  .attr("x", (d, i) => i * cellW + cellW / 2)
  .attr("y", -12)
  .text(d => d);

// Rows
blocks.forEach((bid, row) => {{
  const scores = current.blocks[bid];
  const prevScores = prev ? prev.blocks[bid] : null;
  const shortName = bid.replace(/^\\d+[-]/, "").replace(/-/g, " ");

  // Row label
  g.append("text").attr("class", "label")
    .attr("x", -8).attr("y", row * cellH + cellH / 2 + 1)
    .attr("text-anchor", "end").attr("dominant-baseline", "central")
    .text(`${{bid.split("-")[0]}} ${{shortName}}`);

  dims.forEach((dim, col) => {{
    const val = dim === "render" ? (scores.render ? 10 : 1) : scores[dim];
    const x = col * cellW, y = row * cellH;

    g.append("rect").attr("class", "cell")
      .attr("x", x).attr("y", y).attr("width", cellW).attr("height", cellH)
      .attr("fill", val != null ? color(val) : "#eee")
      .attr("rx", 3);

    if (val != null) {{
      const label = dim === "render" ? (scores.render ? "\\u2713" : "\\u2717") :
                    dim === "composite" ? val.toFixed(1) : val;
      g.append("text").attr("class", "score")
        .attr("x", x + cellW / 2).attr("y", y + cellH / 2)
        .text(label);
    }}

    // Delta annotation
    if (prevScores && dim !== "render") {{
      const prevVal = dim === "composite" ? prevScores.composite : prevScores[dim];
      if (val != null && prevVal != null) {{
        const delta = dim === "composite" ? +(val - prevVal).toFixed(1) : val - prevVal;
        if (delta !== 0) {{
          g.append("text").attr("class", "delta")
            .attr("x", x + cellW / 2).attr("y", y + cellH - 4)
            .text((delta > 0 ? "+" : "") + delta);
        }}
      }}
    }}
  }});
}});

// Averages row
const avgY = blocks.length * cellH + 8;
g.append("text").attr("class", "label").attr("x", -8).attr("y", avgY + cellH / 2)
  .attr("text-anchor", "end").attr("dominant-baseline", "central")
  .attr("font-weight", 600).text("Average");

dims.forEach((dim, col) => {{
  if (dim === "render") return;
  const vals = blocks.map(b => current.blocks[b][dim]).filter(v => v != null);
  if (!vals.length) return;
  const avg = (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);
  g.append("rect").attr("class", "cell")
    .attr("x", col * cellW).attr("y", avgY).attr("width", cellW).attr("height", cellH)
    .attr("fill", color(+avg)).attr("rx", 3).attr("stroke-width", 2);
  g.append("text").attr("class", "score")
    .attr("x", col * cellW + cellW / 2).attr("y", avgY + cellH / 2)
    .attr("font-weight", 600).text(avg);
}});
</script>
</body>
</html>"""

    out = round_dir / "report.html"
    out.write_text(report_html)
    print(f"  Report: {out}")


# === Main ===

def main():
    parser = argparse.ArgumentParser(description="Audit pipeline for D3 Power Tools blocks")
    parser.add_argument("--blocks", default="85-93", help="Block range, e.g. '85-93' or '1-105'")
    parser.add_argument("--round", type=int, default=None, help="Round number (auto-increments)")
    parser.add_argument("--skip-render", action="store_true", help="Reuse previous screenshots")
    parser.add_argument("--parallel", type=int, default=4, help="Max parallel audit subprocesses")
    parser.add_argument("--model", default="sonnet", help="Model for audit subprocesses")
    parser.add_argument("--persist", action="store_true", help="Copy results to git-tracked file")
    args = parser.parse_args()

    blocks = parse_block_range(args.blocks)
    if not blocks:
        print(f"No blocks match range '{args.blocks}'")
        sys.exit(1)

    # Determine round number
    history_path = OUTPUT_DIR / "history.json"
    if args.round:
        round_num = args.round
    elif history_path.exists():
        try:
            h = json.loads(history_path.read_text())
            round_num = max((r["round"] for r in h["rounds"]), default=0) + 1
        except (json.JSONDecodeError, KeyError):
            round_num = 1
    else:
        round_num = 1

    round_dir = OUTPUT_DIR / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Audit Pipeline Round {round_num} ===")
    print(f"Blocks: {args.blocks} ({len(blocks)} blocks)")
    print(f"Tools: {', '.join(TOOLS.keys())}")
    print(f"Model: {args.model}, parallel: {args.parallel}\n")

    # Phase 1
    if args.skip_render:
        prev_round = round_dir.parent / f"round-{round_num - 1}"
        rr_path = prev_round / "render-results.json"
        if rr_path.exists():
            render_results = json.loads(rr_path.read_text())
            # Copy screenshots
            ss_src = prev_round / "screenshots"
            ss_dst = round_dir / "screenshots"
            ss_dst.mkdir(parents=True, exist_ok=True)
            for f in ss_src.glob("*.png"):
                (ss_dst / f.name).write_bytes(f.read_bytes())
            print(f"Phase 1: Reusing {len(render_results)} render results from round {round_num - 1}\n")
        else:
            print("Phase 1: No previous render results, running tests...")
            render_results = run_render_tests(blocks, round_dir)
    else:
        print("Phase 1: Render tests")
        render_results = run_render_tests(blocks, round_dir)

    # Phase 2
    print("Phase 2: Audit evaluations")
    run_audits(blocks, render_results, round_dir, args.parallel, args.model)

    # Phase 3
    print("Phase 3: Aggregation")
    scores = aggregate(blocks, render_results, round_dir, round_num)

    # Phase 4
    print("\nPhase 4: Report")
    generate_report(round_dir, round_num)

    if args.persist:
        PERSIST_FILE.write_text((OUTPUT_DIR / "history.json").read_text())
        print(f"  Persisted to {PERSIST_FILE}")

    print(f"\n=== Done ===")
    print(f"Results: {round_dir}")
    print(f"Report:  {round_dir / 'report.html'}")


if __name__ == "__main__":
    main()
