"""
Base rate (situation I9, "Dividen jauh di atas rata-rata sendiri"): after a
year with a dividend yield far above the stock's own recent average, how often
was the next year's dividend lower?

NOT a falsifiable hypothesis -- descriptive, no explore/holdout split, no
significance test, not counted in the trial counter. Definitions frozen in
EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 1)"); run once. From the
owned yearly fields, no prices, no API calls.

- Trigger in year Y (historical version of the app flag, same multiplier,
  `build_flags.YIELD_ABOVE_AVG_MULTIPLIER` = 1.5, not changed):
  `total_yield[Y] >= 1.5 * mean(total_yield[Y-3], [Y-2], [Y-1])`, needs all
  three prior years, and a positive mean (the flag also skips a zero average).
  Yearly fields only, never the snapshot `yield_ttm`.
- Outcome: `total_dividend[Y+1] < total_dividend[Y]` (a cut). A missing
  `total_dividend[Y+1]` is counted as a cut in the main figure; the figure with
  those stocks left out is printed beside it. `total_dividend[Y]` must exist.
- Y = 2024 and 2025. The owned yearly fields end at 2025, so Y+1 is known only
  for Y = 2024; for Y = 2025 the trigger count is reported and the outcome is
  not computable (n = 0), not filled with a guess.
- Limits: a yield can jump because the price fell, not because the dividend
  rose (the field alone cannot tell); a non-payer has no value at all in the
  owned data, so "missing = cut" also captures stocks that stopped reporting.

Run:
    .venv/bin/python -m pipeline.hypotheses.m_yield_spike_cut
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.appdata.build_flags import YIELD_ABOVE_AVG_MULTIPLIER

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"

YEARS = [2024, 2025]
LAST_KNOWN_YEAR = 2025  # last year present in the owned yearly fields
PRIOR_YEARS = 3


def is_yield_spike(qv: dict, year: int) -> bool:
    current = qv.get(f"total_yield[{year}]")
    prior = [qv.get(f"total_yield[{year - k}]") for k in range(1, PRIOR_YEARS + 1)]
    if current is None or any(p is None for p in prior):
        return False
    mean = sum(prior) / PRIOR_YEARS
    if mean <= 0:
        return False
    return current >= YIELD_ABOVE_AVG_MULTIPLIER * mean


def _rate(count: int, n: int) -> dict:
    return {"n": n, "count": count, "rate": (count / n) if n else None}


def build_yield_spike_cut(universe: list[dict], years: list[int] = YEARS) -> dict:
    out: dict = {}
    for y in years:
        triggered = 0
        cut_missing_as_cut: list[bool] = []
        cut_missing_dropped: list[bool] = []
        for r in universe:
            qv = r.get("query_values") or {}
            if not is_yield_spike(qv, y):
                continue
            triggered += 1
            div_y = qv.get(f"total_dividend[{y}]")
            if y + 1 > LAST_KNOWN_YEAR or div_y is None:
                continue
            div_next = qv.get(f"total_dividend[{y + 1}]")
            if div_next is None:
                cut_missing_as_cut.append(True)
            else:
                cut = div_next < div_y
                cut_missing_as_cut.append(cut)
                cut_missing_dropped.append(cut)
        out[y] = {
            "triggered": triggered,
            "cut_missing_counted_as_cut": _rate(sum(cut_missing_as_cut), len(cut_missing_as_cut)),
            "cut_missing_left_out": _rate(sum(cut_missing_dropped), len(cut_missing_dropped)),
        }
    return out


def main() -> None:
    result = build_yield_spike_cut(json.loads(UNIVERSE_PATH.read_text()))
    for y, res in result.items():
        print(f"Y={y}: stocks in the situation: {res['triggered']}")
        for key in ("cut_missing_counted_as_cut", "cut_missing_left_out"):
            r = res[key]
            share = "n/a" if r["rate"] is None else f"{r['rate']:.1%}"
            print(f"  {key}: n={r['n']}  cuts={r['count']}  share={share}")
    print(f"(Y+1 is only known through {LAST_KNOWN_YEAR}; Y = 2025 has no outcome.)")


if __name__ == "__main__":
    main()
