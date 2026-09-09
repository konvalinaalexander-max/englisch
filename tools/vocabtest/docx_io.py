"""Minimal WordprocessingML reader/writer (stdlib only).

We only need two things:
  * read the paragraphs and tables of a .docx (vocabulary list, self-check)
  * write a .docx by swapping word/document.xml inside a template package,
    which keeps styles, fonts, theme and page setup byte-identical.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


@dataclass
class Block:
    kind: str                       # "p" or "tbl"
    text: str = ""                  # paragraph text
    rows: list = field(default_factory=list)   # table: list[list[str]]


def _para_text(p: ET.Element) -> str:
    out = []
    for node in p.iter():
        if node.tag == _q("t"):
            out.append(node.text or "")
        elif node.tag == _q("tab"):
            out.append("\t")
        elif node.tag == _q("br"):
            out.append("\n")
    return "".join(out)


def read_blocks(path: str) -> list[Block]:
    """Return the body of a .docx as an ordered list of paragraphs/tables."""
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    body = ET.fromstring(xml).find("w:body", NS)
    blocks: list[Block] = []
    for el in body:
        if el.tag == _q("p"):
            blocks.append(Block("p", text=_para_text(el)))
        elif el.tag == _q("tbl"):
            rows = []
            for tr in el.findall("w:tr", NS):
                rows.append([
                    "\n".join(_para_text(p) for p in tc.findall("w:p", NS)).strip()
                    for tc in tr.findall("w:tc", NS)
                ])
            blocks.append(Block("tbl", rows=rows))
    return blocks


def read_text(path: str) -> str:
    """Flat text of a .docx (paragraphs and table cells), for self-checks."""
    parts = []
    for b in read_blocks(path):
        if b.kind == "p":
            parts.append(b.text)
        else:
            for row in b.rows:
                parts.append(" | ".join(row))
    return "\n".join(parts)


def template_namespaces(template: str) -> str:
    """The <w:document ...> opening tag of the template, attributes included."""
    with zipfile.ZipFile(template) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    m = re.search(r"<w:document\b[^>]*>", xml)
    if not m:
        raise ValueError(f"{template}: no <w:document> element found")
    return m.group(0)


def write_from_template(template: str, out_path: str, document_xml: str) -> None:
    """Copy `template` to `out_path`, replacing word/document.xml."""
    with zipfile.ZipFile(template) as src:
        names = src.namelist()
        if "word/document.xml" not in names:
            raise ValueError(f"{template}: not a Word document")
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == "word/document.xml":
                    data = document_xml.encode("utf-8")
                dst.writestr(item, data)
    shutil.copystat(template, out_path)


def xml_escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
