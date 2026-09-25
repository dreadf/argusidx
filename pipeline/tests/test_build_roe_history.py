"""
Tests for pipeline/appdata/build_roe_history.py. The BBCA and Financials
figures asserted against the real sweep are the ones the stock page draws
(BBCA 15.5 to 20.4 percent, sector median 4.2 to 4.7); a mismatch means
the aggregation drifted.
"""
import json

from pipeline.appdata.build_roe_history import YEARS, build, roe_percent
from pipeline.appdata.common import RAW_DIR, UNIVERSE_GLOB, latest_dated_file


def _row(symbol, sector, roes):
    qv = {"sector": sector}
    for year, v in zip(YEARS, roes):
        qv[f"roe[{year}]"] = v
    return {"symbol": symbol, "query_values": qv}


def test_ratio_becomes_percent_and_missing_stays_missing():
    assert roe_percent({"roe[2025]": 0.2043}, 2025) == 20.43
    assert roe_percent({}, 2025) is None


def test_sector_median_ignores_missing_and_counts_reporters():
    rows = [
        _row("A.JK", "S", [0.10, None, 0.10, 0.10, 0.10]),
        _row("B.JK", "S", [0.20, 0.20, 0.20, 0.20, 0.20]),
        _row("C.JK", "S", [0.30, None, 0.30, 0.30, 0.30]),
    ]
    out = build(rows)
    assert out["sectors"]["S"]["median"] == [20.0, 20.0, 20.0, 20.0, 20.0]
    assert out["sectors"]["S"]["n"] == [3, 1, 3, 3, 3]
    assert out["by_symbol"]["A.JK"][1] is None


def test_real_sweep_matches_the_stock_page_figures():
    rows = json.loads(latest_dated_file(RAW_DIR, UNIVERSE_GLOB).read_text())
    out = build(rows)
    assert [round(v, 1) for v in out["by_symbol"]["BBCA.JK"]] == [15.5, 18.4, 20.1, 20.2, 20.4]
    fin = out["sectors"]["Financials"]["median"]
    assert round(fin[0], 1) == 4.2 and round(fin[-1], 1) == 4.7
