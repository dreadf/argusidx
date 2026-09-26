"""Tests for pipeline/hypotheses/m_repeat_spike_suspension.py (definitions in EXPERIMENT.md, 2026-09-26 batch 1)."""
from datetime import date

from pipeline.hypotheses.m_repeat_spike_suspension import (
    build_repeat_spike_suspension,
    first_follow_up_gap,
    is_price_increase_reason,
    price_increase_events,
)

UP = "Terjadinya peningkatan harga kumulatif yang signifikan"
UP2 = "Kenaikan Harga yang tidak wajar"
OTHER = "Penundaan penyampaian laporan keuangan"


def _s(sym, d, reason=UP):
    return {"symbol": sym, "suspension_date": d, "reason": reason}


def test_reason_matching_is_case_insensitive_and_needs_a_keyword():
    assert is_price_increase_reason(UP) and is_price_increase_reason(UP2)
    assert not is_price_increase_reason(OTHER) and not is_price_increase_reason(None)


def test_events_dedupe_same_stock_same_date_and_skip_other_reasons():
    ev = price_increase_events([_s("A.JK", "2024-01-01"), _s("A.JK", "2024-01-01", UP2), _s("A.JK", "2024-02-01", OTHER)])
    assert ev == {"A.JK": [date(2024, 1, 1)]}


def test_follow_up_boundary_365_days_inclusive_366_not():
    e = date(2024, 1, 1)
    assert first_follow_up_gap([e, date(2024, 12, 31)], e) == 365  # 2024 is a leap year: 1 Jan -> 31 Dec is 365 days
    assert first_follow_up_gap([e, date(2025, 1, 1)], e) is None  # 366 days
    assert first_follow_up_gap([e], e) is None  # the event itself is not a follow-up


def test_event_after_the_cutoff_is_not_eligible_and_cutoff_day_is():
    data = [
        _s("A.JK", "2025-09-11"),  # exactly the last eligible day, followed 10 days later
        _s("A.JK", "2025-09-21"),
        _s("B.JK", "2025-09-12"),  # one day too late: not eligible
    ]
    out = build_repeat_spike_suspension(data)
    assert out["events"] == 3 and out["stocks"] == 2
    assert out["eligible_events"] == 1
    assert out["followed_within_365d"] == 1
    assert out["followed_first_gap_within_7d"] == 0
    assert out["stocks_with_2_or_more"] == 1


def test_no_events_gives_none_share():
    out = build_repeat_spike_suspension([_s("A.JK", "2024-01-01", OTHER)])
    assert out["events"] == 0 and out["share_followed"] is None


def test_gap_over_7_days_diagnostic_boundaries():
    # events: Jan 1, Jan 8 (7 days: not over 7), Jan 16 (15 days after the first), then nothing
    out = build_repeat_spike_suspension([_s("A.JK", "2024-01-01"), _s("A.JK", "2024-01-08"), _s("A.JK", "2024-01-16")])
    # Jan 1 has Jan 16 (15d) -> yes; Jan 8 has Jan 16 (8d) -> yes; Jan 16 has none -> no
    assert out["eligible_events"] == 3 and out["followed_by_gap_over_7d"] == 2
    only_close = build_repeat_spike_suspension([_s("B.JK", "2024-01-01"), _s("B.JK", "2024-01-08")])
    assert only_close["followed_by_gap_over_7d"] == 0  # exactly 7 days does not count
    edge = build_repeat_spike_suspension([_s("C.JK", "2024-01-01"), _s("C.JK", "2024-12-31")])
    assert edge["followed_by_gap_over_7d"] == 1  # 365 days is inside


def test_quick_follow_up_diagnostic():
    out = build_repeat_spike_suspension([_s("A.JK", "2024-01-01"), _s("A.JK", "2024-01-05"), _s("A.JK", "2024-06-01")])
    assert out["eligible_events"] == 3
    assert out["followed_within_365d"] == 2  # the last event has nothing after it
    assert out["followed_first_gap_within_7d"] == 1
