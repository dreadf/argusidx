"""
Base rate (situation S1): what does a stock's price usually do in the 60
trading days after a sudden jump of 40% or more within 20 trading days?

NOT a falsifiable hypothesis -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions were
frozen in EXPERIMENT.md ("Pre-registration, 2026-09-22") before outcomes
were computed. No comparison against any other group is made or implied.

- Event: the first close with close[t] / close[t-20] - 1 >= +0.40. After an
  event the next one for the same stock needs at least 40 more trading days.
  Bars with a missing or non-positive close are dropped. Raw `close`, 5-year
  research price cache.
- Outcome, from the event-day close over the next 60 trading days:
  (a) share of events whose close 60 trading days later is below it,
  (b) median and 25th/75th percentile of that 60-day change,
  (c) share that closed 30% or more below it at some point in the 60 days.
  Events with fewer than 60 later bars are left out.
- Limits: events of one stock can overlap, so they are not independent; a
  stock-level view (first event per stock) is reported beside the pooled one.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_recent_spike
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

SPIKE_THRESHOLD = 0.40
LOOKBACK_BARS = 20
REFRACTORY_BARS = 40
HORIZON_BARS = 60
DEEP_DROP = 0.70  # a close at or below 70% of the event-day close
MIN_HISTORY_BARS = 100


def detect_spike_events(closes: list[float]) -> list[int]:
    """Indices of spike events (see module docstring)."""
    events: list[int] = []
    last = None
    for i in range(LOOKBACK_BARS, len(closes)):
        if last is not None and i - last < REFRACTORY_BARS:
            continue
        if closes[i] >= closes[i - LOOKBACK_BARS] * (1 + SPIKE_THRESHOLD):  # multiply: 140/100-1 is 0.3999... in floats
            events.append(i)
            last = i
    return events


def event_outcome(closes: list[float], index: int) -> dict | None:
    """The three outcome measures for one event, or None if fewer than 60 later bars exist."""
    if index + HORIZON_BARS >= len(closes):
        return None
    base = closes[index]
    window = closes[index + 1 : index + HORIZON_BARS + 1]
    return {
        "change": window[-1] / base - 1,
        "deep_drop": min(window) <= base * DEEP_DROP,
    }


def summarize_outcomes(outcomes: list[dict]) -> dict | None:
    if not outcomes:
        return None
    changes = sorted(o["change"] for o in outcomes)
    q = statistics.quantiles(changes, n=4) if len(changes) >= 2 else [changes[0]] * 3
    n = len(outcomes)
    return {
        "n_events": n,
        "share_below_event_close": sum(1 for c in changes if c < 0) / n,
        "median_change": statistics.median(changes),
        "p25_change": q[0],
        "p75_change": q[2],
        "share_deep_drop": sum(1 for o in outcomes if o["deep_drop"]) / n,
    }


def usable_closes(entry: dict | None) -> list[float] | None:
    if not entry:
        return None
    closes = [c for c in entry.get("close", []) if c is not None and c > 0]
    return closes if len(closes) >= MIN_HISTORY_BARS else None


def build_spike_base_rate(prices: dict) -> dict:
    """Pooled events, first event per stock, and how many stocks had at least one event."""
    pooled: list[dict] = []
    first_per_stock: list[dict] = []
    stocks_with_event = 0
    for entry in prices.values():
        closes = usable_closes(entry)
        if closes is None:
            continue
        events = detect_spike_events(closes)
        if events:
            stocks_with_event += 1
        outcomes = [o for o in (event_outcome(closes, i) for i in events) if o is not None]
        pooled.extend(outcomes)
        if outcomes:
            first_per_stock.append(outcomes[0])
    return {
        "pooled": summarize_outcomes(pooled),
        "first_event_per_stock": summarize_outcomes(first_per_stock),
        "stocks_with_event": stocks_with_event,
    }


def main() -> None:
    result = build_spike_base_rate(json.loads(PRICES_5Y_PATH.read_text()))
    print("Pooled events:", result["pooled"])
    print("First event per stock:", result["first_event_per_stock"])
    print("Stocks with at least one event:", result["stocks_with_event"])


if __name__ == "__main__":
    main()
