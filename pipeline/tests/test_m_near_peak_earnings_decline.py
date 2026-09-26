"""Tests for pipeline/hypotheses/m_near_peak_earnings_decline.py (definitions in EXPERIMENT.md, 2026-09-26 batch 1)."""
from datetime import datetime, timedelta, timezone

from pipeline.hypotheses.m_near_peak_earnings_decline import (
    build_near_peak_earnings_decline,
    earnings_declined,
    near_peak_on,
    summarize,
)

CUTOFF = datetime(2024, 5, 1, 23, 59, 59, tzinfo=timezone.utc)


def _entry(days: list[str], closes: list[float], adj: list[float] | None = None) -> dict:
    ts = [int(datetime.strptime(d, "%Y-%m-%d").replace(hour=2, tzinfo=timezone.utc).timestamp()) for d in days]
    return {"timestamps": ts, "close": closes, "adjclose": adj if adj is not None else closes}


def test_near_peak_boundary_exactly_ten_percent_counts():
    e = _entry(["2024-04-01", "2024-04-30"], [100.0, 90.0])
    assert near_peak_on(e, CUTOFF) is True
    e = _entry(["2024-04-01", "2024-04-30"], [100.0, 89.99])
    assert near_peak_on(e, CUTOFF) is False


def test_near_peak_ignores_bars_after_the_cutoff_and_uses_last_bar_on_or_before():
    e = _entry(["2024-04-01", "2024-05-01", "2024-05-02"], [100.0, 95.0, 300.0])
    assert near_peak_on(e, CUTOFF) is True  # the 300 on 2 May is in the future
    assert near_peak_on(_entry(["2024-06-01"], [100.0]), CUTOFF) is None  # no bar yet


def test_earnings_declined_needs_both_reported_and_strict_decline():
    assert earnings_declined({"earnings[2023]": 9, "earnings[2022]": 10}, 2023)
    assert not earnings_declined({"earnings[2023]": 10, "earnings[2022]": 10}, 2023)
    assert not earnings_declined({"earnings[2023]": None, "earnings[2022]": 10}, 2023)
    assert not earnings_declined({"earnings[2023]": 9}, 2023)


def test_summarize_shares_and_strictly_greater_than_median():
    s = summarize([-0.1, 0.05, 0.10], [0.05, 0.05, 0.05])
    assert s["n"] == 3 and s["negative"] == 1
    assert s["beat_median"] == 1  # 0.05 equals the median, not a beat
    assert summarize([], [])["share_negative"] is None


def _daily(start: str, n: int, base: float, step: float) -> tuple[list[str], list[float]]:
    d0 = datetime.strptime(start, "%Y-%m-%d")
    days = [(d0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]
    return days, [base + step * i for i in range(n)]


def test_build_end_to_end_for_one_year():
    # window for Y=2023: 1 May 2024 -> 4 Sep 2024. Series run 1 Jan .. 30 Sep 2024.
    days, up = _daily("2024-01-01", 274, 100.0, 0.5)  # rising: near its running max on 1 May
    flat = [100.0] * 274
    days2, down = _daily("2024-01-01", 274, 200.0, -0.5)  # falling: far below max later, but check at 1 May
    universe = [
        {"symbol": "UP.JK", "query_values": {"earnings[2023]": 5, "earnings[2022]": 10}},  # declined, near peak
        {"symbol": "FLAT.JK", "query_values": {"earnings[2023]": 5, "earnings[2022]": 10}},  # declined, at max (equal)
        {"symbol": "DOWN.JK", "query_values": {"earnings[2023]": 5, "earnings[2022]": 10}},  # declined, far from max
        {"symbol": "GROW.JK", "query_values": {"earnings[2023]": 15, "earnings[2022]": 10}},  # growing -> no trigger
    ]
    prices = {
        "UP.JK": _entry(days, up),
        "FLAT.JK": _entry(days, flat),
        "DOWN.JK": _entry(days2, down),
        "GROW.JK": _entry(days, up),
    }
    out = build_near_peak_earnings_decline(universe, prices)
    y = out["by_year"][2023]
    # DOWN is 0.5*121 = 60.5 below 200 on 1 May (30% below) -> not near peak; UP and FLAT trigger.
    assert y["n"] == 2
    assert y["stocks_with_return"] == 4
    assert out["pooled"]["n"] == 2
    assert out["by_year"][2022]["n"] == 0  # no window bars in 2023
