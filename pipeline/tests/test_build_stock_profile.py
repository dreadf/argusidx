"""
Tests for pipeline/appdata/build_stock_profile.py.
"""
import pytest

from pipeline.appdata.build_stock_profile import build, foreign_days, pe_meaningful, revenue_growth, share_above, share_below, size_third


def _row(sym, **q):
    base = {"sector": "Industrials", "market_cap_rank": 1}
    return {"symbol": sym, "query_values": {**base, **q}}


def test_shares_are_strict():
    assert share_below([1.0, 2.0, 3.0, 4.0], 3.0) == 50.0
    assert share_above([1.0, 2.0, 3.0, 4.0], 3.0) == 25.0
    with pytest.raises(ValueError):
        share_below([], 1.0)


def test_pe_is_not_meaningful_after_a_loss_year_even_if_trailing_pe_is_positive():
    assert pe_meaningful({"pe_ttm": 8.0, "earnings[2025]": 1e12})
    assert not pe_meaningful({"pe_ttm": 30826.0, "earnings[2025]": -1.2e12})
    assert not pe_meaningful({"pe_ttm": -12.0, "earnings[2025]": 1e12})
    assert pe_meaningful({"pe_ttm": 8.0})


def test_revenue_growth_needs_a_positive_base():
    assert revenue_growth({"revenue[2024]": 100.0, "revenue[2025]": 110.0}) == pytest.approx(0.10)
    assert revenue_growth({"revenue[2024]": 0.0, "revenue[2025]": 110.0}) is None
    assert revenue_growth({"revenue[2025]": 110.0}) is None


def test_size_thirds():
    assert size_third(1, 900) == "large"
    assert size_third(301, 900) == "mid"
    assert size_third(601, 900) == "small"
    assert size_third(None, 900) is None


def test_foreign_days_counts_each_list_appearance():
    flow = {"d1": {"buy": [{"symbol": "A"}], "sell": [{"symbol": "B"}]}, "d2": {"buy": [{"symbol": "A"}, {"symbol": "B"}]}}
    assert foreign_days(flow) == {"A": {"buy": 2, "sell": 0}, "B": {"buy": 1, "sell": 1}}


def test_build_ranks_change_within_sector_and_counts_non_payers_as_zero_yield():
    rows = [
        _row("A", yield_ttm=0.05, pe_ttm=5.0, **{"earnings[2025]": 1.0}),
        _row("B", yield_ttm=None, pe_ttm=10.0, **{"earnings[2025]": 1.0}),
        _row("C", yield_ttm=0.02, pe_ttm=20.0, sector="Financials", der_mrq=5.0, **{"earnings[2025]": 1.0}),
    ]
    out = build(rows, {"A": 100.0, "B": 100.0, "C": 100.0}, {"A": 90.0, "B": 120.0, "C": 50.0}, {})
    assert out["A"]["change_1y"] == pytest.approx(-0.10)
    assert out["A"]["sector_rank_1y"] == {"better": 1, "n": 2}  # C is another sector
    assert out["B"]["sector_rank_1y"] == {"better": 0, "n": 2}
    assert out["A"]["yield_higher_than"] == pytest.approx(200 / 3)  # above B (0) and C
    assert out["B"]["yield_higher_than"] == 0.0
    assert out["A"]["yield_higher_than_payers"] == 50.0  # payers only: above C
    assert out["B"]["yield_higher_than_payers"] is None
    assert out["A"]["pe_cheaper_than"] == pytest.approx(200 / 3)
    assert out["C"]["der_higher_than"] is None  # financials never compared on debt
    assert out["A"]["free_float_higher_than"] is None


def test_build_leaves_change_null_when_a_close_is_missing():
    out = build([_row("A")], {}, {"A": 90.0}, {})
    assert out["A"]["change_1y"] is None
    assert out["A"]["sector_rank_1y"] is None
