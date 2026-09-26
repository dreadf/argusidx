"""Skip marker for the few tests that read the purchased raw data.

`data/raw/` lives in a private data repo (Sectors' terms forbid republishing
it), so a fresh clone of the public repo does not have it. Those tests skip
there and run on the machine that owns the data.
"""
import pytest

from pipeline.appdata.common import RAW_DIR

needs_raw = pytest.mark.skipif(
    not any(RAW_DIR.glob("universe_*.json")),
    reason="data/raw is kept in a private data repo and is absent from a fresh clone",
)
