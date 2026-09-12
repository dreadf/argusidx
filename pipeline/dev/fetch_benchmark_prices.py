"""
Dev-only fetcher for the H16 base-rate benchmarks: the IDX Composite
index, gold (in USD), and the USD/IDR exchange rate (used to convert
gold into rupiah terms).

Same status as fetch_yahoo_prices.py: dev/validation only, never
imported by shipped code (RULES.md), reuses that module's `fetch_prices`
(retry/backoff logic) rather than reimplementing it, so a bug fixed
there is fixed here too.

Tickers:
    ^JKSE    -- IDX Composite index (the "just buy the market" benchmark)
    GC=F     -- Gold futures, USD/troy oz
    USDIDR=X -- USD/IDR exchange rate (gold_idr = GC=F * USDIDR=X)

Run:
    .venv/bin/python -m pipeline.dev.fetch_benchmark_prices
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.dev.fetch_yahoo_prices import fetch_prices

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "dev_cache"
OUT_PATH = CACHE_DIR / "benchmarks_5y.json"

TICKERS = ["^JKSE", "GC=F", "USDIDR=X"]


def main() -> None:
    print(f"Fetching {len(TICKERS)} benchmark tickers (5y, daily)...")
    fetched, failed = fetch_prices(TICKERS, "5y")
    if failed:
        print(f"FAILED (after retries): {failed}")
    for sym, entry in fetched.items():
        print(f"  {sym}: {len(entry['close'])} bars")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(fetched))
    print(f"Cached to {OUT_PATH}: {len(fetched)} of {len(TICKERS)} tickers.")


if __name__ == "__main__":
    main()
