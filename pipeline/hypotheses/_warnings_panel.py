"""
Shared stock x month-start panel for R1 (warning overlap) and R2a (does the
count of active warnings matter). Pre-registered in EXPERIMENT.md
("Pre-registration, 2026-09-27: T1, R1 and R2a") before either module was run.

Builds one row per (stock, month-start) from 2022-05-01, with the eight
warning booleans, each already precisely defined by an existing module or
finding in this project (thresholds reused verbatim, not reinvented; the
TIME-VARYING, per-month-as-of-formation computation is new, since every
source module below computes its signal once for a fixed window, not on a
rolling monthly basis):

1. fell 30%+ from peak         -- m_recovery_after_fall.FALL_THRESHOLD (0.70)
2. long below peak             -- m_long_below_peak (event trigger >=252
                                   bars before formation, still below peak)
3. up 40%+ in 20 trading days  -- m_recent_spike (SPIKE_THRESHOLD 0.40,
                                   LOOKBACK_BARS 20)
4. loss year                   -- most recent lagged earnings[Y] < 0
5. earnings down two years     -- m_near_peak_earnings_decline's
                                   earnings_declined(), applied to Y and Y-1
6. payout in the top tercile   -- stats.payout_ratio_from_totals, tercile
                                   cut cross-sectionally within each month
                                   (H4 computes phase-fixed terciles; this
                                   panel is monthly, so the tercile is too)
7. near peak, falling earnings -- m_near_peak_earnings_decline
                                   (NEAR_PEAK_THRESHOLD 0.10) AND earnings
                                   declined in the most recent lagged year
8. yield spike                 -- m_yield_spike_cut (total_yield[Y] >= 1.5x
                                   the trailing 3-year mean)

Price data: `data/dev_cache/prices_5y.json` (raw `close`, matching the
price-EVENT convention H1/the m_ modules already use -- not `adjclose`,
which is for RETURN calculations, see docs/DATA.md's close-vs-adjclose
note). Fundamentals: the latest universe sweep, yearly fields only, lagged
under the project's 1 May rule (a rolling, per-calendar-date version of the
rule every other hypothesis module here applies only at fixed formation
years).

Disclosed limit: `prices_5y.json` starts 2021-09-09 for old listings, only
about 8 months before the panel's own 2022-05-01 start. Warning 2 (long
below peak) requires an event triggered >=252 trading days before
formation; at the panel's earliest months there simply isn't 252 days of
price history yet, so this warning under-fires (false negatives, never
false positives) until enough history has accumulated -- stated here, not
silently absorbed into the base rate.

Run only as a library import (`build_panel()`), not standalone.
"""
from __future__ import annotations

import json
import statistics
from datetime import date
from pathlib import Path

from pipeline.appdata.build_flags import YIELD_ABOVE_AVG_MULTIPLIER
from pipeline.hypotheses.m_recovery_after_fall import _detect_fall_events

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-12.json"

PANEL_START = date(2022, 5, 1)
FALL_THRESHOLD = 0.70  # matches m_recovery_after_fall.FALL_THRESHOLD
LONG_BELOW_PEAK_BARS = 252  # matches m_long_below_peak.YEAR_BARS
SPIKE_THRESHOLD = 0.40  # matches m_recent_spike.SPIKE_THRESHOLD
SPIKE_LOOKBACK_BARS = 20  # matches m_recent_spike.LOOKBACK_BARS
NEAR_PEAK_THRESHOLD = 0.10  # matches m_near_peak_earnings_decline.NEAR_PEAK_THRESHOLD
YIELD_PRIOR_YEARS = 3  # matches m_yield_spike_cut.PRIOR_YEARS
SIZE_FLAG_CHANGE = 0.50  # the plan's "share count changes by >=50%" rule
VOL_WINDOW = 60
MIN_HISTORY_BARS = 100

WARNING_KEYS = [
    "fell_30",
    "long_below_peak",
    "spike_40_20",
    "loss_year",
    "earnings_down_2y",
    "payout_top_tercile",
    "near_peak_earnings_decline",
    "yield_spike",
]


def usable_year(d: date) -> int:
    """Latest calendar year whose yearly fields are usable on date `d`,
    under the project-wide 1 May reporting-lag rule: year Y becomes usable
    on 1 May of Y+1. A rolling, per-date version of the same rule every
    other hypothesis module here applies only at a handful of fixed
    formation years."""
    if d >= date(d.year, 5, 1):
        return d.year - 1
    return d.year - 2


def month_starts(start: date, end: date) -> list[date]:
    """The first of every month from `start` to `end`, inclusive of `start`,
    exclusive of any month starting after `end`."""
    out = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        out.append(date(y, m, 1))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def load_prices() -> dict:
    return json.loads(PRICES_5Y_PATH.read_text())


def load_universe() -> list[dict]:
    return json.loads(UNIVERSE_PATH.read_text())


def usable_closes_with_dates(entry: dict) -> list[tuple[float, float]]:
    """(timestamp, close) pairs, positive closes only, sorted by time."""
    pairs = [
        (t, c)
        for t, c in zip(entry.get("timestamps", []), entry.get("close", []))
        if c is not None and c > 0
    ]
    pairs.sort(key=lambda p: p[0])
    return pairs


def formation_index(pairs: list[tuple[float, float]], month_start: date) -> int | None:
    """Index (into `pairs`) of the last trading day STRICTLY BEFORE
    `month_start` -- no look-ahead into the formation month itself. None if
    there's no such bar, or fewer than MIN_HISTORY_BARS bars exist up to it."""
    import calendar
    from datetime import datetime, timezone

    cutoff_ts = datetime(month_start.year, month_start.month, month_start.day, tzinfo=timezone.utc).timestamp()
    idx = None
    for i, (t, _c) in enumerate(pairs):
        if t < cutoff_ts:
            idx = i
        else:
            break
    if idx is None or idx + 1 < MIN_HISTORY_BARS:
        return None
    return idx


def w_fell_30(closes: list[float]) -> bool:
    peak = max(closes)
    return closes[-1] <= peak * FALL_THRESHOLD


def w_long_below_peak(closes: list[float]) -> bool:
    last = len(closes) - 1
    for ev in _detect_fall_events(closes):
        if ev["trigger_idx"] <= last - LONG_BELOW_PEAK_BARS and closes[last] < ev["peak_price"]:
            return True
    return False


def w_spike_40_20(closes: list[float]) -> bool:
    if len(closes) <= SPIKE_LOOKBACK_BARS:
        return False
    return closes[-1] >= closes[-1 - SPIKE_LOOKBACK_BARS] * (1 + SPIKE_THRESHOLD)


def w_loss_year(qv: dict, y: int) -> bool:
    e = qv.get(f"earnings[{y}]")
    return e is not None and e < 0


def earnings_declined(qv: dict, year: int) -> bool:
    a, b = qv.get(f"earnings[{year}]"), qv.get(f"earnings[{year - 1}]")
    return a is not None and b is not None and a < b


def w_earnings_down_2y(qv: dict, y: int) -> bool:
    return earnings_declined(qv, y) and earnings_declined(qv, y - 1)


def w_near_peak_earnings_decline(closes: list[float], qv: dict, y: int) -> bool:
    peak = max(closes)
    near_peak = (peak - closes[-1]) / peak <= NEAR_PEAK_THRESHOLD
    return near_peak and earnings_declined(qv, y)


def w_yield_spike(qv: dict, y: int) -> bool:
    current = qv.get(f"total_yield[{y}]")
    prior = [qv.get(f"total_yield[{y - k}]") for k in range(1, YIELD_PRIOR_YEARS + 1)]
    if current is None or any(p is None for p in prior):
        return False
    mean = sum(prior) / YIELD_PRIOR_YEARS
    if mean <= 0:
        return False
    return current >= YIELD_ABOVE_AVG_MULTIPLIER * mean


def payout_ratio(qv: dict, y: int) -> float | None:
    div = qv.get(f"total_dividend[{y}]")
    earnings = qv.get(f"earnings[{y}]")
    shares = qv.get(f"outstanding_shares[{y}]")
    if div is None or earnings is None or shares is None or earnings <= 0 or shares <= 0:
        return None
    eps = earnings / shares
    return div / eps


def sized(qv: dict, y: int) -> tuple[float | None, bool]:
    """(size, flagged) using the plan's flag rule: a stock-year whose share
    count changes by >=50% vs the prior year is flagged and, if the
    following year's count is already usable, takes its size from THAT
    year instead. If the following year isn't usable yet, the flagged
    row's size is None (excluded from cell assignment, not guessed)."""
    cur = qv.get(f"outstanding_shares[{y}]")
    prev = qv.get(f"outstanding_shares[{y - 1}]")
    nxt = qv.get(f"outstanding_shares[{y + 1}]")
    if cur is not None and prev is not None and prev > 0 and abs(cur / prev - 1) >= SIZE_FLAG_CHANGE:
        return (nxt, True) if nxt is not None else (None, True)
    return cur, False


def realised_vol(closes: list[float], window: int = VOL_WINDOW) -> float | None:
    if len(closes) <= window:
        return None
    tail = closes[-(window + 1) :]
    rets = [tail[i] / tail[i - 1] - 1 for i in range(1, len(tail))]
    return statistics.pstdev(rets)


def build_panel(prices: dict, universe: list[dict], end: date) -> tuple[list[dict], dict]:
    """Returns (rows, stats). Each row: symbol, month_start (iso), formation_idx
    (index into that symbol's own price-pair list, for the outcome window later),
    the 8 warning booleans, size, size_flagged, vol_60. Rows needing a payout
    ratio get it filled in a second pass (cross-sectional tercile needs the
    whole month's pool first, done by the caller or `attach_payout_tercile`).
    `stats` reports how many stock-months were skipped and why."""
    starts = month_starts(PANEL_START, end)
    universe_by_symbol = {r["symbol"]: r.get("query_values") or {} for r in universe}

    rows: list[dict] = []
    skipped_no_price = 0
    skipped_short_history = 0
    n_flagged_size = 0

    for symbol, entry in prices.items():
        qv = universe_by_symbol.get(symbol)
        if qv is None:
            skipped_no_price += 1
            continue
        pairs = usable_closes_with_dates(entry)
        if len(pairs) < MIN_HISTORY_BARS:
            skipped_short_history += 1
            continue
        for month_start in starts:
            idx = formation_index(pairs, month_start)
            if idx is None:
                continue
            closes = [c for _t, c in pairs[: idx + 1]]
            y = usable_year(month_start)
            size, flagged = sized(qv, y)
            if flagged:
                n_flagged_size += 1
            rows.append(
                {
                    "symbol": symbol,
                    "month_start": month_start.isoformat(),
                    "formation_idx": idx,
                    "size": size,
                    "size_flagged": flagged,
                    "vol_60": realised_vol(closes),
                    "payout_ratio": payout_ratio(qv, y),
                    "warnings": {
                        "fell_30": w_fell_30(closes),
                        "long_below_peak": w_long_below_peak(closes),
                        "spike_40_20": w_spike_40_20(closes),
                        "loss_year": w_loss_year(qv, y),
                        "earnings_down_2y": w_earnings_down_2y(qv, y),
                        "payout_top_tercile": False,  # filled by attach_payout_tercile
                        "near_peak_earnings_decline": w_near_peak_earnings_decline(closes, qv, y),
                        "yield_spike": w_yield_spike(qv, y),
                    },
                }
            )

    attach_payout_tercile(rows)
    stats = {
        "n_rows": len(rows),
        "n_stocks": len({r["symbol"] for r in rows}),
        "n_months": len(starts),
        "skipped_no_price_for_symbol": skipped_no_price,
        "skipped_short_history": skipped_short_history,
        "n_flagged_size": n_flagged_size,
    }
    return rows, stats


def attach_payout_tercile(rows: list[dict]) -> None:
    """Cross-sectional top-tercile cut of payout_ratio, computed separately
    within each month (mutates `rows` in place)."""
    by_month: dict[str, list[dict]] = {}
    for r in rows:
        by_month.setdefault(r["month_start"], []).append(r)
    for month_rows in by_month.values():
        usable = [r for r in month_rows if r["payout_ratio"] is not None]
        if len(usable) < 3:
            # Too few payers to form terciles this month: explicitly False for
            # everyone, not left unset -- a caller that doesn't pre-populate
            # the key (unlike build_panel) must still get a well-formed row.
            for r in month_rows:
                r["warnings"]["payout_top_tercile"] = False
            continue
        ordered = sorted(usable, key=lambda r: r["payout_ratio"])
        n = len(ordered)
        cutoff_idx = (2 * n) // 3  # top tercile starts here
        top = set(id(r) for r in ordered[cutoff_idx:])
        for r in month_rows:
            r["warnings"]["payout_top_tercile"] = id(r) in top
