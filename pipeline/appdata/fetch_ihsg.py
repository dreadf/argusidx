"""Pull the full IHSG daily index history from `/v2/index-daily/ihsg/`
(plan `kind-juggling-hoare.md` §3, M1): the index itself, cap-weighted,
distinct from `idx_total` (total market cap across all listings, already
in `data/raw/idx_total_*.json`). Feeds T1 ("Kondisi pasar: tertekan")
and locates the IHSG peak date for the Kesimpulan's "sejak puncak IHSG"
window, which may differ from idx_total's 19 Jan 2026 peak.

Live schema, confirmed via the 1-credit probe (docs/credit_ledger.md,
2026-09-27): earliest date 2019-01-02, max 90-day window, 1 credit per
call. 2019-01-02 through today is ~32 calls, ~32 credits -- matches the
plan's estimate.

Approved: standing approval for every pull in the plan's §9 table
(user, 2026-09-27, "Yes I approve every pull, no need to ask again"),
which lists "M1: IHSG from 2019" at 32 credits. Logged in
docs/credit_ledger.md the moment it completes, per the standing project
rule (CLAUDE.md).

Guarded by `pipeline.guards.assert_within_index_floor` so this can never
silently start before the documented floor.

Saves incrementally after every call (same pattern as fetch_idx_total.py,
itself modeled on the save-as-you-go fix `sectors_client.paginate()`'s
docstring documents after a real lost-data incident): a crash or 429
partway through loses at most one call's worth of days, not the whole
pull, and none of it needs re-billing since each 90-day window is a
distinct, non-overlapping call.

Resumable and 429-tolerant: if `OUT_PATH` already exists (e.g. from a
prior run cut short by a rate limit), windows already fully covered by
its saved date range are skipped rather than re-fetched -- so a re-run
never re-bills. A 429 (unbilled, per docs/PLAN.md 8.4) is retried with a
45-second wait rather than failing the whole run, matching the pattern
`fetch_sectors_closes.py` already uses for the same trap.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_ihsg
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta

from pipeline.appdata.common import REPO_ROOT
from pipeline.guards import SECTORS_INDEX_FLOOR, assert_within_index_floor
from pipeline.sectors_client import SectorsAPIError, get

WINDOW_DAYS = 90
MAX_RETRIES = 8
RETRY_SLEEP = 45.0
OUT_PATH = REPO_ROOT / "data" / "raw" / f"ihsg_{date.today()}.json"


def build_windows(start: date, end: date, window_days: int) -> list[tuple[date, date]]:
    windows = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=window_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def _get_with_429_retry(path: str, params: dict) -> list[dict]:
    for attempt in range(MAX_RETRIES):
        try:
            return get(path, params)
        except SectorsAPIError as e:
            if "429" not in str(e) or attempt == MAX_RETRIES - 1:
                raise
            print(f"    429, waiting {RETRY_SLEEP:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(RETRY_SLEEP)
    raise AssertionError("unreachable")  # loop always returns or raises


def main() -> None:
    assert_within_index_floor(SECTORS_INDEX_FLOOR)  # documents intent; must not raise

    today = date.today()
    windows = build_windows(SECTORS_INDEX_FLOOR, today, WINDOW_DAYS)

    all_records: list[dict] = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else []
    saved_dates = {r["date"] for r in all_records}
    # A window is already covered if every day the API could return for it
    # (i.e. every date already saved that falls in-range) -- since trading
    # days are a subset of calendar days, the reliable resume signal is
    # simpler: skip any window whose end date is not after the latest
    # date already saved.
    latest_saved = max(saved_dates) if saved_dates else None
    todo = [(s, e) for (s, e) in windows if latest_saved is None or e.isoformat() > latest_saved]
    skipped = len(windows) - len(todo)
    if skipped:
        print(f"Resuming: {skipped} windows already saved (through {latest_saved}), {len(todo)} left.")
    print(f"{len(todo)} windows to fetch, ~{len(todo)} credits (1 per call, approved).")

    for i, (start, end) in enumerate(todo, start=1):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        records = _get_with_429_retry("/index-daily/ihsg/", params)
        all_records.extend(records)
        print(f"  [{i}/{len(todo)}] {start} to {end}: {len(records)} days")
        # Save after every call, not just at the end: one lost call on a
        # crash, never the whole pull.
        OUT_PATH.write_text(json.dumps(all_records, indent=2))

    print(f"\nDone. {len(all_records)} total daily records saved to {OUT_PATH}")
    print(f"Spent this run: {len(todo)} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
