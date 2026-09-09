"""Enforce the workflow rules (see rules.py) on a spec before anything is built.

validate() never fixes anything - it reports. build refuses to write a .docx
while a single rule is broken, so a wrong exam cannot reach the exams/ folder.
"""

from __future__ import annotations

import re

from . import rules
from .extract import find_section
from .spec import Spec


def _norm(s: str) -> str:
    """Compare German prompts robustly: case, spacing around '/', whitespace."""
    s = s.strip().lower()
    s = re.sub(r"\s*/\s*", " / ", s)
    return re.sub(r"\s+", " ", s)


def _word_forms(en: str) -> list:
    """Cheap English word forms, enough to spot an answer given away in the text."""
    en = en.strip().lower()
    forms = {en}
    if " " in en:                                   # "special effect"
        forms.add(en + "s")
        return sorted(forms)
    forms.update({en + "s", en + "ed", en + "ing"})
    if en.endswith("e"):
        forms.update({en + "d", en[:-1] + "ing"})
    if en.endswith("y"):
        forms.update({en[:-1] + "ies", en[:-1] + "ied"})
    return sorted(forms)


def validate(spec: Spec, vocab: dict) -> list:
    """Return a list of human-readable problems. Empty list == exam is valid."""
    problems: list[str] = []

    def bad(rule: str, msg: str) -> None:
        problems.append(f"[{rule}] {msg}")

    # --- the vocabulary section the exam draws from -------------------
    try:
        section = find_section(vocab, spec.vocab_section)
    except ValueError as exc:
        bad("R4", str(exc))
        return problems

    by_de = {_norm(e["de"]): e for e in section["entries"]}
    if len(by_de) != len(section["entries"]):
        bad("R4", f"section {section['name']!r} contains duplicate German entries")

    gaps_de = spec.gap_answers_de
    used = list(spec.translate) + gaps_de

    # --- R1/R2/R3: composition ---------------------------------------
    if len(used) != rules.TOTAL_WORDS:
        bad("R1", f"{len(used)} words tested, must be exactly {rules.TOTAL_WORDS}")
    if len(spec.translate) != rules.TRANSLATE_WORDS:
        bad("R2", f"exercise 1 has {len(spec.translate)} rows, "
                  f"must be exactly {rules.TRANSLATE_WORDS}")
    if len(gaps_de) != rules.GAPFILL_WORDS:
        bad("R3", f"exercise 2 has {len(gaps_de)} gaps, "
                  f"must be exactly {rules.GAPFILL_WORDS}")

    # --- R4: every word comes from the list --------------------------
    for word in used:
        if _norm(word) not in by_de:
            bad("R4", f"{word!r} is not in section {section['name']!r} "
                      f"of {vocab['source']}")

    # --- R5: no word twice -------------------------------------------
    seen: dict = {}
    for word in used:
        key = _norm(word)
        if key in seen:
            bad("R5", f"{word!r} is tested twice")
        seen[key] = True
    seen_en: dict = {}
    for word in used:
        entry = by_de.get(_norm(word))
        if not entry:
            continue
        key = entry["en"].strip().lower()
        if key in seen_en:
            bad("R5", f"{word!r} and {seen_en[key]!r} share the English "
                      f"answer {entry['en']!r}")
        seen_en[key] = word

    # --- R6: the Words: line matches the gaps ------------------------
    if sorted(_norm(w) for w in spec.gap_words) != sorted(_norm(w) for w in gaps_de):
        bad("R6", "the 'Words:' line does not match the gaps "
                  f"(line: {spec.gap_words}, gaps: {gaps_de})")

    # --- R7/R8: the gap text ------------------------------------------
    plain = spec.rendered_text(" ")
    for word in gaps_de:
        entry = by_de.get(_norm(word))
        if not entry:
            continue
        for form in _word_forms(entry["en"]):
            if re.search(rf"\b{re.escape(form)}\b", plain, re.IGNORECASE):
                bad("R7", f"the text gives {entry['en']!r} away "
                          f"(contains {form!r} outside the gap)")
                break
        if re.search(re.escape(word.split("/")[0].strip()), plain, re.IGNORECASE):
            bad("R7", f"the German prompt {word!r} appears in the English text")

    if rules.GAP_OPEN.rstrip(":") in plain or "{{" in plain or "}}" in plain:
        bad("R8", "the gap text contains a malformed {{gap:...}} placeholder")
    if not spec.gap_text.strip().endswith((".", "!", "?")):
        bad("R8", "the gap text must end with a full stop")
    if len(plain.split()) < 30:
        bad("R8", "the gap text is too short to give the words a real context "
                  "(at least 30 words)")

    answers = {}
    for word in gaps_de:
        entry = by_de.get(_norm(word))
        answers[word] = entry["en"] if entry else "?"
    if answers and all(v != "?" for v in answers.values()):
        filled = spec.filled_text(answers)
        for word, en in answers.items():
            if filled.count(en) != 1:
                bad("R8", f"the answer {en!r} would appear "
                          f"{filled.count(en)}x in the filled text")
        if re.search(r"\s{2,}", filled):
            bad("R8", "the filled text contains double spaces around a gap")
        if re.search(r"\ba (?=[aeiou])", filled):
            bad("R8", "an inserted answer breaks the a/an article in the text")

    # --- R9/R10: header, points, output -------------------------------
    if not spec.title.strip():
        bad("R9", "title must not be empty")
    if not spec.source_label.strip():
        bad("R9", "source_label must not be empty (used in both instructions)")
    if not spec.output.endswith(".docx"):
        bad("R10", f"output {spec.output!r} must be a .docx file")

    return problems
