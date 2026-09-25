"""Build data/app/commodity_context.json from the purchased commodity
price history (data/raw/commodity_prices_*.json, pipeline/appdata/
fetch_commodity_prices.py).

Gives the extractive lens a dated, descriptive fact per commodity: where
its price sits in the fetched range and how it moved over the last 12
months of the series. Deliberately NOT a comparison against the miners'
current share prices: verified 2026-09-20 that the API's series for coal,
nickel and copper end 2026-02-15 while gold ends 2026-09-01, so a
side-by-side with today's prices would compare different time windows.
The latest date is carried through so every screen can print it.

Run: .venv/bin/python -m pipeline.appdata.build_commodity_context
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from pipeline.appdata.common import APP_DIR, COMMODITY_PRICES_GLOB, RAW_DIR, latest_dated_file, position_in_range

YEAR_BACK_TOLERANCE_DAYS = 45


def _nearest_point(points: list[dict], target: date, tolerance_days: int) -> dict | None:
    best = None
    best_gap = None
    for p in points:
        gap = abs((date.fromisoformat(p["date"]) - target).days)
        if gap <= tolerance_days and (best_gap is None or gap < best_gap):
            best, best_gap = p, gap
    return best


def build_commodity(records: list[dict]) -> dict | None:
    points = sorted(
        ({"date": r["date"], "price": r["price_usd_per_ton"]} for r in records if r.get("price_usd_per_ton") is not None),
        key=lambda p: p["date"],
    )
    if not points:
        return None
    latest = points[-1]
    prices = [p["price"] for p in points]
    low, high = min(prices), max(prices)

    year_ago = _nearest_point(
        points[:-1], date.fromisoformat(latest["date"]) - timedelta(days=365), YEAR_BACK_TOLERANCE_DAYS
    )
    change_12m_pct = None
    if year_ago is not None and year_ago["price"] > 0:
        change_12m_pct = (latest["price"] / year_ago["price"] - 1) * 100

    return {
        "latest_date": latest["date"],
        "latest_price": latest["price"],
        "year_ago_date": year_ago["date"] if year_ago else None,
        "change_12m_pct": change_12m_pct,
        "range_start": points[0]["date"],
        "range_low": low,
        "range_high": high,
        "position_in_range": position_in_range(low, high, latest["price"]),
        "n_points": len(points),
    }


def build_commodity_context(raw: dict[str, list[dict]]) -> dict[str, dict]:
    result = {}
    for name, records in raw.items():
        built = build_commodity(records)
        if built is not None:
            result[name] = built
    return result


def main() -> None:
    source_path = latest_dated_file(RAW_DIR, COMMODITY_PRICES_GLOB)
    as_of = source_path.stem.replace("commodity_prices_", "")
    raw = json.loads(source_path.read_text())

    output = {"as_of": as_of, "source_file": source_path.name, "commodities": build_commodity_context(raw)}

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "commodity_context.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {source_path.name}")
    for name, c in output["commodities"].items():
        chg = f"{c['change_12m_pct']:+.1f}%" if c["change_12m_pct"] is not None else "n/a"
        print(f"  {name:8s} latest {c['latest_date']}  12m {chg}  position {c['position_in_range']}")


if __name__ == "__main__":
    main()
