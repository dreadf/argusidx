"""
Base rate: of IDX companies that lost money in a given year, what
fraction were profitable again the following year?

NOT a falsifiable hypothesis -- descriptive base rate, same category as
H16 (does not enter the trial counter, no explore/holdout split, no
significance test). From docs/PLAN.md's Chunk M ("base-rate family"):
serves "it's cheap because it's temporarily loss-making" -- a common
retail rationale for buying a struggling company -- by replacing the
guess with a frequency.

Data: `earnings[YYYY]` from the owned screener sweep
(data/raw/universe_2026-09-12.json, 962 companies, 2021-2025) -- the
same field H4/H10 already use. No new Sectors cost, no price data
needed at all (this is a pure Sectors-fundamentals question, unlike
H1/H5/H14 which need Yahoo prices).

Method: for each company and each consecutive year pair (2021→2022,
2022→2023, 2023→2024, 2024→2025), a "loss year" is `earnings[Y] < 0`.
Of loss years, what fraction have `earnings[Y+1] > 0` ("turned
around")? Reported pooled across all 4 year-transitions, and broken out
per-transition to show whether the rate is stable across time (a single
pooled number could hide one unusual year driving the whole result --
the same reasoning H1's year-by-year breakdown already applies).

Predictor-before-outcome: trivially satisfied -- `earnings[Y]` is
observed at year Y's close, `earnings[Y+1]` a full year later.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_loss_maker_turnaround
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-12.json"

YEARS = [2021, 2022, 2023, 2024, 2025]


def build_rows(universe: list[dict]) -> list[dict]:
    rows = []
    for r in universe:
        qv = r.get("query_values") or {}
        sym = r.get("symbol")
        for year in YEARS[:-1]:
            e_y = qv.get(f"earnings[{year}]")
            e_next = qv.get(f"earnings[{year + 1}]")
            if e_y is None or e_next is None:
                continue
            if e_y >= 0:
                continue  # only loss years are eligible
            rows.append({"sym": sym, "year": year, "turned_around": e_next > 0})
    return rows


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    rows = build_rows(universe)

    print(f"Loss-maker turnaround -- {len(rows)} (company, loss-year) observations across {YEARS[0]}-{YEARS[-1]}\n")

    print(f"{'Year -> next':<16}{'n loss-years':>14}{'turned around':>16}{'rate':>10}")
    for year in YEARS[:-1]:
        year_rows = [r for r in rows if r["year"] == year]
        if not year_rows:
            continue
        n = len(year_rows)
        n_turned = sum(1 for r in year_rows if r["turned_around"])
        print(f"{year} -> {year + 1:<9}{n:>14}{n_turned:>16}{n_turned / n:>10.1%}")

    n_total = len(rows)
    n_turned_total = sum(1 for r in rows if r["turned_around"])
    print(f"\nPooled across all transitions: {n_turned_total} of {n_total} loss-years turned around ({n_turned_total / n_total:.1%})")
    print(
        "\nDescriptive base rate only -- no explore/holdout split, no significance\n"
        "test, not counted in the project trial counter (same category as H16)."
    )


if __name__ == "__main__":
    main()
