"""
Guards against known Sectors API traps and injection surfaces.

Each guard here corresponds to a specific failure documented in
docs/PLAN.md: this module exists so the trap is fixed once, in code,
rather than re-discovered per-caller (RULES.md process rule 3: fix the
class, not the instance).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# Individual-stock daily data returns empty arrays (not errors) before this
# date, and the call still bills credits. Undocumented; found by testing.
# See docs/PLAN.md 8.1. Does not apply to `listing-performance`, which
# covers listings after May 2005.
SECTORS_DATA_FLOOR = date(2021, 1, 1)


def assert_within_data_floor(start: date) -> None:
    """Raise loudly instead of silently billing for an empty result."""
    if start < SECTORS_DATA_FLOOR:
        raise ValueError(
            f"requested start date {start} is before the Sectors data floor "
            f"({SECTORS_DATA_FLOOR}); individual-stock daily endpoints return "
            "empty arrays for this range and still bill credits"
        )


def _load_known_tickers() -> frozenset[str]:
    """Ticker universe from the purchased free-float dataset (961 companies).

    The glob is pinned to the dated filename pattern rather than
    `free_float_*.json` -- a loose glob would silently treat any
    matching file as the authoritative universe by lexicographic sort
    order (e.g. a `free_float_backup.json` sorts after every dated file
    and would win, regardless of which is actually most recent).
    """
    matches = sorted(DATA_RAW.glob("free_float_????-??-??.json"))
    if not matches:
        raise FileNotFoundError(
            f"no free_float_YYYY-MM-DD.json found under {DATA_RAW}"
        )
    with matches[-1].open() as f:
        rows = json.load(f)
    return frozenset(row["symbol"].upper() for row in rows)


_KNOWN_TICKERS: frozenset[str] | None = None


def is_known_ticker(symbol: str) -> bool:
    """Validate a user-supplied ticker against the known IDX universe.

    Defends against ticker-field injection (docs/PLAN.md 6.1): no
    user-supplied string should reach a query unchecked.
    """
    global _KNOWN_TICKERS
    if _KNOWN_TICKERS is None:
        _KNOWN_TICKERS = _load_known_tickers()
    return symbol.upper() in _KNOWN_TICKERS
