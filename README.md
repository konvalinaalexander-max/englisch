# Englisch – Voci-Liste → Prüfung

Aus einer Voci-Liste (`.docx`) wird eine Prüfung (`.docx`) im **exakt gleichen
Layout** wie `reference/Unit_8_Part_I_Niv._A_2.docx`.

Du musst das Tool nicht bedienen. Du lädst die Voci-Liste im Chat hoch, Claude
macht den Rest. Das Tool existiert, damit dabei jedes Mal derselbe Ablauf und
dieselben Regeln eingehalten werden.

## Aufbau einer Prüfung

| Teil | Inhalt | Punkte |
|------|--------|--------|
| Kopf | schwarzer Balken: Titel, `Unit X Part Y`, darunter `Name:` / `Grade :` | – |
| 1)   | Übersetzungstabelle, 8 deutsche Wörter, rechte Spalte leer | 8P |
| 2)   | Lückentext, 4 Wörter, `Words:`-Zeile mit den deutschen Vorgaben | 4P |

Insgesamt **12 Wörter**, jedes genau einmal.

## Ordner

```
vocab/       hochgeladene Voci-Listen
specs/       je Prüfung eine JSON-Datei: Wortauswahl + Lückentext
exams/       die fertigen Prüfungen (.docx)
reference/   die Original-Prüfung, an der sich alles ausrichtet
tools/       das Tool (nur Python-Standardbibliothek)
tests/       Tests für Tool und Regeln
```

## Tool

```bash
cd tools
python3 -m vocabtest rules                              # die Regeln anzeigen
python3 -m vocabtest sections ../vocab/liste.docx       # welche Tests enthält die Liste?
python3 -m vocabtest extract  ../vocab/liste.docx       # Liste als JSON
python3 -m vocabtest scaffold ../vocab/liste.docx --section "Test 2" -o ../specs/neu.json
python3 -m vocabtest validate ../specs/neu.json         # nur prüfen
python3 -m vocabtest build    ../specs/neu.json         # prüfen + Prüfung schreiben
python3 -m vocabtest check                              # alle Specs in specs/ prüfen
```

`build` schreibt nichts, solange eine Regel verletzt ist.

## Regeln

| | |
|---|---|
| R1 | genau 12 abgefragte Wörter |
| R2 | Aufgabe 1: genau 8 Zeilen |
| R3 | Aufgabe 2: genau 4 Lücken |
| R4 | jedes Wort steht im gewählten Abschnitt der Voci-Liste |
| R5 | kein Wort zweimal (weder deutsch noch englisch) |
| R6 | die `Words:`-Zeile enthält genau die Wörter der Lücken |
| R7 | keine Lücke verrät ihre eigene Antwort im Text |
| R8 | jeder Satz passt zur Wortform aus der Liste |
| R9 | Punkte ergeben sich aus der Anzahl Wörter (8P / 4P) |
| R10 | Layout kommt unverändert aus der Vorlage |
| R11 | die fertige `.docx` wird zurückgelesen und geprüft |

## Spec-Format

```json
{
  "title": " Vocabulary",
  "unit_large": "Unit 8 ",
  "unit_small": "Part II",
  "source_label": "vocabulary from unit 8 part II",
  "vocab_file": "vocab/Vocabulary_Unit_8_updated.docx",
  "vocab_section": "Test 2 (updated)",
  "translate": ["Regie führen", "..."],
  "gapfill": {
    "words": ["Filmmusik", "..."],
    "text": "... decided to {{gap:veröffentlichen / herausbringen}} a new film ..."
  },
  "output": "exams/Unit_8_Part_II_Niv._A_2.docx"
}
```

Die Lücken werden mit `{{gap:<deutsche Vorgabe>}}` markiert; im Dokument stehen
dort 26 Unterstriche, genau wie in der Original-Prüfung.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Voraussetzungen

Python 3.9+, sonst nichts. Für die optionale Sichtkontrolle als Bild:
`libreoffice-writer` und `poppler-utils`.
