"""
Base rates (situations A and D), from annual net income `earnings[YYYY]`
(owned Sectors sweep, 2021-2025). No prices, no API calls.

NOT falsifiable hypotheses -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions were
frozen in EXPERIMENT.md ("Pre-registration, 2026-09-22").

- A "Laba turun dua tahun berturut-turut": earnings[Y] < earnings[Y-1] <
  earnings[Y-2], all reported, earnings[Y-2] > 0. Base rate: of stock-years
  with that trigger and an earnings[Y+1], the share with
  earnings[Y+1] > earnings[Y] (earnings rose the next year). Y = 2023, 2024.
- D "Laba lebih dari dua kali lipat": earnings[Y] > 2 * earnings[Y-1] and
  earnings[Y-1] > 0. Base rate: of stock-years with that trigger and an
  earnings[Y+1], (a) the share with earnings[Y+1] < earnings[Y] and (b) the
  share with earnings[Y+1] < earnings[Y-1]. Y = 2022..2024.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_earnings_streaks
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"

DOUBLE = 2.0


def _e(qv: dict, year: int) -> float | None:
    return qv.get(f"earnings[{year}]")


def is_two_year_decline(qv: dict, year: int) -> bool:
    a, b, c = _e(qv, year), _e(qv, year - 1), _e(qv, year - 2)
    return a is not None and b is not None and c is not None and c > 0 and a < b < c


def is_more_than_doubled(qv: dict, year: int) -> bool:
    a, b = _e(qv, year), _e(qv, year - 1)
    return a is not None and b is not None and b > 0 and a > DOUBLE * b


def two_year_decline_rows(universe: list[dict], years: list[int]) -> list[dict]:
    rows = []
    for y in years:
        for r in universe:
            qv = r.get("query_values") or {}
            nxt = _e(qv, y + 1)
            if is_two_year_decline(qv, y) and nxt is not None:
                rows.append({"year": y, "rose_next_year": nxt > _e(qv, y)})
    return rows


def doubled_rows(universe: list[dict], years: list[int]) -> list[dict]:
    rows = []
    for y in years:
        for r in universe:
            qv = r.get("query_values") or {}
            nxt = _e(qv, y + 1)
            if is_more_than_doubled(qv, y) and nxt is not None:
                rows.append(
                    {"year": y, "gave_part_back": nxt < _e(qv, y), "gave_all_back": nxt < _e(qv, y - 1)}
                )
    return rows


def _rate(rows: list[dict], key: str) -> dict:
    n = len(rows)
    return {"n": n, "count": sum(1 for r in rows if r[key]), "rate": (sum(1 for r in rows if r[key]) / n) if n else None}


def build_two_year_decline(universe: list[dict]) -> dict:
    rows = two_year_decline_rows(universe, [2023, 2024])
    return {"pooled": _rate(rows, "rose_next_year"), "by_year": {y: _rate([r for r in rows if r["year"] == y], "rose_next_year") for y in (2023, 2024)}}


def build_more_than_doubled(universe: list[dict]) -> dict:
    rows = doubled_rows(universe, [2022, 2023, 2024])
    return {
        "gave_part_back": _rate(rows, "gave_part_back"),
        "gave_all_back": _rate(rows, "gave_all_back"),
        "by_year": {
            y: {"gave_part_back": _rate([r for r in rows if r["year"] == y], "gave_part_back"), "gave_all_back": _rate([r for r in rows if r["year"] == y], "gave_all_back")}
            for y in (2022, 2023, 2024)
        },
    }


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    print("A (two-year decline, earnings rose next year):", json.dumps(build_two_year_decline(universe)))
    print("D (more than doubled):", json.dumps(build_more_than_doubled(universe)))
    now = [r["symbol"] for r in universe if is_two_year_decline(r.get("query_values") or {}, 2025)]
    doubled_now = [r["symbol"] for r in universe if is_more_than_doubled(r.get("query_values") or {}, 2025)]
    print(f"\nIn situation A now (Y=2025): {len(now)} stocks; in D now: {len(doubled_now)} stocks")


if __name__ == "__main__":
    main()
