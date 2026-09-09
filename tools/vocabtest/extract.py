"""Read a vocabulary list (.docx) into structured JSON.

Expected shape of the source document (as in vocab/Vocabulary_Unit_8_updated.docx):

    Test 1                      <- section heading paragraph
    | Nr. | Deutsch | English | Example sentence |
    | 1   | ...     | ...     | ...              |
    Test 2 (updated)
    | Nr. | Deutsch | English | Example sentence |
    ...

Section headings are optional: a table without a preceding heading becomes
"Section 1", "Section 2", ...
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from .docx_io import read_blocks

HEADER_ALIASES = {
    "nr": "nr", "nr.": "nr", "no": "nr", "no.": "nr", "#": "nr",
    "deutsch": "de", "german": "de", "d": "de",
    "english": "en", "englisch": "en", "e": "en",
    "example sentence": "example", "example": "example",
    "beispielsatz": "example", "beispiel": "example",
}


@dataclass
class Entry:
    nr: int
    de: str
    en: str
    example: str


@dataclass
class Section:
    name: str
    slug: str
    entries: list


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "section"


def _header_map(row: list[str]) -> dict[int, str] | None:
    mapping = {}
    for i, cell in enumerate(row):
        key = HEADER_ALIASES.get(cell.strip().lower())
        if key:
            mapping[i] = key
    if "de" in mapping.values() and "en" in mapping.values():
        return mapping
    return None


def extract(path: str) -> dict:
    blocks = read_blocks(path)
    sections: list[Section] = []
    pending_name = None

    for block in blocks:
        if block.kind == "p":
            text = block.text.strip()
            if text:
                pending_name = text
            continue

        rows = [r for r in block.rows if any(c.strip() for c in r)]
        if not rows:
            continue
        mapping = _header_map(rows[0])
        if mapping is None:
            continue  # not a vocabulary table

        entries: list[Entry] = []
        for row in rows[1:]:
            cells = {mapping[i]: row[i].strip() for i in mapping if i < len(row)}
            de, en = cells.get("de", ""), cells.get("en", "")
            if not de or not en:
                continue
            nr_raw = cells.get("nr", "").strip()
            nr = int(nr_raw) if nr_raw.isdigit() else len(entries) + 1
            entries.append(Entry(nr=nr, de=de, en=en, example=cells.get("example", "")))

        if not entries:
            continue
        name = pending_name or f"Section {len(sections) + 1}"
        sections.append(Section(name=name, slug=slugify(name), entries=entries))
        pending_name = None

    if not sections:
        raise ValueError(f"{path}: no vocabulary table found "
                         "(need a table with 'Deutsch' and 'English' columns)")

    return {
        "source": path,
        "sections": [
            {"name": s.name, "slug": s.slug,
             "entries": [asdict(e) for e in s.entries]}
            for s in sections
        ],
    }


def find_section(vocab: dict, wanted: str | None) -> dict:
    """Pick a section by name, slug, index ('2') or 'last'. Default: last."""
    sections = vocab["sections"]
    if wanted in (None, "", "last"):
        return sections[-1]
    key = wanted.strip().lower()
    for s in sections:
        if key in (s["name"].strip().lower(), s["slug"]):
            return s
    for s in sections:                      # substring fallback: "Test 2"
        if key in s["name"].strip().lower():
            return s
    if key.isdigit() and 1 <= int(key) <= len(sections):
        return sections[int(key) - 1]
    names = ", ".join(repr(s["name"]) for s in sections)
    raise ValueError(f"section {wanted!r} not found; available: {names}")
