"""
Base rate (item I7): the typical 1-year drawdown, by IDX sector.

NOT a falsifiable hypothesis -- descriptive, no split, no significance test, not
counted in the trial counter. Definitions frozen in EXPERIMENT.md
("Pre-registration, 2026-09-26 (batch 2)"); run once.

Same method as `m_typical_drawdown` (imported helpers, unchanged): 1-year cache
`close`, one `stats.max_drawdown` per stock with at least 120 usable bars,
grouped by the universe field `sector` instead of size tercile. Per sector:
n, 25th percentile, median, 75th percentile, and the share with a drawdown of
at least 30%. Sectors with fewer than 15 stocks are marked "too few" (numbers
withheld). `sector` is a current snapshot used only as a descriptive grouping.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_typical_drawdown_by_sector
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.hypotheses.m_typical_drawdown import MIN_TRADING_DAYS, _percentiles
from pipeline.stats import max_drawdown

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_1Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_1y.json"

MIN_GROUP = 15
DEEP = -0.30  # a drawdown of at least 30%


def build_rows(prices1y: dict, universe: list[dict]) -> list[dict]:
    sector_of = {r.get("symbol"): (r.get("query_values") or {}).get("sector") for r in universe}
    rows = []
    for sym, entry in prices1y.items():
        sector = sector_of.get(sym)
        closes = [c for c in entry.get("close", []) if c is not None and c > 0]
        if sector is None or len(closes) < MIN_TRADING_DAYS:
            continue
        rows.append({"sym": sym, "sector": sector, "mdd": max_drawdown(closes)})
    return rows


def summarize_group(rows: list[dict]) -> dict:
    n = len(rows)
    if n < MIN_GROUP:
        return {"n": n, "too_few": True}
    p25, p50, p75 = _percentiles([r["mdd"] for r in rows])
    return {
        "n": n,
        "too_few": False,
        "p25": p25,
        "median": p50,
        "p75": p75,
        "share_drawdown_30_or_worse": sum(1 for r in rows if r["mdd"] <= DEEP) / n,
    }


def build_by_sector(prices1y: dict, universe: list[dict]) -> dict:
    rows = build_rows(prices1y, universe)
    sectors = sorted({r["sector"] for r in rows})
    return {
        "n_stocks": len(rows),
        "by_sector": {s: summarize_group([r for r in rows if r["sector"] == s]) for s in sectors},
    }


def main() -> None:
    out = build_by_sector(json.loads(PRICES_1Y_PATH.read_text()), json.loads(UNIVERSE_PATH.read_text()))
    print(f"Typical 1-year drawdown by sector -- {out['n_stocks']} stocks with >= {MIN_TRADING_DAYS} bars")
    for sector, g in out["by_sector"].items():
        if g["too_few"]:
            print(f"  {sector:<28}: n={g['n']:>4}  too few")
        else:
            print(
                f"  {sector:<28}: n={g['n']:>4}  25th={g['p25']:+.1%}  median={g['median']:+.1%}  "
                f"75th={g['p75']:+.1%}  drawdown>=30%: {g['share_drawdown_30_or_worse']:.1%}"
            )


if __name__ == "__main__":
    main()
