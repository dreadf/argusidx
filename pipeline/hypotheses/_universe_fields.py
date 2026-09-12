"""
Shared field list and `where`-clause builder for the full-universe
screener sweep (`/v2/companies/`).

Single source of truth for phase1_full_query_test.py (the ~1-credit
pre-flight) and phase1_universe_sweep.py (the real ~5-credit sweep) --
previously each file carried its own verbatim copy of this list, so a
field added to one and not the other would silently let the pre-flight
validate a different query than the sweep actually runs, defeating the
pre-flight's whole purpose (found by /code-review, 2026-09-12).

Extended 2026-09-12 with fields verified against the live schema
(`https://api.sectors.app/schema/`, fetched free with `curl -A
"Mozilla/5.0"`, 2026-09-12) for the "one sweep, four jobs" plan
(docs/PLAN.md): `industry`/`sub_industry` (fixes 207 stranded
companies), price bands (powers rankings/anomaly flags), `earnings[YYYY]`
(unlocks H4/H10). All confirmed available through the cheap
`/v2/companies/` screener via `is not null`, not the expensive per-symbol
`/v2/company/report/` endpoint -- cost is per-page (5 pages = ~5 credits
for the whole universe), not per-field.

Deliberately NOT included: `tags`, `indices`, `affiliates`. The schema
requires these to be queried with the `in` operator against a specific
value list (e.g. `tags in ['52-w-high']`), not `is not null` -- the full
tag vocabulary isn't verified yet (needs its own `/v2/tags/` call, not
costed here), and guessing a partial list would silently miss any
company whose tags aren't in the guess, which is worse than leaving this
unverified a while longer. Revisit once `/v2/tags/`'s cost is stated and
approved.
"""
from __future__ import annotations

SNAPSHOT_NULL_CHECK = [
    "market_cap", "free_float", "pe_ttm", "pb_mrq", "roe_ttm",
    "roa_ttm", "der_mrq", "yield_ttm", "payout_ratio",
    # Added 2026-09-12 -- all verified present on /v2/companies/ via the
    # live schema, same is-not-null mechanism as the fields above.
    "market_cap_rank", "employee_num", "esg_score", "forward_pe",
    "dividend_yield_avg", "yearly_mcap_change", "cash_payout_ratio",
    "ps_ttm", "dar_mrq", "last_close_price", "daily_close_change",
    "ytd_low_price", "ytd_high_price", "52_w_low_price", "52_w_high_price",
    "90_d_low_price", "90_d_high_price", "all_time_low_price", "all_time_high_price",
]
SNAPSHOT_STR = [
    "sector", "sub_sector", "listing_board", "listing_date",
    # Added 2026-09-12.
    "industry", "sub_industry", "last_ex_dividend_date",
    "ytd_low_date", "ytd_high_date", "52_w_low_date", "52_w_high_date",
    "90_d_low_date", "90_d_high_date", "all_time_low_date", "all_time_high_date",
]
YEARLY = [
    "pe", "roe", "total_dividend", "total_yield",
    "debt_to_equity_ratio", "revenue", "outstanding_shares",
    "earnings",  # Added 2026-09-12 -- unlocks H4 (payout-ratio-per-year).
]
YEARS = [2021, 2022, 2023, 2024, 2025]


def build_where() -> str:
    conds = [f"{f} is not null" for f in SNAPSHOT_NULL_CHECK]
    conds += [f"{f} is not null" for f in SNAPSHOT_STR]
    conds += [f"{f}[{y}] is not null" for f in YEARLY for y in YEARS]
    conds.append("market_cap > 0")  # universal safety net
    return " or ".join(conds)


def expected_fields() -> set[str]:
    fields = set(SNAPSHOT_NULL_CHECK) | set(SNAPSHOT_STR)
    fields |= {f"{f}[{y}]" for f in YEARLY for y in YEARS}
    return fields
