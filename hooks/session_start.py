#!/usr/bin/env python3
"""SessionStart hook: inject the active STE100 prompt into the session.

Reads the level from level.active_level(). Prints nothing when the level is
`off` or when the prompt file is missing. Python stdlib only.
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
    try:
        text = level_module.prompt_text(active)
    except OSError as error:
        print(f"ste100: cannot read the prompt file: {error}", file=sys.stderr)
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
