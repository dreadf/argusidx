"""Build data/app/idx_total.json from the purchased daily IDX total
market-cap history (data/raw/idx_total_*.json, pipeline/appdata/
fetch_idx_total.py).

Powers Home's 4th market-condition reading (docs/PRODUCT.md §3.1,
§21) — the one reading that genuinely has years of history, so it gets
the actual line/area chart (`components/viz/trend-chart.tsx`, built
2026-09-13 but never wired to real data until this) instead of another
stat tile. Replaces the literal "Menunggu data" placeholder that was
shipping in its place.

Run: .venv/bin/python -m pipeline.appdata.build_idx_total
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, IDX_TOTAL_GLOB, RAW_DIR, latest_dated_file


def build_idx_total(records: list[dict]) -> dict:
    series = sorted(
        ({"date": r["date"], "value": r["idx_total_market_cap"]} for r in records),
        key=lambda p: p["date"],
    )
    if not series:
        return {"series": [], "latest": None, "min": None, "max": None}
    latest = series[-1]
    min_point = min(series, key=lambda p: p["value"])
    max_point = max(series, key=lambda p: p["value"])
    return {"series": series, "latest": latest, "min": min_point, "max": max_point}


def main() -> None:
    raw_path = latest_dated_file(RAW_DIR, IDX_TOTAL_GLOB)
    records = json.loads(raw_path.read_text())
    result = build_idx_total(records)

    output = {
        "as_of": raw_path.stem.replace("idx_total_", ""),
        "source_file": raw_path.name,
        **result,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "idx_total.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {raw_path.name}")
    if result["series"]:
        print(f"  {len(result['series'])} daily points, {result['series'][0]['date']} to {result['latest']['date']}")
    else:
        print("  0 daily points (empty input - see build_idx_total()'s empty-series guard)")


if __name__ == "__main__":
    main()
