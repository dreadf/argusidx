"""Tests for pipeline/hypotheses/r2a_warning_count.py, on synthetic rows."""
from datetime import datetime, timezone

from pipeline.hypotheses.r2a_warning_count import (
    HOLDOUT_START,
    MIN_CELL_GROUP,
    attach_terciles,
    cell_weighted_du_by_bucket,
    cell_weighted_du_for_champion,
    cell_weighted_du_two_plus,
    choose_champion_warning,
    compute_outcomes,
    count_bucket,
    qualifying_cells,
    split_explore_holdout,
    warning_count,
)


def _row(symbol, month_start, formation_idx, warnings, size=None, vol_60=None):
    return {
        "symbol": symbol,
        "month_start": month_start,
        "formation_idx": formation_idx,
        "size": size,
        "vol_60": vol_60,
        "warnings": dict.fromkeys(["a", "b", "c"], False) | warnings,
    }


def test_count_bucket_caps_at_max():
    assert count_bucket(0) == 0
    assert count_bucket(2) == 2
    assert count_bucket(3) == 3
    assert count_bucket(7) == 3


def test_warning_count_counts_only_the_given_keys():
    row = _row("X", "2022-05-01", 0, {"a": True, "b": True, "c": False})
    assert warning_count(row, ["a", "b", "c"]) == 2
    assert warning_count(row, ["a"]) == 1


def test_compute_outcomes_detects_fall_and_rise_and_drops_short_windows():
    from pipeline.hypotheses.r2a_warning_count import OUTCOME_WINDOW

    def ts(day_offset):
        return datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() + day_offset * 86400

    # symbol A: complete window, a 30%+ fall inside it
    closes_a = [100.0] * 5 + [69.0] * OUTCOME_WINDOW
    entry_a = {"timestamps": [ts(i) for i in range(len(closes_a))], "close": closes_a}
    # symbol B: window runs past the end of the series -> dropped
    closes_b = [100.0] * 5 + [100.0] * 10
    entry_b = {"timestamps": [ts(i) for i in range(len(closes_b))], "close": closes_b}

    prices = {"A.JK": entry_a, "B.JK": entry_b}
    rows = [
        _row("A.JK", "2022-05-01", 4, {}),
        _row("B.JK", "2022-05-01", 4, {}),
    ]
    kept, dropped_end = compute_outcomes(rows, prices, suspensions={})
    assert dropped_end == 1
    assert len(kept) == 1
    assert kept[0]["symbol"] == "A.JK"
    assert kept[0]["d"] == 1
    assert kept[0]["u"] == 0


def test_compute_outcomes_flags_a_suspension_inside_the_window():
    from pipeline.hypotheses.r2a_warning_count import OUTCOME_WINDOW

    def ts(day_offset):
        return datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() + day_offset * 86400

    closes = [100.0] * (5 + OUTCOME_WINDOW)
    entry = {"timestamps": [ts(i) for i in range(len(closes))], "close": closes}
    rows = [_row("A.JK", "2022-05-01", 4, {})]
    # A suspension a few days into the window.
    kept, _dropped = compute_outcomes(rows, {"A.JK": entry}, suspensions={"A.JK": ["2022-01-10"]})
    assert kept[0]["l"] == 1
    kept2, _ = compute_outcomes(rows, {"A.JK": entry}, suspensions={"A.JK": ["2019-01-01"]})
    assert kept2[0]["l"] == 0


def test_split_explore_holdout_embargoes_a_crossing_window():
    rows = [
        {"month_start": "2023-12-01", "window_end": "2024-01-15"},  # crosses -> embargoed
        {"month_start": "2023-11-01", "window_end": "2023-12-30"},  # fully in explore
        {"month_start": HOLDOUT_START, "window_end": "2024-06-01"},  # holdout
    ]
    explore, holdout, dropped = split_explore_holdout(rows)
    assert dropped == 1 and len(explore) == 1 and len(holdout) == 1


def test_attach_terciles_splits_a_months_pool_into_three_roughly_equal_groups():
    rows = [_row(f"S{i}", "2022-05-01", 0, {}, size=float(i)) for i in range(9)]
    attach_terciles(rows)
    counts = {}
    for r in rows:
        counts[r["size_tercile"]] = counts.get(r["size_tercile"], 0) + 1
    assert counts == {0: 3, 1: 3, 2: 3}


def test_qualifying_cells_requires_every_bucket_in_both_periods():
    def make_rows(period_month, n_per_bucket):
        rows = []
        for bucket_count in range(4):
            warn_keys = ["a", "b", "c"][:bucket_count] if bucket_count < 3 else ["a", "b", "c"]
            for i in range(n_per_bucket):
                r = _row(f"S{bucket_count}_{i}", period_month, 0, dict.fromkeys(warn_keys, True))
                r["size_tercile"], r["vol_tercile"] = 0, 0
                rows.append(r)
        return rows

    explore = make_rows("2022-05-01", MIN_CELL_GROUP)
    holdout = make_rows("2024-01-01", MIN_CELL_GROUP)
    cells, _detail = qualifying_cells(explore, holdout, ["a", "b", "c"])
    assert cells == [(0, 0)]

    # Now starve one bucket in holdout: should no longer qualify.
    holdout_short = make_rows("2024-01-01", MIN_CELL_GROUP)
    holdout_short = [r for r in holdout_short if not (count_bucket(warning_count(r, ["a", "b", "c"])) == 3)][:-1]
    cells2, _ = qualifying_cells(explore, holdout_short, ["a", "b", "c"])
    assert cells2 == []


def test_cell_weighted_du_by_bucket_known_value():
    rows = []
    for i in range(5):
        r = _row(f"S{i}", "2022-05-01", 0, {})
        r["size_tercile"], r["vol_tercile"] = 0, 0
        r["d"], r["u"] = 1, 0
        rows.append(r)
    out = cell_weighted_du_by_bucket(rows, [(0, 0)], ["a", "b", "c"])
    assert out[0] == 1.0  # all 5 rows have count 0, D-U = 1 - 0 = 1
    assert out[1] is None  # no rows in bucket 1


def test_choose_champion_and_two_plus_and_champion_du():
    rows = []
    # Warning "a" alone (count==1): strong D-U (mostly falls).
    for i in range(MIN_CELL_GROUP):
        r = _row(f"A{i}", "2022-05-01", 0, {"a": True})
        r["d"], r["u"] = (1, 0) if i < MIN_CELL_GROUP - 2 else (0, 0)
        r["size_tercile"], r["vol_tercile"] = 0, 0
        rows.append(r)
    # Warning "b" alone (count==1): weak D-U.
    for i in range(MIN_CELL_GROUP):
        r = _row(f"B{i}", "2022-05-01", 0, {"b": True})
        r["d"], r["u"] = (0, 0)
        r["size_tercile"], r["vol_tercile"] = 0, 0
        rows.append(r)
    # count>=2 group: even stronger D-U.
    for i in range(MIN_CELL_GROUP):
        r = _row(f"C{i}", "2022-05-01", 0, {"a": True, "b": True})
        r["d"], r["u"] = 1, 0
        r["size_tercile"], r["vol_tercile"] = 0, 0
        rows.append(r)

    keys = ["a", "b", "c"]
    champion, du = choose_champion_warning(rows, keys)
    assert champion == "a"
    cells = [(0, 0)]
    champ_du = cell_weighted_du_for_champion(rows, cells, champion, keys)
    two_plus_du = cell_weighted_du_two_plus(rows, cells, keys)
    assert champ_du == du
    assert two_plus_du == 1.0
    assert two_plus_du > champ_du
