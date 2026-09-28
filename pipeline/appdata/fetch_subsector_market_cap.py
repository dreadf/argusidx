"""Pull the `market_cap` section of `/v2/subsector/report/{sub_sector}/` for
every IDX subsector (plan `kind-juggling-hoare.md` §3, M3). Feeds the
Sektor section on Pasar.

Two steps, both billed, both confirmed against the live schema
(`api.sectors.app/schema/`, read 2026-09-28):

1. `/v2/subsectors/` -- 1 credit, returns the canonical kebab-case
   `sub_sector` slugs (e.g. `food-beverage`). The 33 subsector NAMES
   (not slugs) are already free in `data/raw/universe_2026-09-12.json`,
   but several contain "&" and "," (e.g. "Oil, Gas & Coal"), and this
   project's rule is to check an external contract rather than guess
   one, so the slug itself is pulled rather than hand-derived.
2. `/v2/subsector/report/{slug}/?sections=market_cap` -- 1 credit per
   subsector (confirmed: "Costs 1 API credit per requested section"),
   so requesting only `market_cap` is 1 credit, not the 6-credit
   all-sections default.

Approved: standing approval for every pull in the plan's §9 table (user,
2026-09-27), which lists "M3: subsectors (count first)" at about 30
credits, re-confirmed by the user 2026-09-28 alongside M2 and M6.
Logged in docs/credit_ledger.md the moment it completes.

Save-as-you-go and resumable: the slug list and each subsector's report
are written to disk immediately, and a re-run skips any slug already
saved.

Run only after the above approval already holds:
    .venv/bin/python -m pipeline.appdata.fetch_subsector_market_cap
"""
from __future__ import annotations

import json
import time

from pipeline.appdata.common import REPO_ROOT
from pipeline.sectors_client import SectorsAPIError, get

SLUGS_PATH = REPO_ROOT / "data" / "raw" / "subsectors_2026-09-28.json"
REPORTS_PATH = REPO_ROOT / "data" / "raw" / "subsector_market_cap_2026-09-28.json"
MAX_RETRIES = 8
RETRY_SLEEP = 45.0


def _get_with_429_retry(path: str, params: dict | None = None) -> object:
    for attempt in range(MAX_RETRIES):
        try:
            return get(path, params)
        except SectorsAPIError as e:
            if "429" not in str(e) or attempt == MAX_RETRIES - 1:
                raise
            print(f"    429, waiting {RETRY_SLEEP:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(RETRY_SLEEP)
    raise AssertionError("unreachable")


def fetch_slugs() -> tuple[list[dict], int]:
    """Returns (slugs, new_calls_made)."""
    if SLUGS_PATH.exists():
        slugs = json.loads(SLUGS_PATH.read_text())
        print(f"Subsector slugs: reusing saved {SLUGS_PATH} ({len(slugs)} entries, 0 new credits).")
        return slugs, 0
    print("Subsector slugs: fetching /v2/subsectors/ (1 credit).")
    slugs = _get_with_429_retry("/subsectors/")
    SLUGS_PATH.write_text(json.dumps(slugs))
    print(f"  saved {len(slugs)} entries to {SLUGS_PATH}")
    return slugs, 1


def fetch_reports(slugs: list[dict]) -> int:
    """Returns the number of new calls made."""
    reports: dict = json.loads(REPORTS_PATH.read_text()) if REPORTS_PATH.exists() else {}
    sub_sector_slugs = sorted({row["subsector"] for row in slugs})
    todo = [s for s in sub_sector_slugs if s not in reports]
    skipped = len(sub_sector_slugs) - len(todo)
    if skipped:
        print(f"Resuming: {skipped} subsectors already saved, {len(todo)} left.")
    print(f"{len(todo)} subsectors to fetch, ~{len(todo)} credits (1 per subsector, market_cap only).")

    made = 0
    for i, slug in enumerate(todo, start=1):
        body = _get_with_429_retry(f"/subsector/report/{slug}/", {"sections": "market_cap"})
        reports[slug] = body
        made += 1
        REPORTS_PATH.write_text(json.dumps(reports))
        print(f"  [{i}/{len(todo)}] {slug} (saved)")
    print(f"Done: {len(reports)} total subsector reports, {REPORTS_PATH}")
    return made


def main() -> None:
    slugs, slug_calls = fetch_slugs()
    report_calls = fetch_reports(slugs)
    print(f"Total new calls this run: {slug_calls + report_calls}")


if __name__ == "__main__":
    main()
