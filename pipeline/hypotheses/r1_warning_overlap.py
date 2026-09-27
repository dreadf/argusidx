"""
R1 -- overlap between the eight warnings (descriptive, not a trial).

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-27: T1, R1 and
R2a") before this module was run. Produces the overlap table and the
(possibly-merged) warning list that R2a consumes; carries no pass/fail rule
and does not move the trial counter.

Method: for each pair of the eight warnings (`_warnings_panel.WARNING_KEYS`),
the Jaccard index of their active (stock, month) sets across the whole
panel. Any pair with Jaccard > 0.5 merges into whichever of the two is more
specific (the smaller active-month count); the merged pair is reported as
one warning with both original names noted.

Run:
    .venv/bin/python -m pipeline.hypotheses.r1_warning_overlap
"""
from __future__ import annotations

from datetime import date
from itertools import combinations

from pipeline.hypotheses._warnings_panel import WARNING_KEYS, build_panel, load_prices, load_universe

PANEL_END = date(2026, 9, 25)  # last bar in the current prices_5y.json cache


def active_sets(rows: list[dict]) -> dict[str, set[tuple[str, str]]]:
    """warning key -> set of (symbol, month_start) where it's active."""
    out: dict[str, set[tuple[str, str]]] = {k: set() for k in WARNING_KEYS}
    for r in rows:
        for k in WARNING_KEYS:
            if r["warnings"][k]:
                out[k].add((r["symbol"], r["month_start"]))
    return out


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_merges(sets: dict[str, set], threshold: float = 0.5) -> list[tuple[str, str, float]]:
    """Pairs with Jaccard > threshold, as (more_specific, less_specific, jaccard)."""
    merges = []
    for a, b in combinations(sets, 2):
        j = jaccard(sets[a], sets[b])
        if j > threshold:
            specific, general = (a, b) if len(sets[a]) <= len(sets[b]) else (b, a)
            merges.append((specific, general, j))
    return merges


def main() -> None:
    prices = load_prices()
    universe = load_universe()
    rows, panel_stats = build_panel(prices, universe, end=PANEL_END)
    print(f"Panel: {panel_stats}")

    sets = active_sets(rows)
    print("\nActive-month counts:")
    for k in WARNING_KEYS:
        print(f"  {k:<28}: {len(sets[k]):>6} of {len(rows)} ({len(sets[k]) / len(rows):.1%})")

    print("\nPairwise Jaccard overlap:")
    all_pairs = []
    for a, b in combinations(WARNING_KEYS, 2):
        j = jaccard(sets[a], sets[b])
        all_pairs.append((a, b, j))
    for a, b, j in sorted(all_pairs, key=lambda x: -x[2]):
        print(f"  {a:<28} x {b:<28}: {j:.3f}")

    merges = find_merges(sets)
    print(f"\nMerges (Jaccard > 0.5): {len(merges)}")
    for specific, general, j in merges:
        print(f"  '{general}' merges into '{specific}' (more specific; Jaccard {j:.3f})")

    merged_out = {general for _specific, general, _j in merges}
    final_keys = [k for k in WARNING_KEYS if k not in merged_out]
    print(f"\nFinal warning list for R2a/R2b ({len(final_keys)} of {len(WARNING_KEYS)}): {final_keys}")

    print(
        "\nDescriptive only -- no pass/fail rule, not counted in the project trial\n"
        "counter. Feeds R2a's common-support check and R2b's pre-registered pairs."
    )


if __name__ == "__main__":
    main()
