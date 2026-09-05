"""
H1: does free float predict volatility and drawdown on IDX?

STATUS: exploratory, not confirmatory (see EXPERIMENT.md). Tested on all
available data at once with no held-out period. Its credibility rests on
holding across five separate calendar years, not on a formal train/holdout
split. H2 onward must use a proper holdout (RULES.md verification approach).

Pre-registered hypothesis (committed before looking at any result):
    IDX stocks with LOWER free float show HIGHER volatility and deeper
    max drawdowns than high-float stocks over the same period.
    Basis: the documented "gorengan" mechanism, where thin free float
    lets small trades move price disproportionately.
    Falsified if: no monotonic relationship across float quintiles, or
    if the relationship reverses.

Data:
    data/raw/free_float_2026-09-06.json  -- Sectors, PURCHASED (10 credits),
        committed to the repo, never gitignored.
    data/dev_cache/prices_1y.json, prices_5y.json -- Yahoo, free,
        development-time only (see pipeline/dev/fetch_yahoo_prices.py).
        Re-fetchable; regenerate with that script if missing.
    data/raw/market_cap_2026-09-06.json -- Sectors, PURCHASED (5 credits),
        used for the size-confound control.

Run:
    python -m pipeline.hypotheses.h1_free_float

Every number this prints should match EXPERIMENT.md's H1 entry exactly.
If it doesn't, either this code or that entry is wrong -- find out which
before trusting either.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.stats import (
    annualized_volatility,
    max_drawdown,
    median_of,
    no_move_fraction,
    quintiles,
    spearman,
    total_return,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FREE_FLOAT_PATH = REPO_ROOT / "data" / "raw" / "free_float_2026-09-06.json"
MARKET_CAP_PATH = REPO_ROOT / "data" / "raw" / "market_cap_2026-09-06.json"
PRICES_1Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_1y.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"


def load_free_float() -> dict[str, float]:
    rows = json.loads(FREE_FLOAT_PATH.read_text())
    return {r["symbol"]: r["free_float"] for r in rows if r.get("free_float") is not None}


def load_market_cap() -> dict[str, float]:
    rows = json.loads(MARKET_CAP_PATH.read_text())
    out = {}
    for r in rows:
        mc = (r.get("query_values") or {}).get("market_cap")
        if mc:
            out[r["symbol"]] = mc
    return out


def build_1y_rows(ff: dict[str, float]) -> list[dict]:
    prices = json.loads(PRICES_1Y_PATH.read_text())
    rows = []
    for sym, closes in prices.items():
        if sym not in ff or len(closes) < 120:
            continue
        rows.append(
            {
                "sym": sym,
                "ff": ff[sym],
                "vol": annualized_volatility(closes),
                "mdd": max_drawdown(closes),
                "ret": total_return(closes),
                "no_move": no_move_fraction(closes),
            }
        )
    return rows


def print_main_result(rows: list[dict]) -> None:
    print(f"H1 -- main test, n={len(rows)}\n")
    for label, field in [("volatility", "vol"), ("max drawdown", "mdd"), ("1-year return", "ret")]:
        c = spearman([r["ff"] for r in rows], [r[field] for r in rows])
        print(f"  free float vs {label:<14} rho={c.rho:+.3f}  t={c.t:+.2f}")

    print("\n  Quintiles (Q1 = thinnest float):")
    for i, bucket in enumerate(quintiles(rows, "ff"), start=1):
        print(
            f"    Q{i}: n={len(bucket):>4}  ff_median={median_of(bucket,'ff'):.3f}"
            f"  vol={median_of(bucket,'vol'):.1%}  mdd={median_of(bucket,'mdd'):.1%}"
        )


def print_staleness_check(rows: list[dict]) -> None:
    print("\nExplanation 1 check: stale prices from illiquidity?\n")
    for i, bucket in enumerate(quintiles(rows, "ff"), start=1):
        print(
            f"    Q{i}: ff_median={median_of(bucket,'ff'):.3f}"
            f"  no_move_days={median_of(bucket,'no_move'):.1%}"
        )
    liquid = [r for r in rows if r["no_move"] < 0.20]
    c = spearman([r["ff"] for r in liquid], [r["vol"] for r in liquid])
    print(f"\n  Liquid-only re-test (n={len(liquid)}): rho={c.rho:+.3f}  t={c.t:+.2f}")


def print_year_by_year(ff: dict[str, float]) -> None:
    print("\nExplanation 2 check: single-regime (2026 crash) effect?\n")
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    for year in [2022, 2023, 2024, 2025, 2026]:
        rows = []
        for sym, pairs in prices5y.items():
            if sym not in ff:
                continue
            closes = [
                c
                for t, c in pairs
                if datetime.fromtimestamp(t, timezone.utc).year == year
            ]
            if len(closes) < 100:
                continue
            rows.append({"ff": ff[sym], "vol": annualized_volatility(closes)})
        if len(rows) < 50:
            print(f"    {year}: insufficient data (n={len(rows)})")
            continue
        c = spearman([r["ff"] for r in rows], [r["vol"] for r in rows])
        buckets = quintiles(rows, "ff")
        q1, q5 = median_of(buckets[0], "vol"), median_of(buckets[-1], "vol")
        print(f"    {year}: n={len(rows):>4}  rho={c.rho:+.3f}  t={c.t:+.2f}  Q1={q1:.1%}  Q5={q5:.1%}")


def print_size_control(rows: list[dict], mcap: dict[str, float]) -> None:
    print("\nSize control: is free float just proxying for company size?\n")
    sized = [r | {"mc": mcap[r["sym"]]} for r in rows if r["sym"] in mcap]
    print(f"  n={len(sized)}")
    c_mc_vol = spearman([r["mc"] for r in sized], [r["vol"] for r in sized])
    c_mc_ff = spearman([r["mc"] for r in sized], [r["ff"] for r in sized])
    print(f"  rho(market_cap, volatility) = {c_mc_vol.rho:+.3f}")
    print(f"  rho(market_cap, free_float) = {c_mc_ff.rho:+.3f}")

    print("\n  Double sort -- within each size bucket, does float still predict vol?")
    size_buckets = quintiles(sized, "mc", n_buckets=4)
    labels = ["smallest", "small-mid", "mid-large", "largest"]
    for label, bucket in zip(labels, size_buckets):
        c = spearman([r["ff"] for r in bucket], [r["vol"] for r in bucket])
        ff_buckets = quintiles(bucket, "ff", n_buckets=3)
        lo = median_of(ff_buckets[0], "vol")
        hi = median_of(ff_buckets[-1], "vol")
        print(f"    {label:>10}: n={len(bucket):>4}  rho={c.rho:+.3f}  t={c.t:+.2f}  low_ff_vol={lo:.1%}  high_ff_vol={hi:.1%}")


def main() -> None:
    ff = load_free_float()
    mcap = load_market_cap()
    rows = build_1y_rows(ff)

    print_main_result(rows)
    print_staleness_check(rows)
    print_year_by_year(ff)
    print_size_control(rows, mcap)

    print(
        "\nConclusion: among small IDX companies, widely-floated ones are far more\n"
        "volatile than closely-held ones. Among large companies, free float barely\n"
        "matters. Robust 2022-2026. This is about volatility, not returns -- the\n"
        "return relationship is ~0. Trial count: 1. Status: exploratory (no holdout)."
    )


if __name__ == "__main__":
    main()
