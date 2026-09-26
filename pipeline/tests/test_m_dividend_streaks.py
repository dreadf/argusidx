"""Tests for pipeline/hypotheses/m_dividend_streaks.py (definitions in EXPERIMENT.md, 2026-09-26 batch 1)."""
from pipeline.hypotheses.m_dividend_streaks import (
    build_dividend_streaks,
    computable,
    has_streak,
    paid,
    streak_cell,
)


def _r(sym: str, divs: dict[int, float | None], earn_years: tuple[int, ...] = ()):
    qv = {f"total_dividend[{y}]": v for y, v in divs.items()}
    for y in earn_years:
        qv[f"earnings[{y}]"] = 1.0
    return {"symbol": sym, "query_values": qv}


def test_paid_needs_a_positive_value_missing_or_zero_is_not_paid():
    assert paid({"total_dividend[2022]": 1.0}, 2022)
    assert not paid({"total_dividend[2022]": 0.0}, 2022)
    assert not paid({"total_dividend[2022]": None}, 2022)
    assert not paid({}, 2022)


def test_streak_needs_every_year_and_the_data_floor():
    qv = _r("A", {2021: 1, 2022: 1, 2023: 1})["query_values"]
    assert has_streak(qv, 3, 2023) and has_streak(qv, 1, 2023)
    qv2 = _r("B", {2021: 1, 2022: None, 2023: 1})["query_values"]
    assert has_streak(qv2, 1, 2023) and not has_streak(qv2, 2, 2023)
    assert computable(2, 2022) and not computable(3, 2022) and computable(4, 2024) and not computable(4, 2023)
    assert streak_cell([], 4, 2023) is None


def test_outcomes_paid_again_and_at_least_as_much_boundary_equal_counts():
    universe = [
        _r("SAME", {2023: 10, 2024: 10}),  # equal -> at least as much
        _r("LESS", {2023: 10, 2024: 9}),  # paid again, but less
        _r("MORE", {2023: 10, 2024: 11}),
        _r("STOP", {2023: 10, 2024: None}),  # missing counts as not paid
        _r("NEVER", {2023: None, 2024: 5}),  # no streak in 2023
    ]
    cell = streak_cell(universe, 1, 2023)
    assert cell["paid_again"] == {"n": 4, "count": 3, "rate": 0.75}
    assert cell["paid_at_least_as_much"] == {"n": 4, "count": 2, "rate": 0.5}


def test_reported_only_view_uses_earnings_of_the_next_year():
    universe = [
        _r("REPORTED_STOP", {2023: 10, 2024: None}, earn_years=(2024,)),
        _r("SILENT_STOP", {2023: 10, 2024: None}),
        _r("PAID", {2023: 10, 2024: 10}, earn_years=(2024,)),
    ]
    cell = streak_cell(universe, 1, 2023)
    assert cell["paid_again"]["n"] == 3 and cell["paid_again"]["count"] == 1
    assert cell["paid_again_reported_only"] == {"n": 2, "count": 1, "rate": 0.5}


def test_empty_cell_has_none_rate_and_build_covers_all_twelve_cells():
    out = build_dividend_streaks([])
    assert len(out) == 12
    assert out["N=1,Y=2022"]["paid_again"] == {"n": 0, "count": 0, "rate": None}
    assert out["N=4,Y=2022"] is None and out["N=3,Y=2022"] is None and out["N=4,Y=2023"] is None
