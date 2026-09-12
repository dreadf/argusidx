"""
Tests for pipeline/sectors_client.py's `.env` loader -- a bug here
silently produces a broken Authorization header with no hint at the
cause beyond a generic Cloudflare 403 (docs/credit_ledger.md already
records one such mis-sourced-.env incident).
"""
import os

import pytest

from pipeline.sectors_client import _load_dotenv


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
