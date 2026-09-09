"""The exam spec: the only thing a human (or Claude) has to write by hand.

    {
      "title": "Vocabulary",
      "unit_large": "Unit 8 ",         # rendered big in the black header bar
      "unit_small": "Part II",         # rendered small, like the reference exam
      "source_label": "vocabulary from unit 8 part II",
      "vocab_file": "vocab/Vocabulary_Unit_8_updated.docx",
      "vocab_section": "Test 2 (updated)",
      "translate": ["Regie führen", ...],                  # 8 German prompts
      "gapfill": {
          "words": ["Filmmusik", ...],                     # order of the Words: line
          "text": "... decided to {{gap:veröffentlichen / herausbringen}} a film ..."
      },
      "output": "exams/Unit_8_Part_II_Niv._A_2.docx"
    }
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .rules import GAP_CLOSE, GAP_OPEN

GAP_RE = re.compile(re.escape(GAP_OPEN) + r"(.+?)" + re.escape(GAP_CLOSE))

REQUIRED = ("title", "unit_large", "unit_small", "source_label",
            "vocab_file", "vocab_section", "translate", "gapfill", "output")


@dataclass
class Spec:
    title: str
    unit_large: str
    unit_small: str
    source_label: str
    vocab_file: str
    vocab_section: str
    translate: list          # German prompts, exercise 1
    gap_words: list          # German prompts, order of the "Words:" line
    gap_text: str            # text with {{gap:...}} placeholders
    output: str
    path: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def gap_answers_de(self) -> list:
        """German prompts in the order the gaps appear in the text."""
        return [m.group(1).strip() for m in GAP_RE.finditer(self.gap_text)]

    def rendered_text(self, gap: str) -> str:
        """Gap text with every placeholder replaced by `gap`."""
        return GAP_RE.sub(lambda _m: gap, self.gap_text)

    def filled_text(self, answers: dict) -> str:
        """Gap text with the English answers inserted (used for checking)."""
        return GAP_RE.sub(lambda m: answers[m.group(1).strip()], self.gap_text)


def load(path: str) -> Spec:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise ValueError(f"{path}: missing key(s): {', '.join(missing)}")
    gap = data["gapfill"]
    for k in ("words", "text"):
        if k not in gap:
            raise ValueError(f"{path}: gapfill.{k} is missing")
    return Spec(
        title=data["title"],
        unit_large=data["unit_large"],
        unit_small=data["unit_small"],
        source_label=data["source_label"],
        vocab_file=data["vocab_file"],
        vocab_section=data["vocab_section"],
        translate=list(data["translate"]),
        gap_words=list(gap["words"]),
        gap_text=gap["text"],
        output=data["output"],
        path=path,
        raw=data,
    )


def dump(spec_dict: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec_dict, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
