"""Tests for pipeline/hypotheses/_stress_common.py, with known values."""
import math

from pipeline.hypotheses._stress_common import (
    cluster_bootstrap,
    cluster_bootstrap_rate,
    is_wide,
    mde_mean,
    moving_block_bootstrap,
    newcombe_diff,
    percentile,
    permutation_position,
    rate,
    t_quantile_two_sided,
    wilson,
)


def test_wilson_known_values():
    lo, hi = wilson(8, 10)
    assert abs(lo - 0.4902) < 1e-3 and abs(hi - 0.9433) < 1e-3
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 1e-3
    lo, hi = wilson(5, 10)
    assert abs(lo - 0.2366) < 1e-3 and abs(hi - 0.7634) < 1e-3
    assert wilson(0, 0) is None


def test_wilson_stays_inside_zero_one_at_the_edges():
    lo, hi = wilson(10, 10)
    assert abs(hi - 1.0) < 1e-12 and 0.0 < lo < 1.0


def test_rate_dict():
    r = rate(121, 999)
    assert r["count"] == 121 and r["n"] == 999
    assert abs(r["rate"] - 0.1211) < 1e-4
    assert abs(r["wilson_low"] - 0.1024) < 1e-3 and abs(r["wilson_high"] - 0.1428) < 1e-3
    assert rate(0, 0)["rate"] is None


def test_newcombe_matches_the_published_example():
    # Newcombe (1998), 56/70 vs 48/80: difference 0.2000, 95% interval 0.0524 to 0.3339
    d = newcombe_diff(56, 70, 48, 80)
    assert abs(d["diff"] - 0.2) < 1e-9
    assert abs(d["low"] - 0.0524) < 1e-3 and abs(d["high"] - 0.3339) < 1e-3
    assert d["includes_zero"] is False


def test_newcombe_includes_zero_for_equal_rates():
    d = newcombe_diff(5, 20, 5, 20)
    assert d["diff"] == 0 and d["includes_zero"] is True and d["low"] < 0 < d["high"]
    assert newcombe_diff(1, 0, 1, 5) is None


def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([1, 2, 3, 4], 0.0) == 1 and percentile([1, 2, 3, 4], 1.0) == 4
    assert math.isnan(percentile([], 0.5))


def test_cluster_bootstrap_is_deterministic_and_collapses_when_all_equal():
    a = cluster_bootstrap_rate({f"S{i}": (1, 1) for i in range(20)}, b=200)
    assert a["low"] == a["high"] == 1.0 and a["n_clusters"] == 20
    mixed = {f"S{i}": (i % 2, 1) for i in range(40)}
    r1 = cluster_bootstrap_rate(mixed, b=300, seed=7)
    r2 = cluster_bootstrap_rate(mixed, b=300, seed=7)
    assert r1 == r2 and r1["low"] < 0.5 < r1["high"]


def test_cluster_bootstrap_resamples_whole_clusters():
    # one stock holds 10 events, all hits; three stocks hold one miss each: a stock-level resample is very wide
    clusters = {"BIG": (10, 10), "A": (0, 1), "B": (0, 1), "C": (0, 1)}
    res = cluster_bootstrap_rate(clusters, b=500)
    assert res["n_clusters"] == 4 and res["high"] - res["low"] > 0.5


def test_cluster_bootstrap_general_stat_matches_the_point_estimate():
    clusters = {"A": [1.0, 3.0], "B": [5.0]}
    res = cluster_bootstrap(clusters, lambda s: sum(s) / len(s), b=50)
    assert res["estimate"] == 3.0


def test_moving_block_bootstrap_is_deterministic_and_collapses_when_all_equal():
    series = [1.0] * 100
    r1 = moving_block_bootstrap(series, lambda s: sum(s) / len(s), block_len=20, b=200, seed=7)
    r2 = moving_block_bootstrap(series, lambda s: sum(s) / len(s), block_len=20, b=200, seed=7)
    assert r1 == r2
    assert r1["estimate"] == 1.0 and r1["low"] == r1["high"] == 1.0


def test_moving_block_bootstrap_resample_is_always_original_length():
    series = list(range(137))  # not a multiple of block_len, exercises the truncation

    def stat(sample: list) -> float:
        assert len(sample) == len(series)
        return sum(sample) / len(sample)

    moving_block_bootstrap(series, stat, block_len=20, b=25, seed=1)


def test_moving_block_bootstrap_wider_than_iid_would_be_for_correlated_blocks():
    # Blocks of 20 alternate between "all 0" and "all 1": a plain i.i.d.
    # resample of points would average toward 0.5 with a narrow interval;
    # a block resample keeps whole runs together and stays much wider.
    series: list[float] = []
    for block in range(10):
        series.extend([float(block % 2)] * 20)
    res = moving_block_bootstrap(series, lambda s: sum(s) / len(s), block_len=20, b=1000, seed=3)
    # An i.i.d. resample of 200 near-binary points would give a width around
    # 2*1.96*sqrt(0.25/200) =~ 0.14; keeping whole 20-point blocks together
    # should land well above that.
    assert res["high"] - res["low"] > 0.25


def test_permutation_position_counts():
    r = permutation_position(1.5, [-2, -1, 0, 1, 2])
    assert r["p_upper"] == (1 + 1) / 6 and r["p_two_sided"] == (1 + 2) / 6 and r["percentile"] == 4 / 5


def test_t_quantile_known_values():
    assert abs(t_quantile_two_sided(0.05, 10) - 2.228) < 2e-3
    assert abs(t_quantile_two_sided(0.05, 9) - 2.262) < 2e-3
    assert abs(t_quantile_two_sided(0.4, 9) - 0.883) < 2e-3  # the 80th percentile of t with 9 df


def test_mde_mean_known_value():
    # n = 10, sd = 1: (2.262 + 0.883) / sqrt(10)
    assert abs(mde_mean(1.0, 10) - 0.9946) < 3e-3
    assert math.isnan(mde_mean(1.0, 2))


def test_is_wide_uses_the_20_point_rule():
    assert is_wide(0.201) and not is_wide(0.20) and not is_wide(None) and is_wide(0.1, 0.25)
