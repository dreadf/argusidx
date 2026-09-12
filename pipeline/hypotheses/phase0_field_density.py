"""
Phase 0: does one Sectors `companies` screener call return many fields at
once, or only the field(s) actually referenced in `where`/`order_by`?

STATUS: run 2026-09-06. RESULT: multi-field confirmed -- pe_ttm, roe_ttm
and market_cap all came back in query_values for every row. Billed 1
credit (docs/credit_ledger.md). Raw response saved to
data/raw/phase0_field_density_2026-09-06.json (the original curl-based
run did not persist it at the time, contrary to the standing rule in
docs/PLAN.md 3.1 -- that file transcribes the billed response verbatim
to close the gap). This module is safe to re-run (idempotent, same
query), but doing so bills again -- get explicit go-ahead first, per the
standing project rule (docs/PLAN.md 3.2).

Why this matters (docs/PLAN.md 6.2): "unresolved and decisive... a 10x
cost swing on everything below." If query_values reliably includes every
field referenced in the query (not just the one used to filter), Phase 1's
full universe sweep costs an estimated ~5-25 credits total. If not, it
could cost roughly 5 credits PER FIELD requested.

The query below references three fields across `where` and `order_by`,
confirmed to exist against the public schema (https://api.sectors.app/schema/,
fetched 2026-09-06 -- not from search results, which describe the dead v1):
    pe_ttm      -- valuation (price-to-earnings, trailing twelve months)
    roe_ttm     -- profitability (return on equity, trailing twelve months)
    market_cap  -- used for order_by, and itself a Phase-1 candidate field

The schema's own example response for this endpoint already shows
query_values containing two fields at once when both are referenced
(sub_sector from `where`, market_cap from `order_by`) -- but that is
documentation, not a live result, and the previous ad hoc test of this
same endpoint (logged in docs/credit_ledger.md) found query_values held
only the one field used in `where`. This call exists to find out which
is true for a query that deliberately references more than one field
across both clauses.

Cost: ~1 credit, based on every prior `/v2/companies/` call in
docs/credit_ledger.md billing 1 credit per query/page regardless of
field count. Confirmed against the actual response before being written
to the ledger.

Run only after explicit go-ahead:
    python -m pipeline.hypotheses.phase0_field_density
"""
from __future__ import annotations

import json

from pipeline.sectors_client import get

QUERY_PARAMS = {
    "where": "pe_ttm > 0 and roe_ttm > 0",
    "order_by": "-market_cap",
    "limit": "5",
    "include_query_values": "true",
}


def main() -> None:
    print("Phase 0: field-density test")
    print(f"  GET /v2/companies/ params={QUERY_PARAMS}")
    print("  Estimated cost: ~1 credit (see module docstring)\n")

    response = get("/companies/", QUERY_PARAMS)

    print(json.dumps(response, indent=2)[:3000])

    results = response.get("results", [])
    if not results:
        print("\nNo results returned -- can't assess field density.")
        return

    query_values_keys = set()
    for row in results:
        query_values_keys |= set(row.get("query_values", {}).keys())

    requested_fields = {"pe_ttm", "roe_ttm", "market_cap"}
    found = query_values_keys & requested_fields
    missing = requested_fields - query_values_keys

    print(f"\nRequested fields (across where/order_by): {sorted(requested_fields)}")
    print(f"Fields present in query_values:            {sorted(query_values_keys)}")

    if found == requested_fields:
        print(
            "\nRESULT: multi-field confirmed. query_values returned every "
            "field referenced in the query. Phase 1's full universe sweep "
            "should cost roughly the per-page rate, not per-field."
        )
    elif found:
        print(
            f"\nRESULT: partial. Only {sorted(found)} came back; "
            f"{sorted(missing)} did not. Needs a closer look before "
            "costing Phase 1."
        )
    else:
        print(
            "\nRESULT: single-field only. query_values did not include "
            "any of the requested fields beyond what a single `where` "
            "clause would have produced alone. Phase 1 should be costed "
            "per field, not per query."
        )


if __name__ == "__main__":
    main()
