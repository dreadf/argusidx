"""Tests for pipeline/hypotheses/_warnings_panel.py, on synthetic data."""
from datetime import date, datetime, timezone

from pipeline.hypotheses._warnings_panel import (
    MIN_HISTORY_BARS,
    attach_payout_tercile,
    earnings_declined,
    formation_index,
    month_starts,
    payout_ratio,
    sized,
    usable_year,
    w_earnings_down_2y,
    w_fell_30,
    w_long_below_peak,
    w_loss_year,
    w_near_peak_earnings_decline,
    w_spike_40_20,
    w_yield_spike,
)


def test_usable_year_boundary():
    assert usable_year(date(2022, 5, 1)) == 2021
    assert usable_year(date(2022, 4, 30)) == 2020
    assert usable_year(date(2022, 12, 31)) == 2021
    assert usable_year(date(2023, 5, 1)) == 2022


def test_month_starts_covers_every_month_inclusive():
    starts = month_starts(date(2022, 5, 1), date(2022, 8, 15))
    assert starts == [date(2022, 5, 1), date(2022, 6, 1), date(2022, 7, 1), date(2022, 8, 1)]


def _ts(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc).timestamp()


def test_formation_index_excludes_the_formation_month_itself():
    # MIN_HISTORY_BARS + a few days of genuinely increasing daily bars, then
    # one bar exactly on the formation month-start, then a couple more after.
    n_before = MIN_HISTORY_BARS + 5
    pairs = [(_ts(2022, 1, 1) + i * 86400, 100.0 + i) for i in range(n_before)]
    formation_ts = _ts(2022, 5, 1)
    pairs.append((formation_ts, 999.0))
    pairs.append((formation_ts + 86400, 1000.0))
    idx = formation_index(pairs, date(2022, 5, 1))
    assert idx is not None
    assert pairs[idx][0] < formation_ts  # last bar used is strictly before month start
    assert pairs[idx][1] != 999.0 and pairs[idx][1] != 1000.0  # never the 5-1 bar or later


def test_formation_index_none_when_padding_alone_is_too_short():
    pairs = [(_ts(2022, 4, 28), 100.0), (_ts(2022, 4, 29), 101.0)]
    assert formation_index(pairs, date(2022, 5, 1)) is None


def test_formation_index_none_below_min_history():
    pairs = [(_ts(2022, 4, 1), 100.0)] * 5  # far fewer than MIN_HISTORY_BARS
    assert formation_index(pairs, date(2022, 5, 1)) is None


def test_w_fell_30_true_only_past_the_threshold():
    assert w_fell_30([100.0, 100.0, 69.0]) is True  # 69/100 = 0.69 <= 0.70
    assert w_fell_30([100.0, 100.0, 71.0]) is False


def test_w_long_below_peak_needs_the_full_252_bar_gap():
    # A fall event triggers, but formation is too soon after it.
    closes = [100.0] + [69.0] * 100  # trigger at index 1, only ~99 bars since
    assert w_long_below_peak(closes) is False
    # Now with 252+ bars since the trigger and still below the peak.
    closes = [100.0] + [69.0] * 260
    assert w_long_below_peak(closes) is True
    # Recovered above the peak: should not fire even with enough elapsed time.
    closes = [100.0] + [69.0] * 200 + [150.0] * 60
    assert w_long_below_peak(closes) is False


def test_w_spike_40_20_compares_to_20_bars_ago():
    closes = [100.0] * 20 + [141.0]  # +41% vs 20 bars back
    assert w_spike_40_20(closes) is True
    closes = [100.0] * 20 + [139.0]
    assert w_spike_40_20(closes) is False


def test_w_loss_year():
    qv = {"earnings[2021]": -5.0, "earnings[2020]": 10.0, "earnings[2019]": 20.0}
    assert w_loss_year(qv, 2021) is True
    assert w_loss_year(qv, 2020) is False


def test_earnings_declined_direction():
    qv = {"earnings[2022]": 5.0, "earnings[2021]": 10.0, "earnings[2020]": 20.0}
    assert earnings_declined(qv, 2022) is True  # 5 < 10
    assert earnings_declined(qv, 2021) is True  # 10 < 20
    assert w_earnings_down_2y(qv, 2022) is True  # both 2022 and 2021 declined


def test_w_near_peak_earnings_decline():
    closes = [100.0, 95.0]  # within 10% of peak (95/100 = 0.95, drop 5%)
    qv = {"earnings[2022]": 5.0, "earnings[2021]": 10.0}
    assert w_near_peak_earnings_decline(closes, qv, 2022) is True
    closes_far = [100.0, 80.0]  # 20% off peak: not near-peak
    assert w_near_peak_earnings_decline(closes_far, qv, 2022) is False


def test_w_yield_spike():
    qv = {
        "total_yield[2022]": 6.0,
        "total_yield[2021]": 2.0,
        "total_yield[2020]": 2.0,
        "total_yield[2019]": 2.0,
    }
    assert w_yield_spike(qv, 2022) is True  # 6 >= 1.5 * 2
    qv2 = dict(qv, **{"total_yield[2022]": 2.5})
    assert w_yield_spike(qv2, 2022) is False


def test_payout_ratio_matches_stats_formula():
    qv = {"total_dividend[2022]": 50.0, "earnings[2022]": 1000.0, "outstanding_shares[2022]": 100.0}
    # eps = 1000/100 = 10; payout = 50/10 = 5.0
    assert payout_ratio(qv, 2022) == 5.0
    assert payout_ratio({}, 2022) is None


def test_sized_flags_a_large_share_count_jump_and_uses_the_next_year():
    qv = {
        "outstanding_shares[2021]": 100.0,
        "outstanding_shares[2022]": 200.0,  # +100%, flagged
        "outstanding_shares[2023]": 205.0,
    }
    size, flagged = sized(qv, 2022)
    assert flagged is True and size == 205.0  # takes the following year's count


def test_sized_flagged_but_no_next_year_yet_is_none():
    qv = {"outstanding_shares[2021]": 100.0, "outstanding_shares[2022]": 200.0}
    size, flagged = sized(qv, 2022)
    assert flagged is True and size is None


def test_sized_unflagged_uses_its_own_year():
    qv = {"outstanding_shares[2021]": 100.0, "outstanding_shares[2022]": 105.0}
    size, flagged = sized(qv, 2022)
    assert flagged is False and size == 105.0


def test_attach_payout_tercile_marks_only_the_top_third():
    rows = [
        {"month_start": "2022-05-01", "payout_ratio": r, "warnings": {}}
        for r in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    ]
    attach_payout_tercile(rows)
    flagged = [r["payout_ratio"] for r in rows if r["warnings"]["payout_top_tercile"]]
    assert flagged == [0.5, 0.6]  # top 2 of 6


def test_attach_payout_tercile_skips_a_too_small_month():
    rows = [{"month_start": "2022-05-01", "payout_ratio": 0.5, "warnings": {}}]
    attach_payout_tercile(rows)
    assert rows[0]["warnings"]["payout_top_tercile"] is False
