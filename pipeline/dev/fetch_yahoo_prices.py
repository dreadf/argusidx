"""
DEVELOPMENT-TIME ONLY. Never imported by, or shipped in, the ArgusIDX app.

Per RULES.md / plan section 8.3: Yahoo Finance is used exclusively to
validate hypotheses cheaply before spending Sectors credits on them. The
shipped product is Sectors-only, so nothing here may be reused at runtime.

Fetches IDX daily closing prices from Yahoo's batched `spark` endpoint and
caches them to data/dev_cache/, which is gitignored (this data is free and
re-fetchable, unlike the purchased data/raw/ files).

Two silent-failure traps hit while building this, kept here as comments so
they aren't rediscovered the hard way:
  1. Yahoo labels IDX equities as instrumentType "MUTUALFUND", not "EQUITY".
     Do not filter on instrumentType -- it silently discards every row.
  2. Double-check epoch/date conversions. An earlier run fetched 2025 data
     while believing it was 2026; the failure was silent and only caught by
     printing the actual date range returned.

Usage:
    python -m pipeline.dev.fetch_yahoo_prices --range 1y
    python -m pipeline.dev.fetch_yahoo_prices --range 5y
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FREE_FLOAT_PATH = REPO_ROOT / "data" / "raw" / "free_float_2026-09-06.json"
CACHE_DIR = REPO_ROOT / "data" / "dev_cache"

BATCH_SIZE = 10
RETRIES = 2
SLEEP_BETWEEN_BATCHES = 0.15
RETRY_SLEEP = 0.6


def _tickers_from_free_float() -> list[str]:
    data = json.loads(FREE_FLOAT_PATH.read_text())
    return [row["symbol"] for row in data if row.get("free_float") is not None]


def fetch_prices(symbols: list[str], yahoo_range: str) -> dict[str, list]:
    """Returns {symbol: [close, close, ...]} for range='1y', or
    {symbol: [[timestamp, close], ...]} for range='5y' (timestamps needed
    for the per-calendar-year regime check)."""
    keep_timestamps = yahoo_range != "1y"
    out: dict[str, list] = {}
    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i : i + BATCH_SIZE]
        url = (
            "https://query1.finance.yahoo.com/v7/finance/spark?symbols="
            + ",".join(batch)
            + f"&range={yahoo_range}&interval=1d"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        for attempt in range(RETRIES):
            try:
                r = json.load(urllib.request.urlopen(req, timeout=45))
                for item in r["spark"]["result"]:
                    resp = item["response"][0]
                    q = (resp.get("indicators", {}).get("quote") or [{}])[0]
                    ts = resp.get("timestamp") or []
                    closes = q.get("close") or []
                    if keep_timestamps:
                        pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
                        if len(pairs) >= 400:
                            out[item["symbol"]] = pairs
                    else:
                        vals = [c for c in closes if c is not None]
                        if len(vals) >= 120:
                            out[item["symbol"]] = vals
                break
            except Exception:
                time.sleep(RETRY_SLEEP)
        time.sleep(SLEEP_BETWEEN_BATCHES)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--range", choices=["1y", "5y"], default="1y")
    args = parser.parse_args()

    symbols = _tickers_from_free_float()
    print(f"Fetching {args.range} Yahoo prices for {len(symbols)} IDX tickers...")
    prices = fetch_prices(symbols, args.range)
    print(f"Got usable history for {len(prices)} of {len(symbols)} tickers.")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / f"prices_{args.range}.json"
    out_path.write_text(json.dumps(prices))
    print(f"Cached to {out_path}")


if __name__ == "__main__":
    main()
