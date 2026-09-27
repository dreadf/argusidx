"""
Tests for pipeline/stats.py: the single shared statistics implementation
every hypothesis test builds on (RULES.md process rule 3: a bug here is a
bug everywhere, so this is the highest-leverage place to have coverage).
"""
import math

import pytest

from datetime import datetime, timezone

from pipeline.stats import (
    annualized_volatility,
    closes_in_year,
    holm_bonferroni,
    log_returns,
    max_drawdown,
    median_of,
    moving_average,
    nearest_index,
    nearest_value,
    no_move_fraction,
    payout_ratio_from_totals,
    quintiles,
    rsi,
    spearman,
    total_return,
    welch_ttest,
)


def _ts(year, month, day):
    return datetime(year, month, day, tzinfo=timezone.utc).timestamp()


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


# --- Regression tests for bugs found and fixed 2026-09-07 -----------------
# Each corresponds to a real defect: distinct sequential ranks fabricating
# structure from ties, a sign-blind infinite t-statistic, a spurious
# perfect correlation at n<=2, empty quintile buckets crashing median_of,
# and quintiles() dumping its remainder entirely into the last bucket.


def test_spearman_ties_are_averaged_not_sequential():
    # Six identical x-values against a monotonic y: with proper tie
    # averaging every x-rank is the same, so rho must be 0 -- the
    # previous behavior (distinct sequential ranks) reported rho=+1.0,
    # a perfect correlation from zero information in x.
    result = spearman([1, 1, 1, 1, 1, 1], [10, 20, 30, 40, 50, 60])
    assert math.isclose(result.rho, 0.0, abs_tol=1e-9)
    assert result.t == 0.0


def test_spearman_tie_sign_does_not_flip_with_input_order():
    a = spearman([1, 1, 1, 1], [1, 2, 3, 4])
    b = spearman([1, 1, 1, 1], [4, 3, 2, 1])
    assert a.rho == b.rho == 0.0


def test_spearman_perfect_negative_correlation_has_negative_t():
    result = spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
    assert result.rho == -1.0
    assert result.t == float("-inf")  # previously always +inf regardless of sign


def test_spearman_below_n3_returns_nan_not_spurious_perfect_correlation():
    # n=2 is mathematically always rho=+-1 -- a correlation estimate with
    # no information content. Previously returned rho=1.0, t=inf; now NaN.
    for a, b in [([], []), ([1], [2]), ([1, 2], [3, 4])]:
        result = spearman(a, b)
        assert math.isnan(result.rho)
        assert math.isnan(result.t)
        assert result.n == len(a)


def test_quintiles_n_less_than_buckets_does_not_crash_median_of():
    rows = [{"v": 1}, {"v": 2}]
    buckets = quintiles(rows, "v", n_buckets=5)
    assert len(buckets) == 5
    assert sum(len(b) for b in buckets) == 2
    empty = [b for b in buckets if not b]
    assert empty  # some buckets are unavoidably empty when n < n_buckets
    assert math.isnan(median_of(empty[0], "v"))  # previously StatisticsError


def test_quintiles_remainder_spread_not_dumped_in_last_bucket():
    # n=14 into 5 buckets: 14 = 5*2 + 4, so 4 buckets get 3 and 1 gets 2 --
    # previously the last bucket absorbed the whole remainder ([2,2,2,2,6]),
    # making it 3x wider than the others and biasing any first-vs-last
    # bucket comparison (exactly what every hypothesis module here does).
    rows = [{"v": i} for i in range(14)]
    buckets = quintiles(rows, "v", n_buckets=5)
    sizes = [len(b) for b in buckets]
    assert sizes == [3, 3, 3, 3, 2]
    assert max(sizes) - min(sizes) <= 1


def test_max_drawdown_raises_on_non_positive_price():
    with pytest.raises(ValueError):
        max_drawdown([0.0, 100.0, 50.0])
    with pytest.raises(ValueError):
        max_drawdown([100.0, -5.0, 50.0])


def test_log_returns_raises_on_non_positive_price():
    with pytest.raises(ValueError):
        log_returns([100.0, 0.0, 100.0])
    with pytest.raises(ValueError):
        log_returns([100.0, -1.0, 100.0])


def test_closes_in_year_filters_by_calendar_year():
    entry = {
        "timestamps": [_ts(2023, 12, 31), _ts(2024, 1, 1), _ts(2024, 6, 1), _ts(2025, 1, 1)],
        "close": [1.0, 2.0, 3.0, 4.0],
    }
    assert closes_in_year(entry, 2024) == [2.0, 3.0]


def test_closes_in_year_uses_requested_field():
    entry = {
        "timestamps": [_ts(2024, 1, 1)],
        "close": [10.0],
        "adjclose": [9.0],
    }
    assert closes_in_year(entry, 2024, field="adjclose") == [9.0]


def test_closes_in_year_raises_on_length_mismatch():
    entry = {"timestamps": [_ts(2024, 1, 1), _ts(2024, 1, 2)], "close": [1.0]}
    with pytest.raises(ValueError):
        closes_in_year(entry, 2024)


def test_nearest_value_picks_closest_timestamp():
    entry = {
        "timestamps": [_ts(2024, 1, 1), _ts(2024, 1, 10), _ts(2024, 1, 20)],
        "close": [1.0, 2.0, 3.0],
    }
    assert nearest_value(entry, datetime(2024, 1, 12, tzinfo=timezone.utc)) == 2.0


def test_nearest_value_none_outside_max_gap_days():
    entry = {"timestamps": [_ts(2024, 1, 1)], "close": [1.0]}
    assert nearest_value(entry, datetime(2024, 2, 1, tzinfo=timezone.utc), max_gap_days=10) is None


def test_nearest_value_boundary_is_inclusive():
    entry = {"timestamps": [_ts(2024, 1, 1)], "close": [1.0]}
    target = datetime(2024, 1, 11, tzinfo=timezone.utc)  # exactly 10 days later
    assert nearest_value(entry, target, max_gap_days=10) == 1.0


def test_nearest_value_uses_requested_field():
    entry = {"timestamps": [_ts(2024, 1, 1)], "close": [10.0], "adjclose": [9.0]}
    assert nearest_value(entry, datetime(2024, 1, 1, tzinfo=timezone.utc), field="adjclose") == 9.0


def test_nearest_value_raises_on_length_mismatch():
    entry = {"timestamps": [_ts(2024, 1, 1), _ts(2024, 1, 2)], "close": [1.0]}
    with pytest.raises(ValueError):
        nearest_value(entry, datetime(2024, 1, 1, tzinfo=timezone.utc))


def test_nearest_value_raises_on_non_positive_price():
    entry = {"timestamps": [_ts(2024, 1, 1)], "close": [0.0]}
    with pytest.raises(ValueError):
        nearest_value(entry, datetime(2024, 1, 1, tzinfo=timezone.utc))


def test_nearest_index_picks_closest_timestamp():
    entry = {"timestamps": [_ts(2024, 1, 1), _ts(2024, 1, 10), _ts(2024, 1, 20)]}
    assert nearest_index(entry, datetime(2024, 1, 12, tzinfo=timezone.utc)) == 1


def test_nearest_index_none_outside_max_gap_days():
    entry = {"timestamps": [_ts(2024, 1, 1)]}
    assert nearest_index(entry, datetime(2024, 2, 1, tzinfo=timezone.utc), max_gap_days=10) is None


# --- moving_average / rsi (added for H14) ----------------------------------


def test_moving_average_basic():
    out = moving_average([1, 2, 3, 4, 5], window=3)
    assert out == [None, None, 2, 3, 4]


def test_moving_average_too_short_is_all_none():
    out = moving_average([1, 2], window=3)
    assert out == [None, None]


def test_moving_average_window_must_be_positive():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], window=0)


def test_rsi_all_gains_is_100():
    # Monotonically rising closes -> avg_loss is always 0 -> RSI pinned at 100.
    out = rsi([1, 2, 3, 4, 5, 6], period=3)
    assert out[:3] == [None, None, None]
    assert out[3:] == [100.0, 100.0, 100.0]


def test_rsi_flat_prices_is_50():
    # No price movement at all -> avg_gain and avg_loss both 0 -> RSI=50
    # (0/0 is undefined; 50 is the conventional "no signal" value).
    out = rsi([5, 5, 5, 5, 5], period=2)
    assert out[:2] == [None, None]
    assert out[2:] == [50.0, 50.0, 50.0]


def test_rsi_too_short_is_all_none():
    out = rsi([1, 2, 3], period=14)
    assert out == [None, None, None]


def test_rsi_matches_hand_calculation():
    # closes 1..15, period=14: 14 consecutive +1 deltas -> avg_gain=1,
    # avg_loss=0 -> RS=inf -> RSI=100. Only one value is defined (index 14).
    closes = list(range(1, 16))
    out = rsi(closes, period=14)
    assert out[:14] == [None] * 14
    assert out[14] == 100.0


# --- welch_ttest (added for H15) -------------------------------------------


def test_welch_ttest_identical_groups_has_zero_diff():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = welch_ttest(a, b)
    assert math.isclose(result.diff, 0.0, abs_tol=1e-9)
    assert math.isclose(result.t, 0.0, abs_tol=1e-9)
    assert result.n_a == result.n_b == 5


def test_welch_ttest_detects_a_real_mean_difference():
    a = [10.0, 11.0, 9.0, 10.5, 9.5]
    b = [1.0, 2.0, 0.5, 1.5, 0.0]
    result = welch_ttest(a, b)
    assert result.diff > 0
    assert result.t > 5  # large, obvious separation


def test_welch_ttest_insufficient_data_is_nan():
    result = welch_ttest([1.0], [1.0, 2.0, 3.0])
    assert math.isnan(result.t)
    assert math.isnan(result.diff)
    assert result.n_a == 1
    assert result.n_b == 3


# --- payout_ratio_from_totals (added for H4/H10, 2026-09-13) ---------------


def test_payout_ratio_from_totals_matches_hand_calculation():
    # BBCA 2024: total_dividend=277.5/share, earnings=54,836,305,000,000,
    # outstanding_shares=123,275,050,000 -> EPS ~= 444.83, payout ~= 0.624.
    result = payout_ratio_from_totals(277.5, 54_836_305_000_000.0, 123_275_050_000.0)
    assert math.isclose(result, 0.6238353655484264, rel_tol=1e-9)


def test_payout_ratio_from_totals_naive_division_would_be_tiny():
    # Guards against regressing to the units bug this function exists to
    # fix -- a naive dividend/earnings division is off by a factor of
    # shares outstanding (~1e-12 for BBCA), not a real payout ratio.
    naive = 277.5 / 54_836_305_000_000.0
    result = payout_ratio_from_totals(277.5, 54_836_305_000_000.0, 123_275_050_000.0)
    assert result > naive * 1e6


def test_payout_ratio_from_totals_none_for_missing_or_undefined_inputs():
    assert payout_ratio_from_totals(None, 100.0, 10.0) is None
    assert payout_ratio_from_totals(5.0, None, 10.0) is None
    assert payout_ratio_from_totals(5.0, 100.0, None) is None
    assert payout_ratio_from_totals(5.0, -100.0, 10.0) is None  # loss-making
    assert payout_ratio_from_totals(5.0, 100.0, 0.0) is None  # no shares


def test_holm_bonferroni_all_reject_when_all_tiny():
    assert holm_bonferroni([0.001, 0.002, 0.003]) == [True, True, True]


def test_holm_bonferroni_none_reject_when_all_large():
    assert holm_bonferroni([0.5, 0.6, 0.7]) == [False, False, False]


def test_holm_bonferroni_stops_at_the_first_failure():
    # Sorted: 0.01, 0.02, 0.20. Thresholds (m=3): rank1 alpha/3=.0167,
    # rank2 alpha/2=.025, rank3 alpha/1=.05. p(1)=.01 <= .0167: reject.
    # p(2)=.02 <= .025: reject. p(3)=.20 > .05: stop, do not reject.
    p = [0.02, 0.01, 0.20]
    assert holm_bonferroni(p) == [True, True, False]


def test_holm_bonferroni_is_more_conservative_than_uncorrected():
    # A single borderline p-value (0.03 < 0.05) would pass uncorrected,
    # but Holm's rank-1 threshold with m=3 is alpha/3 ~ 0.0167.
    assert holm_bonferroni([0.03, 0.9, 0.9]) == [False, False, False]


def test_holm_bonferroni_nan_never_rejected():
    p = [0.001, float("nan"), 0.002]
    result = holm_bonferroni(p)
    assert result[1] is False


def test_holm_bonferroni_matches_plain_bonferroni_at_rank_one():
    # The strictest (first) threshold in Holm's step-down IS alpha/m,
    # identical to a plain Bonferroni correction.
    p = [0.05 / 3 - 1e-6, 0.9, 0.9]
    assert holm_bonferroni(p)[0] is True
