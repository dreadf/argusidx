"""
Tests for pipeline/appdata/build_rankings.py.
"""
from pipeline.appdata.build_rankings import (
    build_biggest_daily_moves,
    build_furthest_below_52w_high,
    build_lowest_free_float,
    build_mcap_change,
)


def _row(symbol, high=None, current=None, free_float=None, mcap_change=None, name="Test Co"):
    return {
        "symbol": symbol,
        "company_name": name,
        "query_values": {
            "52_w_high_price": high,
            "last_close_price": current,
            "free_float": free_float,
            "yearly_mcap_change": mcap_change,
        },
    }


def test_sorts_most_negative_first():
    rows = [
        _row("A.JK", high=100, current=90),   # -10%
        _row("B.JK", high=100, current=50),   # -50%
        _row("C.JK", high=100, current=95),   # -5%
    ]
    result = build_furthest_below_52w_high(rows)
    assert [r["symbol"] for r in result] == ["B.JK", "A.JK", "C.JK"]


def test_excludes_rows_missing_either_price():
    rows = [
        _row("A.JK", high=100, current=90),
        _row("B.JK", high=None, current=90),
        _row("C.JK", high=100, current=None),
    ]
    result = build_furthest_below_52w_high(rows)
    assert [r["symbol"] for r in result] == ["A.JK"]


def test_excludes_zero_high_to_avoid_division_by_zero():
    rows = [_row("A.JK", high=0, current=10)]
    assert build_furthest_below_52w_high(rows) == []


def test_ties_broken_alphabetically_by_ticker():
    rows = [
        _row("Z.JK", high=100, current=50),
        _row("A.JK", high=100, current=50),
    ]
    result = build_furthest_below_52w_high(rows)
    assert [r["symbol"] for r in result] == ["A.JK", "Z.JK"]


def test_lowest_free_float_sorts_ascending_and_excludes_nulls():
    rows = [
        _row("A.JK", free_float=0.5),
        _row("B.JK", free_float=0.001),
        _row("C.JK", free_float=None),
    ]
    result = build_lowest_free_float(rows)
    assert [r["symbol"] for r in result] == ["B.JK", "A.JK"]


def test_mcap_change_keeps_increases_and_decreases_as_separate_lists():
    rows = [
        _row("A.JK", mcap_change=2.0),   # +200%
        _row("B.JK", mcap_change=-0.5),  # -50%
        _row("C.JK", mcap_change=None),  # excluded
    ]
    result = build_mcap_change(rows)
    assert result["evaluable_count"] == 2
    assert [r["symbol"] for r in result["increases"]] == ["A.JK", "B.JK"]
    assert [r["symbol"] for r in result["decreases"]] == ["B.JK", "A.JK"]


def _move_row(symbol, change):
    return {"symbol": symbol, "company_name": "Test Co", "query_values": {"daily_close_change": change}}


def test_biggest_daily_moves_sorts_by_absolute_size_mixing_directions():
    rows = [_move_row("A.JK", 0.05), _move_row("B.JK", -0.20), _move_row("C.JK", 0.10), _move_row("D.JK", None)]
    result = build_biggest_daily_moves(rows)
    assert [r["symbol"] for r in result] == ["B.JK", "C.JK", "A.JK"]
    assert result[0]["daily_close_change"] == -0.20


def test_biggest_daily_moves_ties_by_ticker_and_caps_at_100():
    rows = [_move_row("B.JK", 0.1), _move_row("A.JK", -0.1)] + [_move_row(f"Z{i}.JK", 0.01) for i in range(150)]
    result = build_biggest_daily_moves(rows)
    assert [r["symbol"] for r in result[:2]] == ["A.JK", "B.JK"]
    assert len(result) == 100
