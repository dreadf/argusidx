"""
H19 -- coal price -> coal miners. STEP 1 ONLY: the power-rule count.

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 2)").
This module counts; it computes NO outcome, no return and no correlation.

- Series: owned monthly `Coal` and `Coal (HBA 1)` prices
  (`commodity_prices_*.json`, `commodity_prices_hba_*.json`).
- Usable monthly change: a price at the first of month M and a price at the
  first of month M+1, both present and positive. The owned files switch to two
  points per month (the 1st and the 15th) from 2025-03; the 15th points are
  not monthly observations and are not used for the monthly count. The count of
  all consecutive observations (mixed 1st/15th spacing) is printed beside it
  for transparency and is NOT the pre-registered quantity.
- Power rule: fewer than 24 usable monthly changes -> H19 becomes a descriptive
  chart with no verdict; 24 or more -> a test is pre-registered separately
  before any outcome is computed.
- Coal miners: entries in `mining_companies_*.json` with a non-null `symbol`
  and "Coal" among `commodity_type` (pre-registration expects 55).

Run:
    .venv/bin/python -m pipeline.hypotheses.h19_coal_miners
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COAL_PATH = REPO_ROOT / "data" / "raw" / "commodity_prices_2026-09-20.json"
HBA_PATH = REPO_ROOT / "data" / "raw" / "commodity_prices_hba_2026-09-20.json"
MINING_PATH = REPO_ROOT / "data" / "raw" / "mining_companies_2026-09-13.json"

MIN_CHANGES = 24
SERIES = ("Coal", "Coal (HBA 1)")


def _price(p: dict) -> float | None:
    v = p.get("price_usd_per_ton")
    return v if v is not None and v > 0 else None


def _ym(date_str: str) -> tuple[int, int]:
    return int(date_str[:4]), int(date_str[5:7])


def monthly_points(points: list[dict]) -> dict[tuple[int, int], float]:
    """Price at the first of each month, keyed (year, month); non-positive or missing prices are skipped."""
    out: dict[tuple[int, int], float] = {}
    for p in points:
        price = _price(p)
        if price is not None and p["date"][8:10] == "01":
            out[_ym(p["date"])] = price
    return out


def count_monthly_changes(points: list[dict]) -> int:
    """Consecutive calendar months, both present."""
    m = monthly_points(points)
    return sum(1 for (y, mo) in m if ((y + 1, 1) if mo == 12 else (y, mo + 1)) in m)


def count_consecutive_observation_changes(points: list[dict]) -> int:
    """Changes between consecutive usable observations of any date (not the pre-registered quantity)."""
    usable = [p for p in sorted(points, key=lambda p: p["date"]) if _price(p) is not None]
    return max(len(usable) - 1, 0)


def coal_miner_symbols(companies: list[dict]) -> list[str]:
    return sorted({c["symbol"] for c in companies if c.get("symbol") and "Coal" in (c.get("commodity_type") or [])})


def build_counts(coal: dict, hba: dict, companies: list[dict]) -> dict:
    series = {"Coal": coal["Coal"], "Coal (HBA 1)": hba["Coal (HBA 1)"]}
    per_series = {}
    for name, pts in series.items():
        per_series[name] = {
            "points_total": len(pts),
            "first_of_month_points": len(monthly_points(pts)),
            "usable_monthly_changes": count_monthly_changes(pts),
            "consecutive_observation_changes_all_dates": count_consecutive_observation_changes(pts),
        }
    symbols = coal_miner_symbols(companies)
    return {
        "series": per_series,
        "power_rule_met_by_series": {n: s["usable_monthly_changes"] >= MIN_CHANGES for n, s in per_series.items()},
        "coal_miner_symbols": symbols,
    }


def main() -> None:
    out = build_counts(
        json.loads(COAL_PATH.read_text()),
        json.loads(HBA_PATH.read_text()),
        json.loads(MINING_PATH.read_text()),
    )
    for name, s in out["series"].items():
        print(f"{name}: {s}")
    print(f"Power rule (>= {MIN_CHANGES} usable monthly changes):", out["power_rule_met_by_series"])
    print(f"Coal-miner symbols: {len(out['coal_miner_symbols'])}")
    print(", ".join(out["coal_miner_symbols"]))
    print("(No outcome, return or correlation is computed by this module.)")


if __name__ == "__main__":
    main()
