"""R4: H5, H10 and H4 re-tabulated by market state at their already-fixed
formation dates.

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-28: R3 and R4")
before this module was run. NOT a trial: no new formation logic, no new
decision rule -- every entry date is already fixed by each hypothesis's
own pre-registered methodology; this only adds a state label found via
`t1_market_state.compute_states` (already run for T1) and re-tabulates
each hypothesis's own already-computed relationship by that one extra cut.

Disclosed confound (see the pre-registration entry): for H5/H10, state is
perfectly collinear with explore/holdout phase, so their split cannot
separate a state effect from a phase effect. H4 alone has within-holdout
variation (2023-formation normal, 2024-formation tertekan) and is the one
comparison in this module not confounded that way.

Run:
    .venv/bin/python -m pipeline.hypotheses.r4_market_state_split
"""
from __future__ import annotations

import json
from datetime import date

from pipeline.hypotheses.h4_payout_dividend_cuts import UNIVERSE_PATH as H4_UNIVERSE_PATH
from pipeline.hypotheses.h4_payout_dividend_cuts import (
    EXPLORE_YEARS as H4_EXPLORE_YEARS,
)
from pipeline.hypotheses.h4_payout_dividend_cuts import (
    HOLDOUT_YEARS as H4_HOLDOUT_YEARS,
)
from pipeline.hypotheses.h4_payout_dividend_cuts import build_rows_for_year as h4_rows_for_year
from pipeline.hypotheses.h5_value_size import EXPLORE_YEARS as H5_EXPLORE_YEARS
from pipeline.hypotheses.h5_value_size import HOLDOUT_YEARS as H5_HOLDOUT_YEARS
from pipeline.hypotheses.h5_value_size import PRICES_5Y_PATH
from pipeline.hypotheses.h5_value_size import UNIVERSE_PATH as H5_UNIVERSE_PATH
from pipeline.hypotheses.h5_value_size import build_rows_for_year as h5_rows_for_year
from pipeline.hypotheses.t1_market_state import compute_states, load_ihsg
from pipeline.stats import median_of, quintiles, spearman


def state_lookup() -> tuple[list[str], list[str | None]]:
    dates, closes = load_ihsg()
    return dates, compute_states(closes)


def state_on_or_after(dates: list[str], states: list[str | None], target: str) -> tuple[str, str | None]:
    """Nearest trading day on/after `target` and its state."""
    for d, s in zip(dates, states):
        if d >= target:
            return d, s
    raise ValueError(f"{target} is after the end of the IHSG series")


def h5_entry_date(formation_year: int) -> str:
    return date(formation_year + 1, 5, 1).isoformat()


def h4_entry_date(formation_year: int) -> str:
    return date(formation_year + 1, 5, 1).isoformat()


def run_h5(dates: list[str], states: list[str | None]) -> None:
    print("\n" + "=" * 70)
    print("H5 (value/size), per formation year, annotated with market state")
    print("=" * 70)
    universe = json.loads(H5_UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    for phase, years in (("explore", H5_EXPLORE_YEARS), ("holdout", H5_HOLDOUT_YEARS)):
        for year in years:
            entry = h5_entry_date(year)
            entry_trading_day, state = state_on_or_after(dates, states, entry)
            rows = h5_rows_for_year(universe, prices5y, year)
            print(f"\n{phase} formation {year} (entry {entry_trading_day}, state={state}) -- n={len(rows)}")
            if len(rows) < 10:
                print("  insufficient data, skipped")
                continue
            c_val = spearman([r["earnings_yield"] for r in rows], [r["ret"] for r in rows])
            c_size = spearman([r["size"] for r in rows], [r["ret"] for r in rows])
            print(f"  earnings_yield vs return: rho={c_val.rho:+.3f}  t={c_val.t:+.2f}")
            print(f"  size vs return: rho={c_size.rho:+.3f}  t={c_size.t:+.2f}")


def run_h10_note() -> None:
    print("\n" + "=" * 70)
    print("H10 (broad feature screen)")
    print("=" * 70)
    print("Shares H5's EXPLORE_YEARS/HOLDOUT_YEARS and therefore the exact")
    print("same state-vs-phase confound shown for H5 above (same entry dates,")
    print("same states: explore=normal, holdout=tertekan). Not re-run feature")
    print("by feature here -- the confound already makes the split uninformative")
    print("for any of H10's features on this data, for the same reason as H5.")


def run_h4(dates: list[str], states: list[str | None]) -> None:
    print("\n" + "=" * 70)
    print("H4 (payout ratio -> dividend cut), per formation year, annotated with market state")
    print("=" * 70)
    universe = json.loads(H4_UNIVERSE_PATH.read_text())
    by_year: dict[int, tuple[str, str | None, list[dict]]] = {}
    for phase, years in (("explore", H4_EXPLORE_YEARS), ("holdout", H4_HOLDOUT_YEARS)):
        for year in years:
            entry = h4_entry_date(year)
            entry_trading_day, state = state_on_or_after(dates, states, entry)
            rows = h4_rows_for_year(universe, year)
            by_year[year] = (entry_trading_day, state, rows)
            print(f"\n{phase} formation {year} (entry {entry_trading_day}, state={state}) -- n={len(rows)}")
            if len(rows) < 10:
                print("  insufficient data, skipped")
                continue
            c = spearman([r["payout_ratio"] for r in rows], [r["cut"] for r in rows])
            print(f"  payout_ratio vs cut-next-year: rho={c.rho:+.3f}  t={c.t:+.2f}  n={c.n}")
            for i, bucket in enumerate(quintiles(rows, "payout_ratio", n_buckets=3), start=1):
                n = len(bucket)
                cuts = sum(r["cut"] for r in bucket)
                rate = cuts / n if n else float("nan")
                print(f"    T{i}: n={n:>4}  cut_rate={rate:.1%} ({int(cuts)} of {n})")

    print("\n--- The one within-phase state comparison in this batch (H4 holdout years) ---")
    for year in H4_HOLDOUT_YEARS:
        entry_trading_day, state, rows = by_year[year]
        cuts = sum(r["cut"] for r in rows)
        n = len(rows)
        rate = cuts / n if n else float("nan")
        print(f"  formation {year} (state={state}): cut_rate={rate:.1%} ({int(cuts)} of {n})")


def main() -> None:
    dates, states = state_lookup()
    print(f"IHSG state series: {len(dates)} trading days, {dates[0]} to {dates[-1]}")
    run_h5(dates, states)
    run_h10_note()
    run_h4(dates, states)


if __name__ == "__main__":
    main()
