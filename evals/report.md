# Eval report, v0.1.0

This report covers 20 cases, run with and without the plugin at each level. See `run_evals.md` for the method and `results.jsonl` for the raw outputs.

## Setup

- Model: the `sonnet` alias of Claude Code 2.1.281, in `claude -p` mode with tools disabled.
- Each case ran once per condition: `baseline`, `strict`, `standard`, `terse`. That is 80 runs per round.
- The plugin runs used the real SessionStart hook, with `STE100_LEVEL` set to the level.
- Round 1 used the first draft of `rules.md`. Round 2 used the tuned rules. The raw outputs of round 1 are in `results.round1.jsonl`, and those of round 2 are in `results.jsonl`.

Each cell is one sample from a model that samples at random, so small differences between rounds are noise. The large differences are not.

## Do the levels change the output?

Yes. The numbers below are per case, and the linter counts only form problems.

| Condition | Round | Words per case | Hard lint findings per case | Sentences over the limit | Passive-voice hits |
| --- | --- | --- | --- | --- | --- |
| baseline | 1 | 80.8 | 0.90 | 14 | 4 |
| strict | 1 | 69.8 | 0.00 | 0 | 0 |
| standard | 1 | 65.8 | 0.05 | 1 | 1 |
| terse | 1 | 48.1 | 0.10 | 0 | 0 |
| baseline | 2 | 102.5 | 1.20 | 18 | 11 |
| strict | 2 | 62.0 | 0.00 | 0 | 0 |
| standard | 2 | 63.1 | 0.00 | 0 | 0 |
| terse | 2 | 40.0 | 0.05 | 1 | 1 |

The baseline word count rose from round 1 to round 2 because of random variation in a few long answers. Terse output is the shortest in both rounds.

A sample of the visible change, case S-01 (round 2). The input is an error message with two hedges.

| Condition | Output |
| --- | --- |
| baseline | Your upload couldn't be processed because the file's columns don't match the expected format. Please check that you're using the latest template and try again. |
| strict | Your upload may have failed. A possible cause is a column format that does not match the expected template. Try the latest template version. |
| standard | Your upload may have failed because the file's columns do not match the expected format. This can happen if you used an outdated template. |
| terse | Your upload may have failed because the file's columns do not match the expected format. Try using the latest template. |

The baseline states the failure as a fact. All three levels keep "may have failed".

## Trait checks

The script in `run_evals.md` tests 33 traits with text patterns. It is a rough check and it complements the manual review below.

| Condition | Round 1 | Round 2 |
| --- | --- | --- |
| baseline | 29/33 | 29/33 |
| strict | 32/33 | 33/33 |
| standard | 32/33 | 32/33 |
| terse | 30/33 | 33/33 |

Two failures are false alarms of the patterns. In `R-02` (standard), the output says "The re-run passed with no errors", and the pattern looks for "passes". In `T-03` (baseline), the output says "I can't determine causation", and the pattern misses it. The other baseline failures are real. In `S-01`, the baseline states a failure as fact. In `S-07`, it turns a hedge into a purpose: "to prevent columns from being dropped".

## Problems found in round 1, and the changes

| Case | Level | Problem | Change to `rules.md` |
| --- | --- | --- | --- |
| S-01 | terse | Dropped a needed qualifier. "May have failed" became "failed", and the output added a fix that the source does not give. | Rule 9: do not turn a possible cause into a fact, and do not add a fact, cause, or fix. Terse level: keep every hedge, and removing filler never removes a hedge. |
| S-07 | strict, terse | Changed the requirement strength: "should" became "must". | Rule 9: keep the strength that the source gives. New pair S15 (tagged `keep` and `inject`). |
| T-05 | terse | Too robotic. "Use a line chart for trends, a bar chart for month-to-month comparison" omits the second verb. | Rule 8: every sentence has a subject and a verb. New pair R15. |
| R-05 | terse | Too robotic. The answer "48 seconds, for 48,213 rows." has no verb. | Terse level: a one-line answer is still a full sentence. Pair R15. |
| T-02 | baseline | The baseline run went looking for a project in the directory and gave no answer. | None. Random behavior, and the round 2 baseline answers the question. |
| T-02 | terse | Used two semicolons. | None. See "Known remaining problems". |

No case broke a project term in either round. Cases `S-07` and `R-06` kept "mapping profile", "Workspace Admin", "Segment", and "Cohort" in every condition.

## Round 2 results by risk

- **Hedges and conditions kept:** `S-01`, `T-03`, `R-03`, `S-05`. All levels keep the hedge, the condition, or the exception.
- **Project terms kept:** `S-07`, `R-06`, `S-03`, `S-04`. All levels keep the terms exactly.
- **Code, commit, and security text written normally:** `T-06` and `T-07`. The code and the commit message look the same as the baseline, and the security warning keeps every risk.
- **Natural phrasing at standard:** `T-05` reads naturally, with full sentences of varied shape.

## Known remaining problems

These problems remain after tuning. The rules do not remove them.

1. **Added fixes.** In `S-01`, strict and terse still add "Try the latest template". The source names an outdated template as a possible cause but gives no fix. Rule 9 now forbids this, and the model still does it in some runs.
2. **Missing articles in terse headlines.** The terse output of `R-02` starts with "Schema check passed." without "The". The sentence is complete, but it breaks rule 8.
3. **Rare lint findings in terse.** One terse output per round has a hard finding: two semicolons in `T-02` (round 1) and a 26-word sentence in `T-02` (round 2). The linter catches them.
4. **Staccato strict output.** Strict output is repetitive ("The query ... The query ..."). This is the cost of one idea per sentence and of repeating the noun. It suits procedures and tool descriptions. Use `standard` for chat.
5. **Small sample.** The eval has one sample per cell and one model. A change of one or two traits between rounds is not a trend.
