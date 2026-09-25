#!/usr/bin/env python3
"""Phase 1 ablation: does each content skill still change output on the current model?

For each skill, generate a few manifest prompts with only that skill staged
(and a forced read) vs. no skills, then judge blind. Outputs land under
evals/ablation-v3/ with opaque IDs; key.json maps IDs back to conditions and
is never shown to judges.

Usage:
  python3 scripts/ablate.py plan [--per-skill 3]     # write plan.json (hand-edit after)
  python3 scripts/ablate.py gen  [--samples 2] [--model M] [--skills a,b] [--limit N]
  python3 scripts/ablate.py audit [--judge M]        # existing 4-tool pipeline, absolute scores
  python3 scripts/ablate.py pair  [--judge M]        # blind A/B: skill vs baseline, same prompt+seed
  python3 scripts/ablate.py report                   # notes/ablation-v3-data.md tables
  python3 scripts/ablate.py cost                     # spend so far + projection

--suite corpus runs the same steps on evals/corpus/ (fixed tasks with real data, ported from d3pt) with a
third arm: "prompt", d3pt's hand-compressed tier-100 prompt with no skill. Base and skill arms get the
task's plain request. That asks whether a short, well-made prompt matches what a skill adds. Corpus-only step:
  python3 scripts/ablate.py --suite corpus struct     # verify.json structural checks, no LLM
Pairs in the corpus suite: skill-base, prompt-base, skill-prompt.
"""
import argparse
import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from staging import create_staging_dir, cleanup_staging_dir, parse_skill_reads, parse_stream_report

PROJ = Path(__file__).resolve().parent.parent
CORPUS = PROJ / "evals" / "corpus"
D3 = PROJ / "plugin" / "vendor" / "js" / "d3.v7.min.js"
SUITE = "skills"
OUT = PROJ / "evals" / "ablation-v3"
GEN = OUT / "gen"
PLAN = OUT / "plan.json"
KEY = OUT / "key.json"
MANIFEST = json.loads((PROJ / "blocks" / "manifest.json").read_text())
CLAUDE = shutil.which("claude") or "claude"
TIMEOUT_S = 900

# Skills with no manifest coverage get hand-written prompts.
EXTRA_PROMPTS = {
    "x-choreo-election": {
        "skills": ["motion"], "wait_for": "svg",
        "prompt": "Scrollytelling explainer with a sticky graphic: 6 scroll steps walk through 400 synthetic county results. "
                  "Step 1 scatters dots, step 2 sorts them into a beeswarm by margin, step 3 splits by region, step 4 "
                  "highlights flipped counties, step 5 morphs to a bar chart of totals, step 6 returns to the swarm. "
                  "Transitions between steps are staged (exit, then move, then enter) and reversible when scrolling up."},
    "x-choreo-race": {
        "skills": ["motion"], "wait_for": "svg",
        "prompt": "Animated bar chart race of 20 synthetic programming languages over 30 years with play/pause and a year "
                  "scrubber. Bars reorder smoothly, new entrants slide in from below, dropouts exit downward, value labels "
                  "tween. Scrubbing mid-animation must not leave bars in inconsistent positions."},
    "x-choreo-sort": {
        "skills": ["motion"], "wait_for": "svg",
        "prompt": "Grouped bar chart of 12 synthetic products x 4 quarters with buttons to regroup (by product / by quarter), "
                  "sort (alphabetical / total / growth), and toggle stacked vs grouped. Each change is a multi-stage "
                  "transition with staggered delays; rapid clicking must not break the layout."},
    "x-coord-dashboard": {
        "skills": ["interaction"], "wait_for": "svg",
        "prompt": "Crossfilter dashboard over 50,000 synthetic flight records: histograms of delay, distance, and hour of "
                  "day, plus a bar chart of carriers. Brushing any histogram or clicking a carrier filters all the others "
                  "live. Show the filtered count. Filtering must stay smooth while dragging."},
    "x-coord-map-table": {
        "skills": ["interaction"], "wait_for": "svg",
        "prompt": "Three coordinated views of 300 synthetic weather stations: a scatter of elevation vs mean temperature, a "
                  "line chart of the selected stations' monthly temperature, and a sortable table. Hover in any view "
                  "highlights the station in all three; click toggles persistent selection. Include a reset button."},
    "x-coord-undo": {
        "skills": ["interaction"], "wait_for": "svg",
        "prompt": "Two linked charts over 2,000 synthetic customer records: a scatter of spend vs visits with a 2D brush, and "
                  "a bar chart of segments that filters on click. State is kept in one store, the URL hash reflects the "
                  "current selection so it can be shared, and undo/redo buttons step through selection history."},
    "x-explore-sensor": {
        "skills": ["design"], "wait_for": "svg",
        "prompt": "I have a synthetic dataset of 90 days of readings from 24 building sensors (temperature, humidity, CO2, "
                  "occupancy, every 15 minutes). I don't know what's interesting in it yet. Build a visualization that "
                  "helps me find out."},
    "x-explore-survey": {
        "skills": ["design"], "wait_for": "svg",
        "prompt": "Synthetic employee survey: 1,200 respondents, 8 departments, tenure, remote/hybrid/office, and 15 Likert "
                  "questions. Leadership wants to understand what drives low engagement. Build a visualization for it."},
    "x-explore-trips": {
        "skills": ["design"], "wait_for": "svg",
        "prompt": "Synthetic bike-share data: 40 stations with coordinates and 20,000 trips with start/end station, start "
                  "time, duration, and rider type. Visualize it so an operations team can see how the system behaves."},
    "x-data-messy-csv": {
        "skills": ["design"], "wait_for": "svg",
        "prompt": "Embed this as an inline CSV string with 600 synthetic rows of city air-quality readings: mixed date formats "
                  "(2024-03-01, 03/01/2024, 1 Mar 2024), numbers with thousands separators and units ('1,204 ppm'), blank "
                  "and 'N/A' cells, duplicate rows, and inconsistent city casing. Parse and clean it, then show a line "
                  "chart of monthly median PM2.5 per city with a note of how many rows were dropped and why."},
    "x-data-wide-to-long": {
        "skills": ["design"], "wait_for": "svg",
        "prompt": "Inline a wide-format synthetic table: 50 countries x 30 year columns of GDP per capita plus region and "
                  "income-group columns. Reshape to long form, compute each country's growth relative to its region's "
                  "median, and show a small ranked dot plot per region with a toggle between absolute and relative."},
}
# Underspecified self-visualizations; they reference repo data the generator never sees.
EXCLUDE = {"85-skill-constellation", "90-skill-growth-sparklines", "91-test-coverage-heatmap"}


def use_suite(name):
    global SUITE, OUT, GEN, PLAN, KEY
    SUITE = name
    OUT = PROJ / "evals" / ("ablation-v3" if name == "skills" else "ablation-corpus")
    GEN, PLAN, KEY = OUT / "gen", OUT / "plan.json", OUT / "key.json"


def frontmatter(path):
    """(fields, body) for a --- delimited markdown file. Values stay strings."""
    _, front, body = path.read_text().split("---", 2)
    return dict(l.split(":", 1) for l in front.strip().splitlines()), body.strip()


def corpus_prompts():
    """Corpus tasks as prompt entries. "prompt" is the plain request (the task's first paragraph), which base
    and skill arms get and critics judge against; "compact" is d3pt's tier-100 prompt for the prompt arm."""
    p = {}
    for d in sorted(x for x in CORPUS.iterdir() if (x / "verify.json").exists()):
        meta, body = frontmatter(d / "task.md")
        _, compact = frontmatter(d / "tier-100.md")
        p[f"c-{d.name}"] = {"id": f"c-{d.name}", "skills": [meta["ablate-skill"].strip()], "wait_for": "svg",
                            "prompt": " ".join(body.split("\n\n")[0].split()), "compact": compact,
                            "data": sorted((d / "data").iterdir()), "verify": d / "verify.json"}
    return p


def all_prompts():
    if SUITE == "corpus":
        return corpus_prompts()
    p = {b["id"]: b for b in MANIFEST["blocks"]}
    for k, v in EXTRA_PROMPTS.items():
        p[k] = {"id": k, **v}
    return p


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def opaque(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


# === plan ===

def cmd_plan(a):
    """Per skill: prefer prompts where the skill is listed first, then with fewest co-skills."""
    prompts = all_prompts()
    skills = sorted(p.name for p in (PROJ / "plugin" / "skills").iterdir() if (p / "SKILL.md").exists() and p.name != "review")
    plan = {}
    for s in skills:
        cands = [(b["skills"].index(s), len(b["skills"]), bid) for bid, b in sorted(prompts.items())
                 if s in b["skills"] and bid not in EXCLUDE]
        plan[s] = [bid for *_, bid in sorted(cands)[: a.per_skill]]
    if SUITE == "corpus":
        plan = {s: v for s, v in plan.items() if v}
    save_json(PLAN, plan)
    uniq = {bid for v in plan.values() for bid in v}
    thin = [s for s, v in plan.items() if len(v) < a.per_skill]
    print(f"plan: {len(skills)} skills, {sum(map(len, plan.values()))} skill-prompt pairs, {len(uniq)} unique prompts")
    if thin and SUITE == "skills":
        print(f"under-covered: {', '.join(thin)}")
    print(f"wrote {PLAN.relative_to(PROJ)}")


# === gen ===

def jobs_for(plan, samples, only=None):
    """(oid, meta) for every generation needed. Baselines (and the corpus prompt arm) are shared per prompt+seed."""
    jobs = {}
    prompts = all_prompts()
    for skill, bids in plan.items():
        if only and skill not in only:
            continue
        for bid in bids:
            for seed in range(samples):
                jobs[opaque(bid, "base", seed)] = {"prompt_id": bid, "cond": "base", "skill": None, "seed": seed}
                jobs[opaque(bid, skill, seed)] = {"prompt_id": bid, "cond": "skill", "skill": skill, "seed": seed}
                if "compact" in prompts[bid]:
                    jobs[opaque(bid, "prompt", seed)] = {"prompt_id": bid, "cond": "prompt", "skill": None, "seed": seed}
    return jobs


def gen_one(oid, meta, model):
    out = GEN / f"{oid}.html"
    out.unlink(missing_ok=True)  # else a failed call leaves the previous page in place and counts as ok
    b = all_prompts()[meta["prompt_id"]]
    skills = [meta["skill"]] if meta["skill"] else []
    force = f"Before writing any code, read skills/{meta['skill']}/SKILL.md and apply what is relevant.\n\n" if skills else ""
    body = b["compact"] if meta["cond"] == "prompt" else b["prompt"]
    if b.get("data"):
        names = ", ".join(f"data/{f.name}" for f in b["data"])
        data_note = (f"The dataset is at {names} in your working directory; read it before designing. The page is "
                     f"served with that same path beside it, so load it with d3.json('{names.split(', ')[0]}'), and "
                     f"load D3 with <script src=\"d3.v7.min.js\"></script>.\n"
                     # Every arm gets this: verify.json finds marks and states by class name, and only some arms'
                     # text asked for classes, which made the structural gate grade naming instead of the chart.
                     "Give marks descriptive class names (such as node, leaf, link, label, cell, dot), and show "
                     "interaction state by toggling a class (such as highlight, active, dimmed).")
    else:
        data_note = "Generate ALL synthetic data inline. No external data files."
    prompt = (f"{force}Build a standalone D3.js visualization as a single HTML file.\n\n{body}\n\n"
              f"{MANIFEST['defaults'].get('suffix', '')}\n{data_note}\n"
              f"Write the complete file to {out}")
    staging = create_staging_dir(oid, skills, PROJ, prefix="ablate")
    for f in b.get("data", []):
        (staging / "data").mkdir(exist_ok=True)
        shutil.copy(f, staging / "data" / f.name)
    cmd = [CLAUDE, "-p", prompt, "--allowedTools", "Write,Read", "--disallowedTools", "Bash,Glob,Grep,Agent",
           "--max-turns", "25", "--output-format", "stream-json", "--verbose", "--model", model]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, cwd=str(staging))
        stream, err = r.stdout, None
    except subprocess.TimeoutExpired as e:
        stream, err = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
    finally:
        cleanup_staging_dir(staging)
    rep = parse_stream_report(stream)
    res = rep.get("result") or {}
    ok = out.exists() and out.stat().st_size > 200
    if not ok and not err:
        err = f"api: {res['text'][:120]}" if res.get("is_error") else "no output"
    return {**meta, "model": model, "ok": ok, "error": err,
            "skills_read": parse_skill_reads(stream), "cost_usd": res.get("cost_usd"),
            "tokens_out": res.get("total_tokens_out"), "elapsed_s": round(time.time() - t0, 1)}


def cmd_gen(a):
    plan = load_json(PLAN, None) or sys.exit("run plan first")
    key = load_json(KEY, {})
    only = set(a.skills.split(",")) if a.skills else None
    todo = [(oid, m) for oid, m in jobs_for(plan, a.samples, only).items()
            # Resume only outputs from this model, so switching --model regenerates rather than mixing generators.
            if not (oid in key and key[oid].get("ok") and key[oid].get("model") == a.model
                    and (GEN / f"{oid}.html").exists())]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} generations to run on {a.model} ({a.parallel} parallel)")
    GEN.mkdir(parents=True, exist_ok=True)
    if SUITE == "corpus":
        (GEN / "data").mkdir(exist_ok=True)
        shutil.copy(D3, GEN / "d3.v7.min.js")
        for b in all_prompts().values():
            for f in b["data"]:
                shutil.copy(f, GEN / "data" / f.name)
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        futs = {pool.submit(gen_one, oid, m, a.model): oid for oid, m in todo}
        for f in as_completed(futs):
            oid = futs[f]
            try:
                rec = f.result()
            except Exception as e:  # keep the batch going; record and move on
                rec = {**dict(todo)[oid], "ok": False, "error": repr(e)}
            key[oid] = rec
            save_json(KEY, key)
            if rec["ok"]:  # same oid, new page: cached renders and critic verdicts belong to the old one
                for stale in [OUT / "screenshots" / f"{oid}.png", *OUT.glob(f"audit-tmp/*/{oid}-*.json")]:
                    stale.unlink(missing_ok=True)
            c = rec.get("cost_usd")
            print(f"  {oid} {rec['prompt_id']:40} {rec['skill'] or rec['cond']:22} s{rec['seed']} "
                  f"{'ok' if rec['ok'] else rec['error']:8} {f'${c:.2f}' if c else ''} {rec.get('elapsed_s', '')}s")


# === audit (existing pipeline, absolute scores) ===

def load_pipeline():
    spec = importlib.util.spec_from_file_location("audit_pipeline", PROJ / "scripts" / "run-audit-pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CLAUDE_BIN = CLAUDE
    return mod


def cmd_audit(a):
    if importlib.util.find_spec("playwright") is None:
        # test-viz.py needs Playwright; host python usually lacks it. Under uv, "python3" on PATH is the venv's.
        uv = shutil.which("uv") or sys.exit("playwright missing and uv not found")
        sys.exit(subprocess.call([uv, "run", "--with", "playwright", "python3", *sys.argv]))
    key = load_json(KEY, {})
    prompts = all_prompts()
    blocks = [{"id": oid, "wait_for": prompts[m["prompt_id"]].get("wait_for", "svg"),
               "prompt": prompts[m["prompt_id"]]["prompt"]}  # viz-critic judges against the request
              for oid, m in sorted(key.items()) if m.get("ok")]
    pipe = load_pipeline()
    ss_dir = OUT / "screenshots"
    cache = f"{OUT.name}-{a.judge}"  # audit-tmp/<cache>/: critic verdicts cached per judge model
    rendered = pipe.run_render(blocks, cache, ss_dir, block_dir=str(GEN))
    audits = pipe.run_audits(blocks, rendered, cache, a.judge, a.parallel, ss_dir, block_dir=str(GEN))
    scores = load_json(OUT / "audit.json", {})
    for b in blocks:
        oid = b["id"]
        e = {"render": rendered.get(oid, False)}
        for tool, w in pipe.WEIGHTS.items():
            e[tool] = audits.get(oid, {}).get(tool, {}).get("score")
            e[f"{tool}_note"] = audits.get(oid, {}).get(tool, {}).get("note")
        vals = [e[t] for t in pipe.WEIGHTS]
        # Broken render scores 0 so skills that prevent breakage get credit.
        e["composite"] = (round(sum(e[t] * w for t, w in pipe.WEIGHTS.items()), 2) if e["render"] and None not in vals
                          else 0.0 if not e["render"] else None)
        scores[oid] = e
    save_json(OUT / "audit.json", scores)
    print(f"wrote {len(scores)} scores to {(OUT / 'audit.json').relative_to(PROJ)}")


# === pair (blind A/B) ===

PAIR_PROMPT = """You are judging two D3.js visualizations built from the same request. You don't know how either was made.

## Request
{request}

## Artifacts
- A: screenshot {ss_a}, source {html_a}
- B: screenshot {ss_b}, source {html_b}

Read both screenshots and both sources. Judge which better serves the request: correctness of the encoding,
legibility, interaction robustness as written in the code, and design quality. A broken or empty render loses.

Write JSON to {out}:
{{"winner": "A" | "B" | "tie", "margin": "slight" | "clear" | "decisive",
  "reasons": ["<up to 3 specific differences that decided it>"]}}
Write the file now. No markdown, no explanation."""


def pair_one(pid, a_oid, b_oid, request, judge):
    out = OUT / "pairs-tmp" / f"{pid}.json"
    if out.exists() and out.stat().st_size > 5:
        return json.loads(out.read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    ss = OUT / "screenshots"
    prompt = PAIR_PROMPT.format(request=request, ss_a=ss / f"{a_oid}.png", html_a=GEN / f"{a_oid}.html",
                                ss_b=ss / f"{b_oid}.png", html_b=GEN / f"{b_oid}.html", out=out)
    r = subprocess.run([CLAUDE, "-p", prompt, "--allowedTools", "Read,Write", "--max-turns", "25", "--model", judge,
                        "--permission-mode", "bypassPermissions", "--output-format", "json"],
                       capture_output=True, text=True, timeout=300, cwd=str(OUT / "pairs-tmp"))
    try:
        v = json.loads(out.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        try:
            env = json.loads(r.stdout)
            if env.get("is_error"):
                print(f"  {pid} api: {str(env.get('result'))[:120]}")
        except json.JSONDecodeError:
            pass
        return None
    try:
        v["cost_usd"] = json.loads(r.stdout).get("total_cost_usd")
    except json.JSONDecodeError:
        pass
    out.write_text(json.dumps(v, ensure_ascii=False))
    return v


PAIRS = {"skills": [("skill", "base")], "corpus": [("skill", "base"), ("prompt", "base"), ("skill", "prompt")]}


def cmd_pair(a):
    key = load_json(KEY, {})
    prompts = all_prompts()
    by_cell = defaultdict(lambda: defaultdict(list))  # (prompt_id, seed) -> cond -> [oid]; a prompt can serve several skills
    for oid, m in key.items():
        if m.get("ok"):
            by_cell[(m["prompt_id"], m["seed"])][m["cond"]].append(oid)
    tasks = []
    for (bid, seed), conds in sorted(by_cell.items()):
        for x, y in PAIRS[SUITE]:
            for ox in conds[x]:
                for oy in conds[y]:
                    pid = opaque("pair", ox, oy, a.judge, *(hashlib.sha1((GEN / f"{o}.html").read_bytes()).hexdigest()
                                                            for o in (ox, oy)))
                    x_is_a = random.Random(pid).random() < 0.5  # deterministic per pair, position-balanced overall
                    tasks.append((pid, (x, y), (ox, oy), x_is_a, (ox, oy) if x_is_a else (oy, ox), prompts[bid]["prompt"]))
    pairs = load_json(OUT / "pairs.json", {})
    print(f"{len(tasks)} pairwise judgments on {a.judge}")
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        futs = {pool.submit(pair_one, pid, ab[0], ab[1], req, a.judge): (pid, cs, oids, xa)
                for pid, cs, oids, xa, ab, req in tasks}
        for f in as_completed(futs):
            pid, (x, y), oids, x_is_a = futs[f]
            v = f.result()
            if not v:
                print(f"  {pid} FAIL")
                continue
            w = v.get("winner")
            winner = "tie" if w == "tie" else x if (w == "A") == x_is_a else y
            m = key[oids[0]]
            pairs[pid] = {"conds": [x, y], "oids": list(oids), "skill": key[oids[0]]["skill"] or key[oids[1]]["skill"],
                          "prompt_id": m["prompt_id"], "seed": m["seed"], "winner": winner,
                          "margin": v.get("margin"), "reasons": v.get("reasons", []), "judge": a.judge,
                          "cost_usd": v.get("cost_usd")}
            save_json(OUT / "pairs.json", pairs)
            print(f"  {m['prompt_id']:40} {x} vs {y} -> {winner} ({v.get('margin')})")


# === struct (corpus only: verify.json fingerprints, no LLM) ===

def cmd_struct(a):
    if SUITE != "corpus":
        sys.exit("struct needs --suite corpus (manifest prompts have no verify.json)")
    if importlib.util.find_spec("playwright") is None:
        uv = shutil.which("uv") or sys.exit("playwright missing and uv not found")
        sys.exit(subprocess.call([uv, "run", "--with", "playwright", "python3", *sys.argv]))
    from structural import check_all
    key = load_json(KEY, {})
    prompts = all_prompts()
    items = [(GEN / f"{oid}.html", json.loads(prompts[m["prompt_id"]]["verify"].read_text()))
             for oid, m in sorted(key.items()) if m.get("ok")]
    got = check_all(items, GEN)
    res = {Path(h).stem: r for h, r in got.items()}
    save_json(OUT / "structural.json", res)
    for oid, r in res.items():
        m = key[oid]
        fails = [c["name"] for c in r["checks"] if not c["pass"]]
        print(f"  {m['prompt_id']:32} {m['cond']:6} s{m['seed']} {'pass' if r['pass'] else 'FAIL ' + ', '.join(fails)}")
    print(f"structural: {sum(r['pass'] for r in res.values())}/{len(res)} pass")


# === report ===

def wlt(pairs, x, y, skill=None):
    ps = [p for p in pairs if p["conds"] == [x, y] and (skill is None or p["skill"] == skill)]
    return f"{sum(p['winner'] == x for p in ps)}-{sum(p['winner'] == y for p in ps)}-{sum(p['winner'] == 'tie' for p in ps)}"


def mean(v):
    return f"{sum(v) / len(v):.2f}" if v else "-"


def cmd_report(a):
    key = load_json(KEY, {})
    audit = load_json(OUT / "audit.json", {})
    pairs = list(load_json(OUT / "pairs.json", {}).values())
    if SUITE == "corpus":
        return report_corpus(key, audit, pairs)
    base = {(m["prompt_id"], m["seed"]): oid for oid, m in key.items() if m["cond"] == "base"}
    rows = defaultdict(lambda: {"d": [], "read": 0, "n": 0})
    for oid, m in key.items():
        if m["cond"] != "skill":
            continue
        r = rows[m["skill"]]
        r["n"] += 1
        r["read"] += m["skill"] in (m.get("skills_read") or [])
        b = base.get((m["prompt_id"], m["seed"]))
        sa, sb = audit.get(oid, {}).get("composite"), audit.get(b, {}).get("composite")
        if sa is not None and sb is not None:
            r["d"].append(sa - sb)
    lines = ["| skill | n | read | composite delta (mean) | pairwise W-L-T |", "|---|---|---|---|---|"]
    for s in sorted(rows):
        r = rows[s]
        d = f"{sum(r['d']) / len(r['d']):+.2f} (n={len(r['d'])})" if r["d"] else "-"
        lines.append(f"| {s} | {r['n']} | {r['read']}/{r['n']} | {d} | {wlt(pairs, 'skill', 'base', s)} |")
    write_report(PROJ / "notes" / "ablation-v3-data.md", "Ablation v3: raw per-skill numbers", lines)


def report_corpus(key, audit, pairs):
    struct = load_json(OUT / "structural.json", {})
    conds = ["base", "prompt", "skill"]
    cell = defaultdict(lambda: defaultdict(lambda: {"n": 0, "struct": 0, "comp": []}))
    for oid, m in key.items():
        c = cell[m["prompt_id"]][m["cond"]]
        c["n"] += 1
        c["struct"] += bool(struct.get(oid, {}).get("pass"))
        if audit.get(oid, {}).get("composite") is not None:
            c["comp"].append(audit[oid]["composite"])
    head = " | ".join(f"{c} struct | {c} composite" for c in conds)
    lines = [f"| task | skill | {head} |", "|---|---|" + "---|---|" * len(conds)]
    for bid in sorted(cell):
        skill = next((m["skill"] for m in key.values() if m["prompt_id"] == bid and m["skill"]), "-")
        vals = " | ".join(f"{cell[bid][c]['struct']}/{cell[bid][c]['n']} | {mean(cell[bid][c]['comp'])}" for c in conds)
        lines.append(f"| {bid} | {skill} | {vals} |")
    lines += ["", "Pairwise W-L-T (first condition's wins first):", "",
              "| task | skill vs base | prompt vs base | skill vs prompt |", "|---|---|---|---|"]
    for bid in sorted(cell) + [None]:
        ps = [p for p in pairs if bid is None or p["prompt_id"] == bid]
        lines.append(f"| {bid or '**all**'} | " + " | ".join(wlt(ps, x, y) for x, y in PAIRS["corpus"]) + " |")
    write_report(PROJ / "notes" / "ablation-corpus-data.md", "Ablation on the d3pt corpus: base / prompt / skill", lines)


def write_report(out, title, lines):
    out.write_text(f"# {title}\n\nGenerated by `scripts/ablate.py report`.\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out.relative_to(PROJ)}")


def cmd_cost(a):
    key = load_json(KEY, {})
    costs = [m["cost_usd"] for m in key.values() if m.get("cost_usd")]
    by = defaultdict(list)
    for m in key.values():
        if m.get("cost_usd"):
            by[m["cond"]].append(m["cost_usd"])
    print(f"generations: {len(key)}, with cost: {len(costs)}, total ${sum(costs):.2f}")
    for c, v in by.items():
        print(f"  {c}: n={len(v)} mean ${sum(v) / len(v):.2f}")
    plan = load_json(PLAN, None)
    if plan and costs:
        n = len(jobs_for(plan, a.samples))
        print(f"projected for full plan at {a.samples} samples: {n} gens x ${sum(costs) / len(costs):.2f} "
              f"= ${n * sum(costs) / len(costs):.0f} (generation only)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=["skills", "corpus"], default="skills")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--per-skill", type=int, default=3)
    p = sub.add_parser("gen")
    p.add_argument("--samples", type=int, default=2); p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--skills"); p.add_argument("--limit", type=int); p.add_argument("--parallel", type=int, default=5)
    p = sub.add_parser("audit"); p.add_argument("--judge", default="claude-opus-5-5"); p.add_argument("--parallel", type=int, default=6)
    p = sub.add_parser("pair"); p.add_argument("--judge", default="claude-opus-5-5"); p.add_argument("--parallel", type=int, default=6)
    sub.add_parser("report")
    sub.add_parser("struct")
    p = sub.add_parser("cost"); p.add_argument("--samples", type=int, default=2)
    a = ap.parse_args()
    use_suite(a.suite)
    {"struct": cmd_struct, "plan": cmd_plan, "gen": cmd_gen, "audit": cmd_audit, "pair": cmd_pair, "report": cmd_report, "cost": cmd_cost}[a.cmd](a)


if __name__ == "__main__":
    main()
