"""Build data/app/base_rates.json -- the three "Chunk M" base-rate results
(docs/PLAN.md's Chunk M "base-rate family"; research done 2026-09-13,
EXPERIMENT.md's "Chunk M base rates" section).

**Why these ship despite two of the three reading Yahoo dev-cache data**,
same compliance shape as `build_beat_gold.py` (read its docstring first --
this one restates only what differs): `CLAUDE.md` bans Yahoo from shipping
IN THE PRODUCT -- the live frontend never calls Yahoo, and nothing under
`pipeline/dev/` is imported by `frontend/`. This script is a build-time-only
precompute step that reads the already-fetched, free, dev-only cache
(`data/dev_cache/prices_1y.json`, `prices_5y.json` -- gitignored,
re-fetchable, zero cost) ONCE per module, and freezes only DERIVED FACTS
(percentages, counts, medians -- never a raw price series) into
`data/app/base_rates.json`. `loss_maker_turnaround` needs no Yahoo data at
all -- it reads only the owned `earnings[YYYY]` fields from the purchased
universe sweep.

**These are descriptive base rates, not falsifiable predictions.**
EXPERIMENT.md's "Chunk M" section classifies all three in the same
category as H16: no explore/holdout split, no significance test, not
counted in the project's trial counter. `CLAUDE.md`'s predictor-before-
outcome rule governs "X predicts Y" claims -- it is not engaged here, and
per-stock rendering of these facts must never imply a forecast for that
specific stock (docs/PLAN.md's own note on `typical_drawdown`'s market-cap
grouping: "descriptive grouping ... not a predictive claim").

Computation duplicates the small pieces of `pipeline/hypotheses/
m_loss_maker_turnaround.py`, `m_typical_drawdown.py`, and
`m_recovery_after_fall.py` needed here (same not-importing-from-the-
hypothesis-session's-active-territory precedent as `build_beat_gold.py`
and `lens_fields.py`). `pipeline/stats.py`'s `max_drawdown` IS imported,
since CLAUDE.md designates it explicitly as shared.

Verified against EXPERIMENT.md's own recorded Chunk M results before
shipping -- this script's output must match those exactly or something
has drifted (see the pipeline test):
  - loss-maker turnaround: 225 of 853 pooled (26.4%); per-year 35.2% /
    26.6% / 18.5% / 24.4%
  - typical drawdown: all 913 stocks, 25th -66.3% / median -49.5% / 75th
    -35.2%; smallest tercile median -54.7%, largest tercile median -44.3%
  - recovery after a fall: 1,348 events, 1,191 (88.4%) still below the
    pre-fall peak a year later, 157 (11.6%) recovered; median gap for the
    still-down group -49.2%

Run: .venv/bin/python -m pipeline.appdata.build_base_rates
"""
from __future__ import annotations

import json
import statistics

from pipeline.appdata.common import APP_DIR, RAW_DIR, REPO_ROOT, UNIVERSE_GLOB, latest_dated_file
from pipeline.hypotheses.m_dividend_streaks import build_dividend_streaks
from pipeline.hypotheses.m_earnings_streaks import build_more_than_doubled, build_two_year_decline
from pipeline.hypotheses.m_long_below_peak import build_long_below_peak
from pipeline.hypotheses.m_near_peak_earnings_decline import build_near_peak_earnings_decline
from pipeline.hypotheses.m_payout_flag_check import EXPLORE_YEARS, H4_UNIVERSE_PATH, HOLDOUT_YEARS, cut_rate_above_100
from pipeline.hypotheses.m_repeat_spike_suspension import build_repeat_spike_suspension
from pipeline.hypotheses.m_yield_spike_cut import build_yield_spike_cut
from pipeline.hypotheses.m_recent_spike import build_spike_base_rate
from pipeline.stats import max_drawdown

PRICES_1Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_1y.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
MARKET_CAP_PATH = REPO_ROOT / "data" / "raw" / "market_cap_2026-09-06.json"

RESEARCH_DATE = "2026-09-13"  # when Chunk M was run / the Yahoo cache this reads was fetched

EARNINGS_YEARS = [2021, 2022, 2023, 2024, 2025]
DRAWDOWN_MIN_TRADING_DAYS = 120
FALL_THRESHOLD = 0.70  # trigger when price <= 70% of running peak (a 30%+ fall)
FALL_FORWARD_TRADING_DAYS = 252
FALL_MIN_FORWARD_DAYS_AVAILABLE = 200


# --- Loss-maker turnaround (from m_loss_maker_turnaround.py) ---------------

def build_loss_maker_rows(universe: list[dict]) -> list[dict]:
    rows = []
    for r in universe:
        qv = r.get("query_values") or {}
        sym = r.get("symbol")
        for year in EARNINGS_YEARS[:-1]:
            e_y = qv.get(f"earnings[{year}]")
            e_next = qv.get(f"earnings[{year + 1}]")
            if e_y is None or e_next is None:
                continue
            if e_y >= 0:
                continue  # only loss years are eligible
            rows.append({"sym": sym, "year": year, "turned_around": e_next > 0})
    return rows


def build_loss_maker_turnaround(universe: list[dict]) -> dict:
    rows = build_loss_maker_rows(universe)
    by_year = []
    for year in EARNINGS_YEARS[:-1]:
        year_rows = [r for r in rows if r["year"] == year]
        if not year_rows:
            continue
        n = len(year_rows)
        n_turned = sum(1 for r in year_rows if r["turned_around"])
        by_year.append({
            "from_year": year,
            "to_year": year + 1,
            "n": n,
            "turned_around": n_turned,
            "pct": round(100 * n_turned / n, 1),
        })
    n_total = len(rows)
    n_turned_total = sum(1 for r in rows if r["turned_around"])
    return {
        "n": n_total,
        "turned_around": n_turned_total,
        "pct": round(100 * n_turned_total / n_total, 1) if n_total else None,
        "by_year": by_year,
    }


# --- Typical drawdown (from m_typical_drawdown.py) -------------------------

def load_market_cap(path=MARKET_CAP_PATH) -> dict[str, float]:
    rows = json.loads(path.read_text())
    out = {}
    for r in rows:
        mc = (r.get("query_values") or {}).get("market_cap")
        if mc is not None:
            out[r["symbol"]] = mc
    return out


def build_drawdown_rows(prices1y: dict, market_cap: dict[str, float]) -> list[dict]:
    rows = []
    for sym, entry in prices1y.items():
        closes = [c for c in entry.get("close", []) if c is not None and c > 0]
        if len(closes) < DRAWDOWN_MIN_TRADING_DAYS:
            continue
        mc = market_cap.get(sym)
        if mc is None:
            continue
        rows.append({"sym": sym, "mdd": max_drawdown(closes), "market_cap": mc})
    return rows


def _percentiles_25_50_75(values: list[float]) -> dict:
    s = sorted(values)
    n = len(s)
    p25 = s[int(0.25 * (n - 1))]
    p50 = statistics.median(s)
    p75 = s[int(0.75 * (n - 1))]
    return {
        "n": n,
        "p25_pct": round(100 * p25, 1),
        "median_pct": round(100 * p50, 1),
        "p75_pct": round(100 * p75, 1),
    }


def build_typical_drawdown(prices1y: dict, market_cap: dict[str, float]) -> dict:
    rows = build_drawdown_rows(prices1y, market_cap)
    mdds = [r["mdd"] for r in rows]
    overall = _percentiles_25_50_75(mdds)

    sorted_rows = sorted(rows, key=lambda r: r["market_cap"])
    n = len(sorted_rows)
    tercile_size = n // 3
    small = sorted_rows[:tercile_size]
    mid = sorted_rows[tercile_size:2 * tercile_size]
    large = sorted_rows[2 * tercile_size:]

    return {
        "overall": overall,
        "by_size_tercile": {
            "smallest": _percentiles_25_50_75([r["mdd"] for r in small]),
            "mid": _percentiles_25_50_75([r["mdd"] for r in mid]),
            "largest": _percentiles_25_50_75([r["mdd"] for r in large]),
        },
    }


# --- Recovery after a fall (from m_recovery_after_fall.py) -----------------

def _detect_fall_events(closes: list[float]) -> list[dict]:
    events = []
    if not closes:
        return events
    peak = closes[0]
    peak_idx = 0
    armed = True
    for i, c in enumerate(closes):
        if c > peak:
            peak = c
            peak_idx = i
            armed = True
            continue
        if armed and c <= peak * FALL_THRESHOLD:
            events.append({"peak_idx": peak_idx, "peak_price": peak, "trigger_idx": i, "trigger_price": c})
            armed = False
    return events


def build_recovery_rows(prices5y: dict) -> list[dict]:
    rows = []
    for sym, entry in prices5y.items():
        closes = [c for c in entry.get("close", []) if c is not None and c > 0]
        if len(closes) < 100:
            continue
        for ev in _detect_fall_events(closes):
            forward_idx = ev["trigger_idx"] + FALL_FORWARD_TRADING_DAYS
            available = len(closes) - 1 - ev["trigger_idx"]
            if available < FALL_MIN_FORWARD_DAYS_AVAILABLE:
                continue
            end_idx = min(forward_idx, len(closes) - 1)
            price_later = closes[end_idx]
            rows.append({
                "sym": sym,
                "peak_price": ev["peak_price"],
                "trigger_price": ev["trigger_price"],
                "price_later": price_later,
                "recovered": price_later >= ev["peak_price"],
            })
    return rows


def build_recovery_after_fall(prices5y: dict) -> dict:
    rows = build_recovery_rows(prices5y)
    n = len(rows)
    n_recovered = sum(1 for r in rows if r["recovered"])
    n_still_down = n - n_recovered

    still_down_gaps = [r["price_later"] / r["peak_price"] - 1 for r in rows if not r["recovered"]]
    median_gap_pct = round(100 * statistics.median(still_down_gaps), 1) if still_down_gaps else None

    return {
        "n_events": n,
        "n_stocks": len(prices5y),
        "still_below_peak": {"n": n_still_down, "pct": round(100 * n_still_down / n, 1) if n else None},
        "recovered": {"n": n_recovered, "pct": round(100 * n_recovered / n, 1) if n else None},
        "still_down_median_gap_pct": median_gap_pct,
    }


# --- Assembly ----------------------------------------------------------------

def _without(d: dict, key: str) -> dict:
    return {k: v for k, v in d.items() if k != key}


def _read_suspensions() -> list[dict]:
    return json.loads(latest_dated_file(RAW_DIR, "suspensions_????-??-??.json").read_text())


def _payout_cut_rates() -> dict:
    """H4's own universe file, payout ratio strictly above 100%, per phase (no new test)."""
    h4_universe = json.loads(H4_UNIVERSE_PATH.read_text())
    return {
        "explore": cut_rate_above_100(h4_universe, EXPLORE_YEARS),
        "holdout": cut_rate_above_100(h4_universe, HOLDOUT_YEARS),
    }


def main() -> None:
    if not PRICES_1Y_PATH.exists() or not PRICES_5Y_PATH.exists():
        raise FileNotFoundError(
            f"{PRICES_1Y_PATH} / {PRICES_5Y_PATH} not found - dev_cache is gitignored and machine-local; "
            "re-fetch via pipeline/dev/ (free, Yahoo) if missing, never invent this data"
        )
    if not MARKET_CAP_PATH.exists():
        raise FileNotFoundError(f"{MARKET_CAP_PATH} not found - required for the drawdown size breakout")

    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    universe = json.loads(universe_path.read_text())
    prices1y = json.loads(PRICES_1Y_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    market_cap = load_market_cap()

    output = {
        "as_of": RESEARCH_DATE,
        "note": (
            "Descriptive base rates, not predictions for any individual stock - same "
            "epistemic status as the beat-gold result (data/app/beat_gold.json): no "
            "explore/holdout split, no significance test, not counted in the project's "
            "trial counter (see EXPERIMENT.md's Chunk M section). Two of the three "
            "(typical_drawdown, recovery_after_fall) are computed once from "
            "development-only Yahoo Finance price history, never live in this product - "
            "a disclosed, dated research result, not a live capability."
        ),
        "loss_maker_turnaround": build_loss_maker_turnaround(universe),
        "typical_drawdown": build_typical_drawdown(prices1y, market_cap),
        "recovery_after_fall": build_recovery_after_fall(prices5y),
        # Added 2026-09-22 (EXPERIMENT.md "Pre-registration, 2026-09-22"). Imported from the
        # finished m_* modules rather than duplicated, so the situation trigger and its base
        # rate cannot drift apart. Same descriptive status: no test, not counted as a trial.
        "recent_spike": build_spike_base_rate(prices5y),
        "earnings_two_year_decline": build_two_year_decline(universe),
        "earnings_more_than_doubled": build_more_than_doubled(universe),
        # Added 2026-09-26 (EXPERIMENT.md "Pre-registration, 2026-09-26 (batch 1)"): same rule,
        # imported from the finished modules so trigger and base rate cannot drift.
        "long_below_peak": _without(build_long_below_peak(prices5y), "in_situation_now"),
        "repeat_spike_suspension": build_repeat_spike_suspension(_read_suspensions()),
        "near_peak_earnings_decline": build_near_peak_earnings_decline(universe, prices5y),
        "dividend_streaks": build_dividend_streaks(universe),
        "yield_spike_cut": build_yield_spike_cut(universe),
        "payout_above_100_cut_rate": _payout_cut_rates(),
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "base_rates.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")
    lmt = output["loss_maker_turnaround"]
    dd = output["typical_drawdown"]["overall"]
    rec = output["recovery_after_fall"]
    print(f"loss_maker_turnaround: {lmt['turned_around']}/{lmt['n']} ({lmt['pct']}%)")
    print(f"typical_drawdown overall: n={dd['n']} median={dd['median_pct']}%")
    print(f"recovery_after_fall: {rec['still_below_peak']['n']}/{rec['n_events']} still below ({rec['still_below_peak']['pct']}%)")


if __name__ == "__main__":
    main()
