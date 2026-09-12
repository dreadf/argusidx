"""
H10: broad pre-registered feature screen -- which single features predict
subsequent IDX returns, tested honestly, with nulls published just like
positives.

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (docs/PLAN.md's H10 section, adopted 2026-09-09): single
hypotheses (H1, H5) answer "does this one thing predict returns" one at a
time. This tests several PRE-REGISTERED candidates at once, honestly --
the trap being p-hacking (testing 20 unrelated things yields ~1
"significant" result by chance alone at the usual 5% threshold). The
discipline that separates this from a fishing trip: every feature listed
below is frozen before any result is seen, tested identically in explore
and holdout, and reported in full -- including whatever comes back null --
with Benjamini-Hochberg FDR correction across the whole batch, not a bare
per-test ~1.96 threshold.

Pre-registered features (written before running anything), each a yearly
`field[year]` (predictor-before-outcome; no snapshot field qualifies, see
CLAUDE.md):

1. earnings_yield = 1/pe[year], pe>0 only. OVERLAPS H5's already-confirmed
   value leg -- not independent evidence; kept for completeness under the
   sector-neutral-rank methodology, disclosed explicitly rather than
   presented as a fresh result.
2. roe[year] -- quality. H15 tested this only inside an interaction
   (quality x uptrend, null); this is the first STANDALONE test.
3. debt_to_equity_ratio[year] -- leverage. Same H15 relationship: tested
   only inside an interaction there (high-leverage x downtrend, null);
   standalone here for the first time. Predicted direction: negative
   (higher leverage -> lower subsequent return).
4. total_yield[year] -- realized dividend yield. Belief under test: "high
   dividend yield means better returns." Not tested standalone anywhere
   else in this project.
5. size = outstanding_shares[year] * raw close at formation. OVERLAPS
   H5's size leg (unconfirmed lead, not a validated finding there either)
   -- disclosed, not independent evidence.
6. revenue_growth = revenue[year] / revenue[year-1] - 1, revenue[year-1]
   > 0 only. Belief under test: growing companies keep growing (or:
   growth is already priced in and doesn't predict forward return).
7. payout_ratio = total_dividend[year] / earnings[year], earnings[year] >
   0 only. Belief under test: a high payout ratio predicts WORSE forward
   returns (the "unsustainable yield" story). Distinct from the future
   H4 (payout ratio -> DIVIDEND CUT, a different outcome variable) --
   same numerator/denominator construction, different question, no
   overlap in outcome.

No interaction terms here -- H15 already covers pre-registered
interactions under its own trial count; adding more here would double-
count that work under a different name.

Pooling -- sector-neutral ranks, decided in the plan before this was
built: comparing a bank's raw P/E to a miner's is partly meaningless
(sector multiples differ systematically), and per-sub_sector correlation
would be far too small-sample for the tiniest groups (`Tobacco` has 4
companies in the plan's own count). Chosen: convert each feature to a
percentile RANK within the company's own sub_sector before pooling
(`pipeline.stats.sector_neutral_rank`, new this module) -- strips
systematic sector differences while keeping the full pooled sample.

Explore/holdout: EXPLORE_YEARS/HOLDOUT_YEARS imported directly from
h5_value_size.py, so this can never silently drift from H1/H5/H14/H15's
own boundary (2022-2023 explore, 2024-2025 holdout, same May-1-to-Sep-4
formation-lag window).

Multiple-comparisons correction: Benjamini-Hochberg FDR at q=0.10 across
all 7 holdout tests (pipeline.stats.benjamini_hochberg, new this session
-- p-values via the standard-normal approximation this project already
implicitly uses for its ~1.96 threshold, math.erfc, no scipy). Explore
does not count as a separate trial (matching H5/H15's own convention).
Pre-declared level and correction stated here, before running, not
chosen after seeing which survives.

Publish the entire scoreboard -- every feature, holdout result, and
FDR verdict, whether or not anything survives. Trial count: adds 7
pre-registered feature tests to the project total.

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/universe_2026-09-12.json -- pe/roe/debt_to_equity_ratio/
        total_yield/total_dividend/earnings/revenue/outstanding_shares
        [YYYY], sub_sector (used for sector-neutral ranking).
    data/dev_cache/prices_5y.json -- Yahoo, dev-only, close (raw price,
        matching h5_value_size.py's size-proxy convention) for the size
        feature's price component.

Run:
    .venv/bin/python -m pipeline.hypotheses.h10_broad_feature_screen
    .venv/bin/python -m pipeline.hypotheses.h10_broad_feature_screen --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline.hypotheses.h5_value_size import EXPLORE_YEARS, HOLDOUT_YEARS, PRICES_5Y_PATH
from pipeline.stats import benjamini_hochberg, nearest_value, normal_two_sided_p, sector_neutral_rank, spearman

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-12.json"
MAX_PRICE_GAP_DAYS = 10
RETURN_FIELD = "adjclose"  # matches h5_value_size.py -- return measurement
# must include dividends; the size feature's PRICE component below
# deliberately uses raw "close" instead, same reasoning as h5_value_size.py.
FDR_Q = 0.10

# label -> callable(query_values, year) -> float | None. Each is computed
# strictly from `year`'s figures (and, for revenue_growth, `year-1`'s) --
# predictor-before-outcome by construction.
FEATURES = ["earnings_yield", "roe", "debt_to_equity_ratio", "total_yield", "size", "revenue_growth", "payout_ratio"]


def build_rows_for_year(universe: list[dict], prices5y: dict, year: int) -> list[dict]:
    formation_dt = datetime(year + 1, 5, 1, tzinfo=timezone.utc)
    outcome_dt = datetime(year + 1, 9, 4, tzinfo=timezone.utc)
    rows = []
    for r in universe:
        sym = r.get("symbol")
        qv = r.get("query_values") or {}
        sub_sector = qv.get("sub_sector")
        entry = prices5y.get(sym)
        if not entry or not sub_sector:
            continue

        p0_raw = nearest_value(entry, formation_dt, field="close", max_gap_days=MAX_PRICE_GAP_DAYS)
        p0 = nearest_value(entry, formation_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        p1 = nearest_value(entry, outcome_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        if p0_raw is None or p0 is None or p1 is None:
            continue
        ret = p1 / p0 - 1

        pe = qv.get(f"pe[{year}]")
        roe = qv.get(f"roe[{year}]")
        der = qv.get(f"debt_to_equity_ratio[{year}]")
        yld = qv.get(f"total_yield[{year}]")
        shares = qv.get(f"outstanding_shares[{year}]")
        div = qv.get(f"total_dividend[{year}]")
        earnings = qv.get(f"earnings[{year}]")
        revenue = qv.get(f"revenue[{year}]")
        revenue_prev = qv.get(f"revenue[{year - 1}]")

        row: dict = {"sym": sym, "year": year, "sub_sector": sub_sector, "ret": ret}
        row["earnings_yield"] = 1.0 / pe if pe is not None and pe > 0 else None
        row["roe"] = roe
        row["debt_to_equity_ratio"] = der
        row["total_yield"] = yld
        row["size"] = shares * p0_raw if shares is not None and shares > 0 else None
        row["revenue_growth"] = (
            revenue / revenue_prev - 1 if revenue is not None and revenue_prev is not None and revenue_prev > 0 else None
        )
        row["payout_ratio"] = div / earnings if div is not None and earnings is not None and earnings > 0 else None
        rows.append(row)
    return rows


def build_pooled_rows(universe: list[dict], prices5y: dict, years: list[int]) -> list[dict]:
    pooled: list[dict] = []
    for y in years:
        pooled.extend(build_rows_for_year(universe, prices5y, y))
    return pooled


def run_phase(universe: list[dict], prices5y: dict, years: list[int], phase_label: str) -> dict:
    pooled = build_pooled_rows(universe, prices5y, years)
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(pooled)} pooled (symbol, formation year) rows\n{'=' * 70}")

    results = {}
    for feature in FEATURES:
        ranked = sector_neutral_rank(pooled, feature, "sub_sector")
        if len(ranked) < 10:
            print(f"\n{feature}: insufficient data (n={len(ranked)}), skipped")
            results[feature] = None
            continue
        c = spearman([r[f"{feature}_rank"] for r in ranked], [r["ret"] for r in ranked])
        p = normal_two_sided_p(c.t)
        print(f"\n{feature}: n={c.n}  rho={c.rho:+.3f}  t={c.t:+.2f}  p={p:.4f}")
        results[feature] = (c, p)
    return results


def print_holdout_verdicts(explore_results: dict, holdout_results: dict) -> None:
    """FDR alone is not enough to call a feature confirmed -- every earlier
    hypothesis here (H1, H5, H14, H15) also requires explore and holdout to
    AGREE IN SIGN, since a result that only shows up in one phase (or flips
    sign between them) is exactly H5's own already-documented size-leg
    weakness. This prints both checks side by side rather than letting the
    FDR column alone imply "confirmed."
    """
    p_values = [holdout_results[f][1] if holdout_results[f] is not None else float("nan") for f in FEATURES]
    significant = benjamini_hochberg(p_values, q=FDR_Q)
    print(f"\nBenjamini-Hochberg FDR (q={FDR_Q}) across {len(FEATURES)} pre-registered features:")
    print("(FDR survival alone is NOT confirmation -- explore/holdout sign agreement is also required, see below)")
    for feature, sig in zip(FEATURES, significant):
        hres = holdout_results[feature]
        eres = explore_results.get(feature)
        if hres is None:
            print(f"  {feature:<18}: skipped in holdout (insufficient data)")
            continue
        hc, hp = hres
        fdr_verdict = "survives FDR" if sig else "does not survive FDR"
        confirmed = False
        if eres is None:
            sign_verdict = "no explore comparison (insufficient explore data)"
            print(f"  {feature:<18}: explore skipped")
        else:
            ec, _ = eres
            same_sign = (ec.rho > 0) == (hc.rho > 0)
            sign_verdict = "SAME sign as explore" if same_sign else "SIGN FLIPPED vs explore"
            confirmed = sig and same_sign
            print(f"  {feature:<18}: explore rho={ec.rho:+.3f} t={ec.t:+.2f}")
        print(f"                      holdout rho={hc.rho:+.3f} t={hc.t:+.2f} p={hp:.4f} -> {fdr_verdict}, {sign_verdict}")
        print(f"                      => {'CONFIRMED' if confirmed else 'NOT confirmed'}")


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())

    print("H10 -- EXPLORE phase (methodology may still change)")
    explore_results = run_phase(universe, prices5y, EXPLORE_YEARS, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_results = run_phase(universe, prices5y, HOLDOUT_YEARS, "HOLDOUT")
        print_holdout_verdicts(explore_results, holdout_results)
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
