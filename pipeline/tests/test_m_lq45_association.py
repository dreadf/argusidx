"""Tests for pipeline/hypotheses/m_lq45_association.py."""
from pipeline.hypotheses.m_lq45_association import GROUP_SIZE, build_lq45_association, is_lq45_member, select_groups


def _u(sym, mcap, indices):
    return {"symbol": sym, "query_values": {"market_cap": mcap, "indices": indices}}


def _series(drop: float, bars: int = 130) -> dict:
    half = bars // 2
    return {"close": [100.0] * half + [100.0 * (1 - drop)] * (bars - half)}


def test_membership_needs_a_list_containing_lq45():
    assert is_lq45_member({"indices": ["IDX30", "LQ45"]})
    assert not is_lq45_member({"indices": []}) and not is_lq45_member({"indices": None}) and not is_lq45_member({})


def test_non_members_are_the_45_largest_by_market_cap_and_members_are_excluded():
    universe = [_u("M.JK", 10**15, ["LQ45"])]
    universe += [_u(f"N{i:02d}.JK", 1000 + i, None) for i in range(60)]
    universe.append(_u("NOCAP.JK", None, None))
    members, non = select_groups(universe)
    assert members == ["M.JK"]
    assert len(non) == GROUP_SIZE
    assert non[0] == "N59.JK" and non[-1] == "N15.JK"  # 45 largest of 60
    assert "M.JK" not in non and "NOCAP.JK" not in non


def test_summary_medians_share_and_dropped_stocks():
    universe = [_u("M1.JK", 5, ["LQ45"]), _u("M2.JK", 5, ["LQ45"]), _u("M3.JK", 5, ["LQ45"]), _u("M4.JK", 5, ["LQ45"]), _u("N1.JK", 4, [])]
    prices = {"M1.JK": _series(0.1), "M2.JK": _series(0.3), "M3.JK": _series(0.5), "N1.JK": _series(0.2)}  # M4 has no prices
    out = build_lq45_association(universe, prices)
    m = out["lq45_members"]
    assert m["selected"] == 4 and m["n"] == 3 and m["dropped_no_history"] == 1
    assert abs(m["median_max_drawdown"] + 0.3) < 1e-9
    assert abs(m["share_drawdown_30_or_worse"] - 2 / 3) < 1e-9  # exactly -30% counts
    assert out["largest_non_members"]["n"] == 1
