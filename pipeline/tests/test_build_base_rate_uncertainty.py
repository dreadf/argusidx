"""Tests for pipeline/appdata/build_base_rate_uncertainty.py (ST0)."""
import json

import pytest

from pipeline.appdata.build_base_rate_uncertainty import (
    APP_DIR,
    assemble,
    collect_earnings,
    collect_i6,
    collect_i9,
    collect_loss_turnaround,
    entry,
)


def test_entry_wilson_only_when_no_clusters():
    e = entry("k", "s", "label", 26, 47, n_stocks=47)
    assert (e["count"], e["n"], e["n_stocks"]) == (26, 47, 47)
    assert abs(e["rate"] - 26 / 47) < 1e-12
    assert abs(e["wilson_low"] - 0.412) < 2e-3 and abs(e["wilson_high"] - 0.686) < 2e-3
    assert e["cluster_low"] is None and e["cluster_high"] is None
    assert abs(e["width_points"] - 27.4) < 0.3 and e["wide"] is True  # 47 stocks: wider than 20 points


def test_entry_narrow_interval_is_not_wide():
    e = entry("k", "s", "label", 121, 999)
    assert e["wide"] is False and e["width_points"] < 5


def test_entry_cluster_interval_can_make_a_rate_wide_when_wilson_is_not():
    clusters = {"BIG": (30, 30), **{f"S{i}": (0, 1) for i in range(30)}}  # 60 events, but one stock holds half of them
    e = entry("k", "s", "label", 30, 60, n_stocks=31, clusters=clusters)
    assert e["cluster_low"] is not None and (e["cluster_high"] - e["cluster_low"]) * 100 > 20
    assert e["wide"] is True and e["width_points"] > 20


def test_assemble_rejects_duplicate_keys_and_strips_the_key():
    a = entry("k", "s", "l", 1, 2)
    assert assemble([a]) == {"k": a} and "key" not in a
    with pytest.raises(ValueError):
        assemble([entry("k", "s", "l", 1, 2), entry("k", "s", "l", 1, 2)])


def _u(sym, **f):
    return {"symbol": sym, "query_values": f}


def test_collect_i9_counts_a_missing_next_dividend_as_a_cut():
    base = {"total_yield[2021]": 1.0, "total_yield[2022]": 1.0, "total_yield[2023]": 1.0, "total_yield[2024]": 2.0}
    universe = [
        _u("CUT", **base, **{"total_dividend[2024]": 10.0, "total_dividend[2025]": 5.0}),
        _u("GONE", **base, **{"total_dividend[2024]": 10.0}),
        _u("KEPT", **base, **{"total_dividend[2024]": 10.0, "total_dividend[2025]": 10.0}),
    ]
    (e,) = collect_i9(universe)
    assert (e["key"], e["count"], e["n"]) == ("i9_cut_Y2024", 2, 3)


def test_collect_i6_skips_cells_that_cannot_exist():
    universe = [_u("A", **{f"total_dividend[{y}]": 1.0 for y in range(2021, 2026)})]
    keys = {e["key"] for e in collect_i6(universe)}
    assert "i6_paid_again_N4_Y2024" in keys and "i6_paid_again_N4_Y2022" not in keys and "i6_paid_again_N3_Y2022" not in keys


def test_collect_loss_turnaround_pooled_and_by_year():
    universe = [
        _u("A", **{"earnings[2021]": -1, "earnings[2022]": 1}),
        _u("B", **{"earnings[2021]": -1, "earnings[2022]": -1}),
    ]
    by_key = {e["key"]: e for e in collect_loss_turnaround(universe)}
    assert (by_key["loss_turnaround_pooled"]["count"], by_key["loss_turnaround_pooled"]["n"]) == (1, 2)
    assert by_key["loss_turnaround_pooled"]["n_stocks"] == 2 and by_key["loss_turnaround_2021"]["n"] == 2


def test_collect_earnings_returns_pooled_and_year_keys():
    keys = {e["key"] for e in collect_earnings([])}
    assert "earnings_two_year_decline_rose_pooled" in keys and "earnings_more_than_doubled_gave_all_back_2024" in keys


def test_generated_file_schema_when_present():
    path = APP_DIR / "base_rate_uncertainty.json"
    if not path.exists():
        pytest.skip("data/app/base_rate_uncertainty.json not generated yet")
    data = json.loads(path.read_text())
    assert set(data) == {"as_of", "computed_on", "method", "rates"}
    required = {"situation", "label", "count", "n", "rate", "wilson_low", "wilson_high", "n_stocks", "cluster_low", "cluster_high", "width_points", "wide", "as_of"}
    for k, v in data["rates"].items():
        assert required <= set(v), k
        assert 0 <= v["wilson_low"] <= v["rate"] <= v["wilson_high"] <= 1
        assert v["wide"] == (v["width_points"] > 20)
        if v["cluster_low"] is not None:
            assert v["cluster_low"] <= v["cluster_high"]
    for k in ("c_recovered_by_trigger_plus_504", "s2_followed_within_365d", "recent_spike_pooled"):
        assert data["rates"][k]["cluster_low"] is not None and data["rates"][k]["n_stocks"]
