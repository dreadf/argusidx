"""
Tests for pipeline/appdata/build_lens_banking.py (docs/PRODUCT.md §9).
"""
from pipeline.appdata.build_lens_banking import RANKED_FIELDS, build_lens_banking


def _bank(symbol, **qv):
    qv.setdefault("sub_sector", "Banks")
    return {"symbol": symbol, "company_name": f"{symbol} Co", "query_values": qv}


def test_only_banks_sub_sector_included():
    rows = [
        _bank("A.JK"),
        {"symbol": "B.JK", "company_name": "Not A Bank", "query_values": {"sub_sector": "Insurance"}},
    ]
    result = build_lens_banking(rows)
    assert set(result.keys()) == {"A.JK"}


def test_higher_is_healthier_ranking_direction():
    rows = [
        _bank("A.JK", **{"casa_ratio[2025]": 0.9}),
        _bank("B.JK", **{"casa_ratio[2025]": 0.5}),
        _bank("C.JK", **{"casa_ratio[2025]": 0.3}),
    ]
    result = build_lens_banking(rows)
    assert result["A.JK"]["ratios"]["casa_ratio[2025]"]["better_than_count"] == 2
    assert result["C.JK"]["ratios"]["casa_ratio[2025]"]["better_than_count"] == 0


def test_npl_ratio_lower_is_healthier_and_computed_not_returned_raw():
    rows = [
        _bank("A.JK", **{"non_performing_loan[2025]": 10, "net_loan[2025]": 1000}),  # 1%
        _bank("B.JK", **{"non_performing_loan[2025]": 50, "net_loan[2025]": 1000}),  # 5%
    ]
    result = build_lens_banking(rows)
    assert result["A.JK"]["ratios"]["npl_ratio"]["value"] == 0.01
    assert result["A.JK"]["ratios"]["npl_ratio"]["better_than_count"] == 1  # A has lower NPL
    assert result["B.JK"]["ratios"]["npl_ratio"]["better_than_count"] == 0


def test_loan_to_deposit_ratio_never_ranked():
    """A real outlier (Bank Aladin Syariah, LDR=920x) confirmed LDR has no
    single 'better' direction - it must be a plain value, never a
    better_than_count claim."""
    rows = [
        _bank("A.JK", **{"loan_to_deposit_ratio[2025]": 920.0}),
        _bank("B.JK", **{"loan_to_deposit_ratio[2025]": 0.8}),
    ]
    result = build_lens_banking(rows)
    assert result["A.JK"]["loan_to_deposit_ratio"] == 920.0
    assert "loan_to_deposit_ratio[2025]" not in RANKED_FIELDS


def test_missing_metric_returns_none_not_zero():
    rows = [_bank("A.JK"), _bank("B.JK", **{"casa_ratio[2025]": 0.5})]
    result = build_lens_banking(rows)
    assert result["A.JK"]["ratios"]["casa_ratio[2025]"] is None


def test_loan_growth_computed_correctly():
    rows = [_bank("A.JK", **{"net_loan[2025]": 110, "net_loan[2024]": 100})]
    result = build_lens_banking(rows)
    assert abs(result["A.JK"]["loan_growth"] - 0.10) < 1e-9
