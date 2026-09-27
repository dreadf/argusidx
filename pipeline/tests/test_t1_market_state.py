"""Tests for pipeline/hypotheses/t1_market_state.py, on synthetic series."""
from pipeline.hypotheses.t1_market_state import (
    BURN_IN_DAYS,
    OUTCOME_WINDOW,
    Formation,
    build_formations,
    compute_states,
    diff_in_diff,
    expanding_percentile,
    realised_vol_20,
    split_explore_holdout,
)


def _dates(n: int, start_year: int = 2019) -> list[str]:
    """n synthetic ISO dates, one per day (calendar gaps don't matter to this
    module -- it only ever indexes by trading-day position)."""
    from datetime import date, timedelta

    d0 = date(start_year, 1, 1)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def test_states_are_none_before_burn_in():
    closes = [100.0] * 400
    states = compute_states(closes)
    assert all(s is None for s in states[: BURN_IN_DAYS - 1])
    assert states[BURN_IN_DAYS - 1] is not None


def test_flat_series_is_never_tertekan():
    """A perfectly flat price never falls 10% from its own peak and has zero
    volatility, so it can never satisfy either tertekan condition."""
    closes = [100.0] * 400
    states = compute_states(closes)
    assert all(s == "normal" for s in states if s is not None)


def test_a_real_drawdown_below_the_moving_average_is_tertekan():
    # 300 days flat at 100 (burns in and fills the 200-day MA with 100s),
    # then a sustained drop to 80 (-20%, safely below the -10% threshold)
    # held long enough that the 200-day MA itself drops below the current
    # price's shadow... actually: MA200 lags, so staying at 80 eventually
    # pulls the MA below the peak but the current price (80) still sits
    # below whatever the (still-elevated) MA is, satisfying condition (a).
    closes = [100.0] * 300 + [80.0] * 100
    states = compute_states(closes)
    # The days right after the drop: peak is still 100, price is 80 (-20%,
    # past -10%), and MA200 is still pulled up by the earlier 100s -- so
    # price < MA200 holds too.
    assert states[305] == "tertekan"


def test_realised_vol_is_none_until_window_fills():
    closes = [100.0 + i for i in range(30)]
    vol = realised_vol_20(closes)
    assert all(v is None for v in vol[:20])
    assert vol[20] is not None


def test_expanding_percentile_uses_only_past_values():
    # values grow monotonically: the expanding max (q=1.0) at index i must
    # equal max(values[0..i]), never a later, larger value.
    values = [float(i) for i in range(10)]
    out = expanding_percentile(values, 1.0)
    assert out[0] is None  # only one value seen: needs >=2 to report anything
    for i in range(1, 10):
        assert out[i] == max(values[: i + 1])


def test_build_formations_detects_a_fall_and_a_rise():
    n = 5 + 1 + OUTCOME_WINDOW + 5  # formation day at index 5, room after its window
    dates = _dates(n)
    closes = [100.0] * n
    closes[5] = 100.0  # formation day, base = 100
    closes[6 : 6 + OUTCOME_WINDOW] = [94.0] * OUTCOME_WINDOW  # -6%: satisfies A
    states = [None] * 5 + ["normal"] + [None] * (n - 6)
    formations, dropped_end = build_formations(dates, closes, states)
    assert dropped_end == 0
    assert len(formations) == 1
    assert formations[0].a == 1
    assert formations[0].b == 0


def test_split_explore_holdout_embargoes_a_crossing_window():
    dates = ["2022-12-20", "2022-12-21", "2022-12-22", "2022-12-23", "2022-12-24",
             "2022-12-25", "2022-12-26", "2022-12-27", "2022-12-28", "2022-12-29",
             "2022-12-30", "2023-01-02", "2023-01-03"]
    # A 3-day outcome window for this test (small, to keep the fixture short).
    import pipeline.hypotheses.t1_market_state as t1
    old_window = t1.OUTCOME_WINDOW
    t1.OUTCOME_WINDOW = 3
    try:
        # Formation at index 9 (2022-12-29): window ends at index 12 (2023-01-03),
        # which is >= HOLDOUT_START -> must be embargoed out of explore.
        formations = [Formation(date=dates[9], state="normal", a=0, b=0)]
        explore, holdout, dropped = t1.split_explore_holdout(formations, dates)
        assert dropped == 1 and explore == [] and holdout == []
    finally:
        t1.OUTCOME_WINDOW = old_window


def test_split_explore_holdout_keeps_a_holdout_formation():
    dates = ["2022-12-30", "2023-01-02", "2023-01-03", "2023-01-04"]
    formations = [Formation(date="2023-01-02", state="normal", a=0, b=0)]
    explore, holdout, dropped = split_explore_holdout(formations, dates)
    assert dropped == 0 and holdout == formations and explore == []


def test_diff_in_diff_known_value():
    formations = [
        Formation(date="d1", state="tertekan", a=1, b=0),
        Formation(date="d2", state="tertekan", a=1, b=0),
        Formation(date="d3", state="normal", a=0, b=0),
        Formation(date="d4", state="normal", a=0, b=1),
    ]
    # tertekan: mean A=1, mean B=0 -> A-B=1. normal: mean A=0, mean B=0.5 -> A-B=-0.5.
    # diff = 1 - (-0.5) = 1.5
    assert diff_in_diff(formations) == 1.5


def test_diff_in_diff_none_when_a_group_is_empty():
    formations = [Formation(date="d1", state="tertekan", a=1, b=0)]
    assert diff_in_diff(formations) is None
