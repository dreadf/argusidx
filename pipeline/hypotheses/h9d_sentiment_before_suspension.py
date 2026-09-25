"""
H9d: is a stock's news coverage more bearish than usual in the days
before it gets suspended for an "unusual price increase" -- the
gorengan-flavored suspension category H11/H8 already use?

STATUS: DESCRIPTIVE ONLY, not a pre-registered statistical test, and
not counted in the project trial counter -- stated up front, matching
H8's own honesty convention for its underpowered subgroup.

Why this exists: the third of three follow-up angles requested on H9's
own data. Conceptually the most direct tie to H8/H11's gorengan theme
("does the market notice something is off before a suspension"), but
severely constrained by data overlap, disclosed here rather than after
running it:

⚠️ SAMPLE SIZE PROBLEM, checked before building anything else: the news
corpus spans only 2026-05-16 to 2026-09-12 (~4 months), while the
"unusual price increase" suspension events span all of 2025-2026 (437
total, per H11/H8). Only suspension events falling INSIDE the news
window can be checked at all -- verified by direct count: 30 of 437
(6.9%). That is far below this project's usual MIN_GROUP_SIZE=10 for a
formal comparison, and there is no way to test the other 407 events
(2025's suspensions predate the news corpus entirely). This is reported
descriptively, with raw counts, not as a Welch t-test with a p-value --
a formal test on n=30 pre-registered after already knowing how small the
sample is would be exactly the kind of dressed-up-looking-rigor this
project's own discipline exists to avoid.

What's shown instead: for each of the 30 events, how many bullish- and
bearish-tagged articles about that symbol appeared in the 30 days
before the suspension date, compared to the OVERALL bullish/bearish
split across the entire corpus (as a rough population baseline -- not a
matched control group, stated as a limitation).

Predictor-before-outcome: trivially satisfied -- only articles strictly
before the suspension's own date count.

Reuses `h11_suspension_underperformance._parse_events` and
`h9_news_sentiment._parse_articles` rather than reimplementing either.

Data (already purchased -- no further Sectors call needed):
    data/raw/suspensions_2026-09-13.json,
    data/raw/sentiment_news_2025_2026_2026-09-13.jsonl.

Run:
    .venv/bin/python -m pipeline.hypotheses.h9d_sentiment_before_suspension
"""
from __future__ import annotations

import json
from datetime import timedelta, timezone
from pathlib import Path

from pipeline.hypotheses.h11_suspension_underperformance import _parse_events
from pipeline.hypotheses.h9_news_sentiment import NEWS_PATH, _parse_articles

REPO_ROOT = Path(__file__).resolve().parents[2]
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"

PRE_WINDOW_DAYS = 30


def main() -> None:
    suspensions = json.loads(SUSPENSIONS_PATH.read_text())
    events = _parse_events(suspensions)
    articles = _parse_articles(NEWS_PATH)

    by_sym: dict[str, list[dict]] = {}
    for a in articles:
        by_sym.setdefault(a["sym"], []).append(a)

    total_bull = sum(1 for a in articles if a["sentiment"] == 1)
    total_bear = sum(1 for a in articles if a["sentiment"] == -1)
    pop_bear_share = total_bear / (total_bull + total_bear)
    print(f"H9d -- population baseline: {total_bull} bullish / {total_bear} bearish articles ({pop_bear_share:.1%} bearish overall)\n")

    overlapping = [e for e in events if by_sym.get(e["sym"])]
    print(f"{len(events)} total 'unusual price increase' suspension events; checking pre-window coverage for all of them\n")

    rows = []
    for e in events:
        sym, t0 = e["sym"], e["t0"]
        window_start = t0 - timedelta(days=PRE_WINDOW_DAYS)
        arts = by_sym.get(sym, [])
        pre = [a for a in arts if window_start <= a["t0"] < t0]
        if not pre:
            continue  # no coverage in window -- most events, given corpus only spans ~4 months
        n_bull = sum(1 for a in pre if a["sentiment"] == 1)
        n_bear = sum(1 for a in pre if a["sentiment"] == -1)
        rows.append({"sym": sym, "date": t0.date(), "n_bull": n_bull, "n_bear": n_bear})

    print(f"Events WITH at least 1 tagged article in the 30-day pre-window: {len(rows)} of {len(events)}\n")
    print(f"{'Symbol':<10}{'Suspended':<14}{'Bullish':>8}{'Bearish':>8}")
    n_bear_only = n_bull_only = n_mixed = 0
    for r in rows:
        print(f"{r['sym']:<10}{str(r['date']):<14}{r['n_bull']:>8}{r['n_bear']:>8}")
        if r["n_bear"] > 0 and r["n_bull"] == 0:
            n_bear_only += 1
        elif r["n_bull"] > 0 and r["n_bear"] == 0:
            n_bull_only += 1
        elif r["n_bull"] > 0 and r["n_bear"] > 0:
            n_mixed += 1

    total_pre_bull = sum(r["n_bull"] for r in rows)
    total_pre_bear = sum(r["n_bear"] for r in rows)
    pre_bear_share = total_pre_bear / (total_pre_bull + total_pre_bear) if (total_pre_bull + total_pre_bear) else float("nan")

    print(f"\nOf {len(rows)} covered events: {n_bear_only} bearish-only, {n_bull_only} bullish-only, {n_mixed} mixed")
    print(f"Pre-window bearish share: {pre_bear_share:.1%} (population baseline: {pop_bear_share:.1%})")
    print(
        "\n⚠️ Descriptive only -- n too small (and not a matched control) for a formal\n"
        "test. Not counted in the project trial counter. See module docstring."
    )


if __name__ == "__main__":
    main()
