"""Tests for pipeline/appdata/build_commodity_context.py."""
import pytest

from pipeline.appdata.build_commodity_context import build_commodity, build_commodity_context


def _rec(date, price):
    return {"name": "X", "date": date, "price_usd_per_ton": price}


def test_change_12m_uses_point_nearest_one_year_before_latest():
    records = [_rec("2025-02-15", 100.0), _rec("2025-08-15", 120.0), _rec("2026-02-15", 90.0)]
    result = build_commodity(records)
    assert result["latest_date"] == "2026-02-15"
    assert result["year_ago_date"] == "2025-02-15"
    assert result["change_12m_pct"] == pytest.approx(-10.0)


def test_change_12m_none_when_no_point_near_a_year_back():
    records = [_rec("2026-01-01", 100.0), _rec("2026-02-15", 110.0)]
    result = build_commodity(records)
    assert result["change_12m_pct"] is None
    assert result["year_ago_date"] is None


def test_position_in_range_places_latest_between_low_and_high():
    records = [_rec("2024-01-01", 50.0), _rec("2025-02-15", 150.0), _rec("2026-02-15", 100.0)]
    result = build_commodity(records)
    assert result["range_low"] == 50.0
    assert result["range_high"] == 150.0
    assert result["position_in_range"] == pytest.approx(0.5)


def test_out_of_order_records_are_sorted_by_date():
    records = [_rec("2026-02-15", 100.0), _rec("2025-02-15", 80.0)]
    assert build_commodity(records)["latest_date"] == "2026-02-15"


def test_empty_or_all_null_records_are_skipped():
    assert build_commodity([]) is None
    assert build_commodity([{"date": "2026-01-01", "price_usd_per_ton": None}]) is None
    assert build_commodity_context({"Empty": []}) == {}
