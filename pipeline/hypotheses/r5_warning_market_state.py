"""
R5 -- do active warnings matter more during a stressed market? A
difference-in-differences of D-U (2+ warnings vs 0) between stressed and
normal formation months, holdout only.

Plan reference: `kind-juggling-hoare.md` section 5, R5. As with R2b, this
module's exact spec was fixed in the approved plan text before any code
existed, but the EXPERIMENT.md pre-registration entry for it is written
after running it (same disclosed deviation as R2b, at the user's explicit
instruction to keep moving).

**Correction to the plan's stated premise, found while building this**: the
plan says "the explore period has no stressed months." Checked directly
against T1's real fitted states (not assumed): explore (through
2023-12-31) has exactly ONE stressed month, 2022-06-01, a single isolated
episode, not a sustained one. This is close enough to the plan's premise
that its holdout-only design still stands (this test is fundamentally
about the 2025-2026 stress episode, which explore barely touches), but it
is not literally true as stated, so it's corrected here rather than
silently assumed.

"Stressed": a formation month is stressed if T1's state (recomputed on
the real IHSG series, `t1_market_state.compute_states`) at the last IHSG
trading day before that month-start is 'tertekan'. Groups: 0 warnings vs
2+ warnings (using R1's merged 7-warning list), same D/U outcomes and
size x volatility cells as R2a/R2b, holdout only (2024-01-01 onward).

**Episode minimum, this module's own operationalization (the plan states
the idea, "a trial only if the episode minimum is met," without a number)**:
each of the 4 groups (0-stressed, 2+-stressed, 0-normal, 2+-normal) needs
>=30 holdout observations, POOLED across cells (not cell-weighted -- R5
splits the panel two more ways than R2a/R2b already did, and cell-weighting
on top would very likely starve every cell the same way R2a's did). If any
group falls short, R5 is descriptive, not a trial -- same fallback pattern
as R2a and R2b.

Decision (this module's own choice, since the plan doesn't state a
significance threshold for R5 specifically): CONFIRMED only if the DiD
statistic -- (DU[2+,stressed] - DU[0,stressed]) - (DU[2+,normal] -
DU[0,normal]) -- is > 0 and its stock-clustered bootstrap CI (2,000
replicates, same method as T1/R2b) is entirely above 0.

Run:
    .venv/bin/python -m pipeline.hypotheses.r5_warning_market_state
"""
from __future__ import annotations

import random
import statistics
from datetime import date, datetime, timezone

from pipeline.hypotheses._stress_common import BOOTSTRAP_B, SEED, percentile_interval
from pipeline.hypotheses._warnings_panel import build_panel, formation_index, load_prices, load_universe, month_starts, PANEL_START
from pipeline.hypotheses.r1_warning_overlap import PANEL_END
from pipeline.hypotheses.r2a_warning_count import (
    attach_terciles,
    compute_outcomes,
    count_bucket,
    load_suspensions,
    merged_warning_keys,
    split_explore_holdout,
    warning_count,
)
from pipeline.hypotheses.t1_market_state import compute_states, load_ihsg

MIN_GROUP = 30


def stressed_months(end: date) -> dict[str, str]:
    """month_start (iso) -> T1 state ('tertekan'/'normal') at the last IHSG
    trading day strictly before that month-start."""
    ihsg_dates, ihsg_closes = load_ihsg()
    states = compute_states(ihsg_closes)
    pairs = [
        (datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp(), c)
        for d, c in zip(ihsg_dates, ihsg_closes)
    ]
    out: dict[str, str] = {}
    for month_start in month_starts(PANEL_START, end):
        idx = formation_index(pairs, month_start)
        if idx is not None and states[idx] is not None:
            out[month_start.isoformat()] = states[idx]
    return out


def group_stats(rows: list[dict], stressed: dict[str, str], keys: list[str], count_min: int, market: str) -> tuple[float | None, int]:
    """(D-U, n) for rows whose active-warning count >= count_min (or == 0 if
    count_min == 0) and whose market state matches `market`."""
    group = [
        r
        for r in rows
        if stressed.get(r["month_start"]) == market
        and ((warning_count(r, keys) == 0) if count_min == 0 else (count_bucket(warning_count(r, keys)) >= count_min))
    ]
    if not group:
        return None, 0
    du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
    return du, len(group)


def did_stat(rows: list[dict], stressed: dict[str, str], keys: list[str]) -> float | None:
    du_2plus_stressed, _ = group_stats(rows, stressed, keys, 2, "tertekan")
    du_0_stressed, _ = group_stats(rows, stressed, keys, 0, "tertekan")
    du_2plus_normal, _ = group_stats(rows, stressed, keys, 2, "normal")
    du_0_normal, _ = group_stats(rows, stressed, keys, 0, "normal")
    if None in (du_2plus_stressed, du_0_stressed, du_2plus_normal, du_0_normal):
        return None
    return (du_2plus_stressed - du_0_stressed) - (du_2plus_normal - du_0_normal)


def bootstrap_ci(rows: list[dict], stressed: dict[str, str], keys: list[str]) -> dict:
    by_stock: dict[str, list[dict]] = {}
    for r in rows:
        by_stock.setdefault(r["symbol"], []).append(r)
    stocks = sorted(by_stock)
    rng = random.Random(SEED)
    real = did_stat(rows, stressed, keys)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_B):
        sample: list[dict] = []
        for _k in range(len(stocks)):
            sample.extend(by_stock[stocks[rng.randrange(len(stocks))]])
        v = did_stat(sample, stressed, keys)
        if v is not None:
            draws.append(v)
    lo, hi = percentile_interval(draws) if draws else (float("nan"), float("nan"))
    return {"estimate": real, "low": lo, "high": hi, "n_valid_replicates": len(draws)}


def main() -> None:
    prices = load_prices()
    universe = load_universe()
    rows, panel_stats = build_panel(prices, universe, end=PANEL_END)
    keys = merged_warning_keys(rows)
    print(f"Panel: {panel_stats}")
    print(f"Warning keys: {keys}\n")

    suspensions = load_suspensions()
    rows, _dropped_end = compute_outcomes(rows, prices, suspensions)
    attach_terciles(rows)
    explore, holdout, _dropped_embargo = split_explore_holdout(rows)

    stressed = stressed_months(PANEL_END)
    n_stressed_explore = sum(1 for r in explore if stressed.get(r["month_start"]) == "tertekan")
    n_stressed_holdout = sum(1 for r in holdout if stressed.get(r["month_start"]) == "tertekan")
    print(f"Stressed-month formations: explore {n_stressed_explore} of {len(explore)}, "
          f"holdout {n_stressed_holdout} of {len(holdout)}")

    counts = {}
    for market in ("tertekan", "normal"):
        for count_min, label in ((0, "0"), (2, "2+")):
            _du, n = group_stats(holdout, stressed, keys, count_min, market)
            counts[(market, label)] = n
    print("\nHoldout group sizes:")
    for k, n in counts.items():
        print(f"  {k}: n={n}")

    if min(counts.values()) < MIN_GROUP:
        print(f"\n**R5: at least one group has fewer than {MIN_GROUP} holdout observations -- DESCRIPTIVE, not a trial.**")
        for market in ("tertekan", "normal"):
            for count_min, label in ((0, "0"), (2, "2+")):
                du, n = group_stats(holdout, stressed, keys, count_min, market)
                print(f"  {market}, {label} warnings: n={n}, D-U={du}")
        return

    boot = bootstrap_ci(holdout, stressed, keys)
    print(f"\nDiD estimate: {boot['estimate']}")
    print(f"Bootstrap CI: [{boot['low']:.4f}, {boot['high']:.4f}] ({boot['n_valid_replicates']} valid replicates)")

    ci_above_zero = boot["low"] == boot["low"] and boot["low"] > 0  # False (not an error) if low is NaN
    confirmed = boot["estimate"] is not None and boot["estimate"] > 0 and ci_above_zero
    print(f"\n**R5: {'CONFIRMED' if confirmed else 'NOT confirmed'}**")


if __name__ == "__main__":
    main()
