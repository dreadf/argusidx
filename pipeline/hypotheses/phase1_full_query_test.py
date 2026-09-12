"""
Phase 1 C2 pre-flight: does the FULL combined field list work as one
`where` clause, or does it need to be split into groups?

Field lists live in `pipeline/hypotheses/_universe_fields.py`, shared
with phase1_universe_sweep.py -- the real sweep -- so this pre-flight
always validates exactly the query the sweep will actually run (they
used to be separate copies; see that module's docstring for why that
was a real risk, found by /code-review 2026-09-12).

A flat OR chain has no precedence ambiguity (unlike mixing `and`/`or`
without confirmed parenthesis support), and `is not null` was confirmed
valid structured-query syntax by phase1_shape_probe.py's Q1
(docs/credit_ledger.md, 2026-09-07).

Run at limit=1: ~1 credit, cheap insurance before the real 5-page sweep
(~5 more credits) that would otherwise fail the same way 5 times over.

Run:
    python -m pipeline.hypotheses.phase1_full_query_test
"""
from __future__ import annotations

import json

from pipeline.hypotheses._universe_fields import build_where, expected_fields
from pipeline.sectors_client import get


def main() -> None:
    where = build_where()
    print(f"where clause: {len(where)} chars, {where.count(' or ') + 1} conditions\n")

    params = {
        "where": where,
        "order_by": "-market_cap",
        "limit": "1",
        "include_query_values": "true",
    }
    response = get("/companies/", params)
    print(json.dumps(response, indent=2))

    if "results" in response and response["results"]:
        qv = response["results"][0].get("query_values", {})
        expected = expected_fields()
        present = set(qv.keys())
        print(f"\nExpected {len(expected)} fields; got {len(present)} in query_values")
        missing = expected - present
        if missing:
            print(f"MISSING: {sorted(missing)}")
        else:
            print("ALL expected fields present.")
        print(f"total_count: {response.get('pagination', {}).get('total_count')} (compare to ~962 full universe)")
    else:
        print("\nNo results / malformed query -- check error field above.")


if __name__ == "__main__":
    main()
