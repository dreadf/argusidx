"""Build data/app/stock_profile.json: the numbers the redesigned stock page
reads beyond stocks.json (five-year financials, valuation, dividend, the
one-year change against IHSG and the sector, index membership, foreign-flow
list days, and where each stock sits among all stocks).

Only fields the page displays are copied. Every comparison is computed here,
once, so the page never ranks stocks at request time:

- change_1y: Sectors closes on WINDOW_START and WINDOW_END (owned snapshots,
  sectors_daily_close_*.json), null when either close is missing.
- sector_rank_1y: how many stocks in the same sector had a larger change_1y,
  out of the sector's stocks with a change_1y.
- pe_meaningful: P/E > 0 and 2025 earnings not a loss. A trailing P/E can be
  positive and huge when trailing earnings are barely above zero after a loss
  year (GOTO: 30,826x); it is then not a valuation and is never compared.
- pe_cheaper_than: share (0-100) of stocks with a meaningful P/E whose P/E is
  higher. Null when this stock's P/E is not meaningful.
- yield_higher_than: share of ALL stocks with a lower trailing yield; a
  non-payer counts as 0, so the comparison is against every stock.
- yield_higher_than_payers: the same among dividend payers only (null for a
  non-payer). Most stocks pay nothing, so a 0,2% yield already beats two
  thirds of all stocks; "high dividend" is judged against payers.
- roe_higher_than, revenue_growth_higher_than, free_float_higher_than: share
  of stocks with a value whose value is lower.
- der_higher_than: same, among non-financial companies only (a bank's
  debt-to-equity is not comparable).
- size_third: "small" / "mid" / "large" by market-cap rank, thirds of the
  ranked universe.
- daily_gain_rank: 1 = largest one-day gain on the snapshot date.

Run: .venv/bin/python -m pipeline.appdata.build_stock_profile
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file
from pipeline.hypotheses.t1_market_state import load_ihsg

YEARS = [2021, 2022, 2023, 2024, 2025]
WINDOW_START, WINDOW_END = "2025-09-04", "2026-09-04"
DAILY_CLOSE_GLOB = "sectors_daily_close_????-??-??.json"
FOREIGN_FLOW_GLOB = "foreign_flow_lists_????-??-??.json"
FINANCIALS = "Financials"

SCALARS = ["pe_ttm", "forward_pe", "pb_mrq", "ps_ttm", "yield_ttm", "payout_ratio", "dividend_yield_avg", "roe_ttm", "der_mrq", "daily_close_change"]
YEARLY = {"revenue": "revenue", "earnings": "earnings", "roe": "roe", "der": "debt_to_equity_ratio", "dividend": "total_dividend", "pe": "pe"}


def share_below(values: list[float], x: float) -> float:
    """Share (0-100) of `values` strictly below x."""
    if not values:
        raise ValueError("empty comparison set")
    return 100 * sum(1 for v in values if v < x) / len(values)


def share_above(values: list[float], x: float) -> float:
    """Share (0-100) of `values` strictly above x."""
    if not values:
        raise ValueError("empty comparison set")
    return 100 * sum(1 for v in values if v > x) / len(values)


def pe_meaningful(q: dict) -> bool:
    pe, e = q.get("pe_ttm"), q.get("earnings[2025]")
    return pe is not None and pe > 0 and (e is None or e >= 0)


def revenue_growth(q: dict) -> float | None:
    a, b = q.get("revenue[2024]"), q.get("revenue[2025]")
    if a is None or b is None or a <= 0:
        return None
    return b / a - 1


def size_third(rank: int | None, n_ranked: int) -> str | None:
    if rank is None:
        return None
    if rank <= n_ranked / 3:
        return "large"
    if rank <= 2 * n_ranked / 3:
        return "mid"
    return "small"


def closes_on(daily: dict, day: str) -> dict[str, float]:
    if day not in daily:
        raise KeyError(f"no Sectors closes for {day} in the daily-close file")
    return {r["symbol"]: r["close"] for page in daily[day]["pages"].values() for r in page}


def foreign_days(flow: dict) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for day in flow.values():
        for side in ("buy", "sell"):
            for r in day.get(side, []):
                out.setdefault(r["symbol"], {"buy": 0, "sell": 0})[side] += 1
    return out


def build(rows: list[dict], start_close: dict[str, float], end_close: dict[str, float], ff: dict[str, dict[str, int]]) -> dict[str, dict]:
    q = {r["symbol"]: r["query_values"] for r in rows}

    def chg(sym: str) -> float | None:
        a, b = start_close.get(sym), end_close.get(sym)
        return b / a - 1 if a and b else None

    change = {s: chg(s) for s in q}
    pes = [v["pe_ttm"] for v in q.values() if pe_meaningful(v)]
    yields = [v.get("yield_ttm") or 0.0 for v in q.values()]
    payer_yields = [y for y in yields if y > 0]
    roes = [v["roe_ttm"] for v in q.values() if v.get("roe_ttm") is not None]
    ders = [v["der_mrq"] for v in q.values() if v.get("der_mrq") is not None and v.get("sector") != FINANCIALS]
    floats = [v["free_float"] for v in q.values() if v.get("free_float") is not None]
    growths = [g for g in (revenue_growth(v) for v in q.values()) if g is not None]
    n_ranked = sum(1 for v in q.values() if v.get("market_cap_rank") is not None)
    gains = sorted((v["daily_close_change"], s) for s, v in q.items() if v.get("daily_close_change") is not None)
    gain_rank = {s: i + 1 for i, (_, s) in enumerate(reversed(gains))}

    out = {}
    for sym, v in q.items():
        c = change[sym]
        peers = [change[s] for s, w in q.items() if w.get("sector") == v.get("sector") and change[s] is not None]
        pe, roe, der, g = v.get("pe_ttm"), v.get("roe_ttm"), v.get("der_mrq"), revenue_growth(v)
        out[sym] = {
            **{k: v.get(k) for k in SCALARS},
            **{k: [v.get(f"{f}[{y}]") for y in YEARS] for k, f in YEARLY.items()},
            "w52_low_date": v.get("52_w_low_date"),
            "w52_high_date": v.get("52_w_high_date"),
            "d90_low": v.get("90_d_low_price"),
            "d90_high": v.get("90_d_high_price"),
            "all_time_low": v.get("all_time_low_price"),
            "all_time_low_date": v.get("all_time_low_date"),
            "all_time_high": v.get("all_time_high_price"),
            "all_time_high_date": v.get("all_time_high_date"),
            "last_ex_dividend_date": v.get("last_ex_dividend_date"),
            "indices": v.get("indices") or [],
            "change_1y": c,
            "sector_rank_1y": None if c is None else {"better": sum(1 for p in peers if p > c), "n": len(peers)},
            "pe_meaningful": pe_meaningful(v),
            "pe_cheaper_than": share_above(pes, pe) if pe_meaningful(v) else None,
            "yield_higher_than": share_below(yields, v.get("yield_ttm") or 0.0),
            "yield_higher_than_payers": share_below(payer_yields, v["yield_ttm"]) if (v.get("yield_ttm") or 0) > 0 else None,
            "roe_higher_than": share_below(roes, roe) if roe is not None else None,
            "der_higher_than": share_below(ders, der) if der is not None and v.get("sector") != FINANCIALS else None,
            "free_float_higher_than": share_below(floats, v["free_float"]) if v.get("free_float") is not None else None,
            "revenue_growth": g,
            "revenue_growth_higher_than": share_below(growths, g) if g is not None else None,
            "size_third": size_third(v.get("market_cap_rank"), n_ranked),
            "daily_gain_rank": gain_rank.get(sym),
            "foreign_buy_days": ff.get(sym, {}).get("buy", 0),
            "foreign_sell_days": ff.get(sym, {}).get("sell", 0),
        }
    return out


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    daily_path = latest_dated_file(RAW_DIR, DAILY_CLOSE_GLOB)
    flow_path = latest_dated_file(RAW_DIR, FOREIGN_FLOW_GLOB)
    rows = json.loads(universe_path.read_text())
    daily = json.loads(daily_path.read_text())
    flow = json.loads(flow_path.read_text())

    dates, closes = load_ihsg()
    ihsg = dict(zip(dates, closes))
    for day in (WINDOW_START, WINDOW_END):
        if day not in ihsg:
            raise KeyError(f"IHSG has no close on {day}")

    stocks = build(rows, closes_on(daily, WINDOW_START), closes_on(daily, WINDOW_END), foreign_days(flow))
    flow_days = sorted(flow)
    out = {
        "as_of": universe_path.stem.replace("universe_", ""),
        "source_files": [universe_path.name, daily_path.name, flow_path.name],
        "years": YEARS,
        "change_window": {"start": WINDOW_START, "end": WINDOW_END},
        "ihsg_change_1y": ihsg[WINDOW_END] / ihsg[WINDOW_START] - 1,
        "foreign_flow": {"days": len(flow_days), "first": flow_days[0], "last": flow_days[-1]},
        "stocks": stocks,
    }
    path = APP_DIR / "stock_profile.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {path} ({len(stocks)} stocks, {path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
