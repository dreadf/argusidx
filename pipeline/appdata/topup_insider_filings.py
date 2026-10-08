"""Top up insider buy/sell filings with only the rows since the last pull.

`/v2/filings/?holder_type=insider` at 30 rows per page. A 1-credit size probe
on 2026-10-08 (start 2026-09-12) found 108 buys and 104 sells, so about 4
pages each, ~8 credits total. Approved: user's 2026-10-08 go-ahead ("Whatever
you think makes sense, do them") after the cost table was stated.

Writes a NEW dated jsonl per side holding the previous rows plus the new
ones (deduplicated), because build_insider_activity reads only the latest
file. Saves after every page. Refuses to overwrite today's file.

    .venv/bin/python -m pipeline.appdata.topup_insider_filings
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from pipeline.appdata.common import RAW_DIR, latest_dated_file
from pipeline.sectors_client import paginate

PAGE_SIZE = 30


def topup(side: str, today: date) -> int:
    out = RAW_DIR / f"insider_{side}s_2025_2026_{today}.jsonl"
    if out.exists():
        raise FileExistsError(f"{out} already exists: refusing to overwrite purchased data.")
    prev = latest_dated_file(RAW_DIR, f"insider_{side}s_2025_2026_????-??-??.jsonl")
    lines = [ln for ln in prev.read_text().splitlines() if ln.strip()]
    rows = [json.loads(ln) for ln in lines]
    seen = set(lines_key for lines_key in (json.dumps(r, sort_keys=True) for r in rows))
    last = max(r["timestamp"][:10] for r in rows if r.get("timestamp"))
    # Start one day before the last saved date: the boundary day may have had
    # late filings. Duplicates are dropped by full-row equality.
    start = date.fromisoformat(last) - timedelta(days=1)
    params = {"holder_type": "insider", "transaction_type": side, "start": start.isoformat(), "end": today.isoformat()}
    f_lines = list(lines)
    calls = 0
    added = 0

    def on_page(page: list[dict]) -> None:
        nonlocal calls, added
        calls += 1
        for r in page:
            key = json.dumps(r, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            f_lines.append(json.dumps(r))
            added += 1
        out.write_text("\n".join(f_lines) + "\n")

    paginate("/filings/", params, page_size=PAGE_SIZE, on_page=on_page)
    print(f"{side}: {start}..{today}, {calls} calls, {added} new rows, {len(f_lines)} total -> {out.name}")
    return calls


def main() -> None:
    today = date.today()
    spent = sum(topup(side, today) for side in ("buy", "sell"))
    print(f"Spent: {spent} credits. Log this in docs/credit_ledger.md now.")


if __name__ == "__main__":
    main()
