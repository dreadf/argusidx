"""Pull the full IDX total-market-cap daily history from `/v2/idx-total/`
(docs/PRODUCT.md §21): replaces Home's literal "Menunggu data" stat tile
with the one real trend-over-time chart the app already has a component
for (components/viz/trend-chart.tsx, built but never wired to real data).

Live schema, confirmed 2026-09-19 (`https://api.sectors.app/schema/`):
- 1 credit per call.
- Max 90-day window per call; earliest data is 2021-01-01.
- 2021-01-01 through today is ~2,088 days -> 24 calls, ~24 credits.

Approved: user explicitly chose "Spend ~24 credits on idx-total" when
asked directly (this session, 2026-09-19): this is that spend, logged
in docs/credit_ledger.md the moment it completes, per the standing
project rule (CLAUDE.md).

Saves incrementally after every call (the same "save-as-you-go" pattern
`sectors_client.paginate()`'s docstring documents fixing after a real
lost-data incident): a crash or 429 partway through loses at most one
call's worth of days, not the whole pull, and none of it needs re-billing
since each 90-day window is a distinct, non-overlapping call.

Never overwrites an existing dated file (same rule as refresh_universe.py).

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_idx_total
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from pipeline.appdata.common import REPO_ROOT
from pipeline.sectors_client import get

EARLIEST = date(2021, 1, 1)
WINDOW_DAYS = 90
OUT_PATH = REPO_ROOT / "data" / "raw" / f"idx_total_{date.today()}.json"


def build_windows(start: date, end: date, window_days: int) -> list[tuple[date, date]]:
    windows = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=window_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def main() -> None:
    if OUT_PATH.exists():
        raise FileExistsError(
            f"{OUT_PATH} already exists: refusing to overwrite purchased data. "
            "Delete it first if you really mean to re-fetch today's pull."
        )

    today = date.today()
    windows = build_windows(EARLIEST, today, WINDOW_DAYS)
    print(f"{len(windows)} windows, ~{len(windows)} credits (1 per call, approved).")

    all_records: list[dict] = []
    for i, (start, end) in enumerate(windows, start=1):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        records = get("/idx-total/", params)
        all_records.extend(records)
        print(f"  [{i}/{len(windows)}] {start} to {end}: {len(records)} days")
        # Save after every call, not just at the end: one lost call on a
        # crash, never the whole pull.
        OUT_PATH.write_text(json.dumps(all_records, indent=2))

    print(f"\nDone. {len(all_records)} total daily records saved to {OUT_PATH}")
    print(f"Spent: {len(windows)} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
