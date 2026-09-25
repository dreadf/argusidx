"""DEVELOPMENT-TIME ONLY. Never imported by, or shipped in, the ArgusIDX app.

Cross-checks the free Yahoo Finance price cache (data/dev_cache/) that
every return- and volatility-based finding was measured on, against
Sectors' own daily closes (`/v2/daily/{symbol}/`), for a small stratified
sample. This closes the "Sectors price cross-check" that docs/PLAN.md
8.3 and BACKLOG.md list as owed: the research layer's outcome variable is
Yahoo, so we check Yahoo against the licensed source.

What it does and does not establish:
- It checks that Yahoo's raw `close` matches Sectors' `close` on the same
  dates, and how many of Sectors' trading days Yahoo also has (coverage).
- It covers ONE recent 90-day window (the endpoint's maximum) for ~20
  symbols. It does not re-run any hypothesis, and says nothing about
  older years in the cache. A pass is evidence the two sources agree
  today for a sample, not proof for every symbol-year.

Live schema, confirmed 2026-09-20: `/v2/daily/{symbol}/` costs 1 credit
per call, max 90-day window, `end` may not be in the future.
Approved: user approved the step-4 credit plan on 2026-09-20; 20 calls =
20 credits, kept at the standing <=20-credit limit on purpose.

Saves after every call, never overwrites an existing dated file.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.dev.crosscheck_sectors_prices
"""
from __future__ import annotations

import json
import random
import statistics
from datetime import date, datetime, timedelta, timezone

from pipeline.appdata.common import RAW_DIR, REPO_ROOT, UNIVERSE_GLOB, latest_dated_file
from pipeline.sectors_client import get

PRICES_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
OUT_PATH = RAW_DIR / f"sectors_daily_crosscheck_{date.today()}.json"
SEED = 20260920
PER_STRATUM = {"large": 7, "mid": 7, "small": 6}
WINDOW_DAYS = 90
MIN_HISTORY_DAYS = 250


def _yahoo_by_date(entry: dict) -> dict[str, float]:
    return {
        datetime.fromtimestamp(ts, timezone.utc).date().isoformat(): close
        for ts, close in zip(entry["timestamps"], entry["close"])
        if close is not None
    }


def compare_symbol(sectors_rows: list[dict], yahoo_closes: dict[str, float]) -> dict:
    """Per-symbol agreement. `coverage` = share of Sectors' trading days that
    Yahoo also has; diffs are |yahoo/sectors - 1| on matched days only."""
    sectors = {r["date"]: r["close"] for r in sectors_rows if r.get("close") not in (None, 0)}
    matched = [d for d in sectors if d in yahoo_closes]
    diffs = [abs(yahoo_closes[d] / sectors[d] - 1) for d in matched]
    return {
        "n_sectors_days": len(sectors),
        "n_matched_days": len(matched),
        "coverage": len(matched) / len(sectors) if sectors else None,
        "median_abs_diff": statistics.median(diffs) if diffs else None,
        "max_abs_diff": max(diffs) if diffs else None,
        "days_over_1pct": sum(1 for x in diffs if x > 0.01),
    }


def summarize(per_symbol: dict[str, dict]) -> dict:
    scored = {s: r for s, r in per_symbol.items() if r["n_matched_days"] > 0}
    all_days = sum(r["n_matched_days"] for r in scored.values())
    over_1pct = sum(r["days_over_1pct"] for r in scored.values())
    return {
        "symbols_checked": len(per_symbol),
        "symbols_with_overlap": len(scored),
        "matched_days_total": all_days,
        "days_over_1pct_total": over_1pct,
        "share_of_matched_days_within_1pct": (1 - over_1pct / all_days) if all_days else None,
        "median_of_symbol_median_diffs": statistics.median(r["median_abs_diff"] for r in scored.values()) if scored else None,
        "worst_symbol_max_diff": max((r["max_abs_diff"] for r in scored.values()), default=None),
        "min_coverage": min((r["coverage"] for r in scored.values()), default=None),
    }


def pick_sample(universe: list[dict], prices: dict) -> dict[str, list[str]]:
    eligible = [
        r for r in universe
        if r["symbol"] in prices
        and len(prices[r["symbol"]].get("timestamps", [])) >= MIN_HISTORY_DAYS
        and r["query_values"].get("market_cap")
    ]
    eligible.sort(key=lambda r: r["query_values"]["market_cap"], reverse=True)
    third = len(eligible) // 3
    strata = {"large": eligible[:third], "mid": eligible[third : 2 * third], "small": eligible[2 * third :]}
    rng = random.Random(SEED)
    return {name: sorted(r["symbol"] for r in rng.sample(rows, PER_STRATUM[name])) for name, rows in strata.items()}


def main() -> None:
    if OUT_PATH.exists():
        raise FileExistsError(f"{OUT_PATH} already exists - refusing to overwrite purchased data.")

    universe = json.loads(latest_dated_file(RAW_DIR, UNIVERSE_GLOB).read_text())
    prices = json.loads(PRICES_PATH.read_text())
    last_yahoo = max(
        datetime.fromtimestamp(v["timestamps"][-1], timezone.utc).date() for v in prices.values() if v.get("timestamps")
    )
    end = min(last_yahoo, date.today() - timedelta(days=1))
    start = end - timedelta(days=WINDOW_DAYS - 1)

    sample = pick_sample(universe, prices)
    symbols = [s for group in sample.values() for s in group]
    print(f"{len(symbols)} calls, {len(symbols)} credits (1 per call, approved). Window {start} to {end}.")

    raw: dict[str, list[dict]] = {}
    for i, symbol in enumerate(symbols, start=1):
        bare = symbol.replace(".JK", "")
        rows = get(f"/daily/{bare}/", {"start": start.isoformat(), "end": end.isoformat()})
        raw[symbol] = rows
        print(f"  [{i}/{len(symbols)}] {symbol}: {len(rows)} days")
        OUT_PATH.write_text(json.dumps({"window": [str(start), str(end)], "sample": sample, "raw": raw}, indent=2))

    per_symbol = {s: compare_symbol(raw[s], _yahoo_by_date(prices[s])) for s in symbols}
    summary = summarize(per_symbol)
    OUT_PATH.write_text(
        json.dumps({"window": [str(start), str(end)], "sample": sample, "raw": raw, "per_symbol": per_symbol, "summary": summary}, indent=2)
    )
    print("\nSummary:")
    print(json.dumps(summary, indent=2))
    print(f"\nSpent: {len(symbols)} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
