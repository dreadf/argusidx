"""Build data/app/market_condition.json: the Pasar page's "Kondisi pasar"
card and its "Jarak dari harga tertinggi setahun" card.

The state label reuses T1's exact rule (pipeline/hypotheses/t1_market_state.py
compute_states), so the label the app shows is the one that was tested. T1 was
NOT confirmed (EXPERIMENT.md, 2026-09-27): the label describes IHSG's state
today and must never be presented as a forecast.

Tiles, all from IHSG closes up to the latest date only:
- pct_from_peak and the peak's date (running peak-to-date)
- pct_vs_ma200 (distance from the 200-day moving average)
- vol20_percentile: percentile rank (0-100) of today's 20-day realised
  volatility within its own expanding history
- days_since_peak: trading days since that peak

Distance-from-52-week-high distribution: every stock in rankings.json's
furthest_below_52w_high list, binned by 10 percentage points.

Run: .venv/bin/python -m pipeline.appdata.build_market_condition
"""
from __future__ import annotations

import json
import statistics

from pipeline.appdata.common import APP_DIR, IHSG_GLOB, RAW_DIR, latest_dated_file
from pipeline.hypotheses.t1_market_state import (
    BURN_IN_DAYS,
    MA_WINDOW,
    PEAK_DROP_THRESHOLD,
    VOL_PERCENTILE,
    compute_states,
    expanding_percentile,
    load_ihsg,
    realised_vol_20,
)
from pipeline.stats import moving_average

DIST_BINS = 10


def percentile_rank(history: list[float], value: float) -> float:
    """Share (0-100) of `history` at or below `value`."""
    if not history:
        raise ValueError("empty history")
    return 100 * sum(1 for h in history if h <= value) / len(history)


def ihsg_condition(dates: list[str], closes: list[float]) -> dict:
    if len(closes) < BURN_IN_DAYS:
        raise ValueError(f"need at least {BURN_IN_DAYS} IHSG closes, got {len(closes)}")
    states = compute_states(closes)
    last = len(closes) - 1

    peak_i = 0
    for i in range(last + 1):
        if closes[i] >= closes[peak_i]:
            peak_i = i
    ma200 = moving_average(closes, MA_WINDOW)[last]
    vol = realised_vol_20(closes)
    vol_hist = [v for v in vol[: last + 1] if v is not None]

    pct_from_peak = closes[last] / closes[peak_i] - 1
    vol_p90 = expanding_percentile(vol, VOL_PERCENTILE)[last]
    return {
        "date": dates[last],
        "close": closes[last],
        "state": states[last],
        "pct_from_peak": pct_from_peak,
        "peak_date": dates[peak_i],
        "peak_close": closes[peak_i],
        "pct_vs_ma200": closes[last] / ma200 - 1,
        "vol20_percentile": percentile_rank(vol_hist, vol[last]),
        "days_since_peak": last - peak_i,
        "rule": {
            "below_peak_and_ma200": pct_from_peak <= -PEAK_DROP_THRESHOLD and closes[last] < ma200,
            "volatility_above_p90": vol[last] is not None and vol_p90 is not None and vol[last] > vol_p90,
        },
    }


def distance_distribution(pcts: list[float]) -> dict:
    """pcts are fractions <= 0 (e.g. -0.377). Bin i holds -(i+1)/10 < x <= -i/10;
    the last bin also takes anything at or below -90%."""
    bins = [0] * DIST_BINS
    for x in pcts:
        bins[min(DIST_BINS - 1, int(-x * DIST_BINS))] += 1
    return {
        "n": len(pcts),
        "median": statistics.median(pcts),
        "n_down_30_or_more": sum(1 for x in pcts if x <= -0.30),
        "bins": bins,
    }


def main() -> None:
    dates, closes = load_ihsg()
    ihsg_path = latest_dated_file(RAW_DIR, IHSG_GLOB)
    rankings = json.loads((APP_DIR / "rankings.json").read_text())
    pcts = [r["pct_below_high"] for r in rankings["furthest_below_52w_high"]]

    out = {
        "ihsg_source_file": ihsg_path.name,
        "rankings_as_of": rankings["as_of"],
        "ihsg": ihsg_condition(dates, closes),
        "distance_from_high": distance_distribution(pcts),
    }
    path = APP_DIR / "market_condition.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"Wrote {path}")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
