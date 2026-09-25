"""Tests for pipeline/hypotheses/m_earnings_streaks.py (definitions in EXPERIMENT.md, 2026-09-22)."""
from pipeline.hypotheses.m_earnings_streaks import (
    build_more_than_doubled,
    build_two_year_decline,
    doubled_rows,
    is_more_than_doubled,
    is_two_year_decline,
    two_year_decline_rows,
)


def _row(**earnings) -> dict:
    return {"symbol": "X.JK", "query_values": {f"earnings[{y}]": v for y, v in earnings.items()}}


def test_two_year_decline_rules():
    qv = {"earnings[2021]": 90.0, "earnings[2022]": 60.0, "earnings[2023]": 30.0}
    assert is_two_year_decline(qv, 2023)
    assert not is_two_year_decline({**qv, "earnings[2021]": 0.0}, 2023)  # must start from a profit
    assert not is_two_year_decline({**qv, "earnings[2022]": 95.0}, 2023)  # not a steady decline
    assert not is_two_year_decline({"earnings[2022]": 60.0, "earnings[2023]": 30.0}, 2023)  # a year missing


def test_two_year_decline_base_rate_counts_rises_next_year_only_when_next_year_exists():
    universe = [
        _row(**{"2021": 90.0, "2022": 60.0, "2023": 30.0, "2024": 40.0}),  # rose
        _row(**{"2021": 90.0, "2022": 60.0, "2023": 30.0, "2024": 20.0}),  # fell again
        _row(**{"2021": 90.0, "2022": 60.0, "2023": 30.0}),  # no 2024 yet: not counted
    ]
    rows = two_year_decline_rows(universe, [2023])
    assert [r["rose_next_year"] for r in rows] == [True, False]
    out = build_two_year_decline(universe)
    assert out["pooled"] == {"n": 2, "count": 1, "rate": 0.5}


def test_more_than_doubled_is_strict_and_needs_a_positive_base():
    assert is_more_than_doubled({"earnings[2022]": 10.0, "earnings[2023]": 20.1}, 2023)
    assert not is_more_than_doubled({"earnings[2022]": 10.0, "earnings[2023]": 20.0}, 2023)
    assert not is_more_than_doubled({"earnings[2022]": -10.0, "earnings[2023]": 50.0}, 2023)


def test_more_than_doubled_gave_back_measures():
    universe = [
        _row(**{"2022": 10.0, "2023": 30.0, "2024": 25.0}),  # gave part back, still above pre-jump
        _row(**{"2022": 10.0, "2023": 30.0, "2024": 8.0}),  # gave all back
        _row(**{"2022": 10.0, "2023": 30.0, "2024": 35.0}),  # held
    ]
    rows = doubled_rows(universe, [2023])
    assert [(r["gave_part_back"], r["gave_all_back"]) for r in rows] == [(True, False), (True, True), (False, False)]
    out = build_more_than_doubled(universe)
    assert out["gave_part_back"]["count"] == 2
    assert out["gave_all_back"]["count"] == 1
