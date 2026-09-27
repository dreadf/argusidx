"""Tests for pipeline/hypotheses/a1_extreme_gainers.py, on synthetic data."""
from datetime import date

from pipeline.hypotheses.a1_extreme_gainers import (
    COMPARISON_END,
    MIN_ELIGIBLE,
    MIN_PRICE,
    OUTCOME_WINDOW,
    TOP_N,
    build_events,
    corporate_action_dates_from_store,
    daily_spread,
    excess_return,
    rank_day,
    split_explore_holdout,
)


def _calendar(n, start_year=2022, start_month=1, start_day=1):
    import datetime as dt

    d0 = dt.date(start_year, start_month, start_day)
    # Business-day-like: skip weekends for realism, though not required.
    out = []
    d = d0
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def test_corporate_action_dates_from_store_collects_all_three_types():
    store = {
        "w1": {
            "right_issue": [{"symbol": "A.JK", "ex_date": "2022-01-10"}],
            "stock_split": [{"symbol": "A.JK", "date": "2022-02-01"}],
            "bonus": [{"symbol": "B.JK", "ex_date": "2022-03-01"}],
        }
    }
    out = corporate_action_dates_from_store(store)
    assert out["A.JK"] == {"2022-01-10", "2022-02-01"}
    assert out["B.JK"] == {"2022-03-01"}


def test_build_events_excludes_price_floor_and_corp_action_and_gaps():
    cal = _calendar(5)
    symbol_closes = {
        "CHEAP.JK": {cal[0]: 40.0, cal[1]: 45.0},  # below MIN_PRICE on cal[1]
        "SPLIT.JK": {cal[0]: 100.0, cal[1]: 200.0},  # corp action day
        "GAP.JK": {cal[0]: 100.0},  # missing cal[1] entirely
        **{f"OK{i}.JK": {cal[0]: 100.0, cal[1]: 100.0 + i} for i in range(MIN_ELIGIBLE)},
    }
    corp_actions = {"SPLIT.JK": {cal[1]}}
    rows, stats = build_events(cal, symbol_closes, corp_actions, start=date(2022, 1, 1))
    symbols_on_day1 = {r["symbol"] for r in rows if r["date"] == cal[1]}
    assert "CHEAP.JK" not in symbols_on_day1
    assert "SPLIT.JK" not in symbols_on_day1
    assert "GAP.JK" not in symbols_on_day1
    assert stats["n_excluded_price"] == 1
    assert stats["n_excluded_corp_action"] == 1


def test_build_events_skips_thin_days():
    cal = _calendar(3)
    symbol_closes = {"A.JK": {cal[0]: 100.0, cal[1]: 110.0}}  # only 1 eligible stock, only on cal[1]
    rows, stats = build_events(cal, symbol_closes, {}, start=date(2022, 1, 1))
    assert rows == []
    # cal[1] has 1 eligible stock (below MIN_ELIGIBLE); cal[2] has 0 (no data at all): both thin.
    assert stats["skipped_thin_day"] == 2


def test_rank_day_splits_top_and_comparison():
    day_rows = [{"symbol": f"S{i}", "ret": -i / 100} for i in range(150)]  # S0 has the highest ret
    top, comparison = rank_day(day_rows)
    assert len(top) == TOP_N
    assert [r["symbol"] for r in top] == [f"S{i}" for i in range(TOP_N)]
    assert len(comparison) == COMPARISON_END - TOP_N
    assert comparison[0]["symbol"] == f"S{TOP_N}"


def test_excess_return_complete_case():
    cal = _calendar(OUTCOME_WINDOW + 5)
    t_idx = 2
    symbol_adjcloses = {"A.JK": {cal[t_idx + 1]: 100.0, cal[t_idx + OUTCOME_WINDOW]: 110.0}}
    ihsg_by_date = {cal[t_idx + 1]: 1000.0, cal[t_idx + OUTCOME_WINDOW]: 1000.0}  # flat index
    ex, status = excess_return(symbol_adjcloses, "A.JK", cal, t_idx, ihsg_by_date, {})
    assert status == "complete"
    assert abs(ex - 0.10) < 1e-9  # 10% stock return, 0% index return


def test_excess_return_carries_last_close_forward_when_exit_bar_is_missing():
    cal = _calendar(OUTCOME_WINDOW + 5)
    t_idx = 2
    entry_date = cal[t_idx + 1]
    early_exit_date = cal[t_idx + 3]  # last bar available, before the full window ends
    symbol_adjcloses = {"A.JK": {entry_date: 100.0, early_exit_date: 105.0}}
    ihsg_by_date = {d: 1000.0 for d in cal}
    ex, status = excess_return(symbol_adjcloses, "A.JK", cal, t_idx, ihsg_by_date, {})
    assert status == "missing_carried"
    assert abs(ex - 0.05) < 1e-9


def test_excess_return_no_data_at_all():
    cal = _calendar(OUTCOME_WINDOW + 5)
    ex, status = excess_return({"A.JK": {}}, "A.JK", cal, 2, {d: 1000.0 for d in cal}, {})
    assert ex is None and status == "no_data_at_all"


def test_excess_return_window_past_cache_end():
    cal = _calendar(OUTCOME_WINDOW)  # too short for a full window from index 2
    ex, status = excess_return({"A.JK": {}}, "A.JK", cal, len(cal) - 2, {}, {})
    assert ex is None and status == "window_past_cache_end"


def test_excess_return_excluded_by_a_corporate_action_anywhere_in_the_window():
    cal = _calendar(OUTCOME_WINDOW + 5)
    t_idx = 2
    entry_date, exit_date = cal[t_idx + 1], cal[t_idx + OUTCOME_WINDOW]
    symbol_adjcloses = {"A.JK": {entry_date: 100.0, exit_date: 999.0}}  # would otherwise look like a huge gain
    ihsg_by_date = {d: 1000.0 for d in cal}
    mid_window_date = cal[t_idx + 5]  # inside [t, t+21], not on entry/exit/t itself
    corp_action_dates = {"A.JK": {mid_window_date}}
    ex, status = excess_return(symbol_adjcloses, "A.JK", cal, t_idx, ihsg_by_date, corp_action_dates)
    assert ex is None and status == "corp_action_in_window"


def test_excess_return_not_excluded_by_a_corporate_action_outside_the_window():
    cal = _calendar(OUTCOME_WINDOW + 10)
    t_idx = 5
    entry_date, exit_date = cal[t_idx + 1], cal[t_idx + OUTCOME_WINDOW]
    symbol_adjcloses = {"A.JK": {entry_date: 100.0, exit_date: 110.0}}
    ihsg_by_date = {d: 1000.0 for d in cal}
    outside_date = cal[0]  # well before t
    ex, status = excess_return(symbol_adjcloses, "A.JK", cal, t_idx, ihsg_by_date, {"A.JK": {outside_date}})
    assert status == "complete" and ex is not None


def test_daily_spread_known_value():
    cal = _calendar(OUTCOME_WINDOW + 5)
    t_idx = 2
    entry_date, exit_date = cal[t_idx + 1], cal[t_idx + OUTCOME_WINDOW]
    date_index = {d: i for i, d in enumerate(cal)}
    ihsg_by_date = {entry_date: 1000.0, exit_date: 1000.0}
    day_rows = [{"symbol": f"T{i}", "ret": 1.0} for i in range(TOP_N)] + [
        {"symbol": f"C{i}", "ret": 0.01} for i in range(COMPARISON_END - TOP_N)
    ]
    symbol_adjcloses = {}
    for r in day_rows:
        # top group returns +20% excess, comparison group returns 0% excess
        gain = 0.20 if r["symbol"].startswith("T") else 0.0
        symbol_adjcloses[r["symbol"]] = {entry_date: 100.0, exit_date: 100.0 * (1 + gain)}
    result = daily_spread(cal[t_idx], day_rows, symbol_adjcloses, cal, date_index, ihsg_by_date, {})
    assert result is not None
    assert abs(result["spread"] - 0.20) < 1e-9


def test_split_explore_holdout_embargoes_a_crossing_window():
    spreads = [
        {"date": "2022-12-20", "window_end": "2023-01-15", "spread": 0.0},  # crosses -> embargoed
        {"date": "2022-11-01", "window_end": "2022-11-30", "spread": 0.0},  # explore
        {"date": "2023-01-01", "window_end": "2023-02-01", "spread": 0.0},  # holdout
    ]
    explore, holdout, dropped = split_explore_holdout(spreads)
    assert dropped == 1 and len(explore) == 1 and len(holdout) == 1
