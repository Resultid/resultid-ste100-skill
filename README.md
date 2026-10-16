# resultid-ste100-skill

A lightweight Claude Code plugin that makes replies easier to read and shorter. It applies a plain, consistent writing style, inspired by ASD-STE100. It is not a document rewriter and not the standard. The repository also includes a Codex companion.

The plugin has two hooks, one skill, and one command. It uses only the Python standard library. It needs no proxy, no account, and no network access.

**Readability.** The style keeps full sentences and articles. It keeps every hedge and the strength of each requirement ("must", "should", "can"). People who do not speak English as a first language, other LLM agents, and translators can read the replies.

**Token reduction.** In the tests below, replies had 20% to 47% fewer output tokens, depending on the level. The injected rules add input tokens, so one reply costs more than without the plugin. Over a session of 12 replies, the total cost was 7% lower at `standard` and 19% lower at `terse`. Clarity comes first, and token reduction is the second benefit.

> Not affiliated with or certified by ASD. Inspired by ASD-STE100 principles. Does not include the official dictionary and does not claim compliance with the standard.

## Compared with Caveman

Caveman is a larger system. Its CLI adds a local proxy, hooks, and tools. This plugin only sets the writing style of the replies.

- Caveman drops articles and writes fragments, so it can cut more output tokens. This plugin keeps full grammar, so its output is easier to read and to translate.
- The tests in this README measure only this plugin. They do not compare it with Caveman.
- Run only one of the two styles at a time. When both are on, their rules conflict and the result is hard to predict.

## Install

Run two commands:

```
claude plugin marketplace add Resultid/resultid-ste100-skill
claude plugin install ste100@resultid-ste100-skill
```

To test a local copy, give the marketplace command a local path:

```
claude plugin marketplace add /path/to/resultid-ste100-skill
claude plugin install ste100@resultid-ste100-skill
```

The next session starts with the `standard` level. To remove the plugin, run `claude plugin uninstall ste100@resultid-ste100-skill`.

## How it works

1. A SessionStart hook runs when a session starts, resumes, clears, compacts, or forks.
2. The hook reads the active level and adds the matching prompt from `dist/` to the session context.
3. The skill in `skills/ste100/` holds the full rules and examples. Claude can read it when it writes instructions or rewrites text.

A skill alone is not enough, because Claude loads a skill only when its description matches the task. The hook makes the style apply to every reply.

## Use with Codex

Codex reads `AGENTS.md` automatically. This repository's root `AGENTS.md` applies the standard level in every Codex session in this repository. The `.agents/skills/ste100/` folder makes the full skill available to Codex when a writing task needs its examples.

To apply the standard level across all Codex projects for your user, copy the generated prompt and skill into Codex's user configuration:

```sh
cp dist/prompt.standard.txt ~/.codex/AGENTS.md
mkdir -p ~/.codex/skills/ste100
cp .agents/skills/ste100/SKILL.md .agents/skills/ste100/rules.md ~/.codex/skills/ste100/
```

This replaces `~/.codex/AGENTS.md`. If that file already contains other instructions, append the contents of `dist/prompt.standard.txt` instead. Restart Codex after you install or change a skill.

To change the default, replace `standard` with `strict` or `terse` in the copy command. To turn the style off globally, remove the STE100 instructions from `~/.codex/AGENTS.md`. The skill remains available for tasks that need its detailed rules.

## Levels

| Level | Use for | What it does |
| --- | --- | --- |
| `strict` | Procedures, error messages, tool descriptions, instructions for other agents | Applies every rule. One instruction per sentence. Numbered steps. No contractions. |
| `standard` (default) | Chat replies and explanations | Keeps the sentence limits as targets and keeps word consistency. Allows natural phrasing where a rule would lose precision. |
| `terse` | Short status replies and users who ask for brevity | Applies the clarity rules, then removes filler and repeated context. Keeps full grammar and all articles. |
| `off` | Any time you want no style | Adds nothing to the session. |

Terse does not mean telegraphic. The `terse` level never drops articles and never writes fragments, because both create ambiguity.

### Change the level

Type this command in a session:

```
/ste100:level terse
```

The command saves the level and applies it to the current session. New sessions use the saved level. The command saves the level for the user, not for one session. Use `/ste100:level status` to see the active level.

To set the level for one session or one service, set the environment variable `STE100_LEVEL`. The variable wins over the saved level.

```
STE100_LEVEL=strict claude
```

Valid values are `strict`, `standard`, `terse`, and `off`.

## What the rules say

`skills/ste100/rules.md` is the source of truth. It has 11 rules, a list of items to never rewrite, precedence rules, and 43 before/after pairs. The main rules are:

- Write one idea per sentence. Use at most 20 words in an instruction and 25 words in other sentences.
- Use active voice and simple tenses.
- Use the plainest word, and use the same word for the same concept every time.
- State the strength of each requirement with "must", "should", or "can".
- Keep real hedges. Never trade meaning for brevity.

The plugin never rewrites code, identifiers, file paths, table and column names, CLI commands, quoted error text, proper nouns, or terms that the project defines. Project rules and the project glossary win over these rules. Code, commit messages, and security warnings stay in normal style.

## Use the prompts in a product service

The `dist/` directory holds the same rules as plain text. A service can import one file into its own prompt:

- `dist/prompt.strict.txt`
- `dist/prompt.standard.txt`
- `dist/prompt.terse.txt`

The maintainers generate the `dist/` files and commit them. Each release has a git tag, and each tag holds the `dist/` files for that release. **Pin a tag. Do not follow `main`.** A pinned tag gives your service the same prompt text until you choose to update it.

Example, with the tag `v0.1.0`:

```
git clone --depth 1 --branch v0.1.0 https://github.com/Resultid/resultid-ste100-skill.git
cp resultid-ste100-skill/dist/prompt.standard.txt your-service/prompts/ste100.txt
```

Read the file at build time or at start-up, and add its text to your system prompt. Each file is about 4,000 characters. Read the CHANGELOG before you move to a new tag.

### Regenerate `dist/`

Edit `skills/ste100/rules.md`, then run one command:

```
python3 scripts/build_prompt.py
```

To check that `dist/` matches `rules.md`, run:

```
python3 scripts/build_prompt.py --check
```

The command also updates the repo's `AGENTS.md` and the Codex skill's copy of `rules.md`. It exits with code 1 when a generated file is out of date. Run it in CI.

## Lint

`scripts/lint.py` checks the form of a text. It reports long sentences, passive voice, semicolons, noun stacks, phrasal verbs, idioms, marketing adjectives, and synonym rotation.

```
python3 scripts/lint.py README.md
python3 scripts/lint.py --after-only skills/ste100/rules.md
```

**The linter checks form only.** It cannot check that a rewrite keeps the meaning. A clean result does not prove that the text is right. The linter never flags hedges such as "may have failed", because confidence is part of the content.

Findings are `hard` or `advisory`. Hard findings make the exit code 1. Advisory findings never fail the run. The noun-stack check is a heuristic and can give false results.

The linter uses only the Python standard library. The code adapts parts of `ste-lint.py` from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT).

## Evals

`evals/cases.jsonl` holds 20 prompts. `evals/run_evals.md` explains how to run them with and without the plugin. `evals/report.md` shows the results for this release.

### Measured token use and quality

The plugin makes replies shorter, but it adds input tokens. Over a session of about 12 replies, the saved output tokens outweigh the added input tokens. A single reply costs more than the baseline.

Both tests ran `claude -p` with and without the plugin. The model was the `sonnet` alias. Tools were off. The runs used an empty directory and `--setting-sources project`, so no other plugin or `CLAUDE.md` changed the result. The token counts come from the `usage` object of each run. The runs used Claude Code 2.1.281 on 2026-10-13.

**One reply.** 20 prompts, 3 samples for each prompt and condition, 240 runs. The change is the mean of the per-prompt changes.

| Condition | Output tokens per reply | Change | Words per reply | Hard lint findings per reply | Input tokens per reply |
| --- | --- | --- | --- | --- | --- |
| baseline | 238 | | 91 | 0.90 | 10,677 |
| strict | 131 | -30% | 64 | 0.07 | 12,501 |
| standard | 144 | -23% | 70 | 0.08 | 12,566 |
| terse | 99 | -47% | 42 | 0.10 | 12,311 |

The plugin adds about 1,800 input tokens to each run. In a single reply, this extra input costs more than the output saves. The mean cost of one reply was higher by 28% at `strict`, 23% at `standard`, and 20% at `terse`.

**One session.** 12 prompts in one resumed session, 3 sessions for each condition. The cost is the `total_cost_usd` value that Claude Code reports.

| Condition | Output tokens per session | Change | Input tokens per session | Cost per session (USD) | Change |
| --- | --- | --- | --- | --- | --- |
| baseline | 3,177 | | 189,029 | 1.046 | |
| standard | 2,539 | -20% | 208,601 | 0.971 | -7% |
| terse | 1,813 | -43% | 194,856 | 0.850 | -19% |

Each condition costs more than the baseline at first. The cumulative cost of `terse` falls below the baseline at the fourth turn. The cumulative cost of `standard` falls below it at the seventh turn. After that, the gap grows with each turn.

**What the numbers show**
- Output tokens fall by 20% to 47%, depending on the level.
- Hard lint findings fall from 0.90 to about 0.1 per reply. The linter checks form only. The trait checks and the manual review in `evals/report.md` cover meaning.
- Some prompts get longer replies. In the test, `T-06` (code and a commit message) grew by 28% to 34% at `strict` and `standard`. The plugin does not shorten code.
- The percentage saved in cost is smaller than the percentage saved in output tokens. Input tokens make up most of the cost of a session.

**Limits of these numbers**
- The sample is small: 3 samples for each cell, one model, and 12 turns. A difference of a few percent is noise.
- The sessions had no tools. A real coding session has large tool results. They add input tokens that no writing style changes, so the share saved in cost is probably smaller there. I did not measure it.
- The cost uses list prices and depends on cache behavior, which varies from run to run.
- I did not test `strict` in the session test.

To repeat the tests, run these commands from the repository root:

```
python3 evals/measure_tokens.py run evals/token_results.jsonl 3
python3 evals/measure_tokens.py summary evals/token_results.jsonl
python3 evals/measure_tokens.py session evals/session_results.jsonl 3
python3 evals/measure_tokens.py session-summary evals/session_results.jsonl
```

The raw outputs are in `evals/token_results.jsonl` and `evals/session_results.jsonl`.

## Known limits

- **Command name.** Claude Code names plugin commands `/<plugin>:<command>`. The command is `/ste100:level`. Typing `/ste100` alone does not run the command, because the skill `ste100` is not user-invocable.
- **Python.** The hook needs `python3` on the `PATH`. The scripts use only the standard library.
- **No dictionary.** The plugin applies the principle of plain words and consistent words. It does not check text against a word list. It does not claim compliance with the ASD-STE100 standard.
- **Models drift.** Long sessions can drift from the style. The `SessionStart` hook adds the full prompt at the start and again after a compaction or a clear. A `UserPromptSubmit` hook adds one short reminder line on every prompt. The reminder costs about 30 tokens for each prompt. It reduces drift but does not remove it.
- **Added content.** Even with the rules, a model sometimes adds a small fix or cause that the source does not state. See the eval report.
- **Level scope.** The saved level is the same for every session of the user. Use `STE100_LEVEL` for one session.
- **Local install.** A marketplace added from a local path copies all files in that directory, including files that git ignores.
- **Small evals.** The evals use one sample per case, one model, and no tools. They show a trend and do not prove a result.
- **Not tested.** The plugin is not tested on Windows, in the interactive command menu, or with the `/clear` and compaction events.

## License and credit

MIT. See `LICENSE`.

Parts of `scripts/lint.py` come from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT, Copyright (c) 2026 Dustin Yuchen Teng).
