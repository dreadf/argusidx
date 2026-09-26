"""
Base rate (situation C, "Masih di bawah puncak lama"): of stocks that fell
steeply from a peak and were still below that peak a year after the fall
began, how many were back at or above it another year later?

NOT a falsifiable hypothesis -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions were
frozen in EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 1)") before
outcomes were computed; run once.

- Fall event: exactly `m_recovery_after_fall._detect_fall_events` (first
  close <= 70% of the running peak, re-armed only by a new peak). Bars with
  a missing or non-positive close are dropped; stocks with fewer than 100
  usable bars are skipped. Raw `close`, 5-year research price cache.
- In the situation now: a fall event triggered at least 252 trading days
  before the last bar AND the latest close is still below that event's
  pre-fall peak price.
- Base rate: events with more than 199 bars after trigger + 252 (i.e. at
  least 200 bars; fewer are left out). Of those still below the peak at
  trigger + 252, the share at or above the peak at trigger + 504. When the
  cache ends before trigger + 504 (but 200+ bars exist after trigger + 252),
  the last bar stands in for trigger + 504, the same slack
  `m_recovery_after_fall` allows; the number of such events is reported, and
  the rate for exact trigger + 504 events alone is printed beside it.
- Limits: one stock can contribute several events, which are not independent;
  the cache spans about five years, so the base rate rests on falls that
  began in the early years of the cache.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_long_below_peak
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.hypotheses.m_recovery_after_fall import _detect_fall_events

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

YEAR_BARS = 252
MIN_BARS_AFTER = 200
MIN_HISTORY_BARS = 100


def usable_closes(entry: dict | None) -> list[float] | None:
    if not entry:
        return None
    closes = [c for c in entry.get("close", []) if c is not None and c > 0]
    return closes if len(closes) >= MIN_HISTORY_BARS else None


def in_situation_now(closes: list[float]) -> dict | None:
    """The first qualifying fall event (triggered >= 252 bars ago, latest close still below its peak), or None."""
    last = len(closes) - 1
    for ev in _detect_fall_events(closes):
        if ev["trigger_idx"] <= last - YEAR_BARS and closes[last] < ev["peak_price"]:
            return ev
    return None


def event_result(closes: list[float], ev: dict) -> dict | None:
    """Outcome for one event, or None if it is left out (fewer than 200 bars after trigger + 252)."""
    last = len(closes) - 1
    t252 = ev["trigger_idx"] + YEAR_BARS
    if last - t252 < MIN_BARS_AFTER:
        return None
    still_below = closes[t252] < ev["peak_price"]
    t504 = ev["trigger_idx"] + 2 * YEAR_BARS
    end = min(t504, last)
    return {
        "still_below_at_252": still_below,
        "recovered_by_504": closes[end] >= ev["peak_price"],
        "truncated": t504 > last,
    }


def _rate(count: int, n: int) -> dict:
    return {"n": n, "count": count, "rate": (count / n) if n else None}


def build_long_below_peak(prices: dict) -> dict:
    in_now: list[str] = []
    results: list[dict] = []
    for sym, entry in prices.items():
        closes = usable_closes(entry)
        if closes is None:
            continue
        if in_situation_now(closes) is not None:
            in_now.append(sym)
        for ev in _detect_fall_events(closes):
            res = event_result(closes, ev)
            if res is not None:
                results.append(res)
    below = [r for r in results if r["still_below_at_252"]]
    exact = [r for r in below if not r["truncated"]]
    return {
        "in_situation_now": sorted(in_now),
        "events_measurable": len(results),
        "still_below_at_252": len(below),
        "recovered_by_504": _rate(sum(r["recovered_by_504"] for r in below), len(below)),
        "of_which_truncated_endpoint": sum(r["truncated"] for r in below),
        "recovered_exact_504_only": _rate(sum(r["recovered_by_504"] for r in exact), len(exact)),
    }


def main() -> None:
    result = build_long_below_peak(json.loads(PRICES_5Y_PATH.read_text()))
    print("Stocks in the situation now:", len(result["in_situation_now"]))
    print("Symbols:", ", ".join(result["in_situation_now"]))
    print("Fall events with enough follow-up (200+ bars after trigger+252):", result["events_measurable"])
    print("  of which still below the peak at trigger+252:", result["still_below_at_252"])
    print("Back at/above the peak at trigger+504 (of those still below):", result["recovered_by_504"])
    print("  events using the last bar instead of exact trigger+504:", result["of_which_truncated_endpoint"])
    print("  same rate, exact trigger+504 events only:", result["recovered_exact_504_only"])


if __name__ == "__main__":
    main()
