"""Tests for pipeline/hypotheses/flag_sensitivity.py."""
from pipeline.appdata import build_flags
from pipeline.hypotheses.flag_sensitivity import build_sensitivity, count_at


def _row(sym, **qv):
    return {"symbol": sym, "company_name": sym, "query_values": qv}


ROWS = [
    _row("A", payout_ratio=0.9, yield_ttm=0.09, dividend_yield_avg=0.05, free_float=0.22, indices=["LQ45"],
         all_time_high_price=100, last_close_price=91, **{"earnings[2025]": 1, "earnings[2024]": 2}),
    _row("B", payout_ratio=1.1, yield_ttm=0.06, dividend_yield_avg=0.05, free_float=0.28, indices=["LQ45"],
         all_time_high_price=100, last_close_price=85, **{"earnings[2025]": 1, "earnings[2024]": 2}),
    _row("C", payout_ratio=1.3, yield_ttm=0.10, dividend_yield_avg=0.05, free_float=0.10, indices=[]),
]


def test_shipped_constants_are_restored_after_counting():
    before = (build_flags.PAYOUT_RATIO_THRESHOLD, build_flags.LQ45_LOW_FLOAT_THRESHOLD)
    build_sensitivity(ROWS)
    assert (build_flags.PAYOUT_RATIO_THRESHOLD, build_flags.LQ45_LOW_FLOAT_THRESHOLD) == before


def test_counts_move_with_the_threshold_and_boundary_matches_the_flag():
    out = build_sensitivity(ROWS)
    payout = out["payout_snapshot_legacy"]  # ROWS carry the snapshot ratio
    assert payout["x1.0"]["flagged"] == 2  # B and C above 1.0
    assert payout["x0.8"]["flagged"] == 3  # 0.8 threshold adds A (0.9)
    assert payout["x1.2"]["flagged"] == 1  # only C above 1.2
    lq = out["lq45_low_float"]
    assert lq["x1.0"] == {"threshold": 0.25, "flagged": 1, "evaluable": 2}  # A only (C is not LQ45)
    assert lq["x1.2"]["flagged"] == 2  # 0.30 adds B
    near = out["near_ath_earnings_decline"]  # A is 9% below its high, B is 15% below
    assert near["x0.8"]["flagged"] == 0 and near["x1.0"]["flagged"] == 1 and near["x1.2"]["flagged"] == 1
    assert out["yield_far_above_average"]["x1.0"]["flagged"] == 2  # A and C at >= 1.5x average
