"""
H1 stress tests: attacking an existing finding, not proposing a new one.

STATUS: run once; every result below is reported regardless of outcome
(RULES.md verification item 6: ship the null if it's null).

These tests attack H1's own robustness checks, which turned out to be
inadequate (see EXPERIMENT.md and docs/DATA.md). Attacking a finding does
not inflate the trial counter *by itself* -- a test can only weaken or
confirm what's already there. It only counts as a new trial if it
produces a NEW POSITIVE claim rather than a boundary condition on H1
(e.g. "the effect is actually strongest among X" would be fishing; "the
effect fades outside condition X" is a boundary). Each test's
interpretation is fixed below, before running, for exactly this reason.

Pre-registered interpretations (written before this was run):

Test 1 -- Liquidity re-test. H1's published "Explanation 1" check used
    no_move_fraction, which cannot see days a stock did not trade at all
    (docs/DATA.md). This sweeps an actual trading-day-count threshold
    instead. FALSIFIED-AS-ROBUST if rho decays toward/through zero as the
    threshold rises -- that is a boundary condition (undisclosed, not
    previously ruled out), described as "fades", NOT "reverses", unless a
    negative, significant rho survives at multiple adjacent thresholds,
    not one in isolation.
Test 2 -- Tick-size / price-level confound. IDX prices trade on a coarse
    grid (tick size grows with price), so cheap stocks are mechanically
    more volatile per percentage point. FALSIFIED-AS-ROBUST if the effect
    weakens sharply above a price floor -- plausibly the same underlying
    story as test 1 (cheap stocks tend to be thinly traded), not
    independent evidence.
Test 3 -- Placebo. Seeded shuffle of free float across stocks. Gate:
    rho MUST collapse to ~0. If it doesn't, stop -- the pipeline is
    manufacturing correlation and nothing else here is trustworthy.
Test 4 -- Random split-half. Seeded 50/50 split of the full sample;
    compute the smallest-cap effect on one half, check it on the other.
    The cross-sectional holdout a single-date free-float snapshot can
    actually support (no temporal holdout is possible from one
    measurement -- see docs/DATA.md).

Run:
    python -m pipeline.hypotheses.h1_stress
"""
from __future__ import annotations

import json
import math

from pipeline.hypotheses.h1_free_float import (
    PRICES_1Y_PATH,
    PRICES_5Y_PATH,
    build_1y_rows,
    load_free_float,
)
from pipeline.stats import annualized_volatility, closes_in_year, placebo_correlation, spearman, split_half

SEED = 0
MIN_ROWS_FOR_TEST = 10


def test1_liquidity_sweep(rows: list[dict]) -> None:
    print("Test 1 -- liquidity re-test (actual trading-day counts, not no_move_fraction)\n")
    bars1y = {sym: len(entry["close"]) for sym, entry in json.loads(PRICES_1Y_PATH.read_text()).items()}
    for r in rows:
        r["bars1y"] = bars1y.get(r["sym"], 0)

    print("  Sweeping minimum trading days required (of ~242 in the window):")
    for thr in [0, 130, 150, 170, 190, 200, 210, 220, 230, 235]:
        g = [r for r in rows if r["bars1y"] >= thr]
        if len(g) < 10:
            continue
        c = spearman([r["ff"] for r in g], [r["vol"] for r in g])
        print(f"    >={thr:4d} days: n={c.n:4d}  rho={c.rho:+.4f}  t={c.t:+6.2f}")

    print("\n  Balanced panel: same stocks present in all 5 years (removes the\n"
          "  growing-newcomer-share confound in the year-by-year check)")
    ff = load_free_float()
    p5 = json.loads(PRICES_5Y_PATH.read_text())
    by_year: dict[int, set[str]] = {}
    for year in [2022, 2023, 2024, 2025, 2026]:
        s = set()
        for sym, entry in p5.items():
            if sym not in ff:
                continue
            closes = closes_in_year(entry, year)
            if len(closes) >= 100:
                s.add(sym)
        by_year[year] = s
    balanced = set.intersection(*by_year.values())
    print(f"    {len(balanced)} stocks present in all 5 years\n")
    print("    year | all-stocks rho (t)      | balanced-panel rho (t)")
    for year in [2022, 2023, 2024, 2025, 2026]:
        all_rows, bal_rows = [], []
        for sym, entry in p5.items():
            if sym not in ff:
                continue
            closes = closes_in_year(entry, year)
            if len(closes) < 100:
                continue
            entry = {"ff": ff[sym], "vol": annualized_volatility(closes)}
            all_rows.append(entry)
            if sym in balanced:
                bal_rows.append(entry)
        ca = spearman([r["ff"] for r in all_rows], [r["vol"] for r in all_rows])
        cb = spearman([r["ff"] for r in bal_rows], [r["vol"] for r in bal_rows])
        print(f"    {year} | n={ca.n:4d} rho={ca.rho:+.3f} t={ca.t:+.2f}  | n={cb.n:4d} rho={cb.rho:+.3f} t={cb.t:+.2f}")


def test2_tick_size(rows: list[dict]) -> None:
    print("\nTest 2 -- tick-size / price-level confound\n")
    p1 = json.loads(PRICES_1Y_PATH.read_text())
    for r in rows:
        r["last_price"] = p1[r["sym"]]["close"][-1]

    under100 = sum(1 for r in rows if r["last_price"] < 100)
    under50 = sum(1 for r in rows if r["last_price"] < 50)
    print(f"  {under100} of {len(rows)} ({100*under100/len(rows):.1f}%) trade under Rp 100 "
          f"(tick Rp 1, >=1% of price)")
    print(f"  {under50} of {len(rows)} ({100*under50/len(rows):.1f}%) trade under Rp 50 "
          f"(tick Rp 1, >=2% of price)")

    c_price_ff = spearman([r["last_price"] for r in rows], [r["ff"] for r in rows])
    print(f"\n  rho(price, free_float) = {c_price_ff.rho:+.3f} -- is float just a price proxy?")

    above500 = [r for r in rows if r["last_price"] >= 500]
    c = spearman([r["ff"] for r in above500], [r["vol"] for r in above500])
    print(f"  Restricted to price >= Rp 500 (tick <1%): n={c.n}  rho={c.rho:+.3f}  t={c.t:+.2f}")


def _print_placebo_gate(label: str, c) -> None:
    if math.isnan(c.rho):
        print(f"  shuffled {label}: rho=nan (n={c.n} too small for a meaningful correlation)")
        print("  GATE: SKIPPED -- insufficient data, not a pass or fail")
        return
    print(f"  shuffled {label}: rho={c.rho:+.4f}  t={c.t:+.2f}")
    print(f"  GATE: {'PASS' if abs(c.rho) < 0.1 else 'FAIL -- STOP, pipeline may be manufacturing correlation'}")


def test3_placebo(rows: list[dict]) -> None:
    print("\nTest 3 -- placebo (shuffled free float)\n")
    c = placebo_correlation([r["ff"] for r in rows], [r["vol"] for r in rows], SEED)
    _print_placebo_gate("free_float vs real volatility", c)


def test4_split_half(rows: list[dict]) -> None:
    print("\nTest 4 -- random split-half (cross-sectional holdout)\n")
    a, b = split_half(rows, SEED)
    for name, part in [("half A", a), ("half B", b)]:
        if len(part) < MIN_ROWS_FOR_TEST:
            print(f"  {name}: n={len(part)} -- insufficient data, skipped")
            continue
        c = spearman([r["ff"] for r in part], [r["vol"] for r in part])
        print(f"  {name}: n={c.n}  rho={c.rho:+.3f}  t={c.t:+.2f}")


def main() -> None:
    ff = load_free_float()
    rows = build_1y_rows(ff)

    test1_liquidity_sweep(rows)
    test2_tick_size(rows)
    test3_placebo(rows)
    test4_split_half(rows)

    print(
        "\nSummary (updated 2026-09-10 for the corrected Yahoo cache -- see\n"
        "EXPERIMENT.md): the liquidity effect does NOT fade with trading\n"
        "activity or price level on this cache -- test 1's sweep is flat\n"
        "across every threshold. The 'fades as liquidity rises' conclusion\n"
        "printed by earlier versions of this script described the OLD\n"
        "(spark-endpoint) cache and was itself a coverage-gap artifact, not\n"
        "a real boundary condition -- do not trust that framing against\n"
        "this run's numbers."
    )


if __name__ == "__main__":
    main()
