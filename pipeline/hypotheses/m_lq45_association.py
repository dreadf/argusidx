"""
Association (item I8, "LQ45 lebih aman?"): are LQ45 members' 1-year price
records different from those of similarly large non-members?

CONTEMPORANEOUS ASSOCIATION ONLY, like H1 -- never a prediction and never a
claim that index membership makes a stock safer. Descriptive, no significance
test, not counted in the trial counter. Definitions frozen in EXPERIMENT.md
("Pre-registration, 2026-09-26 (batch 2)"); run once.

- Members: universe rows whose `indices` is a list containing "LQ45"
  (expected 45, the index's size). Non-members: the 45 largest by `market_cap`
  among the rest (a size-matched comparison). `indices` and `market_cap` are
  current snapshots, so nothing here can say what membership or size did to a
  stock over the year.
- Both groups are taken from the universe FIRST; a stock without 120+ usable
  bars in the 1-year cache is then dropped and counted, so n can fall below 45.
- Per group, over the 1-year cache `close`: median `stats.max_drawdown`, median
  `stats.annualized_volatility`, and the share with a drawdown of at least 30%.
- Assumption: a stock whose `indices` is null is treated as a non-member, since
  the expected 45 members are all found.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_lq45_association
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from pipeline.hypotheses.m_typical_drawdown import MIN_TRADING_DAYS
from pipeline.stats import annualized_volatility, max_drawdown

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_1Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_1y.json"

GROUP_SIZE = 45
DEEP = -0.30


def is_lq45_member(qv: dict) -> bool:
    indices = qv.get("indices")
    return isinstance(indices, list) and "LQ45" in indices


def select_groups(universe: list[dict]) -> tuple[list[str], list[str]]:
    """(members, the 45 largest non-members by market_cap; rows without market_cap are skipped)."""
    members = sorted(r["symbol"] for r in universe if is_lq45_member(r.get("query_values") or {}))
    non = [
        (r["query_values"]["market_cap"], r["symbol"])
        for r in universe
        if not is_lq45_member(r.get("query_values") or {}) and (r.get("query_values") or {}).get("market_cap") is not None
    ]
    non.sort(key=lambda t: (-t[0], t[1]))
    return members, [s for _, s in non[:GROUP_SIZE]]


def summarize(symbols: list[str], prices1y: dict) -> dict:
    mdds, vols = [], []
    for s in symbols:
        closes = [c for c in (prices1y.get(s) or {}).get("close", []) if c is not None and c > 0]
        if len(closes) < MIN_TRADING_DAYS:
            continue
        mdds.append(max_drawdown(closes))
        vols.append(annualized_volatility(closes))
    n = len(mdds)
    return {
        "selected": len(symbols),
        "n": n,
        "dropped_no_history": len(symbols) - n,
        "median_max_drawdown": statistics.median(mdds) if n else float("nan"),
        "median_annualized_volatility": statistics.median(vols) if n else float("nan"),
        "share_drawdown_30_or_worse": (sum(1 for m in mdds if m <= DEEP) / n) if n else float("nan"),
    }


def build_lq45_association(universe: list[dict], prices1y: dict) -> dict:
    members, non_members = select_groups(universe)
    return {"lq45_members": summarize(members, prices1y), "largest_non_members": summarize(non_members, prices1y)}


def main() -> None:
    out = build_lq45_association(json.loads(UNIVERSE_PATH.read_text()), json.loads(PRICES_1Y_PATH.read_text()))
    for k, v in out.items():
        print(f"{k}: {v}")
    print("(Contemporaneous association only; index membership and market cap are current snapshots.)")


if __name__ == "__main__":
    main()
