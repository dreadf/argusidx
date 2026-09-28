"""Tests for pipeline/appdata/build_market_analysis.py, on synthetic data."""
import pytest

from pipeline.appdata.build_market_analysis import LARGE_CAP_N, PRODUCER_SUB_INDUSTRIES, build


def _row(symbol, name, mcap, last, sub_industry=None):
    return {"symbol": symbol, "company_name": name, "query_values": {"market_cap": mcap, "last_close_price": last, "sub_industry": sub_industry}}


def test_build_skips_a_stock_missing_either_close():
    rows = [_row("AAA.JK", "A", 1000, 100), _row("BBB.JK", "B", 1000, 100)]
    peak_close = {"AAA.JK": 100, "BBB.JK": 100}
    end_close = {"AAA.JK": 90}  # BBB has no end close
    out = build(rows, peak_close, end_close)
    assert out["universe"]["n"] == 1


def test_build_skips_a_stock_with_no_market_cap_or_last_close():
    rows = [_row("AAA.JK", "A", None, 100), _row("BBB.JK", "B", 1000, None), _row("CCC.JK", "C", 1000, 100)]
    peak_close = {s: 100 for s in ("AAA.JK", "BBB.JK", "CCC.JK")}
    end_close = {s: 90 for s in ("AAA.JK", "BBB.JK", "CCC.JK")}
    out = build(rows, peak_close, end_close)
    assert out["universe"]["n"] == 1


def test_market_value_and_return_use_shares_held_constant_from_the_snapshot():
    # AAA: mcap 1_000_000 / last 100 = 10_000 shares. Peak 100 -> end 80: -20%.
    rows = [_row("AAA.JK", "A", 1_000_000, 100)]
    out = build(rows, {"AAA.JK": 100}, {"AAA.JK": 80})
    assert out["universe"]["market_value_start"] == 10_000 * 100
    assert out["universe"]["market_value_end"] == 10_000 * 80
    assert out["drag"][0]["return"] == pytest.approx(-0.2)


def test_drag_is_sorted_by_value_change_not_by_return_and_share_sums_to_the_fall():
    # AAA is a small stock down 90% (small rupiah drag); BBB is a giant down 5%
    # (big rupiah drag). BBB must be the top drag row even though its % fall
    # is smaller, because "menanggung penurunan" is about rupiah, not percent.
    rows = [_row("AAA.JK", "A", 100_000, 100), _row("BBB.JK", "B", 100_000_000, 100)]
    peak_close = {"AAA.JK": 100, "BBB.JK": 100}
    end_close = {"AAA.JK": 10, "BBB.JK": 95}
    out = build(rows, peak_close, end_close)
    assert out["drag"][0]["symbol"] == "BBB.JK"
    assert out["drag"][1]["symbol"] == "AAA.JK"
    total_fall = out["universe"]["market_value_end"] - out["universe"]["market_value_start"]
    assert abs(sum(r["value_change"] for r in out["drag"]) - total_fall) < 1e-6
    assert abs(sum(r["drag_share"] for r in out["drag"]) - 1.0) < 1e-9


def test_large_caps_selection_is_by_peak_day_size_not_by_return():
    # LARGE_CAP_N (100) big stocks, all flat, plus one tiny stock up 1000%.
    # The tiny stock's huge return must not buy it a seat among "the 100
    # largest": selection is by size (m0), only the ordering within it is
    # by return.
    rows = [_row(f"BIG{i}.JK", f"Big {i}", 1_000_000_000 - i, 100) for i in range(LARGE_CAP_N)]
    rows.append(_row("TINY.JK", "Tiny", 1_000, 100))
    closes = {r["symbol"]: 100 for r in rows}
    end_close = dict(closes)
    end_close["TINY.JK"] = 1100
    out = build(rows, closes, end_close)
    symbols = {r["symbol"] for r in out["large_caps"]["up"]} | {"BIG0.JK"}
    assert "TINY.JK" not in symbols
    assert out["large_caps"]["n_up"] == 0  # every BIG* stock is flat


def test_large_caps_up_list_is_ordered_by_return():
    rows = [_row("A.JK", "A", 100, 100), _row("B.JK", "B", 100, 100)]
    peak_close = {"A.JK": 100, "B.JK": 100}
    end_close = {"A.JK": 105, "B.JK": 120}
    out = build(rows, peak_close, end_close)
    assert [r["symbol"] for r in out["large_caps"]["up"]] == ["B.JK", "A.JK"]


def test_producer_count_only_matches_the_pinned_sub_industry_set():
    rows = [
        _row("MINE.JK", "Coal miner", 1_000_000, 100, sub_industry="Coal Production"),
        _row("HAUL.JK", "Coal hauler", 1_000_000, 100, sub_industry="Coal Distribution"),
    ]
    peak_close = {"MINE.JK": 100, "HAUL.JK": 100}
    end_close = {"MINE.JK": 110, "HAUL.JK": 110}
    out = build(rows, peak_close, end_close)
    assert out["large_caps"]["n_up"] == 2
    assert out["large_caps"]["n_producer"] == 1
    assert "Coal Distribution" not in PRODUCER_SUB_INDUSTRIES
    assert "Coal Production" in PRODUCER_SUB_INDUSTRIES
