"""Shared helpers across pipeline/appdata/ builders. A bug fixed here is
fixed everywhere - the same discipline pipeline/stats.py applies to the
research side (CLAUDE.md's repo-shape note)."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
APP_DIR = REPO_ROOT / "data" / "app"

UNIVERSE_GLOB = "universe_????-??-??.json"
SUSPENSIONS_GLOB = "suspensions_????-??-??.json"
INSIDER_BUYS_GLOB = "insider_buys_????_????_????-??-??.jsonl"
INSIDER_SELLS_GLOB = "insider_sells_????_????_????-??-??.jsonl"
IDX_TOTAL_GLOB = "idx_total_????-??-??.json"
IHSG_GLOB = "ihsg_????-??-??.json"
COMMODITY_PRICES_GLOB = "commodity_prices_????-??-??.json"
CORPORATE_ACTIONS_GLOB = "corporate_actions_????-??-??.json"
SENTIMENT_GLOB = "sentiment_news_????_????_????-??-??.jsonl"


def latest_dated_file(directory: Path, glob: str) -> Path:
    """Pinned-glob lookup (pipeline/guards.py's convention) - never a bare
    `Path.glob("*.json")` that could silently pick up an unrelated file."""
    candidates = sorted(directory.glob(glob))
    if not candidates:
        raise FileNotFoundError(f"No file found matching {glob} in {directory}")
    return candidates[-1]


def position_in_range(low, high, current) -> float | None:
    """Same position-in-range idea used everywhere in this product: 0.0 at
    the low, 1.0 at the high. None when there isn't enough data to place
    it, or the range is degenerate (low == high)."""
    if low is None or high is None or current is None or high == low:
        return None
    return max(0.0, min(1.0, (current - low) / (high - low)))
