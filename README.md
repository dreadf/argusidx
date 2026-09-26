# ArgusIDX

Built for the **Sectors Hackathon 2026** (Track 03: Market Intelligence).

An evidence layer for Indonesian retail investors: for a given stock,
what does the data actually say about the situation it's in — measured
against IDX history, explained in plain language — without ever telling
anyone what to do.

Indonesia added 4.28 million new stock market investors in 2025 alone,
while capital-market-specific financial literacy sits around 1.55%.
Herding, influencer-driven pump-and-dump ("saham gorengan"), and IPO
hype are all documented, regulator-acknowledged problems. Existing
tools — screeners, broker-flow trackers, ownership dashboards — all
display signals as if they work. **None of them publish whether they
actually do.** That's the gap this project occupies: not a new signal,
but honest, tested evidence about the signals people already believe.

## Built on the Sectors API

Every company fact in the app comes from the Sectors API: fundamentals and
price bands for all 962 companies, official suspension records with IDX's
own stated reasons, insider filings, corporate actions, sub-industry peer
groups, banking and mining fields, IDX total market cap, and
sentiment-tagged news. Ten endpoints, each pulled once, committed in
`data/raw/`, and logged credit by credit in `docs/credit_ledger.md` (599 of
1,000 credits as of 2026-09-20). Nothing calls Sectors at request time, so
judging does not depend on the API being reachable.

The one input that does not come from Sectors is historical price series,
used only to measure price outcomes ("what happened 90 days or a year
later"). Daily prices through Sectors cost 1 credit per 90-day window,
about 4 to 5 credits per stock per year, so a multi-year history for 962
companies would far exceed the whole 1,000-credit budget. Those outcomes
are computed once from a free public source (Yahoo Finance), frozen as
derived facts, and cross-checked against Sectors' own daily closes (see
Data provenance). Every endpoint, and what it powers, is in the table
under "Sectors endpoints".

## What's actually here

A working, statically-generated web app covering all 962 IDX-listed
companies, plus the research pipeline that feeds it:

- **Beranda** (`/`) — what has been tested (the honesty scoreboard
  headline), nine "situations" you can be in, today's market (IDX total
  market cap against its 2021–present history, breadth, biggest movers),
  and two anomaly flags.
- **Situasi** (`/situasi`, nine detail pages) — "what usually happens" in a
  circumstance (a stock that fell a lot, a loss-making company, an IPO,
  a price-spike suspension, a large dividend, thin free float, beating
  gold or deposits), each as one chart with a worked "how to read it"
  example and its limits. Natural frequencies ("88 of 100"), never a
  forecast for one stock.
- **Jelajah** (`/jelajah`) — one place, four tabs: Peringkat (six
  descriptive rankings), Sektor (11 sectors, each with its stock list),
  Tanda (four anomaly flags with their full company lists), Berita (news
  volume and Bullish/Bearish split). Old `/peringkat`, `/sektor`,
  `/tanda` URLs redirect here.
- **Temuan** (`/temuan`, one detail page per finding) — the honesty
  scoreboard: 17 popular market beliefs, tested against IDX data, one
  tab per outcome, each row carrying its real sample size, test period,
  and the one limit that matters most. `/temuan/cara-kami-menguji`
  explains the method.
- **Stock pages** (`/saham/[kode]`, all 962, statically generated) — a
  short "Ringkasan" on top (six one-line comparisons, no combined
  verdict), then price range, sector comparison with ROE history, news,
  its resolved standing on the free-float finding (H1), insider activity
  against the market, suspension history, sector-specific ratios
  (banking/mining), corporate actions, and a 5-year "did this beat
  gold/the index/deposits" comparison.
- **Tanya** (`/tanya`) — ask a question about the data, follow-ups
  included. Facts are retrieved from the precomputed files (stock facts,
  tested findings, situations, market, glossary); an LLM (Gemini) may
  word the answer from them, and every number in its answer is checked
  against those facts. Each user gets 3 AI answers per 6 hours (signed
  cookie, plus a per-IP backstop); past that, or with no key, answers
  come from the same facts without AI.
- **Cari** (`/cari`, the magnifier in the header; a search box in the
  desktop sidebar) — find any of the 962 companies by code or name.
- **Watchlist** — saved locally on-device, no account.

**Architecture:** every number comes from precomputed JSON
(`pipeline/appdata/` → `data/app/*.json`); there is no database and
nothing to keep running. All 962 stock pages, Home, sector pages and the
findings detail pages are pre-built static HTML. A few listing pages
(`/jelajah`, `/jelajah/tanda`, `/temuan`, and a sector's stock list) read
their filters from the URL, so they render per request from the same JSON
files, and `/api/ask` is a route handler for the question box, which
falls back to deterministic template answers if the LLM is unavailable.
Nothing calls the Sectors API at request time. `next.config.ts` packages
`data/app/` with the server routes (verified in the build's trace files).

## Sectors endpoints

Every endpoint below is real, purchased data committed in `data/raw/`
— not a demo call:

| Endpoint | Used for |
|---|---|
| `/v2/companies/` (screener, paginated) | The core universe sweep — fundamentals, price bands, banking/insurance ratios, index membership, for all 962 companies |
| `/v2/free-float/` | Public-ownership percentage (an early standalone pull, since folded into the universe sweep) |
| `/v2/suspensions/` | Full IDX trading-suspension history with official reasons |
| `/v2/mining/companies/` | Commodity/company-type facts for the extractive lens |
| `/v2/filings/` | Insider buy/sell transactions — powers each stock page's insider-activity section |
| `/v2/news/` | Sentiment-tagged news, used in research (see `EXPERIMENT.md`, H9/H9b/H9c) |
| `/v2/idx-total/` | Daily total IDX market cap, 2021-01-01 to present — Home's one real trend chart |
| `/v2/mining/commodities/{name}/price/` | Monthly prices for coal, nickel, gold and copper, shown as a dated 12-month trend on listed miners' pages |
| `/v2/corporate-actions/` | Dated dividends, AGMs, rights issues and stock splits per company, with the window and pull date shown on every use |
| `/v2/daily/{symbol}/` | Daily closes for 20 sampled symbols, used to cross-check the research price history (see Data provenance) |

Full endpoint-by-endpoint cost and approval trail: `docs/credit_ledger.md`.

## Real engineering gotchas hit building this

- **Cloudflare fronts the Sectors API.** Requests without a browser-like
  `User-Agent` get error 1010, which reads as a generic 403.
- **The individual-stock daily-data floor is 2021-01-01.** Below it,
  queries return empty arrays rather than errors — and still bill.
- **`/v2/idx-total/`'s server-side clock ran a day behind** the date
  this environment reported as "today" — a request for the final,
  most-recent day returned 400 ("future date") until the window end was
  pulled back by one day. Worth checking directly rather than assuming
  a client and server agree on "today."
- **Peer-group cascade:** companies are grouped sub_industry → industry
  → sub_sector → sector, using the most specific level with ≥15
  members, so no comparison ever runs on a group too small to mean
  anything.
- **LQ45 index membership** wasn't in the original field list — required
  a live schema check to discover `indices` as a filterable field before
  the 4th anomaly flag (low free float within LQ45) could ship at all.

## Data provenance

Two kinds of data ship in the app. This table says which is which, so
nothing is mistaken for something it isn't.

| Feature | Source | Live or frozen |
|---|---|---|
| Stock snapshot, peer comparison, sector context, 4 anomaly flags, rankings, market breadth, `/sektor` | Sectors `/v2/companies/` sweep | Snapshot dated in the UI |
| Suspension history | Sectors `/v2/suspensions/` | Snapshot |
| Corporate actions (dividends, AGMs, rights issues, splits) | Sectors `/v2/corporate-actions/` | Snapshot, window stated on the page |
| Insider activity | Sectors `/v2/filings/` | Snapshot |
| Banking and mining lenses, commodity price trends for miners | Sectors `/v2/companies/`, `/v2/mining/companies/`, `/v2/mining/commodities/{name}/price/` | Snapshot (commodity series end Feb 2026 for coal, nickel, copper; the date is shown) |
| IDX total market cap chart | Sectors `/v2/idx-total/` | Snapshot |
| Where a stock sits on the free-float finding (H1) | Sectors market cap and free float, applied to the H1 result | Snapshot |
| **Findings scoreboard verdicts** (`/temuan`) | Sectors fundamentals as predictors; **outcomes measured on research price history** (18 of 19 rows; only H4, dividend cuts, uses Sectors data alone) | **Frozen research results** |
| **Beat gold / index / deposit comparison** | Research price history, gold and index series | **Frozen, dated 2026-09-12** |
| **IPO board and recovery / drawdown base rates** | Research price history plus Sectors listing fields | **Frozen, dated 2026-09-13** |

**Why price outcomes are "frozen research results":** they are the one
place the app does not use Sectors data, mainly because of cost: daily
prices through Sectors are 1 credit per 90-day window (`docs/credit_ledger.md`),
far past the budget for a multi-year, 962-company history (the gold series
has its own note in the "Beat gold" section of `docs/PRODUCT.md`). The price
history is a development-time input from a free public source. Raw prices
are never committed (`data/dev_cache/` is gitignored), the frontend never
imports or calls it, and no live screen depends on it. What ships are
derived facts (percentages, counts, medians) computed once at build time.
Without Sectors the app loses its stock pages, flags, lenses, peer
comparison and market views; without the price history it would keep all of
those and lose only the frozen outcome summaries.

**Price cross-check against Sectors (2026-09-20, 20 credits):** a seeded,
stratified sample of 20 symbols (7 large, 7 mid, 6 small by market cap)
over the latest 90-day window found the research closes identical to
Sectors' own daily closes on all 1,218 matched trading days; two symbols
each lacked one research-price day (minimum coverage 98.4%). Scope, stated
plainly: this validates the price source for a recent window and a
sample. It does not re-run any finding, and older years in the cache
were not checked. Code: `pipeline/dev/crosscheck_sectors_prices.py`;
raw responses: `data/raw/sectors_daily_crosscheck_2026-09-20.json`.

All Sectors-sourced data in this repo is provided by
[Sectors](https://sectors.app).

## Repo layout

- `pipeline/stats.py` — shared statistics (rank correlation, volatility,
  drawdown, quintiles) used by every hypothesis test.
- `pipeline/hypotheses/` — one module per hypothesis, each reproducible
  from a single command, printing numbers that match `EXPERIMENT.md`.
- `pipeline/appdata/` — turns purchased Sectors data into the plain JSON
  files (`data/app/*.json`) the frontend reads. Nothing here calls
  Sectors live at request time — every pull is a one-off, approved,
  logged command.
- `frontend/` — the Next.js app (App Router, TypeScript, Tailwind).
- `data/raw/` — Sectors API data actually purchased with real credits.
  Committed to the repo, never gitignored.
- `data/app/` — precomputed JSON the frontend reads directly.
- `EXPERIMENT.md` — the living research log: what was tested, how, what
  was found, what it means, and what's next. 20 hypotheses tested as of
  2026-09-19; nulls are logged with the same honesty as positives.
- `RULES.md` — the hackathon's constraints and this project's process
  rules.
- `BACKLOG.md` — the to-do list, by category.
- `docs/PLAN.md` — the full project plan and reasoning behind every
  decision `RULES.md`/`BACKLOG.md` only summarize.
- `docs/PRODUCT.md` — the product spec: what each screen shows and why.
- `docs/credit_ledger.md` — every Sectors API credit spent, and why.

## Setup

Requires Python 3.11+ and Node 20+.

```
# Pipeline (stdlib-only, pytest for the test suite)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest pipeline/tests/

# Rebuild data/app/*.json from the committed data/raw/ sweep — order
# matters, build_stock_pages.py depends on everything before it:
.venv/bin/python -m pipeline.appdata.peer_groups
.venv/bin/python -m pipeline.appdata.build_market
.venv/bin/python -m pipeline.appdata.build_rankings
.venv/bin/python -m pipeline.appdata.build_flags
.venv/bin/python -m pipeline.appdata.build_suspensions
.venv/bin/python -m pipeline.appdata.build_lens_banking
.venv/bin/python -m pipeline.appdata.build_lens_extractive
.venv/bin/python -m pipeline.appdata.build_beat_gold
.venv/bin/python -m pipeline.appdata.build_base_rates
.venv/bin/python -m pipeline.appdata.build_ipo_boards
.venv/bin/python -m pipeline.appdata.build_sector_breakdown
.venv/bin/python -m pipeline.appdata.build_commodity_context
.venv/bin/python -m pipeline.appdata.build_corporate_actions
.venv/bin/python -m pipeline.appdata.build_h1_applicability
.venv/bin/python -m pipeline.appdata.build_insider_activity
.venv/bin/python -m pipeline.appdata.build_idx_total
.venv/bin/python -m pipeline.appdata.build_news_sentiment
.venv/bin/python -m pipeline.appdata.build_roe_history
.venv/bin/python -m pipeline.appdata.build_findings
.venv/bin/python -m pipeline.appdata.build_situations
.venv/bin/python -m pipeline.appdata.build_stock_pages

# Frontend
cd frontend
npm install
npm run dev

# Everything a submission needs in one command (tests, secret scan,
# production build, and a check that the app still works with the LLM off)
scripts/preflight.sh
```

`build_beat_gold.py`, `build_base_rates.py`, `build_ipo_boards.py` and
`build_situations.py` read from `data/dev_cache/` (research price history, dev-only, gitignored — the only
dependency in this chain not committed to the repo). On a fresh clone
they need re-fetching first via `pipeline/dev/fetch_yahoo_prices.py`;
every other builder above runs on committed `data/raw/` alone. `data/app/*.json` is already committed too, so none of
this is required just to run the frontend — only to regenerate it.

Live Sectors API calls (not required to reproduce anything already
committed in `data/raw/`) need `SECTORS_API_KEY` in a repo-root `.env`
(gitignored, copy `.env.example`). The Ask layer's optional Gemini
answers need `GEMINI_API_KEY` in `frontend/.env.local` (optional
`GEMINI_MODEL`, `ASK_COOKIE_SECRET`); the app is fully functional, by
design, with it unset.

## Disclaimer

This project is an information and analysis tool. It does not provide
financial advice, and does not recommend buying, selling, or holding any
security. Nothing here should be read as a signal to act on. All
findings describe historical, statistical relationships measured in past
IDX data — they are not predictions, and they are not guarantees about
future performance. Each finding stands on its own evidence and its own
stated limits; findings are never combined into a single score or
verdict. If you're making a financial decision, that decision is yours
alone — consult a licensed financial professional.
