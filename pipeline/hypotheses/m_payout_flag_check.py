"""
Check and base rate (situation I2, "Dividen besar dibanding laba").

NOT a falsifiable hypothesis -- descriptive, no significance test, not
counted in the trial counter, no new outcome test. Definitions were frozen
in EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 1)"); run once.

(a) Construct check. The app flag `payout_above_earnings`
    (`pipeline.appdata.build_flags.build_payout_above_earnings`) trips on the
    snapshot field `payout_ratio` > 1.0 (exactly 100% does not trip it). H4
    measures the payout ratio as `stats.payout_ratio_from_totals(
    total_dividend[Y], earnings[Y], outstanding_shares[Y])`. For every flagged
    stock this module recomputes the H4 ratio for the last complete fiscal
    year (Y = 2025, the "prior year" as of the universe date) and reports
    every stock where the two disagree, i.e. the recomputed ratio is not
    above 1.0 or is undefined (no dividend, earnings <= 0, or shares
    missing). Y = 2024 is printed beside it as a sensitivity, since the
    snapshot field is a trailing figure and not tied to one fiscal year.
(b) Cut rates. From `h4_payout_dividend_cuts.build_pooled_rows` (unchanged),
    the share of rows with payout ratio strictly above 1.0 whose next-year
    dividend was lower than the year's own, for H4's explore (formation 2021,
    2022) and holdout (2023, 2024) phases. H4 itself published tercile cut
    rates, not an above-100% bucket, so this bucket is a recomputation from
    H4's rows, not a copy of a published number.

Limits: the snapshot `payout_ratio` and the fiscal-year ratio are different
measurements even when they agree on the side of 100%; H4's mechanical-effect
caveat (a payout above 100% leaves little room for a profit dip) applies.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_payout_flag_check
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.appdata.build_flags import PAYOUT_RATIO_THRESHOLD, build_payout_above_earnings
from pipeline.hypotheses.h4_payout_dividend_cuts import (
    EXPLORE_YEARS,
    HOLDOUT_YEARS,
    UNIVERSE_PATH as H4_UNIVERSE_PATH,
    build_pooled_rows,
)
from pipeline.stats import payout_ratio_from_totals

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"


def h4_ratio(qv: dict, year: int) -> float | None:
    return payout_ratio_from_totals(
        qv.get(f"total_dividend[{year}]"),
        qv.get(f"earnings[{year}]"),
        qv.get(f"outstanding_shares[{year}]"),
    )


def check_flag_construct(universe: list[dict], year: int) -> dict:
    """Recompute the H4 ratio for every stock the flag marks; list those that do not exceed 1.0."""
    flagged = build_payout_above_earnings(universe)["flagged"]
    by_symbol = {r["symbol"]: r.get("query_values") or {} for r in universe}
    agree = 0
    disagree: list[dict] = []
    for f in flagged:
        recomputed = h4_ratio(by_symbol[f["symbol"]], year)
        if recomputed is not None and recomputed > PAYOUT_RATIO_THRESHOLD:
            agree += 1
        else:
            disagree.append({"symbol": f["symbol"], "snapshot": f["payout_ratio"], "recomputed": recomputed})
    return {
        "year": year,
        "flagged": len(flagged),
        "agree": agree,
        "disagree": len(disagree),
        "disagree_undefined": sum(1 for d in disagree if d["recomputed"] is None),
        "disagree_at_or_below_1": sum(1 for d in disagree if d["recomputed"] is not None),
        "disagreements": disagree,
    }


def cut_rate_above_100(universe: list[dict], years: list[int]) -> dict:
    rows = [r for r in build_pooled_rows(universe, years) if r["payout_ratio"] > PAYOUT_RATIO_THRESHOLD]
    n = len(rows)
    cuts = int(sum(r["cut"] for r in rows))
    return {"n": n, "cuts": cuts, "cut_rate": (cuts / n) if n else None}


def build_payout_flag_check(universe: list[dict], h4_universe: list[dict]) -> dict:
    return {
        "construct_check_2025": check_flag_construct(universe, 2025),
        "construct_check_2024": check_flag_construct(universe, 2024),
        "cut_rate_above_100_h4_universe": {
            "explore": cut_rate_above_100(h4_universe, EXPLORE_YEARS),
            "holdout": cut_rate_above_100(h4_universe, HOLDOUT_YEARS),
        },
        "cut_rate_above_100_this_universe": {
            "explore": cut_rate_above_100(universe, EXPLORE_YEARS),
            "holdout": cut_rate_above_100(universe, HOLDOUT_YEARS),
        },
    }


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    h4_universe = json.loads(H4_UNIVERSE_PATH.read_text())
    out = build_payout_flag_check(universe, h4_universe)
    for key in ("construct_check_2025", "construct_check_2024"):
        c = out[key]
        print(
            f"{key}: flagged={c['flagged']} agree={c['agree']} disagree={c['disagree']} "
            f"(undefined={c['disagree_undefined']}, recomputed<=1.0={c['disagree_at_or_below_1']})"
        )
    print("Disagreements (Y=2025):")
    for d in out["construct_check_2025"]["disagreements"]:
        print("  ", d)
    print(f"Cut rate, payout ratio > 100% (H4 universe file {H4_UNIVERSE_PATH.name}):", out["cut_rate_above_100_h4_universe"])
    print(f"Cut rate, payout ratio > 100% (universe file {UNIVERSE_PATH.name}):", out["cut_rate_above_100_this_universe"])


if __name__ == "__main__":
    main()
