"""Pull the market-wide corporate-actions calendar (`/v2/corporate-actions/`)
for a window around today, to show dated dividend/AGM/rights-issue/split
events on each stock page.

Live schema, confirmed 2026-09-20 (`https://api.sectors.app/schema/`):
- Costs 1 credit PER REQUESTED TYPE (all 7 types = 7 credits), not per call.
  This corrects an earlier estimate of 1 credit total.
- Window is clamped to 90 days ending at `end`; `end` may be in the future.
- Rows key on `symbol`; dividend rows carry dividend_amount/dividend_yield.

Five types are requested (dividend, upcoming_dividend, agm, right_issue,
stock_split) = 5 credits. `bonus` and `warrant` are skipped: rare, and
not worth 2 more credits for a minor section.

Approved: user approved the step-4 credit plan on 2026-09-20. This file
is meant to be re-run near the final data refresh (each run writes a new
dated file), because events announced after the pull are not in it.

Never overwrites an existing dated file.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_corporate_actions
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from pipeline.appdata.common import REPO_ROOT
from pipeline.sectors_client import get

TYPES = ["dividend", "upcoming_dividend", "agm", "right_issue", "stock_split"]
DAYS_BACK = 30
DAYS_AHEAD = 30
OUT_PATH = REPO_ROOT / "data" / "raw" / f"corporate_actions_{date.today()}.json"


def main() -> None:
    if OUT_PATH.exists():
        raise FileExistsError(f"{OUT_PATH} already exists - refusing to overwrite purchased data.")

    today = date.today()
    params = {
        "start": (today - timedelta(days=DAYS_BACK)).isoformat(),
        "end": (today + timedelta(days=DAYS_AHEAD)).isoformat(),
        "type": ",".join(TYPES),
    }
    print(f"1 call, {len(TYPES)} credits (1 per requested type, approved). Window {params['start']} to {params['end']}.")
    response = get("/corporate-actions/", params)
    OUT_PATH.write_text(json.dumps(response, indent=2))
    for key in TYPES:
        print(f"  {key}: {len(response.get(key, []))} rows")
    print(f"\nSaved to {OUT_PATH}\nSpent: {len(TYPES)} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
