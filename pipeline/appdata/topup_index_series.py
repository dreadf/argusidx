"""Top up the four dated index series with only the days since their last pull.

Series: IHSG (`/index-daily/ihsg/`), LQ45, IDXHIDIV20 and IDX total
(`/idx-total/`). The full fetchers re-bill overlapping 90-day windows; this
fetches `latest_saved + 1 day` through yesterday, which fits one 90-day
window (1 credit per series) while the gap is under 90 days.

Cost: 4 credits (one call per series). Approved: user's 2026-10-08 go-ahead
("Whatever you think makes sense, do them") after the cost table was stated.

Writes a NEW dated file per series (the existing records plus the new days,
deduplicated by date) and refuses to overwrite an existing file for today.
The builders already read the latest dated file.

    .venv/bin/python -m pipeline.appdata.topup_index_series
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from pipeline.appdata.common import RAW_DIR, latest_dated_file
from pipeline.sectors_client import get

MAX_WINDOW_DAYS = 90

# (file prefix, API path)
SERIES = [
    ("ihsg", "/index-daily/ihsg/"),
    ("lq45", "/index-daily/lq45/"),
    ("idxhidiv20", "/index-daily/idxhidiv20/"),
    ("idx_total", "/idx-total/"),
]


def topup(prefix: str, path: str, today: date) -> int:
    out = RAW_DIR / f"{prefix}_{today}.json"
    if out.exists():
        raise FileExistsError(f"{out} already exists: refusing to overwrite purchased data.")
    latest = latest_dated_file(RAW_DIR, f"{prefix}_????-??-??.json")
    records: list[dict] = json.loads(latest.read_text())
    last = max(r["date"] for r in records)
    start = date.fromisoformat(last) + timedelta(days=1)
    end = today - timedelta(days=1)  # idx-total rejects an end date of today
    if start > end:
        print(f"{prefix}: already current through {last}, nothing to fetch.")
        return 0
    if (end - start).days + 1 > MAX_WINDOW_DAYS:
        raise ValueError(f"{prefix}: gap {start}..{end} exceeds one {MAX_WINDOW_DAYS}-day window; use the full fetcher.")
    new = get(path, {"start": start.isoformat(), "end": end.isoformat()})
    have = {r["date"] for r in records}
    added = [r for r in new if r["date"] not in have]
    records.extend(added)
    records.sort(key=lambda r: r["date"])
    out.write_text(json.dumps(records, indent=2))
    print(f"{prefix}: {start}..{end}, {len(added)} new days, through {max(r['date'] for r in records)} -> {out.name}")
    return 1


def main() -> None:
    today = date.today()
    spent = sum(topup(p, a, today) for p, a in SERIES)
    print(f"Spent: {spent} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
