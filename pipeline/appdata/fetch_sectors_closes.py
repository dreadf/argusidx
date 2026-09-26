"""
Pull Sectors' closing prices for the whole universe on a few dates, through the
MCP tool `fetch-daily-close` (docs/credit_ledger.md, 2026-09-27; pre-registration
"V" in EXPERIMENT.md). Costs 1 credit per page of 30 tickers, about 32 pages per
date.

Saves after every page and skips saved pages, so a re-run never re-bills. Refuses
to make more than `MAX_CALLS` new calls and stops on a date that would need more
than `MAX_PAGES_PER_DATE` pages. Needs `allow_billed=True`, i.e. the caller has
stated the cost and been approved.

Run:
    .venv/bin/python -m pipeline.appdata.fetch_sectors_closes
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "raw" / "sectors_daily_close_2026-09-27.json"

# The dates the H5/H10 nearest-price rule picks for the two holdout formation years.
DATES = ["2025-04-30", "2025-09-04", "2026-04-30", "2026-09-04"]
PAGE = 30
MAX_PAGES_PER_DATE = 34
MAX_CALLS = 140

CallFn = Callable[[dict], dict]


def fetch_closes(dates: list[str], path: Path, call: CallFn, max_calls: int = MAX_CALLS) -> int:
    """Returns the number of new calls made. `call(arguments)` returns the tool payload."""
    store: dict = json.loads(path.read_text()) if path.exists() else {}
    made = 0
    for d in dates:
        entry = store.setdefault(d, {"pages": {}, "complete": False})
        offset = 0
        while not entry["complete"]:
            key = str(offset)
            if key in entry["pages"]:
                offset += PAGE
                continue
            if len(entry["pages"]) >= MAX_PAGES_PER_DATE:
                raise RuntimeError(f"{d}: more than {MAX_PAGES_PER_DATE} pages, stopping to report")
            if made >= max_calls:
                raise RuntimeError(f"cap of {max_calls} new calls reached")
            body = call({"date": d, "limit": PAGE, "offset": offset})
            made += 1
            entry["pages"][key] = body.get("results", [])
            pagination = body.get("pagination", {})
            entry["total_count"] = pagination.get("total_count")
            if not pagination.get("has_next") or not entry["pages"][key]:
                entry["complete"] = True
            path.write_text(json.dumps(store))
            offset += PAGE
    return made


def main() -> None:
    from pipeline.sectors_mcp import SectorsMCP

    import time

    from pipeline.sectors_mcp import SectorsMCPError

    client = SectorsMCP()

    def call(args: dict) -> dict:
        # A rate-limited call (429) is not billed: wait and retry the same page.
        for attempt in range(8):
            try:
                body = client.call_tool("fetch-daily-close", args, allow_billed=True)
                time.sleep(1.5)
                return body
            except SectorsMCPError as e:
                if "RATE_LIMIT" not in str(e) or attempt == 7:
                    raise
                time.sleep(45)
        raise RuntimeError("unreachable")

    made = fetch_closes(DATES, OUT_PATH, call)
    print(f"{made} new calls; saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
