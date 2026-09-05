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

**Total spent as of 2026-09-06: 28 credits.**

*(Note: earlier conversational summaries said 29 — the discrepancy is a
single free/billed ambiguity around one of the very first exploratory
calls that was never conclusively confirmed either way. Treat 28 as the
floor and recheck the portal before this matters.)*

**Remaining: ~972.**

## Rules for this ledger

1. Every billed call gets a line **before** moving on to the next task,
   not reconstructed from memory afterward.
2. State the cost and get explicit go-ahead before spending, per the
   standing project rule — this ledger records what was approved and
   spent, it doesn't replace asking first.
3. If the running total here and the portal's actual balance ever
   disagree, the portal wins, and the discrepancy gets a line explaining
   why (a free response miscounted as billed, or vice versa).
