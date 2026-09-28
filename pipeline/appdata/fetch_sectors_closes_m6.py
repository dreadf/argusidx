"""Pull Sectors' closing prices for the whole universe on the two M6 dates
(plan `kind-juggling-hoare.md` §3): 2025-12-30 and 2026-06-30, for R3
(sector-neutral, size-controlled comparison across that window, labelled
"satu kejadian, bukan uji") and R4 (H5/H10/H4 split by market state).

Both dates verified as real IDX trading days against the M1 IHSG calendar
(`data/raw/ihsg_2026-09-27.json`) before this pull, per the plan's own
note ("Both are trading days (verified in the idx_total.json calendar)").

Reuses `fetch_sectors_closes.fetch_closes` (same MCP `fetch-daily-close`
tool, same page-30, save-as-you-go, 429-tolerant, resumable pattern
already used for the 4 H5/H10 dates) rather than reimplementing it --
`pipeline/stats.py`'s "fix it once" rule applies just as much to fetch
code as to statistics.

Approved: standing approval for every pull in the plan's §9 table (user,
2026-09-27), which lists "M6: two universe closes" at about 64 credits,
re-confirmed by the user 2026-09-28 alongside M2 and M3. Logged in
docs/credit_ledger.md the moment it completes.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_sectors_closes_m6
"""
from __future__ import annotations

from pipeline.appdata.common import REPO_ROOT
from pipeline.appdata.fetch_sectors_closes import MAX_CALLS, fetch_closes

OUT_PATH = REPO_ROOT / "data" / "raw" / "sectors_daily_close_m6_2026-09-28.json"
DATES = ["2025-12-30", "2026-06-30"]


def main() -> None:
    import time

    from pipeline.sectors_mcp import SectorsMCP, SectorsMCPError

    client = SectorsMCP()

    def call(args: dict) -> dict:
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

    made = fetch_closes(DATES, OUT_PATH, call, max_calls=MAX_CALLS)
    print(f"{made} new calls; saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
