# resultid-ste100-skill

An always-on plain-writing style for Claude Code replies, inspired by ASD-STE100. It is not a document rewriter and not the standard. It is a Claude Code plugin with a Codex companion. The style follows most of the STE100 discipline, without the fixed vocabulary. Claude Code uses a SessionStart hook. Codex uses automatic `AGENTS.md` instructions and a discoverable skill.

The readers can be people who do not speak English as a first language, other LLM agents, and translators. For these readers, clarity matters more than saving tokens.

> Not affiliated with or certified by ASD. Inspired by ASD-STE100 principles. Does not include the official dictionary and does not claim compliance with the standard.

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

## Known limits

- **Command name.** Claude Code names plugin commands `/<plugin>:<command>`. The command is `/ste100:level`. Typing `/ste100` alone does not run the command, because the skill `ste100` is not user-invocable.
- **Python.** The hook needs `python3` on the `PATH`. The scripts use only the standard library.
- **No dictionary.** The plugin applies the principle of plain words and consistent words. It does not check text against a word list. It does not claim compliance with the ASD-STE100 standard.
- **Models drift.** Long sessions can drift from the style. The hook adds the prompt again after a compaction or a clear.
- **Added content.** Even with the rules, a model sometimes adds a small fix or cause that the source does not state. See the eval report.
- **Level scope.** The saved level is the same for every session of the user. Use `STE100_LEVEL` for one session.
- **Local install.** A marketplace added from a local path copies all files in that directory, including files that git ignores.
- **Small evals.** The evals use one sample per case, one model, and no tools. They show a trend and do not prove a result.
- **Not tested.** The plugin is not tested on Windows, in the interactive command menu, or with the `/clear` and compaction events.

## License and credit

MIT. See `LICENSE`.

Parts of `scripts/lint.py` come from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT, Copyright (c) 2026 Dustin Yuchen Teng).
