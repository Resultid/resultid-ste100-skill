# Changelog

This file lists all notable changes. Product services pin a release tag. Each tag holds the `dist/` files that the build script generated from `skills/ste100/rules.md` at that tag.

## 0.1.0

First release.

- Add the `ste100` plugin with a SessionStart hook that injects the active level in every session.
- Add three levels: `strict`, `standard` (default), and `terse`. Add the value `off`.
- Add the command `/ste100:ste100 level strict|standard|terse|off`.
- Add `skills/ste100/rules.md` as the single source of truth: 11 rules, a never-rewrite list, precedence rules, and 43 before/after pairs.
- Add `scripts/build_prompt.py`. It generates `dist/prompt.strict.txt`, `dist/prompt.standard.txt`, and `dist/prompt.terse.txt`. The option `--check` reports when `dist/` differs from `rules.md`.
- Add `scripts/lint.py`. It checks form only. Parts of it adapt `ste-lint.py` from danyuchn/asd-ste100-skill (MIT).
- Add 20 eval cases, the run method, and the eval report in `evals/`.
