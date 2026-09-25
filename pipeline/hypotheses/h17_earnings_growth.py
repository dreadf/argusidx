"""
H17 -- "Laba naik -> harga naik": do companies whose annual net income
grew go on to have higher returns?

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-22") before
this module was run. One falsifiable test, counted as one trial.

- Predictor: earnings[Y] / earnings[Y-1] - 1, only where earnings[Y-1] > 0.
  A yearly field, published by about April Y+1, so it is known strictly
  before the outcome window opens (predictor-before-outcome).
- Outcome: adjclose return 1 May to 4 Sep of Y+1, same window and price
  rule as H5/H10 (constants imported from h5_value_size).
- Method: percentile rank within sub_sector, pooled, Spearman.
  Explore 2022-2023, holdout 2024-2025. Direction fixed in advance: positive.
- Decision rule: CONFIRMED only if holdout p < 0.05 (two-sided) AND explore
  and holdout agree in sign. One test, so no FDR correction.

Run:
    .venv/bin/python -m pipeline.hypotheses.h17_earnings_growth
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pipeline.hypotheses.h5_value_size import EXPLORE_YEARS, HOLDOUT_YEARS, PRICES_5Y_PATH
from pipeline.hypotheses.h10_broad_feature_screen import MAX_PRICE_GAP_DAYS, RETURN_FIELD, UNIVERSE_PATH
from pipeline.stats import nearest_value, normal_two_sided_p, sector_neutral_rank, spearman

ALPHA = 0.05
FEATURE = "earnings_growth"


def earnings_growth(query_values: dict, year: int) -> float | None:
    """earnings[year] / earnings[year-1] - 1, defined only when the prior year was profitable."""
    now = query_values.get(f"earnings[{year}]")
    prior = query_values.get(f"earnings[{year - 1}]")
    if now is None or prior is None or prior <= 0:
        return None
    return now / prior - 1


def build_rows_for_year(universe: list[dict], prices5y: dict, year: int) -> list[dict]:
    formation_dt = datetime(year + 1, 5, 1, tzinfo=timezone.utc)
    outcome_dt = datetime(year + 1, 9, 4, tzinfo=timezone.utc)
    rows = []
    for r in universe:
        qv = r.get("query_values") or {}
        sub_sector = qv.get("sub_sector")
        entry = prices5y.get(r.get("symbol"))
        growth = earnings_growth(qv, year)
        if not entry or not sub_sector or growth is None:
            continue
        p0 = nearest_value(entry, formation_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        p1 = nearest_value(entry, outcome_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        if p0 is None or p1 is None:
            continue
        rows.append({"sym": r["symbol"], "year": year, "sub_sector": sub_sector, "ret": p1 / p0 - 1, FEATURE: growth})
    return rows


def run_phase(universe: list[dict], prices5y: dict, years: list[int], label: str):
    pooled = [row for y in years for row in build_rows_for_year(universe, prices5y, y)]
    ranked = sector_neutral_rank(pooled, FEATURE, "sub_sector")
    print(f"\n{label}: {len(pooled)} pooled rows, {len(ranked)} ranked")
    if len(ranked) < 10:
        print("  insufficient data")
        return None
    c = spearman([r[f"{FEATURE}_rank"] for r in ranked], [r["ret"] for r in ranked])
    p = normal_two_sided_p(c.t)
    print(f"  n={c.n}  rho={c.rho:+.3f}  t={c.t:+.2f}  p={p:.4f}")
    return c, p


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    explore = run_phase(universe, prices5y, EXPLORE_YEARS, "EXPLORE")
    holdout = run_phase(universe, prices5y, HOLDOUT_YEARS, "HOLDOUT")
    if explore is None or holdout is None:
        print("\nVerdict: not enough data")
        return
    (ec, _), (hc, hp) = explore, holdout
    same_sign = (ec.rho > 0) == (hc.rho > 0)
    confirmed = hp < ALPHA and same_sign and hc.rho > 0
    print(f"\nexplore rho={ec.rho:+.3f}  holdout rho={hc.rho:+.3f} p={hp:.4f}  same sign: {same_sign}")
    print(f"H17 verdict: {'CONFIRMED' if confirmed else 'NOT confirmed'} (positive direction, p<{ALPHA}, same sign)")


if __name__ == "__main__":
    main()
