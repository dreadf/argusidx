"""
H4: does a high payout ratio predict a dividend CUT the following year?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (docs/PLAN.md's H4, adopted 2026-09-09 as "near-free" --
`total_dividend[YYYY]` was already purchased, `earnings[YYYY]` unlocked
by the 2026-09-12 sweep): "this dividend may not be sustainable" is a
concrete, checkable, non-advisory flag IF the underlying claim actually
holds on IDX -- untested until now.

Pre-registered hypothesis (committed before looking at any outcome --
NOTE: a units bug in the payout-ratio construction itself was caught
and fixed during the exploratory build, BEFORE the holdout was ever
run/confirmed -- see `stats.payout_ratio_from_totals`'s docstring for
the full story. What's stated below is the CORRECTED formula, which is
what was actually frozen before touching holdout; the initial, briefly-
buggy naive version never produced a published number):
    A company with a HIGH payout ratio in year Y (dividend-per-share
    total_dividend[Y] divided by EPS = earnings[Y]/outstanding_shares[Y],
    restricted to earnings[Y] > 0 and total_dividend[Y] > 0 -- payout
    ratio is undefined for a loss-making company and meaningless for a
    non-payer) is MORE LIKELY to cut its dividend (total_dividend[Y+1] <
    total_dividend[Y]) than a low-payout company. Falsified if: no clear
    monotonic relationship between payout-ratio tercile and cut rate in
    the holdout phase, or if the relationship
    reverses.

Distinct outcome from H10's payout_ratio feature (docs/PLAN.md already
flags this explicitly): H10 tested payout_ratio[year] against subsequent
RETURN and found no confirmed relationship. This tests the same ratio
construction against a DIVIDEND CUT -- a different outcome variable, no
overlap in what's being predicted, despite sharing the numerator/
denominator.

Predictor-before-outcome, same reporting-lag convention as H5/H10:
payout_ratio[Y] is read no earlier than May 1 of Y+1 (the ~4-month
reporting-lag assumption already used project-wide); the outcome
(whether total_dividend[Y+1] is lower than total_dividend[Y]) is only
usable once Y+1's own full-year figure is itself public, i.e. no earlier
than May 1 of Y+2. As of this module's build date (2026-09-13), Y+1=2026
is not yet complete, so the latest usable formation year is Y=2024
(outcome: was total_dividend[2025] < total_dividend[2024]?).

Usable formation years: 2021-2024 (outcome years 2022-2025, all
complete in the purchased data). Explore/holdout split, mirroring the
2-2 shape H5 uses (shifted one year earlier since H4, unlike H5, isn't
blocked by pe[2021]'s absence -- total_dividend[2021]/earnings[2021]
are both present):
    EXPLORE: formation 2021, 2022 -> was the dividend cut in 2022, 2023?
    HOLDOUT: formation 2023, 2024 -> was the dividend cut in 2024, 2025?

Method: payout_ratio terciles (bottom/middle/top) computed separately
within each phase's own pooled sample (explore terciles never see
holdout rows), cut-rate reported per tercile (a base-rate framing,
matching this project's "ship the verdict" convention), plus a single
summary `spearman(payout_ratio, cut_indicator)` -- Spearman handles a
binary outcome fine (equivalent in spirit to a point-biserial
correlation), giving one t-statistic alongside the tercile table rather
than only the table.

Trial count: adds 1 pre-registered trial (holdout tested once).

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/universe_2026-09-12.json -- total_dividend[YYYY],
        earnings[YYYY].

Run:
    .venv/bin/python -m pipeline.hypotheses.h4_payout_dividend_cuts
    .venv/bin/python -m pipeline.hypotheses.h4_payout_dividend_cuts --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pipeline.stats import median_of, payout_ratio_from_totals, quintiles, spearman

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-12.json"

EXPLORE_YEARS = [2021, 2022]
HOLDOUT_YEARS = [2023, 2024]


def build_rows_for_year(universe: list[dict], year: int) -> list[dict]:
    """Payout ratio via `stats.payout_ratio_from_totals` -- see that
    function's docstring for the units bug this avoids (a naive
    `total_dividend/earnings` division is off by shares outstanding, not
    a payout ratio; found building this module, 2026-09-13, and also
    fixed in h10_broad_feature_screen.py's payout_ratio feature, which
    had the identical bug -- now both share one implementation per
    stats.py's own "fix it once" convention, found by /code-review).
    """
    rows = []
    for r in universe:
        qv = r.get("query_values") or {}
        sym = r.get("symbol")
        div_y = qv.get(f"total_dividend[{year}]")
        earnings_y = qv.get(f"earnings[{year}]")
        shares_y = qv.get(f"outstanding_shares[{year}]")
        div_next = qv.get(f"total_dividend[{year + 1}]")
        if div_y is None or div_y <= 0 or div_next is None:
            continue
        payout_ratio = payout_ratio_from_totals(div_y, earnings_y, shares_y)
        if payout_ratio is None:
            continue
        rows.append(
            {
                "sym": sym,
                "year": year,
                "payout_ratio": payout_ratio,
                "cut": 1.0 if div_next < div_y else 0.0,
            }
        )
    return rows


def build_pooled_rows(universe: list[dict], years: list[int]) -> list[dict]:
    pooled: list[dict] = []
    for y in years:
        pooled.extend(build_rows_for_year(universe, y))
    return pooled


def print_phase(rows: list[dict], phase_label: str) -> None:
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} pooled (symbol, formation year) rows\n{'=' * 70}")
    if len(rows) < 10:
        print("  insufficient data, skipped")
        return

    c = spearman([r["payout_ratio"] for r in rows], [r["cut"] for r in rows])
    print(f"\n  payout_ratio vs cut-next-year: rho={c.rho:+.3f}  t={c.t:+.2f}  n={c.n}")

    print("\n  Payout-ratio terciles (T1=lowest payout, T3=highest payout):")
    for i, bucket in enumerate(quintiles(rows, "payout_ratio", n_buckets=3), start=1):
        n = len(bucket)
        cuts = sum(r["cut"] for r in bucket)
        rate = cuts / n if n else float("nan")
        median_pr = median_of(bucket, "payout_ratio")
        print(f"    T{i}: n={n:>4}  payout_ratio_median={median_pr:.2f}  cut_rate={rate:.1%} ({int(cuts)} of {n})")


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())

    print("H4 -- EXPLORE phase (methodology may still change)")
    explore_rows = build_pooled_rows(universe, EXPLORE_YEARS)
    print_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_pooled_rows(universe, HOLDOUT_YEARS)
        print_phase(holdout_rows, "HOLDOUT")
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
