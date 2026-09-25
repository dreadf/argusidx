"""
Tests for pipeline/appdata/build_beat_gold.py.
"""
from pipeline.appdata.build_beat_gold import (
    bi_deposit_return,
    build_per_symbol,
    build_rows,
    build_summary,
    compute_typical_and_sector_median,
    _annualize,
    _dt,
)


def test_annualize_doubles_over_one_year():
    assert round(_annualize(1.0, 1.0), 4) == 1.0


def test_annualize_compounds_over_multiple_years():
    # 100% total return over 2 years annualizes to sqrt(2)-1, not 50%.
    result = _annualize(1.0, 2.0)
    assert abs(result - (2 ** 0.5 - 1)) < 1e-9


def test_bi_deposit_return_uses_flat_rate_when_no_segment_change():
    start = _dt(2023, 10, 1)
    end = _dt(2024, 10, 1)
    # Both dates fall inside the single 2023-09-01 6.00% segment (held through 2024).
    result = bi_deposit_return(start, end)
    assert abs(result - 0.06) < 0.005


def _price_entry(start_ts, end_ts, start_price, end_price):
    return {
        "timestamps": [start_ts, end_ts],
        "close": [start_price, end_price],
        "adjclose": [start_price, end_price],
    }


YEAR_SECONDS = 365.25 * 86400


def test_build_rows_excludes_short_history():
    prices5y = {
        "SHORT.JK": _price_entry(0, int(0.5 * YEAR_SECONDS), 100, 110),  # < MIN_YEARS
        "LONG.JK": _price_entry(0, int(2 * YEAR_SECONDS), 100, 200),
    }
    rows = build_rows(prices5y, {}, {}, {})
    assert [r["sym"] for r in rows] == ["LONG.JK"]


def test_build_rows_excludes_non_positive_prices():
    prices5y = {"BAD.JK": _price_entry(0, int(2 * YEAR_SECONDS), 0, 100)}
    rows = build_rows(prices5y, {}, {}, {})
    assert rows == []


def test_build_summary_win_rate_and_typical_stock():
    rows = [
        {"sym": "A.JK", "years": 2.0, "stock_ann": 0.20, "jkse_ann": 0.05, "gold_ann": 0.10, "bi_ann": 0.06, "sub_sector": "X"},
        {"sym": "B.JK", "years": 2.0, "stock_ann": -0.10, "jkse_ann": 0.05, "gold_ann": 0.10, "bi_ann": 0.06, "sub_sector": "X"},
    ]
    typical, sector_median = compute_typical_and_sector_median(rows)
    summary = build_summary(rows, typical, sector_median)
    assert summary["n"] == 2
    assert summary["beat_index"] == {"wins": 1, "n": 2, "pct": 50.0}
    assert summary["beat_gold"] == {"wins": 1, "n": 2, "pct": 50.0}
    assert summary["negative_return"] == {"count": 1, "n": 2, "pct": 50.0}


def test_build_summary_beat_typical_stock_pct_is_computed_not_hardcoded():
    # n=3, uneven split (1 of 3 beats the median) - a hardcoded 50.0 would
    # not match this and must be caught, unlike the n=2/no-ties case above.
    rows = [
        {"sym": "A.JK", "years": 2.0, "stock_ann": 0.30, "jkse_ann": 0.05, "gold_ann": 0.10, "bi_ann": 0.06, "sub_sector": "X"},
        {"sym": "B.JK", "years": 2.0, "stock_ann": 0.10, "jkse_ann": 0.05, "gold_ann": 0.10, "bi_ann": 0.06, "sub_sector": "X"},
        {"sym": "C.JK", "years": 2.0, "stock_ann": -0.10, "jkse_ann": 0.05, "gold_ann": 0.10, "bi_ann": 0.06, "sub_sector": "X"},
    ]
    typical, sector_median = compute_typical_and_sector_median(rows)
    summary = build_summary(rows, typical, sector_median)
    assert summary["beat_typical_stock"] == {"wins": 1, "n": 3, "pct": 33.3}


def test_build_summary_handles_missing_benchmark_gracefully():
    # If gold_ann is None for every row (benchmark ticker missing), beat_gold
    # must report n=0/pct=None, never divide-by-zero crash.
    rows = [
        {"sym": "A.JK", "years": 2.0, "stock_ann": 0.20, "jkse_ann": 0.05, "gold_ann": None, "bi_ann": 0.06, "sub_sector": None},
    ]
    typical, sector_median = compute_typical_and_sector_median(rows)
    summary = build_summary(rows, typical, sector_median)
    assert summary["beat_gold"] == {"wins": 0, "n": 0, "pct": None}


def test_build_per_symbol_beat_flags():
    rows = [
        {"sym": "A.JK", "company_name": "A Co", "years": 3.0, "stock_ann": 0.20, "jkse_ann": 0.05, "gold_ann": 0.10, "bi_ann": 0.06, "sub_sector": "Banks"},
    ]
    result = build_per_symbol(rows, sector_median={"Banks": 0.15}, typical=0.02)
    a = result["A.JK"]
    assert a["beat_index"] is True
    assert a["beat_gold"] is True
    assert a["beat_deposit"] is True
    assert a["beat_typical_stock"] is True
    assert a["beat_sector_peer"] is True  # 0.20 > 0.15


def test_build_per_symbol_none_when_sub_sector_unknown():
    rows = [
        {"sym": "A.JK", "company_name": "A Co", "years": 3.0, "stock_ann": 0.20, "jkse_ann": None, "gold_ann": None, "bi_ann": 0.06, "sub_sector": None},
    ]
    result = build_per_symbol(rows, sector_median={}, typical=0.02)
    a = result["A.JK"]
    assert a["beat_index"] is None
    assert a["beat_gold"] is None
    assert a["beat_sector_peer"] is None
