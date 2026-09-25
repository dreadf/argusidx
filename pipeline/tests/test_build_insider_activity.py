"""
Tests for pipeline/appdata/build_insider_activity.py.
"""
from pipeline.appdata.build_insider_activity import build_by_symbol, build_market_summary


def _txn(symbol, timestamp):
    return {"symbol": symbol, "timestamp": timestamp}


def test_counts_buys_and_sells_per_symbol():
    buys = [_txn("A.JK", "2025-03-01T00:00:00"), _txn("A.JK", "2025-04-01T00:00:00")]
    sells = [_txn("A.JK", "2025-02-01T00:00:00")]
    result = build_by_symbol(buys, sells)
    assert result["A.JK"]["buy_count"] == 2
    assert result["A.JK"]["sell_count"] == 1
    assert result["A.JK"]["net_direction"] == "net_buying"


def test_net_direction_selling_and_balanced():
    buys = [_txn("B.JK", "2025-01-01T00:00:00")]
    sells = [_txn("B.JK", "2025-01-02T00:00:00"), _txn("B.JK", "2025-01-03T00:00:00")]
    buys += [_txn("C.JK", "2025-01-01T00:00:00")]
    sells += [_txn("C.JK", "2025-01-02T00:00:00")]
    result = build_by_symbol(buys, sells)
    assert result["B.JK"]["net_direction"] == "net_selling"
    assert result["C.JK"]["net_direction"] == "balanced"


def test_last_transaction_date_is_the_most_recent_of_either_side():
    buys = [_txn("A.JK", "2025-01-01T00:00:00")]
    sells = [_txn("A.JK", "2025-06-15T00:00:00")]
    result = build_by_symbol(buys, sells)
    assert result["A.JK"]["last_transaction_date"] == "2025-06-15"


def test_rows_with_no_symbol_are_excluded():
    buys = [{"symbol": None, "timestamp": "2025-01-01T00:00:00"}]
    result = build_by_symbol(buys, [])
    assert result == {}


def test_market_summary_counts_each_direction():
    by_symbol = {
        "A.JK": {"net_direction": "net_buying"},
        "B.JK": {"net_direction": "net_buying"},
        "C.JK": {"net_direction": "net_selling"},
        "D.JK": {"net_direction": "balanced"},
        "OUTSIDE.JK": {"net_direction": "net_buying"},
    }
    universe = {"A.JK", "B.JK", "C.JK", "D.JK", "E.JK"}
    summary = build_market_summary(by_symbol, universe)
    assert summary == {
        "universe_count": 5,
        "companies_with_activity": 4,
        "net_buying": 2,
        "net_selling": 1,
        "balanced": 1,
    }
