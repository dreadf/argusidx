"""
Tests for pipeline/appdata/build_sector_breakdown.py.
"""
import pytest

from pipeline.appdata.build_sector_breakdown import build_sector_row, build_sectors, group_by_sector


def _row(symbol, sector, **qv):
    qv.setdefault("52_w_low_price", None)
    qv.setdefault("52_w_high_price", None)
    qv.setdefault("last_close_price", None)
    qv["sector"] = sector
    return {"symbol": symbol, "query_values": qv}


def test_group_by_sector_excludes_null_sector():
    rows = [_row("A.JK", "Financials"), _row("B.JK", None)]
    groups = group_by_sector(rows)
    assert list(groups.keys()) == ["Financials"]
    assert len(groups["Financials"]) == 1


def test_build_sector_row_computes_median_roe_and_pe_over_reporting_companies_only():
    rows = [
        _row("A.JK", "Financials", roe_ttm=0.10, pe_ttm=10),
        _row("B.JK", "Financials", roe_ttm=0.20, pe_ttm=20),
        _row("C.JK", "Financials", roe_ttm=None, pe_ttm=None),  # excluded from both medians
    ]
    result = build_sector_row("Financials", rows)
    assert result["company_count"] == 3
    assert result["roe_n"] == 2
    assert result["pe_n"] == 2
    assert result["typical_roe_pct"] == pytest.approx(15.0)  # median of 10%, 20%
    assert result["typical_pe"] == 15.0


def test_build_sector_row_null_when_nobody_reports_the_field():
    rows = [_row("A.JK", "Technology", roe_ttm=None, pe_ttm=None)]
    result = build_sector_row("Technology", rows)
    assert result["typical_roe_pct"] is None
    assert result["typical_pe"] is None
    assert result["roe_n"] == 0


def test_build_sector_row_includes_breadth():
    rows = [_row("A.JK", "Energy", **{"52_w_low_price": 100, "52_w_high_price": 200, "last_close_price": 190})]
    result = build_sector_row("Energy", rows)
    assert result["breadth"]["near_high"] == 1


def test_build_sectors_sorted_by_company_count_descending_not_by_performance():
    rows = (
        [_row(f"A{i}.JK", "Small", roe_ttm=0.50) for i in range(2)]
        + [_row(f"B{i}.JK", "Big", roe_ttm=0.01) for i in range(5)]
    )
    result = build_sectors(rows)
    assert [r["sector"] for r in result] == ["Big", "Small"]
