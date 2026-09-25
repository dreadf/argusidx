"""Tests for pipeline/hypotheses/h17_earnings_growth.py (pre-registered 2026-09-22)."""
from pipeline.hypotheses.h17_earnings_growth import earnings_growth


def test_growth_is_relative_to_the_prior_year():
    assert earnings_growth({"earnings[2024]": 100.0, "earnings[2025]": 150.0}, 2025) == 0.5
    assert earnings_growth({"earnings[2024]": 100.0, "earnings[2025]": 50.0}, 2025) == -0.5


def test_growth_is_undefined_from_a_zero_or_negative_base_or_missing_year():
    assert earnings_growth({"earnings[2024]": 0.0, "earnings[2025]": 5.0}, 2025) is None
    assert earnings_growth({"earnings[2024]": -10.0, "earnings[2025]": 5.0}, 2025) is None
    assert earnings_growth({"earnings[2025]": 5.0}, 2025) is None
    assert earnings_growth({"earnings[2024]": 10.0}, 2025) is None
