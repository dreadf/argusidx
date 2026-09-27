"""Tests for pipeline/hypotheses/r5_warning_market_state.py, on synthetic rows."""
from pipeline.hypotheses.r5_warning_market_state import did_stat, group_stats

KEYS = ["a", "b", "c"]


def _row(symbol, month_start, warnings, d, u):
    return {
        "symbol": symbol,
        "month_start": month_start,
        "warnings": dict.fromkeys(KEYS, False) | warnings,
        "d": d,
        "u": u,
    }


def test_group_stats_filters_by_count_and_market():
    stressed = {"2025-01-01": "tertekan", "2022-05-01": "normal"}
    rows = [
        _row("A", "2025-01-01", {}, 1, 0),  # 0 warnings, stressed
        _row("B", "2025-01-01", {"a": True, "b": True}, 1, 0),  # 2 warnings, stressed
        _row("C", "2022-05-01", {}, 0, 1),  # 0 warnings, normal
    ]
    du0_stressed, n0_stressed = group_stats(rows, stressed, KEYS, 0, "tertekan")
    assert du0_stressed == 1.0 and n0_stressed == 1
    du2_stressed, n2_stressed = group_stats(rows, stressed, KEYS, 2, "tertekan")
    assert du2_stressed == 1.0 and n2_stressed == 1
    du0_normal, n0_normal = group_stats(rows, stressed, KEYS, 0, "normal")
    assert du0_normal == -1.0 and n0_normal == 1


def test_group_stats_none_when_empty():
    du, n = group_stats([], {}, KEYS, 0, "tertekan")
    assert du is None and n == 0


def test_did_stat_known_value():
    stressed = {"S": "tertekan", "N": "normal"}
    rows = (
        [_row(f"A{i}", "S", {"a": True, "b": True}, 1, 0) for i in range(3)]  # 2+, stressed: D-U=1
        + [_row(f"B{i}", "S", {}, 0, 0) for i in range(3)]  # 0, stressed: D-U=0
        + [_row(f"C{i}", "N", {"a": True, "b": True}, 0, 0) for i in range(3)]  # 2+, normal: D-U=0
        + [_row(f"D{i}", "N", {}, 0, 0) for i in range(3)]  # 0, normal: D-U=0
    )
    # (1 - 0) - (0 - 0) = 1
    assert did_stat(rows, stressed, KEYS) == 1.0


def test_did_stat_none_when_a_group_is_missing():
    stressed = {"S": "tertekan"}
    rows = [_row("A", "S", {"a": True, "b": True}, 1, 0)]
    assert did_stat(rows, stressed, KEYS) is None
