"""Build data/app/roe_history.json: return on equity by year for every
stock, and the median for each sector by year, from the purchased universe
sweep (`roe[YYYY]` yearly fields). Pure aggregation, no model.

The stock page draws a stock's own line against its sector's median line.
Only companies that report a value in a given year count toward that
year's sector median, and the count is kept so the page can say how many
reported (docs/PRODUCT.md §0 rule 3: never a number without its comparison).

Run: .venv/bin/python -m pipeline.appdata.build_roe_history
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file

YEARS = [2021, 2022, 2023, 2024, 2025]


def roe_percent(qv: dict, year: int) -> float | None:
    """`roe[YYYY]` ships as a ratio (0.2043); the app shows percent."""
    value = qv.get(f"roe[{year}]")
    return None if value is None else round(value * 100, 2)


def build(rows: list[dict]) -> dict:
    by_symbol: dict[str, list[float | None]] = {}
    per_sector_year: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        qv = row["query_values"]
        values = [roe_percent(qv, y) for y in YEARS]
        by_symbol[row["symbol"]] = values
        sector = qv.get("sector")
        if sector is None:
            continue
        for year, v in zip(YEARS, values):
            if v is not None:
                per_sector_year[sector][year].append(v)
    sectors = {
        sector: {
            "median": [round(statistics.median(per_year[y]), 2) if per_year[y] else None for y in YEARS],
            "n": [len(per_year[y]) for y in YEARS],
        }
        for sector, per_year in per_sector_year.items()
    }
    return {"years": YEARS, "sectors": sectors, "by_symbol": by_symbol}


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    rows = json.loads(universe_path.read_text())
    out = {"as_of": universe_path.stem.replace("universe_", ""), "source_file": universe_path.name, **build(rows)}
    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "roe_history.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False))
    print(f"Wrote {out_path} ({len(out['by_symbol'])} stocks, {len(out['sectors'])} sectors)")
    fin = out["sectors"].get("Financials")
    if fin:
        print("Financials median ROE by year:", fin["median"], "n:", fin["n"])


if __name__ == "__main__":
    main()
