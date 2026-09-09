"""The workflow rules. Every generated exam has to satisfy all of them.

These constants are deliberately kept in one place: they *are* the
specification of the exam format, and validate.py checks nothing else.
"""

# --- exam composition -------------------------------------------------
TOTAL_WORDS = 12          # words tested in total
TRANSLATE_WORDS = 8       # exercise 1: German -> English translation table
GAPFILL_WORDS = 4         # exercise 2: gap-fill text

# --- layout constants copied from the reference exam ------------------
GAP_UNDERSCORES = 26      # width of one gap in exercise 2
TABLE_ROW_HEIGHT = 680    # twips, exercise 1 table rows
POINT_SUFFIX = "P"        # "8P" / "4P"

# --- exercise wording (reference exam, with the unit label as a slot) --
EX1_INSTRUCTION = "1) Translate using the {source_label}."
EX2_INSTRUCTION = "2)  Fill in the gaps using the {source_label}. "
EX2_WORDS_LABEL = "Words:"

# Placeholder syntax used inside a spec's gap-fill text:
#     ... decided to {{gap:veröffentlichen / herausbringen}} a new film ...
GAP_OPEN = "{{gap:"
GAP_CLOSE = "}}"

RULES = [
    ("R1", f"exactly {TOTAL_WORDS} vocabulary words are tested"),
    ("R2", f"exercise 1 has exactly {TRANSLATE_WORDS} translation rows"),
    ("R3", f"exercise 2 has exactly {GAPFILL_WORDS} gaps"),
    ("R4", "every tested word exists in the chosen section of the vocabulary list"),
    ("R5", "no word is tested twice (neither the German nor the English side)"),
    ("R6", "the 'Words:' line lists exactly the German prompts of the gaps"),
    ("R7", "no gap gives its own answer away in the surrounding text"),
    ("R8", "every gap sentence fits the word (grammatically checked against the list form)"),
    ("R9", "points are derived from the word counts (8P / 4P)"),
    ("R10", "the exam is built from the reference template, so the layout is identical"),
    ("R11", "the built .docx is read back and must match the spec exactly"),
]
