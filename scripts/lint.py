#!/usr/bin/env python3
"""Form linter for the STE100 rules in skills/ste100/rules.md.

This linter checks FORM only: sentence length, passive voice, semicolons,
noun stacks, phrasal verbs, and a few related patterns. It cannot verify that
a rewrite keeps the meaning. A clean result does not prove a text is correct.

Adapted from ste-lint.py in https://github.com/danyuchn/asd-ste100-skill
(MIT License, Copyright (c) 2026 Dustin Yuchen Teng). The reuse covers the
rule-table design, the code-fence, inline-code and table handling, the
modal-perfect (hedge) protection, the synonym groups, the dangling-conjunction
check, and the self-test approach. See LICENSE.

Hedges and modality (may, might, could) are never flagged. Confidence is
content, not style.

Usage:
    lint.py FILE [FILE ...]
    echo "text" | lint.py [--json]
    lint.py --after-only FILE      # lint only the text of "After:" lines
    lint.py --baseline N FILE      # pass unless hard findings exceed N
    lint.py --disable rule1,rule2 FILE
    lint.py --selftest

Exit 1 when hard findings exceed the baseline (default 0). Advisory findings
never fail the run. Python stdlib only.
"""
import json
import re
import sys

INSTRUCTION_MAX = 20
OTHER_MAX = 25
NOUN_STACK_MAX = 3

# Irregular past participles for the present-perfect check.
IRREGULAR_PARTICIPLES = (
    "given|taken|made|done|found|seen|known|shown|written|built|sent|set|run|"
    "read|kept|held|left|put|cut|hit|let|shut|split|spread|begun|become|come|"
    "gone|got|gotten|lost|met|paid|said|sold|told|thought|brought|bought|caught|"
    "taught|won|worn|torn|born|drawn|grown|thrown|flown|driven|risen|chosen|"
    "broken|spoken|frozen|hidden|ridden|forgotten|fallen|eaten|beaten|"
    "understood|stood|struck|stuck|swung|hung|led|fed|bled|fled|sped|bound|"
    "wound|dug|spun|slid|bit|lit|quit"
)
PASSIVE_PARTICIPLES = "given|taken|made|done|found|seen|known|shown|written|built|sent|set|run|read|kept|held|left|put"
MODAL_PERFECT_PREFIX = re.compile(
    r"\b(?:may|might|could|should|would|must|can|will|shall)"
    r"(?:\s+not|n['’]t)?\s+$", re.I,
)

PHRASAL_VERBS = (
    r"spin(?:ning|s)? up|spun up|reach(?:ing|es|ed)? out|div(?:e|es|ing|ed) into|"
    r"dove into|dig(?:s|ging)? into|dug into|kick(?:ing|s|ed)? off|"
    r"circl(?:e|es|ing|ed) back|loop(?:s|ed|ing)? back|touch(?:ing|es|ed)? base|"
    r"set(?:s|ting)? up|pull(?:s|ed|ing)? up|go(?:es|ing)? through|went through|"
    r"figur(?:e|es|ed|ing) out|hook(?:s|ed|ing)? up|take(?:s|n)? off|took off|"
    r"look(?:s|ed|ing)? into|come(?:s)? up with|came up with|carry(?:ing)? on|"
    r"carried on|point(?:s|ed|ing)? out|bring(?:s|ing)? up|brought up|"
    r"fill(?:s|ed|ing)? in|fill(?:s|ed|ing)? out|back(?:s|ed|ing)? out|"
    r"roll(?:s|ed|ing)? out|wrap(?:s|ped|ping)? up|sort(?:s|ed|ing)? out|"
    r"work(?:s|ed|ing)? out|boil(?:s|ed|ing)? down to|get(?:s|ting)? around"
)

IDIOMS = (
    r"move the needle|moves the needle|moved the needle|low[- ]hanging fruit|"
    r"hit the ground running|at the end of the day|deep[- ]dive|silver bullet|"
    r"under the hood|out of the box|heavy lifting|ballpark|touch base|"
    r"on the same page|game plan|sweet spot|tip of the iceberg|"
    r"bang for (?:the|your) buck|think outside the box"
)

MARKETING = (
    r"seamless(?:ly)?|robust(?:ly)?|cutting-edge|effortless(?:ly)?|"
    r"blazing[- ]fast|world-class|state-of-the-art|game-chang(?:ing|er)|"
    r"powerful(?:ly)?|supercharg(?:e|es|ed|ing)|next-generation|best-in-class|"
    r"revolutionar(?:y|ily)|turbocharg(?:e|es|ed|ing)|unparalleled|"
    r"mission-critical|industry-leading"
)

RULES = [
    ("semicolon", "hard", re.compile(r";"),
     "Rule 11: no semicolons. Split into separate sentences."),
    ("phrasal-verb", "hard", re.compile(r"\b(" + PHRASAL_VERBS + r")\b", re.I),
     "Rule 7: use one plain verb in place of this phrasal verb."),
    ("idiom", "hard", re.compile(r"\b(" + IDIOMS + r")\b", re.I),
     "Rule 11: no idioms. Say the plain meaning."),
    ("marketing-adjective", "hard", re.compile(r"\b(" + MARKETING + r")\b", re.I),
     "Rule 11: no marketing adjectives. Delete it, or give the measurement."),
    ("nominalization", "hard",
     re.compile(r"\b(perform|performs|performed|conduct|conducts|conducted|carry out|carries out|carried out)\s+(?:a|an|the)\s+\w+(?:tion|sion|ment|ance|ence|ysis)\b", re.I),
     "Rule 4: action frozen into a noun. Use the verb."),
    ("plain-word", "hard",
     re.compile(r"\b(utili[sz](?:e|es|ed|ing)|initiat(?:e|es|ed|ing)|demonstrat(?:e|es|ed|ing)|"
                r"ascertain(?:s|ed|ing)?|commenc(?:e|es|ed|ing)|terminat(?:e|es|ed|ing)|"
                r"prior to|subsequent to|in order to|due to the fact that|"
                r"leverag(?:e|es|ed|ing))\b", re.I),
     "Rule 4: use the plainest word (use, start, show, find, before, after, to, because)."),
    ("passive-voice", "advisory",
     re.compile(r"\b(is|are|was|were|been|being)\s+(\w+ed|" + PASSIVE_PARTICIPLES + r")\b(?!\s+(?:to|for|by)\s+\w+ing)", re.I),
     "Rule 2: possible passive voice. Name the actor, unless the actor is unknown or does not matter."),
    ("present-perfect", "advisory",
     re.compile(r"\b(has|have|had)\s+(?:been\s+)?(?:\w+(?:ed|en)|" + IRREGULAR_PARTICIPLES + r")\b", re.I),
     "Rule 3: compound tense. Use a simple tense, unless the meaning needs this form."),
]

# One word, one concept: groups of words often rotated for one thing.
# Each group is advisory. A project can define the members as different things.
SYNONYM_GROUPS = [
    ("check", "verify", "confirm", "validate"),
    ("delete", "remove", "erase"),
    ("start", "launch", "begin", "initiate"),
    ("stop", "halt", "terminate"),
    ("show", "display"),
    ("use", "utilize", "employ"),
    ("fix", "repair", "correct"),
    ("send", "transmit"),
    ("get", "retrieve", "fetch", "obtain"),
    ("change", "modify", "alter"),
    ("metric", "kpi", "measure"),
    ("dataset", "spreadsheet", "sheet"),
    ("dashboard", "report page"),
    ("upload", "ingest"),
]

IMPERATIVE_VERBS = frozenset("""
add allow apply ask avoid back call change check choose clear click close
compare confirm connect contact copy create define delete disable do download
drag enable enter ensure export fill find fix follow generate give go import
increase install keep leave limit load log make map merge move name note
open paste pick press provide read record refresh reload remove rename
replace report request reset restart restore retry return review run save
search select send set show sign split start stop store submit switch tap
test try turn type update upload use verify view wait warn write
""".split())
INSTRUCTION_LEAD = re.compile(r"^(?:do not|don't|never|always|warning:|note:|make sure)\b", re.I)

# Words that are not nouns. A run of other words counts as a noun stack.
NOT_NOUNS = frozenset("""
a an the this that these those some any each every no all both either neither
and or but nor so yet if then than because while when where whether although
of in on at to for from by with without about into onto over under after
before between through during within across against per via as like
i you he she it we they me him her us them my your his its our their
is are was were be been being am do does did done have has had having
will would shall should can could may might must
not also only just very more most less least much many few other another
such same own too still even ever never always often usually sometimes
here there now soon again already once twice first second third next last
new old big small large high low long short good bad right wrong early late
able possible different similar available active current final single
get gets got make makes made take takes took give gives gave go goes went
see sees saw show shows shown find finds found keep keeps kept let lets put
puts know knows need needs want wants try tries tried fail fails help helps
mean means include includes exclude excludes contain contains
""".split())

CODE_FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
LIST_ITEM_START = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>[-*+]|[0-9]+[.)])(?P<gap> +)(?P<body>.*)$"
)
STEP_MARKER = re.compile(r"(?:^|\s)\d+[.)]\s+(?=[A-Z*`])")
CONJUNCTION_END = re.compile(r"\b(?:and|or)\s*$", re.I)
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")


def _word_re(base):
    return re.compile(r"\b" + re.escape(base) + r"(?:s|es|ed|d|ing)?\b", re.I)


def _leading_spaces(line):
    return len(line) - len(line.lstrip(" "))


def _is_list_continuation(line, content_indent):
    if not line.strip():
        return True
    if LIST_ITEM_START.match(line):
        return False
    return _leading_spaces(line) >= content_indent


def _split_table_row(line):
    """Return trimmed table cells with their source columns, or None."""
    left = len(line) - len(line.lstrip())
    right = len(line.rstrip())
    content = line[left:right]
    if "|" not in content:
        return None
    if content.startswith("|"):
        content = content[1:]
        left += 1
    if content.endswith("|"):
        content = content[:-1]
    raw_cells = re.split(r"(?<!\\)\|", content)
    if len(raw_cells) < 2:
        return None
    cells, column = [], left
    for raw_cell in raw_cells:
        leading = len(raw_cell) - len(raw_cell.lstrip())
        cells.append((raw_cell.strip(), column + leading))
        column += len(raw_cell) + 1
    return cells


def _markdown_table_cells(lines):
    """Map ordinary Markdown table rows to their cells (separator row anchors)."""
    table_cells, index = {}, 1
    while index < len(lines):
        separator = _split_table_row(lines[index])
        header = _split_table_row(lines[index - 1])
        if (not separator or not header or len(separator) != len(header)
                or not all(TABLE_SEPARATOR_CELL.fullmatch(cell) for cell, _ in separator)):
            index += 1
            continue
        table_cells[index - 1] = header
        table_cells[index] = []
        index += 1
        while index < len(lines):
            row = _split_table_row(lines[index])
            if not row or len(row) != len(separator):
                break
            table_cells[index] = row
            index += 1
    return table_cells


def _dangling_conjunction_findings(lines, filename):
    findings, in_fence, index = [], False, 0
    while index < len(lines):
        line = lines[index]
        if CODE_FENCE.match(line.strip()):
            in_fence = not in_fence
            index += 1
            continue
        start = None if in_fence else LIST_ITEM_START.match(line)
        if not start:
            index += 1
            continue
        content_indent = (len(start.group("indent")) + len(start.group("marker"))
                          + len(start.group("gap")))
        item_lines, next_index, item_fence = [(index, start.group("body"))], index + 1, False
        while next_index < len(lines):
            candidate = lines[next_index]
            if CODE_FENCE.match(candidate.strip()):
                item_fence = not item_fence
                next_index += 1
                continue
            if item_fence:
                next_index += 1
                continue
            if not _is_list_continuation(candidate, content_indent):
                break
            item_lines.append((next_index, candidate))
            next_index += 1
        meaningful = [(i, INLINE_CODE.sub(" CODE ", t).strip()) for i, t in item_lines
                      if INLINE_CODE.sub(" CODE ", t).strip()]
        if meaningful:
            end_index, end_line = meaningful[-1]
            if CONJUNCTION_END.search(end_line):
                findings.append({
                    "file": filename, "line": end_index + 1,
                    "col": start.start("marker") + 1 if end_index == index else 1,
                    "rule": "dangling-conjunction", "level": "hard", "match": end_line,
                    "message": "List item ends with a conjunction. Complete the item or join it to the next item.",
                })
        index = next_index
    return findings


def noun_stacks(text):
    """Yield (start, words) for runs of more than NOUN_STACK_MAX noun-like words.

    Heuristic only. A word counts as noun-like when it is alphabetic, not in
    NOT_NOUNS, and does not end in -ly or -ed. Hyphenated words count by part.
    Inline code and punctuation end a run.
    """
    for match in re.finditer(r"[A-Za-z][A-Za-z'’-]*(?:\s+[A-Za-z][A-Za-z'’-]*)*", text):
        run, run_start = [], None
        for word in re.finditer(r"[A-Za-z][A-Za-z'’]*", match.group(0)):
            token = word.group(0).lower()
            noun_like = (token not in NOT_NOUNS and not token.endswith(("ly", "ed"))
                         and len(token) > 2)
            if noun_like:
                if not run:
                    run_start = match.start() + word.start()
                run.append(word.group(0))
                # A plural noun (or a verb ending in -s) ends a noun phrase.
                if token.endswith("s") and not token.endswith(("ss", "us", "is")):
                    if len(run) > NOUN_STACK_MAX:
                        yield run_start, run
                    run = []
            else:
                if len(run) > NOUN_STACK_MAX:
                    yield run_start, run
                run = []
        if len(run) > NOUN_STACK_MAX:
            yield run_start, run


def clean_markup(text):
    text = LINK.sub(r"\1", text)
    return text.replace("**", "").replace("__", "")


def sentence_cap(sentence):
    """Return (cap, kind): 20 for an instruction, 25 for any other sentence."""
    stripped = re.sub(r"^[-*+>\s]+", "", sentence).strip()
    stripped = re.sub(r"^\d+[.)]\s*", "", stripped)
    first = re.match(r"[A-Za-z']+", stripped)
    if INSTRUCTION_LEAD.match(stripped) or (first and first.group(0).lower() in IMPERATIVE_VERBS):
        return INSTRUCTION_MAX, "instruction"
    return OTHER_MAX, "sentence"


def lint(text, filename="<stdin>", after_only=False):
    findings, words_total, in_fence = [], 0, False
    lines = text.splitlines()
    table_cells = _markdown_table_cells(lines)
    seen = {}  # (group index, base) -> (line, col, match)
    for lineno, raw_line in enumerate(lines, 1):
        if CODE_FENCE.match(raw_line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        source_offset = 0
        if after_only:
            marker = re.match(r"^\s*(?:[-*+]\s+)?After:\s*", raw_line)
            if not marker:
                continue
            raw_line = raw_line[marker.end():]
            source_offset = marker.end()
        is_heading = bool(HEADING.match(raw_line))
        for segment, source_column in table_cells.get(lineno - 1, [(raw_line, source_offset)]):
            line = INLINE_CODE.sub(" CODE ", segment)
            line = clean_markup(line)
            words_total += len(line.split())
            for rule_id, level, pattern, message in RULES:
                for m in pattern.finditer(line):
                    if rule_id == "present-perfect" and MODAL_PERFECT_PREFIX.search(line[:m.start()]):
                        continue
                    findings.append({"file": filename, "line": lineno,
                                     "col": source_column + m.start() + 1,
                                     "rule": rule_id, "level": level,
                                     "match": m.group(0), "message": message})
            for gi, group in enumerate(SYNONYM_GROUPS):
                for base in group:
                    if (gi, base) not in seen:
                        m = _word_re(base).search(line)
                        if m:
                            seen[(gi, base)] = (lineno, source_column + m.start() + 1, m.group(0))
            if is_heading:
                continue
            for start, run in noun_stacks(line):
                findings.append({"file": filename, "line": lineno,
                                 "col": source_column + start + 1,
                                 "rule": "noun-stack", "level": "advisory",
                                 "match": " ".join(run),
                                 "message": f"Rule 6: {len(run)} nouns in a row (limit {NOUN_STACK_MAX}). Rewrite with prepositions. This check is a heuristic."})
            for part in re.split(r"(?<=[.!?])\s+|(?<=:)\s+(?=\d+[.)]\s)", STEP_MARKER.sub(" ", line)):
                n = len(part.split())
                cap, kind = sentence_cap(part)
                if n > cap:
                    findings.append({"file": filename, "line": lineno,
                                     "col": source_column + 1,
                                     "rule": "long-sentence", "level": "hard",
                                     "match": f"{n} words",
                                     "message": f"Rule 1: {kind} has {n} words (limit {cap}). Split it."})
    for gi, group in enumerate(SYNONYM_GROUPS):
        present = sorted((seen[(gi, b)], b) for b in group if (gi, b) in seen)
        if len(present) > 1:
            first_base = present[0][1]
            for (lineno, col, match), base in present[1:]:
                findings.append({"file": filename, "line": lineno, "col": col,
                                 "rule": "synonym-rotation", "level": "advisory",
                                 "match": match,
                                 "message": f"Rule 5: '{base}' and '{first_base}' may name one concept. Pick one word and use it every time."})
    if not after_only:
        findings.extend(_dangling_conjunction_findings(lines, filename))
    findings.sort(key=lambda f: (f["line"], f["col"]))
    return findings, words_total


def report(findings, words_total, as_json, hard_count, baseline):
    rate = round(len(findings) * 100 / words_total, 1) if words_total else 0.0
    if as_json:
        print(json.dumps({"findings": findings, "count": len(findings),
                          "hard_count": hard_count, "baseline": baseline,
                          "words": words_total, "per_100_words": rate}, indent=2))
        return
    for f in findings:
        print(f"{f['file']}:{f['line']}:{f['col']} [{f['level']}] {f['rule']}: {f['message']} [{f['match']}]")
    print(f"\n{len(findings)} findings ({hard_count} hard, baseline {baseline}), "
          f"{words_total} words, {rate} per 100 words")
    print("Form checks only. This linter cannot verify that the meaning is preserved.")


def selftest():
    def rules_of(text, **kw):
        return {f["rule"] for f in lint(text, **kw)[0]}

    bad = ("The panel is removed; spin up the job. "
           "Perform an analysis of the seamless log. We have received the report.")
    for expected in ("semicolon", "phrasal-verb", "nominalization",
                     "marketing-adjective", "passive-voice", "present-perfect"):
        assert expected in rules_of(bad), expected

    # Hedges and modal perfects are never flagged.
    assert lint("The request may have failed. It could be a timeout. "
                "The disk might have filled.")[0] == []
    for modal in ("may", "might", "could", "should", "would", "must"):
        for gap in (" ", "  ", "\t", " not "):
            assert "present-perfect" not in rules_of(f"The task {modal}{gap}have run.")
    assert "present-perfect" not in rules_of("The task couldn't have run. The task MAY NOT HAVE RUN.")
    assert "present-perfect" in rules_of("The task has run.")

    # Sentence caps: 20 for an instruction, 25 for any other sentence.
    twenty_one = " ".join(["word"] * 21) + "."
    assert "long-sentence" in rules_of("Open " + twenty_one)
    assert "long-sentence" not in rules_of("The " + " ".join(["word"] * 21) + ".")
    assert "long-sentence" in rules_of("The " + " ".join(["word"] * 25) + ".")
    assert "long-sentence" not in rules_of("1. Open the page. 2. Click **Add Source**. 3. Select **CSV**.")

    # Noun stacks: four nouns flag, three do not, prepositions break a run.
    assert "noun-stack" in rules_of("Check the customer order status update settings.")
    assert "noun-stack" not in rules_of("Check the status update settings.")
    assert "noun-stack" not in rules_of("Check the settings for updates to order status.")
    assert "noun-stack" not in rules_of("Check the `customer_order_status_update` settings.")

    # Phrasal verbs, idioms, plain words.
    assert "phrasal-verb" in rules_of("Set up the connector and figure out the error.")
    assert "idiom" in rules_of("Caching will move the needle.")
    assert "plain-word" in rules_of("Utilize the filter prior to export.")

    # Synonym rotation is advisory and names the keeper.
    found = [f for f in lint("Check the config. Then verify the output.")[0]
             if f["rule"] == "synonym-rotation"]
    assert len(found) == 1 and "'verify' and 'check'" in found[0]["message"]
    assert "synonym-rotation" not in rules_of("Check the config. Check the output.")

    # Code fences and inline code are skipped.
    assert lint("```\nx = a; y = b\n```")[0] == []
    assert lint("Run `a; b` now.")[0] == []

    # Dangling conjunctions in list items.
    dangling = [f for f in lint("- Confirm the target and\n* Record the result OR  \n- Close the panel")[0]
                if f["rule"] == "dangling-conjunction"]
    assert [f["line"] for f in dangling] == [1, 2], dangling
    assert "dangling-conjunction" not in rules_of("- Combine `left` and `right`")

    # Tables: pipes are layout, cells are prose.
    cell = " ".join(f"term{n}" for n in range(1, 24)) + "."
    table = f"| Label | Detail |\n| --- | --- |\n| Clear | {cell} |"
    assert "long-sentence" not in rules_of(table)

    # --after-only lints only the After lines.
    sample = "- Before: Utilize it; now.\n- After: Use it now.\n"
    assert lint(sample, after_only=True)[0] == []
    assert "semicolon" in rules_of(sample)

    # Advisory findings never fail the run.
    findings, _ = lint("The file is deleted by the job.")
    assert findings and all(f["level"] == "advisory" for f in findings)
    print("selftest OK")


def main(argv):
    if "--selftest" in argv:
        selftest()
        return 0
    as_json = "--json" in argv
    after_only = "--after-only" in argv
    baseline, disabled, paths, i = 0, set(), [], 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--baseline":
            i += 1
            baseline = int(argv[i])
        elif arg == "--disable":
            i += 1
            disabled = set(argv[i].split(","))
        elif not arg.startswith("--"):
            paths.append(arg)
        i += 1
    findings, words_total = [], 0
    if paths:
        for path in paths:
            with open(path, encoding="utf-8") as handle:
                f, w = lint(handle.read(), filename=path, after_only=after_only)
            findings.extend(f)
            words_total += w
    else:
        findings, words_total = lint(sys.stdin.read(), after_only=after_only)
    findings = [f for f in findings if f["rule"] not in disabled]
    hard_count = sum(1 for f in findings if f["level"] == "hard")
    report(findings, words_total, as_json, hard_count, baseline)
    return 1 if hard_count > baseline else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
