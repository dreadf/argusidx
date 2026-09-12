"""
H15: do technical x fundamental factor combinations predict returns on
IDX better than either factor alone?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (see the working plan, 2026-09-12): H14 tested RSI,
200-day-MA position, and momentum standalone and found all three null,
after confirming (via literature search) that standalone technical
indicators on IDX already have dense, contested published research --
testing them again one at a time adds little. The more original,
unaddressed question is whether COMBINING a technical signal with a
fundamental one predicts anything neither predicts alone -- something
retail screeners never test, because they only ever show factors in
isolation.

**Not a composite score.** CLAUDE.md's hard constraint -- "No score or
combined verdict across findings" -- governs anything this project ships;
a weighted/blended signal is exactly the shape it forbids. This is also
the statistically sounder design independent of that rule: a fitted
multi-factor model has many tunable parameters against a holdout of only
~600-1,200 rows -- the same setup that produced H5's size leg, a result
that looked real until it needed to survive out-of-sample. Chosen
instead: a SMALL number of pre-registered, theory-justified interaction
tests (3, not exhaustive), the same low-free-parameter design that
already worked for H1 and H5. If any interaction survives, it becomes
its own finding card with its own limits, same as every other hypothesis
here -- never assembled into a "buy/sell algorithm" or a single number.

Pre-registered interactions (written before running anything):

1. Cheap (earnings_yield = 1/pe[year], top tercile, pe>0 only) x
   oversold (RSI(14) < 30). Why expect one: a temporarily oversold cheap
   stock is a different situation from an oversold expensive one --
   value provides a floor an overbought/expensive stock lacks. Distinct
   from H14's already-tested standalone RSI (null) and H5's already-
   tested standalone value (confirmed) -- this asks whether the
   COMBINATION adds something neither alone captures.
2. Quality (roe[year], top tercile) x uptrend (price above its 200-day
   MA at formation). Why expect one: trend-confirmation logic -- good
   fundamentals the market hasn't yet priced in should show up as
   sustained price strength; good fundamentals with no price
   confirmation could mean the market disagrees for a reason not in
   these two factors.
3. High leverage (debt_to_equity_ratio[year], top tercile) x downtrend
   (price at or below its 200-day MA at formation). Why expect one:
   risk-confirmation -- leverage is dangerous specifically when a company
   is also losing price support.

Falsified (per interaction) if the combination's mean return does not
differ from EITHER single-factor-alone group's mean return (Welch's
t-test, |t| < ~1.96) in the holdout phase, or if it does but the sign
disagrees with the theory above.

Design, reusing existing machinery rather than reimplementing it:
    - Technical side: same `pipeline/stats.py` rsi()/moving_average()
      helpers h14_technical_indicators.py uses, computed on "close" (raw
      price -- a technical signal is about the chart a trader watches,
      same reasoning as H1/H14), evaluated at the SAME formation date the
      fundamental side uses (`nearest_index`, new in stats.py this
      session specifically for this lookup).
    - Fundamental side: same yearly-field-with-formation-lag pattern as
      h5_value_size.py (`pe[year]`, `roe[year]`, `debt_to_equity_ratio[year]`,
      read no earlier than May 1 of year+1, matching H5's ~4-month
      reporting-lag assumption).
    - Return: RETURN_FIELD ("adjclose") from h5_value_size.py, same May
      1 -> Sep 4 window -- one row per (symbol, formation year), NOT
      H14's dense monthly sampling, because the fundamental side only
      changes once a year, so re-sampling the technical side monthly
      around a fixed once-a-year fundamental value would add rows
      without adding independent information (the same pseudo-
      replication concern already solved differently for H5's stress
      test and H14, just resolved here by matching H5's own row
      cardinality instead).
    - Explore/holdout: EXPLORE_YEARS/HOLDOUT_YEARS imported directly from
      h5_value_size.py, so this can never silently drift from H5's own
      boundary. Terciles (for the "top tercile" factors) are computed
      SEPARATELY within each phase's own pooled sample -- explore
      terciles never see holdout rows, or vice versa.

Comparison against H1/H5 (the side-by-side the user asked for): reported
in EXPERIMENT.md as a plain table of already-published effect sizes next
to whatever survives here -- never a new combined statistic.

Multiple comparisons: 3 pre-registered interactions x 2 comparisons each
(combo vs factor-A-alone, combo vs factor-B-alone) = 6 holdout tests.
Explore doesn't count as a separate trial (matching H5's own convention).
No p-value/FDR machinery exists in this project yet (no scipy dependency)
-- reported honestly against the same ~1.96 threshold every other
hypothesis module here uses, with a plain Bonferroni note (alpha/6 implies
roughly t~2.6, not 1.96) stated alongside any result that clears the
weaker but not the stricter bar.

Run:
    .venv/bin/python -m pipeline.hypotheses.h15_technical_fundamental_interactions
    .venv/bin/python -m pipeline.hypotheses.h15_technical_fundamental_interactions --confirm-holdout
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone

from pipeline.hypotheses.h5_value_size import (
    EXPLORE_YEARS,
    HOLDOUT_YEARS,
    PRICES_5Y_PATH,
    RETURN_FIELD,
    UNIVERSE_PATH,
)
from pipeline.stats import median_of, moving_average, nearest_index, nearest_value, quintiles, rsi, welch_ttest

MAX_PRICE_GAP_DAYS = 10
MA_WINDOW = 200
RSI_PERIOD = 14
RSI_OVERSOLD = 30
MIN_GROUP_SIZE = 10


def build_rows_for_year(universe: list[dict], prices5y: dict, year: int) -> list[dict]:
    """One row per (symbol, formation year) -- fundamental fields as of
    `year`, technical signal and return as of the same May-1-of-year+1
    formation date h5_value_size.py uses."""
    formation_dt = datetime(year + 1, 5, 1, tzinfo=timezone.utc)
    outcome_dt = datetime(year + 1, 9, 4, tzinfo=timezone.utc)
    rows = []
    for r in universe:
        sym = r.get("symbol")
        qv = r.get("query_values") or {}
        pe = qv.get(f"pe[{year}]")
        roe = qv.get(f"roe[{year}]")
        der = qv.get(f"debt_to_equity_ratio[{year}]")
        entry = prices5y.get(sym)
        if not entry:
            continue
        closes = entry.get("close")
        timestamps = entry.get("timestamps")
        if not closes or not timestamps or len(closes) != len(timestamps):
            continue
        if any(c <= 0 for c in closes):
            continue
        idx = nearest_index(entry, formation_dt, max_gap_days=MAX_PRICE_GAP_DAYS)
        if idx is None or idx < MA_WINDOW - 1:
            continue
        ma200 = moving_average(closes, MA_WINDOW)
        rsi14 = rsi(closes, RSI_PERIOD)
        if ma200[idx] is None or rsi14[idx] is None:
            continue
        p0 = nearest_value(entry, formation_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        p1 = nearest_value(entry, outcome_dt, field=RETURN_FIELD, max_gap_days=MAX_PRICE_GAP_DAYS)
        if p0 is None or p1 is None:
            continue
        rows.append(
            {
                "sym": sym,
                "year": year,
                "earnings_yield": 1.0 / pe if pe is not None and pe > 0 else None,
                "roe": roe,
                "der": der,
                "rsi": rsi14[idx],
                "ma_ratio": closes[idx] / ma200[idx] - 1,
                "ret": p1 / p0 - 1,
            }
        )
    return rows


def build_pooled_rows(universe: list[dict], prices5y: dict, years: list[int]) -> list[dict]:
    pooled = []
    for y in years:
        pooled.extend(build_rows_for_year(universe, prices5y, y))
    return pooled


def _with_top_tercile_flag(rows: list[dict], field: str, flag_name: str) -> list[dict]:
    """Returns only rows with a non-None `field`, each carrying a new
    boolean `flag_name` for whether it's in the top tercile of `field`
    WITHIN THIS SAMPLE (never mixed across explore/holdout -- callers
    must pass one phase's pooled rows at a time)."""
    usable = [r for r in rows if r.get(field) is not None]
    if len(usable) < 3:
        return [dict(r, **{flag_name: False}) for r in usable]
    # (sym, year) is a natural, guaranteed-unique key -- each row is one
    # (symbol, formation year) pair -- safer than tracking membership by
    # object identity, which would be fragile if this function's rows
    # were ever copied or rebuilt between the bucket split and this check.
    top_keys = {(r["sym"], r["year"]) for r in quintiles(usable, field, n_buckets=3)[-1]}
    return [dict(r, **{flag_name: (r["sym"], r["year"]) in top_keys}) for r in usable]


def _mean_ret(rows: list[dict]) -> float:
    return statistics.mean(r["ret"] for r in rows) if rows else float("nan")


def _print_interaction(
    rows: list[dict], label: str, flag_a: str, name_a: str, flag_b: str, name_b: str
) -> None:
    both = [r for r in rows if r[flag_a] and r[flag_b]]
    a_only = [r for r in rows if r[flag_a] and not r[flag_b]]
    b_only = [r for r in rows if not r[flag_a] and r[flag_b]]
    neither = [r for r in rows if not r[flag_a] and not r[flag_b]]

    print(f"\n{label} -- n={len(rows)}")
    for group_name, group in [
        (f"{name_a} AND {name_b}", both),
        (f"{name_a} only", a_only),
        (f"{name_b} only", b_only),
        ("neither", neither),
    ]:
        if not group:
            print(f"  {group_name:>28}: n=0")
            continue
        print(
            f"  {group_name:>28}: n={len(group):>4}  mean_ret={_mean_ret(group):+.1%}"
            f"  median_ret={median_of(group, 'ret'):+.1%}"
        )

    if len(both) >= MIN_GROUP_SIZE and len(a_only) >= MIN_GROUP_SIZE:
        t1 = welch_ttest([r["ret"] for r in both], [r["ret"] for r in a_only])
        print(f"  [{name_a}+{name_b}] vs [{name_a}-only]: diff={t1.diff:+.1%}  t={t1.t:+.2f}")
    else:
        print(f"  [{name_a}+{name_b}] vs [{name_a}-only]: insufficient data (need n>={MIN_GROUP_SIZE} each)")

    if len(both) >= MIN_GROUP_SIZE and len(b_only) >= MIN_GROUP_SIZE:
        t2 = welch_ttest([r["ret"] for r in both], [r["ret"] for r in b_only])
        print(f"  [{name_a}+{name_b}] vs [{name_b}-only]: diff={t2.diff:+.1%}  t={t2.t:+.2f}")
    else:
        print(f"  [{name_a}+{name_b}] vs [{name_b}-only]: insufficient data (need n>={MIN_GROUP_SIZE} each)")


def test1_cheap_and_oversold(rows: list[dict], phase_label: str) -> None:
    tagged = _with_top_tercile_flag(rows, "earnings_yield", "cheap")
    tagged = [dict(r, oversold=r["rsi"] < RSI_OVERSOLD) for r in tagged]
    _print_interaction(tagged, f"{phase_label} -- Interaction 1: cheap x oversold", "cheap", "cheap", "oversold", "oversold")


def test2_quality_and_uptrend(rows: list[dict], phase_label: str) -> None:
    tagged = _with_top_tercile_flag(rows, "roe", "quality")
    tagged = [dict(r, uptrend=r["ma_ratio"] > 0) for r in tagged]
    _print_interaction(tagged, f"{phase_label} -- Interaction 2: quality x uptrend", "quality", "quality", "uptrend", "uptrend")


def test3_leverage_and_downtrend(rows: list[dict], phase_label: str) -> None:
    tagged = _with_top_tercile_flag(rows, "der", "high_leverage")
    tagged = [dict(r, downtrend=r["ma_ratio"] <= 0) for r in tagged]
    _print_interaction(
        tagged,
        f"{phase_label} -- Interaction 3: high leverage x downtrend",
        "high_leverage",
        "high-leverage",
        "downtrend",
        "downtrend",
    )


def run_phase(universe: list[dict], prices5y: dict, years: list[int], phase_label: str) -> None:
    rows = build_pooled_rows(universe, prices5y, years)
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} pooled (symbol, formation year) rows\n{'=' * 70}")
    test1_cheap_and_oversold(rows, phase_label)
    test2_quality_and_uptrend(rows, phase_label)
    test3_leverage_and_downtrend(rows, phase_label)


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())

    print("H15 -- EXPLORE phase (methodology may still change)")
    run_phase(universe, prices5y, EXPLORE_YEARS, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        run_phase(universe, prices5y, HOLDOUT_YEARS, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 3 interactions x 2 comparisons = 6 holdout\n"
            "tests. No p-value/FDR machinery in this project (no scipy) -- t is\n"
            "reported against the usual ~1.96 threshold, but a result should only be\n"
            "trusted at that bar if it ALSO holds up against a stricter, Bonferroni-\n"
            "style bar of roughly t~2.6 (0.05/6), and only if explore agreed in sign."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
