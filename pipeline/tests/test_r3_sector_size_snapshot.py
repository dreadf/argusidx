"""Tests for pipeline/hypotheses/r3_sector_size_snapshot.py, on synthetic data."""
import pytest

from pipeline.hypotheses.r3_sector_size_snapshot import _closes_by_symbol, build_rows


def test_closes_by_symbol_reads_across_pages():
    closes = {
        "2025-12-30": {
            "pages": {
                "0": [{"symbol": "AAA.JK", "date": "2025-12-30", "close": 100}],
                "30": [{"symbol": "BBB.JK", "date": "2025-12-30", "close": 200}],
            }
        }
    }
    out = _closes_by_symbol(closes, "2025-12-30")
    assert out == {"AAA.JK": 100, "BBB.JK": 200}


def test_closes_by_symbol_skips_null_close():
    closes = {"2025-12-30": {"pages": {"0": [{"symbol": "AAA.JK", "date": "2025-12-30", "close": None}]}}}
    assert _closes_by_symbol(closes, "2025-12-30") == {}


def _closes_fixture():
    return {
        "2025-12-30": {"pages": {"0": [{"symbol": "AAA.JK", "close": 100}, {"symbol": "BBB.JK", "close": 200}]}},
        "2026-06-30": {"pages": {"0": [{"symbol": "AAA.JK", "close": 150}, {"symbol": "BBB.JK", "close": 180}]}},
    }


def _universe_fixture():
    return [
        {"symbol": "AAA.JK", "query_values": {"sub_sector": "Banks", "outstanding_shares[2025]": 1000}},
        {"symbol": "BBB.JK", "query_values": {"sub_sector": "Banks", "outstanding_shares[2025]": 2000}},
    ]


def test_build_rows_computes_return_size_and_sector():
    rows = build_rows(_closes_fixture(), _universe_fixture())
    by_sym = {r["sym"]: r for r in rows}
    assert by_sym["AAA.JK"]["ret"] == pytest.approx(0.5)  # 150/100 - 1
    assert by_sym["AAA.JK"]["size"] == 1000 * 100
    assert by_sym["AAA.JK"]["sub_sector"] == "Banks"
    assert by_sym["BBB.JK"]["ret"] == pytest.approx(-0.1)  # 180/200 - 1


def test_build_rows_skips_symbol_missing_end_price():
    closes = _closes_fixture()
    closes["2026-06-30"]["pages"]["0"] = [{"symbol": "AAA.JK", "close": 150}]  # BBB dropped
    rows = build_rows(closes, _universe_fixture())
    assert {r["sym"] for r in rows} == {"AAA.JK"}


def test_build_rows_skips_symbol_missing_universe_fields():
    universe = [
        {"symbol": "AAA.JK", "query_values": {"sub_sector": "Banks", "outstanding_shares[2025]": 1000}},
        {"symbol": "BBB.JK", "query_values": {"sub_sector": None, "outstanding_shares[2025]": 2000}},
    ]
    rows = build_rows(_closes_fixture(), universe)
    assert {r["sym"] for r in rows} == {"AAA.JK"}


def test_build_rows_skips_symbol_not_in_universe():
    universe = [{"symbol": "AAA.JK", "query_values": {"sub_sector": "Banks", "outstanding_shares[2025]": 1000}}]
    rows = build_rows(_closes_fixture(), universe)
    assert {r["sym"] for r in rows} == {"AAA.JK"}
