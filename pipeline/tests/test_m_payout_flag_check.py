"""Tests for pipeline/hypotheses/m_payout_flag_check.py (definitions in EXPERIMENT.md, 2026-09-26 batch 1)."""
from pipeline.hypotheses.m_payout_flag_check import (
    check_flag_construct,
    cut_rate_above_100,
    h4_ratio,
)


def _row(sym, snapshot, div, earnings, shares, **extra):
    qv = {"payout_ratio": snapshot, "total_dividend[2025]": div, "earnings[2025]": earnings, "outstanding_shares[2025]": shares}
    qv.update(extra)
    return {"symbol": sym, "company_name": sym, "query_values": qv}


def test_h4_ratio_is_dividend_per_share_over_eps_and_none_when_undefined():
    qv = {"total_dividend[2025]": 50.0, "earnings[2025]": 1000.0, "outstanding_shares[2025]": 10.0}
    assert h4_ratio(qv, 2025) == 0.5  # EPS 100, dividend 50
    assert h4_ratio({**qv, "earnings[2025]": -5.0}, 2025) is None
    assert h4_ratio({**qv, "total_dividend[2025]": None}, 2025) is None
    assert h4_ratio(qv, 2024) is None


def test_agreement_requires_recomputed_ratio_strictly_above_one():
    universe = [
        _row("AGREE", 1.4, 150.0, 1000.0, 10.0),  # ratio 1.5
        _row("EXACT", 1.4, 100.0, 1000.0, 10.0),  # ratio exactly 1.0 -> not above
        _row("BELOW", 1.4, 50.0, 1000.0, 10.0),  # ratio 0.5
        _row("UNDEF", 1.4, 50.0, -1000.0, 10.0),  # loss-making -> undefined
        _row("NOTFLAGGED", 1.0, 500.0, 1000.0, 10.0),  # snapshot exactly 1.0 -> not flagged
        _row("NOSNAP", None, 500.0, 1000.0, 10.0),
    ]
    out = check_flag_construct(universe, 2025)
    assert out["flagged"] == 4
    assert out["agree"] == 1
    assert out["disagree"] == 3
    assert out["disagree_undefined"] == 1 and out["disagree_at_or_below_1"] == 2
    assert {d["symbol"] for d in out["disagreements"]} == {"EXACT", "BELOW", "UNDEF"}


def _y(sym, year, div, div_next, earnings=1000.0, shares=10.0):
    return {
        "symbol": sym,
        "query_values": {
            f"total_dividend[{year}]": div,
            f"total_dividend[{year + 1}]": div_next,
            f"earnings[{year}]": earnings,
            f"outstanding_shares[{year}]": shares,
        },
    }


def test_cut_rate_bucket_is_strictly_above_100_percent_and_counts_cuts():
    universe = [
        _y("CUT", 2021, 150.0, 100.0),  # ratio 1.5, cut
        _y("KEEP", 2021, 150.0, 150.0),  # ratio 1.5, unchanged -> not a cut
        _y("EXACT", 2021, 100.0, 50.0),  # ratio exactly 1.0 -> excluded
        _y("LOW", 2021, 10.0, 5.0),  # ratio 0.1 -> excluded
        _y("NOOUT", 2021, 150.0, None),  # no next-year value -> H4 skips it
    ]
    out = cut_rate_above_100(universe, [2021])
    assert out == {"n": 2, "cuts": 1, "cut_rate": 0.5}


def test_cut_rate_empty_bucket_is_none():
    assert cut_rate_above_100([], [2021]) == {"n": 0, "cuts": 0, "cut_rate": None}
