"""Tests for the H19 count-only step (pipeline/hypotheses/h19_coal_miners.py)."""
from pipeline.hypotheses.h19_coal_miners import (
    build_counts,
    coal_miner_symbols,
    count_consecutive_observation_changes,
    count_monthly_changes,
)


def _p(d, v=100.0):
    return {"name": "Coal", "date": d, "price_usd_per_ton": v}


def test_consecutive_first_of_month_points_count_changes():
    pts = [_p("2024-11-01"), _p("2024-12-01"), _p("2025-01-01"), _p("2025-02-01")]
    assert count_monthly_changes(pts) == 3  # year boundary counts


def test_gap_missing_or_nonpositive_price_breaks_the_chain():
    pts = [_p("2024-01-01"), _p("2024-02-01", None), _p("2024-03-01"), _p("2024-04-01"), _p("2024-06-01")]
    assert count_monthly_changes(pts) == 1  # only Mar->Apr
    assert count_monthly_changes([_p("2024-01-01"), _p("2024-02-01", 0.0)]) == 0


def test_mid_month_points_are_not_monthly_observations():
    pts = [_p("2025-03-01"), _p("2025-03-15"), _p("2025-04-01"), _p("2025-04-15"), _p("2025-05-01")]
    assert count_monthly_changes(pts) == 2
    assert count_consecutive_observation_changes(pts) == 4


def test_empty_series_has_zero_changes():
    assert count_monthly_changes([]) == 0 and count_consecutive_observation_changes([]) == 0


def test_coal_miners_need_a_symbol_and_coal_and_are_deduplicated():
    companies = [
        {"symbol": "ADRO.JK", "commodity_type": ["Coal"]},
        {"symbol": "ADRO.JK", "commodity_type": ["Coal", "Gold"]},
        {"symbol": None, "commodity_type": ["Coal"]},
        {"symbol": "ANTM.JK", "commodity_type": ["Gold"]},
        {"symbol": "XXXX.JK", "commodity_type": None},
    ]
    assert coal_miner_symbols(companies) == ["ADRO.JK"]


def test_power_rule_boundary_24_changes():
    months = [f"{2024 + i // 12}-{i % 12 + 1:02d}-01" for i in range(25)]  # 25 points -> 24 changes
    coal = {"Coal": [_p(d) for d in months]}
    hba = {"Coal (HBA 1)": [_p(d) for d in months[:24]]}  # 23 changes
    out = build_counts(coal, hba, [])
    assert out["series"]["Coal"]["usable_monthly_changes"] == 24
    assert out["power_rule_met_by_series"] == {"Coal": True, "Coal (HBA 1)": False}
