"""
T1 -- "Kondisi pasar: tertekan": does a market-state label built only from
IHSG's own history predict what happens to IHSG over the next 20 trading
days?

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-27: T1, R1 and
R2a") before this module was run. One falsifiable test, counted as +1 trial.

- State at close t, using data up to t only: `tertekan` if EITHER (a) IHSG
  is >=10% below its running peak-to-date AND below its own 200-day moving
  average, OR (b) its 20-day realised volatility is above the 90th
  percentile of that volatility measure's own expanding history up to t.
- Burn-in: state computed only from trading day 250 onward (2020-01-08 on
  the real M1 data, verified before pre-registering -- the COVID low,
  2020-03-24, falls 53 trading days after burn-in ends, not at its edge).
- Outcomes over t+1..t+20 trading days: A = a further >=5% fall from
  close[t] at any point in the window; B = a >=5% rise from close[t] at any
  point in the window.
- Split: explore = burn-in end through formations whose 20-day window ends
  before 2023-01-01 (a formation whose window would cross the boundary is
  dropped and counted, not partially included). Holdout = formations from
  2023-01-01 onward with a complete 20-day window.
- Primary statistic: on the holdout, (A-B | tertekan) - (A-B | normal).
  CI via a 20-day moving-block bootstrap (preserves the outcome windows'
  serial overlap, which a plain i.i.d. resample of formation days would
  destroy).
- Decision rule: CONFIRMED only if the holdout statistic is > 0, its CI is
  entirely above 0, and explore has the same sign. Anything else is NOT
  confirmed and is published as such.

Run:
    .venv/bin/python -m pipeline.hypotheses.t1_market_state
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass

from pipeline.appdata.common import IHSG_GLOB, RAW_DIR, latest_dated_file
from pipeline.hypotheses._stress_common import moving_block_bootstrap
from pipeline.stats import log_returns, moving_average

BURN_IN_DAYS = 250
VOL_WINDOW = 20
PEAK_DROP_THRESHOLD = 0.10  # the pre-registered 10%; 0.08/0.12 are robustness-only
MA_WINDOW = 200
VOL_PERCENTILE = 0.90
OUTCOME_WINDOW = 20
MOVE_THRESHOLD = 0.05
HOLDOUT_START = "2023-01-01"


@dataclass
class Formation:
    date: str
    state: str  # "tertekan" or "normal"
    a: int  # 1 if a further >=5% fall happened within the outcome window
    b: int  # 1 if a >=5% rise happened within the outcome window


def load_ihsg() -> tuple[list[str], list[float]]:
    path = latest_dated_file(RAW_DIR, IHSG_GLOB)
    rows = json.loads(path.read_text())
    rows = sorted(rows, key=lambda r: r["date"])
    return [r["date"] for r in rows], [r["price"] for r in rows]


def expanding_percentile(values: list[float | None], q: float) -> list[float | None]:
    """out[i] = the q-th percentile of the defined values in values[0..i], using
    only information available up to and including i (no look-ahead)."""
    out: list[float | None] = [None] * len(values)
    seen: list[float] = []
    for i, v in enumerate(values):
        if v is not None:
            seen.append(v)
        if len(seen) >= 2:
            s = sorted(seen)
            pos = q * (len(s) - 1)
            lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
            out[i] = s[lo] + (s[hi] - s[lo]) * (pos - lo)
    return out


def realised_vol_20(closes: list[float]) -> list[float | None]:
    """Trailing 20-day standard deviation of daily log returns, aligned to
    `closes` (same length, None where fewer than 20 returns exist yet)."""
    rets = log_returns(closes)  # rets[i] = log(closes[i+1]/closes[i]), length n-1
    n = len(closes)
    out: list[float | None] = [None] * n
    for i in range(n):
        # returns available up to and including day i are rets[0..i-1]
        window = rets[max(0, i - VOL_WINDOW) : i]
        if len(window) == VOL_WINDOW:
            out[i] = statistics.pstdev(window)
    return out


def compute_states(closes: list[float], peak_drop_threshold: float = PEAK_DROP_THRESHOLD) -> list[str | None]:
    """state[i] is None before burn-in; otherwise 'tertekan' or 'normal'."""
    n = len(closes)
    ma200 = moving_average(closes, MA_WINDOW)
    vol20 = realised_vol_20(closes)
    vol_p90 = expanding_percentile(vol20, VOL_PERCENTILE)

    peak = 0.0
    states: list[str | None] = [None] * n
    for i in range(n):
        if closes[i] > peak:
            peak = closes[i]
        if i < BURN_IN_DAYS - 1:
            continue
        dist_from_peak = closes[i] / peak - 1
        cond_a = dist_from_peak <= -peak_drop_threshold and ma200[i] is not None and closes[i] < ma200[i]
        cond_b = vol20[i] is not None and vol_p90[i] is not None and vol20[i] > vol_p90[i]
        states[i] = "tertekan" if (cond_a or cond_b) else "normal"
    return states


def build_formations(dates: list[str], closes: list[float], states: list[str | None]) -> tuple[list[Formation], int]:
    """Returns (formations with a complete outcome window, count dropped for
    insufficient trailing data at the series end)."""
    n = len(closes)
    formations: list[Formation] = []
    dropped_end = 0
    for i in range(n):
        if states[i] is None:
            continue
        window_end = i + OUTCOME_WINDOW
        if window_end >= n:
            dropped_end += 1
            continue
        window = closes[i + 1 : window_end + 1]
        base = closes[i]
        a = 1 if any(c <= base * (1 - MOVE_THRESHOLD) for c in window) else 0
        b = 1 if any(c >= base * (1 + MOVE_THRESHOLD) for c in window) else 0
        formations.append(Formation(date=dates[i], state=states[i], a=a, b=b))
    return formations, dropped_end


def split_explore_holdout(formations: list[Formation], dates: list[str]) -> tuple[list[Formation], list[Formation], int]:
    """Embargo at the boundary: an explore-side formation whose outcome window's
    last date falls on or after HOLDOUT_START is dropped (its window would reach
    into holdout territory), not counted in either half. Returns (explore, holdout,
    n_dropped_to_embargo)."""
    date_index = {d: i for i, d in enumerate(dates)}
    explore, holdout = [], []
    dropped = 0
    for f in formations:
        if f.date >= HOLDOUT_START:
            holdout.append(f)
            continue
        i = date_index[f.date]
        window_end_date = dates[i + OUTCOME_WINDOW]
        if window_end_date >= HOLDOUT_START:
            dropped += 1
            continue
        explore.append(f)
    return explore, holdout, dropped


def diff_in_diff(formations: list[Formation]) -> float | None:
    """(mean A - mean B | tertekan) - (mean A - mean B | normal). None if
    either group is empty (matching this project's NaN/None-for-insufficient-
    data convention)."""
    tertekan = [f for f in formations if f.state == "tertekan"]
    normal = [f for f in formations if f.state == "normal"]
    if not tertekan or not normal:
        return None
    ab_tertekan = statistics.mean(f.a for f in tertekan) - statistics.mean(f.b for f in tertekan)
    ab_normal = statistics.mean(f.a for f in normal) - statistics.mean(f.b for f in normal)
    return ab_tertekan - ab_normal


def main() -> None:
    dates, closes = load_ihsg()
    print(f"IHSG series: {len(closes)} trading days, {dates[0]} to {dates[-1]}")

    states = compute_states(closes)
    burn_in_date = dates[BURN_IN_DAYS - 1]
    print(f"Burn-in ends at trading day {BURN_IN_DAYS} ({burn_in_date})")

    formations, dropped_end = build_formations(dates, closes, states)
    explore, holdout, dropped_embargo = split_explore_holdout(formations, dates)
    print(f"Formations: {len(formations)} total, {dropped_end} dropped (insufficient trailing data),")
    print(f"  {dropped_embargo} dropped at the embargo (window would cross into holdout)")
    print(f"  explore: {len(explore)} ({sum(1 for f in explore if f.state == 'tertekan')} tertekan)")
    print(f"  holdout: {len(holdout)} ({sum(1 for f in holdout if f.state == 'tertekan')} tertekan)")

    explore_stat = diff_in_diff(explore)
    holdout_stat = diff_in_diff(holdout)
    print(f"\nExplore (A-B|tertekan) - (A-B|normal): {explore_stat}")
    print(f"Holdout (A-B|tertekan) - (A-B|normal): {holdout_stat}")

    boot = moving_block_bootstrap(holdout, diff_in_diff, block_len=OUTCOME_WINDOW)
    print(f"Holdout 20-day moving-block bootstrap CI: [{boot['low']:.4f}, {boot['high']:.4f}] "
          f"(estimate {boot['estimate']:.4f}, {boot['n_valid_replicates']} valid replicates)")

    ci_low_positive = boot["low"] == boot["low"] and boot["low"] > 0  # False (not an error) if low is NaN
    confirmed = (
        holdout_stat is not None and holdout_stat > 0
        and ci_low_positive
        and explore_stat is not None and explore_stat > 0
    )
    print(f"\n**T1: {'CONFIRMED' if confirmed else 'NOT confirmed'}**")

    print("\n--- Robustness (reported, not additional trials) ---")
    for threshold in (0.08, 0.12):
        states_r = compute_states(closes, peak_drop_threshold=threshold)
        formations_r, _ = build_formations(dates, closes, states_r)
        _, holdout_r, _ = split_explore_holdout(formations_r, dates)
        stat_r = diff_in_diff(holdout_r)
        print(f"  peak threshold {threshold:.0%}: holdout statistic = {stat_r}")
    print("  ARB-7%-period exclusion: NOT run. The pre-registration requires the ARB")
    print("  regime's dates to be verified against IDX before this check is reported;")
    print("  that verification has not happened yet, so this robustness check is")
    print("  skipped rather than run on an assumed date range.")


if __name__ == "__main__":
    main()
