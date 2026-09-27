"""Build data/app/market.json from the purchased universe sweep.

Day-1 scaffold (docs/PRODUCT.md §3.1, §12's Sep 13 gate). Computes the
three readings that don't need a new API call, breadth, movers,
intensity, from the existing owned data. Reading 4 (idx-total vs. its
own history) is added once /v2/idx-total/'s approved full-history fetch
has actually run (§18, §21): not before, since that data doesn't exist
yet and this module must never invent it.

Run: .venv/bin/python -m pipeline.appdata.build_market
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file, position_in_range as _position_in_range


def build_breadth(rows: list[dict]) -> dict:
    near_high = near_low = middle = excluded = 0
    for row in rows:
        qv = row["query_values"]
        pos = _position_in_range(qv.get("52_w_low_price"), qv.get("52_w_high_price"), qv.get("last_close_price"))
        if pos is None:
            excluded += 1
        elif pos >= 0.8:
            near_high += 1
        elif pos <= 0.2:
            near_low += 1
        else:
            middle += 1
    return {
        "near_high": near_high,
        "middle": middle,
        "near_low": near_low,
        "excluded": excluded,
        "total_evaluable": near_high + middle + near_low,
    }


def build_movers(rows: list[dict]) -> dict:
    up = down = flat = 0
    for row in rows:
        change = row["query_values"].get("daily_close_change")
        if change is None:
            continue
        if change > 0:
            up += 1
        elif change < 0:
            down += 1
        else:
            flat += 1
    return {"up": up, "down": down, "flat": flat}


def build_intensity(rows: list[dict]) -> dict:
    calm = moderate = choppy = 0
    for row in rows:
        change = row["query_values"].get("daily_close_change")
        if change is None:
            continue
        magnitude = abs(change)
        if magnitude >= 0.03:
            choppy += 1
        elif magnitude < 0.005:
            calm += 1
        else:
            moderate += 1
    return {"calm": calm, "moderate": moderate, "choppy": choppy}


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())

    market = {
        "as_of": as_of,
        "source_file": universe_path.name,
        "breadth": build_breadth(rows),
        "movers": build_movers(rows),
        "intensity": build_intensity(rows),
        # idx_total: intentionally absent until the approved full-history
        # fetch actually runs (docs/PRODUCT.md §18, §21): never invented.
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "market.json"
    out_path.write_text(json.dumps(market, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {universe_path.name} (as_of {as_of})")
    print(json.dumps(market, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
