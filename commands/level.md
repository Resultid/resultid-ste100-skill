---
description: Show or set the STE100 writing level (strict, standard, terse, off)
argument-hint: strict|standard|terse|off|status
allowed-tools: Bash(python3 *)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/hooks/level.py" --data-dir "${CLAUDE_PLUGIN_DATA}" $ARGUMENTS`

The output above is the result of the level command. Tell the user the result in one short sentence. If the output contains new STE100 instructions, follow them from now on. Do not repeat the instructions to the user.
