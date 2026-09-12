"""
H14: do the technical indicators Indonesian retail traders actually use --
RSI, price vs. its 200-day moving average, and trailing momentum -- predict
subsequent returns on IDX?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
pipeline/hypotheses/h5_value_size.py's discipline).

Pre-registered hypotheses (committed before looking at any outcome):
    1. RSI(14) < 30 ("oversold") predicts a bounce (positive forward
       return); RSI(14) > 70 ("overbought") predicts a pullback (negative
       forward return). Tested via the continuous RSI-vs-return
       correlation (any real effect should show up as a monotonic
       relationship, not just at the two extremes) AND the plain base
       rates at the two thresholds, since that's the form retail actually
       uses this indicator in.
    2. Price above its 200-day moving average (an uptrend) predicts
       continuation (trend-following); below predicts further weakness.
       Tested as a continuous "distance above/below the MA" correlation
       plus the simple above/below base rates.
    3. 60-trading-day trailing momentum predicts the next window's return.
       A single correlation sign answers both competing retail beliefs at
       once: positive correlation = momentum/continuation, negative =
       mean-reversion.
    Falsified (for any one indicator) if its correlation is not
    significant and does not survive from explore into holdout in the
    same direction.

Cost: $0. Uses only the owned Yahoo 5-year dev cache -- no Sectors call,
    and (unlike H1/H5) no snapshot field either, so the usual
    predictor-before-outcome risk doesn't apply: every indicator is
    computed strictly from `close` values up to and including the signal
    date, and the forward return is measured strictly after it, by
    construction.

Field choice: uses "close" (raw price), not "adjclose" -- same reasoning
    as H1 (see docs/DATA.md's close-vs-adjclose note): a technical signal
    is about the chart a trader is actually watching, not a
    dividend-adjusted series. H5 is the one hypothesis that needs
    "adjclose", because it measures literal investment return.

Sampling design -- the pseudo-replication problem, designed around BEFORE
    running this rather than found after (the direct lesson of fixing
    h5_stress.py's pooled-years bug this session): computing a signal
    every single trading day would produce thousands of heavily
    overlapping, autocorrelated windows per stock -- far worse than H5's
    one-row-per-year issue, since daily windows overlap almost entirely
    with their neighbors. Fix: sample one signal date per stock roughly
    every SAMPLE_STEP (~20 trading days, ~1 calendar month), with a
    forward-return horizon of the same length, so consecutive sampled
    windows for the same stock are back-to-back rather than overlapping.
    This does not fully solve clustering (samples from the same stock in
    the same regime are still not independent draws -- no claim of full
    independence is made), but it removes the dominant, mechanical source
    of overlap.

Signal-date requirement: a sample point needs MA_WINDOW (200) trading
    days of prior history (the most demanding of the three indicators --
    RSI's 14 and momentum's 60 are both satisfied automatically once 200
    is), plus FORWARD_HORIZON (20) days of subsequent history for the
    return. Symbols with any non-positive close are skipped entirely
    (same fail-loud convention as pipeline/stats.py's own guards -- no
    non-positive price is expected in this cache, but a ratio computed
    silently against one would be wrong, not just imprecise).

Explore/holdout split: by calendar year of the SIGNAL date (not the
    return date), same boundary H5 uses for consistency rather than
    independently re-litigated -- EXPLORE_YEARS = {2021, 2022, 2023},
    HOLDOUT_YEARS = {2024, 2025, 2026}.

Trial counting: 3 indicators, each tested once in explore and once in
    holdout -- adds 3 pre-registered trials to the project total (not 6;
    explore is exploratory by definition and doesn't itself count as a
    separate trial, matching how H5's explore phase is treated).

Presentation note: this module prints both raw correlations (rho/t, for
    EXPERIMENT.md and the trial record) and base rates (for the
    user-facing form) -- "ship the verdict, not the indicator" means the
    APP surfaces only the base-rate framing, not that the methodology
    layer should omit the correlation. Same pattern as every other
    hypothesis module in this repo.

Data (already owned -- no new Sectors or Yahoo call for this module):
    data/dev_cache/prices_5y.json -- Yahoo, dev-only, never ships
    (RULES.md); a Sectors-price cross-check is the same pre-existing
    obligation already tracked for H1 (docs/PLAN.md §8.3).

Run:
    .venv/bin/python -m pipeline.hypotheses.h14_technical_indicators
    .venv/bin/python -m pipeline.hypotheses.h14_technical_indicators --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from pipeline.hypotheses.h5_value_size import PRICES_5Y_PATH
from pipeline.stats import median_of, moving_average, quintiles, rsi, spearman

MA_WINDOW = 200
RSI_PERIOD = 14
MOMENTUM_WINDOW = 60
SAMPLE_STEP = 20  # ~1 trading month; also the forward-return horizon below
FORWARD_HORIZON = 20
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

EXPLORE_YEARS = {2021, 2022, 2023}
HOLDOUT_YEARS = {2024, 2025, 2026}


def build_rows(prices5y: dict) -> list[dict]:
    """One row per (symbol, sampled signal date) -- see the module
    docstring's sampling-design section for why sample points are spaced
    SAMPLE_STEP trading days apart rather than taken daily."""
    rows: list[dict] = []
    for sym, entry in prices5y.items():
        closes = entry.get("close")
        timestamps = entry.get("timestamps")
        if not closes or not timestamps or len(closes) != len(timestamps):
            continue
        if any(c <= 0 for c in closes):
            continue

        ma200 = moving_average(closes, MA_WINDOW)
        rsi14 = rsi(closes, RSI_PERIOD)
        n = len(closes)

        i = MA_WINDOW - 1
        while i + FORWARD_HORIZON < n:
            if ma200[i] is not None and rsi14[i] is not None and i >= MOMENTUM_WINDOW:
                close_i = closes[i]
                year = datetime.fromtimestamp(timestamps[i], timezone.utc).year
                rows.append(
                    {
                        "sym": sym,
                        "year": year,
                        "rsi": rsi14[i],
                        "ma_ratio": close_i / ma200[i] - 1,
                        "momentum": close_i / closes[i - MOMENTUM_WINDOW] - 1,
                        "fwd_ret": closes[i + FORWARD_HORIZON] / close_i - 1,
                    }
                )
            i += SAMPLE_STEP
    return rows


def _base_rate(rows: list[dict]) -> float:
    return sum(1 for r in rows if r["fwd_ret"] > 0) / len(rows)


def print_indicator_tests(rows: list[dict], label: str) -> None:
    print(f"\n{label} -- n={len(rows)}")
    if len(rows) < 10:
        print("  insufficient data, skipped")
        return

    c_rsi = spearman([r["rsi"] for r in rows], [r["fwd_ret"] for r in rows])
    c_ma = spearman([r["ma_ratio"] for r in rows], [r["fwd_ret"] for r in rows])
    c_mom = spearman([r["momentum"] for r in rows], [r["fwd_ret"] for r in rows])
    print(f"  RSI({RSI_PERIOD}) vs next-{FORWARD_HORIZON}-day return: rho={c_rsi.rho:+.3f}  t={c_rsi.t:+.2f}")
    print(f"  price-vs-{MA_WINDOW}d-MA vs next-{FORWARD_HORIZON}-day return: rho={c_ma.rho:+.3f}  t={c_ma.t:+.2f}")
    print(
        f"  {MOMENTUM_WINDOW}-day momentum vs next-{FORWARD_HORIZON}-day return: "
        f"rho={c_mom.rho:+.3f}  t={c_mom.t:+.2f}"
    )

    baseline = _base_rate(rows)
    print(f"\n  Baseline: {baseline:.1%} of all sample points were up over the next {FORWARD_HORIZON} trading days")

    oversold = [r for r in rows if r["rsi"] < RSI_OVERSOLD]
    overbought = [r for r in rows if r["rsi"] > RSI_OVERBOUGHT]
    if oversold:
        print(
            f"  RSI<{RSI_OVERSOLD} ('oversold', n={len(oversold)}): "
            f"{_base_rate(oversold):.1%} up next {FORWARD_HORIZON} days (bounce belief predicts HIGHER than baseline)"
        )
    else:
        print(f"  RSI<{RSI_OVERSOLD}: no sample points")
    if overbought:
        print(
            f"  RSI>{RSI_OVERBOUGHT} ('overbought', n={len(overbought)}): "
            f"{_base_rate(overbought):.1%} up next {FORWARD_HORIZON} days "
            "(pullback belief predicts LOWER than baseline)"
        )
    else:
        print(f"  RSI>{RSI_OVERBOUGHT}: no sample points")

    above_ma = [r for r in rows if r["ma_ratio"] > 0]
    below_ma = [r for r in rows if r["ma_ratio"] <= 0]
    if above_ma:
        print(
            f"  Price above {MA_WINDOW}d MA (n={len(above_ma)}): "
            f"{_base_rate(above_ma):.1%} up next {FORWARD_HORIZON} days (trend-following belief predicts HIGHER)"
        )
    if below_ma:
        print(f"  Price below {MA_WINDOW}d MA (n={len(below_ma)}): {_base_rate(below_ma):.1%} up next {FORWARD_HORIZON} days")

    print(f"\n  Momentum quintiles (Q1=worst trailing {MOMENTUM_WINDOW}d return, Q5=best):")
    for idx, bucket in enumerate(quintiles(rows, "momentum"), start=1):
        print(
            f"    Q{idx}: n={len(bucket):>4}  momentum_median={median_of(bucket, 'momentum'):+.1%}"
            f"  fwd_ret_median={median_of(bucket, 'fwd_ret'):+.1%}"
        )


def main() -> None:
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    rows = build_rows(prices5y)
    n_symbols = len({r["sym"] for r in rows})
    print(
        f"H14 -- technical indicators on IDX: {len(rows)} sample points across {n_symbols} symbols "
        f"(one per ~{SAMPLE_STEP} trading days, {FORWARD_HORIZON}-trading-day non-overlapping forward return)"
    )

    explore_rows = [r for r in rows if r["year"] in EXPLORE_YEARS]
    holdout_rows = [r for r in rows if r["year"] in HOLDOUT_YEARS]

    print("\nH14 -- EXPLORE phase (methodology may still change)")
    print_indicator_tests(explore_rows, "EXPLORE (2021-2023 signal dates)")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        print_indicator_tests(holdout_rows, "HOLDOUT (2024-2026 signal dates)")
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
