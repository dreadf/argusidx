"""Tests for the H18 event rule and counts (pipeline/hypotheses/h18_insider_buying.py). No outcome code exists yet."""
from datetime import date, datetime, timedelta, timezone

from pipeline.hypotheses.h18_insider_buying import (
    build_events,
    count_events,
    has_follow_up,
    load_filings,
    next_trading_day,
    phase_of,
    trading_days_from_entry,
)


def _weekdays(start: date, n: int) -> list[date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


CAL = _weekdays(date(2025, 1, 1), 600)


def _f(sym, d, takeover=False):
    return {"sym": sym, "date": d, "is_takeover": takeover}


def test_non_trading_day_shifts_to_the_next_trading_day():
    assert next_trading_day(date(2025, 1, 4), CAL) == date(2025, 1, 6)  # Saturday -> Monday
    assert next_trading_day(date(2025, 1, 6), CAL) == date(2025, 1, 6)  # a trading day stays
    assert next_trading_day(date(2030, 1, 1), CAL) is None  # beyond the calendar


def test_first_filing_is_the_event_and_the_shifted_date_is_used():
    ev = build_events([_f("A.JK", date(2025, 1, 4))], CAL)  # Saturday
    assert len(ev) == 1 and ev[0]["event_date"] == date(2025, 1, 6) and ev[0]["date"] == date(2025, 1, 4)


def test_refractory_60_calendar_days_boundary():
    first = date(2025, 2, 3)  # Monday
    at_60 = first + timedelta(days=60)  # Friday 2025-04-04: inside the window
    at_61 = first + timedelta(days=61)  # Saturday -> shifts to Monday 2025-04-07 (64 days after)
    ev = build_events([_f("A.JK", first), _f("A.JK", at_60)], CAL)
    assert [e["event_date"] for e in ev] == [first]
    ev = build_events([_f("A.JK", first), _f("A.JK", at_61)], CAL)
    assert len(ev) == 2 and ev[1]["event_date"] == date(2025, 4, 7)


def test_day_60_is_inside_and_day_61_on_a_trading_day_is_an_event():
    first = date(2025, 2, 7)  # Friday
    day60, day61 = first + timedelta(days=60), first + timedelta(days=61)  # Tue 2025-04-08, Wed 2025-04-09
    assert day60.weekday() < 5 and day61.weekday() < 5
    assert len(build_events([_f("A.JK", first), _f("A.JK", day60)], CAL)) == 1
    assert len(build_events([_f("A.JK", first), _f("A.JK", day61)], CAL)) == 2


def test_skipped_filing_does_not_restart_the_clock():
    first = date(2025, 2, 3)
    filings = [_f("A.JK", first), _f("A.JK", first + timedelta(days=40)), _f("A.JK", first + timedelta(days=70))]
    ev = build_events(filings, CAL)
    # the day-40 filing is skipped; the day-70 filing is more than 60 days after the first event
    assert len(ev) == 2


def test_same_day_duplicates_and_other_stocks_are_independent():
    d = date(2025, 3, 3)
    ev = build_events([_f("A.JK", d), _f("A.JK", d), _f("B.JK", d)], CAL)
    assert sorted(e["sym"] for e in ev) == ["A.JK", "B.JK"]


def test_refractory_uses_the_shifted_date():
    first = date(2025, 2, 7)  # Friday
    sat_inside = date(2025, 4, 5)  # Saturday -> Monday 2025-04-07, 59 days after: not an event
    sat_outside = date(2025, 4, 12)  # Saturday -> Monday 2025-04-14, 66 days after: an event
    assert len(build_events([_f("A.JK", first), _f("A.JK", sat_inside)], CAL)) == 1
    assert len(build_events([_f("A.JK", first), _f("A.JK", sat_outside)], CAL)) == 2


def test_filing_beyond_the_calendar_is_kept_and_flagged():
    ev = build_events([_f("A.JK", date(2030, 1, 5))], CAL)
    assert len(ev) == 1 and ev[0]["beyond_calendar"] is True and ev[0]["event_date"] == date(2030, 1, 5)


def test_phase_uses_the_filing_year_not_the_shifted_year():
    ev = build_events([_f("A.JK", date(2025, 12, 31))], _weekdays(date(2025, 12, 31), 10))
    assert phase_of(ev[0]) == "explore"
    assert phase_of({"date": date(2026, 1, 1)}) == "holdout"
    assert phase_of({"date": date(2024, 12, 31)}) is None


def test_counts_per_phase_power_rule_and_takeover_split():
    filings = [_f(f"E{i}.JK", date(2025, 3, 3)) for i in range(100)]
    filings += [_f(f"H{i}.JK", date(2026, 3, 2), takeover=(i == 0)) for i in range(99)]
    counts = count_events(build_events(filings, CAL))
    assert counts["explore"]["events"] == 100 and counts["explore"]["enough_for_power_rule"] is True
    assert counts["holdout"]["events"] == 99 and counts["holdout"]["enough_for_power_rule"] is False
    assert counts["holdout"]["takeover_tag"] == 1 and counts["holdout"]["without_takeover_tag"] == 98
    assert counts["power_rule_met"] is False
    filings.append(_f("H99.JK", date(2026, 3, 2)))
    assert count_events(build_events(filings, CAL))["power_rule_met"] is True


def _entry(days: list[date]) -> dict:
    ts = [int(datetime(d.year, d.month, d.day, 2, tzinfo=timezone.utc).timestamp()) for d in days]
    return {"timestamps": ts, "close": [1.0] * len(days), "adjclose": [1.0] * len(days)}


def test_has_follow_up_needs_bar_20_after_the_next_bar():
    days = _weekdays(date(2025, 1, 1), 30)
    entry = _entry(days)
    # event on days[0]: window starts at days[1], ends at days[21]
    assert has_follow_up(entry, days[0]) is True
    assert has_follow_up(entry, days[8]) is True  # days[9] .. days[29]: exactly enough
    assert has_follow_up(entry, days[9]) is False  # would need days[30]
    assert has_follow_up(None, days[0]) is False
    assert trading_days_from_entry(entry) == days


def test_count_events_with_prices_reports_price_and_window_availability():
    days = _weekdays(date(2025, 1, 1), 60)
    prices = {"A.JK": _entry(days)}
    filings = [_f("A.JK", days[0]), _f("B.JK", days[0]), _f("A.JK", date(2025, 3, 20), True)]
    counts = count_events(build_events(filings, days), prices)
    assert counts["explore"]["events"] == 3
    assert counts["explore"]["with_price_history"] == 2
    assert counts["explore"]["with_full_20_day_window"] == 1  # the March filing has < 21 bars left


def test_load_filings_reads_symbol_date_and_takeover_tag(tmp_path):
    p = tmp_path / "f.jsonl"
    p.write_text(
        '{"symbol":"A.JK","timestamp":"2025-01-02T15:27:00","tags":["investment","takeover"]}\n'
        '{"symbol":"B.JK","timestamp":"2026-09-11T21:34:31","tags":null}\n'
        '{"symbol":null,"timestamp":"2026-09-11T21:34:31","tags":[]}\n'
    )
    rows = load_filings(p)
    assert rows == [
        {"sym": "A.JK", "date": date(2025, 1, 2), "is_takeover": True},
        {"sym": "B.JK", "date": date(2026, 9, 11), "is_takeover": False},
    ]
