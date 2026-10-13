# Changelog

This file lists all notable changes. Product services pin a release tag. Each tag holds the `dist/` files that the build script generated from `skills/ste100/rules.md` at that tag.

## 0.1.3

- Add a `UserPromptSubmit` hook, `hooks/prompt_reminder.py`. It adds one short reminder of the active level on every prompt, to reduce drift in long sessions. It prints nothing when the level is `off`.
- Add `tests/test_hooks.py`. Run it with `python3 -m unittest discover -s tests -v`.
- Correct the README note about drift.

## 0.1.2

- Clarify the plugin description and the first line of the README: the plugin is an always-on response style, not a document rewriter and not the ASD-STE100 standard.
- Drop the extra word `level` from the command. Use `/ste100:level terse`. The old form `/ste100:level level terse` no longer works. Change the argument hint to `strict|standard|terse|off|status`.

## 0.1.1

- Fix the command name clash. The command had the same name as the skill `ste100`, so `/ste100` showed "This skill can only be invoked by Claude". Rename `commands/ste100.md` to `commands/level.md`. The command is now `/ste100:level strict|standard|terse|off`.

## 0.1.0

First release.

- Add the `ste100` plugin with a SessionStart hook that injects the active level in every session.
- Add three levels: `strict`, `standard` (default), and `terse`. Add the value `off`.
- Add the command `/ste100:ste100 level strict|standard|terse|off`.
- Add `skills/ste100/rules.md` as the single source of truth: 11 rules, a never-rewrite list, precedence rules, and 43 before/after pairs.
- Add `scripts/build_prompt.py`. It generates `dist/prompt.strict.txt`, `dist/prompt.standard.txt`, and `dist/prompt.terse.txt`. The option `--check` reports when `dist/` differs from `rules.md`.
- Add `scripts/lint.py`. It checks form only. Parts of it adapt `ste-lint.py` from danyuchn/asd-ste100-skill (MIT).
- Add 20 eval cases, the run method, and the eval report in `evals/`.
