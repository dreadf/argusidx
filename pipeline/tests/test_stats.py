"""
Tests for pipeline/stats.py — the single shared statistics implementation
every hypothesis test builds on (RULES.md process rule 3: a bug here is a
bug everywhere, so this is the highest-leverage place to have coverage).
"""
import math

from pipeline.stats import (
    annualized_volatility,
    log_returns,
    max_drawdown,
    median_of,
    no_move_fraction,
    quintiles,
    spearman,
    total_return,
)


def test_log_returns():
    rets = log_returns([100, 110, 121])
    assert len(rets) == 2
    assert math.isclose(rets[0], math.log(1.1), rel_tol=1e-9)
    assert math.isclose(rets[1], math.log(1.1), rel_tol=1e-9)


def test_log_returns_too_short():
    assert log_returns([100]) == []


def test_annualized_volatility_constant_growth_is_zero():
    # Constant daily log return -> zero standard deviation.
    closes = [100 * (1.01**i) for i in range(30)]
    assert math.isclose(annualized_volatility(closes), 0.0, abs_tol=1e-9)


def test_annualized_volatility_too_short_is_nan():
    assert math.isnan(annualized_volatility([100]))


def test_max_drawdown_example_from_docstring():
    # 100 -> 150 -> 60: worst drop is from the 150 peak.
    assert math.isclose(max_drawdown([100, 150, 60]), -0.6, rel_tol=1e-9)


def test_max_drawdown_monotonic_rise_is_zero():
    assert max_drawdown([100, 110, 120]) == 0.0


def test_max_drawdown_empty_is_nan():
    assert math.isnan(max_drawdown([]))


def test_total_return():
    assert math.isclose(total_return([100, 150]), 0.5, rel_tol=1e-9)


def test_total_return_too_short_is_nan():
    assert math.isnan(total_return([100]))


def test_no_move_fraction():
    # closes -> log returns [0, log(1.1), 0, 0]: 3 of 4 days didn't move.
    frac = no_move_fraction([100, 100, 110, 110, 110])
    assert math.isclose(frac, 0.75, rel_tol=1e-9)


def test_no_move_fraction_empty_is_nan():
    assert math.isnan(no_move_fraction([100]))


def test_spearman_perfect_positive_correlation():
    result = spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert math.isclose(result.rho, 1.0, rel_tol=1e-9)
    assert result.t == float("inf")
    assert result.n == 5


def test_spearman_partial_correlation_matches_hand_calculation():
    result = spearman([1, 2, 3, 4, 5], [1, 3, 2, 5, 4])
    assert math.isclose(result.rho, 0.8, rel_tol=1e-9)
    assert math.isclose(result.t, 2.3094, rel_tol=1e-4)
    assert result.n == 5


def test_quintiles_splits_evenly():
    rows = [{"v": i} for i in range(10)]
    buckets = quintiles(rows, "v", n_buckets=5)
    assert len(buckets) == 5
    assert [b["v"] for b in buckets[0]] == [0, 1]
    assert [b["v"] for b in buckets[-1]] == [8, 9]


def test_median_of():
    rows = [{"x": 1}, {"x": 3}, {"x": 2}]
    assert median_of(rows, "x") == 2
