# Sectors API Credit Ledger

One line per call that hit the real Sectors API. Non-renewing budget:
1,000 credits total for the whole build period. **Running total below
must always match reality — check "Usage and Balances" in the Sectors
portal periodically to confirm.**

Free responses (400/401/403/429/5xx) are not logged individually here
unless they're notable (e.g. revealed something useful) — only billed
calls count toward the total.

| Date | Endpoint | Purpose | Cost | Running total |
|---|---|---|---|---|
| 2026-09-05 | `/v2/daily/BBCA/` (2 calls) | Verify split-adjustment + freshness | 2 | 2 |
| 2026-09-05 | `/v2/companies/` (structured screener test) | Verify screener works live | 1 | 3 |
| 2026-09-05 | `/v2/subsectors/` | Verify taxonomy | 1 | 4 |
| 2026-09-05 | `/v2/news/?symbols=BBCA` | Verify dedup behavior | 1 | 5 |
| 2026-09-05 | `/v2/daily/BBCA/` (historical floor probes, x3) | Find undocumented 2021 floor | 3 | 8 |
| 2026-09-05 | `/v2/company/report/BBCA/?sections=overview` | Verify section-limiting | 1 | 9 |
| 2026-09-05 | `/v2/financials/quarterly/BBCA/?n_quarters=1` | Verify sector-dependent nulls | 1 | 10 |
| 2026-09-06 | `/v2/company/shareholders-composition/GOTO/` (2 years) | Verify retail-crowding data (H7 exploration, later deprioritized) | 2 | 12 |
| 2026-09-06 | `/v2/foreign-flow/GOTO/` | Verify foreign-flow data | 1 | 13 |
| 2026-09-06 | `/v2/free-float/` (full universe) | H1 explanatory variable | 10 | 23 |
| 2026-09-06 | `/v2/companies/` (market cap, 5 pages) | H1 size-confound control | 5 | 28 |
| 2026-09-06 | `/v2/companies/?where=pe_ttm>0 and roe_ttm>0&order_by=-market_cap&limit=5&include_query_values=true` | Phase 0 — field density test (approved in advance, see BACKLOG.md) | 1 | 29 |
| 2026-09-07 | `/v2/companies/?where=pe[2024] is not null&order_by=-market_cap&limit=3&include_query_values=true` | Phase 1 shape probe Q1 — yearly bracket-notation key format (confirmed flat: `"pe[2024]"`) | 1 | 30 |
| 2026-09-07 | `/v2/companies/?where=pe_ttm>0 or market_cap>0&order_by=-market_cap&limit=5&include_query_values=true` | Phase 1 shape probe Q2 — confirms permissive OR avoids AND's filtering (total_count 962 vs Phase 0's 604) | 1 | 31 |
| 2026-09-07 | `/v2/companies/` — full 49-condition combined `where` (all snapshot + yearly fields), limit=1 | Phase 1 pre-flight — confirms one query gets all 48 fields with zero rows excluded (total_count 962). Avoids the ~30-35 credit field-group fallback. | 1 | 32 |
| 2026-09-07 | `/v2/companies/` — full universe sweep, 5 pages × limit=200 | Phase 1 C2 — all snapshot + yearly 2021-2025 fields for 962 companies. `data/raw/universe_2026-09-07.json`. Cross-checked against purchased `free_float_2026-09-06.json`: 0 disagreements across 961 common symbols. | 5 | 37 |
| 2026-09-12 | `/v2/companies/` — expanded combined `where` (adds `industry`/`sub_industry`/price-bands/`earnings[YYYY]`/etc., verified against the live schema, `pipeline/hypotheses/_universe_fields.py`), limit=1 | Pre-flight for the re-sweep — approved by user. Confirmed: all 83 expected fields present, `total_count=962` (zero rows excluded) | 1 | 38 |
| 2026-09-12 | `/v2/companies/` — full universe re-sweep, 5 pages × limit=200, expanded field list | Approved by user 2026-09-12 (unlocks H4/H10/H15, fixes 207 stranded peer groups). `data/raw/universe_2026-09-12.json`, 962 companies, all 83 fields populated. Cross-checked against purchased `free_float_2026-09-06.json`: 36 of 961 common symbols now disagree (vs. 0 disagreements on the 2026-09-07 sweep against the same purchased file) — real free-float drift over the 5 days between sweeps, not a bug; see `docs/DATA.md` note | 5 | 43 |

**Total spent as of 2026-09-12: 43 credits.**

*(Note on how the Phase 0 call actually ran: the first attempts via
`pipeline/sectors_client.py` and a mis-sourced `.env` both hit Cloudflare
403s, which are free per the rules above and not logged as separate
lines. The one call above is the single successful, billed request —
made while diagnosing the 403s, with curl rather than the script, but
using the exact approved query. No extra call was made beyond the one
approved.)*

*(Historical note: before the Phase 0 line above, this table's own
28-credit total once disagreed with an earlier conversational summary of
29 — a single free/billed ambiguity around one of the very first
exploratory calls, never conclusively resolved either way. That old
uncertainty is unrelated to the current 29-credit total, which reflects
the real, newly-logged Phase 0 call. Recheck the portal before either
number matters for a decision.)*

**Remaining: ~957.**

## Rules for this ledger

1. Every billed call gets a line **before** moving on to the next task,
   not reconstructed from memory afterward.
2. State the cost and get explicit go-ahead before spending, per the
   standing project rule, this ledger records what was approved and
   spent, it doesn't replace asking first.
3. If the running total here and the portal's actual balance ever
   disagree, the portal wins, and the discrepancy gets a line explaining
   why (a free response miscounted as billed, or vice versa).
4. `pipeline/sectors_client.py`'s `get()` retries on 5xx, which is not
   fully idempotent against billing -- a 5xx generated after Sectors
   already ran the query bills the retry a second time. Low-risk for a
   single call; recheck the portal balance against this ledger after any
   `paginate()`-driven sweep, where the call count is much higher.
