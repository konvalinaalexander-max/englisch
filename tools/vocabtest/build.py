"""Build the exam .docx.

The WordprocessingML below is a 1:1 copy of the reference exam
(reference/Unit_8_Part_I_Niv._A_2.docx) with the content turned into slots:
same table grid, same cell widths, same fonts, same tab stops, same spacing.
Only word/document.xml is generated - styles, theme, fonts and page setup are
taken from the template package unchanged, so the result cannot drift visually.
"""

from __future__ import annotations

import os

from . import rules
from .docx_io import template_namespaces, write_from_template, xml_escape, read_text
from .extract import find_section
from .spec import Spec
from .validate import _norm, validate

TEMPLATE = os.path.join(os.path.dirname(__file__), "template", "exam_template.docx")

# --- run property blocks used by the reference exam --------------------
RPR_HEAD = ('<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>'
            '<w:sz w:val="30"/><w:szCs w:val="30"/>')
RPR_TASK = ('<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:b/><w:bCs/>'
            '<w:lang w:val="fr-CH"/>')
RPR_TASK2 = '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:b/><w:bCs/>'
RPR_BODY = '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>'
RPR_WORDS_LABEL = ('<w:rStyle w:val="Fett"/><w:rFonts w:ascii="Aptos" '
                   'w:eastAsiaTheme="majorEastAsia" w:hAnsi="Aptos"/>')
RPR_WORDS_LIST = ('<w:rFonts w:ascii="Aptos" w:eastAsiaTheme="majorEastAsia" '
                  'w:hAnsi="Aptos"/><w:i/><w:iCs/>')

TBL_LOOK = ('<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
            'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>')
BLACK = '<w:shd w:val="clear" w:color="auto" w:fill="000000" w:themeFill="text1"/>'


def _run(text: str, rpr: str = "", tabs: int = 0) -> str:
    body = "<w:tab/>" * tabs
    if text:
        body += f'<w:t xml:space="preserve">{xml_escape(text)}</w:t>'
    rpr_xml = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f"<w:r>{rpr_xml}{body}</w:r>"


def _para(runs: str = "", ppr: str = "", rpr: str = "") -> str:
    inner = ppr + (f"<w:rPr>{rpr}</w:rPr>" if rpr else "")
    ppr_xml = f"<w:pPr>{inner}</w:pPr>" if inner else ""
    return f"<w:p>{ppr_xml}{runs}</w:p>"


def _header_table(spec: Spec) -> str:
    def cell(width: str, para: str, shaded: bool, span: int = 1) -> str:
        span_xml = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
        shd = BLACK if shaded else ""
        return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="pct"/>'
                f"{span_xml}{shd}</w:tcPr>{para}</w:tc>")

    title = _para(_run(spec.title, RPR_HEAD), rpr=RPR_HEAD)
    # the reference exam sets the unit number big and the part label at
    # default size - kept exactly like that.
    unit = _para(_run(spec.unit_large, RPR_HEAD) + _run(spec.unit_small),
                 rpr=RPR_HEAD)
    empty = _para(rpr=RPR_HEAD)
    name = _para(_run("Name:", RPR_HEAD), rpr=RPR_HEAD)
    grade = _para(_run("Grade :", RPR_HEAD), rpr=RPR_HEAD) + _para(rpr=RPR_HEAD)

    return (
        "<w:tbl>"
        '<w:tblPr><w:tblStyle w:val="Tabellenraster"/>'
        f'<w:tblW w:w="5000" w:type="pct"/>{TBL_LOOK}</w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="4673"/><w:gridCol w:w="3853"/>'
        '<w:gridCol w:w="536"/></w:tblGrid>'
        "<w:tr>"
        + cell("2578", title, True)
        + cell("2126", unit, True)
        + cell("295", empty, True)
        + "</w:tr><w:tr>"
        + cell("2578", name, False)
        + cell("2422", grade, False, span=2)
        + "</w:tr></w:tbl>"
    )


def _translate_table(prompts: list) -> str:
    rows = []
    for prompt in prompts:
        left = _para(_run(prompt), rpr=RPR_TASK)
        right = _para(rpr=RPR_TASK)
        rows.append(
            f'<w:tr><w:trPr><w:trHeight w:val="{rules.TABLE_ROW_HEIGHT}"/></w:trPr>'
            '<w:tc><w:tcPr><w:tcW w:w="2405" w:type="dxa"/>'
            f'<w:vAlign w:val="center"/></w:tcPr>{left}</w:tc>'
            '<w:tc><w:tcPr><w:tcW w:w="6662" w:type="dxa"/></w:tcPr>'
            f"{right}</w:tc></w:tr>"
        )
    return (
        "<w:tbl>"
        '<w:tblPr><w:tblStyle w:val="Tabellenraster"/>'
        f'<w:tblW w:w="9067" w:type="dxa"/>{TBL_LOOK}</w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="2405"/><w:gridCol w:w="6662"/></w:tblGrid>'
        + "".join(rows) + "</w:tbl>"
    )


def build_document_xml(spec: Spec) -> str:
    open_tag = template_namespaces(TEMPLATE)

    ex1_text = rules.EX1_INSTRUCTION.format(source_label=spec.source_label)
    ex2_text = rules.EX2_INSTRUCTION.format(source_label=spec.source_label)
    ex1_points = f"{len(spec.translate)}{rules.POINT_SUFFIX}"
    ex2_points = f"{len(spec.gap_answers_de)}{rules.POINT_SUFFIX} "

    ex1_heading = _para(
        _run(ex1_text, RPR_TASK)
        + _run("", RPR_TASK, tabs=4)
        + _run(ex1_points, RPR_TASK, tabs=1),
        ppr='<w:spacing w:before="240"/>', rpr=RPR_TASK,
    )

    spacing2 = '<w:spacing w:before="240" w:after="0" w:line="240" w:lineRule="auto"/>'
    ex2_heading = _para(
        _run(ex2_text, RPR_TASK2)
        + _run("", RPR_TASK2, tabs=3)
        + _run(ex2_points, RPR_TASK2, tabs=1),
        ppr=spacing2, rpr=RPR_TASK2,
    )

    words = _para(
        _run(rules.EX2_WORDS_LABEL, RPR_WORDS_LABEL)
        + _run("  ", RPR_WORDS_LIST)
        + _run(", ".join(spec.gap_words), RPR_WORDS_LIST),
        ppr=spacing2,
        rpr='<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:b/><w:bCs/><w:i/><w:iCs/>',
    )

    gap_para = _para(
        _run(spec.rendered_text("_" * rules.GAP_UNDERSCORES), RPR_BODY),
        ppr='<w:pStyle w:val="StandardWeb"/>'
            '<w:spacing w:line="360" w:lineRule="auto"/>',
        rpr=RPR_BODY,
    )

    blank_task = _para(ppr=spacing2, rpr=RPR_TASK2)
    tail = (_para(rpr=RPR_TASK2) * 2
            + _para(ppr='<w:pStyle w:val="StandardWeb"/>'
                        '<w:spacing w:line="360" w:lineRule="auto"/>',
                    rpr=RPR_HEAD) * 2)

    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1417" w:right="1417" w:bottom="635" w:left="1417" '
            'w:header="708" w:footer="708" w:gutter="0"/>'
            '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        + open_tag + "<w:body>"
        + _header_table(spec)
        + ex1_heading
        + _translate_table(spec.translate)
        + blank_task
        + ex2_heading
        + words
        + gap_para
        + tail
        + sect
        + "</w:body></w:document>"
    )


def build(spec: Spec, vocab: dict, out_path: str | None = None) -> str:
    """Validate, write the .docx, then read it back and check it (R11)."""
    problems = validate(spec, vocab)
    if problems:
        raise ValueError("spec violates the workflow rules:\n  "
                         + "\n  ".join(problems))

    out_path = out_path or spec.output
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    write_from_template(TEMPLATE, out_path, build_document_xml(spec))
    _self_check(spec, vocab, out_path)
    return out_path


def _self_check(spec: Spec, vocab: dict, out_path: str) -> None:
    text = read_text(out_path)
    missing = [w for w in spec.translate if w not in text]
    if missing:
        raise AssertionError(f"{out_path}: translation rows missing: {missing}")
    for word in spec.gap_words:
        if word not in text:
            raise AssertionError(f"{out_path}: {word!r} missing from the Words line")
    gap = "_" * rules.GAP_UNDERSCORES
    if text.count(gap) != len(spec.gap_answers_de):
        raise AssertionError(f"{out_path}: expected {len(spec.gap_answers_de)} gaps, "
                             f"found {text.count(gap)}")
    section = find_section(vocab, spec.vocab_section)
    by_de = {_norm(e["de"]): e["en"] for e in section["entries"]}
    for word in spec.translate + spec.gap_answers_de:
        answer = by_de.get(_norm(word), "")
        if answer and f" {answer} " in f" {text} ":
            raise AssertionError(f"{out_path}: the answer {answer!r} is printed "
                                 "in the exam")
