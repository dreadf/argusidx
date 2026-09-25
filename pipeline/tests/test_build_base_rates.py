"""
Tests for pipeline/appdata/build_base_rates.py.
"""
from pipeline.appdata.build_base_rates import (
    _detect_fall_events,
    _percentiles_25_50_75,
    build_drawdown_rows,
    build_loss_maker_rows,
    build_loss_maker_turnaround,
    build_recovery_after_fall,
    build_recovery_rows,
    build_typical_drawdown,
    load_market_cap,
)


def test_build_loss_maker_rows_only_counts_loss_years():
    universe = [
        {"symbol": "A", "query_values": {"earnings[2021]": -100, "earnings[2022]": 50}},
        {"symbol": "B", "query_values": {"earnings[2021]": 200, "earnings[2022]": 300}},  # not a loss year
    ]
    rows = build_loss_maker_rows(universe)
    assert len(rows) == 1
    assert rows[0] == {"sym": "A", "year": 2021, "turned_around": True}


def test_build_loss_maker_rows_skips_missing_fields():
    universe = [{"symbol": "A", "query_values": {"earnings[2021]": -100}}]  # no earnings[2022]
    rows = build_loss_maker_rows(universe)
    assert rows == []


def test_build_loss_maker_turnaround_pooled_and_by_year():
    universe = [
        {"symbol": "A", "query_values": {"earnings[2021]": -1, "earnings[2022]": 1}},
        {"symbol": "B", "query_values": {"earnings[2021]": -1, "earnings[2022]": -1}},
        {"symbol": "C", "query_values": {"earnings[2022]": -1, "earnings[2023]": 1}},
    ]
    result = build_loss_maker_turnaround(universe)
    assert result["n"] == 3
    assert result["turned_around"] == 2
    assert result["pct"] == round(100 * 2 / 3, 1)
    by_year_2021 = next(y for y in result["by_year"] if y["from_year"] == 2021)
    assert by_year_2021 == {"from_year": 2021, "to_year": 2022, "n": 2, "turned_around": 1, "pct": 50.0}


def test_load_market_cap_skips_none_but_keeps_zero(tmp_path):
    path = tmp_path / "market_cap.json"
    path.write_text(
        '[{"symbol": "A", "query_values": {"market_cap": 0}}, '
        '{"symbol": "B", "query_values": {"market_cap": null}}, '
        '{"symbol": "C", "query_values": {"market_cap": 500}}]'
    )
    result = load_market_cap(path)
    assert result == {"A": 0, "C": 500}


def test_build_drawdown_rows_excludes_short_history_and_missing_market_cap():
    prices1y = {
        "SHORT.JK": {"close": [100.0] * 10},  # below MIN_TRADING_DAYS
        "NOCAP.JK": {"close": [100.0] * 200},
        "OK.JK": {"close": [100.0] * 200},
    }
    market_cap = {"OK.JK": 1000.0}  # NOCAP.JK deliberately missing
    rows = build_drawdown_rows(prices1y, market_cap)
    assert [r["sym"] for r in rows] == ["OK.JK"]


def test_percentiles_25_50_75_known_values():
    # 9 values 0..8 -> index 0.25*8=2, 0.5*8=4, 0.75*8=6
    values = [v / 100 for v in range(9)]
    result = _percentiles_25_50_75(values)
    assert result == {"n": 9, "p25_pct": 2.0, "median_pct": 4.0, "p75_pct": 6.0}


def test_build_typical_drawdown_splits_into_terciles():
    prices1y = {f"S{i}.JK": {"close": [100.0] * 130} for i in range(6)}
    # max_drawdown of a flat series is 0.0 for all - fine, this test is about
    # the tercile split, not the drawdown math itself (covered by pipeline.stats).
    market_cap = {f"S{i}.JK": float(i) for i in range(6)}
    result = build_typical_drawdown(prices1y, market_cap)
    assert result["overall"]["n"] == 6
    assert result["by_size_tercile"]["smallest"]["n"] == 2
    assert result["by_size_tercile"]["mid"]["n"] == 2
    assert result["by_size_tercile"]["largest"]["n"] == 2


def test_detect_fall_events_single_prolonged_decline_counts_once():
    # Peaks at 100, falls to 60 and stays low - must register exactly one
    # event, not one per day below threshold (the double-counting guard).
    closes = [100.0] + [60.0] * 10
    events = _detect_fall_events(closes)
    assert len(events) == 1
    assert events[0]["peak_price"] == 100.0


def test_detect_fall_events_rearms_after_genuine_new_high():
    closes = [100.0, 60.0, 61.0, 150.0, 90.0]  # falls, recovers, new peak, falls again
    events = _detect_fall_events(closes)
    assert len(events) == 2
    assert events[0]["peak_price"] == 100.0
    assert events[1]["peak_price"] == 150.0


def test_build_recovery_rows_recovered_flag():
    # trigger_idx=1 (first close <= 70% of the peak=100); forward_idx =
    # 1 + 252 = 253, which must land inside the recovered (110.0) segment
    # for this fixture to actually exercise the "recovered" branch.
    prices5y = {
        "REC.JK": {"close": [100.0] + [60.0] * 252 + [110.0] * 20},
    }
    rows = build_recovery_rows(prices5y)
    assert len(rows) == 1
    assert rows[0]["recovered"] is True


def test_build_recovery_after_fall_computes_median_gap_for_still_down_only():
    prices5y = {
        "DOWN.JK": {"close": [100.0] + [60.0] * 260},  # never recovers, stays at 60% of peak
    }
    result = build_recovery_after_fall(prices5y)
    assert result["still_below_peak"]["n"] == 1
    assert result["recovered"]["n"] == 0
    assert result["still_down_median_gap_pct"] == -40.0
