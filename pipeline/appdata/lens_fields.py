"""Field list for the lens/flag universe re-sweep (docs/PRODUCT.md §6, §9).

A standalone copy of the base 48-field list already verified working in
`data/raw/universe_2026-09-12.json` (originally established in
`pipeline/hypotheses/_universe_fields.py`, duplicated here rather than
imported so this module doesn't depend on a file under the hypothesis-
testing session's active territory), plus the fields this session's own
live schema check confirmed exist for: the LQ45 anomaly flag (`indices`)
and the Banking lens (casa/LDR/NIM/CAR/NPL/net_loan). Also includes
`INSURANCE_YEARLY` (premium income/expense/net), fetched on the same
sweep but never used for a lens — `docs/PRODUCT.md`'s "Cut, and why"
section (2026-09-13) confirms these fields populate for Banks, not the
Insurance sub-sector, and that no substitute field exists anywhere in
the schema. Kept here rather than deleted since the data was already
paid for and is a documented, correct fact about the schema even though
no lens consumes it.

`indices` needs the `in` operator per the schema (`where=indices in
['LQ45', 'IDX30']` — confirmed at https://api.sectors.app/schema/,
2026-09-13), not `is not null` like every other field here. The exact
enum list below is read off a real example response for BBCA in the live
schema doc, not guessed.
"""
from __future__ import annotations

SNAPSHOT_NULL_CHECK = [
    "market_cap", "free_float", "pe_ttm", "pb_mrq", "roe_ttm",
    "roa_ttm", "der_mrq", "yield_ttm", "payout_ratio",
    "market_cap_rank", "employee_num", "esg_score", "forward_pe",
    "dividend_yield_avg", "yearly_mcap_change", "cash_payout_ratio",
    "ps_ttm", "dar_mrq", "last_close_price", "daily_close_change",
    "ytd_low_price", "ytd_high_price", "52_w_low_price", "52_w_high_price",
    "90_d_low_price", "90_d_high_price", "all_time_low_price", "all_time_high_price",
]
SNAPSHOT_STR = [
    "sector", "sub_sector", "listing_board", "listing_date",
    "industry", "sub_industry", "last_ex_dividend_date",
    "ytd_low_date", "ytd_high_date", "52_w_low_date", "52_w_high_date",
    "90_d_low_date", "90_d_high_date", "all_time_low_date", "all_time_high_date",
]
YEARLY = [
    "pe", "roe", "total_dividend", "total_yield",
    "debt_to_equity_ratio", "revenue", "outstanding_shares", "earnings",
]

# New this sweep — Banking lens (docs/PRODUCT.md §9).
BANKING_YEARLY = [
    "casa_ratio", "loan_to_deposit_ratio", "net_interest_margin",
    "capital_adequacy_ratio", "non_performing_loan", "net_loan",
]
# Fetched this sweep, but the Insurance lens was cut 2026-09-13 (docs/PRODUCT.md
# §3, "Cut, and why") — these fields populate for Banks, not Insurance, and no
# substitute exists. Unused by any builder; kept only as a documented schema fact.
INSURANCE_YEARLY = [
    "premium_income", "premium_expense", "net_premium_income",
]

YEARS = [2021, 2022, 2023, 2024, 2025]

# The Banking/Insurance lens fields are for a current-snapshot comparison
# scorecard, not a hypothesis-testing predictor series, so they don't need
# YEARLY's full 5-year range - and empirically CAN'T share it: the where
# clause has a real server-side limit (confirmed live, 2026-09-13:
# 109 conditions/3584 chars succeeded, 115/3815 failed - bisected by hand
# rather than guessed). 2 years fits comfortably under that limit alongside
# the full base field list.
LENS_YEARS = [2024, 2025]

# Real enum values confirmed via a live example response (BBCA) in the
# Sectors schema doc, 2026-09-13 — not guessed.
INDEX_MEMBERSHIP_VALUES = [
    "LQ45", "IDX30", "IDXG30", "ECONOMIC30", "IDXESGL", "FTSE",
    "SRIKEHATI", "KOMPAS100", "IDXHIDIV20", "IDXQ30",
]


def build_where() -> str:
    conds = [f"{f} is not null" for f in SNAPSHOT_NULL_CHECK]
    conds += [f"{f} is not null" for f in SNAPSHOT_STR]
    conds += [f"{f}[{y}] is not null" for f in YEARLY for y in YEARS]
    conds += [f"{f}[{y}] is not null" for f in BANKING_YEARLY for y in LENS_YEARS]
    conds += [f"{f}[{y}] is not null" for f in INSURANCE_YEARLY for y in LENS_YEARS]
    conds.append(f"indices in {INDEX_MEMBERSHIP_VALUES!r}")
    conds.append("market_cap > 0")  # universal safety net, same as the base sweep
    return " or ".join(conds)
