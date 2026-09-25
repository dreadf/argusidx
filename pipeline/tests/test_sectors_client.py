"""
Tests for pipeline/sectors_client.py's `.env` loader -- a bug here
silently produces a broken Authorization header with no hint at the
cause beyond a generic Cloudflare 403 (docs/credit_ledger.md already
records one such mis-sourced-.env incident).
"""
import os

import pytest

import pipeline.sectors_client as sectors_client
from pipeline.sectors_client import _load_dotenv, paginate


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SECTORS_API_KEY", raising=False)


def test_plain_assignment(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SECTORS_API_KEY=abc123\n")
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "abc123"


def test_export_prefix(tmp_path):
    env = tmp_path / ".env"
    env.write_text("export SECTORS_API_KEY=abc123\n")
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "abc123"


def test_double_quoted_value(tmp_path):
    env = tmp_path / ".env"
    env.write_text('SECTORS_API_KEY="abc123"\n')
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "abc123"


def test_single_quoted_value(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SECTORS_API_KEY='abc123'\n")
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "abc123"


def test_trailing_comment_unquoted(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SECTORS_API_KEY=abc123  # from the portal\n")
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "abc123"


def test_quoted_value_with_trailing_comment(tmp_path):
    """Regression: found by /code-review 2026-09-12. A quoted value
    followed by a trailing comment satisfied neither the old
    startswith/endswith-quote check nor the comment-stripping branch,
    leaving literal quote characters embedded in the parsed value."""
    env = tmp_path / ".env"
    env.write_text('SECTORS_API_KEY="abc123" # from the portal\n')
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "abc123"


def test_does_not_override_real_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTORS_API_KEY", "already-set")
    env = tmp_path / ".env"
    env.write_text("SECTORS_API_KEY=from_file\n")
    _load_dotenv(env)
    assert os.environ["SECTORS_API_KEY"] == "already-set"


def test_missing_file_is_a_noop(tmp_path):
    _load_dotenv(tmp_path / "does_not_exist.env")
    assert "SECTORS_API_KEY" not in os.environ


# --- paginate's `on_page` incremental-save callback (added 2026-09-13
# after a real cost-overrun incident during H8's own bulk data pull --
# see docs/credit_ledger.md and the module docstring above. NOTE: that
# pull itself used a one-off scratch script with its own manual
# pagination, not this function -- `on_page` is this project's fix so
# a FUTURE large paginate() call doesn't repeat the same mistake, not a
# claim that H8's analysis module (which only reads an already-fetched
# file, no API calls) calls paginate() itself) ---------------------


def test_paginate_returns_all_pages(monkeypatch):
    pages = [
        {"results": [{"id": 1}, {"id": 2}], "pagination": {"has_next": True, "next_offset": 2}},
        {"results": [{"id": 3}], "pagination": {"has_next": False}},
    ]
    calls = iter(pages)
    monkeypatch.setattr(sectors_client, "get", lambda path, params: next(calls))

    result = paginate("/fake/", {}, page_size=2)
    assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_paginate_calls_on_page_with_each_pages_results_in_order(monkeypatch):
    pages = [
        {"results": [{"id": 1}, {"id": 2}], "pagination": {"has_next": True, "next_offset": 2}},
        {"results": [{"id": 3}], "pagination": {"has_next": False}},
    ]
    calls = iter(pages)
    monkeypatch.setattr(sectors_client, "get", lambda path, params: next(calls))

    seen_pages = []
    result = paginate("/fake/", {}, page_size=2, on_page=seen_pages.append)

    assert seen_pages == [[{"id": 1}, {"id": 2}], [{"id": 3}]]
    # on_page must not change what paginate itself returns.
    assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_paginate_without_on_page_is_unaffected(monkeypatch):
    pages = [{"results": [{"id": 1}], "pagination": {"has_next": False}}]
    calls = iter(pages)
    monkeypatch.setattr(sectors_client, "get", lambda path, params: next(calls))

    result = paginate("/fake/", {}, page_size=10)
    assert result == [{"id": 1}]


def test_paginate_start_offset_resumes_without_refetching_earlier_pages(monkeypatch):
    """A resumed pull must request offset=start_offset first, not 0 --
    otherwise already-billed pages get re-fetched (and re-billed) on
    retry, exactly the gap found by /code-review, 2026-09-13."""
    seen_offsets = []

    def fake_get(path, params):
        seen_offsets.append(params["offset"])
        if params["offset"] == "20":
            return {"results": [{"id": 3}], "pagination": {"has_next": False}}
        return {"results": [{"id": 99}], "pagination": {"has_next": True, "next_offset": 999}}

    monkeypatch.setattr(sectors_client, "get", fake_get)

    result = paginate("/fake/", {}, page_size=10, start_offset=20)
    assert seen_offsets == ["20"]
    assert result == [{"id": 3}]
