"""
Tests for pipeline/appdata/build_ipo_boards.py.
"""
from datetime import datetime, timezone

from pipeline.appdata.build_ipo_boards import (
    DATA_AS_OF,
    _board_stats,
    _parse_listings,
    build_phase,
    build_rows,
)


def test_parse_listings_excludes_pre_2021_and_missing_board():
    universe = [
        {"symbol": "OLD", "query_values": {"listing_date": "2019-01-01", "listing_board": "Main"}},
        {"symbol": "NOBOARD", "query_values": {"listing_date": "2022-01-01"}},
        {"symbol": "OK", "query_values": {"listing_date": "2022-01-01", "listing_board": "Main"}},
    ]
    result = _parse_listings(universe)
    assert [ev["sym"] for ev in result] == ["OK"]
    assert result[0]["year"] == "2022"


def _flat_entry(price: float, days: int = 800):
    # One price per day for `days` days starting 2021-01-01, so nearest_value
    # can find a point near any listing date + horizon within the window.
    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    timestamps = [int((start.timestamp()) + i * 86400) for i in range(days)]
    return {"timestamps": timestamps, RETURN_FIELD_STUB: [price] * days}


RETURN_FIELD_STUB = "adjclose"


def test_build_rows_computes_return_from_listing_price():
    listings = [{"sym": "A", "board": "Main", "t0": datetime(2022, 1, 1, tzinfo=timezone.utc), "year": "2022"}]
    entry = _flat_entry(100.0)
    # Bump the price after ~180 days so the +180d return is nonzero and checkable.
    entry["adjclose"] = [100.0] * 180 + [150.0] * (800 - 180)
    rows = build_rows(listings, {"A": entry})
    assert len(rows) == 1
    assert rows[0]["board"] == "Main"
    assert rows[0]["ret_180d"] is not None


def test_build_rows_excludes_horizons_past_data_as_of():
    # Listed one day before DATA_AS_OF - the 180/365/720d horizons all fall
    # after DATA_AS_OF and must come back None, not be silently estimated.
    listings = [{"sym": "A", "board": "Main", "t0": DATA_AS_OF, "year": "2026"}]
    entry = _flat_entry(100.0)
    rows = build_rows(listings, {"A": entry})
    # No usable horizon at all -> excluded entirely (`usable` stays False).
    assert rows == []


def test_board_stats_negative_rate_and_median():
    rows = [
        {"board": "Main", "ret_180d": -0.5},
        {"board": "Main", "ret_180d": 0.1},
        {"board": "Main", "ret_180d": -0.2},
    ]
    stats = _board_stats(rows, "Main", 180)
    assert stats["n"] == 3
    assert stats["negative_rate_pct"] == round(100 * 2 / 3, 1)
    assert stats["median_return_pct"] == -20.0


def test_board_stats_none_when_no_data():
    assert _board_stats([], "Main", 180) is None


def test_build_phase_welch_t_requires_min_group_size():
    # Only 3 rows per board - below MIN_GROUP_SIZE (10), so Welch-t must be
    # None rather than computed on an underpowered/misleading sample.
    rows = [{"board": "Acceleration", "ret_180d": -0.1, "ret_365d": None, "ret_720d": None}] * 3
    rows += [{"board": "Main", "ret_180d": 0.1, "ret_365d": None, "ret_720d": None}] * 3
    phase = build_phase(rows)
    assert phase["horizons"]["180d"]["acceleration_vs_main_welch_t"] is None
