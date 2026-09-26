"""Tests for the H18 outcome step (pipeline/hypotheses/h18_insider_buying.py), synthetic data only."""
from datetime import date, timedelta

from pipeline.hypotheses.h18_insider_buying import analyze_phase, build_outcomes, event_excess


def _weekdays(start: date, n: int) -> list[date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


CAL = _weekdays(date(2025, 1, 1), 600)
FLAT_INDEX = {d: 100.0 for d in CAL}


def _ev(sym, d, takeover=False):
    return {"sym": sym, "date": d, "event_date": d, "is_takeover": takeover, "beyond_calendar": False}


def _month_days(year: int, month: int, k: int) -> list[date]:
    return [d for d in CAL if d.year == year and d.month == month][:k]


def _step(bar: int, level: float) -> dict:
    """100 before `bar`, `level` from `bar` on."""
    return {d: (100.0 if k < bar else level) for k, d in enumerate(CAL)}


def test_start_is_the_day_after_so_the_filing_day_move_is_excluded():
    d = CAL[10]
    # jumps at bar 10 (event day) or bar 11 (day after) are before the window's start close: excluded
    for bar in (10, 11):
        assert abs(event_excess(_ev("A.JK", d), CAL, {"A.JK": _step(bar, 150.0)}, FLAT_INDEX)) < 1e-12
    # a jump on bar 12 is the first move inside the window
    assert abs(event_excess(_ev("A.JK", d), CAL, {"A.JK": _step(12, 150.0)}, FLAT_INDEX) - 0.5) < 1e-12


def test_window_is_day_after_to_20_bars_later():
    d = CAL[10]
    px = {x: 100.0 for x in CAL}
    px[CAL[12]] = 120.0  # bar 2 after the event: inside the window (start CAL[11], end CAL[31])
    px[CAL[32]] = 50.0  # one bar past the end: irrelevant
    assert abs(event_excess(_ev("A.JK", d), CAL, {"A.JK": px}, FLAT_INDEX) - 0.0) < 1e-12  # ends back at 100
    px2 = {x: 100.0 for x in CAL}
    px2[CAL[31]] = 130.0  # the end bar
    assert abs(event_excess(_ev("A.JK", d), CAL, {"A.JK": px2}, FLAT_INDEX) - 0.30) < 1e-12
    px3 = {x: 100.0 for x in CAL}
    px3[CAL[30]] = 130.0  # one bar before the end bar: not the end
    assert abs(event_excess(_ev("A.JK", d), CAL, {"A.JK": px3}, FLAT_INDEX)) < 1e-12


def _px_gain_from_start(event_day: date, gain: float) -> dict:
    """100 through the start bar (day after the event), x(1+gain) from the bar after that on: the window sees `gain`."""
    i = CAL.index(event_day)
    return {d: (100.0 if k <= i + 1 else 100.0 * (1 + gain)) for k, d in enumerate(CAL)}


def test_excess_is_stock_minus_same_window_index_return():
    d = CAL[10]
    idx = {x: (100.0 if k <= 11 else 110.0) for k, x in enumerate(CAL)}
    px = {"A.JK": _px_gain_from_start(d, 0.05)}
    assert abs(event_excess(_ev("A.JK", d), CAL, px, idx) - (0.05 - 0.10)) < 1e-12


def test_none_for_missing_prices_or_no_full_window():
    d = CAL[10]
    assert event_excess(_ev("NOPE.JK", d), CAL, {}, FLAT_INDEX) is None
    partial = _px_gain_from_start(d, 0.05)
    del partial[CAL[31]]  # the end bar
    assert event_excess(_ev("A.JK", d), CAL, {"A.JK": partial}, FLAT_INDEX) is None
    last = CAL[-5]
    assert event_excess(_ev("A.JK", last), CAL, {"A.JK": _px_gain_from_start(last, 0.05)}, FLAT_INDEX) is None
    beyond = {**_ev("A.JK", date(2030, 1, 5)), "beyond_calendar": True}
    assert event_excess(beyond, CAL, {"A.JK": {}}, FLAT_INDEX) is None


def _planted(year: int, gains: list[float]) -> tuple[list[dict], dict]:
    """One event per month (months 1..len(gains)) for a stock whose in-window gain is gains[m]."""
    events, prices = [], {}
    for m, g in enumerate(gains, start=1):
        d = _month_days(year, m, 3)[1]
        sym = f"S{year}{m}.JK"
        events.append(_ev(sym, d))
        prices[sym] = _px_gain_from_start(d, g)
    return events, prices


def test_planted_five_percent_edge_is_found_and_confirmed():
    gains = [0.04, 0.06, 0.05, 0.045, 0.055, 0.05]
    e1, p1 = _planted(2025, gains)
    e2, p2 = _planted(2026, gains)
    out = build_outcomes(e1 + e2, CAL, {**p1, **p2}, FLAT_INDEX)
    assert abs(out["holdout"]["mean"] - 0.05) < 1e-9 and out["holdout"]["p"] < 0.05
    assert out["explore"]["mean"] > 0
    assert out["verdict"] == "CONFIRMED"


def test_null_is_not_confirmed():
    gains = [0.05, -0.05, 0.03, -0.03, 0.04, -0.04]
    e1, p1 = _planted(2025, gains)
    e2, p2 = _planted(2026, gains)
    out = build_outcomes(e1 + e2, CAL, {**p1, **p2}, FLAT_INDEX)
    assert out["holdout"]["p"] > 0.05
    assert out["verdict"] == "NOT confirmed"


def test_significant_negative_holdout_is_reported_as_the_opposite():
    e1, p1 = _planted(2025, [0.01] * 3 + [0.02] * 3)
    e2, p2 = _planted(2026, [-0.05, -0.06, -0.04, -0.055, -0.045, -0.05])
    out = build_outcomes(e1 + e2, CAL, {**p1, **p2}, FLAT_INDEX)
    assert out["verdict"].startswith("OPPOSITE")


def test_month_clustering_each_month_counts_once():
    jan, feb = _month_days(2025, 1, 12), _month_days(2025, 2, 3)
    events, prices = [], {}
    for k, d in enumerate(jan[:10]):  # ten January events at +10%
        events.append(_ev(f"J{k}.JK", d))
        prices[f"J{k}.JK"] = _px_gain_from_start(d, 0.10)
    for sym, d in (("F.JK", feb[1]), ("G.JK", feb[2])):  # two February events at 0%
        events.append(_ev(sym, d))
        prices[sym] = _px_gain_from_start(d, 0.0)
    mar = _month_days(2025, 3, 3)[1]
    events.append(_ev("M.JK", mar))  # one March event at +2%
    prices["M.JK"] = _px_gain_from_start(mar, 0.02)
    res = analyze_phase([{"date": e["date"], "excess": event_excess(e, CAL, prices, FLAT_INDEX)} for e in events])
    assert res["n_months"] == 3
    assert abs(res["mean"] - 0.04) < 1e-9  # mean of month means (0.10, 0.0, 0.02), not the pooled event mean
    assert res["n_events_used"] == 13


def test_missing_prices_are_dropped_and_counted_and_takeover_split_is_reported():
    e1, p1 = _planted(2025, [0.05] * 6)
    e2, p2 = _planted(2026, [0.05] * 6)
    events = e1 + e2
    events[6]["is_takeover"] = True
    del p2[events[7]["sym"]]  # no prices for one holdout stock
    out = build_outcomes(events, CAL, {**p1, **p2}, FLAT_INDEX)
    assert out["holdout"]["n_events"] == 6 and out["holdout"]["n_dropped_missing_prices"] == 1
    assert out["holdout"]["n_events_used"] == 5 and out["holdout"]["n_months"] == 5
    assert out["holdout_without_takeover"]["n_events"] == 5
    assert out["explore"]["n_dropped_missing_prices"] == 0
    assert out["holdout"]["share_beating_index"] == 1.0
    assert abs(out["holdout"]["median_event_excess"] - 0.05) < 1e-9


def test_other_years_ignored_and_too_few_months_give_nan_p():
    e, p = _planted(2025, [0.05, 0.05])
    out = build_outcomes(e, CAL, p, FLAT_INDEX)
    assert out["explore"]["n_months"] == 2 and out["explore"]["p"] != out["explore"]["p"]  # nan
    assert out["holdout"]["n_events"] == 0
    assert out["verdict"].startswith("NOT confirmed")
