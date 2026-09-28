"""R3: sector-neutral, size-controlled snapshot, 2025-12-30 -> 2026-06-30.

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-28: R3 and R4")
before this module was run. NOT a trial: one realized outcome per stock,
not a repeated-sampling statistic. Labelled "satu kejadian, bukan uji" on
Sektor, per the plan (`kind-juggling-hoare.md` §5).

Feeds the Sektor section on Pasar.

Run:
    .venv/bin/python -m pipeline.hypotheses.r3_sector_size_snapshot
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.appdata.common import REPO_ROOT
from pipeline.stats import median_of, quintiles, sector_neutral_rank

CLOSES_PATH = REPO_ROOT / "data" / "raw" / "sectors_daily_close_m6_2026-09-28.json"
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-12.json"
DATE_START = "2025-12-30"
DATE_END = "2026-06-30"


def _closes_by_symbol(closes: dict, date: str) -> dict[str, float]:
    entry = closes[date]
    out: dict[str, float] = {}
    for page in entry["pages"].values():
        for row in page:
            sym = row.get("symbol")
            close = row.get("close")
            if sym is not None and close is not None:
                out[sym] = close
    return out


def build_rows(closes: dict, universe: list[dict]) -> list[dict]:
    """One row per symbol present on both dates and in the universe sweep,
    with `sub_sector`, `size` (outstanding_shares[2025] * close at start)
    and `ret` (raw return over the window)."""
    start_prices = _closes_by_symbol(closes, DATE_START)
    end_prices = _closes_by_symbol(closes, DATE_END)
    by_symbol = {r["symbol"]: r for r in universe}

    rows = []
    for sym, p0 in start_prices.items():
        p1 = end_prices.get(sym)
        u = by_symbol.get(sym)
        if p1 is None or u is None or p0 <= 0:
            continue
        qv = u.get("query_values") or {}
        sub_sector = qv.get("sub_sector")
        shares = qv.get("outstanding_shares[2025]")
        if sub_sector is None or shares is None or shares <= 0:
            continue
        rows.append(
            {
                "sym": sym,
                "sub_sector": sub_sector,
                "size": shares * p0,
                "ret": p1 / p0 - 1,
            }
        )
    return rows


def main() -> None:
    closes = json.loads(CLOSES_PATH.read_text())
    universe = json.loads(UNIVERSE_PATH.read_text())

    rows = build_rows(closes, universe)
    print(f"R3: {DATE_START} -> {DATE_END}, {len(rows)} stocks with a return and a known sub_sector/size.")

    ranked = sector_neutral_rank(rows, "ret", "sub_sector")
    print(f"Sector-neutral rank computed for {len(ranked)} of {len(rows)} rows.")

    print("\nSize terciles (T1=smallest, T3=largest), sector-neutral return rank:")
    for i, bucket in enumerate(quintiles(ranked, "size", n_buckets=3), start=1):
        n = len(bucket)
        rank_median = median_of(bucket, "ret_rank") if n else float("nan")
        ret_median = median_of(bucket, "ret") if n else float("nan")
        print(f"  T{i}: n={n:>4}  size_median={median_of(bucket, 'size'):,.0f}  ret_rank_median={rank_median:.3f}  raw_ret_median={ret_median:+.1%}")

    top10 = sorted(ranked, key=lambda r: r["ret_rank"], reverse=True)[:10]
    bottom10 = sorted(ranked, key=lambda r: r["ret_rank"])[:10]
    print("\nTop 10 sector-adjusted movers:")
    for r in top10:
        print(f"  {r['sym']:6s} {r['sub_sector']:35s} rank={r['ret_rank']:.3f}  raw_ret={r['ret']:+.1%}")
    print("\nBottom 10 sector-adjusted movers:")
    for r in bottom10:
        print(f"  {r['sym']:6s} {r['sub_sector']:35s} rank={r['ret_rank']:.3f}  raw_ret={r['ret']:+.1%}")


if __name__ == "__main__":
    main()
