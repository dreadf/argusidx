# Data dictionary

What every file under `data/` actually contains: what one row is, whether
it's a snapshot or a time series, units, provenance, and the limitations
that have already caused real mistakes in this project. Read this before
writing a new hypothesis module, not after.

## The rule that matters most

> **For any hypothesis of the form "X predicts Y", X must be measured
> strictly *before* the window over which Y is measured.**

Snapshot columns (below) are a single current value with no history and
**cannot** satisfy this rule: using one to predict a historical outcome
is circular (a stock that already crashed has a low P/E *because* it
crashed; ranking by today's P/E and checking 2022 returns rediscovers
that). Yearly columns (`field[YYYY]`, arriving with Phase 1) measure a
specific past date and can.

This is also why **H1 is a contemporaneous association, not a
prediction**: its only predictor, `free_float`, is a snapshot. Product
copy must never describe it as predictive.

## `data/raw/free_float_2026-09-06.json`

**Purchased from Sectors** (`/v2/free-float/`, 10 credits). Never
gitignored.

- **One row per company, one number, no date.** `{symbol, company_name,
  free_float}`. **Snapshot: DANGEROUS to reuse as history.** Ownership
  shifts over time; this file cannot tell you what free float was in
  2022, only what it is as of 2026-09-06. `/v2/free-float/` has no date
  parameter: there is no way to buy a historical version from Sectors.
  SGX's screener has no `free_float` field at all; KLSE's is far
  thinner. **This limitation is structural, not a gap to be filled later.**
- `free_float` is a decimal: `0.45` = 45% publicly held.
- **Verified profile:** 961 rows, 0 nulls, median 0.232, range
  [0.001, 1.0]. Exactly one company at 1.0 (`HKMU.JK`).
- Consumer: hypothesis testing (H1, H1b). Also useful for the product's
  Stock lookup, with an "as of" date shown: see the UI tag requirement
  in `BACKLOG.md`.

## `data/raw/market_cap_2026-09-06.json`

**Purchased from Sectors** (5 pages, 5 credits). Never gitignored.

- **One row per company, one number, no date.** `{symbol, company_name,
  query_values: {market_cap}}`. **Snapshot: equally DANGEROUS as
  `free_float`, for the same reason, and this is easy to miss because
  it doesn't get discussed as often.** Market cap moves *daily* with
  price. `h1_free_float.py`'s size-control double-sort is safe only
  because it runs entirely on the same 1-year window: that's luck, not
  design. A future test that combines a size bucket with a multi-year
  check must use a dated market cap, not this file.
- **Verified: 962 rows, one more than `free_float`.** The extra row is
  `BIMA.JK`, present in market cap but not free float. Every symbol in
  `free_float` is in `market_cap`, so joins keyed on `free_float` are
  unaffected.
- Consumer: H1's size-confound control.

## `data/dev_cache/prices_1y.json` and `prices_5y.json`

**Free, from Yahoo Finance**, via `pipeline/dev/fetch_yahoo_prices.py`.
**Gitignored** (re-fetchable, unlike the two purchased files above: if
missing, regenerate with `.venv/bin/python -m
pipeline.dev.fetch_yahoo_prices --range 1y` / `--range 5y`). **Never
used by the shipped product**: see `RULES.md`.

**Schema switched 2026-09-09** (from Yahoo's batched `/v7/finance/spark`
endpoint to per-symbol `/v8/finance/chart`: see the fetcher's own
docstring for why: `spark` was silently dropping a large share of
history for exactly the small/thin-float symbols this project cares
about most). Both files now share **one schema**, unlike the old
per-range shapes:

    {symbol: {"timestamps": [...], "close": [...], "adjclose": [...]}}

All three arrays are the same length and index-aligned; a day missing
either `close` or `adjclose` is dropped from all three before caching,
so no consumer needs to guard against a length mismatch. `close` is the
plain traded price (what H1 uses throughout: see `EXPERIMENT.md`'s note
on why H1 deliberately keeps raw price, not a dividend-adjusted one);
`adjclose` is dividend-and-split-adjusted. **H5 uses both, for different
sub-calculations, not one or the other**: `close` for its size proxy
(`shares × price`: using `adjclose` here would retroactively shrink
market cap for stocks that later pay more dividends, a direction-specific
bias, not just noise), `adjclose` for its return ratio (which must
include dividends to measure actual investment return). See the comment
in `h5_value_size.py`'s `build_rows_for_year` for the full reasoning.

- `prices_1y.json`: **Verified: 913 of 961 symbols, ≥120 bars each**
  (threshold enforced by the fetcher itself, so nothing reaching a
  consumer can fail it: same dead-code note as before, now against
  `len(entry["close"])` rather than `len(closes)`). Up from 853 under
  the old endpoint.
- `prices_5y.json`: **Verified: 887 of 961 symbols, ≥400 bars each.**
  Up from 810 under the old endpoint.
- **Any hypothesis module written or updated against this file must use
  the new schema**: `prices[symbol]["close"]` / `["adjclose"]` /
  `["timestamps"]`, not a bare list or `[timestamp, close]` pairs. As of
  this note, `h1_free_float.py`, `h1_stress.py`,
  `h1b_float_drawdown_size.py`, and `h5_value_size.py` still expect the
  **old** schema and will silently produce `n=0` or crash with
  `ValueError: too many values to unpack` against the regenerated cache
: updating them is separate, tracked follow-up work (`BACKLOG.md`),
  not yet done as of this fetcher fix landing.

### The trap that broke H1's own robustness check

**A short array is NOT the same signal as "the price didn't move."**
`pipeline/stats.no_move_fraction()` measures flat days *among the bars
that exist*: a day the stock never traded produces no bar at all, so
it's invisible to that measure, not counted as "no movement."

This is why H1's published "checked and ruled out" claim about stale
prices does not hold up: `no_move_fraction` cannot see the exact failure
mode it was built to catch. Re-checked using actual bar counts, the
effect decays toward zero as required trading activity rises: see
`EXPERIMENT.md`'s H1 entry for the numbers. **Never use
`no_move_fraction` as a liquidity or trading-frequency measure again.**
If you need to know whether a stock actually traded, count its bars
(`len(prices_1y[symbol]["close"])`: note the schema switch above) or
use a Sectors volume field (`tags` in the screener response, or
`/v2/most-traded/`): not this.

**A second wrinkle, substantially, not fully, resolved by the
`chart`-endpoint fetcher fix (2026-09-09):** a short array can still
mean the stock genuinely traded rarely, *or* that Yahoo simply doesn't
have good IDX coverage for it; bar count alone still cannot tell these
apart *in general*. `GOTO.JK`: one of the most heavily traded stocks on
IDX, and the specific case this caveat was written about: went from
**128 of ~242 days** (old `spark` endpoint) to **244 of ~249 days**
(new `chart` endpoint): the coverage gap for this particular symbol is
gone. **Careful wording, per the standing instruction not to overclaim:
"substantially resolved," not "resolved."** This fixes the *dev-cache*
data only. `docs/PLAN.md` §8.3 still requires any Yahoo-validated result
to be confirmed against real Sectors prices before it ships: that
obligation is completely unchanged by this fix, and a symbol could
still, in principle, have a genuine remaining Yahoo gap this fetcher
switch didn't happen to catch.

## `data/dev_cache/benchmarks_5y.json`

**Yahoo, dev-only, never ships** (`pipeline/dev/fetch_benchmark_prices.py`,
new 2026-09-12). Same `{timestamps, close, adjclose}` schema as
`prices_5y.json`, keyed by ticker instead of IDX symbol: `^JKSE` (IDX
Composite index), `GC=F` (gold futures, USD/troy oz), `USDIDR=X`
(USD/IDR exchange rate). Built for H16's benchmark comparisons: gold in
rupiah is `GC=F` × `USDIDR=X` at the same date, not a single ticker.
Verified date ranges cover the same ~2021-09 to present window as
`prices_5y.json` (1199/1257/1301 bars respectively: daily, more than
`prices_5y.json`'s per-stock counts since these three never have a
non-trading gap the way a thinly-traded IDX stock can).

## `data/raw/phase0_field_density_2026-09-06.json`

**Purchased from Sectors** (1 credit). Never gitignored.

- The single billed response from the Phase 0 test: does one
  `/v2/companies/` query return multiple requested fields at once?
  **Answer: yes**: `pe_ttm`, `roe_ttm`, and `market_cap` all appeared in
  `query_values` for every row.
- Not itself reusable for anything beyond that answer (5 rows, not a
  universe pull): but its `pagination` object already answers how
  `paginate()` should terminate (`has_next` / `next_offset`), so Phase 1
  doesn't need to rediscover that.

## `data/raw/universe_2026-09-07.json`

**Purchased from Sectors** (5 pages, 5 credits: `pipeline/hypotheses/phase1_universe_sweep.py`).
Never gitignored.

- **962 rows, one per company.** Each row is `{symbol, company_name,
  query_values: {...48 fields...}}`: both snapshot fields (for the
  product's Stock lookup) and yearly `field[YYYY]` fields 2021–2025 (for
  hypothesis testing), pulled in one sweep. See the snapshot↔yearly
  mapping below for which field to use for which purpose.
- **Cross-checked against the purchased `free_float_2026-09-06.json`:
  zero disagreements** across 961 common symbols: real validation that
  Sectors' screener and dedicated free-float endpoint agree.
- **Coverage is uneven, and that unevenness is itself informative, not
  a data quality problem to fix.** Verified counts (of 962): `pe_ttm`
  863, `roe_ttm`/`roa_ttm` 860, `der_mrq` 716, `yield_ttm` 487,
  `payout_ratio` 326, yearly fields ~830–890 at `[2024]`. Loss-making or
  non-dividend-paying companies genuinely lack these fields: H4/H5 must
  report their sample size against 962, not assume full coverage.
- **`tags` was not fetched**: the sweep query omitted it despite the
  original plan calling for it. See `BACKLOG.md`'s open "liquidity /
  coverage-gap question" for why this matters and what was considered
  instead (`/v2/most-traded/` turned out to only cover the top 5–10
  tickers per day, not the full universe).

## `data/raw/universe_2026-09-12.json`: re-sweep, expanded field list

**Purchased from Sectors, approved 2026-09-12** (1-credit pre-flight +
5-page/5-credit sweep: `pipeline/hypotheses/phase1_full_query_test.py`
then `phase1_universe_sweep.py`, field list in the shared
`pipeline/hypotheses/_universe_fields.py`). Never gitignored. Supersedes
`universe_2026-09-07.json` for anything using the new fields; the older
file is kept, not deleted, since existing hypothesis modules (H1/H1b/H5)
were written against it and re-pointing them is a separate, deliberate
step, not an automatic consequence of this sweep landing.

- **962 rows, same shape, 83 `query_values` fields** (up from 48): all
  verified present in a live response (pre-flight, `docs/credit_ledger.md`
  2026-09-12), not just the schema doc. Adds, per the "one sweep, four
  jobs" plan: `industry`/`sub_industry` (finer peer groups than
  `sub_sector` alone: fixes the 207 companies previously stranded in an
  oversized `Basic Materials`/`Properties & Real Estate` sector-level
  group), 8 price-band pairs (`ytd`/`52_w`/`90_d`/`all_time` × `low`/`high`,
  each with a price and a date), and `earnings[YYYY]` (unlocks H4's
  payout-ratio-per-year calculation). Also pulled, not previously used:
  `market_cap_rank`, `esg_score`, `forward_pe`, `dividend_yield_avg`,
  `yearly_mcap_change`, `cash_payout_ratio`, `ps_ttm`, `dar_mrq`,
  `employee_num`, `last_close_price`, `daily_close_change`,
  `last_ex_dividend_date`.
- **`tags`/`indices`/`affiliates` still not fetched: deliberately, this
  time.** Verified against the live schema (not assumed): these require
  the `in` operator against a specific value list, not `is not null` like
  every other field here. The full tag vocabulary isn't verified yet
  (would need its own costed `/v2/tags/` call): guessing a partial list
  risks silently missing any company whose tags aren't in the guess,
  worse than leaving it unfetched. `BACKLOG.md`'s open question about what
  `tags` actually contains is still open, not resolved by this sweep.
- **Free-float drift found, not a bug:** cross-checked against the same
  purchased `free_float_2026-09-06.json` the 2026-09-07 sweep checked
  against zero-disagreement: this time **36 of 961 common symbols
  disagree**, some substantially (e.g. `CBMF.JK` 0.0306 → 0.24). Not a
  query or parsing error: the query shape and cross-check logic are
  unchanged from the zero-disagreement run five days earlier.
  ⚠️ **Investigated 2026-09-13.** Pilot (1 credit, approved:
  `docs/credit_ledger.md`): pulled `/v2/filings/` for `CBMF.JK` over
  2026-09-01→09-12 to see whether an insider/institutional filing
  explained its jump. **Zero filings returned.**
  **A follow-up check that session ran (comparing `last_close_price`
  null→populated across the drift symbols) was a false lead and has
  been retracted here**: `last_close_price` is `null` for **all 962
  rows** in the 2026-09-07 sweep, not just the drift set, because that
  field was never part of that earlier sweep's query at all (it was
  added in the 2026-09-12 expanded field list, `_universe_fields.py`).
  Comparing it across the two sweeps was comparing "not fetched" against
  "fetched," not a real suspension/dormancy signal: caught by checking
  the full population before trusting the pattern, not before writing it
  down once. **Broader probe run afterward (8 more credits, approved) on
  6 real, liquid drift symbols (ADRO/BBNI/BSDE/BULL/BHIT/BIRD) plus 2
  zero-drift controls (AKRA/AMMN), same window:** all 6 drifting symbols
  came back with **zero filings**; the zero-drift control AKRA had 6
  small filings (individual stakes of 0.02%–0.27%) whose combined
  magnitude roughly matches its own near-zero measured free_float
  change. **Conclusion: individually filed insider/institutional
  transactions are real and roughly consistent with SMALL free_float
  changes, but are far too small in magnitude to explain the multi-
  percentage-point jumps in this drift set** (`CBMF` +20.9pp, `ATIC`
  +11.5pp). Whatever drives those larger moves is not captured by
  `/v2/filings/` at all: plausibly a bulk/block trade below the
  individual-filing threshold, a corporate action, or a Sectors-side
  recalculation, none investigated further this session. **Practical
  takeaway: `/v2/filings/` does not look viable as a way to reconstruct
  a free-float time series for H1**: it may track small ownership moves
  but misses whatever causes the large swings this drift set is made
  of. Not pursued further. H1/H1b currently use the original purchased
  `free_float_2026-09-06.json` directly, not this sweep's copy, so they
  are unaffected either way.

## `data/raw/suspensions_2026-09-13.json`

**Purchased from Sectors, approved 2026-09-13** (20 credits: `/v2/suspensions/`,
full history, 20 pages × `limit=30`, flat 1 credit/call regardless of
filters, verified against the live schema). Never gitignored. 588
records, each `{symbol, suspension_date, reason, pdf_url}`.

- **437 of 588 (74%) are for "unusual price increase"** (UMA/cooling-
  down): the direct gorengan/pump marker; 10 more for unusual price
  decrease, 17 generic cooling-down. The rest are governance/reporting
  reasons (late financials, listing-fee arrears, going-concern doubt,
  etc.): see `BACKLOG.md` for the category breakdown.
- Unlocks H11 (suspension → underperformance) for real: was previously
  a costed-but-unpurchased candidate.
- Companion probe (4 more credits, same session): pulled `/v2/filings/`
  for 4 real "unusual price increase" suspensions to test whether
  insider filing activity shows a pattern beforehand. Found one: see
  `BACKLOG.md`'s write-up: but it is 4 case studies, not a validated
  finding; any future hypothesis built on this needs its own
  pre-registration and a control group, not this exploratory pass.
- **Legal caution, unchanged from the rest of this project:** any
  manipulation-adjacent write-up (H8, H11, this note) stays
  frequency-only in anything user-facing: named tickers appear here and
  in `BACKLOG.md` only as descriptive filing/suspension facts already
  public via IDX's own official notices, never as an accusation.

## `data/raw/mining_companies_2026-09-13.json`

**Purchased from Sectors, approved 2026-09-13** (13 credits:
`/v2/mining/companies/`, discovery list, 13 pages × `limit=30`, 1
credit/page. ⚠️ **Cost was mis-stated to the user as "1 credit" before
this call ran**: the endpoint itself is 1 credit per CALL, but 366
total mining entities at 30/page meant 13 calls; disclosed and corrected
in `docs/credit_ledger.md` immediately after, not caught beforehand.)
Never gitignored. 366 records, each `{slug, name, symbol, company_type,
key_operation, commodity_type}`.

- **Only 68 of 366 have an IDX `symbol`** (the rest are unlisted
  subsidiaries/holding entities): 55 coal, 10 nickel, 9 gold, 4 copper,
  2 silver, 1 aluminium, 1 zinc/lead (some companies have >1 commodity).
  Smaller than `docs/PLAN.md`'s original "≤205" estimate, which
  conflated the whole Basic Materials/Energy sectors with actual miners.
- **H12 probe finding, from the live schema (free, not a purchased
  call):** `/v2/mining/resources-reserves/{province}/` returns reserves
  at PROVINCE+COMMODITY+YEAR granularity, not per company. There is no
  per-listed-miner "years of reserves left" figure anywhere in this API
: see `BACKLOG.md`'s H12 entry for the full implication (blocks the
  plan's original "clean, uninvented arithmetic" pitch for this lens;
  needs a user decision on whether a province-level proxy is acceptable).

## `data/raw/insider_sells_2025_2026_2026-09-13.jsonl`

**Purchased from Sectors, approved 2026-09-13** (79 credits: see
`docs/credit_ledger.md`'s cost-overrun disclosure: estimated ~47, cost
79 in practice because a first attempt using the plain `paginate()`
helper billed 32 pages before hitting a 429 rate limit, then lost that
data because nothing was saved until the very end; the corrected,
incrementally-saving re-run re-billed those same 32 pages). Never
gitignored. JSONL (one filing per line, not a JSON array, to make
incremental writes trivial), 1,388 records: every `/v2/filings/`
record for `holder_type=insider&transaction_type=sell` between
2025-01-01 and 2026-09-13.

- **1 of 1,388 records has an impossible field value**:
  `share_percentage_transaction` of 930.2% for a `PPRI.JK` filing: a
  garbled/duplicate record sharing the same holder and date as an
  adjacent, sane record (0.93%). Excluded via a `<=100%` filter in
  `pipeline/hypotheses/h8_insider_selling_gorengan.py`, not silently
  included in any sum.
- Built specifically to test H8's cheap version (see `EXPERIMENT.md`):
  joined locally against the already-purchased suspension events to
  check whether insider selling before a price-spike suspension
  predicts a deeper crash. Result: falsified, reversed in holdout.
- **Prompted a real fix to shared infrastructure:** `pipeline/
  sectors_client.py`'s `paginate()` gained an optional `on_page`
  callback so a future large pull can persist each page immediately:
  the exact gap that caused this file's cost overrun. Later found (via
  `/code-review`) that `on_page` alone only prevents data LOSS, not
  RE-BILLING on retry: `paginate()` also gained a `start_offset`
  parameter to close that gap for good.

## `data/raw/sentiment_news_2025_2026_2026-09-13.jsonl`

**Purchased from Sectors, approved 2026-09-13** (294 credits: see
`docs/credit_ledger.md`). Never gitignored. JSONL, 8,801 records:
every `/v2/news/` article tagged `bullish` or `bearish` (never both:
verified 0 of 8,801 carry both tags). Clean pull, no rate-limit hits, no
re-billing: used the same incrementally-saving pattern H8's cost
overrun forced this project to adopt.

- **Real limitation, found only after pulling (not knowable from the
  schema):** the corpus covers only **2026-05-16 to 2026-09-12, ~4
  months**: not a multi-year span. Forces H9 (`EXPERIMENT.md`) into a
  within-window explore/holdout split instead of the calendar-year
  split every other hypothesis here uses.
- **7,737 of 8,801 (87.9%) link to at least one IDX symbol**; 2,428
  name more than one (broad market-wide news): each named company gets
  an identical sentiment reading from that one article, a disclosed,
  not-deduplicated limitation.
- Built to test H9 (does Bullish/Bearish tagging predict short-term
  returns): result: not confirmed, sign reverses at the 10-day horizon
  between explore and holdout despite huge holdout significance. See
  `EXPERIMENT.md`'s H9 entry.
- Also reused, at no extra Sectors cost, for three follow-up
  hypotheses on the same corpus (H9b sentiment dispersion → volatility,
  H9c news-attention volume → returns, H9d sentiment before
  suspensions): see `EXPERIMENT.md`. H9b and H9c both null (explore
  looked real, holdout didn't replicate); H9d descriptive-only, n too
  small for a formal test.

## `data/raw/insider_buys_2025_2026_2026-09-13.jsonl`

**Purchased from Sectors, approved 2026-09-13** (60 credits: see
`docs/credit_ledger.md`). Never gitignored. JSONL, 1,767 records:
every `/v2/filings/` record for `holder_type=insider&transaction_type=
buy` between 2025-01-01 and 2026-09-13. Clean run, no rate-limit hits,
no re-billing (used the same incrementally-saving pattern from the
start, learned from `insider_sells_...`'s cost-overrun incident).

- **1 of 1,767 records has an impossible field value** (`PPRI.JK`,
  `share_percentage_transaction` = 929.3%: the buy-side mirror of the
  sell file's own garbled record). Excluded via a `<=100%` filter in
  `pipeline/hypotheses/h8b_insider_buying_suspension.py`.
- **A real filter improvement over the sell file's own convention,
  found while building H8b:** the sell file's `0 < pct <= 100` filter
  silently drops any transaction whose `share_percentage_transaction`
  rounds to 0.0: checked directly and confirmed these are genuine
  small transactions, not bad data (e.g. BBCA buys of 0.001%-0.03% of
  its enormous share count, verified via matching
  `share_percentage_before`/`_after`). 281 of 1,767 buy records and 69
  of 1,388 sell records fall in this category. H8b's loader uses
  `pct <= 100` instead (keeps the 0.0 cases). Not backported to H8
  itself, to avoid re-touching an already-closed hypothesis.
- Built to test H8b (does insider buying before a price-spike
  suspension predict a *better* outcome, the mirror of H8), result:
  underpowered (holdout n=7), and the two horizons disagree with each
  other (30d says worse, 90d says better, both directionally consistent
  across explore/holdout on their own). See `EXPERIMENT.md`'s H8b entry.

## Snapshot ↔ yearly field mapping

Use the left column for "what is this stock like right now" (the
product). Use the right column for "what was this stock like at a
specific past date" (an experiment).

| Snapshot (current only) | Yearly equivalent |
|---|---|
| `pe_ttm` | `pe[YYYY]` |
| `roe_ttm` | `roe[YYYY]` |
| `der_mrq` | `debt_to_equity_ratio[YYYY]` |
| `yield_ttm`, `payout_ratio` | `total_dividend[YYYY]`, `total_yield[YYYY]` |
| `market_cap` | derivable from `outstanding_shares[YYYY]` × historical price |
| `free_float` | *(no yearly equivalent exists: see above)* |

## Snapshot fields: which are actually safe

Not every "current value" field is equally dangerous. Some describe
something that essentially never changes, so using today's value as if
it always applied is harmless:

- **Safe as snapshots** (static or near-static): `symbol`,
  `company_name`, `listing_date`, `sector`, `sub_sector`.
- **Not safe for questions about listing time**: `listing_board`. It is
  the company's *current* board, not its board at IPO. Stocks move
  boards, and 2021+ listings carry "Watchlist", a status assigned after
  listing. Grouping by it partly reflects where stocks ended up (see the
  caveat in `pipeline/appdata/build_ipo_boards.py`).
- **Dangerous as snapshots** (change constantly): `free_float`,
  `market_cap`, and by extension every `_ttm` / `_mrq` field: these
  describe *today*, and using them against a different time period
  reintroduces the exact anachronism this file exists to prevent.

## A minor, deliberately-undisturbed statistical note

`pipeline.stats.annualized_volatility` uses `statistics.pstdev`
(population standard deviation) rather than `stdev` (sample). This makes
published volatilities ~0.2% low in relative terms at typical sample
sizes: immaterial to any rank correlation in this project, since the
bias is nearly constant across stocks with similar history length. Not
worth a re-publish. Flagged here because the year-by-year check compares
years with very different sample sizes (n ranges roughly 100–240 trading
days across 2022–2026), where the bias is *not* perfectly uniform.

## Final refresh, 2026-10-08

One last pull before the submission freeze (credits and calls are logged in
`docs/credit_ledger.md`). Each step wrote a NEW dated file; the builders read
the latest one of each kind.

- `data/raw/universe_2026-10-08.json`: full `/v2/companies/` re-sweep, 962
  companies. Replaces the 2026-09-13 snapshot as the source of prices,
  fundamentals, flags, rankings and the stock pages.
- `data/raw/corporate_actions_2026-10-08.json`: dividend, upcoming dividend,
  AGM, rights issue and stock split events for 2026-09-08 to 2026-11-07.
- `data/raw/{ihsg,lq45,idxhidiv20,idx_total}_2026-10-08.json`: the previous
  series plus the days since the last pull (to 2026-10-07), via
  `pipeline/appdata/topup_index_series.py`, one call per series.
- `data/raw/insider_{buys,sells}_2025_2026_2026-10-08.jsonl`: the previous
  rows plus filings since 2026-09-10 (108 buys, 104 sells), deduplicated, via
  `pipeline/appdata/topup_insider_filings.py`.

Not refreshed, still at their earlier dates: suspensions (2026-09-13), news
sentiment (2026-09-13), commodity prices (2026-09-20; the API's coal series
ends 2026-02-15), foreign-flow lists and the fixed-date close snapshots (M5,
M6), which back already-published tests and dates that cannot change.
