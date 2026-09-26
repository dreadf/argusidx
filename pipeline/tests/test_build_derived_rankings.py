"""Tests for pipeline/appdata/build_derived_rankings.py (synthetic rows)."""
import json

from pipeline.appdata.build_derived_rankings import (
    build_dividend_consistency,
    build_earnings_streaks,
    build_net_insider,
    build_roe_percentile,
    dividend_years,
    earnings_run,
    load_filings,
)
from pipeline.appdata.peer_groups import MIN_GROUP_SIZE


def _row(sym, **qv):
    base = {"sector": "S", "sub_sector": "SS", "industry": "I", "sub_industry": "SI"}
    base.update(qv)
    return {"symbol": sym, "company_name": sym, "query_values": base}


def test_roe_percentile_within_group_and_small_groups_skipped():
    rows = [_row(f"A{i:02d}", **{"roe[2025]": 0.01 * i}) for i in range(MIN_GROUP_SIZE)]
    out = build_roe_percentile(rows)
    assert out["evaluable_count"] == MIN_GROUP_SIZE
    top = out["top"][0]
    assert top["symbol"] == f"A{MIN_GROUP_SIZE - 1:02d}" and top["percentile"] == 100.0
    assert out["top"][-1]["percentile"] == 0.0 or len(out["top"]) == 20
    assert build_roe_percentile(rows[: MIN_GROUP_SIZE - 1])["evaluable_count"] == 0  # too few reported ROEs
    with_gap = rows[:-1] + [_row("NOROE")]
    assert build_roe_percentile(with_gap)["evaluable_count"] == 0  # 14 reported < 15


def test_dividend_years_and_ordering_by_years_then_smaller_variation():
    steady = _row("STEADY", **{f"total_dividend[{y}]": 10.0 for y in range(2021, 2026)})
    wobbly = _row("WOBBLY", **{f"total_dividend[{y}]": v for y, v in zip(range(2021, 2026), [5, 20, 5, 20, 5])})
    four = _row("FOUR", **{f"total_dividend[{y}]": 10.0 for y in range(2022, 2026)})
    none = _row("NONE")
    out = build_dividend_consistency([four, wobbly, steady, none])
    assert [e["symbol"] for e in out["top"]] == ["STEADY", "WOBBLY", "FOUR"]
    assert out["top"][0]["years_paid"] == 5 and out["top"][0]["variation"] == 0.0
    assert dividend_years({"total_dividend[2023]": 0.0, "total_dividend[2024]": None, "total_dividend[2025]": 1.0}) == [1.0]


def test_earnings_run_counts_consecutive_rises_and_stops_at_a_fall_or_nonpositive():
    def q(*vals):
        return {f"earnings[{y}]": v for y, v in zip(range(2021, 2026), vals)}

    assert earnings_run(q(1, 2, 3, 4, 5)) == 4
    assert earnings_run(q(1, 2, 3, 3, 5)) == 1  # equal is not a rise
    assert earnings_run(q(-1, 2, 3, 4, 5)) == 3  # a rise from a loss is not counted
    assert earnings_run(q(1, 2, 3, 4, None)) == 0
    rows = [_row("A", **q(1, 2, 3, 4, 5)), _row("B", **q(9, 8, 7, 6, 5)), _row("C", **q(1, 2, 3, 4, 5))]
    out = build_earnings_streaks(rows)
    assert [e["symbol"] for e in out["top"]] == ["A", "C"]
    assert out["longest_run"] == 4 and out["stocks_at_longest_run"] == 2


def _write(path, recs):
    path.write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def _rec(sym, before, after, ts="2025-01-02T10:00:00", holder="H", tags=None):
    return {"symbol": sym, "holding_before": before, "holding_after": after, "timestamp": ts, "holder_name": holder, "tags": tags}


def test_load_filings_dedupes_signs_and_skips_missing_holdings(tmp_path):
    b, s = tmp_path / "b.jsonl", tmp_path / "s.jsonl"
    _write(b, [_rec("A", 100, 150), _rec("A", 100, 150), _rec("A", None, 5), _rec("T", 0, 10, tags=["takeover"])])
    _write(s, [_rec("A", 150, 120)])
    buys, sells = load_filings(b, "buy"), load_filings(s, "sell")
    assert [f["signed_shares"] for f in buys] == [50, 10] and buys[1]["takeover"] is True
    assert [f["signed_shares"] for f in sells] == [-30]


def test_net_insider_ratio_lists_takeover_separation_and_over_100_flag():
    rows = [_row(s, **{"outstanding_shares[2025]": 1000.0}) for s in ("A", "B", "T", "Z")]
    rows.append(_row("NOSH"))
    filings = [
        {"symbol": "A", "signed_shares": 100, "takeover": False},
        {"symbol": "A", "signed_shares": -20, "takeover": False},
        {"symbol": "B", "signed_shares": -50, "takeover": False},
        {"symbol": "T", "signed_shares": 5000, "takeover": True},
        {"symbol": "NOSH", "signed_shares": 5, "takeover": False},
    ]
    out = build_net_insider(rows, filings)
    a = out["top_net_buyers"][0]
    assert a["symbol"] == "A" and a["net_shares"] == 80 and abs(a["share_of_outstanding"] - 0.08) < 1e-12
    assert a["buy_shares"] == 100 and a["sell_shares"] == 20 and a["n_filings"] == 2
    assert [e["symbol"] for e in out["top_net_sellers"]] == ["B"]
    assert [e["symbol"] for e in out["takeover_tagged_separate"]] == ["T"]
    assert out["takeover_tagged_separate"][0]["over_100_percent"] is True
    assert "T" not in [e["symbol"] for e in out["top_net_buyers"]]
    assert out["evaluable_count"] == 2  # NOSH lacks outstanding shares
    assert out["filings_tagged_takeover"] == 1


def test_roe_above_100_percent_is_excluded_and_reported():
    rows = [_row(f"A{i:02d}", **{"roe[2025]": 0.01 * i}) for i in range(MIN_GROUP_SIZE)]
    rows.append(_row("ZZZZ", **{"roe[2025]": 67.0}))
    out = build_roe_percentile(rows)
    assert [e["symbol"] for e in out["excluded_over_100_percent"]] == ["ZZZZ"]
    assert all(e["symbol"] != "ZZZZ" for e in out["top"])
