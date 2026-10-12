---
name: ste100
description: Plain writing style based on ASD-STE100 principles, without the fixed vocabulary. Claude Code receives its active level from a SessionStart hook. Codex uses AGENTS.md for automatic style instructions. Load this skill for the full rules and examples.
user-invocable: false
---

# STE100 writing style

This skill applies most of the STE100 discipline, without the fixed vocabulary. It does not include the ASD-STE100 dictionary.

## How to use this skill

1. Read [rules.md](rules.md). It is the source of truth for the rules, the three levels, and the before/after examples.
2. Find the active level in the session context. Claude Code's SessionStart hook states it. Codex gets its default from `AGENTS.md`. If no level is set, use `standard`. If the level is `off`, do not apply this style.
3. Apply the rules of that level to the prose you write.
4. Do not rewrite the items in the "Never rewrite" section of rules.md.
5. Follow the "Precedence" section: project rules and the project glossary win. Write code, commit messages, and security warnings in normal style.

## Levels

- `strict`: procedures, error messages, tool descriptions, and instructions to other agents.
- `standard` (default): chat replies and explanations.
- `terse`: the standard rules, then no filler and no repeated context. Keep full grammar.

In Claude Code, the user changes the level with `/ste100:ste100 level strict|standard|terse|off`. The environment variable `STE100_LEVEL` overrides the saved level. In Codex, the user changes the active level in the applicable `AGENTS.md` instructions.

## When a rewrite would lose meaning

Keep the longer wording. Never turn a hedge into a fact, never drop a condition or an exception, and never merge "must" and "should". See the pairs tagged `keep` in rules.md.
