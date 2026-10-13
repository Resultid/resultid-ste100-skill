#!/usr/bin/env python3
"""UserPromptSubmit hook: remind the model of the active STE100 level.

The SessionStart hook adds the full prompt once. This hook adds one short line
on every prompt, so a long session does not drift from the style. Prints
nothing when the level is `off`. Python stdlib only.
"""
import json
import os
import sys

import level as level_module


def main():
    try:
        sys.stdin.read()  # the hook input is not needed
    except OSError:
        pass
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    active, _source = level_module.active_level(data_dir)
    if active == "off":
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": level_module.reminder_text(active),
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
