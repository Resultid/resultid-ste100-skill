#!/usr/bin/env python3
"""Measure output tokens, input tokens, and lint findings with and without the plugin.

Usage:
    python3 evals/measure_tokens.py run OUT_JSONL [SAMPLES]   # call `claude -p`
    python3 evals/measure_tokens.py summary IN_JSONL          # print the tables
    python3 evals/measure_tokens.py session OUT_JSONL [SAMPLES]  # 12 turns in one session
    python3 evals/measure_tokens.py session-summary IN_JSONL

Each case runs SAMPLES times (default 3) for `baseline`, `strict`, `standard`,
and `terse`. The flags match evals/run_evals.md. Token counts come from the
`usage` object of `claude -p --output-format json`. Python stdlib only.
"""
import json
import os
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS = ["baseline", "strict", "standard", "terse"]
sys.path.insert(0, str(ROOT / "scripts"))


def run_one(job):
    case, condition, sample, workdir = job
    cmd = ["claude", "-p", case["input"], "--setting-sources", "project",
           "--tools", "", "--no-session-persistence", "--model", "sonnet",
           "--output-format", "json"]
    if case.get("project_context"):
        cmd += ["--append-system-prompt", case["project_context"]]
    env = dict(os.environ)
    env.pop("STE100_LEVEL", None)
    if condition != "baseline":
        cmd += ["--plugin-dir", str(ROOT)]
        env["STE100_LEVEL"] = condition
    row = {"id": case["id"], "condition": condition, "sample": sample}
    try:
        proc = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True,
                              text=True, timeout=300)
        data = json.loads(proc.stdout)
        usage = data["usage"]
        row.update(
            output=data["result"].strip(),
            output_tokens=usage["output_tokens"],
            input_tokens=usage["input_tokens"] + usage["cache_creation_input_tokens"]
            + usage["cache_read_input_tokens"],
            cost_usd=data.get("total_cost_usd"),
        )
    except Exception as error:  # keep the run going and record the failure
        row["error"] = f"{type(error).__name__}: {error}"
    return row


def run(out_path, samples):
    cases = [json.loads(l) for l in open(ROOT / "evals" / "cases.jsonl")]
    workdir = tempfile.mkdtemp(prefix="ste100-tokens-")  # empty dir: no CLAUDE.md
    jobs = [(c, cond, s, workdir) for c in cases for cond in CONDITIONS
            for s in range(samples)]
    with ThreadPoolExecutor(max_workers=6) as pool, open(out_path, "w") as out:
        for done, row in enumerate(pool.map(run_one, jobs), 1):
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            print(f"{done}/{len(jobs)}", end="\r", file=sys.stderr)
    print(f"{len(jobs)} runs written to {out_path}")


SESSION_CASES = ["T-01", "T-02", "T-03", "T-04", "T-05", "T-06",
                 "T-07", "R-01", "S-01", "S-02", "S-04", "R-03"]
SESSION_CONDITIONS = ["baseline", "standard", "terse"]


def run_chain(job):
    """Run the session cases in order, in one resumed session."""
    import uuid
    cases, condition, sample, workdir = job
    session_id = str(uuid.uuid4())
    env = dict(os.environ)
    env.pop("STE100_LEVEL", None)
    if condition != "baseline":
        env["STE100_LEVEL"] = condition
    rows = []
    for turn, case in enumerate(cases, 1):
        cmd = ["claude", "-p", case["input"], "--setting-sources", "project",
               "--tools", "", "--model", "sonnet", "--output-format", "json"]
        cmd += ["--session-id", session_id] if turn == 1 else ["--resume", session_id]
        if condition != "baseline":
            cmd += ["--plugin-dir", str(ROOT)]
        row = {"id": case["id"], "condition": condition, "sample": sample, "turn": turn}
        try:
            proc = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True,
                                  text=True, timeout=300)
            data = json.loads(proc.stdout)
            usage = data["usage"]
            row.update(
                output=data["result"].strip(),
                output_tokens=usage["output_tokens"],
                input_tokens=usage["input_tokens"] + usage["cache_creation_input_tokens"]
                + usage["cache_read_input_tokens"],
                cost_usd=data.get("total_cost_usd"),
            )
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {error}"
        rows.append(row)
    return rows


def session(out_path, samples):
    by_id = {}
    for line in open(ROOT / "evals" / "cases.jsonl"):
        case = json.loads(line)
        by_id[case["id"]] = case
    cases = [by_id[i] for i in SESSION_CASES]
    workdir = tempfile.mkdtemp(prefix="ste100-session-")
    jobs = [(cases, cond, s, workdir) for cond in SESSION_CONDITIONS
            for s in range(samples)]
    with ThreadPoolExecutor(max_workers=9) as pool, open(out_path, "w") as out:
        for rows in pool.map(run_chain, jobs):
            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
    print(f"{len(jobs)} sessions written to {out_path}")


def session_summary(in_path):
    rows = [json.loads(l) for l in open(in_path)]
    bad = [r for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    print(f"{len(rows)} turns, {len(bad)} failed\n")
    print("| Condition | Output tokens per session | Change | Input tokens per session | Cost per session (USD) | Change |")
    print("| --- | --- | --- | --- | --- | --- |")
    totals = {}
    for cond in SESSION_CONDITIONS:
        sess = {}
        for r in rows:
            if r["condition"] == cond:
                t = sess.setdefault(r["sample"], [0, 0, 0.0])
                t[0] += r["output_tokens"]
                t[1] += r["input_tokens"]
                t[2] += r["cost_usd"] or 0
        if sess:
            totals[cond] = [statistics.mean(v[i] for v in sess.values()) for i in range(3)]
    base = totals["baseline"]
    for cond, v in totals.items():
        pct = lambda i: "" if cond == "baseline" else f"{(v[i] / base[i] - 1) * 100:+.0f}%"
        print(f"| {cond} | {v[0]:.0f} | {pct(0)} | {v[1]:.0f} | {v[2]:.3f} | {pct(2)} |")
    print("\nCumulative cost after each turn, mean of samples (USD):\n")
    print("| Turn | " + " | ".join(SESSION_CONDITIONS) + " |")
    print("| --- | " + " | ".join("---" for _ in SESSION_CONDITIONS) + " |")
    for turn in range(1, len(SESSION_CASES) + 1):
        cells = []
        for cond in SESSION_CONDITIONS:
            per = {}
            for r in rows:
                if r["condition"] == cond and r["turn"] <= turn:
                    per[r["sample"]] = per.get(r["sample"], 0) + (r["cost_usd"] or 0)
            cells.append(f"{statistics.mean(per.values()):.4f}" if per else "n/a")
        print(f"| {turn} | " + " | ".join(cells) + " |")
    for r in bad:
        print("FAILED", r["id"], r["condition"], r["sample"], r["error"][:120])


def hard_findings(text):
    import lint
    findings, _ = lint.lint(text)
    return sum(f["level"] == "hard" for f in findings)


def summary(in_path):
    rows = [json.loads(l) for l in open(in_path)]
    bad = [r for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    for r in rows:
        r["words"] = len(r["output"].split())
        r["hard"] = hard_findings(r["output"])
    cases = sorted({r["id"] for r in rows})

    def case_mean(cond, case, key):
        vals = [r[key] for r in rows if r["condition"] == cond and r["id"] == case]
        return statistics.mean(vals) if vals else None

    print(f"{len(rows)} runs, {len(bad)} failed, {len(cases)} cases\n")
    print("| Condition | Output tokens per reply | Change vs baseline | Words per reply | Hard lint findings per reply | Input tokens per reply |")
    print("| --- | --- | --- | --- | --- | --- |")
    base = {c: case_mean("baseline", c, "output_tokens") for c in cases}
    for cond in CONDITIONS:
        sub = [r for r in rows if r["condition"] == cond]
        if not sub:
            continue
        tok = statistics.mean(r["output_tokens"] for r in sub)
        change = ""
        if cond != "baseline":
            ratios = [case_mean(cond, c, "output_tokens") / base[c]
                      for c in cases if base[c] and case_mean(cond, c, "output_tokens")]
            change = f"{(statistics.mean(ratios) - 1) * 100:+.0f}%"
        print(f"| {cond} | {tok:.0f} | {change} | "
              f"{statistics.mean(r['words'] for r in sub):.0f} | "
              f"{statistics.mean(r['hard'] for r in sub):.2f} | "
              f"{statistics.mean(r['input_tokens'] for r in sub):.0f} |")
    print("\nPer-case change in output tokens vs baseline (mean of samples):\n")
    print("| Case | " + " | ".join(c for c in CONDITIONS[1:]) + " |")
    print("| --- | --- | --- | --- |")
    for c in cases:
        cells = []
        for cond in CONDITIONS[1:]:
            v = case_mean(cond, c, "output_tokens")
            cells.append(f"{(v / base[c] - 1) * 100:+.0f}%" if v and base[c] else "n/a")
        print(f"| {c} | " + " | ".join(cells) + " |")
    for r in bad:
        print("FAILED", r["id"], r["condition"], r["sample"], r["error"][:120])


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "run":
        run(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    elif mode == "summary":
        summary(sys.argv[2])
    elif mode == "session":
        session(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    elif mode == "session-summary":
        session_summary(sys.argv[2])
    else:
        sys.exit(__doc__)
