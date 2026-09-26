"""Tests for pipeline/hypotheses/stress_baselines.py (synthetic data only)."""
from pipeline.hypotheses.stress_baselines import compare, payer_cut_rate
from pipeline.hypotheses._stress_common import rate


def _u(sym, **fields):
    return {"symbol": sym, "query_values": fields}


UNIVERSE = [
    _u("CUT", **{"total_dividend[2023]": 10.0, "total_dividend[2024]": 5.0}),
    _u("SAME", **{"total_dividend[2023]": 10.0, "total_dividend[2024]": 10.0}),
    _u("UP", **{"total_dividend[2023]": 10.0, "total_dividend[2024]": 12.0}),
    _u("GONE", **{"total_dividend[2023]": 10.0}),  # next year missing
    _u("NONPAYER", **{"total_dividend[2024]": 3.0}),  # no 2023 dividend: not a 2023 payer
]


def test_payer_cut_rate_missing_as_cut_versus_left_out():
    as_cut = payer_cut_rate(UNIVERSE, [2023], missing_as_cut=True)
    left_out = payer_cut_rate(UNIVERSE, [2023], missing_as_cut=False)
    assert (as_cut["count"], as_cut["n"]) == (2, 4)  # CUT and GONE
    assert (left_out["count"], left_out["n"]) == (1, 3)  # only CUT


def test_payer_cut_rate_pools_years():
    u = UNIVERSE + [_u("Y2", **{"total_dividend[2022]": 4.0, "total_dividend[2023]": 1.0})]
    r = payer_cut_rate(u, [2022, 2023], missing_as_cut=False)
    assert (r["count"], r["n"]) == (2, 4)  # 2022: Y2 cut; 2023: CUT (SAME, UP, Y2 own 2023 has no 2024 -> left out)


def test_compare_flags_intervals_that_include_zero():
    res = compare("small", rate(6, 10), "base", rate(500, 1000))
    assert res["difference"]["includes_zero"] is True
    res = compare("large", rate(900, 1000), "base", rate(500, 1000))
    assert res["difference"]["includes_zero"] is False and res["difference"]["diff"] > 0.39


def test_compare_handles_an_empty_group():
    assert compare("none", rate(0, 0), "base", rate(5, 10)) == {"label": "none", "not_computable": True}
