"""
Base rate: how far does a typical IDX stock actually fall in a bad
stretch, and does that answer differ by company size?

NOT a falsifiable hypothesis -- descriptive base rate, same category as
H16/loss-maker-turnaround (no explore/holdout split, no significance
test, not counted in the trial counter). From docs/PLAN.md's Chunk M:
"sets expectations before buying, so a normal fall isn't mistaken for a
unique disaster."

Data: Yahoo **1-year** dev cache (`close`, matching H1/H1b's own
convention -- both compute max_drawdown over the 1-year cache, not the
5-year one; using raw price, not `adjclose`, per H1's price-behavior
convention -- see docs/DATA.md's close-vs-adjclose note) + the owned
`market_cap` snapshot (`data/raw/market_cap_2026-09-06.json`) for the
size bucketing.

⚠️ A first attempt at this used the 5-year cache's FULL-PERIOD max
drawdown and produced implausibly extreme numbers (median −74.7%,
smallest tercile −85.1%) -- caught by comparing against H1b's own
already-published 1-year drawdown figures (−40% to −66% range) before
writing anything up. The 5-year cumulative figure answers a different,
much harsher question ("worst single decline across 5 years, which for
many stocks includes a genuine multi-year collapse") than "how far does
a stock like this usually fall in a bad year" -- switched to the 1-year
cache to match H1b's own convention and stay answerable to the question
actually being asked.

⚠️ Using a CURRENT snapshot field (`market_cap`) to bucket stocks here
is fine precisely because this is a DESCRIPTIVE grouping ("stocks this
size, right now"), not a predictive claim -- CLAUDE.md's
predictor-before-outcome rule governs hypothesis tests ("X predicts
Y"), not descriptive peer/size groupings, the same reasoning that
already lets docs/PRODUCT.md's peer-comparison lenses use current
`sub_sector`.

Method: one `pipeline.stats.max_drawdown` computed per stock over its
1-year `close` history (a single number per stock -- no rolling-window
overlap issue, since this isn't a per-window significance test).
Reported as the overall distribution (median/25th/75th percentile)
across all stocks with usable history, then broken out by market-cap
tercile.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_typical_drawdown
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from pipeline.hypotheses.h1_free_float import load_market_cap
from pipeline.stats import max_drawdown

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_1Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_1y.json"

MIN_TRADING_DAYS = 120  # matches H1's own 1y minimum-history threshold


def build_rows(prices1y: dict, market_cap: dict[str, float]) -> list[dict]:
    rows = []
    for sym, entry in prices1y.items():
        closes = [c for c in entry.get("close", []) if c is not None and c > 0]
        if len(closes) < MIN_TRADING_DAYS:
            continue
        mc = market_cap.get(sym)
        if mc is None:
            continue
        rows.append({"sym": sym, "mdd": max_drawdown(closes), "market_cap": mc})
    return rows


def _percentiles(values: list[float]) -> tuple[float, float, float]:
    s = sorted(values)
    n = len(s)
    p25 = s[int(0.25 * (n - 1))]
    p50 = statistics.median(s)
    p75 = s[int(0.75 * (n - 1))]
    return p25, p50, p75


def _print_bucket(label: str, rows: list[dict]) -> None:
    mdds = [r["mdd"] for r in rows]
    p25, p50, p75 = _percentiles(mdds)
    print(f"  {label:<24}: n={len(rows):>4}  25th={p25:+.1%}  median={p50:+.1%}  75th={p75:+.1%}")


def main() -> None:
    prices1y = json.loads(PRICES_1Y_PATH.read_text())
    market_cap = load_market_cap()
    rows = build_rows(prices1y, market_cap)

    print(f"Typical drawdown -- {len(rows)} stocks with >= {MIN_TRADING_DAYS} trading days of history (1-year window)\n")
    print("Overall (all stocks pooled):")
    _print_bucket("All IDX stocks", rows)

    sorted_rows = sorted(rows, key=lambda r: r["market_cap"])
    n = len(sorted_rows)
    tercile_size = n // 3
    small = sorted_rows[:tercile_size]
    mid = sorted_rows[tercile_size : 2 * tercile_size]
    large = sorted_rows[2 * tercile_size :]

    print("\nBy market-cap tercile (current snapshot, descriptive grouping only):")
    _print_bucket("Smallest tercile", small)
    _print_bucket("Mid tercile", mid)
    _print_bucket("Largest tercile", large)

    print(
        "\nDescriptive base rate only -- worst peak-to-trough decline over the most\n"
        "recent 1-year window, one observation per stock (same window H1/H1b use).\n"
        "Not a forecast of any specific stock's future drawdown; not counted in the\n"
        "project trial counter."
    )


if __name__ == "__main__":
    main()
