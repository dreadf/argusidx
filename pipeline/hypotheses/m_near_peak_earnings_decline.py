"""
Base rate (situation I3, "Dekat puncak, laba menurun"): what happened over
1 May to 4 Sep to stocks that sat near their high while reported earnings
had fallen?

NOT a falsifiable hypothesis -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions frozen in
EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 1)"); run once.

- Evaluated on 1 May of Y+1 for Y = 2022, 2023, 2024 (earnings[Y] is public
  by then, the H5/H10/H17 reporting-lag convention).
- Trigger: the last close on or before 1 May of Y+1 is within 10% of the
  running maximum close (over all cached bars up to that date), i.e.
  (max - close) / max <= 0.10 (the same "<=" as the flag), AND earnings[Y] <
  earnings[Y-1] with both reported. Raw `close` for the trigger.
- Outcome window, the H5/H10/H17 window: `adjclose` at the bar nearest 1 May
  of Y+1 to the bar nearest 4 Sep of Y+1 (`stats.nearest_value`, 10-day gap
  limit). Reported: share with a negative return, and share beating the
  median stock. "Median stock" = the median window return of ALL cached
  stocks with a valid return that year (not only triggered ones); "beating"
  is strictly greater.
- Proxy, disclosed: the app flag uses the all-time high from Sectors; the base
  rate can only use the maximum close inside the ~5-year cache, which starts
  in Sep 2021 (so the running maximum for 2022 covers only about 7 months).
- Limits: three formation years, one window each; stocks are not independent
  within a year (common market move).

Run:
    .venv/bin/python -m pipeline.hypotheses.m_near_peak_earnings_decline
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from pipeline.stats import nearest_value

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

NEAR_PEAK_THRESHOLD = 0.10
YEARS = [2022, 2023, 2024]
RETURN_FIELD = "adjclose"
MAX_PRICE_GAP_DAYS = 10


def earnings_declined(qv: dict, year: int) -> bool:
    a, b = qv.get(f"earnings[{year}]"), qv.get(f"earnings[{year - 1}]")
    return a is not None and b is not None and a < b


def near_peak_on(entry: dict, cutoff: datetime) -> bool | None:
    """True if the last close on or before `cutoff` is within 10% of the running max close up to then.

    None if no bar exists on or before the cutoff (or no positive close).
    """
    cutoff_ts = cutoff.timestamp()
    closes = [
        c
        for t, c in zip(entry["timestamps"], entry["close"])
        if t <= cutoff_ts and c is not None and c > 0
    ]
    if not closes:
        return None
    peak = max(closes)
    return (peak - closes[-1]) / peak <= NEAR_PEAK_THRESHOLD


def window_return(entry: dict, start: datetime, end: datetime) -> float | None:
    p0 = nearest_value(entry, start, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
    p1 = nearest_value(entry, end, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
    if p0 is None or p1 is None:
        return None
    return p1 / p0 - 1


def build_year(universe: list[dict], prices: dict, year: int) -> dict:
    start = datetime(year + 1, 5, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 9, 4, tzinfo=timezone.utc)
    cutoff = datetime(year + 1, 5, 1, 23, 59, 59, tzinfo=timezone.utc)
    qv_by_symbol = {r.get("symbol"): r.get("query_values") or {} for r in universe}
    returns: dict[str, float] = {}
    for sym, entry in prices.items():
        r = window_return(entry, start, end)
        if r is not None:
            returns[sym] = r
    median_return = statistics.median(returns.values()) if returns else None
    triggered = []
    for sym, ret in returns.items():
        qv = qv_by_symbol.get(sym)
        if qv is None or not earnings_declined(qv, year):
            continue
        if near_peak_on(prices[sym], cutoff):
            triggered.append(ret)
    return {"year": year, "median_return": median_return, "stocks_with_return": len(returns), "triggered_returns": triggered}


def summarize(returns: list[float], medians: list[float]) -> dict:
    """`medians[i]` is the median stock's return in the year of `returns[i]`."""
    n = len(returns)
    neg = sum(1 for r in returns if r < 0)
    beat = sum(1 for r, m in zip(returns, medians) if r > m)
    return {
        "n": n,
        "negative": neg,
        "share_negative": (neg / n) if n else None,
        "beat_median": beat,
        "share_beat_median": (beat / n) if n else None,
    }


def build_near_peak_earnings_decline(universe: list[dict], prices: dict) -> dict:
    per_year = [build_year(universe, prices, y) for y in YEARS]
    out: dict = {"by_year": {}}
    pooled_r: list[float] = []
    pooled_m: list[float] = []
    for py in per_year:
        rs = py["triggered_returns"]
        ms = [py["median_return"]] * len(rs)
        pooled_r += rs
        pooled_m += ms
        out["by_year"][py["year"]] = {
            **summarize(rs, ms),
            "median_stock_return": py["median_return"],
            "stocks_with_return": py["stocks_with_return"],
        }
    out["pooled"] = summarize(pooled_r, pooled_m)
    return out


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices = json.loads(PRICES_5Y_PATH.read_text())
    result = build_near_peak_earnings_decline(universe, prices)
    for y, s in result["by_year"].items():
        print(f"Y={y} (1 May {y + 1} to 4 Sep {y + 1}):", json.dumps(s))
    print("Pooled:", json.dumps(result["pooled"]))


if __name__ == "__main__":
    main()
