"""
Tests for pipeline/appdata/build_news_sentiment.py. The figures asserted
against the real corpus (8,801 articles, 15,820 mentions, 795 symbols,
BBCA 389/208) are the ones EXPERIMENT.md and the UI quote; a mismatch means
the aggregation drifted.
"""
from pipeline.tests.raw_data import needs_raw
import json

import pytest

from pipeline.appdata.build_news_sentiment import aggregate, tag_of
from pipeline.appdata.common import RAW_DIR, SENTIMENT_GLOB, latest_dated_file


def _art(tags, symbols, ts="2026-06-01T10:00:00"):
    return {"tags": tags, "symbols": symbols, "timestamp": ts}


def test_tag_requires_exactly_one_of_bullish_bearish():
    assert tag_of(["Dividend", "Bullish"]) == "bullish"
    assert tag_of(["bearish"]) == "bearish"
    assert tag_of(["Dividend"]) is None
    assert tag_of(["Bullish", "Bearish"]) is None


def test_multi_symbol_article_counts_once_as_article_and_once_per_symbol_as_mention():
    result = aggregate([_art(["Bullish"], ["A.JK", "B.JK"]), _art(["Bearish"], ["A.JK"])])
    assert result["n_articles"] == 2
    assert result["n_mentions"] == 3
    assert result["bullish_articles_pct"] == 50.0
    assert result["bullish_mentions_pct"] == pytest.approx(66.7)
    assert result["per_symbol"]["A.JK"] == {"bullish": 1, "bearish": 1}
    assert result["multi_symbol_articles"] == 1


def test_untagged_articles_are_ignored_and_dates_bound_the_window():
    result = aggregate([_art([], ["A.JK"]), _art(["Bullish"], ["A.JK"], "2026-05-16T07:24:00"), _art(["Bullish"], ["A.JK"], "2026-09-12T22:54:00")])
    assert result["n_articles"] == 2
    assert (result["first_date"], result["last_date"]) == ("2026-05-16", "2026-09-12")


@needs_raw
def test_real_corpus_matches_the_quoted_figures():
    source = latest_dated_file(RAW_DIR, SENTIMENT_GLOB)
    articles = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    result = aggregate(articles)
    assert result["n_articles"] == 8801
    assert result["n_mentions"] == 15820
    assert result["n_symbols"] == 795
    assert result["bullish_articles_pct"] == 75.1
    assert result["bullish_mentions_pct"] == 69.1
    assert result["per_symbol"]["BBCA.JK"] == {"bullish": 389, "bearish": 208}
