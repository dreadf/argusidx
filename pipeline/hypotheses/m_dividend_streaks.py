"""
Base rate (situation I6, "Dividen rutin"): of stocks with a run of dividend
years, how many paid again the next year, and how many paid at least as much?

NOT a falsifiable hypothesis -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions frozen in
EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 1)"); run once. From the
owned `total_dividend[YYYY]` fields (2021..2025), no prices, no API calls.

- A stock has a streak of N years ending Y if `total_dividend[y] > 0` for
  every y in Y-N+1..Y.
- For N = 1..4 and Y = 2022..2024: the share that paid again in Y+1
  (`total_dividend[Y+1] > 0`), and the share whose `total_dividend[Y+1]` is at
  least `total_dividend[Y]`. n is reported per cell.
- Data floor: the field starts in 2021, so a streak of N years ending Y needs
  Y-N+1 >= 2021. Cells that cannot exist (N=3 for Y=2022, N=4 for Y=2022 and
  Y=2023) are reported as "not computable", not as n=0 measurements.
- Missing values: in the owned data a non-payer has no value at all (no zero
  appears in any year), so a missing `total_dividend[Y+1]` is treated as "did
  not pay" -- the reading the definition needs. A missing value cannot be told
  apart from a dividend that was not reported, so the same rates are also
  printed for stocks that reported `earnings[Y+1]` (evidence that the company
  filed for that year). That second view is a diagnostic added beside the
  frozen definition, not a replacement.
- Limits: stock-years of one company overlap across N and Y, so cells are not
  independent; the universe is the stocks in the owned file, which may omit
  companies delisted before it was built.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_dividend_streaks
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"

FIRST_YEAR = 2021
STREAK_LENGTHS = [1, 2, 3, 4]
END_YEARS = [2022, 2023, 2024]


def _div(qv: dict, year: int) -> float | None:
    return qv.get(f"total_dividend[{year}]")


def paid(qv: dict, year: int) -> bool:
    v = _div(qv, year)
    return v is not None and v > 0


def has_streak(qv: dict, n_years: int, end_year: int) -> bool:
    return all(paid(qv, y) for y in range(end_year - n_years + 1, end_year + 1))


def computable(n_years: int, end_year: int) -> bool:
    return end_year - n_years + 1 >= FIRST_YEAR


def _rate(count: int, n: int) -> dict:
    return {"n": n, "count": count, "rate": (count / n) if n else None}


def _outcomes(qv: dict, end_year: int) -> tuple[bool, bool]:
    paid_again = paid(qv, end_year + 1)
    at_least = paid_again and _div(qv, end_year + 1) >= _div(qv, end_year)
    return paid_again, at_least


def streak_cell(universe: list[dict], n_years: int, end_year: int) -> dict | None:
    """Rates for one (N, Y) cell, or None if the data floor makes it impossible."""
    if not computable(n_years, end_year):
        return None
    rows = []
    for r in universe:
        qv = r.get("query_values") or {}
        if has_streak(qv, n_years, end_year):
            again, at_least = _outcomes(qv, end_year)
            rows.append((again, at_least, qv.get(f"earnings[{end_year + 1}]") is not None))
    reported = [x for x in rows if x[2]]
    return {
        "paid_again": _rate(sum(x[0] for x in rows), len(rows)),
        "paid_at_least_as_much": _rate(sum(x[1] for x in rows), len(rows)),
        "paid_again_reported_only": _rate(sum(x[0] for x in reported), len(reported)),
        "paid_at_least_as_much_reported_only": _rate(sum(x[1] for x in reported), len(reported)),
    }


def build_dividend_streaks(universe: list[dict]) -> dict:
    return {f"N={n},Y={y}": streak_cell(universe, n, y) for n in STREAK_LENGTHS for y in END_YEARS}


def main() -> None:
    result = build_dividend_streaks(json.loads(UNIVERSE_PATH.read_text()))
    for cell, res in result.items():
        if res is None:
            print(f"{cell}: not computable (streak would start before {FIRST_YEAR})")
            continue
        a, b = res["paid_again"], res["paid_at_least_as_much"]
        ra, rb = res["paid_again_reported_only"], res["paid_at_least_as_much_reported_only"]
        fmt = lambda x: "n/a" if x["rate"] is None else f"{x['rate']:.1%}"  # noqa: E731
        print(
            f"{cell}: n={a['n']}  paid again {a['count']} ({fmt(a)})  at least as much {b['count']} ({fmt(b)})"
            f"  | reported-only n={ra['n']}  paid again {ra['count']} ({fmt(ra)})  at least as much {rb['count']} ({fmt(rb)})"
        )


if __name__ == "__main__":
    main()
