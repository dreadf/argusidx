"""
H9b: does SENTIMENT DISAGREEMENT -- both bullish- and bearish-tagged
articles about the same stock in the same window -- predict HIGHER
subsequent volatility than one-sided coverage?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists: a follow-up angle on H9's own data, proposed by the
user after H9 came back inconclusive on DIRECTION (bullish vs bearish).
This tests a different axis entirely -- not which way sentiment leans,
but whether the market disagreeing about a stock (bulls and bears both
writing about it at once) is itself informative about how choppy the
stock gets next. Same underlying dataset as H9 (no new Sectors cost),
same limitation inherited: the news corpus only spans ~4 months
(2026-05-16 to 2026-09-12), so explore/holdout here is a within-window
split, not a genuine calendar-year holdout -- see h9_news_sentiment.py's
docstring for the full disclosure, which applies identically here.

Pre-registered hypothesis (committed before looking at any holdout
result): a symbol-window with BOTH a bullish- and a bearish-tagged
article earns HIGHER realized volatility over the following 10 trading
days than a symbol-window with only one-sided coverage. Falsified if:
no consistent direction in holdout, or if it reverses.

Design choice made up front to avoid pseudo-replication (the H14/H15
lesson, applied here before writing any code rather than discovered
after): articles are grouped into non-overlapping 20-day bins per
symbol (`_news_bins.bin_articles_by_symbol`), not scored article-by-
article -- otherwise two articles about the same stock three days apart
would generate two heavily overlapping "windows" that aren't
independent observations.

Predictor-before-outcome: the bin's article set is drawn entirely from
articles published within the bin; the volatility outcome is measured
strictly starting at the bin's end date.

Reuses `h9_news_sentiment._parse_articles` (article-level rows) and
`pipeline.stats.annualized_volatility`/`nearest_index` rather than
reimplementing them.

Trial count: adds 1 pre-registered test to the project total (single
horizon, unlike H9's two).

Data (already purchased -- no further Sectors call needed):
    data/raw/sentiment_news_2025_2026_2026-09-13.jsonl,
    data/dev_cache/prices_5y.json -- Yahoo, dev-only.

Run:
    .venv/bin/python -m pipeline.hypotheses.h9b_sentiment_dispersion_volatility
    .venv/bin/python -m pipeline.hypotheses.h9b_sentiment_dispersion_volatility --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pipeline.hypotheses._news_bins import bin_articles_by_symbol
from pipeline.hypotheses.h9_news_sentiment import NEWS_PATH, SPLIT_DATE, _parse_articles
from pipeline.stats import annualized_volatility, median_of, nearest_index, welch_ttest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

BIN_DAYS = 20
FORWARD_TRADING_DAYS = 10
MIN_GROUP_SIZE = 10


def _forward_volatility(entry: dict, start, n_trading_days: int, field: str = "close") -> float | None:
    idx = nearest_index(entry, start, max_gap_days=10)
    if idx is None:
        return None
    closes = entry[field][idx : idx + n_trading_days + 1]
    if len(closes) < 5:  # too few points for a meaningful stdev
        return None
    vol = annualized_volatility(closes)
    return vol if vol == vol else None  # NaN guard


def build_rows(bins: list[dict], prices5y: dict) -> list[dict]:
    rows = []
    for b in bins:
        entry = prices5y.get(b["sym"])
        if not entry:
            continue
        has_bull = any(a["sentiment"] == 1 for a in b["articles"])
        has_bear = any(a["sentiment"] == -1 for a in b["articles"])
        if not (has_bull or has_bear):
            continue
        vol = _forward_volatility(entry, b["bin_end"], FORWARD_TRADING_DAYS)
        if vol is None:
            continue
        rows.append({"sym": b["sym"], "mixed": has_bull and has_bear, "bin_end": b["bin_end"], "vol": vol})
    return rows


def run_phase(rows: list[dict], phase_label: str) -> None:
    mixed = [r["vol"] for r in rows if r["mixed"]]
    one_sided = [r["vol"] for r in rows if not r["mixed"]]
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} symbol-windows ({len(mixed)} mixed, {len(one_sided)} one-sided)\n{'=' * 70}")
    for label, group in [("Mixed (bull+bear)", mixed), ("One-sided", one_sided)]:
        if not group:
            print(f"  {label:<20}: n=0")
            continue
        mean_v = sum(group) / len(group)
        median_v = median_of([{"v": v} for v in group], "v")
        print(f"  {label:<20}: n={len(group):>4}  mean vol={mean_v:.1%}  median vol={median_v:.1%}")
    if len(mixed) >= MIN_GROUP_SIZE and len(one_sided) >= MIN_GROUP_SIZE:
        t = welch_ttest(mixed, one_sided)
        print(f"  Welch t (mixed vs one-sided): t={t.t:+.2f}  diff={t.diff:+.1%}")
    else:
        print(f"  Welch t: insufficient data (need n>={MIN_GROUP_SIZE} each; have {len(mixed)} mixed, {len(one_sided)} one-sided)")


def main() -> None:
    articles = _parse_articles(NEWS_PATH)
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    bins = bin_articles_by_symbol(articles, bin_days=BIN_DAYS)

    explore_bins = [b for b in bins if b["bin_end"] < SPLIT_DATE]
    holdout_bins = [b for b in bins if b["bin_end"] >= SPLIT_DATE]
    print(
        f"H9b -- {len(bins)} total symbol-windows "
        f"({len(explore_bins)} ending before {SPLIT_DATE.date()} [explore], "
        f"{len(holdout_bins)} on/after [holdout])"
    )
    print(
        "⚠️  Same within-window-split caveat as H9 -- the news corpus only spans\n"
        "~4 months, so this is not a genuine calendar-year holdout. See\n"
        "h9_news_sentiment.py's module docstring for the full disclosure."
    )

    print("\nH9b -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_bins, prices5y)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_bins, prices5y)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nSame weak-holdout caveat as H9: treat any result here as a lead\n"
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
