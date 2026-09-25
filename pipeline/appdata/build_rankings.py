"""Build data/app/rankings.json from the purchased universe sweep.

Three of four rankings (docs/PRODUCT.md §5): furthest below 52-week high,
lowest free float, biggest market-cap change (increase/decrease, kept as
two separate lists - never merged into one "most changed", per the plan).
Beat gold needs the other session's 5-year-return research and lands
separately - not stubbed here with placeholder numbers.

Run: .venv/bin/python -m pipeline.appdata.build_rankings
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file


def build_furthest_below_52w_high(rows: list[dict]) -> list[dict]:
    results = []
    excluded = 0
    for row in rows:
        qv = row["query_values"]
        high = qv.get("52_w_high_price")
        current = qv.get("last_close_price")
        if high is None or current is None or high == 0:
            excluded += 1
            continue
        pct_below_high = (current - high) / high
        results.append({
            "symbol": row["symbol"],
            "company_name": row["company_name"],
            "pct_below_high": pct_below_high,
        })
    # Ties broken alphabetically by ticker (docs/PRODUCT.md §5).
    results.sort(key=lambda r: (r["pct_below_high"], r["symbol"]))
    return results


def build_lowest_free_float(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows:
        free_float = row["query_values"].get("free_float")
        if free_float is None:
            continue
        results.append({
            "symbol": row["symbol"],
            "company_name": row["company_name"],
            "free_float": free_float,
        })
    results.sort(key=lambda r: (r["free_float"], r["symbol"]))
    return results


def build_mcap_change(rows: list[dict]) -> dict:
    results = []
    for row in rows:
        change = row["query_values"].get("yearly_mcap_change")
        if change is None:
            continue
        results.append({
            "symbol": row["symbol"],
            "company_name": row["company_name"],
            "yearly_mcap_change": change,
        })
    increases = sorted(results, key=lambda r: (-r["yearly_mcap_change"], r["symbol"]))
    decreases = sorted(results, key=lambda r: (r["yearly_mcap_change"], r["symbol"]))
    return {"increases": increases, "decreases": decreases, "evaluable_count": len(results)}


def build_biggest_daily_moves(rows: list[dict]) -> list[dict]:
    """Largest one-day price changes by absolute size, up and down mixed in
    one list. Sorted by magnitude only: a neutral "moved most today", never
    "best" or "worst" (docs/PRODUCT.md §2 Rankings). Ties by ticker."""
    results = []
    for row in rows:
        change = row["query_values"].get("daily_close_change")
        if change is None:
            continue
        results.append({
            "symbol": row["symbol"],
            "company_name": row["company_name"],
            "daily_close_change": change,
        })
    results.sort(key=lambda r: (-abs(r["daily_close_change"]), r["symbol"]))
    return results[:100]


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())

    furthest_below_high = build_furthest_below_52w_high(rows)
    lowest_free_float = build_lowest_free_float(rows)
    mcap_change = build_mcap_change(rows)
    biggest_daily_moves = build_biggest_daily_moves(rows)

    rankings = {
        "as_of": as_of,
        "source_file": universe_path.name,
        "furthest_below_52w_high": furthest_below_high,
        "lowest_free_float": lowest_free_float,
        "mcap_change": mcap_change,
        "biggest_daily_moves": biggest_daily_moves,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "rankings.json"
    out_path.write_text(json.dumps(rankings, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {universe_path.name} (as_of {as_of})")
    print(f"furthest_below_52w_high: {len(furthest_below_high)} eligible")
    for r in furthest_below_high[:5]:
        print(f"  {r['symbol']:12s} {r['pct_below_high']*100:.0f}%  {r['company_name']}")
    print(f"lowest_free_float: {len(lowest_free_float)} eligible")
    for r in lowest_free_float[:5]:
        print(f"  {r['symbol']:12s} {r['free_float']*100:.1f}%  {r['company_name']}")
    print(f"mcap_change: {mcap_change['evaluable_count']} eligible")
    for r in mcap_change["increases"][:5]:
        print(f"  +{r['symbol']:12s} {r['yearly_mcap_change']*100:+.0f}%  {r['company_name']}")
    for r in mcap_change["decreases"][:5]:
        print(f"  -{r['symbol']:12s} {r['yearly_mcap_change']*100:+.0f}%  {r['company_name']}")


if __name__ == "__main__":
    main()
