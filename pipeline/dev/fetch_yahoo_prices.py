"""
DEVELOPMENT-TIME ONLY. Never imported by, or shipped in, the ArgusIDX app.

Per RULES.md / plan section 8.3: Yahoo Finance is used exclusively to
validate hypotheses cheaply before spending Sectors credits on them. The
shipped product is Sectors-only, so nothing here may be reused at runtime.

Fetches IDX daily prices from Yahoo's per-symbol `/v8/finance/chart`
endpoint and caches them to data/dev_cache/, which is gitignored (this
data is free and re-fetchable, unlike the purchased data/raw/ files).

Switched from `/v7/finance/spark` (2026-09-09) -- that endpoint is built
for lightweight sparkline widgets and silently drops a large share of
history for exactly the small/thin-float symbols this project cares
about most (GOTO.JK: 127 -> 244 of ~249 days on `chart`; see
EXPERIMENT.md/docs/DATA.md for the full before/after). `chart` also
exposes `adjclose` (dividend-and-split-adjusted), which `spark` never
did -- H5's return calculation needs it (see docs/DATA.md's close-vs-
adjclose note). The trade-off, verified before committing to this:
`chart` has no batch mode, so a full universe fetch is ~1,700-1,900
sequential single-symbol calls (2 ranges) instead of ~85 batched ones --
still free, just slower (several minutes, not seconds).

Cache schema (same shape for both --range values, unlike the old
spark-based cache, which stored bare close-only lists for 1y and
[timestamp, close] pairs for 5y):

    {symbol: {"timestamps": [...], "close": [...], "adjclose": [...]}}

All three arrays are the same length and index-aligned; any day missing
either close or adjclose is dropped from all three so callers never see
a length mismatch. Consumers pick close (H1: raw price movement, what a
retail user's chart actually shows) or adjclose (H5: total return
including dividends) explicitly -- see docs/DATA.md.

Two silent-failure traps hit while building the original (spark-based)
version, kept here as comments so they aren't rediscovered the hard way:
  1. Yahoo's `spark` endpoint labels IDX equities as instrumentType
     "MUTUALFUND", not "EQUITY" -- do not filter on instrumentType, it
     silently discards every row. `chart`'s meta.instrumentType read
     "EQUITY" for the one symbol spot-checked (BBCA.JK) while building
     this fix; not re-verified across the full universe, so the same
     caution still applies if this ever gets filtered on again.
  2. Double-check epoch/date conversions. An earlier run fetched 2025
     data while believing it was 2026; the failure was silent and only
     caught by printing the actual date range returned.

A mid-run failure trap specific to this endpoint: a ~1,700-1,900-call
sequential run is long enough that a transient rate-limit or network
blip could silently degrade the cache if failures aren't tracked. This
version prints fetched-vs-failed counts and the list of symbols still
failing after one retry -- never treat a run as complete without reading
that summary.

Usage:
    python -m pipeline.dev.fetch_yahoo_prices --range 1y
    python -m pipeline.dev.fetch_yahoo_prices --range 5y
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FREE_FLOAT_PATH = REPO_ROOT / "data" / "raw" / "free_float_2026-09-06.json"
CACHE_DIR = REPO_ROOT / "data" / "dev_cache"

MIN_BARS = {"1y": 120, "5y": 400}
RETRIES = 2
SLEEP_BETWEEN_REQUESTS = 0.12
RETRY_SLEEP = 0.6


def _tickers_from_free_float() -> list[str]:
    data = json.loads(FREE_FLOAT_PATH.read_text())
    return [row["symbol"] for row in data if row.get("free_float") is not None]


def _fetch_one(symbol: str, yahoo_range: str) -> dict | None:
    """One symbol, one range. Returns the aligned {timestamps, close,
    adjclose} dict, or None if Yahoo has nothing usable for it (unknown
    symbol, error object, or below MIN_BARS after dropping incomplete
    days). Raises on a network/HTTP/JSON failure that ISN'T a plain "no
    such symbol" 404 -- the caller decides whether that's worth a retry.

    A 404 is handled here, not left to propagate, because it's Yahoo's
    actual response shape for an unknown symbol [verified against the
    live endpoint, 2026-09-09: a bad symbol returns HTTP 404 with body
    {"chart": {"result": null, "error": {"code": "Not Found", ...}}}].
    `urllib.request.urlopen` raises `HTTPError` before any code below
    could inspect that body, so treating 404 as "not found" here (instead
    of via the now-unreachable `results` check below, which only fires
    for a 200 response Yahoo doesn't actually send for this case) is what
    makes a permanently-missing symbol get excluded instead of retried
    three times and reported as a transient "Failed" symbol."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?range={yahoo_range}&interval=1d&events=div,split"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # unknown/delisted symbol -- permanent, not worth retrying
        raise  # other HTTP errors (429, 5xx) are worth a retry

    chart = payload.get("chart") or {}
    results = chart.get("result")
    if not results:
        return None  # defensive: no result but not a 404 either

    r = results[0]
    timestamps = r.get("timestamp") or []
    indicators = r.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    closes = quote.get("close") or []
    adjcloses = (indicators.get("adjclose") or [{}])[0].get("adjclose") or []
    if not (len(timestamps) == len(closes) == len(adjcloses)):
        return None  # malformed/unexpected shape -- don't guess at alignment

    ts, cl, adj = [], [], []
    for t, c, a in zip(timestamps, closes, adjcloses):
        if c is None or a is None:
            continue
        ts.append(t)
        cl.append(c)
        adj.append(a)

    if len(cl) < MIN_BARS[yahoo_range]:
        return None
    return {"timestamps": ts, "close": cl, "adjclose": adj}


_RETRYABLE_ERRORS = (OSError, json.JSONDecodeError)
# OSError, not narrower: urllib.error.URLError/HTTPError are themselves
# OSError subclasses, and so are the raw socket/SSL failures that can
# surface directly from http.client during a long sequential run (hit
# live: a bare ConnectionResetError from a mid-read connection drop,
# which is NOT a URLError -- catching only URLError let it crash the
# whole script instead of being retried like any other network hiccup).
# Still NOT bare Exception: a KeyError/AttributeError here means
# _fetch_one hit a response shape (or a code bug) this script doesn't
# understand, and that must crash loudly rather than get silently
# absorbed into "Failed" -- see pipeline/stats.py's own fail-loudly
# convention for why this matters.


def fetch_prices(symbols: list[str], yahoo_range: str) -> tuple[dict[str, dict], list[str]]:
    """Returns (fetched, failed_after_retry). `fetched` maps symbol -> the
    aligned dict from _fetch_one (only symbols that returned usable data).
    A symbol that reached Yahoo fine but had too little history is not a
    "failure" -- it's just excluded, same as it always has been."""
    fetched: dict[str, dict] = {}

    def attempt(symbol: str) -> bool:
        """True if this symbol is resolved (fetched or genuinely empty),
        False if it should be retried."""
        for attempt_num in range(RETRIES):
            try:
                data = _fetch_one(symbol, yahoo_range)
                if data is not None:
                    fetched[symbol] = data
                return True
            except _RETRYABLE_ERRORS:
                if attempt_num < RETRIES - 1:
                    time.sleep(RETRY_SLEEP)
        return False

    def run_pass(pass_symbols: list[str]) -> list[str]:
        still_failed = []
        for symbol in pass_symbols:
            if not attempt(symbol):
                still_failed.append(symbol)
            time.sleep(SLEEP_BETWEEN_REQUESTS)
        return still_failed

    failed = run_pass(symbols)
    if failed:
        print(f"  {len(failed)} symbols failed after {RETRIES} attempts each; retrying once more...")
        failed = run_pass(failed)

    return fetched, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--range", choices=["1y", "5y"], default="1y")
    args = parser.parse_args()

    symbols = _tickers_from_free_float()
    print(f"Fetching {args.range} Yahoo prices for {len(symbols)} IDX tickers "
          f"(sequential, ~{len(symbols) * SLEEP_BETWEEN_REQUESTS:.0f}s minimum)...")
    fetched, failed = fetch_prices(symbols, args.range)

    excluded = len(symbols) - len(fetched) - len(failed)
    print(f"Fetched: {len(fetched)} of {len(symbols)}")
    print(f"Excluded (reached Yahoo, but below the {MIN_BARS[args.range]}-bar minimum "
          f"or missing entirely): {excluded}")
    print(f"Failed (network/HTTP/JSON error, {RETRIES} attempts + 1 retry pass, "
          f"still unresolved): {len(failed)}")
    if failed:
        print(f"  Failed symbols: {', '.join(failed)}")
        print("  Re-run this script to retry them, or note them explicitly in "
              "docs/DATA.md if they persist.")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / f"prices_{args.range}.json"
    # Merge, don't overwrite: a symbol in `failed` keeps whatever was cached
    # for it last time (if anything), so a transient outage that fails N
    # symbols can't silently shrink the cache by N entries. A symbol that
    # was simply excluded this run (below MIN_BARS, or gone from Yahoo
    # entirely with a clean 404) is NOT carried over -- that's a real
    # re-evaluation, not a failure, and papering over it would hide an
    # actual change in what Yahoo has.
    existing = json.loads(out_path.read_text()) if out_path.exists() else {}
    merged = dict(fetched)
    carried_over = []
    stale_schema = []
    for sym in failed:
        entry = existing.get(sym)
        # A cache from before the schema migration (list, not a dict with
        # a "close" key) must never be merged into the new-schema file --
        # every consumer now expects {timestamps, close, adjclose}, and a
        # single old-shape entry hiding among new-shape ones would only
        # surface as a confusing per-symbol crash much later.
        if entry is None:
            continue
        # All three keys, not just "close" -- an entry with "close" but
        # missing "adjclose"/"timestamps" (e.g. a partially-written file
        # from an interrupted run) would otherwise pass this check and
        # get carried into the merged cache, then raise a KeyError deep in
        # an unrelated hypothesis run the first time something reads the
        # missing field (found by /code-review, 2026-09-12).
        if isinstance(entry, dict) and {"timestamps", "close", "adjclose"} <= entry.keys():
            merged[sym] = entry
            carried_over.append(sym)
        else:
            stale_schema.append(sym)
    if stale_schema:
        print(f"  {len(stale_schema)} failed symbols had a pre-migration-schema cache "
              f"entry -- NOT carried over (would corrupt the new schema): "
              f"{', '.join(stale_schema)}")
    out_path.write_text(json.dumps(merged))
    print(f"Cached to {out_path}: {len(fetched)} freshly fetched"
          + (f", {len(carried_over)} carried over from the previous cache "
             "(failed this run, kept last-known-good data)" if carried_over else "")
          + f", {len(merged)} total.")


if __name__ == "__main__":
    main()
