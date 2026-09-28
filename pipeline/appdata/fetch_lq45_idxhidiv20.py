"""Pull LQ45 and IDXHIDIV20 daily index history from `/v2/index-daily/{index_code}/`
(plan `kind-juggling-hoare.md` §3, M2), 2025-01-01 through today. Feeds
"Saham besar vs seluruh pasar" on Pasar.

Same endpoint shape as `ihsg` (confirmed via the live schema,
`api.sectors.app/schema/`, read 2026-09-28): `lq45` and `idxhidiv20` are
both valid `index_code` values in the documented "Available index codes"
list, 90-day max window, 1 credit per call, floor 2019-01-02 (not binding
here since the plan trims the start to 2025-01-01: only "Saham besar vs
seluruh pasar" uses this series, and no test needs a longer one).

Trimmed to 2025-01-01 per the plan (not the full 2019 floor like M1):
about 7 windows per index, about 14 credits total for both.

Approved: standing approval for every pull in the plan's §9 table (user,
2026-09-27), which lists "M2: LQ45 and IDXHIDIV20 from 2025" at about 14
credits, re-confirmed by the user 2026-09-28 alongside M3 and M6. Logged
in docs/credit_ledger.md the moment it completes.

Same save-as-you-go, resumable, 429-tolerant pattern as fetch_ihsg.py:
one file per index, skips windows already covered on a re-run.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_lq45_idxhidiv20
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

from pipeline.appdata.common import REPO_ROOT
from pipeline.guards import assert_within_index_floor
from pipeline.sectors_client import SectorsAPIError, get

INDEX_CODES = ["lq45", "idxhidiv20"]
START = date(2025, 1, 1)
WINDOW_DAYS = 90
MAX_RETRIES = 8
RETRY_SLEEP = 45.0


def _out_path(index_code: str) -> Path:
    return REPO_ROOT / "data" / "raw" / f"{index_code}_{date.today()}.json"


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
    raise AssertionError("unreachable")


def fetch_index(index_code: str) -> int:
    """Returns the number of new calls made for this index."""
    assert_within_index_floor(START)

    out_path = _out_path(index_code)
    today = date.today()
    windows = build_windows(START, today, WINDOW_DAYS)

    all_records: list[dict] = json.loads(out_path.read_text()) if out_path.exists() else []
    saved_dates = {r["date"] for r in all_records}
    latest_saved = max(saved_dates) if saved_dates else None
    todo = [(s, e) for (s, e) in windows if latest_saved is None or e.isoformat() > latest_saved]
    skipped = len(windows) - len(todo)
    if skipped:
        print(f"{index_code}: resuming, {skipped} windows already saved (through {latest_saved}), {len(todo)} left.")
    print(f"{index_code}: {len(todo)} windows to fetch, ~{len(todo)} credits.")

    made = 0
    for i, (start, end) in enumerate(todo, start=1):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        records = _get_with_429_retry(f"/index-daily/{index_code}/", params)
        all_records.extend(records)
        made += 1
        out_path.write_text(json.dumps(all_records))
        print(f"  [{i}/{len(todo)}] {start}..{end}: {len(records)} rows (saved)")
    print(f"{index_code}: done, {len(all_records)} total rows, {out_path}")
    return made


def main() -> None:
    total_calls = 0
    for code in INDEX_CODES:
        total_calls += fetch_index(code)
    print(f"Total new calls: {total_calls}")


if __name__ == "__main__":
    main()
