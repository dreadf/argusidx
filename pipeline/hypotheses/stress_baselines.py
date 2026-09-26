"""
Stress test ST3 -- ordinary rates next to the situations I9, I2, I3 and I6,
pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-27 -- stress tests
of the newest hypotheses and situations"), run once. Not a new trial; no
verdict changes; owned data only, no API call.

A statement like "55 of 100 cut the dividend" means little without the
ordinary rate. Each comparison prints the situation rate, the baseline rate,
both with Wilson 95% intervals, and the difference in points with a Newcombe
interval (Wilson-based; the situation is a subset of the baseline group, so the
interval treats them as independent and is conservative).

Rule (pre-registered): if the interval of the difference includes 0, the app
copy must not imply the situation raises or lowers the ordinary rate.

Reproduction first: I9 26 of 47, I2 50 of 82 (explore) and 70 of 88 (holdout),
I3 68 stock-years (41, 13, 14) with negative 25 and beating the median 26, and
the I6 N=1 cells are recomputed and printed next to the frozen values. A
mismatch stops the affected comparison.

(a) Cut rate among ALL dividend payers of the same year Y. A payer in Y is a
    stock with `total_dividend[Y] > 0`; a cut is `total_dividend[Y+1] <
    total_dividend[Y]`. Two conventions, each matched to its situation: I9 counts
    a missing `total_dividend[Y+1]` as a cut (its main definition), I2 (H4's rows)
    leaves stock-years with a missing next-year dividend out. Baselines: Y = 2024
    (next to I9, and to I2's holdout years), the I2 phase years (explore 2021 and
    2022; holdout 2023 and 2024), and pooled 2022 to 2024 (next to each).
(b) I3: for every stock with a valid 1 May to 4 Sep return that year (the
    "median stock" population of `m_near_peak_earnings_decline`), the share with
    a negative return and the share beating that year's median (strictly), per
    year and pooled, next to the flagged stock-years.
(c) I6: the share of all payers in Y that paid again in Y+1 (the streak N = 1
    cell), per Y, next to the N = 2, 3, 4 cells.

Run:
    .venv/bin/python -m pipeline.hypotheses.stress_baselines
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from pipeline.hypotheses._stress_common import check_frozen, fmt_pct, newcombe_diff, rate
from pipeline.hypotheses.h4_payout_dividend_cuts import EXPLORE_YEARS, HOLDOUT_YEARS
from pipeline.hypotheses.h4_payout_dividend_cuts import UNIVERSE_PATH as H4_UNIVERSE_PATH
from pipeline.hypotheses.m_dividend_streaks import END_YEARS, STREAK_LENGTHS, streak_cell
from pipeline.hypotheses.m_near_peak_earnings_decline import (
    YEARS as I3_YEARS,
    earnings_declined,
    near_peak_on,
    window_return,
)
from pipeline.hypotheses.m_payout_flag_check import cut_rate_above_100
from pipeline.hypotheses.m_yield_spike_cut import build_yield_spike_cut

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

FROZEN_I9 = (26, 47)
FROZEN_I2 = {"explore": (50, 82), "holdout": (70, 88)}
FROZEN_I3 = {"n": {2022: 41, 2023: 13, 2024: 14}, "neg": {2022: 17, 2023: 4, 2024: 4}, "beat": {2022: 12, 2023: 7, 2024: 7}}
FROZEN_I6_N1 = {2022: (249, 283), 2023: (285, 322), 2024: (296, 341)}
FROZEN_I6_N4_2024 = (170, 177)
UNIVERSE_SIZE_CHECK = {2022: 806, 2023: 870, 2024: 887}


def _div(qv: dict, year: int) -> float | None:
    return qv.get(f"total_dividend[{year}]")


def payer_cut_rate(universe: list[dict], years: list[int], missing_as_cut: bool) -> dict:
    """Cut rate among all payers of each year in `years`, stock-years pooled.

    missing_as_cut=True: a missing next-year dividend counts as a cut (I9's convention);
    False: such stock-years are left out (H4's, hence I2's).
    """
    cuts = n = 0
    for y in years:
        for r in universe:
            qv = r.get("query_values") or {}
            d0 = _div(qv, y)
            if d0 is None or d0 <= 0:
                continue
            d1 = _div(qv, y + 1)
            if d1 is None:
                if not missing_as_cut:
                    continue
                cuts += 1
            else:
                cuts += d1 < d0
            n += 1
    return rate(cuts, n)


def compare(label: str, situation: dict, baseline_label: str, baseline: dict) -> dict:
    d = newcombe_diff(situation["count"], situation["n"], baseline["count"], baseline["n"])
    if d is None:
        print(f"  {label}: not computable")
        return {"label": label, "not_computable": True}
    print(
        f"  {label}: {situation['count']}/{situation['n']} {fmt_pct(situation['rate'])} "
        f"[{fmt_pct(situation['wilson_low'])}-{fmt_pct(situation['wilson_high'])}]  vs {baseline_label}: "
        f"{baseline['count']}/{baseline['n']} {fmt_pct(baseline['rate'])} [{fmt_pct(baseline['wilson_low'])}-{fmt_pct(baseline['wilson_high'])}]  "
        f"diff {d['diff'] * 100:+.1f} points [{d['low'] * 100:+.1f}, {d['high'] * 100:+.1f}] "
        f"-> {'INCLUDES 0 (copy must not imply raise/lower)' if d['includes_zero'] else 'excludes 0'}"
    )
    return {"label": label, "situation": situation, "baseline_label": baseline_label, "baseline": baseline, "difference": d}


# ------------------------------------------------------------------ (a)
def run_dividend_baselines(universe: list[dict], h4_universe: list[dict]) -> dict:
    print("(a) cut rate among all dividend payers of the same year")
    i9 = build_yield_spike_cut(universe)[2024]["cut_missing_counted_as_cut"]
    h4_ex = cut_rate_above_100(h4_universe, EXPLORE_YEARS)
    h4_ho = cut_rate_above_100(h4_universe, HOLDOUT_YEARS)
    print("Reproduction:")
    ok = check_frozen("I9 cuts/n (Y=2024)", (i9["count"], i9["n"]), FROZEN_I9)
    ok &= check_frozen("I2 explore cuts/n", (h4_ex["cuts"], h4_ex["n"]), FROZEN_I2["explore"])
    ok &= check_frozen("I2 holdout cuts/n", (h4_ho["cuts"], h4_ho["n"]), FROZEN_I2["holdout"])
    if not ok:
        print("STOP: frozen I9 / I2 figures not reproduced; ST3 (a) not computed.")
        return {"reproduced": False}
    s_i9 = rate(i9["count"], i9["n"])
    s_ex = rate(h4_ex["cuts"], h4_ex["n"])
    s_ho = rate(h4_ho["cuts"], h4_ho["n"])
    out: dict = {"reproduced": True, "comparisons": []}
    for conv_label, conv in (("missing counted as a cut", True), ("missing left out", False)):
        print(f"\n  -- convention: {conv_label} --")
        base_2024 = payer_cut_rate(universe, [2024], conv)
        base_ex = payer_cut_rate(universe, EXPLORE_YEARS, conv)
        base_ho = payer_cut_rate(universe, HOLDOUT_YEARS, conv)
        base_pool = payer_cut_rate(universe, [2022, 2023, 2024], conv)
        # I9 has no missing next-year dividend among its 47, so its figure is the same under both
        # conventions. I2 (H4's rows) leaves missing out, so it is only compared like for like.
        rows = [
            compare(f"I9 Y=2024 [{conv_label}]", s_i9, "all payers Y=2024", base_2024),
            compare(f"I9 Y=2024 [{conv_label}]", s_i9, "all payers pooled 2022-2024", base_pool),
        ]
        if not conv:
            rows += [
                compare(f"I2 explore [{conv_label}]", s_ex, "all payers 2021+2022", base_ex),
                compare(f"I2 explore [{conv_label}]", s_ex, "all payers pooled 2022-2024", base_pool),
                compare(f"I2 holdout [{conv_label}]", s_ho, "all payers 2023+2024", base_ho),
                compare(f"I2 holdout [{conv_label}]", s_ho, "all payers pooled 2022-2024", base_pool),
            ]
        out["comparisons"].extend({"convention": conv_label, **r} for r in rows)
    return out


# ------------------------------------------------------------------ (b)
def i3_year(universe: list[dict], prices: dict, year: int) -> dict:
    """Per-stock 1 May to 4 Sep returns for the year, the median stock, and the flagged (near peak, earnings down) returns."""
    start = datetime(year + 1, 5, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 9, 4, tzinfo=timezone.utc)
    cutoff = datetime(year + 1, 5, 1, 23, 59, 59, tzinfo=timezone.utc)
    qv_by = {r.get("symbol"): r.get("query_values") or {} for r in universe}
    returns = {}
    for sym, entry in prices.items():
        r = window_return(entry, start, end)
        if r is not None:
            returns[sym] = r
    median = statistics.median(returns.values())
    flagged = [
        ret
        for sym, ret in returns.items()
        if sym in qv_by and earnings_declined(qv_by[sym], year) and near_peak_on(prices[sym], cutoff)
    ]
    return {"year": year, "returns": list(returns.values()), "median": median, "flagged": flagged}


def run_i3_baseline(universe: list[dict], prices: dict) -> dict:
    print("\n(b) I3: all evaluable stock-years vs the flagged ones (1 May to 4 Sep)")
    years = [i3_year(universe, prices, y) for y in I3_YEARS]
    print("Reproduction:")
    ok = True
    for y in years:
        m = y["median"]
        ok &= check_frozen(f"I3 {y['year']} flagged n", len(y["flagged"]), FROZEN_I3["n"][y["year"]])
        ok &= check_frozen(f"I3 {y['year']} flagged negative", sum(r < 0 for r in y["flagged"]), FROZEN_I3["neg"][y["year"]])
        ok &= check_frozen(f"I3 {y['year']} flagged beat median", sum(r > m for r in y["flagged"]), FROZEN_I3["beat"][y["year"]])
        ok &= check_frozen(f"I3 {y['year']} stocks with a return", len(y["returns"]), UNIVERSE_SIZE_CHECK[y["year"]])
    if not ok:
        print("STOP: frozen I3 figures not reproduced; ST3 (b) not computed.")
        return {"reproduced": False}
    out: dict = {"reproduced": True, "comparisons": []}
    cells = [(str(y["year"]), [y]) for y in years] + [("pooled", years)]
    for label, ys in cells:
        n_f = sum(len(y["flagged"]) for y in ys)
        neg_f = sum(r < 0 for y in ys for r in y["flagged"])
        beat_f = sum(r > y["median"] for y in ys for r in y["flagged"])
        n_a = sum(len(y["returns"]) for y in ys)
        neg_a = sum(r < 0 for y in ys for r in y["returns"])
        beat_a = sum(r > y["median"] for y in ys for r in y["returns"])
        out["comparisons"].append(compare(f"I3 {label} negative return", rate(neg_f, n_f), "all evaluable stock-years", rate(neg_a, n_a)))
        out["comparisons"].append(compare(f"I3 {label} beat the median stock", rate(beat_f, n_f), "all evaluable stock-years", rate(beat_a, n_a)))
    return out


# ------------------------------------------------------------------ (c)
def run_i6_baseline(universe: list[dict]) -> dict:
    print("\n(c) I6: share of all payers that paid again, per year, next to the streak cells")
    cells = {(n, y): streak_cell(universe, n, y) for n in STREAK_LENGTHS for y in END_YEARS}
    print("Reproduction (N=1 is every payer):")
    ok = True
    for y in END_YEARS:
        a = cells[(1, y)]["paid_again"]
        ok &= check_frozen(f"I6 N=1 Y={y} paid again/n", (a["count"], a["n"]), FROZEN_I6_N1[y])
    a = cells[(4, 2024)]["paid_again"]
    ok &= check_frozen("I6 N=4 Y=2024 paid again/n", (a["count"], a["n"]), FROZEN_I6_N4_2024)
    if not ok:
        print("STOP: frozen I6 figures not reproduced; ST3 (c) not computed.")
        return {"reproduced": False}
    out: dict = {"reproduced": True, "comparisons": []}
    for y in END_YEARS:
        base = rate(cells[(1, y)]["paid_again"]["count"], cells[(1, y)]["paid_again"]["n"])
        for n in STREAK_LENGTHS[1:]:
            cell = cells[(n, y)]
            if cell is None:
                print(f"  I6 N={n} Y={y}: not computable (streak would start before 2021)")
                continue
            c = cell["paid_again"]
            out["comparisons"].append(compare(f"I6 N={n} Y={y}", rate(c["count"], c["n"]), f"all payers Y={y} (N=1)", base))
    return out


def run_st3(universe: list[dict], h4_universe: list[dict], prices: dict) -> dict:
    print("=" * 78)
    print("ST3 -- baselines for I9, I2, I3, I6")
    print("=" * 78)
    res = {"a": run_dividend_baselines(universe, h4_universe), "b": run_i3_baseline(universe, prices), "c": run_i6_baseline(universe)}
    comps = [c for part in res.values() for c in part.get("comparisons", []) if "difference" in c]
    with_zero = [c for c in comps if c["difference"]["includes_zero"]]
    print(f"\nComparisons made: {len(comps)}; interval of the difference includes 0 in {len(with_zero)}")
    for c in with_zero:
        d = c["difference"]
        print(f"  includes 0: {c['label']} vs {c['baseline_label']}: {d['diff'] * 100:+.1f} [{d['low'] * 100:+.1f}, {d['high'] * 100:+.1f}]")
    res["n_comparisons"] = len(comps)
    return res


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    h4_universe = json.loads(H4_UNIVERSE_PATH.read_text())
    prices = json.loads(PRICES_5Y_PATH.read_text())
    run_st3(universe, h4_universe, prices)


if __name__ == "__main__":
    main()
