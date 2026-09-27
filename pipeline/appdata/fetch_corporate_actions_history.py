"""Pull the FULL 2022-2026 history of `/v2/corporate-actions/` for three
types (right_issue, stock_split, bonus) -- M4 in the research plan
(`kind-juggling-hoare.md` section 3, item 8), used by A1 to exclude a
one-day "extreme gainer" that was actually a split/rights/bonus artifact
rather than a genuine price move.

Distinct from `fetch_corporate_actions.py`, which pulls a ~60-day window
around "today" for the stock-page corporate-action display feature (a
different consumer, a different and much smaller window) -- this file
exists because A1 needs the FULL historical window, not a near-today
snapshot.

Live schema, confirmed via a 3-credit probe (docs/credit_ledger.md,
2026-09-27): 1 credit PER REQUESTED TYPE per call (3 types requested here
= 3 credits per call), window clamped to 90 days. Response keys:
`right_issue` (date field `ex_date`), `stock_split` (date field `date`),
`bonus` (date field `ex_date`) -- each row also carries `symbol`.

2022-01-01 through today is ~20 windows, ~60 credits (matches the plan's
estimate). Approved: standing approval (plan section 9 table, "M4:
corporate actions (optional)"); the user separately confirmed spending on
this specific call after the ARA-band verification path failed
(2026-09-27, "Spend ~61 credits on M4").

Resumable and 429-tolerant, same pattern as `fetch_ihsg.py`: saves after
every call, skips windows already covered by a prior partial run. Unlike
`fetch_ihsg.py`, the output filename is found via a glob (`RAW_DIR.glob(
CORP_ACTIONS_HISTORY_GLOB)`), not re-derived from `date.today()` on every
run: a fixed `date.today()` path would silently break resumability the
moment a resume happens on a different calendar day than the original run
started on, re-fetching (and re-billing) every already-saved window
(found by /code-review, 2026-09-27). A brand-new file is only created
when no matching file exists yet.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_corporate_actions_history
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

from pipeline.appdata.common import CORP_ACTIONS_HISTORY_GLOB, RAW_DIR
from pipeline.sectors_client import SectorsAPIError, get

TYPES = ["right_issue", "stock_split", "bonus"]
WINDOW_DAYS = 90
START = date(2022, 1, 1)
MAX_RETRIES = 8
RETRY_SLEEP = 45.0


def resolve_out_path() -> Path:
    """The existing dated file to resume into, if one exists (regardless of
    which day it was started on); otherwise a fresh one dated today."""
    existing = sorted(RAW_DIR.glob(CORP_ACTIONS_HISTORY_GLOB))
    return existing[-1] if existing else RAW_DIR / f"corporate_actions_history_{date.today()}.json"


def build_windows(start: date, end: date, window_days: int) -> list[tuple[date, date]]:
    windows = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=window_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def _get_with_429_retry(path: str, params: dict) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            return get(path, params)
        except SectorsAPIError as e:
            if "429" not in str(e) or attempt == MAX_RETRIES - 1:
                raise
            print(f"    429, waiting {RETRY_SLEEP:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(RETRY_SLEEP)
    raise AssertionError("unreachable")


def main() -> None:
    today = date.today()
    windows = build_windows(START, today, WINDOW_DAYS)
    out_path = resolve_out_path()

    store: dict = json.loads(out_path.read_text()) if out_path.exists() else {}
    done_ranges = set(store.keys())
    todo = [(s, e) for (s, e) in windows if f"{s.isoformat()}_{e.isoformat()}" not in done_ranges]
    skipped = len(windows) - len(todo)
    if skipped:
        print(f"Resuming into {out_path.name}: {skipped} windows already saved, {len(todo)} left.")
    print(f"{len(todo)} windows to fetch, ~{len(todo) * len(TYPES)} credits ({len(TYPES)} types/call, approved).")

    for i, (start, end) in enumerate(todo, start=1):
        params = {"start": start.isoformat(), "end": end.isoformat(), "type": ",".join(TYPES)}
        response = _get_with_429_retry("/corporate-actions/", params)
        key = f"{start.isoformat()}_{end.isoformat()}"
        store[key] = response
        counts = {t: len(response.get(t, [])) for t in TYPES}
        print(f"  [{i}/{len(todo)}] {start} to {end}: {counts}")
        out_path.write_text(json.dumps(store, indent=2))

    total_events = sum(len(w.get(t, [])) for w in store.values() for t in TYPES)
    print(f"\nDone. {len(store)} windows, {total_events} total events, saved to {out_path}")
    print(f"Spent this run: {len(todo) * len(TYPES)} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
