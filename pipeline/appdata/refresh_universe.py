"""Re-sweep /v2/companies/ with the lens/flag fields added (docs/PRODUCT.md
§6, §9, §18).

Adds to the existing 48-field universe sweep: `indices` (LQ45 anomaly
flag), Banking-lens ratios, Insurance-lens premium fields — all confirmed
present in the live Sectors schema this session but absent from the one
sweep already owned (`data/raw/universe_2026-09-12.json`), because that
sweep's field list was never told to ask for them.

Cost: ~5-6 credits (962 companies / 200 per page = 5 pages, same
per-page rate as every prior /v2/companies/ sweep — cost is per page,
not per field). Approved: user's standing "<=20 credits, no need to ask
each time" rule (this session, 2026-09-12) + explicit go-ahead from the
hypothesis-testing session for this exact call (2026-09-13: "Go ahead
independently — good time, no conflict").

Never overwrites an existing dated file (docs/PRODUCT.md §18's safety
rule) — refuses if today's file already exists.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.refresh_universe
"""
from __future__ import annotations

import json
from datetime import date

from pipeline.appdata.common import REPO_ROOT
from pipeline.appdata.lens_fields import (
    BANKING_YEARLY,
    INSURANCE_YEARLY,
    YEARS,
    build_where,
)
from pipeline.sectors_client import paginate

OUT_PATH = REPO_ROOT / "data" / "raw" / f"universe_{date.today()}.json"


def main() -> None:
    if OUT_PATH.exists():
        raise FileExistsError(
            f"{OUT_PATH} already exists — refusing to overwrite purchased data. "
            "Delete it first if you really mean to re-fetch today's sweep."
        )

    params = {
        "where": build_where(),
        "order_by": "-market_cap",
        "include_query_values": "true",
    }
    print("Pulling universe with lens/flag fields added (~5-6 pages, ~5-6 credits)...")
    results = paginate("/companies/", params, page_size=200)
    print(f"Got {len(results)} companies.")

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved to {OUT_PATH}")

    print("\nNew-field coverage (non-null count out of", len(results), "companies):")
    n_indices = sum(1 for r in results if r.get("query_values", {}).get("indices") is not None)
    print(f"  {'indices':28s} {n_indices:4d}")
    for f in BANKING_YEARLY + INSURANCE_YEARLY:
        n2025 = sum(1 for r in results if r.get("query_values", {}).get(f"{f}[2025]") is not None)
        print(f"  {f + '[2025]':28s} {n2025:4d}")

    # Magnitude sanity check for the insurance fields the other session
    # flagged as a per-share/total unit-mismatch risk — print a few real
    # values rather than trusting the schema doc's silence on units.
    insurers = [
        r for r in results
        if r.get("query_values", {}).get("premium_income[2025]") is not None
    ][:3]
    if insurers:
        print("\nInsurance field magnitude spot-check (raw values, not yet trusted):")
        for r in insurers:
            qv = r["query_values"]
            print(
                f"  {r['symbol']:10s} premium_income[2025]={qv.get('premium_income[2025]')!r} "
                f"premium_expense[2025]={qv.get('premium_expense[2025]')!r} "
                f"total_equity-scale field market_cap={qv.get('market_cap')!r}"
            )


if __name__ == "__main__":
    main()
