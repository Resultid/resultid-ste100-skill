#!/usr/bin/env python3
"""Generate dist/prompt.<level>.txt from skills/ste100/rules.md.

Usage:
    build_prompt.py            # write the files in dist/
    build_prompt.py --check    # exit 1 if dist/ differs from a fresh build

Each file holds: the preamble, the rules, the never-rewrite list, the
precedence list, the section for one level, and the example pairs tagged
`inject` for that level. Python stdlib only.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "skills" / "ste100" / "rules.md"
DIST = ROOT / "dist"
LEVELS = ("strict", "standard", "terse")
MAX_CHARS = 9000  # the SessionStart hook accepts at most 10,000 characters

PAIR_HEAD = re.compile(r"^\*\*(?P<id>[A-Z]\d+)\*\*\s*·\s*(?P<tags>.*)$")
FIELD = re.compile(r"^- (?P<key>Before|After|Avoid|Why): (?P<value>.*)$")


def plain(text):
    """Remove Markdown bold markers. Keep backticks, which mark code."""
    return text.replace("**", "")


def sections(lines, prefix):
    """Split lines into {title: [lines]} at headings that start with prefix."""
    result, title = {}, None
    for line in lines:
        if line.startswith(prefix) and not line.startswith(prefix + "#"):
            title = line[len(prefix):].strip()
            result[title] = []
        elif title is not None:
            result[title].append(line)
    return result


def trim(lines):
    text = "\n".join(lines).strip("\n")
    return plain(text)


def parse_pairs(lines):
    pairs, current = [], None
    for line in lines:
        head = PAIR_HEAD.match(line)
        if head:
            tags = [t.strip() for t in head.group("tags").split("·")]
            current = {"id": head.group("id"), "tags": tags, "fields": {}}
            pairs.append(current)
            continue
        field = FIELD.match(line)
        if field and current is not None:
            current["fields"][field.group("key")] = field.group("value").strip()
    return pairs


def render_pair(pair):
    fields = pair["fields"]
    out = [f"Before: {plain(fields['Before'])}", f"After: {plain(fields['After'])}"]
    if "Avoid" in fields:
        out.append(f"Wrong: {plain(fields['Avoid'].replace('Avoid: ', ''))}")
    return "\n".join(out)


def build(level, text):
    top = sections(text.splitlines(), "## ")
    levels = sections(top["Levels"], "### ")
    examples = sections(top["Examples"], "### ")
    pairs = parse_pairs(examples[f"{level} examples"])
    injected = [p for p in pairs if "inject" in p["tags"]]

    preamble = trim(top["Prompt preamble"]).split("\n\n", 1)[1]  # drop build note
    parts = [
        preamble.replace("{level}", level),
        "RULES\n" + trim(top["Rules"]),
        "NEVER REWRITE\n" + trim(top["Never rewrite"]),
        "PRECEDENCE\n" + trim(top["Precedence"]),
        f"LEVEL: {level}\n" + trim(levels[level]),
        "EXAMPLES\n" + "\n\n".join(render_pair(p) for p in injected),
    ]
    return "\n\n".join(parts) + "\n"


def main(argv):
    check = "--check" in argv
    text = RULES.read_text(encoding="utf-8")
    failed = False
    for level in LEVELS:
        built = build(level, text)
        if len(built) > MAX_CHARS:
            print(f"{level}: {len(built)} characters, over the limit of {MAX_CHARS}")
            failed = True
        path = DIST / f"prompt.{level}.txt"
        if check:
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != built:
                print(f"{path.relative_to(ROOT)} is out of date. Run scripts/build_prompt.py.")
                failed = True
        else:
            DIST.mkdir(exist_ok=True)
            path.write_text(built, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)} ({len(built)} characters)")
    if check and not failed:
        print("dist/ matches rules.md")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
