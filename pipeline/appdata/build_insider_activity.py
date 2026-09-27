"""Build data/app/insider_activity.json from the purchased insider filing
feeds (data/raw/insider_buys_*.jsonl, insider_sells_*.jsonl).

This is a DERIVED aggregate, not the raw feed reformatted: Track 03's
qualifying test explicitly excludes reformatted raw data, and both feeds
are already-purchased research inputs that six hypotheses (H8, H8b, H9d,
plus H9/H9b/H9c on the sentiment side) were run against, all coming back
null, falsified, or inconclusive (EXPERIMENT.md). What ships here is a
per-stock and market-wide COUNT and NET DIRECTION over the disclosed
window: a fact log, paired on the stock page with the shipped null
finding that insider selling did not predict a crash (H8): never a
signal, never a raw transaction dump.

Deliberately NOT surfaced: `share_percentage_after` and similar
magnitude fields. A quick scan of the raw feed turned up values over
900% (a real record, not a parsing bug: an apparent data-quality
artifact in the purchased feed itself), so this module only derives
counts and dates, values simple enough that one bad record can't distort
the shown aggregate the way a magnitude figure could.

Run: .venv/bin/python -m pipeline.appdata.build_insider_activity
"""
from __future__ import annotations

import json

from pipeline.appdata.common import (
    APP_DIR,
    INSIDER_BUYS_GLOB,
    INSIDER_SELLS_GLOB,
    RAW_DIR,
    UNIVERSE_GLOB,
    latest_dated_file,
)


def _load_jsonl(path) -> list[dict]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_by_symbol(buys: list[dict], sells: list[dict]) -> dict[str, dict]:
    by_symbol: dict[str, dict] = {}

    def touch(symbol: str) -> dict:
        return by_symbol.setdefault(
            symbol, {"buy_count": 0, "sell_count": 0, "last_transaction_date": None}
        )

    for row in buys:
        symbol = row.get("symbol")
        if not symbol:
            continue
        entry = touch(symbol)
        entry["buy_count"] += 1
        date = (row.get("timestamp") or "")[:10]
        if date and (entry["last_transaction_date"] is None or date > entry["last_transaction_date"]):
            entry["last_transaction_date"] = date

    for row in sells:
        symbol = row.get("symbol")
        if not symbol:
            continue
        entry = touch(symbol)
        entry["sell_count"] += 1
        date = (row.get("timestamp") or "")[:10]
        if date and (entry["last_transaction_date"] is None or date > entry["last_transaction_date"]):
            entry["last_transaction_date"] = date

    for entry in by_symbol.values():
        if entry["buy_count"] > entry["sell_count"]:
            entry["net_direction"] = "net_buying"
        elif entry["sell_count"] > entry["buy_count"]:
            entry["net_direction"] = "net_selling"
        else:
            entry["net_direction"] = "balanced"

    return by_symbol


def build_market_summary(by_symbol: dict[str, dict], universe_symbols: set[str]) -> dict:
    """Counts only symbols inside the universe, so numerator and denominator match."""
    in_universe = [e for s, e in by_symbol.items() if s in universe_symbols]
    net_buying = sum(1 for e in in_universe if e["net_direction"] == "net_buying")
    net_selling = sum(1 for e in in_universe if e["net_direction"] == "net_selling")
    balanced = sum(1 for e in in_universe if e["net_direction"] == "balanced")
    return {
        "universe_count": len(universe_symbols),
        "companies_with_activity": len(in_universe),
        "net_buying": net_buying,
        "net_selling": net_selling,
        "balanced": balanced,
    }


def main() -> None:
    buys_path = latest_dated_file(RAW_DIR, INSIDER_BUYS_GLOB)
    sells_path = latest_dated_file(RAW_DIR, INSIDER_SELLS_GLOB)
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)

    buys = _load_jsonl(buys_path)
    sells = _load_jsonl(sells_path)
    universe_symbols = {row["symbol"] for row in json.loads(universe_path.read_text())}
    universe_count = len(universe_symbols)

    by_symbol = build_by_symbol(buys, sells)
    summary = build_market_summary(by_symbol, universe_symbols)

    dates = [r["timestamp"][:10] for r in buys + sells if r.get("timestamp")]

    output = {
        "as_of": universe_path.stem.replace("universe_", ""),
        "source_files": [buys_path.name, sells_path.name],
        "window": {"start": min(dates), "end": max(dates)} if dates else None,
        "summary": summary,
        "by_symbol": by_symbol,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "insider_activity.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {buys_path.name}, {sells_path.name}")
    print(f"  {summary['companies_with_activity']} of {universe_count} companies with any filing")
    print(f"  net_buying={summary['net_buying']} net_selling={summary['net_selling']} balanced={summary['balanced']}")


if __name__ == "__main__":
    main()
