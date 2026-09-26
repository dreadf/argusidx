"""Tests for pipeline/hypotheses/stress_h18.py (synthetic data only)."""
from datetime import date, timedelta

from pipeline.hypotheses import h18_insider_buying as h18
from pipeline.hypotheses.stress_h18 import (
    build_events,
    excess_general,
    jkse_benchmark,
    make_rows,
    month_means,
    universe_median_benchmark,
    winsorised,
)


def _weekdays(start: date, n: int) -> list[date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


CAL = _weekdays(date(2025, 1, 1), 600)
FLAT = {d: 100.0 for d in CAL}


def _filing(sym, d, takeover=False):
    return {"sym": sym, "date": d, "is_takeover": takeover}


def test_build_events_parity_with_the_frozen_rule_at_60_days():
    filings = [_filing("A.JK", CAL[i]) for i in (3, 20, 50, 70, 150)] + [_filing("B.JK", CAL[10])]
    assert build_events(filings, CAL, 60) == h18.build_events(filings, CAL)


def test_refractory_length_changes_the_number_of_events():
    filings = [_filing("A.JK", CAL[0]), _filing("A.JK", CAL[30]), _filing("A.JK", CAL[45])]  # about 0, 42 and 63 calendar days
    assert len(build_events(filings, CAL, 30)) == 3 or len(build_events(filings, CAL, 30)) == 2
    assert len(build_events(filings, CAL, 90)) == 1
    assert len(build_events(filings, CAL, 30)) >= len(build_events(filings, CAL, 60)) >= len(build_events(filings, CAL, 90))


def _ev(sym, d):
    return {"sym": sym, "date": d, "event_date": d, "is_takeover": False, "beyond_calendar": False}


def _step(bar, level):
    return {d: (100.0 if k < bar else level) for k, d in enumerate(CAL)}


def test_excess_general_matches_the_frozen_outcome_at_20_days():
    ev = _ev("A.JK", CAL[10])
    px = {"A.JK": _step(15, 130.0)}
    assert excess_general(ev, CAL, px, jkse_benchmark(FLAT), 20) == h18.event_excess(ev, CAL, px, FLAT)


def test_excess_general_horizon_and_window_end():
    ev = _ev("A.JK", CAL[10])
    px = {"A.JK": _step(14, 150.0)}  # jump on bar 14, inside a 5-day window starting at bar 11 (ends bar 16)
    assert abs(excess_general(ev, CAL, px, jkse_benchmark(FLAT), 5) - 0.5) < 1e-12
    assert excess_general(_ev("A.JK", CAL[-3]), CAL, px, jkse_benchmark(FLAT), 5) is None  # calendar ends first


def test_universe_median_benchmark_is_the_median_window_return():
    a, b = CAL[5], CAL[10]
    prices = {"X": {a: 100.0, b: 110.0}, "Y": {a: 100.0, b: 120.0}, "Z": {a: 100.0, b: 90.0}, "MISSING": {a: 100.0}}
    assert abs(universe_median_benchmark(prices)(a, b) - 0.10) < 1e-12


def test_winsorised_clips_and_keeps_missing():
    rows = [{"excess": -1.0}, {"excess": 0.1}, {"excess": 9.0}, {"excess": None}]
    out = winsorised(rows, -0.5, 0.5)
    assert [r["excess"] for r in out] == [-0.5, 0.1, 0.5, None]


def test_make_rows_and_month_means():
    d1, d2 = date(2025, 3, 3), date(2025, 4, 1)
    events = [_ev("A.JK", d1), _ev("A.JK", d2), _ev("B.JK", date(2024, 12, 2))]
    px = {"A.JK": _step(0, 100.0)}
    rows = make_rows(events, CAL, px, jkse_benchmark(FLAT))
    assert len(rows) == 2 and all(r["phase"] == "explore" for r in rows)  # the 2024 filing has no phase
    assert month_means([{"date": d1, "excess": 0.1}, {"date": d1, "excess": 0.3}, {"date": d2, "excess": None}]) == [0.2]
