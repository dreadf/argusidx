"""
R2b -- three pre-registered warning pairs (+3 trials if each has qualifying
support; Holm-corrected).

Plan reference: `kind-juggling-hoare.md` section 5, R2b. Not yet written
into EXPERIMENT.md as a dated pre-registration before this module was run
(a deviation from this project's own discipline, done at the user's
explicit instruction to keep moving through R2b/R5/A1 in one sitting) --
the exact definitions below are copied verbatim from the plan text, which
WAS written and approved before any of R1/R2a/R2b's code existed, so the
substance was fixed in advance even though the EXPERIMENT.md entry for
this specific module is written after running it, not before. Disclosed
here rather than presented as if it followed the usual order.

The three pairs (using R1's merged warning names -- "fell 30%+" no longer
exists on its own, since it merged into "long_below_peak"):
1. spike_40_20 x loss_year (plan: "up 40%+ in 20 days x loss year")
2. payout_top_tercile x earnings_down_2y (plan: "payout in the top tercile
   x earnings down two years")
3. long_below_peak x loss_year (plan: "fell 30%+ x loss year")

Cells: same size-tercile x 60-day-volatility-tercile cells as R2a, cut
cross-sectionally per formation month. Support (HOLDOUT ONLY -- the plan's
R2b text, unlike R2a's, never asks for an explore-side check, and there is
no "champion chosen in explore" step here to protect against): a cell
qualifies for a given pair if each of 3 groups -- "pair" (both warnings
active, count exactly 2), "X alone" (only X active, count 1), "Y alone"
(only Y active, count 1) -- has >=30 holdout observations. A pair with
zero qualifying cells is not run as a trial; reported descriptively.

Decision, per qualifying pair: cell-weighted D-U for "pair" must beat BOTH
"X alone" and "Y alone", cell-weighted, on holdout. Significance: a
one-sided p-value from a 2,000-replicate stock-clustered bootstrap of
min(DU_pair - DU_x, DU_pair - DU_y) (whole stocks resampled together, so a
stock's own repeated monthly rows never get treated as independent
evidence), then Holm-Bonferroni across the (up to 3) pairs that actually
ran, alpha 0.05 (`pipeline.stats.holm_bonferroni` -- family-wise control,
not H10's Benjamini-Hochberg, since 3 specific pre-registered pairs is a
confirmatory family, not an exploratory screen).

Run:
    .venv/bin/python -m pipeline.hypotheses.r2b_warning_pairs
"""
from __future__ import annotations

import random
import statistics
from datetime import date

from pipeline.hypotheses._stress_common import BOOTSTRAP_B, SEED
from pipeline.hypotheses._warnings_panel import build_panel, load_prices, load_universe
from pipeline.hypotheses.r1_warning_overlap import PANEL_END
from pipeline.hypotheses.r2a_warning_count import (
    attach_terciles,
    compute_outcomes,
    load_suspensions,
    merged_warning_keys,
    split_explore_holdout,
    warning_count,
)
from pipeline.stats import holm_bonferroni

MIN_GROUP = 30
ALPHA = 0.05

PAIRS = [
    ("spike_40_20", "loss_year"),
    ("payout_top_tercile", "earnings_down_2y"),
    ("long_below_peak", "loss_year"),
]


def group_label(row: dict, x: str, y: str, keys: list[str]) -> str | None:
    n = warning_count(row, keys)
    if n == 2 and row["warnings"][x] and row["warnings"][y]:
        return "pair"
    if n == 1 and row["warnings"][x]:
        return "x"
    if n == 1 and row["warnings"][y]:
        return "y"
    return None


def qualifying_cells_for_pair(holdout: list[dict], x: str, y: str, keys: list[str]) -> list[tuple[int, int]]:
    cells = {
        (r["size_tercile"], r["vol_tercile"])
        for r in holdout
        if r["size_tercile"] is not None and r["vol_tercile"] is not None
    }
    qualifying = []
    for cell in sorted(cells):
        counts = {"pair": 0, "x": 0, "y": 0}
        for r in holdout:
            if (r["size_tercile"], r["vol_tercile"]) != cell:
                continue
            label = group_label(r, x, y, keys)
            if label:
                counts[label] += 1
        if all(v >= MIN_GROUP for v in counts.values()):
            qualifying.append(cell)
    return qualifying


def cell_weighted_du(rows: list[dict], cells: list[tuple[int, int]], label: str, x: str, y: str, keys: list[str]) -> float | None:
    total_n = 0
    weighted_sum = 0.0
    for cell in cells:
        group = [
            r
            for r in rows
            if (r["size_tercile"], r["vol_tercile"]) == cell and group_label(r, x, y, keys) == label
        ]
        if not group:
            continue
        du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
        weighted_sum += du * len(group)
        total_n += len(group)
    return (weighted_sum / total_n) if total_n else None


def pair_diff_stat(rows: list[dict], cells: list[tuple[int, int]], x: str, y: str, keys: list[str]) -> float | None:
    du_pair = cell_weighted_du(rows, cells, "pair", x, y, keys)
    du_x = cell_weighted_du(rows, cells, "x", x, y, keys)
    du_y = cell_weighted_du(rows, cells, "y", x, y, keys)
    if du_pair is None or du_x is None or du_y is None:
        return None
    return min(du_pair - du_x, du_pair - du_y)


def bootstrap_one_sided_p(rows: list[dict], cells: list[tuple[int, int]], x: str, y: str, keys: list[str]) -> dict:
    """Stock-clustered bootstrap (whole stocks resampled together) of
    `pair_diff_stat`; one-sided p for H1: diff > 0 (the pair beats both
    single warnings)."""
    by_stock: dict[str, list[dict]] = {}
    for r in rows:
        by_stock.setdefault(r["symbol"], []).append(r)
    stocks = sorted(by_stock)
    rng = random.Random(SEED)
    real = pair_diff_stat(rows, cells, x, y, keys)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_B):
        sample: list[dict] = []
        for _k in range(len(stocks)):
            sample.extend(by_stock[stocks[rng.randrange(len(stocks))]])
        v = pair_diff_stat(sample, cells, x, y, keys)
        if v is not None:
            draws.append(v)
    if not draws or real is None:
        return {"estimate": real, "p_one_sided": float("nan"), "n_valid_replicates": len(draws)}
    p = (1 + sum(1 for d in draws if d <= 0)) / (len(draws) + 1)
    return {"estimate": real, "p_one_sided": p, "n_valid_replicates": len(draws)}


def main() -> None:
    prices = load_prices()
    universe = load_universe()
    rows, panel_stats = build_panel(prices, universe, end=PANEL_END)
    keys = merged_warning_keys(rows)
    print(f"Panel: {panel_stats}")
    print(f"Warning keys: {keys}\n")

    suspensions = load_suspensions()
    rows, _dropped_end = compute_outcomes(rows, prices, suspensions)
    attach_terciles(rows)
    _explore, holdout, _dropped_embargo = split_explore_holdout(rows)
    print(f"Holdout formations: {len(holdout)}\n")

    results = []
    for x, y in PAIRS:
        print(f"--- {x} x {y} ---")
        cells = qualifying_cells_for_pair(holdout, x, y, keys)
        print(f"  qualifying cells: {cells}")
        if not cells:
            print("  fewer than 1 qualifying cell -- DESCRIPTIVE, not run as a trial.")
            for label in ("pair", "x", "y"):
                group = [r for r in holdout if group_label(r, x, y, keys) == label]
                if group:
                    du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
                    print(f"    {label} (n={len(group)}): pooled D-U = {du:+.3f}")
            results.append({"pair": (x, y), "ran": False})
            continue
        boot = bootstrap_one_sided_p(holdout, cells, x, y, keys)
        du_pair = cell_weighted_du(holdout, cells, "pair", x, y, keys)
        du_x = cell_weighted_du(holdout, cells, "x", x, y, keys)
        du_y = cell_weighted_du(holdout, cells, "y", x, y, keys)
        print(f"  D-U: pair={du_pair}, {x} alone={du_x}, {y} alone={du_y}")
        print(f"  min(pair-x, pair-y) = {boot['estimate']}, one-sided p = {boot['p_one_sided']:.4f} "
              f"({boot['n_valid_replicates']} valid replicates)")
        results.append({"pair": (x, y), "ran": True, "p": boot["p_one_sided"], "estimate": boot["estimate"]})

    ran = [r for r in results if r["ran"]]
    if ran:
        rejected = holm_bonferroni([r["p"] for r in ran], alpha=ALPHA)
        print(f"\nHolm-Bonferroni across {len(ran)} run pair(s), alpha={ALPHA}:")
        for r, rej in zip(ran, rejected):
            beats_both = r["estimate"] is not None and r["estimate"] > 0
            confirmed = rej and beats_both
            print(f"  {r['pair']}: p={r['p']:.4f}, beats both singles={beats_both}, Holm-significant={rej} "
                  f"-> {'CONFIRMED' if confirmed else 'NOT confirmed'}")
    else:
        print("\nNo pair had qualifying support: 0 of 3 R2b trials ran.")


if __name__ == "__main__":
    main()
