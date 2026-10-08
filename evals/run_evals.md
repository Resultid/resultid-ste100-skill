# How to run the evals

The eval set is `evals/cases.jsonl`: 20 prompts. Each line has these fields:

| Field | Meaning |
| --- | --- |
| `id` | Case id. `S-` cases target strict, `T-` standard, `R-` terse. |
| `level` | The level the case was written for. The runner tests all three levels for every case. |
| `category` | The kind of text or the rule the case tests. |
| `project_context` | Optional. Text added to the system prompt, such as a CLAUDE.md glossary. |
| `input` | The user prompt. |
| `must_have` | Traits that a good answer has. |
| `must_not` | Traits that make an answer fail. |

## Method

1. Run every case four times: `baseline` (no plugin), then `strict`, `standard`, and `terse`.
2. Run the baseline and the plugin runs with the same flags. Only `--plugin-dir` and `STE100_LEVEL` differ.
3. The plugin runs use the real SessionStart hook. They do not paste the prompt by hand.
4. Run from an empty directory with `--setting-sources project`, so that user plugins, user hooks, and CLAUDE.md files do not change the result.
5. Disable tools with `--tools ""`. Every case is a plain text answer.
6. Review the outputs for these problems: too robotic, a needed qualifier dropped, a project term broken, a hedge turned into a fact, a requirement strength changed.
7. Change `skills/ste100/rules.md`, run `python3 scripts/build_prompt.py`, and run again.

## Run

Save the runner below as `run_evals.py`, then run:

```
python3 run_evals.py "$(pwd)" results.jsonl
```

The runner writes one JSON line per run. It takes about one minute for 80 runs.

```python
#!/usr/bin/env python3
"""Run evals/cases.jsonl with and without the ste100 plugin.

Usage: python3 run_evals.py PLUGIN_DIR OUT_JSONL [LEVELS]
Runs each case as: baseline, then one run per level, through `claude -p`.
"""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

plugin_dir, out_path = sys.argv[1], sys.argv[2]
levels = sys.argv[3].split(",") if len(sys.argv) > 3 else ["strict", "standard", "terse"]
cases = [json.loads(l) for l in open(os.path.join(plugin_dir, "evals", "cases.jsonl"))]
workdir = tempfile.mkdtemp(prefix="ste100-eval-")  # empty dir: no CLAUDE.md

def run(job):
    case, condition = job
    cmd = ["claude", "-p", case["input"], "--setting-sources", "project",
           "--tools", "", "--no-session-persistence", "--model", "sonnet"]
    if case.get("project_context"):
        cmd += ["--append-system-prompt", case["project_context"]]
    env = dict(os.environ)
    env.pop("STE100_LEVEL", None)
    if condition != "baseline":
        cmd += ["--plugin-dir", plugin_dir]
        env["STE100_LEVEL"] = condition
    result = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, text=True, timeout=300)
    return {"id": case["id"], "case_level": case["level"], "condition": condition,
            "output": result.stdout.strip(), "error": result.stderr.strip()[:500]}

jobs = [(c, cond) for c in cases for cond in ["baseline"] + levels]
with ThreadPoolExecutor(max_workers=6) as pool, open(out_path, "w") as out:
    for row in pool.map(run, jobs):
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        out.flush()
print(f"{len(jobs)} runs written to {out_path}")
```

## Automatic checks

The script below applies simple text checks to the `must_have` traits that a pattern can test. It does not replace reading the outputs. Some checks give false results (see the report). Save it as `check_traits.py` and run `python3 check_traits.py results.jsonl`.

```python
import json,re,sys
# id -> list of (label, predicate on output text)
def has(p): return lambda t: re.search(p,t,re.I) is not None
def lacks(p): return lambda t: re.search(p,t,re.I) is None
CHECKS = {
 "S-01":[("keeps 'may' hedge",has(r"\bmay\b|\bmight\b|\bcould\b|\bpossibl")),("no 'upload failed' as fact",lacks(r"upload (has )?failed(?! [a-z]* ?because the file)(?<!may have failed)")) ],
 "S-02":[("keeps identifiers",lambda t: all(x in t for x in("map_columns","file_id","profile_name"))),("says unmapped listed",has(r"unmapped|no (rule|mapping|entry)|not mapped"))],
 "S-03":[("uses upload_errors",has(r"upload_errors")),("no-change limit",has(r"not (change|modify|edit|alter|update)|read-only|only read"))],
 "S-04":[("keeps UI names",lambda t: all(x in t for x in("Data Sources","Column Mapping","Add Source","Save Mapping")))],
 "S-05":[("keeps exception",has(r"order_id")),("backup not required",has(r"optional|should|recommend|can skip"))],
 "S-06":[("single data term",lambda t: len({w for w in ("dataset","table","sheet","spreadsheet") if re.search(r"\b"+w+r"\b",t,re.I)})<=1)],
 "S-07":[("keeps glossary terms",lambda t: "mapping profile" in t and "Workspace Admin" in t),("keeps 'should'",has(r"\bshould\b")),("no 'template/configuration' swap",lacks(r"\btemplate\b|\bconfiguration\b")),("hedge kept",has(r"\bcould\b|\bmay\b|\bmight\b|otherwise"))],
 "T-01":[("covers limit 5",has(r"\b5\b|five")),("keeps identifiers",lambda t: all(x in t for x in("status","region","amount")))],
 "T-03":[("no causal claim",lacks(r"the tracking change (did )?cause[sd]? the drop(?!.*\?)(?!.*if)")),("says not proven",has(r"not prove|can'?t confirm|cannot confirm|does not confirm|doesn'?t prove|not enough|can'?t say|cannot say|does not show"))],
 "T-04":[("keeps order_date",has(r"order_date"))],
 "T-06":[("code uses normal names",has(r"def \w+\(")),("commit present",has(r"commit"))],
 "T-07":[("says no / not safe",has(r"\bno\b|not safe|should not|do not|don'?t")),("names logs/history/referrer",has(r"log|history|referr?er"))],
 "R-01":[("no greeting",lacks(r"great question|happy to|sure[,!]|certainly")),("no closing offer",lacks(r"let me know|feel free|i can also|want me to"))],
 "R-02":[("both columns",lambda t: "signup_date" in t and "region" in t),("final ok",has(r"now (passes|completes|passed|runs)|passes"))],
 "R-03":[("keeps condition",has(r"before|until|only after|first")),("not unconditional yes",lacks(r"^yes\b"))],
 "R-04":[("uses table names",lambda t: "orders" in t and "customers" in t)],
 "R-05":[("48 seconds",has(r"48 seconds|48 s\b|48s"))],
 "R-06":[("both terms",has(r"segment")),("cohort start-date",has(r"start date|retention")),],
}
def run(path):
    rows=[json.loads(l) for l in open(path)]
    out=[]
    for r in rows:
        for label,pred in CHECKS.get(r['id'],[]):
            out.append((r['id'],r['condition'],label,bool(pred(r['output']))))
    return out
if __name__=="__main__":
    res=run(sys.argv[1])
    bad=[x for x in res if not x[3]]
    for cond in ("baseline","strict","standard","terse"):
        sub=[x for x in res if x[1]==cond]
        print(f"{cond:9} pass {sum(1 for x in sub if x[3])}/{len(sub)}")
    for b in bad: print("FAIL",b)
```

## Lint statistics

```
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import lint
for line in open("evals/results.jsonl"):
    row = json.loads(line)
    findings, _ = lint.lint(row["output"])
    print(row["id"], row["condition"], sum(f["level"] == "hard" for f in findings))
PY
```

The linter checks form only. It cannot check meaning.
