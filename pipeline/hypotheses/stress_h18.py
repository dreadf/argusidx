"""
Stress test ST4 -- H18 ("Orang dalam beli -> harga naik"), pre-registered in
EXPERIMENT.md ("Pre-registration, 2026-09-27 -- stress tests of the newest
hypotheses and situations"), run once. NOT a new trial: H18 stays NOT confirmed
unless the PRIMARY holdout result is significant (holdout mean above 0 with
p < 0.05 and the holdout median event above 0, primary definition). Variants are
sensitivity, never a second chance; a significant variant is reported as
"significant only under a variant not pre-registered".

Reproduction first: the primary H18 result is recomputed with this module's
generalised code and printed next to the frozen values (explore +7.2%, p 0.039,
300 of 314 events; holdout +3.0%, p 0.25, 292 of 346 events). A mismatch stops
the module.

Variants, each in explore and holdout, all built on `h18_insider_buying`'s own
event rule, outcome window and statistic (month means of the excess return, a
one-sample exact-t test across months; `h18_insider_buying.analyze_phase`):
(a) event excess winsorised at the pooled (both phases) 1st and 99th percentile
    (`h6_foreign_list.winsorize_bounds`); (b) refractory 30 and 90 days instead
    of 60; (c) horizons 5, 10 and 60 trading days instead of 20; (d) benchmark =
    the median window return of every cached stock with prices at both ends
    (an equal-weight median; the event's own stock is included in it) instead of
    ^JKSE; (e) without stocks in the lowest market-cap tercile (terciles of the
    cached stocks by the market-cap snapshot, description of size only);
(f) event-level cluster bootstrap by stock (B = 2,000, seed 20260927) of the
    event mean and the event median, plus the primary month-mean statistic;
(g) minimum detectable effect per phase (two-sided alpha 0.05, 80% power, exact
    t; the pre-registration does not fix these, they are the conventional ones),
    for the month-mean test and for an independent-events test.
Count: (a) 2 + (b) 4 + (c) 6 + (d) 2 + (e) 2 + (f) 2 = 18 phase-cells (16 in
(a) to (e)); the pre-registration says "17 in total", a difference reported as
found. (g) is not a variant.

Run:
    .venv/bin/python -m pipeline.hypotheses.stress_h18
"""
from __future__ import annotations

import bisect
import json
import math
import statistics
from datetime import date
from pathlib import Path
from typing import Callable

from pipeline.hypotheses import h18_insider_buying as h18
from pipeline.hypotheses._stress_common import (
    BOOTSTRAP_B,
    SEED,
    check_frozen,
    cluster_bootstrap,
    mde_mean,
)
from pipeline.hypotheses.h6_foreign_list import _close_by_day, one_sample_t, window_return, winsorize_bounds
from pipeline.hypotheses.stress_c_s2 import load_market_cap, size_terciles

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASES = ("explore", "holdout")
FROZEN = {
    "explore": {"events": 314, "used": 300, "mean_pct": 7.2, "p": 0.039},
    "holdout": {"events": 346, "used": 292, "mean_pct": 3.0, "p": 0.25},
}


# ------------------------------------------------------------- generalised pieces
def build_events(filings: list[dict], days: list[date], refractory: int = h18.REFRACTORY_DAYS) -> list[dict]:
    """`h18_insider_buying.build_events` with the refractory length as a parameter (60 = the frozen one)."""
    by_stock: dict[str, list[dict]] = {}
    for f in filings:
        shifted = h18.next_trading_day(f["date"], days)
        by_stock.setdefault(f["sym"], []).append(
            {**f, "event_date": shifted if shifted is not None else f["date"], "beyond_calendar": shifted is None}
        )
    events: list[dict] = []
    for sym, rows in by_stock.items():
        rows.sort(key=lambda r: (r["event_date"], r["date"]))
        last: date | None = None
        for r in rows:
            if last is not None and (r["event_date"] - last).days <= refractory:
                continue
            events.append({"sym": sym, **{k: r[k] for k in ("date", "event_date", "is_takeover", "beyond_calendar")}})
            last = r["event_date"]
    events.sort(key=lambda e: (e["sym"], e["event_date"]))
    return events


def excess_general(
    event: dict,
    days: list[date],
    prices: dict[str, dict[date, float]],
    benchmark: Callable[[date, date], float | None],
    horizon: int,
) -> float | None:
    """Stock return minus the benchmark return from the first day after the event date to `horizon` days later."""
    i = bisect.bisect_right(days, event["event_date"])
    if i + horizon >= len(days):
        return None
    start, end = days[i], days[i + horizon]
    px = prices.get(event["sym"])
    stock = window_return(px, start, end) if px else None
    bench = benchmark(start, end)
    if stock is None or bench is None:
        return None
    return stock - bench


def jkse_benchmark(index_px: dict[date, float]) -> Callable[[date, date], float | None]:
    return lambda a, b: window_return(index_px, a, b)


def universe_median_benchmark(prices: dict[str, dict[date, float]]) -> Callable[[date, date], float | None]:
    """Median window return over every cached stock with a price at both ends (cached per window)."""
    memo: dict[tuple[date, date], float | None] = {}

    def bench(a: date, b: date) -> float | None:
        key = (a, b)
        if key not in memo:
            rets = [r for px in prices.values() if (r := window_return(px, a, b)) is not None]
            memo[key] = statistics.median(rets) if rets else None
        return memo[key]

    return bench


def make_rows(
    events: list[dict],
    days: list[date],
    prices: dict[str, dict[date, float]],
    benchmark: Callable[[date, date], float | None],
    horizon: int = h18.HORIZON_TRADING_DAYS,
) -> list[dict]:
    """One row per in-phase event: phase, sym, filing date, takeover flag, excess (or None)."""
    rows = []
    for e in events:
        phase = h18.phase_of(e)
        if phase is None:
            continue
        rows.append(
            {
                "phase": phase,
                "sym": e["sym"],
                "date": e["date"],
                "is_takeover": e["is_takeover"],
                "excess": excess_general(e, days, prices, benchmark, horizon),
            }
        )
    return rows


def month_means(rows: list[dict]) -> list[float]:
    by_month: dict[tuple[int, int], list[float]] = {}
    for r in rows:
        if r["excess"] is not None:
            by_month.setdefault((r["date"].year, r["date"].month), []).append(r["excess"])
    return [statistics.fmean(v) for _, v in sorted(by_month.items())]


def phase_stats(rows: list[dict]) -> dict:
    """Primary statistic set for one phase's rows (`h18.analyze_phase`)."""
    return h18.analyze_phase(rows)


def winsorised(rows: list[dict], lo: float, hi: float) -> list[dict]:
    return [{**r, "excess": None if r["excess"] is None else min(max(r["excess"], lo), hi)} for r in rows]


def fmt_stats(s: dict) -> str:
    def pc(x: float) -> str:
        return "n/a" if x is None or math.isnan(x) else f"{x * 100:+.2f}%"

    t = "n/a" if math.isnan(s["t"]) else f"{s['t']:+.2f}"
    p = "n/a" if math.isnan(s["p"]) else f"{s['p']:.3f}"
    return (
        f"events {s['n_events']} used {s['n_events_used']} months {s['n_months']}  mean of month means {pc(s['mean'])} "
        f"(t {t}, p {p})  median event {pc(s['median_event_excess'])}  beat index {s['share_beating_index'] * 100:.1f}%"
        if s["n_events_used"]
        else f"events {s['n_events']} used 0"
    )


# ------------------------------------------------------------------ main run
def run_st4(filings: list[dict], prices_raw: dict, benchmarks: dict, market_cap: dict[str, float]) -> dict:
    print("=" * 78)
    print("ST4 -- H18 (insiders buy): stress variants")
    print("=" * 78)
    days = h18.trading_days_from_entry(benchmarks[h18.BENCHMARK])
    prices = {s: _close_by_day(e) for s, e in prices_raw.items() if e.get("timestamps")}
    index_px = _close_by_day(benchmarks[h18.BENCHMARK])
    jkse = jkse_benchmark(index_px)

    events60 = build_events(filings, days)
    rows = make_rows(events60, days, prices, jkse)
    prim = {ph: phase_stats([r for r in rows if r["phase"] == ph]) for ph in PHASES}

    # ---- reproduction, including a parity check against the frozen module's own outcome function
    print("Reproduction (before any variant):")
    ok = check_frozen("events after the 60-day rule", len(events60), len(h18.build_events(filings, days)))
    frozen_out = h18.build_outcomes(h18.build_events(filings, days), days, prices, index_px)
    for ph in PHASES:
        f = FROZEN[ph]
        p = prim[ph]
        ok &= check_frozen(f"{ph} events / used", (p["n_events"], p["n_events_used"]), (f["events"], f["used"]))
        ok &= check_frozen(f"{ph} mean of month means (%, 1 dp)", round(p["mean"] * 100, 1), f["mean_pct"])
        ok &= check_frozen(f"{ph} p-value ({'3' if ph == 'explore' else '2'} dp)", round(p["p"], 3 if ph == "explore" else 2), f["p"])
        ok &= check_frozen(f"{ph} mean equals h18.build_outcomes exactly", p["mean"], frozen_out[ph]["mean"])
    if not ok:
        print("STOP: frozen H18 figures not reproduced; no variant computed.")
        return {"reproduced": False}
    print()
    for ph in PHASES:
        print(f"  primary {ph}: {fmt_stats(prim[ph])}")
    holdout_ok = prim["holdout"]["mean"] > 0 and prim["holdout"]["p"] < 0.05 and prim["holdout"]["median_event_excess"] > 0
    verdict = "CONFIRMED" if holdout_ok else "NOT confirmed"
    print(f"  decision rule (holdout mean > 0, p < 0.05, holdout median > 0, primary definition): {verdict}\n")

    out: dict = {"reproduced": True, "primary": prim, "verdict": verdict, "variants": {}}
    flagged: list[str] = []
    cells = 0

    def report(label: str, phase_rows: dict[str, list[dict]], extra: str = "") -> None:
        nonlocal cells
        res = {}
        for ph in PHASES:
            s = phase_stats(phase_rows[ph])
            res[ph] = s
            cells += 1
            tag = ""
            if not math.isnan(s["p"]) and s["p"] < 0.05:
                sign = "positive" if s["mean"] > 0 else "negative"
                tag = f"  <-- p < 0.05 ({sign}): significant only under a variant not pre-registered"
                flagged.append(f"{label} {ph} ({sign}, p {s['p']:.3f})")
            print(f"    {label} | {ph}: {fmt_stats(s)}{tag}")
        if extra:
            print(f"      {extra}")
        out["variants"][label] = res

    by_phase = lambda rs: {ph: [r for r in rs if r["phase"] == ph] for ph in PHASES}  # noqa: E731

    # (a) winsorised
    print("(a) event excess winsorised at the pooled 1st and 99th percentile")
    all_ex = [r["excess"] for r in rows if r["excess"] is not None]
    lo, hi = winsorize_bounds(all_ex)
    report("a winsorised", by_phase(winsorised(rows, lo, hi)), f"bounds {lo * 100:+.2f}% / {hi * 100:+.2f}% over {len(all_ex)} events")

    # (b) refractory
    print("(b) refractory window (days between events of one stock)")
    for ref in (30, 90):
        ev = build_events(filings, days, ref)
        rs = make_rows(ev, days, prices, jkse)
        n_ph = {ph: sum(1 for e in ev if h18.phase_of(e) == ph) for ph in PHASES}
        report(f"b refractory {ref}", by_phase(rs), f"events per phase {n_ph}")

    # (c) horizons
    print("(c) horizon in trading days")
    for hz in (5, 10, 60):
        rs = make_rows(events60, days, prices, jkse, hz)
        report(f"c horizon {hz}", by_phase(rs))

    # (d) universe-median benchmark
    print("(d) benchmark = median window return of the cached universe")
    rs = make_rows(events60, days, prices, universe_median_benchmark(prices))
    report("d universe-median benchmark", by_phase(rs))

    # (e) without the lowest market-cap tercile
    print("(e) without stocks in the lowest market-cap tercile")
    terc = size_terciles(market_cap, list(prices))
    kept = [r for r in rows if terc.get(r["sym"]) != "smallest"]
    dropped = {ph: sum(1 for r in rows if r["phase"] == ph and terc.get(r["sym"]) == "smallest") for ph in PHASES}
    no_cap = sum(1 for r in rows if r["sym"] in prices and r["sym"] not in terc)
    report("e without lowest tercile", by_phase(kept), f"events removed {dropped}; events on cached stocks with no market cap (kept): {no_cap}")

    # (f) event-level cluster bootstrap by stock
    print(f"(f) cluster bootstrap by stock (B = {BOOTSTRAP_B}, seed {SEED}), primary definition")
    out["variants"]["f bootstrap"] = {}
    for ph in PHASES:
        used = [r for r in rows if r["phase"] == ph and r["excess"] is not None]
        clusters: dict[str, list] = {}
        for r in used:
            clusters.setdefault(r["sym"], []).append(r)
        stats = {
            "event mean": lambda s: statistics.fmean(r["excess"] for r in s) if s else None,
            "event median": lambda s: statistics.median(r["excess"] for r in s) if s else None,
            "mean of month means (primary statistic)": lambda s: (statistics.fmean(month_means(s)) if month_means(s) else None),
        }
        res = {}
        for name, fn in stats.items():
            bs = cluster_bootstrap(clusters, fn)
            zero_in = bs["low"] <= 0 <= bs["high"]
            res[name] = bs
            print(f"    {ph} {name}: {bs['estimate'] * 100:+.2f}% [95% {bs['low'] * 100:+.2f}%, {bs['high'] * 100:+.2f}%] over {bs['n_clusters']} stocks -> {'includes 0' if zero_in else 'excludes 0'}")
            if name != "mean of month means (primary statistic)":
                cells += 1 if name == "event mean" else 0
        out["variants"]["f bootstrap"][ph] = res

    # (g) minimum detectable effect
    print("(g) minimum detectable effect (two-sided alpha 0.05, 80% power, exact t)")
    out["mde"] = {}
    for ph in PHASES:
        mm = month_means([r for r in rows if r["phase"] == ph])
        ev = [r["excess"] for r in rows if r["phase"] == ph and r["excess"] is not None]
        mde_month = mde_mean(statistics.stdev(mm), len(mm))
        mde_event = mde_mean(statistics.stdev(ev), len(ev))
        out["mde"][ph] = {"months": len(mm), "sd_month_means": statistics.stdev(mm), "mde_month_test": mde_month, "events": len(ev), "sd_events": statistics.stdev(ev), "mde_independent_events": mde_event}
        print(
            f"    {ph}: month-mean test, {len(mm)} months, sd of month means {statistics.stdev(mm) * 100:.2f}%, MDE {mde_month * 100:.2f}% "
            f"(observed primary mean {prim[ph]['mean'] * 100:+.2f}%); independent events, {len(ev)} events, sd {statistics.stdev(ev) * 100:.2f}%, MDE {mde_event * 100:.2f}%"
        )

    out["phase_cells_examined"] = cells
    out["flagged_significant_variants"] = flagged
    print(f"\nVariants examined for ST4: {cells} phase-cells in (a) to (f) (pre-registration text says 17)")
    print(f"Variant cells with p < 0.05: {flagged or 'none'}")
    print(f"Decision: primary result {verdict}; H18 verdict unchanged ({'unchanged' if verdict == 'NOT confirmed' else 'changed'}).")
    return out


def main() -> None:
    filings = h18.load_filings()
    prices_raw = json.loads(h18.PRICES_5Y_PATH.read_text())
    benchmarks = json.loads(h18.BENCHMARKS_5Y_PATH.read_text())
    run_st4(filings, prices_raw, benchmarks, load_market_cap())


if __name__ == "__main__":
    main()
