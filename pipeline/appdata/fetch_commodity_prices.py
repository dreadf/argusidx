"""Pull monthly commodity price history for the four commodities with
enough listed miners to say anything about (`/v2/mining/commodities/
{name}/price/`), to give the extractive lens a real derived comparison
instead of a descriptive-only fact.

Live schema, confirmed 2026-09-20 (`https://api.sectors.app/schema/`):
- 1 credit per call, one commodity per call.
- Monthly data (bi-weekly for recent Coal), max 3 years per call.
- Valid names come from the API's own 400 error body: Coal, Nickel, Gold,
  Copper, Aluminum, Silver, Lead, Zinc, and others.

Only Coal (55 listed miners), Nickel (10), Gold (9) and Copper (4) are
pulled: commodities with 1-2 listed miners (silver, aluminium, zinc/lead)
can't support a comparison, so they aren't worth a credit each. 4 credits.

Approved: user approved the step-4 credit plan on 2026-09-20 (originally
stated as ~7 credits for all seven commodities; narrowed to 4 here).

Saves after every call and never overwrites an existing dated file.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_commodity_prices
"""
from __future__ import annotations

import json
from datetime import date

from pipeline.appdata.common import REPO_ROOT
from pipeline.sectors_client import get

COMMODITIES = ["Coal", "Nickel", "Gold", "Copper"]
START_YEAR = 2024
END_YEAR = 2026
OUT_PATH = REPO_ROOT / "data" / "raw" / f"commodity_prices_{date.today()}.json"


def main() -> None:
    if OUT_PATH.exists():
        raise FileExistsError(
            f"{OUT_PATH} already exists - refusing to overwrite purchased data. "
            "Delete it first if you really mean to re-fetch."
        )

    result: dict[str, list[dict]] = {}
    print(f"{len(COMMODITIES)} calls, {len(COMMODITIES)} credits (1 per call, approved).")
    for name in COMMODITIES:
        records = get(
            f"/mining/commodities/{name}/price/",
            {"start_year": str(START_YEAR), "end_year": str(END_YEAR)},
        )
        result[name] = records
        print(f"  {name}: {len(records)} records")
        OUT_PATH.write_text(json.dumps(result, indent=2))

    print(f"\nDone. Saved to {OUT_PATH}")
    print(f"Spent: {len(COMMODITIES)} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
