"""Build data/app/sector_breakdown.json from the purchased universe sweep.

Fills a real gap: an earlier planning pass sketched a per-sector
breakdown but it never landed in `docs/PRODUCT.md` or got built: the
only place "sector" appeared anywhere in the product was a single
stock's own sector name on its own page (2026-09-19 user question: "why
can't I see sector analysis in the app?").

Per sector: company count, the same price-position breadth reading
Home already shows for the whole market (reusing `build_market.
build_breadth` directly rather than re-deriving the 0.8/0.2 thresholds
a second time: "fix the class, not the instance"), and a typical ROE/
P/E computed with `pipeline.stats.median_of` (shared, common ground).

Sectors are ordered by company count, descending: NOT by any
performance metric. Sorting sectors by how well they're doing would
itself be a cross-sector ranking, which nothing else in this product
does (§0's no-verdict rule applies to sectors exactly as it does to
stocks).

Run: .venv/bin/python -m pipeline.appdata.build_sector_breakdown
"""
from __future__ import annotations

import json
from collections import defaultdict

from pipeline.appdata.build_market import build_breadth
from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file
from pipeline.stats import median_of


def group_by_sector(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        sector = row["query_values"].get("sector")
        if sector is None:
            continue  # "unknown sector" isn't a sector to report a breakdown for
        groups[sector].append(row)
    return groups


def build_sector_row(sector: str, rows: list[dict]) -> dict:
    roe_rows = [{"roe_ttm": r["query_values"]["roe_ttm"]} for r in rows if r["query_values"].get("roe_ttm") is not None]
    pe_rows = [{"pe_ttm": r["query_values"]["pe_ttm"]} for r in rows if r["query_values"].get("pe_ttm") is not None]

    return {
        "sector": sector,
        "company_count": len(rows),
        "breadth": build_breadth(rows),
        "typical_roe_pct": median_of(roe_rows, "roe_ttm") * 100 if roe_rows else None,
        "roe_n": len(roe_rows),
        "typical_pe": median_of(pe_rows, "pe_ttm") if pe_rows else None,
        "pe_n": len(pe_rows),
    }


def build_sectors(rows: list[dict]) -> list[dict]:
    groups = group_by_sector(rows)
    sector_rows = [build_sector_row(sector, rows_for_sector) for sector, rows_for_sector in groups.items()]
    # Company count, descending: never by a performance metric (see module docstring).
    sector_rows.sort(key=lambda r: r["company_count"], reverse=True)
    return sector_rows


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())

    output = {
        "as_of": as_of,
        "source_file": universe_path.name,
        "sectors": build_sectors(rows),
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "sector_breakdown.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {universe_path.name} (as_of {as_of})")
    for row in output["sectors"]:
        print(f"  {row['sector']:28s} n={row['company_count']:3d}  typical ROE={row['typical_roe_pct']}  typical P/E={row['typical_pe']}")


if __name__ == "__main__":
    main()
