"""
Regression tests for check_no_advice_language.py.

Run:
    python -m pytest scripts/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_no_advice_language import find_advice_language  # noqa: E402


def test_catches_indonesian_recommendation():
    assert find_advice_language("Sebaiknya Anda membeli saham ini sekarang.")


def test_catches_english_recommendation():
    assert find_advice_language("You should buy this stock now.")


def test_catches_strong_buy():
    assert find_advice_language("Analysts rate this a strong buy.")


def test_does_not_flag_neutral_tradability_description():
    """diperjualbelikan (tradable) legitimately contains "jual"/"beli" as
    a compound word - must not false-positive on bare presence of those
    substrings, only on actual imperative/recommendation phrasing."""
    assert not find_advice_language(
        "Ini menunjukkan seberapa besar bagian saham yang bisa diperjualbelikan publik."
    )


def test_flags_disclaimer_naming_the_question_it_refuses():
    """A disclaimer sentence naming the very question it refuses to
    answer legitimately matches the pattern - that's expected and
    reviewed by a human, not a bug in the scanner."""
    hits = find_advice_language(
        "Ini bukan jawaban atas apakah sekarang waktu yang tepat untuk bertransaksi."
    )
    assert hits  # scanner correctly surfaces it; a human judges it's fine


def test_does_not_flag_factual_ranking_language():
    assert not find_advice_language("FILM turun 95% dari titik tertinggi tahun ini.")


def test_line_numbers_are_1_indexed():
    text = "line one\nyou should buy this\nline three"
    hits = find_advice_language(text)
    assert hits == [(2, "you should buy this")]
