import json
import math
from datetime import date, timedelta

import pytest

from pipeline.hypotheses import h6_foreign_list as h6


def weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


DAYS = weekdays(date(2024, 12, 2), 460)


def test_grid_is_deterministic_spaced_and_has_room_for_outcome():
    g1, g2 = h6.trading_grid(DAYS), h6.trading_grid(DAYS)
    assert g1 == g2 and g1
    assert g1[0] >= h6.GRID_START
    idx = [DAYS.index(d) for d in g1]
    assert all(b - a == h6.GRID_STEP for a, b in zip(idx, idx[1:]))
    assert idx[-1] + h6.HORIZON + 1 < len(DAYS)


def test_split_dates_boundary():
    ex, ho = h6.split_dates([date(2025, 9, 30), date(2025, 10, 1)])
    assert ex == [date(2025, 9, 30)] and ho == [date(2025, 10, 1)]


def test_t_pvalue_matches_known_values():
    # t=2.228, df=10 -> p about 0.05; t=2.0, df=10 -> about 0.0734
    assert h6._t_cdf_upper_two_sided(2.228, 10) == pytest.approx(0.05, abs=0.002)
    assert h6._t_cdf_upper_two_sided(2.0, 10) == pytest.approx(0.0734, abs=0.002)
    assert h6._t_cdf_upper_two_sided(0.0, 10) == pytest.approx(1.0, abs=1e-6)


def test_one_sample_t_and_degenerate_cases():
    r = h6.one_sample_t([1.0, 2.0, 3.0, 4.0])
    assert r["mean"] == 2.5 and r["t"] == pytest.approx(3.873, abs=0.01)
    assert math.isnan(h6.one_sample_t([1.0, 1.0, 1.0])["t"])
    assert math.isnan(h6.one_sample_t([1.0])["mean"])


def test_winsorize_bounds_clip_extremes():
    lo, hi = h6.winsorize_bounds(list(range(101)))
    assert (lo, hi) == (1, 99)


def test_date_spread_buy_minus_sell_with_clipping():
    rows = [
        {"buy": 1, "excess": 0.10},
        {"buy": 1, "excess": 0.50},  # clipped to 0.20
        {"buy": 0, "excess": -0.10},
    ]
    assert h6.date_spread(rows, -0.2, 0.2) == pytest.approx(0.15 - (-0.10))
    assert h6.date_spread([{"buy": 1, "excess": 0.1}], -1, 1) is None


def test_fetch_is_resumable_capped_and_orders_sell():
    calls = []

    def fake_get(path, params):
        calls.append(dict(params))
        return {"results": [{"symbol": "AAAA.JK"}]}

    dates = [date(2025, 2, 3), date(2025, 2, 10)]
    import tempfile, pathlib

    p = pathlib.Path(tempfile.mkdtemp()) / "l.json"
    assert h6.fetch_lists(dates, p, fake_get, max_calls=4) == 4
    assert sum("order_by" in c for c in calls) == 2
    n_before = len(calls)
    assert h6.fetch_lists(dates, p, fake_get, max_calls=4) == 0  # nothing re-billed
    assert len(calls) == n_before
    p2 = p.with_name("other.json")
    with pytest.raises(RuntimeError):
        h6.fetch_lists(dates, p2, fake_get, max_calls=3)


def synthetic(days, buy_edge):
    """Prices where buy-list stocks return `buy_edge` more over D+1..D+6."""
    d = days[10]
    px = {}
    for s, edge in (("B1.JK", buy_edge), ("S1.JK", 0.0)):
        px[s] = {x: 100.0 for x in days}
        for x in days[12:]:
            px[s][x] = 100.0 * (1 + edge)
    index_px = {x: 1000.0 for x in days}
    lists = {d.isoformat(): {"buy": [{"symbol": "B1.JK"}], "sell": [{"symbol": "S1.JK"}, {"symbol": "GONE.JK"}]}}
    return d, px, index_px, lists


def test_build_date_rows_uses_next_day_start_and_counts_missing():
    d, px, index_px, lists = synthetic(DAYS, 0.05)
    out = h6.build_date_rows(d, lists, DAYS, px, index_px)
    assert out["missing"] == 1  # GONE.JK has no prices
    by = {r["symbol"]: r for r in out["rows"]}
    assert by["B1.JK"]["excess"] == pytest.approx(0.05)
    assert by["S1.JK"]["excess"] == pytest.approx(0.0)
    assert by["B1.JK"]["buy"] == 1 and by["S1.JK"]["buy"] == 0


def test_same_day_move_is_not_in_the_outcome():
    # price jumps ON day D (the list day): must not count toward D+1..D+6
    days = DAYS
    d = days[10]
    px = {"B1.JK": {x: 100.0 for x in days}, "S1.JK": {x: 100.0 for x in days}}
    for x in days[10:]:
        px["B1.JK"][x] = 130.0  # jump at D, flat after
    index_px = {x: 1000.0 for x in days}
    lists = {d.isoformat(): {"buy": [{"symbol": "B1.JK"}], "sell": [{"symbol": "S1.JK"}]}}
    out = h6.build_date_rows(d, lists, days, px, index_px)
    assert h6.date_spread(out["rows"], -1, 1) == pytest.approx(0.0)
    assert out["rows"][0]["same_day"] == pytest.approx(0.30)  # shown as descriptive only


def test_verdict_rules():
    conf = {"mean": 0.01, "p": 0.01}
    assert h6.verdict({"mean": 0.005, "p": 0.4}, conf) == "CONFIRMED"
    assert h6.verdict({"mean": -0.005, "p": 0.4}, conf) == "NOT confirmed"  # explore sign differs
    assert h6.verdict({"mean": 0.005, "p": 0.4}, {"mean": 0.01, "p": 0.2}) == "NOT confirmed"
    assert "OPPOSITE" in h6.verdict({"mean": 0.0, "p": 1}, {"mean": -0.02, "p": 0.01})


def test_fe_regression_recovers_known_coefficient():
    import random

    rnd = random.Random(1)
    groups = []
    for g in range(30):
        base = rnd.gauss(0, 0.05)  # date effect, must be absorbed
        rows = []
        for i in range(20):
            flag = 1.0 if i < 10 else 0.0
            past = rnd.gauss(0, 0.1)
            y = base + 0.02 * flag + 0.3 * past + rnd.gauss(0, 0.01)
            rows.append((y, [flag, past]))
        groups.append(rows)
    out = h6.fe_regression(groups)
    assert out["coef"] == pytest.approx(0.02, abs=0.004)
    assert out["p"] < 0.001 and out["clusters"] == 30


def test_fe_regression_null_has_large_p_and_handles_tiny_input():
    import random

    rnd = random.Random(2)
    groups = [[(rnd.gauss(0, 0.05), [float(i < 5)]) for i in range(10)] for _ in range(25)]
    assert h6.fe_regression(groups)["p"] > 0.05
    assert math.isnan(h6.fe_regression([[(0.1, [1.0])]])["coef"])


def test_analyze_phase_excludes_empty_list_dates():
    d1 = {"date": date(2025, 2, 3), "rows": [{"buy": 1, "excess": 0.01, "beat": True, "same_day": 0.0, "past20": 0.0},
                                             {"buy": 0, "excess": 0.0, "beat": False, "same_day": 0.0, "past20": 0.0}], "missing": 0}
    d2 = {"date": date(2025, 2, 10), "rows": [], "missing": 0}
    d3 = {"date": date(2025, 2, 17), "rows": list(d1["rows"]), "missing": 1}
    d4 = {"date": date(2025, 2, 24), "rows": [{"buy": 1, "excess": 0.03, "beat": True, "same_day": 0.0, "past20": 0.0},
                                              {"buy": 0, "excess": 0.0, "beat": False, "same_day": 0.0, "past20": 0.0}], "missing": 0}
    out = h6.analyze_phase([d1, d2, d3, d4], -1, 1)
    assert out["n_dates"] == 3 and out["n_dates_with_empty_list"] == 1 and out["missing_prices"] == 1
