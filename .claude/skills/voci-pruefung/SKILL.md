---
name: voci-pruefung
description: Turn an uploaded vocabulary list (.docx) into a school exam (.docx) in the exact layout of reference/Unit_8_Part_I_Niv._A_2.docx. Use whenever the user uploads or points at a vocabulary list (Voci-Liste, Wortschatzliste, "Vocabulary Unit ...") and wants a test, Prüfung, Test, Vokabeltest or exam made from it.
---

# Voci-Liste → Prüfung

The user uploads a vocabulary list in the chat. You produce a Word exam that
looks exactly like `reference/Unit_8_Part_I_Niv._A_2.docx`. The user never runs
the tool - you do, and the tool is what guarantees the result is right.

## Workflow (do not skip a step)

1. **Save the upload** to `vocab/<name>.docx` in the repository.

2. **List the sections** so you know what you may draw from:

   ```bash
   cd tools && python3 -m vocabtest sections ../vocab/<name>.docx
   ```

   If the user did not say which test/section to use, use the last one and say so.

3. **Choose the 12 words yourself** - 8 for the translation table, 4 for the
   gap-fill text. Pick a mix like the reference exam does: mostly nouns, plus
   at least one verb and one adjective. Every word appears exactly once in the
   whole exam.

4. **Write the gap-fill text yourself**: one short, coherent English story of
   4 sentences that fits the topic of the vocabulary list. Each of the 4 words
   fits its sentence in exactly the form the list gives it (`release`, not
   `released`). Nothing in the text may give an answer away.

5. **Write the spec** to `specs/<unit>.json` (see `specs/unit8_part2.json`).
   Mark the gaps with `{{gap:<German prompt>}}`; the German prompt must match
   the list exactly. The `words` array is the (shuffled) `Words:` line.

6. **Build**:

   ```bash
   cd tools && python3 -m vocabtest build ../specs/<unit>.json
   ```

   The build validates first and refuses to write anything while a rule is
   broken. Fix the spec, never the tool, until it builds.

7. **Check the result visually** before handing it over:

   ```bash
   soffice --headless --convert-to pdf --outdir /tmp exams/<exam>.docx
   pdftoppm -r 110 -png /tmp/<exam>.pdf /tmp/exam && # then read /tmp/exam-1.png
   ```

8. **Run the tests**, commit spec + exam + vocabulary list, push:

   ```bash
   python3 -m unittest discover -s tests
   ```

9. **Give the user the .docx in the chat** (SendUserFile) and list the 12 words
   with their answers, so the exam can be corrected without opening anything.

## Rules the exam must satisfy

`cd tools && python3 -m vocabtest rules` prints them; the validator enforces
them. 12 words, 8 + 4, no word twice, all from the chosen section, the `Words:`
line matches the gaps, no answer given away, points derived from the counts,
and the layout taken from the template package unchanged.

## Header fields

| field         | reference exam            | what to put there                    |
|---------------|---------------------------|--------------------------------------|
| `title`       | ` Vocabulary`             | leading space kept; add `+ <grammar>` only if the exam really tests that grammar |
| `unit_large`  | `Unit 8 `                 | big text in the black bar            |
| `unit_small`  | `Part II`                 | small text after it                  |
| `source_label`| `vocabulary from unit 8 part II` | goes into both instruction lines |

Test 1 of a list is Part I, Test 2 is Part II, and so on.
