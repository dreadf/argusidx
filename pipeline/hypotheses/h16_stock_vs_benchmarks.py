"""
H16: of IDX stocks, how many actually beat the alternatives to picking
them -- the index itself, gold, a bank deposit, or just a typical other
stock?

NOT a falsifiable predictive hypothesis in the H1/H5/H14/H15 sense --
this makes no "X predicts Y" claim and needs no explore/holdout split.
It is descriptive/comparative, the same category this project's own
plan already distinguishes for the sector lenses ("correct arithmetic,"
not a testable claim) -- so it does NOT add to the trial counter. Kept
the "H16" label only for continuity with how it was discussed before
being built; it belongs with the base-rate family (Chunk M), not the
hypothesis register.

Why this exists (see the conversation that led here): every hypothesis
tested so far (H1, H5, H14, H15) asks "does signal X help pick a BETTER
stock." This asks the prior question a retail investor should ask
first: is picking an individual stock, in general, even a good idea
compared to the alternatives? This is the Bessembinder question
(Bessembinder, "Do Stocks Outperform Treasury Bills?", SSRN 2018)
applied to IDX -- nobody has published this for Indonesia. His US
finding: 4 of 7 stocks underperformed T-bills over their lifetime, and
the best-performing 4% of firms explain the ENTIRE market's net wealth
creation above cash -- the other 96% collectively just matched it. That
result comes from positive skew in the return distribution (a few huge
winners), not from typical stocks being good bets.

Honest scope limitation, stated up front: Bessembinder used ~90 years of
US data; this uses ~5 years of owned Yahoo price history. This measures
"how IDX stocks did over roughly 2021-2026," not "over their lifetimes."
Different, narrower claim -- said so explicitly rather than borrowing
his framing's weight.

Five benchmarks, chosen and scoped in discussion with the user
(2026-09-12), each ANNUALIZED so stocks with different available
histories (older listings vs recent IPOs) can be compared fairly:

1. **IDX Composite index (^JKSE)** -- the standard "just buy the market."
   Date-matched: computed over the SAME two calendar dates as each
   stock's own window, from the new `data/dev_cache/benchmarks_5y.json`
   (pipeline/dev/fetch_benchmark_prices.py, dev-only, never ships).
2. **Gold, in rupiah** (`GC=F` USD price x `USDIDR=X` exchange rate).
   Verified via search (2026-09-12, snippet-level): 67% of Indonesians
   hold gold as an investment; it returned 32% (2024) and 44%
   (2025 YTD) in rupiah terms -- for a large share of this project's
   target audience, this may be the ACTUAL alternative to buying a
   stock, not a theoretical one. Date-matched, same as the index.
3. **Bank deposit / BI policy rate.** No API gives this as a queryable
   time series -- built from a small manually-compiled table
   (BI_RATE_TABLE below) sourced from bi.go.id directly (fetched
   2026-09-12) plus this project's own already-cited 2025 rate-cut
   dates (docs/SOURCES.md). Mixed precision, disclosed per entry: the
   2025-2026 entries are day-precise (fetched from Bank Indonesia's own
   published decision dates); the 2021-2024 entries are month-precise
   (secondary aggregator, `[snippet]`) since day-level BI decision
   dates for that period weren't re-verified this session. One
   disclosed gap: the exact date of the drop from 5.25% (Jul 2025) to
   4.75% (by Dec 2025) isn't pinned down -- approximated as a single
   step at the later, verified date rather than guessing an intermediate
   one. This proxies a floating-rate deposit, not any specific bank's
   actual offered rate (which is typically below the policy rate) --
   a real, stated simplification, not a precise consumer product.
4. **The typical stock, not just the index (Bessembinder's actual
   point).** The cap-weighted index is itself dragged up by the same
   handful of giant winners a stock being evaluated was never
   realistically going to weight like. Computed as the CROSS-SECTIONAL
   MEDIAN of every stock's own annualized return -- a population-level
   number, not date-matched per stock (there's no single "typical
   stock" price series to look up against).
5. **Sector/sub-sector peer median.** Same population-level design as
   (4), computed within each stock's own `sub_sector` (33 groups,
   already owned from the universe sweep) -- ties this into the peer-
   group machinery already planned for the product's 4 lenses.

Per-stock method:
    1. Take the stock's own available window in the Yahoo cache (first
       to last timestamp) -- NOT a forced common window. A forced
       common window would bias toward old, stable, already-listed-in-
       2021 companies and exclude newer IPOs, which is exactly the
       population most relevant to "someone about to buy a hot listing."
    2. Require at least MIN_YEARS of history (default 1.0) -- shorter
       windows produce wild, meaningless annualized numbers.
    3. Total return over that window, `adjclose` (dividend-inclusive,
       matching H5's own return convention), annualized:
       (1 + total_return) ** (1 / years) - 1.
    4. For the index and gold: total return of that SAME benchmark over
       the SAME two calendar dates (`nearest_value`, `MAX_GAP_DAYS`),
       annualized the same way. For the deposit rate: compounded from
       BI_RATE_TABLE over the same two dates. For the typical-stock and
       sector benchmarks: the population-level medians computed after
       every stock's own annualized return is known.

Data (all already owned/free -- no new Sectors call):
    data/dev_cache/prices_5y.json -- Yahoo, dev-only (existing cache).
    data/dev_cache/benchmarks_5y.json -- Yahoo, dev-only, NEW this
        session (pipeline/dev/fetch_benchmark_prices.py).
    data/raw/universe_2026-09-12.json -- `sub_sector`, already purchased.

Run:
    .venv/bin/python -m pipeline.hypotheses.h16_stock_vs_benchmarks
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pipeline.stats import nearest_value

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
BENCHMARKS_PATH = REPO_ROOT / "data" / "dev_cache" / "benchmarks_5y.json"
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-12.json"

MIN_YEARS = 1.0
MAX_GAP_DAYS = 10
RETURN_FIELD = "adjclose"


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=timezone.utc)


# (effective date, annual rate, provenance) -- sorted ascending. See the
# module docstring's benchmark-3 section for the mixed-precision caveat.
BI_RATE_TABLE: list[tuple[datetime, float, str]] = [
    (_dt(2021, 1, 1), 0.0350, "snippet -- held since early 2021"),
    (_dt(2022, 8, 1), 0.0375, "snippet"),
    (_dt(2022, 9, 1), 0.0425, "snippet"),
    (_dt(2022, 10, 1), 0.0475, "snippet"),
    (_dt(2022, 11, 1), 0.0525, "snippet"),
    (_dt(2022, 12, 1), 0.0550, "snippet"),
    (_dt(2023, 2, 1), 0.0575, "snippet"),
    (_dt(2023, 9, 1), 0.0600, "snippet -- held through 2024"),
    (_dt(2025, 1, 15), 0.0575, "fetched -- docs/SOURCES.md"),
    (_dt(2025, 5, 21), 0.0550, "fetched -- docs/SOURCES.md"),
    (_dt(2025, 7, 15), 0.0525, "fetched -- docs/SOURCES.md"),
    (_dt(2025, 12, 17), 0.0475, "fetched -- bi.go.id, 2026-09-12 (one intermediate cut not pinned down)"),
    (_dt(2026, 5, 20), 0.0525, "fetched -- bi.go.id, 2026-09-12"),
    (_dt(2026, 6, 9), 0.0550, "fetched -- bi.go.id, 2026-09-12"),
    (_dt(2026, 6, 18), 0.0575, "fetched -- bi.go.id, 2026-09-12"),
]


def bi_deposit_return(start: datetime, end: datetime) -> float:
    """Compounded return of a floating BI-policy-rate deposit from
    `start` to `end`, built by linking each rate segment's return
    (days_in_segment / 365.25 years at that segment's rate)."""
    total = 1.0
    for i, (eff_date, rate, _prov) in enumerate(BI_RATE_TABLE):
        seg_start = max(eff_date, start)
        next_date = BI_RATE_TABLE[i + 1][0] if i + 1 < len(BI_RATE_TABLE) else end
        seg_end = min(next_date, end)
        if seg_end <= seg_start:
            continue
        days = (seg_end - seg_start).total_seconds() / 86400
        total *= (1 + rate) ** (days / 365.25)
    return total - 1.0


def _annualize(total_return: float, years: float) -> float:
    return (1 + total_return) ** (1 / years) - 1


def build_rows(prices5y: dict, benchmarks: dict, sub_sectors: dict[str, str]) -> list[dict]:
    jkse = benchmarks.get("^JKSE")
    gold_usd = benchmarks.get("GC=F")
    usdidr = benchmarks.get("USDIDR=X")
    rows = []
    for sym, entry in prices5y.items():
        closes = entry.get("close")
        adjcloses = entry.get(RETURN_FIELD)
        timestamps = entry.get("timestamps")
        if not closes or not adjcloses or not timestamps:
            continue
        if any(c <= 0 for c in closes):
            continue
        start_ts, end_ts = timestamps[0], timestamps[-1]
        years = (end_ts - start_ts) / 86400 / 365.25
        if years < MIN_YEARS:
            continue
        p0, p1 = adjcloses[0], adjcloses[-1]
        if p0 <= 0 or p1 <= 0:
            continue
        stock_ann = _annualize(p1 / p0 - 1, years)

        start_dt = datetime.fromtimestamp(start_ts, timezone.utc)
        end_dt = datetime.fromtimestamp(end_ts, timezone.utc)

        jkse_ann = None
        if jkse:
            j0 = nearest_value(jkse, start_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            j1 = nearest_value(jkse, end_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            if j0 and j1:
                jkse_ann = _annualize(j1 / j0 - 1, years)

        gold_ann = None
        if gold_usd and usdidr:
            g0 = nearest_value(gold_usd, start_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            g1 = nearest_value(gold_usd, end_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            fx0 = nearest_value(usdidr, start_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            fx1 = nearest_value(usdidr, end_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            if g0 and g1 and fx0 and fx1:
                gold_idr_0, gold_idr_1 = g0 * fx0, g1 * fx1
                gold_ann = _annualize(gold_idr_1 / gold_idr_0 - 1, years)

        bi_ann = _annualize(bi_deposit_return(start_dt, end_dt), years)

        rows.append(
            {
                "sym": sym,
                "years": years,
                "stock_ann": stock_ann,
                "jkse_ann": jkse_ann,
                "gold_ann": gold_ann,
                "bi_ann": bi_ann,
                "sub_sector": sub_sectors.get(sym),
            }
        )
    return rows


def _win_rate(rows: list[dict], stock_field: str, bench_field: str) -> tuple[int, int]:
    pairs = [(r[stock_field], r[bench_field]) for r in rows if r.get(bench_field) is not None]
    wins = sum(1 for s, b in pairs if s > b)
    return wins, len(pairs)


def main() -> None:
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    benchmarks = json.loads(BENCHMARKS_PATH.read_text())
    universe = json.loads(UNIVERSE_PATH.read_text())
    sub_sectors = {
        r.get("symbol"): (r.get("query_values") or {}).get("sub_sector")
        for r in universe
    }

    rows = build_rows(prices5y, benchmarks, sub_sectors)
    print(f"H16 -- {len(rows)} IDX stocks with >= {MIN_YEARS} year(s) of price history\n")
    if not rows:
        print("  No usable rows -- nothing to report (check prices5y/benchmarks cache).")
        return

    for label, field in [("IDX Composite (^JKSE)", "jkse_ann"), ("Gold (in IDR)", "gold_ann"), ("BI-rate deposit proxy", "bi_ann")]:
        wins, n = _win_rate(rows, "stock_ann", field)
        if n == 0:
            # Reachable if that benchmark ticker failed to fetch entirely
            # (pipeline/dev/fetch_benchmark_prices.py silently excludes a
            # ticker that fails after retries) -- report it plainly
            # instead of crashing on a 100*wins/n divide-by-zero (found
            # by /code-review, 2026-09-12).
            print(f"  Beat {label:>24}: no data (benchmark ticker missing from the cache)")
        else:
            print(f"  Beat {label:>24}: {wins:>4} of {n:>4} stocks ({100*wins/n:.1f}%)")

    # Population-level benchmarks: typical stock, and each stock's own peer group.
    all_ann = [r["stock_ann"] for r in rows]
    typical = statistics.median(all_ann)
    mean_ann = statistics.mean(all_ann)
    wins_typical = sum(1 for a in all_ann if a > typical)
    print(f"  Beat {'the typical (median) stock':>24}: {wins_typical:>4} of {len(all_ann):>4} stocks (50.0% by construction)")
    print(f"\n  Median stock annualized return: {typical:+.1%}   Mean: {mean_ann:+.1%}")
    print(
        f"  (Mean {'>' if mean_ann > typical else '<'} median -- "
        f"{'right-skewed: a few big winners pull the average up, same shape as Bessembinder found in the US' if mean_ann > typical else 'not the skewed shape the US market shows'})"
    )

    by_sector: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r["sub_sector"]:
            by_sector[r["sub_sector"]].append(r["stock_ann"])
    sector_median = {sec: statistics.median(vals) for sec, vals in by_sector.items()}
    sector_wins = sum(1 for r in rows if r["sub_sector"] and r["stock_ann"] > sector_median[r["sub_sector"]])
    sector_n = sum(1 for r in rows if r["sub_sector"])
    if sector_n == 0:
        print("\n  Beat own sub_sector peer median: no rows had a sub_sector value")
    else:
        print(f"\n  Beat {'own sub_sector peer median':>24}: {sector_wins:>4} of {sector_n:>4} stocks ({100*sector_wins/sector_n:.1f}%)")

    print("\n  Concentration (Bessembinder-style) -- top/bottom decile of annualized returns:")
    ordered = sorted(all_ann)
    decile = max(1, len(ordered) // 10)
    bottom = ordered[:decile]
    top = ordered[-decile:]
    print(f"    Bottom decile (n={len(bottom)}): mean {statistics.mean(bottom):+.1%}")
    print(f"    Top decile    (n={len(top)}): mean {statistics.mean(top):+.1%}")
    negative = sum(1 for a in all_ann if a < 0)
    print(f"    {negative} of {len(all_ann)} stocks ({100*negative/len(all_ann):.1f}%) had a NEGATIVE annualized return over their own window")


if __name__ == "__main__":
    main()
