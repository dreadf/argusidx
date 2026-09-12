"""
Phase 1 shape probe (Stage C1): two small, separately-billed questions
that must be answered before the full Phase 1 sweep, per docs/PLAN.md
3.2 ("no Sectors call without stating cost and waiting for explicit
approval") -- approved for this session as part of Stage C.

Q1 -- key format: does a yearly bracket-notation field (`pe[2024]`)
     reach `query_values` flat (`"pe[2024]": ...`) or nested
     (`{"pe": {"2024": ...}}`)? Neither the schema nor Phase 0 answers
     this -- Phase 0 only tested snapshot fields.
Q2 -- permissive filtering: Phase 0 found `pe_ttm > 0 and roe_ttm > 0`
     alone drops the result set to total_count=604 of ~961. A field only
     reaches query_values if referenced in where/order_by, but every
     where condition also filters -- so Phase 1's full field list can't
     just `and` everything together without losing most of the universe.
     Does `field > 0 OR market_cap > 0` reference the field for
     query_values purposes while keeping the OR's permissive branch from
     excluding rows lacking it?

Each call ~1 credit (docs/credit_ledger.md's prior /v2/companies/ calls
all billed 1/query regardless of field count). Run only after explicit
go-ahead -- see the session's plan file for the approval this executed
under.

Run:
    python -m pipeline.hypotheses.phase1_shape_probe
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pipeline.sectors_client import get

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "raw" / f"phase1_shape_probe_{date.today()}.json"

Q1_PARAMS = {
    "where": "pe[2024] is not null",
    "order_by": "-market_cap",
    "limit": "3",
    "include_query_values": "true",
}

Q2_PARAMS = {
    "where": "pe_ttm > 0 or market_cap > 0",
    "order_by": "-market_cap",
    "limit": "5",
    "include_query_values": "true",
}


def main() -> None:
    print("Phase 1 shape probe -- 2 calls, ~1 credit each\n")

    print(f"Q1 (key format): GET /v2/companies/ params={Q1_PARAMS}")
    r1 = get("/companies/", Q1_PARAMS)
    print(json.dumps(r1, indent=2)[:2000])
    qv1 = r1.get("results", [{}])[0].get("query_values", {}) if r1.get("results") else {}
    yearly_keys = [k for k in qv1 if "2024" in k or "pe" in k.lower()]
    print(f"\n  query_values keys seen: {sorted(qv1.keys())}")
    print(f"  yearly-looking keys: {yearly_keys}")
    print(f"  total_count: {r1.get('pagination', {}).get('total_count')}")

    print(f"\nQ2 (permissive OR): GET /v2/companies/ params={Q2_PARAMS}")
    r2 = get("/companies/", Q2_PARAMS)
    print(json.dumps(r2, indent=2)[:2000])
    total2 = r2.get("pagination", {}).get("total_count")
    print(f"\n  total_count with OR (vs Phase 0's AND total_count=604): {total2}")
    has_pe_ttm = any("pe_ttm" in row.get("query_values", {}) for row in r2.get("results", []))
    print(f"  pe_ttm present in query_values for returned rows: {has_pe_ttm}")

    OUT_PATH.write_text(json.dumps({"q1_key_format": r1, "q2_permissive_or": r2}, indent=2))
    print(f"\nSaved raw responses to {OUT_PATH}")

    print(
        "\nRESULT SUMMARY (fill in after running, before Phase 1 C2 proceeds):\n"
        "  - yearly key format: flat or nested? see yearly-looking keys above\n"
        "  - does OR avoid the AND-filtering problem? compare total_count "
        "604 (Phase 0, AND) vs Q2's total_count (OR) above"
    )


if __name__ == "__main__":
    main()
