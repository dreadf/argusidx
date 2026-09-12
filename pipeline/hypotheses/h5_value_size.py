"""
H5: do value (cheap earnings multiple) and size (small market cap) predict
subsequent returns on IDX?

STATUS: explore phase only until --confirm-holdout is passed (see below).

Pre-registered hypothesis (committed before looking at any outcome):
    Stocks with a LOWER pe[year] (cheaper, i.e. HIGHER earnings yield) and/or
    a SMALLER computed market cap at formation earn HIGHER subsequent returns
    than expensive/large stocks over the same window -- the value and size
    premia, well documented in developed markets, untested here on IDX.
    Falsified if: no monotonic relationship across quintiles in the holdout
    window, or if the relationship reverses.

Holdout discipline (approved 2026-09-07 -- see BACKLOG.md, PLAN.md §11):
    pe[2021] is entirely absent from the purchased universe -- 0 of 962
    companies, including BBCA [verified: read data/raw/universe_2026-09-07.json
    directly, not assumed from the field list]. That leaves 4 usable
    formation years: 2022, 2023, 2024, 2025.

    Because the newest usable outcome window (formed on 2025 data) is
    necessarily a partial year -- today is 2026-09-07, so 2026 is not
    complete -- EVERY window in this module, explore and holdout alike, uses
    the identical May-1-to-Sep-4 range of the following year. The methodology
    tested in exploration is exactly what runs in holdout, not a longer or
    cleaner version of it.

    Formation date is May 1 of the following year, not Jan 1, to avoid a
    look-ahead bias that would otherwise undercut this project's own
    predictor-before-outcome rule: fiscal-year figures are not public the
    instant the year ends. [Assumed: ~4-month reporting lag before annual
    figures are public; not verified this session against IDX's actual
    disclosure deadline -- if wrong, it is conservative in the safe
    direction (later, not earlier), so it does not manufacture a false
    positive.] This does shrink the outcome window to ~4 months for every
    pair, which is a real limitation on power, not hidden here.

    EXPLORE (methodology may still change): formation 2022, 2023
        -> partial-year return, May-Sep of 2023, 2024
    HOLDOUT (frozen methodology, run once, reported regardless of outcome):
        formation 2024, 2025 -> partial-year return, May-Sep of 2025, 2026

    Once --confirm-holdout has been run and its result recorded in
    EXPERIMENT.md, it must not be re-run against a changed methodology to
    fish for a better number -- that would be exactly the p-hacking this
    discipline exists to prevent. A second holdout run belongs in the trial
    counter as a new trial, not a silent do-over.

    EXCEPTION, exercised 2026-09-10: the Yahoo price cache itself was
    corrected (endpoint switched from spark to chart -- see
    pipeline/dev/fetch_yahoo_prices.py) for a documented coverage-gap bug
    that predates and is unrelated to this hypothesis's own methodology.
    The hypothesis, value/size proxies, formation lag, and year split are
    all UNCHANGED; only the underlying price series (completeness +
    dividend-adjustment) is corrected. Per this project's own precedent for
    exactly this situation (pipeline/stats.py's tied-rank fix was
    republished with the delta disclosed, not counted as a new trial), this
    re-run is treated as a data correction, not a new trial -- flagged
    explicitly here, and in EXPERIMENT.md with the old numbers struck
    through, so it can't be mistaken for a silent do-over.

Value proxy: earnings_yield = 1/pe[year], restricted to pe > 0. [Assumed:
    negative pe (loss-making companies) is not a meaningful "cheapness"
    signal in the standard value-factor sense, so those rows are excluded
    from the value ranking entirely -- this reduces n and is a real
    limitation, not a neutral filter.]

Size proxy: outstanding_shares[year] * RAW close price nearest the
    formation date. Sectors has no yearly market_cap field (see
    docs/DATA.md's snapshot/yearly mapping), so this is computed from data
    already purchased. Deliberately uses "close", not "adjclose" -- see
    the comment in build_rows_for_year for why using the dividend-adjusted
    price here would distort the size proxy.

Return: computed from "adjclose" (dividend-and-split-adjusted), not
    "close" -- added 2026-09-10 alongside the endpoint fix. This directly
    addresses the dividend-exclusion limitation named in EXPERIMENT.md's
    original H5 entry (cheaper/higher-yield stocks were being measured on
    price return only, understating the value leg).

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/universe_2026-09-07.json -- pe[YYYY], outstanding_shares[YYYY]
    data/dev_cache/prices_5y.json -- Yahoo, dev-only. Corrected 2026-09-10
        (see docs/DATA.md): {timestamps, close, adjclose} per symbol.
        Never ships (RULES.md); a Sectors-price cross-check is the same
        pre-existing obligation already tracked for H1 (docs/PLAN.md §8.3).

Run:
    python -m pipeline.hypotheses.h5_value_size                 # explore only
    python -m pipeline.hypotheses.h5_value_size --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline.stats import median_of, nearest_value, quintiles, spearman

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-07.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

EXPLORE_YEARS = [2022, 2023]
HOLDOUT_YEARS = [2024, 2025]
MAX_PRICE_GAP_DAYS = 10
RETURN_FIELD = "adjclose"  # dividend-and-split-adjusted -- H5 measures total
# investment return, which dividends are part of by definition. H1 keeps
# "close" (raw price) deliberately -- see docs/DATA.md's close-vs-adjclose
# note; this split is intentional, not an inconsistency between modules.


def build_rows_for_year(
    universe: list[dict], prices5y: dict, year: int, midpoint: datetime | None = None
) -> list[dict]:
    """Formation on `year`'s pe/shares; outcome return May 1 -> Sep 4 of year+1.

    `midpoint`, if given, additionally splits that same window's return at
    one intermediate date -- adds `ret_pre`/`ret_post` to each row (nearest
    price at `midpoint`, same `nearest_value`/`RETURN_FIELD` machinery as
    the full-window return). Used by
    pipeline/hypotheses/h5_timing_diagnostic.py's rate-cut-timing check;
    left as None (the default) for every other caller, which is unaffected.
    Added so that diagnostic reuses this function instead of duplicating
    the pe/shares filtering and p0_raw/p0/p1 lookups in its own copy
    (found by /code-review, 2026-09-12) -- matches how h5_stress.py already
    reuses this function rather than reimplementing it.
    """
    formation_dt = datetime(year + 1, 5, 1, tzinfo=timezone.utc)
    outcome_dt = datetime(year + 1, 9, 4, tzinfo=timezone.utc)
    rows = []
    for r in universe:
        sym = r.get("symbol")
        qv = r.get("query_values") or {}
        pe = qv.get(f"pe[{year}]")
        shares = qv.get(f"outstanding_shares[{year}]")
        if pe is None or pe <= 0 or shares is None or shares <= 0:
            continue
        entry = prices5y.get(sym)
        if not entry:
            continue
        # Size (market-cap proxy) must use the RAW price at formation, not
        # adjclose. [Verified 2026-09-10: adjclose retroactively lowers
        # historical prices for dividends/splits that happen AFTER the
        # date being looked up -- checked directly against the cache
        # (e.g. BBCA.JK's close/adjclose gap is 14.65% on the oldest
        # cached date, shrinking to 0% on the most recent one).] Using it
        # here would shrink "size" specifically for stocks that later pay
        # more dividends -- systematically correlated with the value leg
        # this hypothesis tests. Only the return ratio needs the
        # dividend-adjusted series.
        p0_raw = nearest_value(entry, formation_dt, field="close", max_gap_days=MAX_PRICE_GAP_DAYS)
        p0 = nearest_value(entry, formation_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        p1 = nearest_value(entry, outcome_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        if p0_raw is None or p0 is None or p1 is None:
            continue
        row = {
            "sym": sym,
            "year": year,
            "earnings_yield": 1.0 / pe,
            "size": shares * p0_raw,
            "ret": p1 / p0 - 1,
        }
        if midpoint is not None:
            p_mid = nearest_value(entry, midpoint, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
            if p_mid is None:
                continue
            row["ret_pre"] = p_mid / p0 - 1
            row["ret_post"] = p1 / p_mid - 1
        rows.append(row)
    return rows


def print_factor_test(rows: list[dict], label: str) -> None:
    print(f"\n{label} -- n={len(rows)}")
    if len(rows) < 10:
        print("  insufficient data, skipped")
        return

    c_val = spearman([r["earnings_yield"] for r in rows], [r["ret"] for r in rows])
    c_size = spearman([r["size"] for r in rows], [r["ret"] for r in rows])
    c_confound = spearman([r["earnings_yield"] for r in rows], [r["size"] for r in rows])
    print(f"  earnings_yield vs return: rho={c_val.rho:+.3f}  t={c_val.t:+.2f}")
    print(f"  size (shares*price) vs return: rho={c_size.rho:+.3f}  t={c_size.t:+.2f}")
    print(f"  earnings_yield vs size (confound check): rho={c_confound.rho:+.3f}  t={c_confound.t:+.2f}")

    print("  Value quintiles (Q1=most expensive/lowest yield, Q5=cheapest/highest yield):")
    for i, bucket in enumerate(quintiles(rows, "earnings_yield"), start=1):
        print(
            f"    Q{i}: n={len(bucket):>4}  ey_median={median_of(bucket,'earnings_yield'):.4f}"
            f"  ret_median={median_of(bucket,'ret'):+.1%}"
        )

    print("  Size quintiles (Q1=smallest, Q5=largest):")
    for i, bucket in enumerate(quintiles(rows, "size"), start=1):
        print(
            f"    Q{i}: n={len(bucket):>4}  size_median={median_of(bucket,'size'):,.0f}"
            f"  ret_median={median_of(bucket,'ret'):+.1%}"
        )


def run_phase(universe: list[dict], prices5y: dict, years: list[int], phase_label: str) -> None:
    pooled: list[dict] = []
    for y in years:
        rows = build_rows_for_year(universe, prices5y, y)
        print_factor_test(rows, f"{phase_label}: formation {y} -> return May-Sep {y + 1}")
        pooled.extend(rows)
    print_factor_test(pooled, f"{phase_label}: pooled ({'+'.join(str(y) for y in years)})")


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())

    print("H5 -- EXPLORE phase (methodology may still change)")
    run_phase(universe, prices5y, EXPLORE_YEARS, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        run_phase(universe, prices5y, HOLDOUT_YEARS, "HOLDOUT")
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
