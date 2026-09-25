"""Build data/app/news_sentiment.json from the purchased news corpus.

Source: data/raw/sentiment_news_*.jsonl (Sectors news, Bullish/Bearish
tags supplied by Sectors, not by us). Pure aggregation, no model: how many
articles, how many mention each stock, and the bullish/bearish split, with
the market-wide split kept next to every stock's own so a stock's figure is
never shown bare (docs/PRODUCT.md §0 rule 3).

Two denominators exist and are both kept, labelled, because they differ
(75% of articles vs 69% of stock mentions: an article that names several
companies counts once per company in the second). The stock page compares
like with like (mentions vs mentions).

Run: .venv/bin/python -m pipeline.appdata.build_news_sentiment
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pipeline.appdata.common import APP_DIR, RAW_DIR, SENTIMENT_GLOB, UNIVERSE_GLOB, latest_dated_file

TOP_N = 200


def tag_of(tags: list[str]) -> str | None:
    """'bullish' or 'bearish' when exactly one of the two is tagged."""
    lowered = {t.lower() for t in tags}
    bull, bear = "bullish" in lowered, "bearish" in lowered
    if bull == bear:
        return None
    return "bullish" if bull else "bearish"


def aggregate(articles: list[dict]) -> dict:
    """Pure aggregation over parsed article dicts (title-free, testable)."""
    per_symbol: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    n_articles = n_bull_articles = n_mentions = n_bull_mentions = 0
    multi_symbol = 0
    first = last = None
    for art in articles:
        tag = tag_of(art.get("tags") or [])
        if tag is None:
            continue
        n_articles += 1
        n_bull_articles += tag == "bullish"
        ts = art.get("timestamp")
        if ts:
            first = ts if first is None or ts < first else first
            last = ts if last is None or ts > last else last
        symbols = art.get("symbols") or []
        multi_symbol += len(symbols) > 1
        for sym in symbols:
            n_mentions += 1
            n_bull_mentions += tag == "bullish"
            per_symbol[sym][0 if tag == "bullish" else 1] += 1
    return {
        "n_articles": n_articles,
        "bullish_articles_pct": round(100 * n_bull_articles / n_articles, 1) if n_articles else None,
        "n_mentions": n_mentions,
        "bullish_mentions_pct": round(100 * n_bull_mentions / n_mentions, 1) if n_mentions else None,
        "n_symbols": len(per_symbol),
        "multi_symbol_articles": multi_symbol,
        "first_date": first[:10] if first else None,
        "last_date": last[:10] if last else None,
        "per_symbol": {sym: {"bullish": b, "bearish": r} for sym, (b, r) in per_symbol.items()},
    }


def main() -> None:
    source = latest_dated_file(RAW_DIR, SENTIMENT_GLOB)
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    names = {r["symbol"]: r["company_name"] for r in json.loads(universe_path.read_text())}
    articles = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    agg = aggregate(articles)
    per_symbol = agg.pop("per_symbol")
    ranked = sorted(per_symbol.items(), key=lambda kv: (-(kv[1]["bullish"] + kv[1]["bearish"]), kv[0]))
    out = {
        "as_of": agg["last_date"],
        "source_file": source.name,
        "note": "Bullish/Bearish tags are supplied by Sectors, not computed by ArgusIDX.",
        **agg,
        "most_covered": [
            {"symbol": sym, "company_name": names.get(sym), **counts, "mentions": counts["bullish"] + counts["bearish"]}
            for sym, counts in ranked[:TOP_N]
        ],
        "by_symbol": per_symbol,
    }
    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(APP_DIR / "news_sentiment.json")
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {source.name}")
    print(f"articles={agg['n_articles']} bullish={agg['bullish_articles_pct']}% | mentions={agg['n_mentions']} bullish={agg['bullish_mentions_pct']}% | symbols={agg['n_symbols']}")
    for row in out["most_covered"][:5]:
        print(f"  {row['symbol']:10s} {row['bullish']:>4d} bullish {row['bearish']:>4d} bearish")


if __name__ == "__main__":
    main()
