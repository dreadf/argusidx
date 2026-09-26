"""
Base rate (situation S2, "Langganan suspensi"): how often is a price-increase
suspension followed by another one for the same stock within a year?

NOT a falsifiable hypothesis -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions frozen in
EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 1)"); run once.
Sectors-only data (owned suspensions file), no prices.

- Event: a suspension whose `reason` mentions a price increase
  ("peningkatan harga" or "kenaikan harga", case-insensitive substring).
  Expected from the file: 437 events over 229 stocks.
- Event-level base rate: among events dated on or before 2025-09-11 (so at
  least 365 days of follow-up exist before the file's last date, 2026-09-11),
  the share followed by another price-increase suspension of the same stock
  strictly after the event date and no later than 365 days after it.
  Same-stock rows on the same date count as one event.
- Stock-level: of stocks with at least one such event, how many have two or
  more (expected 134 of 229).
- Diagnostic only (not part of the frozen definition): how many of the
  followed events had their first follow-up within 7 days, since consecutive
  notices can be the same episode.
- Diagnostic added after the counts were seen (also not part of the frozen
  definition): the share of eligible events with any follow-up more than 7 and at
  most 365 days after the event, i.e. ignoring follow-ups that only fall within 7 days.
- Limits: events of one stock are not independent, and one stock can add many
  events to the pooled rate.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_repeat_spike_suspension
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"

KEYWORDS = ("peningkatan harga", "kenaikan harga")
FOLLOW_UP_DAYS = 365
LAST_FULL_FOLLOW_UP_EVENT = date(2025, 9, 11)
QUICK_FOLLOW_UP_DAYS = 7


def is_price_increase_reason(reason: str | None) -> bool:
    text = (reason or "").lower()
    return any(k in text for k in KEYWORDS)


def price_increase_events(suspensions: list[dict]) -> dict[str, list[date]]:
    """Sorted, de-duplicated event dates per stock."""
    by_stock: dict[str, set[date]] = defaultdict(set)
    for s in suspensions:
        if s.get("symbol") and s.get("suspension_date") and is_price_increase_reason(s.get("reason")):
            by_stock[s["symbol"]].add(datetime.strptime(s["suspension_date"], "%Y-%m-%d").date())
    return {sym: sorted(ds) for sym, ds in by_stock.items()}


def first_follow_up_gap(dates: list[date], event: date) -> int | None:
    """Days from `event` to the next event of the same stock if it falls within 365 days, else None."""
    for d in dates:
        if d > event:
            gap = (d - event).days
            return gap if gap <= FOLLOW_UP_DAYS else None
    return None


def has_follow_up_after_quick_window(dates: list[date], event: date) -> bool:
    """True if another event falls MORE than 7 and at most 365 days after `event` (added diagnostic)."""
    return any(QUICK_FOLLOW_UP_DAYS < (d - event).days <= FOLLOW_UP_DAYS for d in dates)


def build_repeat_spike_suspension(suspensions: list[dict]) -> dict:
    events = price_increase_events(suspensions)
    n_events = sum(len(v) for v in events.values())
    eligible = 0
    followed = 0
    quick = 0
    beyond_quick = 0
    for dates in events.values():
        for d in dates:
            if d > LAST_FULL_FOLLOW_UP_EVENT:
                continue
            eligible += 1
            if has_follow_up_after_quick_window(dates, d):
                beyond_quick += 1
            gap = first_follow_up_gap(dates, d)
            if gap is not None:
                followed += 1
                if gap <= QUICK_FOLLOW_UP_DAYS:
                    quick += 1
    repeat_stocks = sum(1 for v in events.values() if len(v) >= 2)
    return {
        "events": n_events,
        "stocks": len(events),
        "eligible_events": eligible,
        "followed_within_365d": followed,
        "share_followed": (followed / eligible) if eligible else None,
        "followed_first_gap_within_7d": quick,
        "followed_by_gap_over_7d": beyond_quick,
        "share_followed_by_gap_over_7d": (beyond_quick / eligible) if eligible else None,
        "stocks_with_2_or_more": repeat_stocks,
    }


def main() -> None:
    result = build_repeat_spike_suspension(json.loads(SUSPENSIONS_PATH.read_text()))
    print("Price-increase suspension events:", result["events"], "over", result["stocks"], "stocks")
    print(
        f"Events with 365 days of follow-up (date <= {LAST_FULL_FOLLOW_UP_EVENT}): {result['eligible_events']}; "
        f"followed by another within 365 days: {result['followed_within_365d']} ({result['share_followed']:.1%})"
    )
    print("  of which first follow-up within 7 days (diagnostic):", result["followed_first_gap_within_7d"])
    print(
        "Added after seeing the counts (diagnostic): eligible events with a follow-up MORE than 7 days after, "
        f"within 365 days: {result['followed_by_gap_over_7d']} of {result['eligible_events']} "
        f"({result['share_followed_by_gap_over_7d']:.1%})"
    )
    print(f"Stocks with 2 or more events: {result['stocks_with_2_or_more']} of {result['stocks']}")


if __name__ == "__main__":
    main()
