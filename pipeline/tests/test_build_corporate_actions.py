"""Tests for pipeline/appdata/build_corporate_actions.py."""
import pytest

from pipeline.appdata.build_corporate_actions import build_agms, build_corporate_actions, build_dividends

UNIVERSE = [{"symbol": "A.JK", "query_values": {"last_close_price": 1000.0, "dividend_yield_avg": 0.03}}]


def test_dividends_merge_overlapping_types_on_symbol_and_ex_date():
    rows = [
        {"symbol": "A.JK", "ex_date": "2026-09-25", "dividend_amount": None, "dividend_yield": None},
        {"symbol": "A.JK", "ex_date": "2026-09-25", "dividend_amount": 50.0},
    ]
    result = build_dividends(rows, {r["symbol"]: r for r in UNIVERSE})
    assert len(result["A.JK"]) == 1
    assert result["A.JK"][0]["amount"] == 50.0


def test_dividend_implied_yield_uses_last_close_and_is_not_compared_with_annual_average():
    rows = [{"symbol": "A.JK", "ex_date": "2026-09-25", "dividend_amount": 50.0}]
    event = build_dividends(rows, {r["symbol"]: r for r in UNIVERSE})["A.JK"][0]
    assert event["implied_yield"] == pytest.approx(0.05)
    assert "own_avg_yield" not in event


def test_dividend_without_amount_or_price_has_no_implied_yield():
    rows = [{"symbol": "B.JK", "ex_date": "2026-09-25", "dividend_amount": None}]
    event = build_dividends(rows, {})["B.JK"][0]
    assert event["implied_yield"] is None


def test_cancelled_agm_is_flagged_not_hidden():
    rows = [
        {"symbol": "A.JK", "agm_date": "2026-09-30", "agm_time": "10:00:00", "agm_place": "Dibatalkan"},
        {"symbol": "A.JK", "agm_date": "2026-10-05", "agm_time": "10:00:00", "agm_place": "Jl. Sudirman"},
    ]
    events = build_agms(rows)["A.JK"]
    assert [e["cancelled"] for e in events] == [True, False]


def test_only_companies_with_events_appear_and_all_event_kinds_default_to_empty():
    response = {"agm": [{"symbol": "A.JK", "agm_date": "2026-09-30", "agm_place": "x"}]}
    result = build_corporate_actions(response, UNIVERSE)
    assert list(result) == ["A.JK"]
    assert result["A.JK"]["dividends"] == []
    assert result["A.JK"]["stock_splits"] == []
