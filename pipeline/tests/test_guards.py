"""
Tests for pipeline/guards.py.
"""
from datetime import date

import pytest

from pipeline.guards import (
    SECTORS_DATA_FLOOR,
    assert_within_data_floor,
    is_known_ticker,
)


def test_data_floor_rejects_earlier_date():
    with pytest.raises(ValueError):
        assert_within_data_floor(date(2020, 12, 31))


def test_data_floor_accepts_floor_date():
    assert_within_data_floor(SECTORS_DATA_FLOOR)  # must not raise


def test_data_floor_accepts_later_date():
    assert_within_data_floor(date(2024, 1, 1))  # must not raise


def test_known_ticker_case_insensitive():
    assert is_known_ticker("BBCA.JK")
    assert is_known_ticker("bbca.jk")


def test_unknown_ticker_rejected():
    assert not is_known_ticker("NOTAREALTICKER.JK")


def test_glob_ignores_non_dated_files(tmp_path, monkeypatch):
    """Regression: a loose free_float_*.json glob would let a
    non-dated file (e.g. a backup) win by lexicographic sort order.
    The glob must only match the YYYY-MM-DD dated filename pattern."""
    import json

    import pipeline.guards as guards

    monkeypatch.setattr(guards, "DATA_RAW", tmp_path)
    monkeypatch.setattr(guards, "_KNOWN_TICKERS", None)

    (tmp_path / "free_float_2026-01-01.json").write_text(
        json.dumps([{"symbol": "REAL.JK", "company_name": "Real", "free_float": 0.5}])
    )
    # Sorts AFTER the dated file lexicographically, but must not be picked up.
    (tmp_path / "free_float_zzz_backup.json").write_text(
        json.dumps([{"symbol": "FAKE.JK", "company_name": "Fake", "free_float": 0.5}])
    )

    assert guards.is_known_ticker("REAL.JK")
    assert not guards.is_known_ticker("FAKE.JK")

    monkeypatch.setattr(guards, "_KNOWN_TICKERS", None)  # don't leak cache to other tests
