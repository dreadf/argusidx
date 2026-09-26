"""Tests for pipeline/hypotheses/h4_robustness.py."""
import random

from pipeline.hypotheses.h4_payout_dividend_cuts import build_pooled_rows
from pipeline.hypotheses.h4_robustness import (
    build_rows_incl_missing,
    mechanical_check,
    placebo,
    shuffled_ratios,
    tercile_table,
    variants,
)


def _stock(sym, sub, div, div_next, earn=1000.0, earn_next=1000.0, shares=10.0, year=2023):
    return {
        "symbol": sym,
        "query_values": {
            "sub_sector": sub,
            f"total_dividend[{year}]": div,
            f"total_dividend[{year + 1}]": div_next,
            f"earnings[{year}]": earn,
            f"earnings[{year + 1}]": earn_next,
            f"outstanding_shares[{year}]": shares,
        },
    }


def _universe(n=30):
    u = []
    for i in range(n):
        # payout ratio (div / 100): rises with i; higher payout -> cut
        div = 10.0 + 5 * i
        u.append(_stock(f"S{i}", "A" if i % 2 else "B", div, div * (0.5 if i >= n // 2 else 1.5)))
    return u


def test_known_rows_match_h4_module_exactly_and_missing_rows_are_extra():
    u = _universe() + [_stock("MISS", "A", 50.0, None)]
    ours = build_rows_incl_missing(u, [2023])
    h4 = build_pooled_rows(u, [2023])
    known = [r for r in ours if r["known"]]
    assert [(r["sym"], r["payout_ratio"], r["cut"]) for r in known] == [(r["sym"], r["payout_ratio"], r["cut"]) for r in h4]
    assert len(ours) == len(h4) + 1
    miss = [r for r in ours if not r["known"]][0]
    assert miss["cut"] == 1.0  # missing counted as a cut in the row builder


def test_variants_missing_as_cut_excluded_and_separate_bucket():
    u = _universe(30) + [_stock(f"M{i}", "A", 20.0, None) for i in range(3)]
    v = variants(build_rows_incl_missing(u, [2023]))
    assert sum(b["n"] for b in v["missing_counted_as_cut"]) == 33
    assert sum(b["n"] for b in v["missing_excluded_as_h4"]) == 30
    assert v["missing_separate_bucket"]["missing_bucket"]["n"] == 3
    # counting the missing as cuts can only raise the cut count
    assert sum(b["cuts"] for b in v["missing_counted_as_cut"]) == sum(b["cuts"] for b in v["missing_excluded_as_h4"]) + 3


def test_mechanical_check_keeps_only_earnings_not_fallen_boundary_equal_kept():
    u = [_stock(f"E{i}", "A", 10.0 + i, 5.0, earn=1000.0, earn_next=1000.0) for i in range(3)]  # equal earnings: kept
    u += [_stock(f"F{i}", "A", 10.0 + i, 5.0, earn=1000.0, earn_next=999.0) for i in range(3)]  # fell: dropped
    u += [_stock("N", "A", 10.0, 5.0, earn=1000.0, earn_next=None)]  # unreported: dropped
    t = mechanical_check(build_rows_incl_missing(u, [2023]))
    assert sum(b["n"] for b in t) == 3


def test_tercile_table_too_few_rows_is_empty():
    assert tercile_table([]) == []


def test_shuffle_stays_within_sub_sector_and_is_a_permutation():
    rows = build_rows_incl_missing(_universe(20), [2023])
    out = shuffled_ratios(rows, random.Random(1))
    for sub in ("A", "B"):
        idx = [i for i, r in enumerate(rows) if r["sub_sector"] == sub]
        assert sorted(out[i] for i in idx) == sorted(rows[i]["payout_ratio"] for i in idx)


def test_placebo_places_a_planted_effect_far_outside_the_shuffles_and_is_seeded():
    rows = [r for r in build_rows_incl_missing(_universe(60), [2023]) if r["known"]]
    a = placebo(rows, draws=200, seed=7)
    b = placebo(rows, draws=200, seed=7)
    assert a == b
    assert a["real_rho"] > 0.5 and a["draws_at_or_above_real"] == 0
    assert abs(a["placebo_mean"]) < 0.2
