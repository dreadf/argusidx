"""
Tests for pipeline/appdata/build_h1_applicability.py.
"""
from pipeline.appdata.build_h1_applicability import (
    SIGNIFICANT_SIZE_BUCKETS,
    build_h1_applicability,
)


def _row(symbol, market_cap=None, free_float=None):
    return {"symbol": symbol, "query_values": {"market_cap": market_cap, "free_float": free_float}}


def test_excludes_rows_missing_market_cap_or_free_float():
    rows = [
        _row("A.JK", market_cap=100, free_float=0.5),
        _row("B.JK", market_cap=None, free_float=0.5),
        _row("C.JK", market_cap=100, free_float=None),
    ]
    result = build_h1_applicability(rows)
    assert set(result.keys()) == {"A.JK"}


def test_four_size_buckets_roughly_even():
    # 12 companies, evenly spread market caps -> 3 per size bucket.
    rows = [_row(f"S{i}.JK", market_cap=i, free_float=0.5) for i in range(12)]
    result = build_h1_applicability(rows)
    from collections import Counter
    counts = Counter(v["size_bucket"] for v in result.values())
    assert counts == {"smallest": 3, "small_mid": 3, "mid_large": 3, "largest": 3}


def test_significant_flag_matches_the_documented_three_of_four_buckets():
    rows = [_row(f"S{i}.JK", market_cap=i, free_float=0.5) for i in range(12)]
    result = build_h1_applicability(rows)
    for v in result.values():
        assert v["size_bucket_significant"] == (v["size_bucket"] in SIGNIFICANT_SIZE_BUCKETS)
    assert SIGNIFICANT_SIZE_BUCKETS == {"smallest", "small_mid", "largest"}


def test_float_tercile_computed_within_size_bucket_not_globally():
    # 12 rows / 4 size buckets divides evenly (3 each), so market_cap
    # 1-3 lands cleanly in "smallest" and 10-12 cleanly in "largest" -
    # avoids quintiles()'s remainder-spreading behavior mixing groups
    # across a bucket boundary at smaller row counts.
    rows = [
        # smallest-cap bucket: free floats 0.1 (low), 0.5 (mid), 0.9 (high)
        _row("LOW1.JK", market_cap=1, free_float=0.1),
        _row("LOW2.JK", market_cap=2, free_float=0.5),
        _row("LOW3.JK", market_cap=3, free_float=0.9),
        # filler rows for the two middle size buckets
        _row("MID1.JK", market_cap=4, free_float=0.5),
        _row("MID2.JK", market_cap=5, free_float=0.5),
        _row("MID3.JK", market_cap=6, free_float=0.5),
        _row("MID4.JK", market_cap=7, free_float=0.5),
        _row("MID5.JK", market_cap=8, free_float=0.5),
        _row("MID6.JK", market_cap=9, free_float=0.5),
        # largest-cap bucket: free floats 0.05 (low), 0.4 (mid), 0.99 (high) -
        # overlaps in raw value with the smallest-cap bucket on purpose, so a
        # BUG that computes terciles globally instead of within-bucket would
        # misclassify at least one of these.
        _row("HIGH1.JK", market_cap=10, free_float=0.05),
        _row("HIGH2.JK", market_cap=11, free_float=0.4),
        _row("HIGH3.JK", market_cap=12, free_float=0.99),
    ]
    result = build_h1_applicability(rows)
    assert result["LOW1.JK"]["size_bucket"] == "smallest"
    assert result["HIGH1.JK"]["size_bucket"] == "largest"
    assert result["LOW1.JK"]["free_float_tercile"] == "low"
    assert result["LOW2.JK"]["free_float_tercile"] == "mid"
    assert result["LOW3.JK"]["free_float_tercile"] == "high"
    assert result["HIGH1.JK"]["free_float_tercile"] == "low"
    assert result["HIGH2.JK"]["free_float_tercile"] == "mid"
    assert result["HIGH3.JK"]["free_float_tercile"] == "high"
