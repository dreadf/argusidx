"""Tests for pipeline/appdata/fetch_corporate_actions_history.py's window
logic and resume-path resolution. No network calls."""
from datetime import date

import pipeline.appdata.fetch_corporate_actions_history as fetch_mod
from pipeline.appdata.fetch_corporate_actions_history import START, WINDOW_DAYS, build_windows, resolve_out_path


def test_windows_cover_every_day_once():
    start, end = date(2022, 1, 1), date(2022, 6, 30)
    windows = build_windows(start, end, WINDOW_DAYS)
    assert windows[0][0] == start
    assert windows[-1][1] == end
    for (_a_start, a_end), (b_start, _b_end) in zip(windows, windows[1:]):
        assert (b_start - a_end).days == 1


def test_window_count_matches_plan_estimate():
    windows = build_windows(START, date(2026, 9, 27), WINDOW_DAYS)
    assert len(windows) == 20


def test_no_window_exceeds_the_documented_max():
    windows = build_windows(START, date(2026, 9, 27), WINDOW_DAYS)
    for start, end in windows:
        assert (end - start).days < WINDOW_DAYS


def test_resolve_out_path_resumes_into_an_existing_file_regardless_of_its_date(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_mod, "RAW_DIR", tmp_path)
    existing = tmp_path / "corporate_actions_history_2026-09-20.json"
    existing.write_text("{}")
    # Regression: a path keyed by date.today() would point at a brand-new
    # file here instead of resuming the one already on disk.
    assert resolve_out_path() == existing


def test_resolve_out_path_creates_a_new_dated_file_when_none_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_mod, "RAW_DIR", tmp_path)
    path = resolve_out_path()
    assert path.parent == tmp_path
    assert not path.exists()
    assert path.name.startswith("corporate_actions_history_")
