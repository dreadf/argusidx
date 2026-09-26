"""
H18: after an insider-buy filing, does the stock beat the index over the
next 20 trading days?

STATUS: power rule met (314 explore / 346 holdout events, read before any
outcome was computed); the pre-registered outcome step below is implemented
and is run once on the real data.

Pre-registered event rule (frozen):
- Events: insider-buy filings in the owned file
  (`insider_buys_2025_2026_2026-09-13.jsonl`), one event per stock per 60
  days: the first filing is the event, then none for the next 60 calendar
  days. The filing date counts only if it is a trading day, otherwise the
  next trading day.
- Phases: explore = filings in 2025, holdout = filings in 2026 (by the
  filing's own calendar date, before any shifting).
- Power rule: if either phase has fewer than 100 events, H18 is reported as
  descriptive only ("belum cukup data") with no verdict.
- Filings tagged `takeover` are reported separately by tag, not dropped.
- Outcome: adjclose return from the close of the day after the (shifted)
  event date to 20 trading days later, minus the same-window ^JKSE return;
  per phase, average by calendar month, one-sample t-test across months
  (exact Student-t, `h6_foreign_list.one_sample_t`, imported not copied);
  CONFIRMED only if holdout mean > 0 with p < 0.05 and explore has the same
  sign. A significant negative holdout is reported as the opposite
  (`h6_foreign_list.verdict`, shared).
- Outcome reading choices: the 20 trading days are counted on the ^JKSE
  calendar for stock and index alike, start bar = first calendar day after the
  event date (so the filing-day move is excluded), end bar = 20 days after that
  start; the stock needs a price on both bars, else the event is dropped and
  counted. The calendar month is that of the original filing date (the same
  date that sets the phase). No winsorising (none was pre-registered).
- Robustness only, not the verdict: the same statistic without `takeover`-tagged
  events, the median event excess, the share beating the index, months per
  phase, events dropped for missing prices.

Reading choices for points the text leaves open (disclosed, not hidden):
- Filing date = the date part of the filing's `timestamp` as stored.
- Trading-day calendar = the dates of the ^JKSE series in the research price
  cache (`data/dev_cache/benchmarks_5y.json`), which ends 2026-09-11. A filing
  after the last calendar day cannot be shifted; it keeps its own date and is
  counted in `beyond_calendar`.
- The 60-day refractory is measured on the shifted event dates: after an event
  on date e, filings whose shifted date is at or before e + 60 calendar days
  are not events; a filing shifted to e + 61 or later is. A skipped filing does
  not restart the clock.
- Only the `takeover` tag exists in the data; "ownership changes above 10%" and
  "tender offers" have no separate tag, so they are not separated here.
- Limits: 20 months of filings, clustered in time, and a filing is not proof
  the person is an "insider" in the popular sense.

Data (owned, no API call): the filings file above and the research price cache
(Yahoo, development-time only; nothing under `frontend/` may import this).

Run:
    .venv/bin/python -m pipeline.hypotheses.h18_insider_buying
"""
from __future__ import annotations

import bisect
import json
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline.hypotheses.h6_foreign_list import (
    _close_by_day,
    one_sample_t,
    verdict,
    window_return,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FILINGS_PATH = REPO_ROOT / "data" / "raw" / "insider_buys_2025_2026_2026-09-13.jsonl"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
BENCHMARKS_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "benchmarks_5y.json"

REFRACTORY_DAYS = 60
MIN_EVENTS_PER_PHASE = 100
HORIZON_TRADING_DAYS = 20
EXPLORE_YEAR = 2025
HOLDOUT_YEAR = 2026
TAKEOVER_TAG = "takeover"
BENCHMARK = "^JKSE"


def load_filings(path: Path = FILINGS_PATH) -> list[dict]:
    """One dict per filing: symbol, date (from `timestamp`), is_takeover. Rows lacking a symbol or timestamp are skipped."""
    filings = []
    with path.open() as f:
        for line in f:
            d = json.loads(line)
            sym, ts = d.get("symbol"), d.get("timestamp")
            if not sym or not ts:
                continue
            filings.append(
                {
                    "sym": sym,
                    "date": datetime.strptime(ts[:10], "%Y-%m-%d").date(),
                    "is_takeover": TAKEOVER_TAG in (d.get("tags") or []),
                }
            )
    return filings


def _bar_date(ts: float) -> date:
    return datetime.fromtimestamp(ts, timezone.utc).date()


def trading_days_from_entry(entry: dict) -> list[date]:
    """Sorted, unique bar dates of a dev-cache entry (bars are stamped 02:00 UTC, same date in Jakarta)."""
    return sorted({_bar_date(t) for t, c in zip(entry["timestamps"], entry["close"]) if c is not None})


def next_trading_day(day: date, trading_days: list[date]) -> date | None:
    """`day` if it is a trading day, else the next one; None if the calendar ends before it."""
    i = bisect.bisect_left(trading_days, day)
    return trading_days[i] if i < len(trading_days) else None


def build_events(filings: list[dict], trading_days: list[date]) -> list[dict]:
    """Events per the pre-registered rule (see module docstring), sorted by (symbol, event date)."""
    by_stock: dict[str, list[dict]] = {}
    for f in filings:
        shifted = next_trading_day(f["date"], trading_days)
        by_stock.setdefault(f["sym"], []).append(
            {**f, "event_date": shifted if shifted is not None else f["date"], "beyond_calendar": shifted is None}
        )
    events: list[dict] = []
    for sym, rows in by_stock.items():
        rows.sort(key=lambda r: (r["event_date"], r["date"]))
        last: date | None = None
        for r in rows:
            if last is not None and (r["event_date"] - last).days <= REFRACTORY_DAYS:
                continue
            events.append({"sym": sym, **{k: r[k] for k in ("date", "event_date", "is_takeover", "beyond_calendar")}})
            last = r["event_date"]
    events.sort(key=lambda e: (e["sym"], e["event_date"]))
    return events


def phase_of(event: dict) -> str | None:
    """'explore' for a filing in 2025, 'holdout' for 2026, None otherwise."""
    if event["date"].year == EXPLORE_YEAR:
        return "explore"
    if event["date"].year == HOLDOUT_YEAR:
        return "holdout"
    return None


def has_follow_up(entry: dict | None, event_date: date, horizon: int = HORIZON_TRADING_DAYS) -> bool:
    """True if the stock's own series has the bar `horizon` trading days after the day after `event_date`.

    Availability only (no prices are read for a return): the outcome window starts at the close of the
    first bar after the event date and ends `horizon` bars later.
    """
    if not entry:
        return False
    days = trading_days_from_entry(entry)
    i = bisect.bisect_right(days, event_date)  # first bar strictly after the event date
    return i + horizon < len(days)


def count_events(events: list[dict], prices: dict | None = None) -> dict:
    """Event counts per phase, split by the `takeover` tag; with a price cache also how many have price data / a full window."""
    out: dict = {}
    for phase in ("explore", "holdout"):
        in_phase = [e for e in events if phase_of(e) == phase]
        c: dict = {
            "events": len(in_phase),
            "takeover_tag": sum(e["is_takeover"] for e in in_phase),
            "without_takeover_tag": sum(not e["is_takeover"] for e in in_phase),
            "beyond_calendar": sum(e["beyond_calendar"] for e in in_phase),
            "enough_for_power_rule": len(in_phase) >= MIN_EVENTS_PER_PHASE,
        }
        if prices is not None:
            with_price = [e for e in in_phase if prices.get(e["sym"])]
            with_window = [e for e in with_price if has_follow_up(prices[e["sym"]], e["event_date"])]
            c["with_price_history"] = len(with_price)
            c["with_full_20_day_window"] = len(with_window)
            c["with_full_window_without_takeover_tag"] = sum(not e["is_takeover"] for e in with_window)
        out[phase] = c
    out["power_rule_met"] = out["explore"]["enough_for_power_rule"] and out["holdout"]["enough_for_power_rule"]
    return out


def event_excess(
    event: dict,
    days: list[date],
    prices: dict[str, dict[date, float]],
    index_px: dict[date, float],
) -> float | None:
    """Stock return minus ^JKSE return from the first calendar day after the event date to 20 days later.

    None if the calendar has no such window or the stock (or index) lacks a price at either end.
    """
    i = bisect.bisect_right(days, event["event_date"])  # first calendar day strictly after the event date
    if i + HORIZON_TRADING_DAYS >= len(days):
        return None
    start, end = days[i], days[i + HORIZON_TRADING_DAYS]
    px = prices.get(event["sym"])
    stock = window_return(px, start, end) if px else None
    bench = window_return(index_px, start, end)
    if stock is None or bench is None:
        return None
    return stock - bench


def analyze_phase(rows: list[dict]) -> dict:
    """`rows`: events with an 'excess' (float or None) and a 'date'. Month means, t-test across months, robustness figures."""
    kept = [r for r in rows if r["excess"] is not None]
    by_month: dict[tuple[int, int], list[float]] = {}
    for r in kept:
        by_month.setdefault((r["date"].year, r["date"].month), []).append(r["excess"])
    month_means = [statistics.fmean(v) for _, v in sorted(by_month.items())]
    result = one_sample_t(month_means)
    excesses = [r["excess"] for r in kept]
    result.update(
        {
            "n_events": len(rows),
            "n_events_used": len(kept),
            "n_dropped_missing_prices": len(rows) - len(kept),
            "n_months": len(month_means),
            "median_event_excess": statistics.median(excesses) if excesses else float("nan"),
            "share_beating_index": (sum(e > 0 for e in excesses) / len(excesses)) if excesses else float("nan"),
        }
    )
    return result


def build_outcomes(
    events: list[dict],
    days: list[date],
    prices: dict[str, dict[date, float]],
    index_px: dict[date, float],
) -> dict:
    rows = []
    for e in events:
        phase = phase_of(e)
        if phase is None:
            continue
        rows.append({"phase": phase, "date": e["date"], "is_takeover": e["is_takeover"], "excess": event_excess(e, days, prices, index_px)})
    out: dict = {}
    for phase in ("explore", "holdout"):
        in_phase = [r for r in rows if r["phase"] == phase]
        out[phase] = analyze_phase(in_phase)
        out[phase + "_without_takeover"] = analyze_phase([r for r in in_phase if not r["is_takeover"]])
    out["verdict"] = verdict(out["explore"], out["holdout"])
    out["verdict_without_takeover"] = verdict(out["explore_without_takeover"], out["holdout_without_takeover"])
    return out


def main() -> None:
    filings = load_filings()
    benchmarks = json.loads(BENCHMARKS_5Y_PATH.read_text())
    prices_raw = json.loads(PRICES_5Y_PATH.read_text())
    days = trading_days_from_entry(benchmarks[BENCHMARK])
    events = build_events(filings, days)
    counts = count_events(events, prices_raw)
    print(f"Filings loaded: {len(filings)} ; events after the 60-day rule: {len(events)}")
    for phase in ("explore", "holdout"):
        print(f"{phase} events: {counts[phase]['events']}")
    print("Power rule (both phases >= 100 events):", counts["power_rule_met"])
    if not counts["power_rule_met"]:
        print("belum cukup data: descriptive only, no outcome computed")
        return
    prices = {s: _close_by_day(e) for s, e in prices_raw.items() if e.get("timestamps")}
    index_px = _close_by_day(benchmarks[BENCHMARK])
    out = build_outcomes(events, days, prices, index_px)
    for key in ("explore", "holdout", "explore_without_takeover", "holdout_without_takeover"):
        print(f"{key}: {out[key]}")
    print("verdict:", out["verdict"])
    print("verdict without takeover (robustness only):", out["verdict_without_takeover"])


if __name__ == "__main__":
    main()
