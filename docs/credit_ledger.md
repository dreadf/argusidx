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
| 2026-09-13 | `/v2/filings/?symbol=CBMF&start=2026-09-01&end=2026-09-12&limit=30` | Pilot: does insider-filing data explain CBMF.JK's observed free_float jump (3.06%→24%, 2026-09-06 to 2026-09-12) -- approved by user, tip surfaced by a parallel app-building session. Result: `total_count=0` -- no filings for CBMF in that window. First attempt hit a free 404 (double `/v2/` in the path, my own bug, not billed). | 1 | 44 |
| 2026-09-13 | `/v2/filings/?symbol={ADRO,BBNI,BSDE,BULL,BHIT,BIRD,AKRA,AMMN}&start=2026-09-01&end=2026-09-12&limit=30` (8 calls) | Broader test of the same idea -- approved by user ("test all of it out") -- on liquid, real drift symbols + 2 zero-drift controls, to check whether the CBMF null was a fluke or a pattern. Result: 0 filings for all 6 drift symbols; the zero-drift control AKRA had 6 small filings (~0.02-0.27% stakes each) whose combined magnitude roughly matches its own near-zero measured free_float change. See EXPERIMENT.md-adjacent note / BACKLOG.md for the conclusion. | 8 | 52 |
| 2026-09-13 | `/v2/suspensions/` — full history, 20 pages × limit=30 | Approved by user ("just go ahead and do it") to unlock H11 (suspension → underperformance) and give real "unusual price movement" categorization to test the other session's H8-partial-path and H11-texture tips. `data/raw/suspensions_2026-09-13.json`, 588 suspension records, all fields (`symbol`, `suspension_date`, `reason`, `pdf_url`). | 20 | 72 |
| 2026-09-13 | `/v2/filings/?symbol={JARR,GRPH,MGLV,ASLI}&start=...&end=<suspension_date>&limit=30` (4 calls) | Companion test for the other session's #2 (H8 partial path) and #3 (H11 texture) tips: do insider filings show accumulation before a real "unusual price increase" suspension? Result: JARR 1 filing, GRPH 0, MGLV 3, ASLI 1 -- see BACKLOG.md/EXPERIMENT-adjacent note for the read. | 4 | 76 |
| 2026-09-13 | `/v2/mining/companies/` — discovery probe, 13 pages × limit=30 | H12 probe, approved by user ("go ahead with both" for H4+H12) — discovery before the full mining suite spend, matching the plan's own probe-first pattern. `data/raw/mining_companies_2026-09-13.json`, 366 mining companies with commodity_type/symbol/slug. | 13 | 89 |
| 2026-09-13 | `/v2/companies/`, `limit=1` diagnostic calls (12, app-building session) | Pre-flight for the lens/LQ45-flag field re-sweep, approved via the standing ≤20-credit rule + explicit go-ahead from the hypothesis-testing session ("Go ahead independently — good time, no conflict"). Cost more than the ~6-credit estimate (12, not ~1) because the combined `where` clause hit a real, previously-undocumented server-side limit: bisected live and confirmed 109 conditions/3584 chars succeeds, 115/3815 fails (one 400, free, not counted below). Scoped the new Banking/Insurance fields to 2 years (2024-2025) instead of the base fields' full 2021-2025 to fit under it — a real product/hypothesis-testing precompute doesn't need 5 years for a comparison scorecard anyway. | 12 | 101 |
| 2026-09-13 | `/v2/companies/` — full universe re-sweep, 5 pages × limit=200, adds `indices` + Banking lens (casa_ratio/loan_to_deposit_ratio/net_interest_margin/capital_adequacy_ratio/non_performing_loan/net_loan, 2024-2025) + attempted Insurance lens (premium_income/premium_expense/net_premium_income, 2024-2025) | `data/raw/universe_2026-09-13.json`, 962 companies. Unlocks the LQ45 anomaly flag (45 real LQ45 members, 12 with free float <25% — CUAN, AADI, ICBP, ISAT, ADMR, UNVR, NCKL, INCO, PGEO, MEDC, MAPI, SCMA) and the Banking lens (46 real banks, sanity-checked against BBCA's known real profile: 84.3% CASA, 75.9% LDR, ~30% CAR — all plausible). **Real finding, corrects the plan:** the premium_income/premium_expense fields populate for **Banks** (46/46), not the Insurance sub-sector (0/19) — the Insurance lens as specified in docs/PRODUCT.md §9 is not viable with these fields; needs its own investigation before it ships. | 5 | 106 |
| 2026-09-13 | `/v2/filings/?holder_type=insider&transaction_type=sell&start=2025-01-01&end=2026-09-13&limit=1` | H8-cheap pre-flight, approved by user -- sizing the cost of a bulk insider-sell pull to join against owned suspension events (extends the H11 companion-probe finding into a real pre-registered test). Result: `total_count=1388` -- a full pull at 30/page would be ~47 credits, not yet approved. | 1 | 107 |
| 2026-09-13 | `/v2/tags/` | H9 verification #1, approved by user -- confirmed real sentiment tags exist (`bullish`/`bearish`/`neutral`/`market-sentiment`/`overvalued`/`undervalued`) among 100 total tag slugs. | 1 | 108 |
| 2026-09-13 | `/v2/news/?tags=bullish,bearish&limit=30` | H9 verification #2, approved by user -- checked whether sentiment-tagged articles link to a specific stock. Result: 25 of 30 (83%) have a non-empty `symbols` array; `dimension` scores are real non-trivial values (0-2 scale), not empty placeholders. Per-stock sentiment is viable. `total_count=8801` for all-time bullish/bearish articles -- a full pull at 30/page would be ~294 credits, not yet approved; needs a date-scoped estimate before any further spend. | 1 | 109 |
| 2026-09-13 | `/v2/news/?tags=bullish,bearish&start=2025-01-01&end=2026-09-13&limit=1` | H9 verification #3, approved by user -- date-scoped total to size the real pull cost before committing. Result: `total_count=8801`, IDENTICAL to the all-time total from the unscoped check above -- suggests the news corpus itself may only go back to ~2025 rather than the date filter failing; not independently confirmed (would need an even earlier `start` to test), not blocking H8 progress. | 1 | 110 |
| 2026-09-13 | `/v2/filings/?holder_type=insider&transaction_type=sell&start=2025-01-01&end=2026-09-13` — bulk pull, H8-cheap, 1,388 records total | Approved by user ("do those two things"). ⚠️ **Cost overrun, disclosed immediately: 79 credits actually spent, not the ~47 estimated.** First attempt (naive `paginate()`, no incremental save) successfully fetched and was billed for 32 pages (offset 0-930) before hitting a 429 rate limit at offset=960 -- that data was lost, never written to disk, because the script only saved at the very end. Rewrote as a resumable, incrementally-saving script with inter-page delay; the corrected run re-fetched **all** 47 pages from scratch (since the first attempt's data was unrecoverable), re-billing the same first 32 pages a second time. 32 (lost) + 47 (successful) = 79. `data/raw/insider_sells_2025_2026_2026-09-13.jsonl`. | 79 | 189 |
| 2026-09-13 | `/v2/news/?tags=bullish,bearish` — bulk pull, H9, 294 pages × limit=30, 8,801 records total | Approved by user ("test it out", following the stated ~294-credit estimate). Clean run, no rate-limit hits, no re-billing (learned from H8's overrun -- used the same incremental-save-on-every-page pattern). `data/raw/sentiment_news_2025_2026_2026-09-13.jsonl`. | 294 | 483 |
| 2026-09-13 | `/v2/filings/?holder_type=insider&transaction_type=buy&start=2025-01-01&end=2026-09-13&limit=1` | H8b pre-flight (insider BUYING, the mirror of H8's sell test -- approved by user, "try out the insider buying"), sizing the bulk-pull cost before committing. Result: `total_count=1767` -- a full pull at 30/page would be ~59 credits. | 1 | 484 |
| 2026-09-13 | `/v2/filings/?holder_type=insider&transaction_type=buy&start=2025-01-01&end=2026-09-13` — bulk pull, H8b, 60 pages × limit=30, 1,767 records total | Approved by user ("try out the insider buying"). Clean run, no rate-limit hits (used the same incremental-save-on-every-page pattern that fixed H8's earlier overrun). `data/raw/insider_buys_2025_2026_2026-09-13.jsonl`. | 60 | 544 |
| 2026-09-19 | `/v2/idx-total/?start=...&end=...` — 24 sequential 90-day windows, 2021-01-01 through 2026-09-01 | App-build session. User explicitly chose "Spend ~24 credits on idx-total" when asked directly, after the live schema was checked and confirmed 1 credit/call, max 90-day window, floor 2021-01-01 (docs/PRODUCT.md §21). `pipeline/appdata/fetch_idx_total.py`, run via `.venv/bin/python -m pipeline.appdata.fetch_idx_total`. 23 of 24 windows succeeded; the 24th (`end=2026-09-19`) returned 400 — free, not billed (`sectors_client.py`'s documented 400/401/403-are-free rule) — because the live API's real-world clock is one day behind this environment's stated date. | 23 | 567 |
| 2026-09-19 | `/v2/idx-total/?start=2026-09-02&end=2026-09-18` — diagnostic probe to find the real clock boundary after the above 400 | **Mistake, disclosed rather than hidden:** ran as an ad hoc one-off call to check whether `end=2026-09-18` would succeed where `2026-09-19` didn't. It succeeded and billed, but its response was only printed (`len(records)`), not saved — a real credit spent with nothing to show for it, my own error. | 1 | 568 |
| 2026-09-19 | `/v2/idx-total/?start=2026-09-02&end=2026-09-18` — re-run of the same window, this time saved | Necessary to actually capture the missing 13 days (2026-09-02 through 2026-09-18) after the mistake above discarded them. Appended to the existing `data/raw/idx_total_2026-09-19.json`, giving a complete, gap-free, non-duplicated 1,373-day series, 2021-01-01–2026-09-18. **Total for this task: 25 credits, not the ~24 approved** — the extra 1 is the discarded diagnostic call directly above, not a second, hidden overrun. | 1 | 569 |
| 2026-09-20 | `/v2/mining/commodities/{Coal,Nickel,Gold,Copper}/price/?start_year=2024&end_year=2026` (4 calls) | App-build session. User approved the step-4 credit plan (2026-09-20). Schema-checked first: 1 credit per call, monthly data, 3-year max range. `pipeline/appdata/fetch_commodity_prices.py` -> `data/raw/commodity_prices_2026-09-20.json` (38/38/33/38 records). Gives the extractive lens a real derived comparison (commodity price trend next to the miners' own price position). Narrowed from all 7 commodities to the 4 with >=4 listed miners (Coal 55, Nickel 10, Gold 9, Copper 4), so 4 credits not ~7. Valid commodity names were discovered with one deliberately invalid request (`/mining/commodities/zzzz/price/`), a 400 treated as free per the documented rule; not confirmed against the portal. | 4 | 573 |
| 2026-09-20 | `/v2/mining/commodities/Coal%20(HBA%201)/price/?start_year=2024&end_year=2026` | Test whether the HBA coal benchmark series is fresher than plain `Coal`, whose data ends 2026-02-15 (seven months before today); coal is 55 of 68 listed miners. Result: no, it also ends 2026-02-15, so plain Coal stays. Saved to `data/raw/commodity_prices_hba_2026-09-20.json` (38 records). A first attempt failed client-side on an unencoded space in the URL before any request was sent, so it billed nothing. | 1 | 574 |
| 2026-09-20 | `/v2/daily/{symbol}/?start=2026-06-12&end=2026-09-09` (20 symbols, 1 call each) | Sectors-vs-Yahoo price cross-check (owed per docs/PLAN.md 8.3 / BACKLOG.md): the research layer's outcome prices come from the Yahoo dev cache, so a seeded, stratified sample (7 large, 7 mid, 6 small by market cap) was checked against Sectors' own daily closes. Schema-checked first: 1 credit/call, 90-day max window. Kept at exactly 20 credits to stay within the standing <=20 limit. `pipeline/dev/crosscheck_sectors_prices.py` -> `data/raw/sectors_daily_crosscheck_2026-09-20.json`. **Result: 1,218 matched trading days, zero differences (Yahoo `close` equals Sectors `close` on every matched day); 2 of 20 symbols (UANG, CNKO) each missing one Yahoo day (min coverage 98.4%).** Scope limit: one recent 90-day window, 20 symbols; older years in the cache are unchecked. | 20 | 594 |
| 2026-09-20 | `/v2/corporate-actions/?start=2026-08-21&end=2026-10-20&type=dividend,upcoming_dividend,agm,right_issue,stock_split` (1 call, 5 types) | Dated corporate-actions section on stock pages. Schema-checked first: **billed 1 credit per requested type (default all 7 = 7), not 1 per call**; my earlier "1 credit" estimate was wrong and is corrected here. Skipped `bonus` and `warrant` (rare). `pipeline/appdata/fetch_corporate_actions.py` -> `data/raw/corporate_actions_2026-09-20.json`: dividend 9, upcoming_dividend 7, agm 160, right_issue 4, stock_split 1 rows. Meant to be re-pulled near the final refresh, since events announced later are not in this file. | 5 | 599 |

**Total spent as of 2026-09-20: 599 credits.**

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

**Remaining: ~401** (1,000 budget − 599 spent as of 2026-09-20).

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
