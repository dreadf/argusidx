"""
H9c: does a burst of news COVERAGE VOLUME about a stock (regardless of
tone) predict its subsequent return -- distinct from H9's DIRECTION
test and H9b's DISAGREEMENT test?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists: attention-driven-trading literature (Barber & Odean,
"All That Glitters," 2008) finds that stocks getting unusual investor
attention see distinctive subsequent price behavior, independent of
whether the attention is positive or negative. This tests that on IDX
using the same H9 news corpus.

⚠️ REAL LIMITATION, stated up front: the pulled corpus was filtered to
`tags=bullish,bearish` only (see h9_news_sentiment.py's fetch script) --
there is no neutral-tagged news in this dataset. So "attention" here
means "count of bullish- or bearish-tagged articles," not true total
coverage volume (which would also need neutral-tagged articles, a
separate, uncosted pull). Stated as a proxy for attention, not a clean
measure of it.

Same corpus-span limitation as H9/H9b: ~4 months only
(2026-05-16 to 2026-09-12), within-window explore/holdout split, not a
genuine calendar-year holdout.

Pre-registered hypothesis (committed before looking at any holdout
result): a symbol-window with ABOVE-MEDIAN article count earns a
DIFFERENT subsequent return (10 trading days out) than a
below-median-count window -- direction not pre-specified (this is an
exploratory "does volume matter at all" test, not a directional one
like H9/H9b), so this is reported as: does |mean return| differ
materially and consistently in sign between explore and holdout for
either direction. Falsified if: no consistent sign in holdout.

Same binning as H9b (`_news_bins.bin_articles_by_symbol`, 20-day
non-overlapping windows per symbol) to avoid pseudo-replication from
scoring near-duplicate overlapping windows.

Predictor-before-outcome: the bin's article count is drawn entirely
from articles published within the bin; the return outcome is measured
strictly starting at the bin's end date.

Trial count: adds 1 pre-registered test to the project total.

Data (already purchased -- no further Sectors call needed):
    data/raw/sentiment_news_2025_2026_2026-09-13.jsonl,
    data/dev_cache/prices_5y.json -- Yahoo, dev-only.

Run:
    .venv/bin/python -m pipeline.hypotheses.h9c_news_attention_volume
    .venv/bin/python -m pipeline.hypotheses.h9c_news_attention_volume --confirm-holdout
"""
from __future__ import annotations

import json
import sys
import statistics
from pathlib import Path

from pipeline.hypotheses._news_bins import bin_articles_by_symbol
from pipeline.hypotheses.h11_suspension_underperformance import _baseline_at_or_before
from pipeline.hypotheses.h9_news_sentiment import NEWS_PATH, SPLIT_DATE, _parse_articles
from pipeline.stats import median_of, nearest_value, welch_ttest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

BIN_DAYS = 20
HORIZON_DAYS = 10
RETURN_FIELD = "adjclose"
MAX_GAP_DAYS = 5
MIN_GROUP_SIZE = 10


def build_rows(bins: list[dict], prices5y: dict) -> list[dict]:
    rows = []
    for b in bins:
        entry = prices5y.get(b["sym"])
        if not entry:
            continue
        p0 = _baseline_at_or_before(entry, b["bin_end"], field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        t1 = b["bin_end"]
        from datetime import timedelta

        p1 = nearest_value(entry, t1 + timedelta(days=HORIZON_DAYS), field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p1 is None:
            continue
        rows.append({"sym": b["sym"], "count": len(b["articles"]), "bin_end": b["bin_end"], "ret": p1 / p0 - 1})
    return rows


def run_phase(rows: list[dict], phase_label: str) -> None:
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} symbol-windows\n{'=' * 70}")
    if not rows:
        print("  n=0")
        return
    counts = [r["count"] for r in rows]
    threshold = statistics.median(counts)
    high = [r["ret"] for r in rows if r["count"] > threshold]
    low = [r["ret"] for r in rows if r["count"] <= threshold]
    print(f"  Median article count in window: {threshold:.0f}")
    for label, group in [("High attention (>median count)", high), ("Low attention (<=median count)", low)]:
        if not group:
            print(f"  {label:<32}: n=0")
            continue
        mean_ret = sum(group) / len(group)
        median_ret = median_of([{"v": v} for v in group], "v")
        print(f"  {label:<32}: n={len(group):>4}  mean={mean_ret:+.1%}  median={median_ret:+.1%}")
    if len(high) >= MIN_GROUP_SIZE and len(low) >= MIN_GROUP_SIZE:
        t = welch_ttest(high, low)
        print(f"  Welch t (high vs low attention): t={t.t:+.2f}  diff={t.diff:+.1%}")
    else:
        print(f"  Welch t: insufficient data (need n>={MIN_GROUP_SIZE} each; have {len(high)} high, {len(low)} low)")


def main() -> None:
    articles = _parse_articles(NEWS_PATH)
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    bins = bin_articles_by_symbol(articles, bin_days=BIN_DAYS)

    explore_bins = [b for b in bins if b["bin_end"] < SPLIT_DATE]
    holdout_bins = [b for b in bins if b["bin_end"] >= SPLIT_DATE]
    print(
        f"H9c -- {len(bins)} total symbol-windows "
        f"({len(explore_bins)} ending before {SPLIT_DATE.date()} [explore], "
        f"{len(holdout_bins)} on/after [holdout])"
    )
    print(
        "⚠️  'Attention' here = count of bullish/bearish-tagged articles only\n"
        "(no neutral-tagged news in this corpus -- see module docstring).\n"
        "Same within-window-split caveat as H9/H9b applies."
    )

    print("\nH9c -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_bins, prices5y)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_bins, prices5y)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nSame weak-holdout caveat as H9/H9b: treat any result here as a lead\n"
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
