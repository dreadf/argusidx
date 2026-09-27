"""Tests for pipeline/hypotheses/r1_warning_overlap.py, on synthetic sets."""
from pipeline.hypotheses.r1_warning_overlap import find_merges, jaccard


def test_jaccard_known_values():
    assert jaccard({1, 2, 3}, {2, 3, 4}) == 2 / 4
    assert jaccard(set(), set()) == 0.0
    assert jaccard({1}, {1}) == 1.0
    assert jaccard({1}, {2}) == 0.0


def test_find_merges_picks_the_more_specific_as_the_survivor():
    sets = {
        "broad": {1, 2, 3, 4, 5, 6, 7, 8},
        "narrow": {1, 2, 3, 4, 5, 6},  # jaccard = 6/8 = 0.75, subset of broad
        "unrelated": {100, 101},
    }
    merges = find_merges(sets)
    assert len(merges) == 1
    specific, general, j = merges[0]
    assert specific == "narrow" and general == "broad"
    assert abs(j - 0.75) < 1e-9


def test_find_merges_empty_when_nothing_overlaps_enough():
    sets = {"a": {1, 2}, "b": {3, 4}, "c": {5, 6}}
    assert find_merges(sets) == []
