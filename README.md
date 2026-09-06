# ArgusIDX

Built for the **Sectors Hackathon 2026** (Track 03: Market Intelligence).

An evidence layer for Indonesian retail investors: for a given stock,
what does the data actually say about the situation it's in — measured
against IDX history, explained in plain language — without ever telling
anyone what to do.

**Status: early build. Product not yet functional.** One hypothesis
tested so far (see `EXPERIMENT.md`). This README will be rewritten as the
product takes shape; right now it documents the state of the repo
honestly rather than describing something that doesn't exist yet.

## Why this exists

Indonesia added 4.28 million new stock market investors in 2025 alone,
while capital-market-specific financial literacy sits around 1.55%.
Herding, influencer-driven pump-and-dump ("saham gorengan"), and IPO
hype are all documented, regulator-acknowledged problems. Existing
tools — screeners, broker-flow trackers, ownership dashboards — all
display signals as if they work. **None of them publish whether they
actually do.** That's the gap this project occupies: not a new signal,
but honest, tested evidence about the signals people already believe.

## What's here right now

- `pipeline/stats.py` — reusable statistics (rank correlation,
  volatility, drawdown, quintiles) used by every hypothesis test.
- `pipeline/hypotheses/h1_free_float.py` — the first tested hypothesis,
  fully reproducible. Run it:
  ```
  python -m pipeline.hypotheses.h1_free_float
  ```
- `pipeline/dev/fetch_yahoo_prices.py` — development-time-only price
  fetcher (Yahoo Finance, free). **Never used by the shipped product** —
  see `RULES.md` for why.
- `data/raw/` — Sectors API data actually purchased with real credits.
  Committed to the repo, never gitignored.
- `EXPERIMENT.md` — the living research log. One entry per hypothesis:
  what was tested, how, what was found, what it means, and what's next.
- `RULES.md` — the hackathon's constraints and this project's process
  rules.
- `BACKLOG.md` — the to-do list, by category.
- `docs/PLAN.md` — the full project plan: product design, hypothesis
  register, credit budget, schedule, and the reasoning behind every
  decision `RULES.md` and `BACKLOG.md` only summarize.
- `docs/credit_ledger.md` — every Sectors API credit spent, and why.

## Data sources

- **Sectors API** (sectors.app) — the core, required data source per
  the hackathon rules. Coverage: IDX (Indonesia), also SGX/KLSE/Mining
  though unused here.
- **Yahoo Finance** — development-time only, for cheaply testing a
  hypothesis before spending Sectors credits on it. Never ships.

## Disclaimer

*(To be finalized — see BACKLOG.md, Compliance.)* This project is an
information and analysis tool. It does not provide financial advice and
does not recommend buying, selling, or holding any security. All
findings describe historical relationships in past data and are not
guarantees about the future.
