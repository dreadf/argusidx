"""
Phase 1 C2: the full universe sweep. Pulls every snapshot field the
product's Stock lookup needs, plus yearly 2021-2025 fields for hypothesis
testing (predictor-before-outcome rule -- see docs/DATA.md), in one
paginated query.

De-risked by prior calls (docs/credit_ledger.md, 2026-09-07 and 2026-09-12):
  - phase1_shape_probe.py confirmed yearly keys are flat and a permissive
    `field is not null or market_cap > 0` filter excludes zero rows.
  - phase1_full_query_test.py confirmed the full combined where clause
    (field list in pipeline/hypotheses/_universe_fields.py, extended
    2026-09-12 with industry/sub_industry/price-bands/earnings[YYYY])
    returns every expected field with total_count=962 (no field-group
    fallback needed -- avoids the ~30-35 credit worst case).

Cost: ~5 credits (962 companies / 200 per page = 5 pages, 1 credit/page,
per every prior /v2/companies/ call in docs/credit_ledger.md) --
unchanged by the 2026-09-12 field-list expansion, since cost is per
page, not per field (same query shape, more fields requested per row).

Run only after explicit go-ahead:
    python -m pipeline.hypotheses.phase1_universe_sweep
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pipeline.hypotheses._universe_fields import SNAPSHOT_NULL_CHECK, SNAPSHOT_STR, YEARLY, build_where
from pipeline.sectors_client import paginate

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "raw" / f"universe_{date.today()}.json"
FREE_FLOAT_PATH = REPO_ROOT / "data" / "raw" / "free_float_2026-09-06.json"


def main() -> None:
    params = {
        "where": build_where(),
        "order_by": "-market_cap",
        "include_query_values": "true",
    }
    print("Pulling full universe (~5 pages, ~5 credits)...")
    results = paginate("/companies/", params, page_size=200)
    print(f"Got {len(results)} companies.")

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved to {OUT_PATH}")

    # Cross-check against the purchased free_float file, per the plan's
    # verification step -- a material disagreement is itself a finding.
    purchased_ff = {
        row["symbol"]: row["free_float"]
        for row in json.loads(FREE_FLOAT_PATH.read_text())
        if row.get("free_float") is not None
    }
    swept_ff = {
        row["symbol"]: row.get("query_values", {}).get("free_float")
        for row in results
        if row.get("query_values", {}).get("free_float") is not None
    }
    common = set(purchased_ff) & set(swept_ff)
    diffs = [
        (sym, purchased_ff[sym], swept_ff[sym])
        for sym in common
        if abs(purchased_ff[sym] - swept_ff[sym]) > 1e-6
    ]
    print(f"\nCross-check vs purchased free_float_2026-09-06.json: "
          f"{len(common)} symbols in common, {len(diffs)} disagree by >1e-6")
    if diffs:
        print("Sample disagreements:", diffs[:5])

    # Quick coverage summary, since "how many companies have field X" is
    # exactly what determines whether H4/H5 are viable.
    print("\nField coverage (non-null count out of", len(results), "companies):")
    for f in SNAPSHOT_NULL_CHECK + SNAPSHOT_STR:
        n = sum(1 for r in results if r.get("query_values", {}).get(f) is not None)
        print(f"  {f:20s} {n:4d}")
    for f in YEARLY:
        n2024 = sum(1 for r in results if r.get("query_values", {}).get(f"{f}[2024]") is not None)
        print(f"  {f + '[2024]':20s} {n2024:4d}")


if __name__ == "__main__":
    main()
