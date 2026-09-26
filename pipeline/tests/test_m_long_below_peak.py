"""Tests for pipeline/hypotheses/m_long_below_peak.py (definitions in EXPERIMENT.md, 2026-09-26 batch 1)."""
from pipeline.hypotheses.m_long_below_peak import (
    build_long_below_peak,
    event_result,
    in_situation_now,
    usable_closes,
)
from pipeline.hypotheses.m_recovery_after_fall import _detect_fall_events


def _series(peak_bars: int, after_trigger: list[float]) -> list[float]:
    """100 flat for `peak_bars`, then a trigger at 70 (exactly 70% of the peak), then `after_trigger`."""
    return [100.0] * peak_bars + [70.0] + after_trigger


def test_trigger_at_exactly_70_percent_is_an_event():
    closes = _series(5, [70.0] * 3)
    ev = _detect_fall_events(closes)[0]
    assert ev["trigger_idx"] == 5 and ev["peak_price"] == 100.0


def test_event_with_fewer_than_200_bars_after_trigger_plus_252_is_left_out():
    # trigger at idx 5; idx 257 = trigger+252; need last - 257 >= 200 -> last >= 457
    closes = _series(5, [70.0] * 451)  # last idx = 456 -> 199 bars after 257
    ev = _detect_fall_events(closes)[0]
    assert event_result(closes, ev) is None
    closes = _series(5, [70.0] * 452)  # last idx = 457 -> exactly 200 bars after
    assert event_result(closes, ev) is not None


def test_recovery_at_exactly_the_peak_counts_and_truncated_endpoint_is_flagged():
    closes = _series(5, [70.0] * 600)
    ev = _detect_fall_events(closes)[0]
    closes[5 + 504] = 100.0  # exactly the peak at trigger + 504
    res = event_result(closes, ev)
    assert res == {"still_below_at_252": True, "recovered_by_504": True, "truncated": False}
    short = closes[:5 + 504]  # last bar is trigger + 503, stands in for trigger + 504
    short[-1] = 99.9
    res = event_result(short, ev)
    assert res["truncated"] is True and res["recovered_by_504"] is False


def test_recovered_before_252_is_not_counted_as_still_below():
    closes = _series(5, [70.0] * 100 + [110.0] * 400)
    # a new peak at 110 arrives after the trigger; the first event's peak is 100
    ev = _detect_fall_events(closes)[0]
    res = event_result(closes, ev)
    assert res["still_below_at_252"] is False


def test_in_situation_now_needs_252_bars_since_trigger_and_still_below_peak():
    closes = _series(5, [70.0] * 252)  # last idx = 257 = trigger + 252
    assert in_situation_now(closes) is not None
    assert in_situation_now(closes[:-1]) is None  # only 251 bars since trigger
    closes[-1] = 100.0  # back at the peak (not below) -> not in the situation
    assert in_situation_now(closes) is None


def test_usable_closes_drops_missing_and_requires_100_bars():
    assert usable_closes(None) is None
    assert usable_closes({"close": [1.0] * 99}) is None
    assert len(usable_closes({"close": [1.0] * 100 + [None, 0.0, -1.0]})) == 100


def test_build_counts_stocks_and_rates():
    recovering = {"close": _series(5, [70.0] * 300 + [100.0] * 300)}
    stuck = {"close": _series(5, [70.0] * 600)}
    short = {"close": [100.0] * 50}
    out = build_long_below_peak({"A.JK": recovering, "B.JK": stuck, "C.JK": short})
    assert out["events_measurable"] == 2
    assert out["still_below_at_252"] == 2
    assert out["recovered_by_504"]["n"] == 2 and out["recovered_by_504"]["count"] == 1
    assert out["in_situation_now"] == ["B.JK"]
