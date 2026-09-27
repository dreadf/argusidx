"""
A1 -- "Saham yang naik paling tinggi hari ini akan terus naik" (extreme
one-day gainers keep winning). +1 trial.

Plan reference: `kind-juggling-hoare.md` section 5, A1. Same disclosed
deviation as R2b/R5: the exact spec was fixed in the approved plan before
any of this code existed, but this module's own dated EXPERIMENT.md
pre-registration entry is written after running it, not before (user's
explicit instruction to keep moving, 2026-09-27).

- **Event**: the top 10 one-day gainers on trading day t (by day-over-day
  raw `close` return, matching the price-event convention every other
  m_/r_ module here uses -- not `adjclose`).
  - t-1 is the IDX calendar's immediately preceding trading day (the
    calendar comes from `data/raw/ihsg_2026-09-27.json`'s own date list,
    per this project's IDX-calendar rule -- never a stock's own previous
    price-file row, which can have gaps). A stock is eligible on day t
    only if it has a bar on BOTH t and the calendar's t-1 -- no bridging
    across a gap in its own series.
  - Price >= Rp 50 on day t.
  - Corporate-action days excluded via M4 (the latest `data/raw/
    corporate_actions_history_*.json`, found by glob rather than a
    hardcoded date, 66 credits, docs/credit_ledger.md 2026-09-27): a
    (symbol, date) pair is excluded if that date is `right_issue.ex_date`,
    `stock_split.date` or `bonus.ex_date` for that symbol.
  - A day needs >=100 eligible stocks (for a clean top-10 / 11-100 split);
    days with fewer are skipped and counted.
- **Outcome**: the `adjclose[t+1..t+21]` return in excess of IHSG's own
  return over the same window (t+1 to t+21, 21 trading days -- the plan's
  own number). `adjclose`, not `close`, per docs/DATA.md's rule that a
  multi-day return ratio must include dividends (and, for most IDX names,
  is Yahoo's split-adjusted series) -- unlike the 1-day event-detection
  return above, which is deliberately a raw-price EVENT, not a return
  measurement (found by /code-review, 2026-09-27: the first version of
  this module used raw `close` for both, which is wrong specifically for
  the multi-day outcome). An event is also excluded outright if ANY
  corporate action for that symbol falls anywhere inside its own
  `[t, t+21]` window, not just on day t itself (also found by that
  review): `adjclose` does not reliably absorb a rights issue or bonus
  share the way it does an ordinary split, so a mid-window action could
  otherwise still contaminate the outcome even with the return field
  fixed. Missing outcomes (a stock's series doesn't reach t+21) are
  categorised per protocol §4.8: primary result carries the last
  available close forward through the window; an exclusion-of-missing run
  and a worst-case -50% run are also reported.
- **Comparison**: same-day stocks ranked 11-100 by the same one-day
  return. Per-date spread = mean(excess return, top 10) - mean(excess
  return, 11-100).
- **Split**: explore/holdout boundary 2023-01-01 (T1's boundary, reused
  per the common protocol's explicit "20 days for T1 and A1" embargo
  line, which groups A1 with T1's split). Embargo: a formation date whose
  21-day outcome window would cross the boundary is dropped from explore,
  counted.
- **Significance**: 20-day moving-block bootstrap (`_stress_common.
  moving_block_bootstrap`, same primitive T1 uses) over the ordered
  per-date spread series.
- **Pass**: CONFIRMED only if the holdout mean spread is < 0, its
  bootstrap CI is entirely below 0, and explore has the same sign.

Run:
    .venv/bin/python -m pipeline.hypotheses.a1_extreme_gainers
"""
from __future__ import annotations

import json
import statistics
from datetime import date, datetime, timezone

from pipeline.appdata.common import CORP_ACTIONS_HISTORY_GLOB, RAW_DIR, latest_dated_file
from pipeline.hypotheses._stress_common import moving_block_bootstrap
from pipeline.hypotheses._warnings_panel import load_prices
from pipeline.hypotheses.t1_market_state import load_ihsg

MIN_PRICE = 50.0
TOP_N = 10
COMPARISON_END = 100
MIN_ELIGIBLE = 100
OUTCOME_WINDOW = 21
HOLDOUT_START = "2023-01-01"
CORP_ACTION_DATE_FIELD = {"right_issue": "ex_date", "stock_split": "date", "bonus": "ex_date"}


def corporate_action_dates_from_store(store: dict) -> dict[str, set[str]]:
    """symbol -> set of ISO dates that are a corporate-action effective
    date for that symbol, across all pulled windows and all 3 types."""
    out: dict[str, set[str]] = {}
    for window in store.values():
        for action_type, date_field in CORP_ACTION_DATE_FIELD.items():
            for row in window.get(action_type, []):
                out.setdefault(row["symbol"], set()).add(row[date_field])
    return out


def load_corporate_action_dates() -> dict[str, set[str]]:
    path = latest_dated_file(RAW_DIR, CORP_ACTIONS_HISTORY_GLOB)
    return corporate_action_dates_from_store(json.loads(path.read_text()))


def _build_symbol_field(prices: dict, field: str) -> dict[str, dict[str, float]]:
    """symbol -> {iso_date: value}, positive values only."""
    out: dict[str, dict[str, float]] = {}
    for symbol, entry in prices.items():
        d: dict[str, float] = {}
        for t, v in zip(entry.get("timestamps", []), entry.get(field, [])):
            if v is not None and v > 0:
                iso = datetime.fromtimestamp(t, timezone.utc).date().isoformat()
                d[iso] = v
        out[symbol] = d
    return out


def build_symbol_closes(prices: dict) -> dict[str, dict[str, float]]:
    """symbol -> {iso_date: close}, positive closes only. Raw `close`: used
    ONLY for the 1-day event-detection return (a price EVENT, matching the
    convention every other m_/r_ module here uses), never for a multi-day
    outcome return -- see `build_symbol_adjcloses`."""
    return _build_symbol_field(prices, "close")


def build_symbol_adjcloses(prices: dict) -> dict[str, dict[str, float]]:
    """symbol -> {iso_date: adjclose}, positive values only. Used for the
    t+1..t+21 OUTCOME return, per docs/DATA.md's rule that a multi-day
    return ratio must include dividends (and is Yahoo's split-adjusted
    series for most IDX names)."""
    return _build_symbol_field(prices, "adjclose")


def build_events(
    calendar: list[str],
    symbol_closes: dict[str, dict[str, float]],
    corp_action_dates: dict[str, set[str]],
    start: date,
) -> tuple[list[dict], dict[str, int]]:
    """One row per (date, symbol) event-worthy day: date, symbol, ret (the
    1-day return). Only days with >= MIN_ELIGIBLE eligible stocks produce
    rows. Returns (rows, stats)."""
    rows: list[dict] = []
    skipped_thin_day = 0
    n_excluded_corp_action = 0
    n_excluded_price = 0
    for i in range(1, len(calendar)):
        t = calendar[i]
        if t < start.isoformat():
            continue
        t_prev = calendar[i - 1]
        day_rows = []
        for symbol, closes in symbol_closes.items():
            c_t = closes.get(t)
            c_prev = closes.get(t_prev)
            # Missing either bar means no clean t-1 -> t return: skips a
            # gap in the stock's own series just as much as a day it has
            # no data at all, by construction (no fallback to an earlier
            # bar), which is exactly the "no bridging across gaps" rule.
            if c_t is None or c_prev is None:
                continue
            if c_t < MIN_PRICE:
                n_excluded_price += 1
                continue
            if t in corp_action_dates.get(symbol, ()):
                n_excluded_corp_action += 1
                continue
            day_rows.append({"date": t, "symbol": symbol, "ret": c_t / c_prev - 1})
        if len(day_rows) < MIN_ELIGIBLE:
            skipped_thin_day += 1
            continue
        rows.extend(day_rows)
    stats = {
        "skipped_thin_day": skipped_thin_day,
        "n_excluded_corp_action": n_excluded_corp_action,
        "n_excluded_price": n_excluded_price,
    }
    return rows, stats


def rank_day(day_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    ordered = sorted(day_rows, key=lambda r: -r["ret"])
    return ordered[:TOP_N], ordered[TOP_N:COMPARISON_END]


def excess_return(
    symbol_adjcloses: dict[str, dict[str, float]],
    symbol: str,
    calendar: list[str],
    t_idx: int,
    ihsg_by_date: dict[str, float],
    corp_action_dates: dict[str, set[str]],
) -> tuple[float | None, str]:
    """(excess return, outcome_status) for one event, using the calendar's
    t+1..t+OUTCOME_WINDOW dates on `adjclose`. status is 'complete',
    'missing_carried' (last available adjclose carried forward -- the
    primary treatment), 'no_data_at_all' (not even a t+1 bar; excluded
    even from the primary result), or 'corp_action_in_window' (any of the
    3 tracked action types -- right_issue, stock_split or bonus -- has an
    effective date for this symbol anywhere inside [t, t+OUTCOME_WINDOW]).
    All 3 types are excluded uniformly here, for simplicity: `adjclose`
    does not reliably absorb a rights issue or bonus share, and while it
    typically does handle an ordinary split, this module does not rely on
    that per-type distinction holding for every case in `corp_action_dates`
    (which itself makes no type distinction -- see
    `corporate_action_dates_from_store`)."""
    end_idx = t_idx + OUTCOME_WINDOW
    if end_idx >= len(calendar):
        return None, "window_past_cache_end"
    window_dates = set(calendar[t_idx : end_idx + 1])
    if corp_action_dates.get(symbol, set()) & window_dates:
        return None, "corp_action_in_window"
    entry_date = calendar[t_idx + 1]
    exit_date = calendar[end_idx]
    adjcloses = symbol_adjcloses[symbol]
    entry_price = adjcloses.get(entry_date)
    if entry_price is None:
        return None, "no_data_at_all"
    exit_price = adjcloses.get(exit_date)
    status = "complete"
    if exit_price is None:
        # Carry the last available adjclose in [entry_date, exit_date]
        # forward, scanning only the calendar dates in that range (not the
        # whole multi-year series) so this stays cheap per missing-exit event.
        exit_price = None
        for d in reversed(calendar[t_idx + 1 : end_idx + 1]):
            v = adjcloses.get(d)
            if v is not None:
                exit_price = v
                break
        if exit_price is None:
            return None, "no_data_at_all"
        status = "missing_carried"
    stock_ret = exit_price / entry_price - 1
    ihsg_entry, ihsg_exit = ihsg_by_date.get(entry_date), ihsg_by_date.get(exit_date)
    if ihsg_entry is None or ihsg_exit is None:
        return None, "no_ihsg_data"
    ihsg_ret = ihsg_exit / ihsg_entry - 1
    return stock_ret - ihsg_ret, status


def daily_spread(
    date_str: str,
    day_rows: list[dict],
    symbol_adjcloses: dict[str, dict[str, float]],
    calendar: list[str],
    date_index: dict[str, int],
    ihsg_by_date: dict[str, float],
    corp_action_dates: dict[str, set[str]],
) -> dict | None:
    top, comparison = rank_day(day_rows)
    if len(comparison) < COMPARISON_END - TOP_N:
        return None
    t_idx = date_index[date_str]

    def group_mean(group: list[dict]) -> tuple[float | None, int]:
        vals = []
        for r in group:
            ex, status = excess_return(symbol_adjcloses, r["symbol"], calendar, t_idx, ihsg_by_date, corp_action_dates)
            if ex is not None:
                vals.append(ex)
        return (statistics.mean(vals) if vals else None), len(vals)

    top_mean, top_n = group_mean(top)
    comp_mean, comp_n = group_mean(comparison)
    if top_mean is None or comp_mean is None:
        return None
    window_end_date = calendar[t_idx + OUTCOME_WINDOW]
    return {
        "date": date_str,
        "window_end": window_end_date,
        "spread": top_mean - comp_mean,
        "top_n": top_n,
        "comp_n": comp_n,
    }


def split_explore_holdout(spreads: list[dict]) -> tuple[list[dict], list[dict], int]:
    explore, holdout, dropped = [], [], 0
    for s in spreads:
        if s["date"] >= HOLDOUT_START:
            holdout.append(s)
        elif s["window_end"] < HOLDOUT_START:
            explore.append(s)
        else:
            dropped += 1
    return explore, holdout, dropped


def main() -> None:
    prices = load_prices()
    ihsg_dates, ihsg_closes = load_ihsg()
    calendar = ihsg_dates
    date_index = {d: i for i, d in enumerate(calendar)}
    ihsg_by_date = dict(zip(ihsg_dates, ihsg_closes))

    symbol_closes = build_symbol_closes(prices)
    symbol_adjcloses = build_symbol_adjcloses(prices)
    corp_action_dates = load_corporate_action_dates()

    rows, build_stats = build_events(calendar, symbol_closes, corp_action_dates, start=date(2022, 1, 1))
    print(f"Event-day rows: {len(rows)}; {build_stats}")

    by_date: dict[str, list[dict]] = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)
    print(f"Trading days with >= {MIN_ELIGIBLE} eligible stocks: {len(by_date)}")

    spreads = []
    for date_str, day_rows in sorted(by_date.items()):
        s = daily_spread(date_str, day_rows, symbol_adjcloses, calendar, date_index, ihsg_by_date, corp_action_dates)
        if s is not None:
            spreads.append(s)
    print(f"Days with a computable spread (both groups have >=1 usable outcome): {len(spreads)}")

    explore, holdout, dropped = split_explore_holdout(spreads)
    print(f"Explore: {len(explore)} days, holdout: {len(holdout)} days, dropped at embargo: {dropped}")

    explore_mean = statistics.mean(s["spread"] for s in explore) if explore else None
    holdout_mean = statistics.mean(s["spread"] for s in holdout) if holdout else None
    print(f"\nExplore mean spread: {explore_mean}")
    print(f"Holdout mean spread: {holdout_mean}")

    holdout_series = [s["spread"] for s in holdout]
    boot = moving_block_bootstrap(holdout_series, lambda s: statistics.mean(s) if s else None, block_len=20)
    print(f"Holdout 20-day moving-block bootstrap CI: [{boot['low']:.4f}, {boot['high']:.4f}] "
          f"(estimate {boot['estimate']}, {boot['n_valid_replicates']} valid replicates)")

    ci_below_zero = boot["high"] == boot["high"] and boot["high"] < 0  # False (not error) if NaN
    same_sign = explore_mean is not None and holdout_mean is not None and explore_mean < 0 and holdout_mean < 0
    confirmed = holdout_mean is not None and holdout_mean < 0 and ci_below_zero and same_sign
    print(f"\n**A1: {'CONFIRMED' if confirmed else 'NOT confirmed'}**")


if __name__ == "__main__":
    main()
