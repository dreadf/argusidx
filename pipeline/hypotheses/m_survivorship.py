"""
Count (item P3, survivorship): how many companies can the base rates not see?

NOT a hypothesis -- descriptive counts from owned data, no outcome, not counted
in the trial counter. Definitions frozen in EXPERIMENT.md ("Pre-registration,
2026-09-26 (batch 2)"); run once.

- Delisting events: suspensions whose `reason` mentions `delisting`,
  `penghapusan pencatatan` or `go private` (case-insensitive substring).
- Distinct symbols among them, and how many of those symbols are absent from the
  universe file (i.e. no longer a current company in the owned sweep).
- Universe companies missing from the 5-year price cache (the cache the base
  rates use); the 1-year cache figure is printed beside it.
- Limits: the suspensions file only lists suspensions, so a company that was
  delisted without an event matching these words is not counted; the counts are
  a floor on what the base rates cannot see, not a full census.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_survivorship
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
PRICES_1Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_1y.json"

DELISTING_KEYWORDS = ("delisting", "penghapusan pencatatan", "go private")


def is_delisting_reason(reason: str | None) -> bool:
    text = (reason or "").lower()
    return any(k in text for k in DELISTING_KEYWORDS)


def build_survivorship(suspensions: list[dict], universe: list[dict], prices_5y: dict, prices_1y: dict) -> dict:
    events = [s for s in suspensions if s.get("symbol") and is_delisting_reason(s.get("reason"))]
    symbols = sorted({s["symbol"] for s in events})
    universe_symbols = {r.get("symbol") for r in universe}
    absent = [s for s in symbols if s not in universe_symbols]
    return {
        "delisting_events": len(events),
        "distinct_symbols": len(symbols),
        "symbols_absent_from_universe": len(absent),
        "absent_symbols": absent,
        "universe_companies": len(universe_symbols),
        "universe_missing_from_5y_cache": len(universe_symbols - set(prices_5y)),
        "universe_missing_from_1y_cache": len(universe_symbols - set(prices_1y)),
        "cache_5y_size": len(prices_5y),
    }


def main() -> None:
    out = build_survivorship(
        json.loads(SUSPENSIONS_PATH.read_text()),
        json.loads(UNIVERSE_PATH.read_text()),
        json.loads(PRICES_5Y_PATH.read_text()),
        json.loads(PRICES_1Y_PATH.read_text()),
    )
    for k, v in out.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
