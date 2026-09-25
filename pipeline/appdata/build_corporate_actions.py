"""Build data/app/corporate_actions.json from the purchased corporate-
actions calendar (data/raw/corporate_actions_*.json, pipeline/appdata/
fetch_corporate_actions.py) plus the universe sweep.

Per stock, dated events in the fetched window: dividends, AGMs, rights
issues, stock splits. Two derived touches keep it from being a reformatted
feed:
- each dividend carries what this ONE payment is as a share of the last
  close (`implied_yield`). Deliberately NOT compared with the company's
  average annual yield: checked 2026-09-20, BBCA's interim payment is 0.4%
  of price against a 2.8% annual average, so setting one interim payment
  beside an annual figure would imply a cut that isn't there;
- cancelled AGMs (the API marks them in the venue field) are flagged
  instead of shown as if they will happen.

`dividend` and `upcoming_dividend` overlap (verified 2026-09-20: the same
ex-dates appear in both), so they are merged on (symbol, ex_date), keeping
the row that has an amount. Absence of an entry means "nothing recorded in
this window", never "no events exist" - the window is stated on every use.

Run: .venv/bin/python -m pipeline.appdata.build_corporate_actions
"""
from __future__ import annotations

import json
from collections import defaultdict

from pipeline.appdata.common import APP_DIR, CORPORATE_ACTIONS_GLOB, RAW_DIR, UNIVERSE_GLOB, latest_dated_file


def _is_cancelled(place: str | None) -> bool:
    return bool(place) and "dibatalkan" in place.lower()


def build_dividends(rows: list[dict], universe_by_symbol: dict[str, dict]) -> dict[str, list[dict]]:
    merged: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["symbol"], row["ex_date"])
        existing = merged.get(key)
        if existing is None or (existing.get("dividend_amount") is None and row.get("dividend_amount") is not None):
            merged[key] = row

    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for (symbol, ex_date), row in merged.items():
        qv = (universe_by_symbol.get(symbol) or {}).get("query_values", {})
        amount = row.get("dividend_amount")
        last_close = qv.get("last_close_price")
        implied = amount / last_close if amount is not None and last_close else None
        by_symbol[symbol].append({
            "ex_date": ex_date,
            "cum_date": row.get("cum_date"),
            "recording_date": row.get("recording_date"),
            "payment_date": row.get("payment_date"),
            "amount": amount,
            "implied_yield": implied,
        })
    for events in by_symbol.values():
        events.sort(key=lambda e: e["ex_date"])
    return dict(by_symbol)


def build_agms(rows: list[dict]) -> dict[str, list[dict]]:
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append({
            "agm_date": row["agm_date"],
            "agm_time": row.get("agm_time"),
            "cancelled": _is_cancelled(row.get("agm_place")),
        })
    for events in by_symbol.values():
        events.sort(key=lambda e: e["agm_date"])
    return dict(by_symbol)


def build_rights_issues(rows: list[dict]) -> dict[str, list[dict]]:
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append({
            "ex_date": row["ex_date"],
            "price": row.get("price"),
            "old_ratio": row.get("old_ratio"),
            "new_ratio": row.get("new_ratio"),
            "trading_period_start": row.get("trading_period_start"),
            "trading_period_end": row.get("trading_period_end"),
        })
    for events in by_symbol.values():
        events.sort(key=lambda e: e["ex_date"])
    return dict(by_symbol)


def build_splits(rows: list[dict]) -> dict[str, list[dict]]:
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append({"date": row["date"], "ratio": row.get("ratio"), "split_ratio": row.get("split_ratio")})
    return dict(by_symbol)


def build_corporate_actions(response: dict, universe: list[dict]) -> dict[str, dict]:
    universe_by_symbol = {r["symbol"]: r for r in universe}
    dividends = build_dividends(
        (response.get("dividend") or []) + (response.get("upcoming_dividend") or []), universe_by_symbol
    )
    agms = build_agms(response.get("agm") or [])
    rights = build_rights_issues(response.get("right_issue") or [])
    splits = build_splits(response.get("stock_split") or [])

    symbols = set(dividends) | set(agms) | set(rights) | set(splits)
    return {
        symbol: {
            "dividends": dividends.get(symbol, []),
            "agms": agms.get(symbol, []),
            "rights_issues": rights.get(symbol, []),
            "stock_splits": splits.get(symbol, []),
        }
        for symbol in sorted(symbols)
    }


def main() -> None:
    source_path = latest_dated_file(RAW_DIR, CORPORATE_ACTIONS_GLOB)
    as_of = source_path.stem.replace("corporate_actions_", "")
    response = json.loads(source_path.read_text())
    universe = json.loads(latest_dated_file(RAW_DIR, UNIVERSE_GLOB).read_text())

    by_symbol = build_corporate_actions(response, universe)
    output = {
        "as_of": as_of,
        "source_file": source_path.name,
        "window": {"start": response["start"], "end": response["end"]},
        "by_symbol": by_symbol,
    }
    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "corporate_actions.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {source_path.name} (window {response['start']} to {response['end']})")
    print(f"{len(by_symbol)} companies with at least one event in the window")


if __name__ == "__main__":
    main()
