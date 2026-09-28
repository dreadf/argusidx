"""Pull Sectors' closing prices for the whole universe on the IHSG peak day,
2026-01-20 (plan `kind-juggling-hoare.md` §3, M5). Feeds the Kesimpulan's
"sejak puncak IHSG" window and the Pasar sections on which stocks fell least
and which weighed most on IHSG since the peak.

The date is the IHSG peak found in M1 (`data/raw/ihsg_2026-09-27.json`,
9,134.7), so it is a trading day by construction.

Reuses `fetch_sectors_closes.fetch_closes` (MCP `fetch-daily-close`, page of
30, saved after every page, resumable, 429-tolerant), like the M6 pull.

Approved: listed in the plan's §9 standing approval ("M5: universe close on
the IHSG peak date, about 32"), and re-confirmed by the user 2026-09-28 with
the cost stated (~32 credits, from the ordinary pool; the hackathon pool is
used up). Logged in docs/credit_ledger.md the moment it completes.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_sectors_closes_m5
"""
from __future__ import annotations

from pipeline.appdata.common import REPO_ROOT
from pipeline.appdata.fetch_sectors_closes import MAX_CALLS, fetch_closes

OUT_PATH = REPO_ROOT / "data" / "raw" / "sectors_daily_close_m5_2026-09-28.json"
DATES = ["2026-01-20"]


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
