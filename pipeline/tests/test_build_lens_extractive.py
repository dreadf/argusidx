"""
Tests for pipeline/appdata/build_lens_extractive.py.
"""
from pipeline.appdata.build_lens_extractive import build_lens_extractive


def test_only_entries_with_a_real_symbol_included():
    entries = [
        {"symbol": "A.JK", "company_type": "Mine Owner", "key_operation": "Mining", "commodity_type": ["Coal"]},
        {"symbol": None, "company_type": "Holding", "key_operation": "Investment", "commodity_type": ["Nickel"]},
    ]
    result = build_lens_extractive(entries)
    assert set(result.keys()) == {"A.JK"}


def test_missing_commodity_type_becomes_empty_list_not_none():
    entries = [{"symbol": "A.JK", "company_type": "Trader", "key_operation": "Coal Trading"}]
    result = build_lens_extractive(entries)
    assert result["A.JK"]["commodity_type"] == []


def test_preserves_multi_commodity_exposure():
    entries = [{"symbol": "A.JK", "company_type": "Holding", "key_operation": "Mining", "commodity_type": ["Coal", "Aluminium"]}]
    result = build_lens_extractive(entries)
    assert result["A.JK"]["commodity_type"] == ["Coal", "Aluminium"]
