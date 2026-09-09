"""Tests for the vocabtest workflow. Run with: python3 -m unittest discover tests"""

import copy
import json
import os
import sys
import tempfile
import unittest
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

from vocabtest import rules, spec as spec_mod                      # noqa: E402
from vocabtest.build import TEMPLATE, build                        # noqa: E402
from vocabtest.docx_io import read_text                            # noqa: E402
from vocabtest.extract import extract, find_section                # noqa: E402
from vocabtest.validate import validate                            # noqa: E402

VOCAB_DOCX = os.path.join(REPO, "vocab", "Vocabulary_Unit_8_updated.docx")
SPEC_JSON = os.path.join(REPO, "specs", "unit8_part2.json")


def load_spec(overrides=None):
    with open(SPEC_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    if overrides:
        data = copy.deepcopy(data)
        for key, value in overrides.items():
            if "." in key:
                outer, inner = key.split(".", 1)
                data[outer][inner] = value
            else:
                data[key] = value
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
        path = fh.name
    return spec_mod.load(path)


class TestExtract(unittest.TestCase):
    def test_sections_and_entries(self):
        vocab = extract(VOCAB_DOCX)
        names = [s["name"] for s in vocab["sections"]]
        self.assertEqual(names, ["Test 1", "Test 2 (updated)"])
        self.assertEqual(len(vocab["sections"][0]["entries"]), 29)
        self.assertEqual(len(vocab["sections"][1]["entries"]), 30)

    def test_find_section_accepts_partial_names(self):
        vocab = extract(VOCAB_DOCX)
        for key in ("Test 2", "test-2-updated", "2", "Test 2 (updated)"):
            self.assertEqual(find_section(vocab, key)["name"], "Test 2 (updated)")
        self.assertEqual(find_section(vocab, None)["name"], "Test 2 (updated)")

    def test_unknown_section_raises(self):
        with self.assertRaises(ValueError):
            find_section(extract(VOCAB_DOCX), "Test 9")


class TestValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocab = extract(VOCAB_DOCX)

    def codes(self, overrides):
        problems = validate(load_spec(overrides), self.vocab)
        return {p.split("]")[0].strip("[") for p in problems}

    def test_reference_spec_is_valid(self):
        self.assertEqual(validate(load_spec(), self.vocab), [])

    def test_too_few_words(self):
        short = load_spec().translate[:-1]
        self.assertLessEqual({"R1", "R2"}, self.codes({"translate": short}))

    def test_word_used_twice(self):
        dup = load_spec().translate[:]
        dup[-1] = dup[0]
        self.assertIn("R5", self.codes({"translate": dup}))

    def test_word_not_in_the_list(self):
        bogus = load_spec().translate[:]
        bogus[0] = "Kühlschrank"
        self.assertIn("R4", self.codes({"translate": bogus}))

    def test_word_from_the_other_section(self):
        bogus = load_spec().translate[:]
        bogus[0] = "Abenteuer"          # Test 1, not Test 2
        self.assertIn("R4", self.codes({"translate": bogus}))

    def test_gap_word_also_in_the_translation_table(self):
        both = load_spec().translate[:]
        both[0] = "vermeiden"
        self.assertIn("R5", self.codes({"translate": both}))

    def test_words_line_does_not_match_the_gaps(self):
        self.assertIn("R6", self.codes(
            {"gapfill.words": ["Folge", "vermeiden", "verfügbar", "Filmmusik"]}))

    def test_text_gives_the_answer_away(self):
        text = load_spec().gap_text.replace(
            "on Netflix", "on Netflix, so the soundtrack is easy to find")
        self.assertIn("R7", self.codes({"gapfill.text": text}))

    def test_text_contains_the_german_prompt(self):
        text = load_spec().gap_text.replace("every spoiler", "vermeiden spoiler")
        self.assertIn("R7", self.codes({"gapfill.text": text}))

    def test_text_too_short(self):
        short = ("A film {{gap:veröffentlichen / herausbringen}} {{gap:vermeiden}} "
                 "{{gap:Filmmusik}} {{gap:verfügbar}}.")
        self.assertIn("R8", self.codes({"gapfill.text": short}))

    def test_wrong_number_of_gaps(self):
        text = load_spec().gap_text.replace("{{gap:verfügbar}}", "available")
        self.assertLessEqual({"R1", "R3"}, self.codes({"gapfill.text": text}))


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocab = extract(VOCAB_DOCX)
        cls.spec = load_spec()
        cls.tmp = tempfile.mkdtemp()
        cls.out = build(cls.spec, cls.vocab, os.path.join(cls.tmp, "exam.docx"))
        cls.text = read_text(cls.out)

    def test_layout_parts_come_from_the_template(self):
        """Everything except the content is byte-identical to the reference."""
        with zipfile.ZipFile(TEMPLATE) as tpl, zipfile.ZipFile(self.out) as out:
            self.assertEqual(tpl.namelist(), out.namelist())
            for name in tpl.namelist():
                if name == "word/document.xml":
                    continue
                self.assertEqual(tpl.read(name), out.read(name), name)

    def test_header_and_instructions(self):
        self.assertIn("Unit 8", self.text)
        self.assertIn("Part II", self.text)
        self.assertIn("Name:", self.text)
        self.assertIn("Grade :", self.text)
        self.assertIn("1) Translate using the vocabulary from unit 8 part II.",
                      self.text)
        self.assertIn("2)  Fill in the gaps using the vocabulary from unit 8 part II.",
                      self.text)

    def test_points_match_the_word_counts(self):
        self.assertIn("8P", self.text)
        self.assertIn("4P", self.text)

    def test_all_twelve_words_are_asked_once(self):
        for word in self.spec.translate + self.spec.gap_words:
            self.assertEqual(self.text.count(word), 1, word)

    def test_gaps_have_the_reference_width(self):
        gap = "_" * rules.GAP_UNDERSCORES
        self.assertEqual(self.text.count(gap), rules.GAPFILL_WORDS)
        self.assertNotIn(gap + "_", self.text)

    def test_no_answer_is_printed(self):
        section = find_section(self.vocab, self.spec.vocab_section)
        answers = {e["de"]: e["en"] for e in section["entries"]}
        for word in self.spec.translate + self.spec.gap_answers_de:
            self.assertNotIn(f" {answers[word]} ", f" {self.text} ")

    def test_build_refuses_an_invalid_spec(self):
        broken = load_spec({"translate": load_spec().translate[:-1]})
        with self.assertRaises(ValueError):
            build(broken, self.vocab, os.path.join(self.tmp, "nope.docx"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "nope.docx")))


if __name__ == "__main__":
    unittest.main()
