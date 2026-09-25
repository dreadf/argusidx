"""Tests for pipeline/hypotheses/m_recent_spike.py (definitions in EXPERIMENT.md, 2026-09-22)."""
from pipeline.hypotheses.m_recent_spike import (
    HORIZON_BARS,
    build_spike_base_rate,
    detect_spike_events,
    event_outcome,
    summarize_outcomes,
)


def test_first_close_at_plus_40_percent_over_20_bars_is_the_event():
    closes = [100.0] * 25 + [140.0, 150.0]
    assert detect_spike_events(closes) == [25]


def test_next_event_needs_40_more_bars():
    closes = [100.0] * 25 + [140.0] + [140.0] * 10 + [200.0] + [200.0] * 5
    events = detect_spike_events(closes)
    assert events == [25]  # the +43% at bar 36 is inside the 40-bar refractory period


def test_no_event_when_the_gain_is_spread_over_more_than_20_bars():
    closes = [100.0 + i for i in range(80)]  # +19 per 20 bars at most
    assert detect_spike_events(closes) == []


def test_outcome_needs_60_later_bars_and_measures_from_the_event_close():
    closes = [100.0] * 25 + [140.0] + [140.0] * 59 + [98.0]  # bar 25 event, 60th later bar = 98
    out = event_outcome(closes, 25)
    assert round(out["change"], 4) == round(98 / 140 - 1, 4)
    assert out["deep_drop"] is True  # 98 <= 0.70 * 140
    assert event_outcome(closes[: 25 + HORIZON_BARS], 25) is None  # only 59 later bars


def test_deep_drop_is_any_close_in_the_window_not_just_the_last():
    closes = [100.0] * 25 + [140.0] + [90.0] + [140.0] * 59
    out = event_outcome(closes, 25)
    assert out["deep_drop"] is True
    assert out["change"] == 0.0


def test_summary_shares_and_median():
    outcomes = [{"change": -0.2, "deep_drop": False}, {"change": 0.1, "deep_drop": False}, {"change": -0.4, "deep_drop": True}]
    s = summarize_outcomes(outcomes)
    assert s["n_events"] == 3
    assert round(s["share_below_event_close"], 4) == round(2 / 3, 4)
    assert s["median_change"] == -0.2
    assert round(s["share_deep_drop"], 4) == round(1 / 3, 4)
    assert summarize_outcomes([]) is None


def test_base_rate_counts_stocks_with_an_event_even_when_the_outcome_is_not_yet_known():
    recent = {"close": [100.0] * 120 + [150.0] * 3}  # event, but fewer than 60 later bars
    quiet = {"close": [100.0] * 200}
    out = build_spike_base_rate({"A.JK": recent, "B.JK": quiet})
    assert out["stocks_with_event"] == 1
    assert out["pooled"] is None
