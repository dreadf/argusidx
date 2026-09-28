"""
Tests for pipeline/appdata/build_market_condition.py.
"""
import pytest

from pipeline.appdata.build_market_condition import distance_distribution, ihsg_condition, percentile_rank
from pipeline.hypotheses.t1_market_state import BURN_IN_DAYS


def _dates(n):
    return [f"d{i:04d}" for i in range(n)]


def test_percentile_rank_counts_ties_as_at_or_below():
    assert percentile_rank([1.0, 2.0, 3.0, 4.0], 2.0) == 50.0
    assert percentile_rank([1.0, 2.0, 3.0, 4.0], 4.0) == 100.0


def test_percentile_rank_rejects_empty_history():
    with pytest.raises(ValueError):
        percentile_rank([], 1.0)


def test_ihsg_condition_needs_the_burn_in():
    with pytest.raises(ValueError):
        ihsg_condition(_dates(BURN_IN_DAYS - 1), [100.0] * (BURN_IN_DAYS - 1))


def test_ihsg_condition_finds_peak_and_days_since():
    # rise to a peak at index 300, then fall 20% and stay there
    closes = [100.0 + i * 0.1 for i in range(301)] + [104.0] * 60
    dates = _dates(len(closes))
    out = ihsg_condition(dates, closes)
    assert out["peak_date"] == dates[300]
    assert out["days_since_peak"] == 60
    assert out["pct_from_peak"] == pytest.approx(104.0 / 130.0 - 1)
    assert out["date"] == dates[-1]


def test_ihsg_condition_labels_a_deep_fall_below_ma200_as_tertekan():
    closes = [100.0 + i * 0.1 for i in range(301)] + [104.0] * 60
    out = ihsg_condition(_dates(len(closes)), closes)
    assert out["pct_vs_ma200"] < 0
    assert out["rule"]["below_peak_and_ma200"] is True
    assert out["state"] == "tertekan"


def test_ihsg_condition_labels_a_steady_rise_as_normal():
    closes = [100.0 * (1.0005 ** i) for i in range(400)]
    out = ihsg_condition(_dates(len(closes)), closes)
    assert out["state"] == "normal"
    assert out["days_since_peak"] == 0
    assert out["rule"]["below_peak_and_ma200"] is False


def test_distance_distribution_bins_by_ten_points():
    out = distance_distribution([0.0, -0.05, -0.1, -0.35, -0.3, -0.95, -1.0])
    # 0.0 and -0.05 -> bin 0; -0.1 -> bin 1; -0.3 and -0.35 -> bin 3; -0.95 and -1.0 -> last bin
    assert out["bins"] == [2, 1, 0, 2, 0, 0, 0, 0, 0, 2]
    assert out["n"] == 7
    assert out["n_down_30_or_more"] == 4
    assert out["median"] == -0.3
