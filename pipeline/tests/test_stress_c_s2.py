"""Tests for pipeline/hypotheses/stress_c_s2.py (synthetic data only)."""
import random
from datetime import date, timedelta

from pipeline.hypotheses.m_recovery_after_fall import _detect_fall_events
from pipeline.hypotheses.stress_c_s2 import (
    below_peak_events,
    c_clusters,
    c_rate,
    detect_falls,
    first_event_rows,
    first_per_stock,
    followed,
    s2_events,
    s2_rate,
    size_terciles,
    top_event_stocks,
    window_baseline,
)


def test_detect_falls_matches_the_frozen_detector_at_70_percent():
    rng = random.Random(3)
    closes = [100.0]
    for _ in range(600):
        closes.append(max(1.0, closes[-1] * (1 + rng.uniform(-0.06, 0.06))))
    ours = [(e["peak_price"], e["trigger_idx"]) for e in detect_falls(closes, 0.70)]
    theirs = [(e["peak_price"], e["trigger_idx"]) for e in _detect_fall_events(closes)]
    assert ours == theirs and len(ours) > 0


def test_detect_falls_threshold_is_a_parameter():
    closes = [100.0, 79.0, 79.0]
    assert len(detect_falls(closes, 0.80)) == 1 and len(detect_falls(closes, 0.70)) == 0


def _dates(n: int) -> list[date]:
    return [date(2021, 1, 1) + timedelta(days=i) for i in range(n)]


def test_below_peak_events_wait_and_recovery():
    # peak 100 for 5 bars, trigger at 70, then flat 70, recovery to 100 at trigger + 252 + 252
    closes = [100.0] * 5 + [70.0] * 701
    closes[5 + 252 + 252] = 100.0
    m, ev = below_peak_events(_dates(len(closes)), closes, 0.70, 252)
    assert m == 1 and len(ev) == 1 and ev[0]["recovered"] is True and ev[0]["truncated"] is False
    # wait 126: judged at trigger + 126 + 252 = idx 383, still 70 -> not recovered
    m, ev = below_peak_events(_dates(len(closes)), closes, 0.70, 126)
    assert m == 1 and ev[0]["recovered"] is False


def test_below_peak_events_left_out_when_too_few_bars_remain():
    closes = [100.0] * 5 + [70.0] * 300  # last idx 304, trigger 5, wait idx 257, only 47 bars after
    assert below_peak_events(_dates(len(closes)), closes, 0.70, 252) == (0, [])


def test_first_per_stock_and_clusters():
    rows = [
        {"sym": "A", "recovered": True, "trigger_date": date(2022, 1, 1)},
        {"sym": "A", "recovered": False, "trigger_date": date(2023, 1, 1)},
        {"sym": "B", "recovered": False, "trigger_date": date(2022, 6, 1)},
    ]
    assert [r["sym"] for r in first_per_stock(rows)] == ["A", "B"]
    assert c_rate(rows)["count"] == 1 and c_rate(rows)["n"] == 3
    assert c_clusters(rows) == {"A": (1, 2), "B": (0, 1)}


def test_size_terciles_split_by_cap():
    cap = {f"S{i}": float(i + 1) for i in range(9)}
    t = size_terciles(cap, list(cap) + ["NOCAP"])
    assert t["S0"] == "smallest" and t["S4"] == "mid" and t["S8"] == "largest" and "NOCAP" not in t


def test_followed_is_strictly_after_and_within_window():
    d = date(2025, 1, 10)
    assert not followed([d], d, 365)  # the event itself does not count
    assert followed([d, d + timedelta(days=365)], d, 365)
    assert not followed([d, d + timedelta(days=366)], d, 365)


def test_s2_events_respect_the_eligibility_cutoff():
    events = {"A": [date(2025, 1, 10), date(2025, 3, 1)], "B": [date(2025, 9, 12)]}
    rows = s2_events(events)  # cutoff = 2026-09-11 minus 365 days = 2025-09-11
    assert {(r["sym"], r["date"]) for r in rows} == {("A", date(2025, 1, 10)), ("A", date(2025, 3, 1))}
    assert s2_rate(rows)["count"] == 1  # only the first is followed
    assert first_event_rows(events)[0] == {"sym": "A", "date": date(2025, 1, 10), "followed": True}
    assert s2_events(events, 730) == []  # nothing is old enough for a two-year window


def test_top_event_stocks_ties_broken_alphabetically_and_reported():
    ev = {"C": [1] * 3, "B": [1] * 3, "A": [1] * 2, "D": [1] * 2, "E": [1]}
    top, tied = top_event_stocks(ev, 3)
    assert top == ["B", "C", "A"] and tied == ["A", "D"]


def test_window_baseline_counts_stocks_with_an_event_in_the_window():
    events = {"A": [date(2025, 1, 8)], "B": [date(2025, 1, 8), date(2026, 1, 1)]}
    b = window_baseline(events)
    assert b["n_stocks"] == 2 and b["start_first"] == "2025-01-08" and b["start_last"] == "2025-09-11"
    # on the first start day A's own event is the start (not after it), B's later event is inside the window
    assert b["min_share"] <= b["mean_share"] <= b["max_share"] and b["max_share"] <= 1.0
    assert b["mean_share"] >= 0.5
