"""
Tests for pipeline/appdata/build_flags.py (docs/PRODUCT.md §6).
"""
from pipeline.appdata.build_flags import (
    build_lq45_low_float,
    build_near_ath_earnings_decline,
    build_payout_above_earnings,
    build_payout_snapshot_flag,
    build_yield_far_above_average,
)


def _row(symbol, **qv):
    return {"symbol": symbol, "query_values": qv}


def _h4_row(symbol, dps, earnings, shares):
    return _row(symbol, **{"total_dividend[2025]": dps, "earnings[2025]": earnings, "outstanding_shares[2025]": shares})


def test_payout_h4_construct_exactly_100_percent_does_not_trip():
    rows = [_h4_row("A.JK", 100, 1000, 10), _h4_row("B.JK", 100.01, 1000, 10)]  # 1.0 and 1.0001
    result = build_payout_above_earnings(rows)
    assert result["flagged_count"] == 1
    assert result["flagged"][0]["symbol"] == "B.JK"


def test_payout_h4_construct_ignores_the_snapshot_ratio_and_undefined_rows():
    rows = [
        _row("A.JK", payout_ratio=1.42, **{"total_dividend[2025]": 30, "earnings[2025]": 1000, "outstanding_shares[2025]": 10}),  # 0.3 by H4's construct
        _row("B.JK", payout_ratio=0.2),  # nothing to recompute
    ]
    result = build_payout_above_earnings(rows)
    assert result["flagged_count"] == 0
    assert result["evaluable_count"] == 1


def test_payout_snapshot_exactly_100_percent_does_not_trip():
    """§26: exactly 100% payout must fall on the non-flagged side of the
    line, per the plan's explicit `> 1.0` rule."""
    rows = [_row("A.JK", payout_ratio=1.0), _row("B.JK", payout_ratio=1.0001)]
    result = build_payout_snapshot_flag(rows)
    assert result["flagged_count"] == 1
    assert result["flagged"][0]["symbol"] == "B.JK"
    assert result["evaluable_count"] == 2


def test_payout_snapshot_excludes_nulls_from_denominator():
    rows = [_row("A.JK", payout_ratio=1.5), _row("B.JK", payout_ratio=None)]
    result = build_payout_snapshot_flag(rows)
    assert result["evaluable_count"] == 1
    assert result["flagged_count"] == 1


def test_near_ath_requires_both_earnings_years_present():
    rows = [
        _row("A.JK", all_time_high_price=100, last_close_price=95,
             **{"earnings[2025]": 50, "earnings[2024]": 100}),
        _row("B.JK", all_time_high_price=100, last_close_price=95,
             **{"earnings[2025]": 50}),  # missing 2024 -> excluded, not flagged
    ]
    result = build_near_ath_earnings_decline(rows)
    assert result["evaluable_count"] == 1
    assert result["flagged_count"] == 1
    assert result["flagged"][0]["symbol"] == "A.JK"


def test_near_ath_boundary_and_earnings_direction():
    rows = [
        # exactly 10% below ATH, earnings fell -> flagged (boundary inclusive)
        _row("A.JK", all_time_high_price=100, last_close_price=90,
             **{"earnings[2025]": 50, "earnings[2024]": 100}),
        # 11% below ATH -> not near enough
        _row("B.JK", all_time_high_price=100, last_close_price=89,
             **{"earnings[2025]": 50, "earnings[2024]": 100}),
        # near ATH but earnings rose -> not flagged
        _row("C.JK", all_time_high_price=100, last_close_price=95,
             **{"earnings[2025]": 150, "earnings[2024]": 100}),
    ]
    result = build_near_ath_earnings_decline(rows)
    assert {f["symbol"] for f in result["flagged"]} == {"A.JK"}
    assert result["evaluable_count"] == 3


def test_yield_far_above_average_threshold():
    rows = [
        _row("A.JK", yield_ttm=15, dividend_yield_avg=10),  # 1.5x exactly -> flagged
        _row("B.JK", yield_ttm=14, dividend_yield_avg=10),  # 1.4x -> not flagged
        _row("C.JK", yield_ttm=5, dividend_yield_avg=0),    # avg 0 -> excluded
    ]
    result = build_yield_far_above_average(rows)
    assert {f["symbol"] for f in result["flagged"]} == {"A.JK"}
    assert result["evaluable_count"] == 2


def test_lq45_low_float_only_evaluates_lq45_members():
    rows = [
        _row("A.JK", indices=["LQ45", "IDX30"], free_float=0.10),  # flagged
        _row("B.JK", indices=["LQ45"], free_float=0.50),  # member, not flagged
        _row("C.JK", indices=["IDX30"], free_float=0.05),  # not LQ45 -> excluded entirely
    ]
    result = build_lq45_low_float(rows)
    assert result["evaluable_count"] == 2  # A and B only, never C
    assert {f["symbol"] for f in result["flagged"]} == {"A.JK"}


def test_lq45_low_float_distinguishes_empty_list_from_missing_field():
    """§26: 'confirmed not in any index' (empty list) and 'we don't know'
    (missing/null) are different facts and must not collapse together."""
    rows = [
        _row("A.JK", indices=[], free_float=0.05),  # confirmed: no index membership
        _row("B.JK", free_float=0.05),  # indices field simply absent
    ]
    result = build_lq45_low_float(rows)
    assert result["evaluable_count"] == 0
    assert result["flagged"] == []


def test_lq45_low_float_excludes_missing_free_float():
    rows = [_row("A.JK", indices=["LQ45"], free_float=None)]
    result = build_lq45_low_float(rows)
    assert result["evaluable_count"] == 0
