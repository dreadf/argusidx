"""
Tests for pipeline/appdata/build_stock_pages.py.
"""
import pytest

from pipeline.appdata.build_stock_pages import (
    build_flags_for_stock,
    build_peer_comparison,
    build_situations_for_stock,
    build_snapshot,
    build_suspension_history,
)


def _row(symbol, **qv):
    return {"symbol": symbol, "company_name": f"{symbol} Co", "query_values": qv}


def test_snapshot_position_in_range_is_none_for_degenerate_range():
    """A stock whose 52w low equals its 52w high (e.g. long-suspended,
    frozen price) must not report a fake position - regression for the
    real ARTI.JK case found in the live universe sweep."""
    row = _row("A.JK", **{"52_w_low_price": 2.0, "52_w_high_price": 2.0, "last_close_price": 2.0})
    snapshot = build_snapshot(row)
    assert snapshot["position_in_52w_range"] is None


def test_snapshot_position_in_range_normal_case():
    row = _row("A.JK", **{"52_w_low_price": 80.0, "52_w_high_price": 100.0, "last_close_price": 90.0})
    snapshot = build_snapshot(row)
    assert snapshot["position_in_52w_range"] == 0.5


def test_peer_comparison_counts_strictly_better_peers():
    rows = {
        "A.JK": _row("A.JK", roe_ttm=0.20),
        "B.JK": _row("B.JK", roe_ttm=0.10),
        "C.JK": _row("C.JK", roe_ttm=0.30),
        "D.JK": _row("D.JK", roe_ttm=None),  # missing -> excluded from comparable_count
    }
    peer_groups = {
        "assignments": {"A.JK": {"level": "sector", "group": "X"}},
        "group_members": {"sector:X": ["A.JK", "B.JK", "C.JK", "D.JK"]},
    }
    result = build_peer_comparison(rows["A.JK"], rows, peer_groups)
    assert result["better_than_count"] == 1  # beats B, not C
    assert result["comparable_count"] == 2  # B and C, not D (null) or self
    assert result["peer_count"] == 4


def test_peer_comparison_own_value_missing_returns_null_counts_not_zero():
    """A missing metric is not the same as 'worse than everyone' - must
    surface as null, not a misleading 0."""
    rows = {
        "A.JK": _row("A.JK", roe_ttm=None),
        "B.JK": _row("B.JK", roe_ttm=0.10),
    }
    peer_groups = {
        "assignments": {"A.JK": {"level": "sector", "group": "X"}},
        "group_members": {"sector:X": ["A.JK", "B.JK"]},
    }
    result = build_peer_comparison(rows["A.JK"], rows, peer_groups)
    assert result["own_value"] is None
    assert result["better_than_count"] is None
    assert result["comparable_count"] is None


def test_peer_comparison_no_assignment_returns_none():
    result = build_peer_comparison(_row("Z.JK"), {}, {"assignments": {}, "group_members": {}})
    assert result is None


def test_flags_for_stock_only_returns_tripped_flags():
    flags = {
        "payout_above_earnings": {"flagged": [{"symbol": "A.JK", "payout_ratio": 1.5}]},
        "near_ath_earnings_decline": {"flagged": []},
        "yield_far_above_average": {"flagged": [{"symbol": "B.JK", "yield_ttm": 0.1, "yield_avg": 0.02}]},
        "lq45_low_float": {"flagged": []},
    }
    result = build_flags_for_stock("A.JK", flags)
    assert len(result) == 1
    assert result[0]["key"] == "payout_above_earnings"


def test_flags_for_stock_includes_lq45_flag():
    flags = {
        "payout_above_earnings": {"flagged": []},
        "near_ath_earnings_decline": {"flagged": []},
        "yield_far_above_average": {"flagged": []},
        "lq45_low_float": {"flagged": [{"symbol": "A.JK", "free_float": 0.1}]},
    }
    result = build_flags_for_stock("A.JK", flags)
    assert len(result) == 1
    assert result[0]["key"] == "lq45_low_float"


def test_flags_for_stock_no_flags_returns_empty_list_not_none():
    flags = {
        "payout_above_earnings": {"flagged": []},
        "near_ath_earnings_decline": {"flagged": []},
        "yield_far_above_average": {"flagged": []},
        "lq45_low_float": {"flagged": []},
    }
    assert build_flags_for_stock("A.JK", flags) == []


def test_suspension_history_none_for_never_suspended_company():
    suspensions = {
        "by_symbol": {},
        "base_rates": {},
        "universe_count": 962,
        "companies_with_suspensions": 330,
        "base_rate_pct": 34.3,
    }
    assert build_suspension_history("BBCA.JK", suspensions) is None


def test_suspension_history_carries_base_rate_alongside_events():
    suspensions = {
        "by_symbol": {"A.JK": [{"date": "2026-01-01", "reason": "r", "category": "unusual_price_movement"}]},
        "base_rates": {"A.JK": {"count": 1, "universe_count": 962, "more_than_pct": 60.0}},
        "universe_count": 962,
        "companies_with_suspensions": 330,
        "base_rate_pct": 34.3,
    }
    result = build_suspension_history("A.JK", suspensions)
    assert result["count"] == 1
    assert result["more_than_pct"] == 60.0
    assert result["base_rate_pct"] == 34.3
    assert result["universe_count"] == 962
    assert len(result["events"]) == 1


def test_suspension_history_fails_loudly_when_base_rate_missing():
    # Real, currently-live state (verified 2026-09-19): a symbol can have
    # events in by_symbol with no matching base_rates entry if it dropped
    # out of the universe snapshot between builds. Must not KeyError or
    # silently drop the data.
    suspensions = {
        "by_symbol": {"A.JK": [{"date": "2026-01-01", "reason": "r", "category": "unusual_price_movement"}]},
        "base_rates": {},
        "universe_count": 962,
        "companies_with_suspensions": 330,
        "base_rate_pct": 34.3,
    }
    with pytest.raises(ValueError, match="base_rates"):
        build_suspension_history("A.JK", suspensions)


def test_h1_finding_risky_side_for_high_tercile_significant_bucket():
    from pipeline.appdata.build_stock_pages import build_h1_finding

    h1 = {"A.JK": {"size_bucket": "largest", "size_bucket_significant": True, "free_float_tercile": "high"}}
    result = build_h1_finding("A.JK", h1)
    assert result == {"state": "risky_side", "size_bucket": "largest", "free_float_tercile": "high"}


def test_h1_finding_calm_side_for_low_tercile_significant_bucket():
    from pipeline.appdata.build_stock_pages import build_h1_finding

    h1 = {"A.JK": {"size_bucket": "smallest", "size_bucket_significant": True, "free_float_tercile": "low"}}
    result = build_h1_finding("A.JK", h1)
    assert result["state"] == "calm_side"


def test_h1_finding_in_between_for_mid_tercile_significant_bucket():
    from pipeline.appdata.build_stock_pages import build_h1_finding

    h1 = {"A.JK": {"size_bucket": "smallest", "size_bucket_significant": True, "free_float_tercile": "mid"}}
    result = build_h1_finding("A.JK", h1)
    assert result["state"] == "in_between"


def test_h1_finding_weaker_evidence_for_non_significant_bucket_regardless_of_tercile():
    from pipeline.appdata.build_stock_pages import build_h1_finding

    h1 = {"A.JK": {"size_bucket": "mid_large", "size_bucket_significant": False, "free_float_tercile": "high"}}
    result = build_h1_finding("A.JK", h1)
    assert result["state"] == "weaker_evidence_for_size_range"


def test_h1_finding_none_when_symbol_not_resolvable():
    from pipeline.appdata.build_stock_pages import build_h1_finding

    assert build_h1_finding("MISSING.JK", {}) is None


def test_insider_activity_returns_entry_when_present():
    from pipeline.appdata.build_stock_pages import build_insider_activity_for_stock

    insider_activity = {"A.JK": {"buy_count": 2, "sell_count": 0, "net_direction": "net_buying", "last_transaction_date": "2025-06-01"}}
    result = build_insider_activity_for_stock("A.JK", insider_activity)
    assert result["net_direction"] == "net_buying"


def test_insider_activity_none_when_no_filings():
    from pipeline.appdata.build_stock_pages import build_insider_activity_for_stock

    result = build_insider_activity_for_stock("Z.JK", {})
    assert result is None


def test_sector_context_pairs_own_values_with_sector_medians():
    from pipeline.appdata.build_stock_pages import build_sector_context

    row = _row("A.JK", sector="Financials", roe_ttm=0.20, pe_ttm=12.0)
    sector_breakdown = [
        {"sector": "Financials", "typical_roe_pct": 15.0, "roe_n": 40, "typical_pe": 10.0, "pe_n": 38, "company_count": 45},
    ]
    result = build_sector_context(row, sector_breakdown)
    assert result["own_roe_pct"] == 20.0
    assert result["own_pe"] == 12.0
    assert result["sector_typical_roe_pct"] == 15.0
    assert result["sector_company_count"] == 45


def test_sector_context_none_when_sector_missing():
    from pipeline.appdata.build_stock_pages import build_sector_context

    row = _row("A.JK", roe_ttm=0.20)
    assert build_sector_context(row, []) is None


def test_sector_context_own_values_none_when_not_reported():
    from pipeline.appdata.build_stock_pages import build_sector_context

    row = _row("A.JK", sector="Financials")
    sector_breakdown = [
        {"sector": "Financials", "typical_roe_pct": 15.0, "roe_n": 40, "typical_pe": 10.0, "pe_n": 38, "company_count": 45},
    ]
    result = build_sector_context(row, sector_breakdown)
    assert result["own_roe_pct"] is None
    assert result["own_pe"] is None


def test_lens_extractive_attaches_trends_only_for_commodities_with_history():
    from pipeline.appdata.build_stock_pages import build_lens_extractive_for_stock

    entry = {"company_type": "Mine Owner", "key_operation": "Mining", "commodity_type": ["Coal", "Silver"]}
    context = {"Coal": {"latest_date": "2026-02-15", "change_12m_pct": -17.2}}
    result = build_lens_extractive_for_stock(entry, context)
    assert [t["commodity"] for t in result["commodity_trends"]] == ["Coal"]
    assert result["commodity_trends"][0]["latest_date"] == "2026-02-15"
    assert result["company_type"] == "Mine Owner"


def test_lens_extractive_none_stays_none():
    from pipeline.appdata.build_stock_pages import build_lens_extractive_for_stock

    assert build_lens_extractive_for_stock(None, {"Coal": {}}) is None


def test_corporate_actions_for_stock_always_carries_the_window():
    from pipeline.appdata.build_stock_pages import build_corporate_actions_for_stock

    ca = {"as_of": "2026-09-20", "window": {"start": "2026-08-21", "end": "2026-10-20"}, "by_symbol": {}}
    result = build_corporate_actions_for_stock("A.JK", ca)
    assert result["window_start"] == "2026-08-21"
    assert result["dividends"] == [] and result["agms"] == []


def test_corporate_actions_for_stock_returns_its_events():
    from pipeline.appdata.build_stock_pages import build_corporate_actions_for_stock

    ca = {
        "as_of": "2026-09-20",
        "window": {"start": "2026-08-21", "end": "2026-10-20"},
        "by_symbol": {"A.JK": {"dividends": [{"ex_date": "2026-09-25", "amount": 50.0}]}},
    }
    result = build_corporate_actions_for_stock("A.JK", ca)
    assert result["dividends"][0]["amount"] == 50.0
    assert result["rights_issues"] == []


def test_situations_for_stock_returns_its_entry():
    entry = {"fall": None, "older_fall": None, "loss_year": {"year": 2025, "net_income": -1.0}, "recent_price_suspension": None, "recent_ipo": None}
    assert build_situations_for_stock("A.JK", {"A.JK": entry}) is entry


def test_situations_for_stock_fails_loudly_when_symbol_missing():
    """Every universe symbol has an entry (all-null when in no situation), so a
    missing one means a stale situations.json, not 'no situation'."""
    with pytest.raises(ValueError, match="situations.json"):
        build_situations_for_stock("A.JK", {"B.JK": {}})
