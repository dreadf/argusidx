"""
Base rate: of IDX stocks that fell steeply (~30%+ from a peak), what
fraction were back to their pre-fall level a year later, vs. still
down?

NOT a falsifiable hypothesis -- descriptive base rate, same category as
H16/loss-maker-turnaround/typical-drawdown (no explore/holdout split,
no significance test, not counted in the trial counter). From
docs/PLAN.md's Chunk M: serves "should I average down?" -- flagged
there as the most unserved decision in the product's own problem
statement, and more common than IPO subscription.

Data: Yahoo 5-year dev cache (`close`, matching H1's raw-price
convention -- this is about the chart a retail investor actually
watches, same reasoning H1 uses).

Event definition, decided up front to avoid double-counting the SAME
fall as multiple events (the H14/H9b lesson on overlapping windows,
applied here to price events instead of news bins): walk each stock's
close series tracking a running peak (a monotonically non-decreasing
value). The first time price closes at or below 70% of the running
peak, that's a FALL EVENT, anchored at that trigger date/price against
that peak. Once triggered, no new event can register against the SAME
peak -- only once the running peak itself grows past the triggering
peak (a genuine new high) does the detector re-arm. This means a single
prolonged decline registers exactly once, not once per day it stays
below the threshold.

Outcome measured from the TRIGGER date (not the eventual trough, which
would require looking into the future to identify -- a look-ahead risk
this project's own discipline exists to avoid): "recovered" means the
close price ~252 trading days after the trigger is back at or above the
PRE-FALL PEAK price. Requires at least ~200 trading days of history
after the trigger to be measured at all -- events too close to the end
of the owned price history are excluded rather than guessed at.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_recovery_after_fall
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

FALL_THRESHOLD = 0.70  # trigger when price <= 70% of running peak (a 30%+ fall)
FORWARD_TRADING_DAYS = 252
MIN_FORWARD_DAYS_AVAILABLE = 200  # tolerate some gap/holiday slack


def _detect_fall_events(closes: list[float]) -> list[dict]:
    events = []
    if not closes:
        return events
    peak = closes[0]
    peak_idx = 0
    armed = True  # can trigger against the current peak
    for i, c in enumerate(closes):
        if c > peak:
            peak = c
            peak_idx = i
            armed = True
            continue
        if armed and c <= peak * FALL_THRESHOLD:
            events.append({"peak_idx": peak_idx, "peak_price": peak, "trigger_idx": i, "trigger_price": c})
            armed = False
    return events


def build_rows(prices5y: dict) -> list[dict]:
    rows = []
    for sym, entry in prices5y.items():
        closes = [c for c in entry.get("close", []) if c is not None and c > 0]
        if len(closes) < 100:
            continue
        for ev in _detect_fall_events(closes):
            forward_idx = ev["trigger_idx"] + FORWARD_TRADING_DAYS
            available = len(closes) - 1 - ev["trigger_idx"]
            if available < MIN_FORWARD_DAYS_AVAILABLE:
                continue  # not enough owned history after this event to judge it
            end_idx = min(forward_idx, len(closes) - 1)
            price_later = closes[end_idx]
            rows.append(
                {
                    "sym": sym,
                    "peak_price": ev["peak_price"],
                    "trigger_price": ev["trigger_price"],
                    "price_later": price_later,
                    "recovered": price_later >= ev["peak_price"],
                }
            )
    return rows


def main() -> None:
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    rows = build_rows(prices5y)

    n = len(rows)
    n_recovered = sum(1 for r in rows if r["recovered"])
    print(f"Recovery after a fall -- {n} distinct 30%+ fall events across {len(prices5y)} stocks, each judged ~1 year later\n")
    if n:
        print(f"Still below the pre-fall peak a year later: {n - n_recovered} of {n} ({(n - n_recovered) / n:.1%})")
        print(f"Back at or above the pre-fall peak a year later: {n_recovered} of {n} ({n_recovered / n:.1%})")

        still_down_depths = [r["price_later"] / r["peak_price"] - 1 for r in rows if not r["recovered"]]
        if still_down_depths:
            median_depth = sorted(still_down_depths)[len(still_down_depths) // 2]
            print(f"\nOf those still down a year later, median gap to the old peak: {median_depth:+.1%}")

    print(
        "\nDescriptive base rate only -- one observation per distinct fall event\n"
        "(a prolonged decline counts once, not once per day it stays below\n"
        "threshold). Not a forecast for any specific stock; not counted in the\n"
        "project trial counter."
    )


if __name__ == "__main__":
    main()
