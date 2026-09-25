"""
H9: does the tone of news coverage (Bullish vs. Bearish, as tagged by
Sectors' own news classification) predict a stock's short-term return?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline) -- see the "much weaker than usual"
caveat below on what explore/holdout even means here.

Why this exists (docs/PLAN.md's H9, previously "candidate, uncosted,
not pre-registered"; researched properly 2026-09-13 at the user's
request): sentiment is a genuinely different axis from everything else
tested in this project (technical price patterns, fundamental
financials) -- literature review (see EXPERIMENT.md's citations) finds
real, if short-lived, IDX-specific sentiment effects. Sectors' own
`/v2/news/` endpoint already tags articles Bullish/Bearish/Neutral and
links most of them to a specific IDX symbol, removing the need to build
any NLP/sentiment-classification pipeline ourselves.

Pre-registered hypothesis (committed before looking at any holdout
result): a stock named in a Bullish-tagged article earns a HIGHER
short-term return than a stock named in a Bearish-tagged article, over
the following 10 and 20 calendar days. Falsified if: no consistent
direction (Bullish > Bearish) in holdout at either horizon, or if it
reverses.

⚠️ MAJOR LIMITATION, found only after pulling the data (not knowable
from the schema alone) -- stated up front rather than buried: the
actual `/v2/news/` corpus, once pulled, covers only **2026-05-16 to
2026-09-12 (~4 months)**, not the multi-year span every other
hypothesis in this project uses. This is NOT the date range requested
(no `start`/`end` filter was applied, expecting a longer history) --
it appears to be the full extent of what Sectors' news corpus actually
contains as of this pull. Consequences, disclosed rather than papered
over:
    - The usual calendar-YEAR explore/holdout split (2025 vs 2026) used
      by H1/H5/H10/H11/H13 is not possible -- there's less than one full
      year of data. Explore/holdout here is a WITHIN-WINDOW split
      (first half of the 4-month window vs. second half), a much weaker
      form of holdout discipline than this project's other hypotheses.
      Treat any "confirmed" result here as considerably less trustworthy
      than H1/H4/H5/H10's confirmations until a longer news history is
      available to re-test against.
    - Only short horizons (10/20 calendar days) are tested -- a 90-day
      horizon like H11/H13 use would leave almost no usable holdout
      rows given how little of the window is far enough in the past.

Predictor-before-outcome: trivially satisfied -- an article's own
publish timestamp is the predictor date; the outcome window is strictly
the calendar time after it.

Row construction: one row per (article, symbol) pair, for every
Bullish- or Bearish-tagged (never both -- verified 0 of 8,801 articles
carry both tags) article that names at least one IDX symbol (7,737 of
8,801, 87.9%). **A real, disclosed limitation:** 2,428 of these articles
name MORE than one symbol (e.g. broad market-wide news) -- each named
company gets an identical sentiment reading from that one article,
which is not independent information the way a company-specific article
would be. Not deduplicated or weighted down here; stated plainly instead.

Reuses `pipeline.hypotheses.h11_suspension_underperformance`'s
`_baseline_at_or_before` for the same reason H11/H11b/H8 do: an
article's baseline price must come from at-or-before its own timestamp,
not from either direction (`nearest_value`'s usual convention, kept for
the forward-looking lookup only).

Trial count: adds 2 pre-registered tests (the two horizons) to the
project total.

Data (already purchased -- no further Sectors call needed for this
module):
    data/raw/sentiment_news_2025_2026_2026-09-13.jsonl (294 credits,
        2026-09-13 -- see docs/credit_ledger.md).
    data/dev_cache/prices_5y.json -- Yahoo, dev-only.

Run:
    .venv/bin/python -m pipeline.hypotheses.h9_news_sentiment
    .venv/bin/python -m pipeline.hypotheses.h9_news_sentiment --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.hypotheses.h11_suspension_underperformance import _baseline_at_or_before
from pipeline.stats import median_of, nearest_value, welch_ttest

REPO_ROOT = Path(__file__).resolve().parents[2]
NEWS_PATH = REPO_ROOT / "data" / "raw" / "sentiment_news_2025_2026_2026-09-13.jsonl"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

MAX_GAP_DAYS = 5  # tighter than other modules' 10 -- these are short (10-20d) horizons
RETURN_FIELD = "adjclose"
HORIZONS_DAYS = [10, 20]
MIN_GROUP_SIZE = 10
DATA_AS_OF = datetime(2026, 9, 13, tzinfo=timezone.utc)
# Midpoint of the actual pulled window (2026-05-16 to 2026-09-12) --
# NOT a calendar-year boundary like every other hypothesis here, because
# the news corpus itself doesn't span a full year. See module docstring.
SPLIT_DATE = datetime(2026, 7, 15, tzinfo=timezone.utc)


def _parse_articles(path: Path) -> list[dict]:
    """One row per (article, symbol) pair for single-sentiment,
    symbol-tagged articles."""
    rows = []
    with path.open() as f:
        for line in f:
            d = json.loads(line)
            tags = [t.lower() for t in (d.get("tags") or [])]
            is_bull, is_bear = "bullish" in tags, "bearish" in tags
            if is_bull == is_bear:  # neither, or (never observed) both
                continue
            symbols = d.get("symbols") or []
            if not symbols:
                continue
            ts = d.get("timestamp")
            if not ts:
                continue
            try:
                t0 = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            sentiment = 1 if is_bull else -1
            for sym in symbols:
                rows.append({"sym": sym, "t0": t0, "sentiment": sentiment})
    return rows


def build_rows(articles: list[dict], prices5y: dict) -> list[dict]:
    rows = []
    for a in articles:
        entry = prices5y.get(a["sym"])
        if not entry:
            continue
        p0 = _baseline_at_or_before(entry, a["t0"], field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        row: dict = {"sym": a["sym"], "sentiment": a["sentiment"]}
        usable = False
        for h in HORIZONS_DAYS:
            t1 = a["t0"] + timedelta(days=h)
            if t1 > DATA_AS_OF:
                row[f"ret_{h}d"] = None
                continue
            p1 = nearest_value(entry, t1, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
            row[f"ret_{h}d"] = (p1 / p0 - 1) if p1 is not None else None
            if row[f"ret_{h}d"] is not None:
                usable = True
        if usable:
            rows.append(row)
    return rows


def print_horizon(rows: list[dict], horizon: int, phase_label: str) -> None:
    key = f"ret_{horizon}d"
    bullish = [r[key] for r in rows if r["sentiment"] == 1 and r[key] is not None]
    bearish = [r[key] for r in rows if r["sentiment"] == -1 and r[key] is not None]
    print(f"\n{phase_label} -- +{horizon}d horizon")
    for label, group in [("Bullish-tagged", bullish), ("Bearish-tagged", bearish)]:
        if not group:
            print(f"  {label:<16}: n=0")
            continue
        mean_ret = sum(group) / len(group)
        median_ret = median_of([{"v": v} for v in group], "v")
        print(f"  {label:<16}: n={len(group):>5}  mean={mean_ret:+.1%}  median={median_ret:+.1%}")

    if len(bullish) >= MIN_GROUP_SIZE and len(bearish) >= MIN_GROUP_SIZE:
        t = welch_ttest(bullish, bearish)
        print(f"  Welch t (bullish vs bearish): t={t.t:+.2f}  diff={t.diff:+.1%}")
    else:
        print(f"  Welch t: insufficient data (need n>={MIN_GROUP_SIZE} each)")


def run_phase(rows: list[dict], phase_label: str) -> None:
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} (article, symbol) rows with usable data\n{'=' * 70}")
    for h in HORIZONS_DAYS:
        print_horizon(rows, h, phase_label)


def main() -> None:
    articles = _parse_articles(NEWS_PATH)
    prices5y = json.loads(PRICES_5Y_PATH.read_text())

    explore_articles = [a for a in articles if a["t0"] < SPLIT_DATE]
    holdout_articles = [a for a in articles if a["t0"] >= SPLIT_DATE]
    print(
        f"H9 -- {len(articles)} total (article, symbol) rows "
        f"({len(explore_articles)} before {SPLIT_DATE.date()} [explore], "
        f"{len(holdout_articles)} on/after [holdout])"
    )
    print(
        "⚠️  Explore/holdout here is a within-window date split, NOT the calendar-year\n"
        "split every other hypothesis in this project uses -- the news corpus only\n"
        "spans ~4 months total. See module docstring for the full disclosure."
    )

    print("\nH9 -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_articles, prices5y)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_articles, prices5y)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 2 pre-registered horizons. Given the weak\n"
            "within-window holdout (not a genuinely separate time period the way other\n"
            "hypotheses' year-based holdouts are), treat any result here as a lead\n"
            "worth re-testing once more news history accumulates, not a fully\n"
            "confirmed finding on the same footing as H1/H4/H5/H10."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
