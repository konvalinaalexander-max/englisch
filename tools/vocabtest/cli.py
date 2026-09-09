"""Command line interface.

    python3 -m vocabtest sections  vocab/list.docx
    python3 -m vocabtest extract   vocab/list.docx [-o vocab/list.json]
    python3 -m vocabtest scaffold  vocab/list.docx --section "Test 2" -o specs/x.json
    python3 -m vocabtest validate  specs/x.json
    python3 -m vocabtest build     specs/x.json [-o exams/y.docx]
    python3 -m vocabtest check     [specs/]
    python3 -m vocabtest rules
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from . import rules as R
from .build import build
from .extract import extract, find_section
from .spec import dump, load
from .validate import validate

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _resolve(path: str) -> str:
    """Allow spec paths to be relative to the repository root."""
    if os.path.isabs(path) or os.path.exists(path):
        return path
    candidate = os.path.join(REPO, path)
    return candidate if os.path.exists(candidate) else path


def _vocab_for(spec) -> dict:
    return extract(_resolve(spec.vocab_file))


def cmd_sections(args) -> int:
    vocab = extract(args.vocab)
    for i, s in enumerate(vocab["sections"], 1):
        print(f"{i}. {s['name']}  ({len(s['entries'])} words, slug: {s['slug']})")
    return 0


def cmd_extract(args) -> int:
    vocab = extract(args.vocab)
    text = json.dumps(vocab, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.output}")
    else:
        print(text)
    return 0


def cmd_scaffold(args) -> int:
    vocab = extract(args.vocab)
    section = find_section(vocab, args.section)
    entries = section["entries"]
    if len(entries) < R.TOTAL_WORDS:
        print(f"error: section {section['name']!r} has only {len(entries)} words, "
              f"{R.TOTAL_WORDS} are needed", file=sys.stderr)
        return 2

    picked = [e["de"] for e in entries[:R.TOTAL_WORDS]]
    translate = picked[:R.TRANSLATE_WORDS]
    gaps = picked[R.TRANSLATE_WORDS:]
    text = " ".join(
        f"TODO sentence {i + 1} using {{{{gap:{w}}}}} in a fitting context."
        for i, w in enumerate(gaps)
    )
    skeleton = {
        "_comment": "TODO: pick the words yourself and write real sentences; "
                    "then run: python3 -m vocabtest build <this file>",
        "title": args.title,
        "unit_large": args.unit_large,
        "unit_small": args.unit_small,
        "source_label": args.source_label,
        "vocab_file": os.path.relpath(os.path.abspath(args.vocab), REPO),
        "vocab_section": section["name"],
        "translate": translate,
        "gapfill": {"words": gaps, "text": text},
        "output": args.exam_output,
    }
    dump(skeleton, args.output)
    print(f"wrote {args.output} (skeleton - the words and sentences are still TODO)")
    return 0


def _report(spec, problems) -> int:
    if problems:
        print(f"{spec.path}: INVALID")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"{spec.path}: valid "
          f"({len(spec.translate)} translation rows + {len(spec.gap_answers_de)} gaps "
          f"= {len(spec.translate) + len(spec.gap_answers_de)} words)")
    return 0


def cmd_validate(args) -> int:
    spec = load(_resolve(args.spec))
    return _report(spec, validate(spec, _vocab_for(spec)))


def cmd_build(args) -> int:
    spec = load(_resolve(args.spec))
    vocab = _vocab_for(spec)
    problems = validate(spec, vocab)
    if problems:
        return _report(spec, problems)
    out = args.output or os.path.join(REPO, spec.output)
    path = build(spec, vocab, out)
    print(f"built {path}")
    return 0


def cmd_check(args) -> int:
    target = args.path or os.path.join(REPO, "specs")
    specs = sorted(glob.glob(os.path.join(target, "*.json"))) \
        if os.path.isdir(target) else [target]
    if not specs:
        print(f"no specs found in {target}")
        return 0
    failed = 0
    for path in specs:
        spec = load(path)
        failed |= _report(spec, validate(spec, _vocab_for(spec)))
    return failed


def cmd_rules(args) -> int:
    print("Workflow rules enforced by vocabtest:\n")
    for code, text in R.RULES:
        print(f"  {code:<4} {text}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="vocabtest",
        description="Turn a vocabulary list (.docx) into an exam (.docx) "
                    "in the exact layout of the reference exam.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sections", help="list the test sections of a vocabulary list")
    p.add_argument("vocab")
    p.set_defaults(func=cmd_sections)

    p = sub.add_parser("extract", help="dump a vocabulary list as JSON")
    p.add_argument("vocab")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("scaffold", help="write an empty spec for a section")
    p.add_argument("vocab")
    p.add_argument("--section", default="last")
    p.add_argument("--title", default="Vocabulary")
    p.add_argument("--unit-large", dest="unit_large", default="Unit 8 ")
    p.add_argument("--unit-small", dest="unit_small", default="Part II")
    p.add_argument("--source-label", dest="source_label",
                   default="vocabulary from unit 8 part II")
    p.add_argument("--exam-output", dest="exam_output",
                   default="exams/exam.docx")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_scaffold)

    p = sub.add_parser("validate", help="check a spec against the workflow rules")
    p.add_argument("spec")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("build", help="validate and write the exam .docx")
    p.add_argument("spec")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("check", help="validate every spec in specs/")
    p.add_argument("path", nargs="?")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("rules", help="print the workflow rules")
    p.set_defaults(func=cmd_rules)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, AssertionError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
