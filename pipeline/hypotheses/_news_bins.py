"""Shared per-symbol, non-overlapping date-binning for H9's follow-up
hypotheses (H9b, H9c). Bins are consecutive `bin_days`-day windows
anchored to each symbol's own first tagged-article date, so articles
published days apart don't produce heavily overlapping windows -- the
same pseudo-replication problem H14/H15 were designed around (see
docs/PLAN.md's H14 planning section), applied here to news bins instead
of daily technical-indicator windows.
"""
from __future__ import annotations

from datetime import timedelta


def bin_articles_by_symbol(articles: list[dict], bin_days: int = 20) -> list[dict]:
    """Returns a list of {"sym", "bin_start", "bin_end", "articles"}.
    Bins never overlap for a given symbol; empty bins are skipped."""
    by_sym: dict[str, list[dict]] = {}
    for a in articles:
        by_sym.setdefault(a["sym"], []).append(a)

    bins = []
    for sym, arts in by_sym.items():
        arts = sorted(arts, key=lambda a: a["t0"])
        bin_start = arts[0]["t0"]
        bin_end = bin_start + timedelta(days=bin_days)
        bucket: list[dict] = []
        for a in arts:
            while a["t0"] >= bin_end:
                if bucket:
                    bins.append({"sym": sym, "bin_start": bin_start, "bin_end": bin_end, "articles": bucket})
                bin_start = bin_end
                bin_end = bin_start + timedelta(days=bin_days)
                bucket = []
            bucket.append(a)
        if bucket:
            bins.append({"sym": sym, "bin_start": bin_start, "bin_end": bin_end, "articles": bucket})
    return bins
