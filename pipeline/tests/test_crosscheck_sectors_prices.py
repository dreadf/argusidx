"""Tests for pipeline/dev/crosscheck_sectors_prices.py (pure comparison logic only)."""
import pytest

from pipeline.dev.crosscheck_sectors_prices import compare_symbol, pick_sample, summarize


def test_compare_symbol_matches_on_date_and_measures_relative_diff():
    sectors = [{"date": "2026-09-01", "close": 100.0}, {"date": "2026-09-02", "close": 200.0}]
    yahoo = {"2026-09-01": 100.0, "2026-09-02": 203.0}  # 1.5% off on the second day
    result = compare_symbol(sectors, yahoo)
    assert result["n_matched_days"] == 2
    assert result["coverage"] == 1.0
    assert result["max_abs_diff"] == pytest.approx(0.015)
    assert result["days_over_1pct"] == 1


def test_compare_symbol_coverage_counts_sectors_days_missing_in_yahoo():
    sectors = [{"date": "2026-09-01", "close": 100.0}, {"date": "2026-09-02", "close": 100.0}]
    result = compare_symbol(sectors, {"2026-09-01": 100.0})
    assert result["coverage"] == 0.5
    assert result["median_abs_diff"] == 0.0


def test_compare_symbol_no_overlap_gives_none_not_zero():
    result = compare_symbol([{"date": "2026-09-01", "close": 100.0}], {})
    assert result["median_abs_diff"] is None
    assert result["coverage"] == 0.0


def test_summarize_ignores_symbols_with_no_overlap():
    per_symbol = {
        "A.JK": {"n_matched_days": 10, "days_over_1pct": 1, "median_abs_diff": 0.001, "max_abs_diff": 0.02, "coverage": 1.0},
        "B.JK": {"n_matched_days": 0, "days_over_1pct": 0, "median_abs_diff": None, "max_abs_diff": None, "coverage": 0.0},
    }
    summary = summarize(per_symbol)
    assert summary["symbols_checked"] == 2
    assert summary["symbols_with_overlap"] == 1
    assert summary["share_of_matched_days_within_1pct"] == pytest.approx(0.9)


def test_pick_sample_is_seeded_and_stratified():
    universe = [{"symbol": f"S{i:03d}.JK", "query_values": {"market_cap": 1000 - i}} for i in range(60)]
    prices = {r["symbol"]: {"timestamps": list(range(300))} for r in universe}
    first = pick_sample(universe, prices)
    assert first == pick_sample(universe, prices)
    assert [len(first[k]) for k in ("large", "mid", "small")] == [7, 7, 6]
    assert set(first["large"]) <= {f"S{i:03d}.JK" for i in range(20)}
