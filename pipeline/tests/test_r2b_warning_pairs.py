"""Tests for pipeline/hypotheses/r2b_warning_pairs.py, on synthetic rows."""
from pipeline.hypotheses.r2b_warning_pairs import (
    MIN_GROUP,
    bootstrap_one_sided_p,
    cell_weighted_du,
    group_label,
    pair_diff_stat,
    qualifying_cells_for_pair,
)


def _row(symbol, warnings, d=0, u=0, size_tercile=0, vol_tercile=0):
    return {
        "symbol": symbol,
        "warnings": dict.fromkeys(["x", "y", "z"], False) | warnings,
        "d": d,
        "u": u,
        "size_tercile": size_tercile,
        "vol_tercile": vol_tercile,
    }


KEYS = ["x", "y", "z"]


def test_group_label_pair_vs_alone_vs_neither():
    assert group_label(_row("A", {"x": True, "y": True}), "x", "y", KEYS) == "pair"
    assert group_label(_row("A", {"x": True}), "x", "y", KEYS) == "x"
    assert group_label(_row("A", {"y": True}), "x", "y", KEYS) == "y"
    assert group_label(_row("A", {"x": True, "z": True}), "x", "y", KEYS) is None  # count==2 but not the x,y pair
    assert group_label(_row("A", {}), "x", "y", KEYS) is None


def test_qualifying_cells_for_pair_requires_all_three_groups():
    rows = []
    for i in range(MIN_GROUP):
        rows.append(_row(f"P{i}", {"x": True, "y": True}))
        rows.append(_row(f"X{i}", {"x": True}))
        rows.append(_row(f"Y{i}", {"y": True}))
    cells = qualifying_cells_for_pair(rows, "x", "y", KEYS)
    assert cells == [(0, 0)]

    short = rows[:-1]  # one fewer "y alone" row -> below MIN_GROUP
    cells2 = qualifying_cells_for_pair(short, "x", "y", KEYS)
    assert cells2 == []


def test_cell_weighted_du_and_pair_diff_stat_known_values():
    rows = (
        [_row(f"P{i}", {"x": True, "y": True}, d=1, u=0) for i in range(5)]
        + [_row(f"X{i}", {"x": True}, d=0, u=0) for i in range(5)]
        + [_row(f"Y{i}", {"y": True}, d=0, u=1) for i in range(5)]
    )
    cells = [(0, 0)]
    du_pair = cell_weighted_du(rows, cells, "pair", "x", "y", KEYS)
    du_x = cell_weighted_du(rows, cells, "x", "x", "y", KEYS)
    du_y = cell_weighted_du(rows, cells, "y", "x", "y", KEYS)
    assert du_pair == 1.0 and du_x == 0.0 and du_y == -1.0
    diff = pair_diff_stat(rows, cells, "x", "y", KEYS)
    assert diff == 1.0  # min(1-0, 1-(-1)) = min(1, 2) = 1


def test_pair_diff_stat_none_when_a_group_is_missing():
    rows = [_row("P1", {"x": True, "y": True}, d=1, u=0)]
    assert pair_diff_stat(rows, [(0, 0)], "x", "y", KEYS) is None


def test_bootstrap_one_sided_p_small_for_a_consistently_strong_pair():
    rows = (
        [_row(f"P{i}", {"x": True, "y": True}, d=1, u=0) for i in range(MIN_GROUP)]
        + [_row(f"X{i}", {"x": True}, d=0, u=0) for i in range(MIN_GROUP)]
        + [_row(f"Y{i}", {"y": True}, d=0, u=0) for i in range(MIN_GROUP)]
    )
    res = bootstrap_one_sided_p(rows, [(0, 0)], "x", "y", KEYS)
    assert res["estimate"] == 1.0
    assert res["p_one_sided"] < 0.01


def test_bootstrap_one_sided_p_large_when_there_is_no_real_difference():
    rows = (
        [_row(f"P{i}", {"x": True, "y": True}, d=(i % 2), u=((i + 1) % 2)) for i in range(MIN_GROUP)]
        + [_row(f"X{i}", {"x": True}, d=(i % 2), u=((i + 1) % 2)) for i in range(MIN_GROUP)]
        + [_row(f"Y{i}", {"y": True}, d=(i % 2), u=((i + 1) % 2)) for i in range(MIN_GROUP)]
    )
    res = bootstrap_one_sided_p(rows, [(0, 0)], "x", "y", KEYS)
    assert res["p_one_sided"] > 0.3
