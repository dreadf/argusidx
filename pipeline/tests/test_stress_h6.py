"""Tests for pipeline/hypotheses/stress_h6.py (synthetic data only)."""
from datetime import date, timedelta

from pipeline.hypotheses import h6_foreign_list as h6
from pipeline.hypotheses.stress_h6 import (
    date_rows,
    excluded_review_dates,
    jkse_benchmark,
    permutation_test,
    phase_spread_test,
    select_all,
    select_large_net,
    select_top,
)


def _weekdays(start: date, n: int) -> list[date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


DAYS = _weekdays(date(2025, 1, 1), 400)
D = DAYS[100]


def _item(sym, net):
    return {"symbol": sym, "net_foreign_inflow": net}


LISTS = {
    D.isoformat(): {
        "buy": [_item("B1", 50), _item("B2", 40), _item("B3", 30), _item("B4", 20)],
        "sell": [_item("S1", -5), _item("S2", -50), _item("S3", -40), _item("S4", -10)],
    }
}


def _prices(returns: dict[str, float]) -> dict[str, dict[date, float]]:
    """Each symbol is flat at 100 until D+1, then `100 * (1 + r)` from D+2 on."""
    i = DAYS.index(D)
    return {s: {d: (100.0 if k <= i + 1 else 100.0 * (1 + r)) for k, d in enumerate(DAYS)} for s, r in returns.items()}


INDEX = {d: 100.0 for d in DAYS}
RETS = {"B1": 0.10, "B2": 0.10, "B3": 0.0, "B4": 0.0, "S1": -0.1, "S2": -0.1, "S3": 0.0, "S4": 0.0}


def test_date_rows_parity_with_the_frozen_builder_at_5_days():
    px = _prices(RETS)
    mine = date_rows(D, LISTS, DAYS, px, jkse_benchmark(INDEX), h6.HORIZON)
    ref = h6.build_date_rows(D, LISTS, DAYS, px, INDEX)
    assert [(r["symbol"], r["buy"], r["excess"]) for r in mine["rows"]] == [(r["symbol"], r["buy"], r["excess"]) for r in ref["rows"]]


def test_date_rows_returns_none_when_the_calendar_ends():
    assert date_rows(DAYS[-3], LISTS, DAYS, {}, jkse_benchmark(INDEX), 5) is None


def test_select_top_uses_net_order_for_both_lists():
    assert [x["symbol"] for x in select_top(2)(LISTS[D.isoformat()]["buy"], "buy")] == ["B1", "B2"]
    assert [x["symbol"] for x in select_top(2)(LISTS[D.isoformat()]["sell"], "sell")] == ["S2", "S3"]  # most negative first
    assert select_all(LISTS[D.isoformat()]["buy"], "buy") == LISTS[D.isoformat()]["buy"]


def test_select_large_net_keeps_only_above_the_median_size():
    kept = [x["symbol"] for x in select_large_net(LISTS[D.isoformat()]["sell"], "sell")]
    assert kept == ["S2", "S3"]  # |net| 50 and 40 against a median of 25
    assert [x["symbol"] for x in select_large_net(LISTS[D.isoformat()]["buy"], "buy")] == ["B1", "B2"]
    assert select_large_net([], "buy") == []


def test_excluded_review_dates_are_the_last_three_trading_days_of_the_month():
    out = excluded_review_dates(DAYS)
    feb = [d for d in DAYS if d.year == 2025 and d.month == 2]
    assert set(feb[-3:]) <= out and feb[-4] not in out
    assert not any(d.month in (1, 3, 4, 6) for d in out)


def test_phase_spread_test_splits_phases_and_winsorises():
    per_date = [
        {"date": date(2025, 3, 3), "rows": [{"buy": 1, "excess": 0.2}, {"buy": 0, "excess": 0.0}], "missing": 0},
        {"date": date(2025, 4, 1), "rows": [{"buy": 1, "excess": 0.1}, {"buy": 0, "excess": 0.0}], "missing": 0},
        {"date": date(2025, 5, 2), "rows": [{"buy": 1, "excess": 0.3}, {"buy": 0, "excess": 0.0}], "missing": 0},
        {"date": date(2025, 11, 3), "rows": [{"buy": 1, "excess": -0.1}, {"buy": 0, "excess": 0.0}], "missing": 0},
    ]
    res = phase_spread_test(per_date)
    assert res["explore"]["n_dates"] == 3 and abs(res["explore"]["mean"] - 0.2) < 1e-9
    assert res["holdout"]["n_dates"] == 1 and res["holdout"]["p"] != res["holdout"]["p"]  # n < 3: nan


def test_permutation_test_places_a_perfectly_separated_signal_in_the_tail_and_is_deterministic():
    rows = []
    for k in range(8):  # eight dates where the buy list always beats the sell list by 5 points
        rows.append({"date": date(2025, 2, 3) + timedelta(days=k), "rows": [{"buy": 1, "excess": 0.05 + 0.001 * i} for i in range(5)] + [{"buy": 0, "excess": 0.0 + 0.001 * i} for i in range(5)]})
    phase_rows = {"explore": rows, "holdout": []}
    a = permutation_test(phase_rows, -1.0, 1.0, b=300, seed=5)
    assert a["explore"]["real"] > 0.04 and a["explore"]["p_upper"] < 0.01 and a["explore"]["n_dates"] == 8
    assert a["explore"] == permutation_test(phase_rows, -1.0, 1.0, b=300, seed=5)["explore"]
    assert a["holdout"]["n_dates"] == 0  # an empty phase is reported, not a crash
