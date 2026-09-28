"""Tests for pipeline/hypotheses/r4_market_state_split.py, on synthetic data."""
import pytest

from pipeline.hypotheses.r4_market_state_split import h4_entry_date, h5_entry_date, state_on_or_after


def test_h5_entry_date_is_may_1_of_the_following_year():
    assert h5_entry_date(2022) == "2023-05-01"
    assert h5_entry_date(2025) == "2026-05-01"


def test_h4_entry_date_is_may_1_of_the_following_year():
    assert h4_entry_date(2021) == "2022-05-01"
    assert h4_entry_date(2024) == "2025-05-01"


def test_state_on_or_after_finds_exact_match():
    dates = ["2025-04-29", "2025-04-30", "2025-05-01", "2025-05-02"]
    states = ["normal", "normal", "tertekan", "normal"]
    d, s = state_on_or_after(dates, states, "2025-05-01")
    assert d == "2025-05-01"
    assert s == "tertekan"


def test_state_on_or_after_skips_a_non_trading_day_to_the_next_one():
    """2025-05-01 isn't in the series (e.g. a holiday) -- the nearest trading
    day on/after it is used, same nearest-value convention as the rest of
    this project (stats.nearest_value)."""
    dates = ["2025-04-30", "2025-05-02", "2025-05-05"]
    states = ["normal", "tertekan", "normal"]
    d, s = state_on_or_after(dates, states, "2025-05-01")
    assert d == "2025-05-02"
    assert s == "tertekan"


def test_state_on_or_after_raises_past_the_end_of_the_series():
    with pytest.raises(ValueError):
        state_on_or_after(["2025-04-30"], ["normal"], "2025-05-01")
