"""
Stress test ST5 -- H6 ("Asing borong -> harga naik"), pre-registered in
EXPERIMENT.md ("Pre-registration, 2026-09-27 -- stress tests of the newest
hypotheses and situations"), run once. NOT a new trial: H6 stays NOT confirmed
unless the PRE-REGISTERED PRIMARY result is significant (holdout spread > 0 with
p < 0.05 and the explore spread the same sign, `h6_foreign_list.verdict`).
Variants are sensitivity, never a second chance; a significant variant is
reported as "significant only under a variant not pre-registered". Owned data
only (the purchased foreign-flow lists and the Yahoo research cache), no API call.

Reproduction first: the primary spreads are recomputed with this module's
generalised code and printed next to the frozen values (explore +0.05% over 26
dates, holdout -0.03% over 35 dates). A mismatch stops the module.

The statistic is H6's: per date the mean winsorised excess return of the buy list
minus the sell list, a one-sample exact-t test across dates per phase. Every
variant winsorises at the pooled 1st/99th percentile of ITS OWN excess values
(the primary rule applied to the variant's data).
(a) Permutation: the buy/sell labels are shuffled within each date (list sizes
    kept), 10,000 times, seed 20260927; the phase statistic is the mean per-date
    spread, and the real explore and holdout spreads are placed in that
    distribution (two-sided p = (1 + #{|perm| >= |real|}) / (B + 1)).
(b) Horizons of 1, 10 and 20 trading days after D+1 (instead of 5). Descriptive:
    the grid step (6 days) was set for 5-day windows, so the 10 and 20 day
    windows of successive dates overlap.
(c) The top 10 buys against the top 10 sells (lists re-sorted by net foreign
    inflow: buys descending, sells ascending).
(d) Benchmark = the median window return of every cached stock instead of ^JKSE.
    Since the benchmark is the same for both lists on a date it cancels from the
    spread; it can change the result only through the winsorisation.
(e) Without dates in the last 3 trading days of Feb, May, Aug and Nov (index
    review windows; INFERRED dates, not confirmed from any index provider).
(f) Only stocks whose absolute net foreign flow is above the median of their own
    list (strictly), for both lists: the "large net" subset. Reading choice: the
    sell list has negative net flows, so "above the median" is read on the size of
    the flow.
Variant tests: (a) 1, (b) 3, (c) 1, (d) 1, (e) 1, (f) 1 = 8, each in two phases.

Run:
    .venv/bin/python -m pipeline.hypotheses.stress_h6
"""
from __future__ import annotations

import json
import math
import random
import statistics
from datetime import date
from typing import Callable

from pipeline.hypotheses import h6_foreign_list as h6
from pipeline.hypotheses._stress_common import PERMUTATIONS, SEED, check_frozen, permutation_position

PHASES = ("explore", "holdout")
FROZEN = {"explore": {"n_dates": 26, "spread_pct": 0.05}, "holdout": {"n_dates": 35, "spread_pct": -0.03}}
REVIEW_MONTHS = (2, 5, 8, 11)
LAST_DAYS = 3

Select = Callable[[list[dict], str], list[dict]]


# ------------------------------------------------------------- generalised pieces
def _by_net(items: list[dict], side: str) -> list[dict]:
    """Buys by net inflow descending, sells ascending (most negative first)."""
    return sorted(items, key=lambda x: -x["net_foreign_inflow"] if side == "buy" else x["net_foreign_inflow"])


def select_all(items: list[dict], side: str) -> list[dict]:
    return items


def select_top(k: int) -> Select:
    return lambda items, side: _by_net(items, side)[:k]


def select_large_net(items: list[dict], side: str) -> list[dict]:
    """Items whose |net| is strictly above the median |net| of the list."""
    if not items:
        return []
    med = statistics.median(abs(x["net_foreign_inflow"]) for x in items)
    return [x for x in items if abs(x["net_foreign_inflow"]) > med]


def date_rows(
    d: date,
    lists: dict,
    days: list[date],
    prices: dict[str, dict[date, float]],
    benchmark: Callable[[date, date], float | None],
    horizon: int,
    select: Select = select_all,
) -> dict | None:
    """Per-date rows {buy, excess} for the selected stocks, D+1 to D+1+horizon; None if the calendar lacks the window."""
    i = days.index(d)
    if i + 1 + horizon >= len(days):
        return None
    d1, d_end = days[i + 1], days[i + 1 + horizon]
    bench = benchmark(d1, d_end)
    if bench is None:
        return None
    rows, missing = [], 0
    for side, flag in (("buy", 1), ("sell", 0)):
        for item in select(lists.get(d.isoformat(), {}).get(side, []), side):
            px = prices.get(item["symbol"])
            r = h6.window_return(px, d1, d_end) if px else None
            if r is None:
                missing += 1
                continue
            rows.append({"symbol": item["symbol"], "buy": flag, "excess": r - bench})
    return {"date": d, "rows": rows, "missing": missing}


def jkse_benchmark(index_px: dict[date, float]) -> Callable[[date, date], float | None]:
    return lambda a, b: h6.window_return(index_px, a, b)


def universe_median_benchmark(prices: dict[str, dict[date, float]]) -> Callable[[date, date], float | None]:
    memo: dict[tuple[date, date], float | None] = {}

    def bench(a: date, b: date) -> float | None:
        if (a, b) not in memo:
            rets = [r for px in prices.values() if (r := h6.window_return(px, a, b)) is not None]
            memo[(a, b)] = statistics.median(rets) if rets else None
        return memo[(a, b)]

    return bench


def phase_split(per_date: list[dict]) -> dict[str, list[dict]]:
    return {
        "explore": [x for x in per_date if x["date"] <= h6.EXPLORE_END],
        "holdout": [x for x in per_date if x["date"] > h6.EXPLORE_END],
    }


def phase_spread_test(per_date: list[dict]) -> dict[str, dict]:
    """Winsorise at this variant's pooled 1st/99th percentile, then the per-phase one-sample t on per-date spreads."""
    all_ex = [r["excess"] for x in per_date for r in x["rows"]]
    lo, hi = h6.winsorize_bounds(all_ex)
    out = {}
    for ph, rows in phase_split(per_date).items():
        spreads = [s for s in (h6.date_spread(x["rows"], lo, hi) for x in rows) if s is not None]
        res = h6.one_sample_t(spreads)
        res["n_dates"] = len(spreads)
        res["bounds"] = (lo, hi)
        out[ph] = res
    return out


def fmt(res: dict) -> str:
    if math.isnan(res["mean"]):
        return f"dates {res['n_dates']}: not computable"
    return f"dates {res['n_dates']}  spread {res['mean'] * 100:+.3f}%  (t {res['t']:+.2f}, p {res['p']:.3f})"


def excluded_review_dates(days: list[date]) -> set[date]:
    """The last LAST_DAYS trading days of each Feb, May, Aug and Nov on the ^JKSE calendar (inferred windows)."""
    out: set[date] = set()
    by_month: dict[tuple[int, int], list[date]] = {}
    for d in days:
        by_month.setdefault((d.year, d.month), []).append(d)
    for (y, m), ds in by_month.items():
        if m in REVIEW_MONTHS:
            out.update(sorted(ds)[-LAST_DAYS:])
    return out


def permutation_test(phase_rows: dict[str, list[dict]], lo: float, hi: float, b: int = PERMUTATIONS, seed: int = SEED) -> dict:
    """Shuffle buy/sell labels within each date b times; the real mean spread against the permuted ones."""
    rng = random.Random(seed)
    out = {}
    for ph in PHASES:
        dates = []
        for x in phase_rows[ph]:
            vals = [min(max(r["excess"], lo), hi) for r in x["rows"]]
            k = sum(r["buy"] for r in x["rows"])
            if 0 < k < len(vals):
                dates.append((vals, k, sum(v for v, r in zip(vals, x["rows"]) if r["buy"]), sum(vals)))
        if not dates:
            out[ph] = {"real": float("nan"), "n_perm": 0, "p_two_sided": float("nan"), "p_upper": float("nan"), "percentile": float("nan"), "perm_mean": float("nan"), "perm_sd": float("nan"), "n_dates": 0}
            continue
        real = statistics.fmean(sb / k - (tot - sb) / (len(v) - k) for v, k, sb, tot in dates)
        perm = []
        for _ in range(b):
            spreads = []
            for v, k, _sb, tot in dates:
                s = sum(v[j] for j in rng.sample(range(len(v)), k))
                spreads.append(s / k - (tot - s) / (len(v) - k))
            perm.append(statistics.fmean(spreads))
        res = permutation_position(real, perm)
        res["n_dates"] = len(dates)
        out[ph] = res
    return out


# ------------------------------------------------------------------ main run
def run_st5(lists: dict, days: list[date], prices: dict[str, dict[date, float]], index_px: dict[date, float]) -> dict:
    print("=" * 78)
    print("ST5 -- H6 (foreign buying): stress variants")
    print("=" * 78)
    grid = h6.trading_grid(days)
    jkse = jkse_benchmark(index_px)

    def build(horizon: int, bench, select: Select = select_all, only: set[date] | None = None, skip: set[date] | None = None) -> list[dict]:
        rows = [date_rows(d, lists, days, prices, bench, horizon, select) for d in grid if (only is None or d in only) and not (skip and d in skip)]
        return [r for r in rows if r]

    primary = build(h6.HORIZON, jkse)
    prim = phase_spread_test(primary)

    # parity with the frozen module's own statistic
    frozen_rows = [x for x in (h6.build_date_rows(d, lists, days, prices, index_px) for d in grid) if x]
    lo, hi = h6.winsorize_bounds([r["excess"] for x in frozen_rows for r in x["rows"]])
    frozen_ph = {"explore": [x for x in frozen_rows if x["date"] <= h6.EXPLORE_END], "holdout": [x for x in frozen_rows if x["date"] > h6.EXPLORE_END]}
    print("Reproduction (before any variant):")
    ok = True
    for ph in PHASES:
        ref = h6.analyze_phase(frozen_ph[ph], lo, hi)
        ok &= check_frozen(f"{ph} dates", prim[ph]["n_dates"], FROZEN[ph]["n_dates"])
        ok &= check_frozen(f"{ph} spread (%, 2 dp)", round(prim[ph]["mean"] * 100, 2), FROZEN[ph]["spread_pct"])
        ok &= check_frozen(f"{ph} spread equals h6.analyze_phase exactly", prim[ph]["mean"], ref["mean"])
        ok &= check_frozen(f"{ph} p equals h6.analyze_phase exactly", prim[ph]["p"], ref["p"])
    if not ok:
        print("STOP: frozen H6 figures not reproduced; no variant computed.")
        return {"reproduced": False}
    verdict = h6.verdict(prim["explore"], prim["holdout"])
    print()
    for ph in PHASES:
        print(f"  primary {ph}: {fmt(prim[ph])}")
    print(f"  pre-registered decision (holdout spread > 0, p < 0.05, explore same sign): {verdict}\n")

    out: dict = {"reproduced": True, "primary": prim, "verdict": verdict, "variants": {}}
    flagged: list[str] = []
    n_tests = 0

    def report(label: str, res: dict[str, dict]) -> None:
        nonlocal n_tests
        n_tests += 1
        out["variants"][label] = res
        for ph in PHASES:
            r = res[ph]
            tag = ""
            if not math.isnan(r["p"]) and r["p"] < h6.ALPHA:
                sign = "positive" if r["mean"] > 0 else "negative"
                tag = f"  <-- p < 0.05 ({sign}): significant only under a variant not pre-registered"
                flagged.append(f"{label} {ph} ({sign}, p {r['p']:.3f})")
            print(f"    {label} | {ph}: {fmt(r)}{tag}")

    # (a) permutation
    print(f"(a) permutation of buy/sell labels within each date ({PERMUTATIONS} shuffles, seed {SEED}); primary winsorisation bounds {lo * 100:+.2f}% / {hi * 100:+.2f}%")
    perm = permutation_test(phase_split(primary), lo, hi)
    n_tests += 1
    out["variants"]["a permutation"] = perm
    for ph in PHASES:
        r = perm[ph]
        tag = ""
        if r["p_two_sided"] < h6.ALPHA:
            tag = "  <-- permutation p < 0.05: significant only under a variant not pre-registered"
            flagged.append(f"a permutation {ph} (p {r['p_two_sided']:.4f})")
        print(
            f"    {ph}: real spread {r['real'] * 100:+.3f}% over {r['n_dates']} dates; permuted mean {r['perm_mean'] * 100:+.3f}%, sd {r['perm_sd'] * 100:.3f}%; "
            f"real is at percentile {r['percentile'] * 100:.1f}; two-sided p {r['p_two_sided']:.4f}, upper-tail p {r['p_upper']:.4f}{tag}"
        )

    # (b) horizons
    print("(b) horizon after D+1 (descriptive; 10 and 20 day windows of successive dates overlap)")
    for hz in (1, 10, 20):
        rows = build(hz, jkse)
        report(f"b horizon {hz}", phase_spread_test(rows))

    # (c) top 10 vs top 10
    print("(c) top 10 buys versus top 10 sells")
    order_ok = all(
        [x["net_foreign_inflow"] for x in lists[d.isoformat()][side]] == [x["net_foreign_inflow"] for x in _by_net(lists[d.isoformat()][side], side)]
        for d in grid
        for side in ("buy", "sell")
    )
    print(f"    (lists as saved are already in net order: {order_ok})")
    report("c top10", phase_spread_test(build(h6.HORIZON, jkse, select_top(10))))

    # (d) equal-weight universe benchmark
    print("(d) benchmark = median window return of the cached universe")
    report("d universe-median benchmark", phase_spread_test(build(h6.HORIZON, universe_median_benchmark(prices))))

    # (e) without index-review windows
    skip = excluded_review_dates(days)
    dropped = [d for d in grid if d in skip]
    print(f"(e) without dates in the last {LAST_DAYS} trading days of Feb/May/Aug/Nov (inferred windows); {len(dropped)} grid dates dropped: {', '.join(d.isoformat() for d in dropped)}")
    report("e without review windows", phase_spread_test(build(h6.HORIZON, jkse, skip=skip)))

    # (f) large net flows
    print("(f) only stocks with |net foreign flow| above the median of their own list")
    report("f large net flows", phase_spread_test(build(h6.HORIZON, jkse, select_large_net)))

    out["variant_tests"] = n_tests
    out["flagged_significant_variants"] = flagged
    print(f"\nVariants examined for ST5: {n_tests} tests, each in explore and holdout ({2 * n_tests} phase-cells)")
    print(f"Variant cells with p < 0.05: {flagged or 'none'}")
    print(f"Decision: primary result {verdict}; H6 verdict unchanged ({'unchanged' if not verdict.startswith('CONFIRMED') else 'changed'}).")
    return out


def main() -> None:
    lists = json.loads(h6.LISTS_PATH.read_text())
    prices, index_px = h6._load_prices()
    run_st5(lists, h6.jkse_days(), prices, index_px)


if __name__ == "__main__":
    main()
