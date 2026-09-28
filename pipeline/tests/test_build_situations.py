"""Tests for pipeline/appdata/build_situations.py."""
from datetime import date, datetime, timezone

import pytest

from pipeline.appdata.build_situations import (
    FORWARD_TRADING_DAYS,
    build_fall,
    build_for_stock,
    build_loss_year,
    build_older_fall,
    build_earnings_more_than_doubled,
    build_earnings_two_year_decline,
    build_recent_ipo,
    build_recent_price_suspension,
    build_recent_spike,
    detect_fall_events,
    summarize,
)
from pipeline.hypotheses.m_recovery_after_fall import _detect_fall_events

AS_OF = date(2026, 9, 13)


def _ts(day_index: int) -> int:
    """Consecutive calendar days from 2025-01-01, 02:00 UTC (an IDX open)."""
    return int(datetime(2025, 1, 1, 2, tzinfo=timezone.utc).timestamp()) + day_index * 86400


def _entry(closes: list[float]) -> dict:
    return {"timestamps": [_ts(i) for i in range(len(closes))], "close": closes}


def _flat_then(closes_tail: list[float], flat_len: int = 120, flat_price: float = 100.0) -> dict:
    return _entry([flat_price] * flat_len + closes_tail)


def test_detector_matches_the_hypothesis_module():
    # The app builder duplicates the detector by design; this is the drift guard.
    series = [
        [100, 110, 90, 75, 70, 60, 120, 130, 91, 80, 200, 139, 100],
        [100] * 50,
        [100, 69, 68, 67, 101, 70, 100, 71],
        [50, 100, 70, 71, 72, 100.5, 70.2, 60],
    ]
    for closes in series:
        assert detect_fall_events(closes) == _detect_fall_events(closes)


def test_fall_recent_and_still_below_peak():
    entry = _flat_then([69.0, 60.0, 50.0])  # first close <=70 is index 120
    fall = build_fall(entry)
    assert fall is not None
    assert fall["peak_price"] == 100.0
    assert fall["trigger_price"] == 69.0
    assert fall["trading_days_since"] == 2
    assert fall["window_trading_days"] == FORWARD_TRADING_DAYS
    assert fall["last_close"] == 50.0
    assert round(fall["pct_from_peak"], 1) == -50.0
    assert fall["trigger_date"] == datetime.fromtimestamp(_ts(120), tz=timezone.utc).date().isoformat()
    # The peak is dated too, so a page can say WHICH peak (it can differ from the 52-week high).
    assert fall["peak_date"] == datetime.fromtimestamp(_ts(0), tz=timezone.utc).date().isoformat()


def test_fall_peak_date_is_the_running_peak_not_the_series_start():
    entry = _entry([100.0] * 60 + [120.0] * 60 + [83.0, 60.0])  # peak 120 set at index 60, 30%+ fall after
    fall = build_fall(entry)
    assert fall["peak_price"] == 120.0
    assert fall["peak_date"] == datetime.fromtimestamp(_ts(60), tz=timezone.utc).date().isoformat()


def test_fall_counts_from_first_crossing_not_from_the_bottom():
    # Crosses -30% at index 120, keeps sliding: the date stays the first crossing.
    fall = build_fall(_flat_then([69.0, 40.0, 20.0, 10.0]))
    assert fall["trigger_price"] == 69.0
    assert fall["trading_days_since"] == 3


def test_fall_older_than_the_window_is_not_the_situation():
    entry = _flat_then([69.0] + [60.0] * (FORWARD_TRADING_DAYS + 1))
    assert build_fall(entry) is None
    # ...but it is kept as an explanation, so a page can say why nothing shows.
    older = build_older_fall(entry)
    assert older is not None and older["trading_days_since"] == FORWARD_TRADING_DAYS + 1


def test_older_fall_is_exclusive_with_the_situation_and_needs_still_being_below_peak():
    recent = _flat_then([69.0, 60.0])
    assert build_fall(recent) is not None and build_older_fall(recent) is None
    recovered_long_ago = _flat_then([69.0] + [60.0] * 10 + [100.0] + [100.0] * (FORWARD_TRADING_DAYS + 5))
    assert build_older_fall(recovered_long_ago) is None  # back at the peak: nothing to explain
    assert build_older_fall(None) is None


def test_fall_exactly_at_the_window_edge_still_counts():
    fall = build_fall(_flat_then([69.0] + [60.0] * FORWARD_TRADING_DAYS))
    assert fall is not None
    assert fall["trading_days_since"] == FORWARD_TRADING_DAYS


def test_fall_already_recovered_is_not_the_situation():
    assert build_fall(_flat_then([69.0, 80.0, 100.0])) is None
    assert build_fall(_flat_then([69.0, 80.0, 105.0])) is None


def test_fall_shallow_dip_is_not_the_situation():
    assert build_fall(_flat_then([71.0, 75.0])) is None  # only -29%
    assert build_fall(_flat_then([70.0, 65.0])) is not None  # exactly -30% counts (<=)


def test_fall_needs_enough_history_and_ignores_bad_bars():
    assert build_fall(_entry([100.0] * 30 + [50.0])) is None  # under MIN_HISTORY_BARS
    assert build_fall(None) is None
    entry = _flat_then([69.0, 50.0])
    entry["close"][10] = None  # a missing bar is dropped, not treated as a crash to 0
    entry["close"][11] = 0.0
    fall = build_fall(entry)
    assert fall is not None and fall["trading_days_since"] == 1


def test_loss_year_only_when_annual_earnings_are_negative():
    assert build_loss_year({"earnings[2025]": -5.0}) == {"year": 2025, "net_income": -5.0}
    assert build_loss_year({"earnings[2025]": 0.0}) is None  # break-even is not a loss
    assert build_loss_year({"earnings[2025]": 3.0}) is None
    assert build_loss_year({"earnings[2024]": -3.0}) is None  # a past loss year is not "now"
    assert build_loss_year({"roe_ttm": -0.2}) is None  # ROE alone does not trigger it
    assert build_loss_year({}) is None


def _suspension(day: str, reason: str) -> dict:
    return {"date": day, "reason": reason, "pdf_url": "https://example/x.pdf"}


def test_suspension_price_increase_within_90_days():
    events = [_suspension("2026-08-12", "peningkatan harga kumulatif yang signifikan pada saham X")]
    got = build_recent_price_suspension(events, AS_OF)
    assert got == {"date": "2026-08-12", "days_ago": 32, "pdf_url": "https://example/x.pdf"}


def test_suspension_older_than_90_days_is_history_not_a_situation():
    events = [_suspension("2025-08-12", "peningkatan harga kumulatif")]  # FILM's real case
    assert build_recent_price_suspension(events, AS_OF) is None
    edge = [_suspension("2026-06-15", "peningkatan harga kumulatif")]  # exactly 90 days
    assert build_recent_price_suspension(edge, AS_OF)["days_ago"] == 90
    just_over = [_suspension("2026-06-14", "peningkatan harga kumulatif")]
    assert build_recent_price_suspension(just_over, AS_OF) is None


def test_suspension_other_reasons_do_not_trigger():
    events = [
        _suspension("2026-09-01", "penurunan harga kumulatif yang signifikan"),
        _suspension("2026-09-02", "terlambat menyampaikan laporan keuangan"),
        _suspension("2026-09-03", "cooling down"),
    ]
    assert build_recent_price_suspension(events, AS_OF) is None


def test_suspension_picks_the_most_recent_and_ignores_future_dates():
    events = [
        _suspension("2026-07-01", "peningkatan harga kumulatif"),
        _suspension("2026-09-01", "Peningkatan Harga Kumulatif"),  # case-insensitive, like H11
        _suspension("2026-09-20", "peningkatan harga kumulatif"),  # after as_of: not a real past event
    ]
    assert build_recent_price_suspension(events, AS_OF)["date"] == "2026-09-01"
    assert build_recent_price_suspension(None, AS_OF) is None
    assert build_recent_price_suspension([], AS_OF) is None


def test_ipo_within_a_year_carries_its_board():
    got = build_recent_ipo({"listing_date": "2026-03-01", "listing_board": "Acceleration"}, AS_OF)
    assert got == {"listing_date": "2026-03-01", "board": "Acceleration", "days_since": 196}


def test_ipo_older_than_a_year_or_missing_is_not_a_situation():
    assert build_recent_ipo({"listing_date": "2018-08-07", "listing_board": "Main"}, AS_OF) is None
    assert build_recent_ipo({"listing_date": "2025-09-12", "listing_board": "Main"}, AS_OF) is None  # 366 days
    assert build_recent_ipo({"listing_date": "2025-09-13", "listing_board": "Main"}, AS_OF)["days_since"] == 365
    assert build_recent_ipo({"listing_board": "Main"}, AS_OF) is None


def test_build_for_stock_and_summary_count_the_no_situation_case():
    film = {
        "symbol": "FILM.JK",
        "query_values": {"earnings[2025]": -2.5e11, "listing_date": "2018-08-07", "listing_board": "Main"},
    }
    calm = {"symbol": "CALM.JK", "query_values": {"earnings[2025]": 9.0e10, "listing_date": "2000-01-01"}}
    prices = {"FILM.JK": _flat_then([69.0, 50.0]), "CALM.JK": _entry([100.0] * 200)}
    old_suspension = [_suspension("2025-08-12", "peningkatan harga kumulatif")]

    film_out = build_for_stock(film, prices, old_suspension, AS_OF)
    assert film_out["fall"] is not None
    assert film_out["loss_year"] is not None
    assert film_out["recent_price_suspension"] is None  # a year old
    assert film_out["recent_ipo"] is None

    calm_out = build_for_stock(calm, prices, None, AS_OF)
    assert all(v is None for v in calm_out.values())

    counts = summarize({"FILM.JK": film_out, "CALM.JK": calm_out})
    assert counts == {
        "fall": 1,
        "loss_year": 1,
        "recent_price_suspension": 0,
        "recent_ipo": 0,
        "recent_spike": 0,
        "earnings_two_year_decline": 0,
        "earnings_more_than_doubled": 0,
        "long_below_peak": 0,
        "repeat_suspension": 0,
        "older_fall_not_a_situation": 0,
        "no_situation": 1,
        "universe": 2,
    }


def test_symbol_without_price_history_still_gets_the_sectors_based_situations():
    row = {"symbol": "NEW.JK", "query_values": {"earnings[2025]": -1.0, "listing_date": "2026-05-01", "listing_board": "Main"}}
    out = build_for_stock(row, {}, None, AS_OF)
    assert out["fall"] is None
    assert out["loss_year"] is not None
    assert out["recent_ipo"]["days_since"] == 135


def test_recent_spike_only_when_the_latest_jump_is_within_20_trading_days():
    fresh = _entry([100.0] * 120 + [100.0] * 5 + [145.0] + [146.0] * 3)  # +45% vs 20 bars earlier, 3 bars ago
    got = build_recent_spike(fresh)
    assert got is not None
    assert got["trading_days_since"] == 3
    assert round(got["jump_pct"]) == 45
    assert got["lookback_trading_days"] == 20
    stale = _entry([100.0] * 120 + [145.0] + [146.0] * 30)  # the jump is 30 bars old
    assert build_recent_spike(stale) is None
    assert build_recent_spike(_entry([100.0] * 200)) is None
    assert build_recent_spike(_entry([100.0] * 30 + [150.0])) is None  # under the minimum history
    assert build_recent_spike(None) is None


def test_recent_spike_threshold_is_forty_percent_inclusive():
    assert build_recent_spike(_entry([100.0] * 120 + [140.0])) is not None  # exactly +40%
    assert build_recent_spike(_entry([100.0] * 120 + [139.0])) is None


def test_earnings_two_year_decline_needs_a_profitable_start_and_two_falls():
    qv = {"earnings[2023]": 90.0, "earnings[2024]": 60.0, "earnings[2025]": 30.0}
    assert build_earnings_two_year_decline(qv) == {"year": 2025, "earnings": [90.0, 60.0, 30.0]}
    assert build_earnings_two_year_decline({**qv, "earnings[2023]": -5.0}) is None  # started from a loss
    assert build_earnings_two_year_decline({**qv, "earnings[2025]": 70.0}) is None  # rose in the last year
    assert build_earnings_two_year_decline({"earnings[2024]": 60.0, "earnings[2025]": 30.0}) is None  # a year missing


def test_earnings_more_than_doubled_is_strictly_more_than_twice_a_positive_base():
    assert build_earnings_more_than_doubled({"earnings[2024]": 10.0, "earnings[2025]": 21.0}) == {
        "year": 2025,
        "earnings": [10.0, 21.0],
    }
    assert build_earnings_more_than_doubled({"earnings[2024]": 10.0, "earnings[2025]": 20.0}) is None  # exactly 2x
    assert build_earnings_more_than_doubled({"earnings[2024]": -10.0, "earnings[2025]": 5.0}) is None  # a loss base


def test_build_long_below_peak_reports_pct_below_and_none_for_short_history():
    from pipeline.appdata.build_situations import build_long_below_peak

    assert build_long_below_peak(None) is None
    assert build_long_below_peak({"close": [100.0] * 50}) is None  # too little history
    fall = [100.0] * 20 + [60.0] * 300  # a 40% fall well over 252 bars ago, no recovery
    out = build_long_below_peak({"close": fall})
    assert out["peak_price"] == 100.0 and abs(out["pct_below_peak"] + 0.40) < 1e-9
    assert out["trading_days_since_trigger"] >= 252


def test_build_repeat_suspension_needs_two_events():
    from datetime import date

    from pipeline.appdata.build_situations import build_repeat_suspension

    assert build_repeat_suspension(None) is None
    assert build_repeat_suspension([date(2024, 1, 5)]) is None
    out = build_repeat_suspension([date(2024, 1, 5), date(2024, 6, 1), date(2025, 2, 3)])
    assert out == {"n_events": 3, "first_date": "2024-01-05", "last_date": "2025-02-03"}


def test_fall_ends_once_the_price_touched_the_old_peak_even_if_it_slipped_back():
    # Back to exactly the old peak (100, not a new high, so no new fall event), then 90.
    assert build_fall(_flat_then([69.0, 100.0, 90.0])) is None


def test_one_fall_is_never_both_situations_on_the_edge_day():
    from pipeline.appdata.build_situations import build_long_below_peak

    for extra in (FORWARD_TRADING_DAYS - 1, FORWARD_TRADING_DAYS, FORWARD_TRADING_DAYS + 1):
        entry = _flat_then([69.0] + [60.0] * extra)
        both = build_fall(entry) is not None and build_long_below_peak(entry) is not None
        assert not both, extra
        # the older-fall details (dates) exist exactly when long_below_peak does
        assert (build_older_fall(entry) is None) == (build_long_below_peak(entry) is None), extra
