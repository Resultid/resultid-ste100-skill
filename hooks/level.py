#!/usr/bin/env python3
"""Read and write the active STE100 level.

Precedence for the active level:
1. The STE100_LEVEL environment variable.
2. The state file `level` in the plugin data directory.
3. The default, `standard`.

CLI (used by the /ste100 command):
    level.py --data-dir DIR [level] [strict|standard|terse|off]
    level.py --data-dir DIR status
Python stdlib only.
"""
import argparse
import os
import sys
from pathlib import Path

LEVELS = ("strict", "standard", "terse")
VALID = LEVELS + ("off",)
DEFAULT = "standard"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def normalize(value):
    value = (value or "").strip().lower()
    return value if value in VALID else None


def state_file(data_dir):
    return Path(data_dir) / "level" if data_dir else None


def read_state(data_dir):
    path = state_file(data_dir)
    if path is None:
        return None
    try:
        return normalize(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def write_state(data_dir, level):
    path = state_file(data_dir)
    if path is None:
        raise OSError("no data directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(level + "\n", encoding="utf-8")


def active_level(data_dir, environ=None):
    """Return (level, source). Source is 'env', 'state', or 'default'."""
    environ = os.environ if environ is None else environ
    from_env = normalize(environ.get("STE100_LEVEL"))
    if from_env:
        return from_env, "env"
    from_state = read_state(data_dir)
    if from_state:
        return from_state, "state"
    return DEFAULT, "default"


def prompt_text(level):
    path = PLUGIN_ROOT / "dist" / f"prompt.{level}.txt"
    return path.read_text(encoding="utf-8")


def main(argv):
    parser = argparse.ArgumentParser(description="Show or set the STE100 level.")
    parser.add_argument("--data-dir", default=os.environ.get("CLAUDE_PLUGIN_DATA", ""))
    parser.add_argument("words", nargs="*")
    args = parser.parse_args(argv)
    words = [w.lower() for w in args.words]
    if words[:1] == ["level"]:
        words = words[1:]

    if words and words[0] != "status":
        level = normalize(words[0])
        if level is None or len(words) > 1:
            print(f"Unknown level: {' '.join(args.words)}. "
                  f"Use one of: {', '.join(VALID)}.")
            return 0
        try:
            write_state(args.data_dir, level)
        except OSError as error:
            print(f"Could not save the level ({error}). The level applies to this session only.")
        else:
            print(f"STE100 level saved: {level}.")
        env_level = normalize(os.environ.get("STE100_LEVEL"))
        if env_level and env_level != level:
            print(f"Note: STE100_LEVEL={env_level} overrides the saved level in new sessions.")
        print()
        if level == "off":
            print("STE100 is off. Stop applying the STE100 style to your replies from now on.")
        else:
            print(f"From now on, write in the STE100 {level} style. "
                  "These instructions replace any earlier STE100 level.")
            print()
            print(prompt_text(level))
        return 0

    level, source = active_level(args.data_dir)
    print(f"STE100 level: {level} (source: {source}).")
    print(f"Available levels: {', '.join(VALID)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
