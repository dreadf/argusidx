"""
H4 robustness (item E) -- a disclosure, NOT a new trial and NOT a change to H4.

H4's tercile design and verdict stand. Definitions frozen in EXPERIMENT.md
("Pre-registration, 2026-09-26 (batch 2)"); run once. H4's own modules are
imported unchanged (`h4_payout_dividend_cuts`, `stats`).

Statement of what H4 does today (verified by reading `build_rows_for_year`):
it SKIPS a stock-year whose next-year dividend is missing (`div_next is None`),
so H4's published cut rates are the "missing excluded" variant, not "missing
counted as a cut".

(a) Missing next-year dividend, three ways, for the explore and holdout phases:
    (i) counted as a cut, (ii) excluded (this is H4 as published), (iii) kept
    out of the terciles and shown as a separate bucket (n and median payout
    ratio). Terciles are cut within each phase's own pooled sample of the rows
    the variant uses, as H4 does.
(b) Mechanical-effect check: keep stock-years with earnings[Y+1] >= earnings[Y]
    (both reported) and next-year dividend known; cut rate by payout tercile
    (terciles re-cut within that restricted sample).
(c) Placebo: payout ratios shuffled within `sub_sector` (rows pooled over the
    phase's years), 1,000 times, seed 20260926 (one seeded generator, used in
    sequence); the real holdout Spearman rho (payout ratio vs cut, H4's rows) is
    placed in that distribution.
(d) Note: H10 reused the H5 holdout years for its second screen; a disclosure
    item, no computation.

Run:
    .venv/bin/python -m pipeline.hypotheses.h4_robustness
"""
from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from pipeline.hypotheses.h4_payout_dividend_cuts import (
    EXPLORE_YEARS,
    HOLDOUT_YEARS,
    UNIVERSE_PATH,
    build_pooled_rows,
)
from pipeline.stats import payout_ratio_from_totals, quintiles, spearman

REPO_ROOT = Path(__file__).resolve().parents[2]
PLACEBO_DRAWS = 1000
PLACEBO_SEED = 20260926


def build_rows_incl_missing(universe: list[dict], years: list[int]) -> list[dict]:
    """H4's row rule, except a missing next-year dividend is kept (`div_next` None, `known` False).

    Same payout-ratio construction and skips as `h4_payout_dividend_cuts.build_rows_for_year`.
    """
    rows = []
    for year in years:
        for r in universe:
            qv = r.get("query_values") or {}
            div_y = qv.get(f"total_dividend[{year}]")
            if div_y is None or div_y <= 0:
                continue
            ratio = payout_ratio_from_totals(div_y, qv.get(f"earnings[{year}]"), qv.get(f"outstanding_shares[{year}]"))
            if ratio is None:
                continue
            div_next = qv.get(f"total_dividend[{year + 1}]")
            rows.append(
                {
                    "sym": r.get("symbol"),
                    "year": year,
                    "sub_sector": qv.get("sub_sector"),
                    "payout_ratio": ratio,
                    "known": div_next is not None,
                    "cut": 1.0 if (div_next is None or div_next < div_y) else 0.0,
                    "earn_y": qv.get(f"earnings[{year}]"),
                    "earn_next": qv.get(f"earnings[{year + 1}]"),
                }
            )
    return rows


def tercile_table(rows: list[dict]) -> list[dict]:
    if len(rows) < 3:
        return []
    out = []
    for bucket in quintiles(rows, "payout_ratio", n_buckets=3):
        n = len(bucket)
        cuts = int(sum(r["cut"] for r in bucket))
        out.append({"n": n, "cuts": cuts, "cut_rate": (cuts / n) if n else None,
                    "median_payout": statistics.median(r["payout_ratio"] for r in bucket) if n else None})
    return out


def variants(rows_all: list[dict]) -> dict:
    known = [r for r in rows_all if r["known"]]
    missing = [r for r in rows_all if not r["known"]]
    return {
        "missing_counted_as_cut": tercile_table(rows_all),
        "missing_excluded_as_h4": tercile_table(known),
        "missing_separate_bucket": {
            "terciles_known_only": tercile_table(known),
            "missing_bucket": {
                "n": len(missing),
                "median_payout": statistics.median(r["payout_ratio"] for r in missing) if missing else None,
            },
        },
    }


def mechanical_check(rows_all: list[dict]) -> list[dict]:
    kept = [
        r for r in rows_all
        if r["known"] and r["earn_y"] is not None and r["earn_next"] is not None and r["earn_next"] >= r["earn_y"]
    ]
    return tercile_table(kept)


def shuffled_ratios(rows: list[dict], rng: random.Random) -> list[float]:
    """Payout ratios permuted within sub_sector (rows without one form their own group), in row order."""
    groups: dict = {}
    for i, r in enumerate(rows):
        groups.setdefault(r["sub_sector"], []).append(i)
    out = [r["payout_ratio"] for r in rows]
    for idx in groups.values():
        vals = [rows[i]["payout_ratio"] for i in idx]
        rng.shuffle(vals)
        for i, v in zip(idx, vals):
            out[i] = v
    return out


def placebo(rows: list[dict], draws: int = PLACEBO_DRAWS, seed: int = PLACEBO_SEED) -> dict:
    cuts = [r["cut"] for r in rows]
    real = spearman([r["payout_ratio"] for r in rows], cuts).rho
    rng = random.Random(seed)
    rhos = [spearman(shuffled_ratios(rows, rng), cuts).rho for _ in range(draws)]
    return {
        "n": len(rows),
        "real_rho": real,
        "placebo_mean": statistics.fmean(rhos),
        "placebo_sd": statistics.stdev(rhos) if len(rhos) > 1 else float("nan"),
        "placebo_min": min(rhos),
        "placebo_max": max(rhos),
        "draws": draws,
        "draws_at_or_above_real": sum(1 for x in rhos if x >= real),
    }


def build_robustness(universe: list[dict]) -> dict:
    out: dict = {}
    for name, years in (("explore", EXPLORE_YEARS), ("holdout", HOLDOUT_YEARS)):
        rows_all = build_rows_incl_missing(universe, years)
        known = [r for r in rows_all if r["known"]]
        out[name] = {
            "rows_incl_missing": len(rows_all),
            "rows_known": len(known),
            "rows_h4_module": len(build_pooled_rows(universe, years)),  # cross-check against H4 unchanged
            "variants": variants(rows_all),
            "mechanical_earnings_not_fallen": mechanical_check(rows_all),
        }
    out["placebo_holdout"] = placebo([r for r in build_rows_incl_missing(universe, HOLDOUT_YEARS) if r["known"]])
    return out


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    out = build_robustness(universe)
    print("H4 as published skips stock-years with a missing next-year dividend (missing excluded).")
    for phase in ("explore", "holdout"):
        p = out[phase]
        print(f"\n{phase}: rows incl. missing={p['rows_incl_missing']}, known={p['rows_known']}, H4 module rows={p['rows_h4_module']}")
        for key, val in p["variants"].items():
            print(f"  {key}: {json.dumps(val)}")
        print(f"  mechanical (earnings[Y+1] >= earnings[Y]), terciles: {json.dumps(p['mechanical_earnings_not_fallen'])}")
    print("\nplacebo_holdout:", json.dumps(out["placebo_holdout"]))
    print("(d) Note: H10 reused the H5 holdout years for its second screen (disclosure only).")


if __name__ == "__main__":
    main()
