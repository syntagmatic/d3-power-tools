#!/usr/bin/env python3
"""Generate blocks using Claude Code CLI. Reads manifest.json, outputs to blocks/{version}-{model}/."""
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from staging import create_staging_dir, cleanup_staging_dir, parse_skill_reads, parse_stream_report

PROJ = Path(__file__).resolve().parent.parent
MANIFEST = PROJ / "blocks" / "manifest.json"
MAX_PARALLEL = 5

# Parse args
args = sys.argv[1:]
all_skills = "--all-skills" in args
no_skills = "--no-skills" in args
args = [a for a in args if a not in ("--all-skills", "--no-skills")]
MODEL = None
for i, a in enumerate(args):
    if a == "--model" and i + 1 < len(args):
        MODEL = args[i + 1]
        args = args[:i] + args[i + 2:]
        break

VERSION = args[0] if args else "v1"
ONLY_IDS = set(args[1:]) if len(args) > 1 else None

OUTDIR = PROJ / "blocks" / VERSION
LOGFILE = PROJ / "temp" / f"generate-blocks-claude-{VERSION}.json"

OUTDIR.mkdir(parents=True, exist_ok=True)
FAILURES_DIR = OUTDIR / "failures"


def _save_failure_report(bid, error, report, skills_requested):
    """Save a JSON failure report and an HTML viewer for it."""
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "bid": bid,
        "error": error,
        "version": VERSION,
        "model": MODEL or "claude-opus-4-6",
        "skills_requested": skills_requested,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        **report,
    }

    json_path = FAILURES_DIR / f"{bid}.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # Generate HTML viewer
    html_path = FAILURES_DIR / f"{bid}.html"
    turns_html = []
    for i, turn in enumerate(report.get("turns", []), 1):
        tools_parts = []
        for t in turn.get("tools", []):
            if t["tool"] == "Read":
                tools_parts.append(f'<span class="tool read">Read</span> {_esc(t.get("file", ""))}'  )
            elif t["tool"] == "Write":
                tools_parts.append(f'<span class="tool write">Write</span> {_esc(t.get("file", ""))} ({t.get("size", 0)} chars)')
            elif t["tool"] == "Bash":
                tools_parts.append(f'<span class="tool bash">Bash</span> <code>{_esc(t.get("command", ""))}</code>')
            else:
                tools_parts.append(f'<span class="tool other">{_esc(t["tool"])}</span> {_esc(t.get("input", "")[:100])}')
        tools_str = "<br>".join(tools_parts) if tools_parts else '<span class="no-tools">no tool calls</span>'
        text = _esc(turn.get("text", ""))[:500]
        text_str = f'<div class="turn-text">{text}</div>' if text else ""
        error_str = ""
        if turn.get("error"):
            error_str = f'<div class="turn-error">{_esc(turn["error"])}</div>'
        tokens = ""
        if turn.get("tokens_in") or turn.get("tokens_out"):
            tokens = f' <span class="tokens">{turn.get("tokens_in", 0):,}in / {turn.get("tokens_out", 0):,}out</span>'
        turns_html.append(
            f'<div class="turn"><div class="turn-num">Turn {i}{tokens}</div>'
            f'<div class="turn-body">{tools_str}{text_str}{error_str}</div></div>')

    result_info = report.get("result") or {}
    result_class = "result-error" if result_info.get("is_error") else "result-ok"
    result_text = _esc(result_info.get("text", "")) or "(empty)"

    # Summary stats
    cost = result_info.get("cost_usd")
    duration = result_info.get("duration_ms")
    total_in = result_info.get("total_tokens_in")
    total_out = result_info.get("total_tokens_out")
    stats_parts = []
    if cost is not None:
        stats_parts.append(f"${cost:.4f}")
    if duration is not None:
        stats_parts.append(f"{duration / 1000:.1f}s")
    if total_in is not None:
        stats_parts.append(f"{total_in:,} tokens in")
    if total_out is not None:
        stats_parts.append(f"{total_out:,} tokens out")
    stop = result_info.get("stop_reason")
    if stop and stop != "end_turn":
        stats_parts.append(f"stop: {stop}")
    stats_line = " &middot; ".join(stats_parts) if stats_parts else ""

    skills_line = ", ".join(skills_requested) if skills_requested else "none (baseline run)"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Failure: {_esc(bid)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #222; background: #fafafa; }}
  h1 {{ font-size: 20px; font-weight: 400; margin: 0 0 4px; }} h1 b {{ font-weight: 600; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 8px; }}
  .meta span {{ display: inline-block; margin-right: 16px; }}
  .error-badge {{ background: #d33; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 600; }}
  .stats {{ color: #666; font-size: 13px; margin-bottom: 20px; padding: 8px 12px; background: #fff; border: 1px solid #e8e8e8; border-radius: 4px; }}
  .turn {{ display: flex; gap: 12px; margin-bottom: 8px; padding: 8px 12px; background: #fff; border: 1px solid #e8e8e8; border-radius: 4px; }}
  .turn-num {{ font-size: 11px; color: #999; font-weight: 600; white-space: nowrap; min-width: 48px; padding-top: 2px; }}
  .turn-body {{ font-size: 13px; line-height: 1.5; }}
  .tokens {{ font-weight: 400; color: #bbb; font-size: 10px; display: block; }}
  .tool {{ font-size: 11px; font-weight: 600; padding: 1px 5px; border-radius: 3px; }}
  .tool.read {{ background: #e3f2fd; color: #1565c0; }}
  .tool.write {{ background: #e8f5e9; color: #2e7d32; }}
  .tool.bash {{ background: #fff3e0; color: #e65100; }}
  .tool.other {{ background: #f3e5f5; color: #7b1fa2; }}
  .no-tools {{ color: #bbb; font-style: italic; font-size: 12px; }}
  .turn-text {{ color: #555; font-size: 12px; margin-top: 4px; white-space: pre-wrap; }}
  .turn-error {{ color: #d33; font-size: 12px; margin-top: 4px; }}
  .result {{ margin-top: 20px; padding: 12px; border-radius: 4px; font-size: 13px; }}
  .result-error {{ background: #fde; border: 1px solid #d33; }}
  .result-ok {{ background: #f5f5f5; border: 1px solid #ddd; }}
  code {{ font-size: 12px; background: #f0f0f0; padding: 1px 4px; border-radius: 2px; }}
  a {{ color: #1565c0; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
</style></head><body>
<p><a href="../../../blocks-latest.html">&larr; blocks</a></p>
<h1><b>Failure:</b> {_esc(bid)}</h1>
<div class="meta">
  <span class="error-badge">{_esc(error)}</span>
  <span>{_esc(data.get("model", ""))}</span>
  <span>{report.get("turn_count", 0)} turns</span>
  <span>{_esc(data.get("timestamp", ""))}</span>
</div>
<div class="meta">Skills: {skills_line}</div>
{f'<div class="stats">{stats_line}</div>' if stats_line else ""}
{"".join(turns_html)}
<div class="result {result_class}"><b>Result:</b> {result_text}</div>
</body></html>"""

    html_path.write_text(html)


def _esc(s):
    """HTML-escape a string."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def run_block(idx, block, defaults):
    bid = block["id"]
    outfile = OUTDIR / f"{bid}.html"

    if outfile.exists() and outfile.stat().st_size > 0:
        print(f"[{idx}] SKIP {bid} (exists)")
        return None

    suffix = defaults.get("suffix", "")
    abs_outpath = str(outfile)
    prompt = (
        f"Build a standalone D3.js visualization as a single HTML file.\n\n"
        f"{block['prompt']}\n\n"
        f"{suffix}\n"
        f"Generate ALL synthetic data inline. No external data files.\n"
        f"Write the complete file to {abs_outpath}"
    )

    skills_list = [] if no_skills else block["skills"]
    staging = create_staging_dir(bid, skills_list, PROJ, all_skills=all_skills, prefix=VERSION)
    print(f"[{idx}] START {bid} (skills: {', '.join(skills_list) or 'none'})")
    t0 = time.time()

    stream_file = OUTDIR / f".{bid}.stream"
    try:
        cmd = [
            "claude", "-p", prompt,
            "--allowedTools", "Write,Read",
            "--disallowedTools", "Bash,Glob,Grep,Agent",
            "--max-turns", "25",
            "--output-format", "stream-json",
            "--verbose",
        ]
        if MODEL:
            cmd.extend(["--model", MODEL])
        with open(stream_file, "w") as sf:
            proc = subprocess.Popen(
                cmd, stdout=sf, stderr=subprocess.PIPE, text=True,
                cwd=str(staging))
            try:
                _, stderr = proc.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                stream = stream_file.read_text() if stream_file.exists() else ""
                print(f"[{idx}] TIMEOUT {bid}")
                report = parse_stream_report(stream)
                _save_failure_report(bid, "timeout", report, skills_list)
                return {"bid": bid, "status": "fail", "error": "timeout",
                        "skills_requested": block["skills"],
                        "skills_triggered": parse_skill_reads(stream),
                        "skills_missed": block["skills"], "elapsed_s": 600}

        class _Result:
            pass
        result = _Result()
        result.stdout = stream_file.read_text() if stream_file.exists() else ""
        result.stderr = stderr
        result.returncode = proc.returncode
    finally:
        cleanup_staging_dir(staging)
        if stream_file.exists():
            stream_file.unlink()

    elapsed = time.time() - t0

    # Parse which skills were read
    triggered = parse_skill_reads(result.stdout)
    record = {
        "bid": bid,
        "skills_requested": block["skills"],
        "skills_triggered": triggered,
        "skills_missed": [s for s in block["skills"] if s not in triggered],
        "elapsed_s": round(elapsed, 1),
    }

    # Parse stream for cost/token data (all outcomes)
    report = parse_stream_report(result.stdout)
    result_info = report.get("result") or {}
    if result_info.get("cost_usd") is not None:
        record["cost_usd"] = result_info["cost_usd"]
    if result_info.get("duration_ms") is not None:
        record["duration_ms"] = result_info["duration_ms"]
    if result_info.get("total_tokens_in") is not None:
        record["tokens_in"] = result_info["total_tokens_in"]
    if result_info.get("total_tokens_out") is not None:
        record["tokens_out"] = result_info["total_tokens_out"]
    record["turn_count"] = report.get("turn_count", 0)

    # Check output file
    if outfile.exists() and outfile.stat().st_size > 100:
        content = outfile.read_text()
        first_line = content.split("\n")[0].lower()
        if "<!doctype" in first_line or "<html" in first_line:
            lines = len(content.splitlines())
            record["status"] = "pass"
            record["lines"] = lines
            cost_str = f", ${record['cost_usd']:.3f}" if "cost_usd" in record else ""
            print(f"[{idx}] PASS {bid} ({lines} lines, {elapsed:.0f}s, read: {triggered}{cost_str})")
            return record
        else:
            record["status"] = "fail"
            record["error"] = "invalid html"
            _save_failure_report(bid, "invalid html", report, skills_list)
            print(f"[{idx}] FAIL {bid} (not valid HTML)")
            outfile.unlink()
            return record
    else:
        record["status"] = "fail"
        # With stream-json, errors are in stdout; stderr may be empty
        err_content = result.stderr[:2000] if result.stderr else ""
        if not err_content and result.stdout:
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                    if event.get("type") == "result" and event.get("is_error"):
                        err_content = event.get("result", "unknown error")
                        break
                except (json.JSONDecodeError, ValueError):
                    pass
        record["error"] = err_content or "no output"
        _save_failure_report(bid, record["error"], report, skills_list)
        print(f"[{idx}] FAIL {bid} (no output file)")
        return record


def main():
    manifest = json.loads(MANIFEST.read_text())
    blocks = manifest["blocks"]
    defaults = manifest.get("defaults", {})

    if ONLY_IDS:
        blocks = [b for b in blocks if b["id"] in ONLY_IDS]

    # Filter to only missing blocks
    missing = [b for b in blocks if not (OUTDIR / f"{b['id']}.html").exists()]
    mode = "no skills" if no_skills else "all skills" if all_skills else "manifest skills"
    print(f"{len(missing)} blocks to generate (of {len(blocks)} selected), {mode}, up to {MAX_PARALLEL} parallel\n")

    if not missing:
        print("All blocks already exist. Done.")
        return

    records = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {}
        for i, block in enumerate(missing):
            f = pool.submit(run_block, i + 1, block, defaults)
            futures[f] = block["id"]

        for f in as_completed(futures):
            r = f.result()
            if r is not None:
                records.append(r)

    records.sort(key=lambda r: r["bid"])
    counts = {"pass": 0, "fail": 0}
    all_missed = []
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        all_missed.extend(r.get("skills_missed", []))

    missed_counts = Counter(all_missed)

    report = {
        "version": VERSION,
        "mode": "all_skills" if all_skills else "manifest_only",
        "summary": counts,
        "skills_missed_counts": dict(missed_counts.most_common()),
        "blocks": records,
    }

    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    LOGFILE.write_text(json.dumps(report, indent=2) + "\n")

    # Update generation.json in the output directory
    gen_file = OUTDIR / "generation.json"
    if gen_file.exists():
        gen = json.loads(gen_file.read_text())
    else:
        model_id = MODEL or "claude-opus-4-6"
        skill_mode = "none" if no_skills else "all" if all_skills else "manifest"
        gen = {"model": model_id, "cli": "claude", "version": VERSION,
               "skill_mode": skill_mode, "block_count": 0, "blocks": {}}
    for r in records:
        entry = {"status": r["status"]}
        for field in ("lines", "elapsed_s", "cost_usd", "duration_ms",
                      "tokens_in", "tokens_out", "turn_count",
                      "skills_triggered", "skills_missed", "error"):
            if r.get(field) is not None:
                entry[field] = r[field]
        gen["blocks"][r["bid"]] = entry
    gen["block_count"] = sum(1 for b in gen["blocks"].values() if b.get("status") == "pass")
    gen_file.write_text(json.dumps(gen, indent=2, ensure_ascii=False) + "\n")

    print(f"\n=== DONE ===")
    print(f"Pass: {counts.get('pass', 0)}  Fail: {counts.get('fail', 0)}")
    if missed_counts:
        print(f"Skills never read: {dict(missed_counts.most_common(10))}")
    print(f"Output: {OUTDIR}")
    print(f"Report: {LOGFILE}")


if __name__ == "__main__":
    main()
