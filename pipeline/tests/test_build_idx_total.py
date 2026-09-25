"""
Tests for pipeline/appdata/build_idx_total.py.
"""
from pipeline.appdata.build_idx_total import build_idx_total


def test_sorts_by_date_and_finds_latest_min_max():
    records = [
        {"date": "2021-01-05", "idx_total_market_cap": 100},
        {"date": "2021-01-04", "idx_total_market_cap": 90},
        {"date": "2021-01-06", "idx_total_market_cap": 80},
    ]
    result = build_idx_total(records)
    assert [p["date"] for p in result["series"]] == ["2021-01-04", "2021-01-05", "2021-01-06"]
    assert result["latest"] == {"date": "2021-01-06", "value": 80}
    assert result["min"] == {"date": "2021-01-06", "value": 80}
    assert result["max"] == {"date": "2021-01-05", "value": 100}


def test_empty_input_returns_empty_series_not_an_error():
    result = build_idx_total([])
    assert result == {"series": [], "latest": None, "min": None, "max": None}
