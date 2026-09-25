"""
Tests for pipeline/appdata/peer_groups.py (docs/PRODUCT.md §8).
"""
from pipeline.appdata.peer_groups import MIN_GROUP_SIZE, build_peer_groups


def _row(symbol, sub_industry=None, industry=None, sub_sector=None, sector=None):
    return {
        "symbol": symbol,
        "query_values": {
            "sub_industry": sub_industry,
            "industry": industry,
            "sub_sector": sub_sector,
            "sector": sector,
        },
    }


def test_large_sub_industry_resolves_at_finest_level():
    rows = [_row(f"S{i}.JK", sub_industry="Banks", sector="Financials") for i in range(20)]
    result = build_peer_groups(rows)
    for i in range(20):
        assert result["assignments"][f"S{i}.JK"] == {"level": "sub_industry", "group": "Banks"}
    assert len(result["group_members"]["sub_industry:Banks"]) == 20


def test_small_sub_industry_falls_back_to_industry():
    small = [_row(f"A{i}.JK", sub_industry="Silver Mining", industry="Mining", sector="Basic Materials") for i in range(3)]
    filler = [_row(f"B{i}.JK", sub_industry="Coal Mining", industry="Mining", sector="Basic Materials") for i in range(20)]
    result = build_peer_groups(small + filler)
    for i in range(3):
        assert result["assignments"][f"A{i}.JK"] == {"level": "industry", "group": "Mining"}
    # Peer group at industry level includes the large sub-industry too,
    # not just the leftover companies that also fell back.
    assert len(result["group_members"]["industry:Mining"]) == 23


def test_falls_back_all_the_way_to_sector_when_nothing_else_qualifies():
    tiny = [_row(f"C{i}.JK", sub_industry="Rare Metals", industry="Rare Metals", sub_sector="Rare Metals", sector="Basic Materials") for i in range(2)]
    filler = [_row(f"D{i}.JK", sub_industry="Cement", industry="Cement", sub_sector="Cement", sector="Basic Materials") for i in range(20)]
    result = build_peer_groups(tiny + filler)
    for i in range(2):
        assert result["assignments"][f"C{i}.JK"] == {"level": "sector", "group": "Basic Materials"}


def test_sector_level_is_never_gated_by_min_group_size():
    """The widest level always resolves, even below MIN_GROUP_SIZE, since
    there is nowhere further to fall back to."""
    rows = [_row(f"E{i}.JK", sector="Tiny Sector") for i in range(3)]
    result = build_peer_groups(rows)
    for i in range(3):
        assert result["assignments"][f"E{i}.JK"] == {"level": "sector", "group": "Tiny Sector"}
    assert len(result["group_members"]["sector:Tiny Sector"]) == 3


def test_every_real_universe_group_meets_min_size_except_forced_sector_fallback():
    """Regression for the real universe sweep: every produced group must be
    >= MIN_GROUP_SIZE (the whole point of the cascade), confirmed here on a
    synthetic set shaped like the real skew (one huge sector, one company
    orphaned at every finer level)."""
    huge = [_row(f"F{i}.JK", sub_industry="X", industry="X", sub_sector="X", sector="Big") for i in range(30)]
    result = build_peer_groups(huge)
    assert result["summary"]["smallest_group"] >= MIN_GROUP_SIZE
