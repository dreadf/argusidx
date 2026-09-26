"""Tests for pipeline/hypotheses/m_typical_drawdown_by_sector.py."""
from pipeline.hypotheses.m_typical_drawdown_by_sector import MIN_GROUP, build_by_sector, summarize_group


def _entry(drop: float, bars: int = 130) -> dict:
    # 100 for half the bars, then price*(1-drop) for the rest -> max drawdown of exactly -drop
    half = bars // 2
    return {"close": [100.0] * half + [100.0 * (1 - drop)] * (bars - half)}


def _u(sym, sector):
    return {"symbol": sym, "query_values": {"sector": sector}}


def test_group_below_15_is_too_few_and_15_is_reported():
    rows = [{"mdd": -0.1}] * (MIN_GROUP - 1)
    assert summarize_group(rows) == {"n": 14, "too_few": True}
    assert summarize_group(rows + [{"mdd": -0.5}])["too_few"] is False


def test_share_at_least_30_percent_counts_exactly_30():
    rows = [{"mdd": -0.30}] * 5 + [{"mdd": -0.2999}] * 10
    g = summarize_group(rows)
    assert abs(g["share_drawdown_30_or_worse"] - 5 / 15) < 1e-12
    assert g["median"] == -0.2999


def test_build_groups_by_sector_and_skips_short_history_and_missing_sector():
    universe = [_u(f"A{i}.JK", "Energy") for i in range(15)] + [_u("B1.JK", "Healthcare"), _u("NOSEC.JK", None)]
    prices = {f"A{i}.JK": _entry(0.4) for i in range(15)}
    prices["B1.JK"] = _entry(0.1)
    prices["SHORT.JK"] = _entry(0.1, bars=50)
    prices["NOSEC.JK"] = _entry(0.1)
    prices["UNKNOWN.JK"] = _entry(0.1)
    out = build_by_sector(prices, universe + [_u("SHORT.JK", "Energy")])
    assert out["n_stocks"] == 16
    assert out["by_sector"]["Energy"]["n"] == 15 and abs(out["by_sector"]["Energy"]["median"] + 0.4) < 1e-9
    assert out["by_sector"]["Healthcare"] == {"n": 1, "too_few": True}
