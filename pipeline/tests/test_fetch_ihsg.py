"""Tests for pipeline/appdata/fetch_ihsg.py's window logic. No network calls:
this only checks that the 90-day windowing is gap-free and non-overlapping,
so a real run neither skips a day nor double-bills an overlapping window.
"""
from datetime import date

from pipeline.appdata.fetch_ihsg import WINDOW_DAYS, build_windows
from pipeline.guards import SECTORS_INDEX_FLOOR


def test_windows_cover_every_day_once():
    start, end = date(2019, 1, 2), date(2019, 6, 30)
    windows = build_windows(start, end, WINDOW_DAYS)
    assert windows[0][0] == start
    assert windows[-1][1] == end
    # No overlap and no gap: each window starts the day right after the
    # previous one ends.
    for (_a_start, a_end), (b_start, _b_end) in zip(windows, windows[1:]):
        assert (b_start - a_end).days == 1


def test_window_count_matches_plan_estimate():
    """Plan estimate: 2019-01-02 to 'today' is ~2,834 days / 90 -> 32 windows."""
    windows = build_windows(SECTORS_INDEX_FLOOR, date(2026, 9, 27), WINDOW_DAYS)
    assert len(windows) == 32


def test_no_window_exceeds_the_documented_max():
    windows = build_windows(date(2019, 1, 2), date(2026, 9, 27), WINDOW_DAYS)
    for start, end in windows:
        assert (end - start).days < WINDOW_DAYS
