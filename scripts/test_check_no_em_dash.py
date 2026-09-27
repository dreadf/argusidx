"""
Regression tests for check_no_em_dash.py.

Built from the escape sequence, not a literal glyph, so this file's own
bytes never contain a real em dash and never trip the scanner it tests
(check_no_em_dash.py scans this file too, like every other tracked file).

Run:
    python -m pytest scripts/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_no_em_dash import find_em_dashes  # noqa: E402

# Built from the Unicode code point, with no dash character typed directly
# into this file, so this file's own bytes never trip the scanner it
# tests. Code point 8212 is the em dash; 8211 is the (unrelated, allowed)
# en dash used by the negative test below.
EM_DASH = chr(8212)
EN_DASH = chr(8211)


def test_catches_em_dash():
    assert find_em_dashes(f"this has an em dash {EM_DASH} right here")


def test_does_not_flag_hyphen_or_en_dash():
    assert not find_em_dashes("a hyphenated-word and a 2021-2025 range")
    assert not find_em_dashes(f"an en dash {EN_DASH} is not an em dash")


def test_does_not_flag_plain_punctuation():
    assert not find_em_dashes("a comma, a colon: a semicolon; all fine.")


def test_line_numbers_are_1_indexed():
    text = f"line one\nan em dash {EM_DASH} here\nline three"
    hits = find_em_dashes(text)
    assert hits == [(2, f"an em dash {EM_DASH} here")]


def test_multiple_hits_on_different_lines():
    text = f"a {EM_DASH} b\nc\nd {EM_DASH} e"
    hits = find_em_dashes(text)
    assert [lineno for lineno, _ in hits] == [1, 3]
