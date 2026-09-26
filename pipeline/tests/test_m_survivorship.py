"""Tests for pipeline/hypotheses/m_survivorship.py."""
from pipeline.hypotheses.m_survivorship import build_survivorship, is_delisting_reason


def test_reason_keywords_case_insensitive():
    assert is_delisting_reason("Rencana voluntary DELISTING saham")
    assert is_delisting_reason("Penghapusan Pencatatan Efek")
    assert is_delisting_reason("perubahan status (Go Private)")
    assert not is_delisting_reason("peningkatan harga")
    assert not is_delisting_reason(None)


def test_counts_events_symbols_absent_and_cache_gaps():
    susp = [
        {"symbol": "A.JK", "reason": "delisting"},
        {"symbol": "A.JK", "reason": "go private"},  # same symbol, second event
        {"symbol": "B.JK", "reason": "penghapusan pencatatan"},
        {"symbol": "C.JK", "reason": "peningkatan harga"},
        {"symbol": None, "reason": "delisting"},
    ]
    universe = [{"symbol": "A.JK"}, {"symbol": "C.JK"}, {"symbol": "D.JK"}]
    out = build_survivorship(susp, universe, {"A.JK": {}}, {"A.JK": {}, "C.JK": {}})
    assert out["delisting_events"] == 3
    assert out["distinct_symbols"] == 2
    assert out["symbols_absent_from_universe"] == 1 and out["absent_symbols"] == ["B.JK"]
    assert out["universe_missing_from_5y_cache"] == 2
    assert out["universe_missing_from_1y_cache"] == 1
