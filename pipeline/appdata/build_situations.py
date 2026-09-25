"""Build data/app/situations.json: which of the tested "situations" each stock
is in right now, with triggers that match how each base rate was measured
(docs/PRODUCT.md: "Situasi saham ini").

A base rate only describes a stock if the stock meets the same condition the
rate was computed on, so each trigger below mirrors its base rate's
definition, not a looser lookalike:

- **fall** (base rate: `pipeline/hypotheses/m_recovery_after_fall.py`). That
  rate counts from the FIRST day a close is at or below 70% of the running
  peak, and looks 252 trading days ahead. A stock qualifies when its latest
  such event is at most 252 trading days old and it is still below that peak.
  A fall older than a year, or one already recovered, is not this situation.
- **loss_year** (base rate: `m_loss_maker_turnaround.py`): `earnings[Y] < 0`
  for a full calendar year, from the Sectors sweep. Not ROE: the rate is
  defined on annual net income.
- **recent_price_suspension** (base rate: `h11_suspension_underperformance.py`):
  a suspension whose reason contains "peningkatan harga" (the same filter H11
  uses), within the last 90 days, the longest horizon H11 measured. An older
  suspension is history, not this situation.
- **recent_ipo** (base rate: `h13_ipo_board_performance.py`): a listing within
  the last 365 days, with its listing board, since that rate is per board.
- **recent_spike**, **earnings_two_year_decline**, **earnings_more_than_doubled**
  (added 2026-09-22; base rates `m_recent_spike.py` and `m_earnings_streaks.py`,
  definitions frozen in EXPERIMENT.md before outcomes were computed). Unlike the
  four above, these import the trigger from the base-rate module itself instead of
  duplicating it, so trigger and rate share one definition by construction.

Not here on purpose: the dividend-payout situation. `flags.json` trips on
Sectors' `payout_ratio` snapshot field, while H4's cut rates use a payout
ratio built from dividend per share over EPS; whether the two coincide has
not been checked, so no frequency is attached to that flag yet.

**Yahoo dependency, stated once:** only `fall` reads price history, from the
free dev cache (`data/dev_cache/prices_5y.json`, gitignored, re-fetchable).
Same rule as build_beat_gold.py: this is a build-time step that freezes
derived facts (a date, a percentage, a count), never a raw series, and the
frontend never touches Yahoo. Replacing it with Sectors prices would cost
4 to 5 credits per symbol per year of history (`/v2/daily/` is 1 credit per
90-day window, docs/credit_ledger.md), far past the remaining budget for the
~600 stocks that sit 30% or more below their 52-week high.
The detector is duplicated from the hypothesis module by design (the same
precedent build_beat_gold.py cites); a parity test guards against drift.

Run: .venv/bin/python -m pipeline.appdata.build_situations
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from pipeline.appdata.common import APP_DIR, RAW_DIR, REPO_ROOT, UNIVERSE_GLOB, latest_dated_file
from pipeline.hypotheses.m_earnings_streaks import is_more_than_doubled, is_two_year_decline
from pipeline.hypotheses.m_recent_spike import LOOKBACK_BARS as SPIKE_LOOKBACK_BARS
from pipeline.hypotheses.m_recent_spike import detect_spike_events, usable_closes

PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

FALL_THRESHOLD = 0.70  # a close at or below 70% of the running peak (a 30%+ fall)
FORWARD_TRADING_DAYS = 252
MIN_HISTORY_BARS = 100
LOSS_YEAR = 2025
SUSPENSION_RECENT_DAYS = 90
IPO_RECENT_DAYS = 365
PRICE_INCREASE_PHRASE = "peningkatan harga"  # H11's own filter
EARNINGS_YEAR = 2025  # latest full reported year, for the two earnings situations
SPIKE_RECENT_BARS = 20  # latest jump event at most this many trading days old


def detect_fall_events(closes: list[float]) -> list[dict]:
    """Duplicated from m_recovery_after_fall._detect_fall_events by design.
    One event per fall: it re-arms only when the running peak makes a new high."""
    events = []
    if not closes:
        return events
    peak = closes[0]
    peak_idx = 0
    armed = True
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


def _bar_date(timestamp: int) -> date:
    # IDX opens ~02:00 UTC, so the UTC date is the trading date.
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()


def _latest_fall(entry: dict | None) -> dict | None:
    """The stock's latest fall event, while it is still below that event's peak."""
    if not entry:
        return None
    pairs = [(t, c) for t, c in zip(entry.get("timestamps", []), entry.get("close", [])) if c is not None and c > 0]
    if len(pairs) < MIN_HISTORY_BARS:
        return None
    closes = [c for _, c in pairs]
    events = detect_fall_events(closes)
    if not events:
        return None
    event = events[-1]
    last_index = len(closes) - 1
    peak = event["peak_price"]
    if closes[-1] >= peak:
        return None  # already back at the old peak: no longer in a fall
    return {
        "peak_price": peak,
        "peak_date": _bar_date(pairs[event["peak_idx"]][0]).isoformat(),
        "trigger_date": _bar_date(pairs[event["trigger_idx"]][0]).isoformat(),
        "trigger_price": event["trigger_price"],
        "trading_days_since": last_index - event["trigger_idx"],
        "window_trading_days": FORWARD_TRADING_DAYS,
        "last_close": closes[-1],
        "last_close_date": _bar_date(pairs[last_index][0]).isoformat(),
        "pct_from_peak": (closes[-1] / peak - 1) * 100,
    }


def build_fall(entry: dict | None) -> dict | None:
    """The situation: first crossed -30% within the last 252 trading days."""
    fall = _latest_fall(entry)
    if fall is None or fall["trading_days_since"] > FORWARD_TRADING_DAYS:
        return None
    return fall


def build_older_fall(entry: dict | None) -> dict | None:
    """NOT a situation: still below its peak, but the first -30% crossing is
    more than 252 trading days old, outside what the base rate measured. Kept
    so a page can say why a stock that looks far below its high shows no
    situation, instead of silently showing nothing."""
    fall = _latest_fall(entry)
    if fall is None or fall["trading_days_since"] <= FORWARD_TRADING_DAYS:
        return None
    return fall


def build_loss_year(query_values: dict) -> dict | None:
    earnings = query_values.get(f"earnings[{LOSS_YEAR}]")
    if earnings is None or earnings >= 0:
        return None
    return {"year": LOSS_YEAR, "net_income": earnings}


def build_recent_price_suspension(events: list[dict] | None, as_of: date) -> dict | None:
    best = None
    for event in events or []:
        if PRICE_INCREASE_PHRASE not in (event.get("reason") or "").lower():
            continue
        days_ago = (as_of - date.fromisoformat(event["date"])).days
        if not 0 <= days_ago <= SUSPENSION_RECENT_DAYS:
            continue
        if best is None or days_ago < best["days_ago"]:
            best = {"date": event["date"], "days_ago": days_ago, "pdf_url": event.get("pdf_url")}
    return best


def build_recent_ipo(query_values: dict, as_of: date) -> dict | None:
    listing_date = query_values.get("listing_date")
    if not listing_date:
        return None
    days_since = (as_of - date.fromisoformat(listing_date)).days
    if not 0 <= days_since <= IPO_RECENT_DAYS:
        return None
    return {"listing_date": listing_date, "board": query_values.get("listing_board"), "days_since": days_since}


def build_recent_spike(entry: dict | None) -> dict | None:
    """S1: the latest jump of 40%+ within 20 trading days is at most 20 trading days old.
    Trigger and base rate share one definition: both come from m_recent_spike."""
    if not entry:
        return None
    pairs = [(t, c) for t, c in zip(entry.get("timestamps", []), entry.get("close", [])) if c is not None and c > 0]
    closes = usable_closes({"close": [c for _, c in pairs]})
    if closes is None:
        return None
    events = detect_spike_events(closes)
    if not events:
        return None
    index = events[-1]
    last_index = len(closes) - 1
    if last_index - index > SPIKE_RECENT_BARS:
        return None
    return {
        "event_date": _bar_date(pairs[index][0]).isoformat(),
        "trading_days_since": last_index - index,
        "jump_pct": (closes[index] / closes[index - SPIKE_LOOKBACK_BARS] - 1) * 100,
        "last_close": closes[-1],
        "pct_since_event": (closes[-1] / closes[index] - 1) * 100,
        "lookback_trading_days": SPIKE_LOOKBACK_BARS,
    }


def build_earnings_two_year_decline(qv: dict) -> dict | None:
    if not is_two_year_decline(qv, EARNINGS_YEAR):
        return None
    return {"year": EARNINGS_YEAR, "earnings": [qv[f"earnings[{y}]"] for y in (EARNINGS_YEAR - 2, EARNINGS_YEAR - 1, EARNINGS_YEAR)]}


def build_earnings_more_than_doubled(qv: dict) -> dict | None:
    if not is_more_than_doubled(qv, EARNINGS_YEAR):
        return None
    return {"year": EARNINGS_YEAR, "earnings": [qv[f"earnings[{y}]"] for y in (EARNINGS_YEAR - 1, EARNINGS_YEAR)]}


def build_for_stock(row: dict, prices: dict, suspension_events: list[dict] | None, as_of: date) -> dict:
    qv = row["query_values"]
    return {
        "fall": build_fall(prices.get(row["symbol"])),
        "older_fall": build_older_fall(prices.get(row["symbol"])),
        "loss_year": build_loss_year(qv),
        "recent_price_suspension": build_recent_price_suspension(suspension_events, as_of),
        "recent_ipo": build_recent_ipo(qv, as_of),
        "recent_spike": build_recent_spike(prices.get(row["symbol"])),
        "earnings_two_year_decline": build_earnings_two_year_decline(qv),
        "earnings_more_than_doubled": build_earnings_more_than_doubled(qv),
    }


def summarize(by_symbol: dict[str, dict]) -> dict:
    kinds = (
        "fall",
        "loss_year",
        "recent_price_suspension",
        "recent_ipo",
        "recent_spike",
        "earnings_two_year_decline",
        "earnings_more_than_doubled",
    )
    counts = {k: sum(1 for v in by_symbol.values() if v[k] is not None) for k in kinds}
    counts["older_fall_not_a_situation"] = sum(1 for v in by_symbol.values() if v["older_fall"] is not None)
    counts["no_situation"] = sum(1 for v in by_symbol.values() if all(v[k] is None for k in kinds))
    counts["universe"] = len(by_symbol)
    return counts


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of_str = universe_path.stem.replace("universe_", "")
    as_of = date.fromisoformat(as_of_str)
    rows = json.loads(universe_path.read_text())
    suspensions = json.loads((APP_DIR / "suspensions.json").read_text())["by_symbol"]
    if not PRICES_5Y_PATH.exists():
        raise FileNotFoundError(
            f"{PRICES_5Y_PATH} not found - re-fetch the dev cache first (pipeline/dev/fetch_yahoo_prices.py); "
            "it is gitignored and free"
        )
    prices = json.loads(PRICES_5Y_PATH.read_text())

    by_symbol = {row["symbol"]: build_for_stock(row, prices, suspensions.get(row["symbol"]), as_of) for row in rows}
    counts = summarize(by_symbol)

    output = {
        "as_of": as_of_str,
        "source_file": universe_path.name,
        "price_source_note": (
            "fall reads research price history (dev cache), frozen as derived facts; "
            "loss_year and recent_ipo come from the Sectors sweep, recent_price_suspension from Sectors suspensions"
        ),
        "definitions": {
            "fall_threshold": FALL_THRESHOLD,
            "fall_window_trading_days": FORWARD_TRADING_DAYS,
            "loss_year": LOSS_YEAR,
            "suspension_recent_days": SUSPENSION_RECENT_DAYS,
            "ipo_recent_days": IPO_RECENT_DAYS,
            "spike_threshold": 0.40,
            "spike_lookback_trading_days": SPIKE_LOOKBACK_BARS,
            "spike_recent_trading_days": SPIKE_RECENT_BARS,
            "earnings_year": EARNINGS_YEAR,
        },
        "counts": counts,
        "by_symbol": by_symbol,
    }
    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "situations.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} (as_of {as_of_str})")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
