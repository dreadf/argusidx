"""
H11: do stocks suspended for "unusual price increase" subsequently
underperform the index -- the pump-fades-back pattern?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (docs/PLAN.md's H11 candidate, adopted for real
2026-09-13 once `/v2/suspensions/` was purchased): IDX suspends a stock
and issues an official notice whenever its price moves unusually fast --
588 such records purchased this session, 437 of 588 (74%) for
"peningkatan harga [...] yang signifikan" (a significant cumulative
price INCREASE), literally IDX's own regulatory description of a
pump-like move ("cooling down sebagai bentuk perlindungan bagi
investor" -- cooling down as investor protection). This ties directly to
the gorengan problem statement `docs/PLAN.md` is built around, and
unlike H8 (blocked at ~100+ credits, needs per-symbol broker-summary
history), the suspension record itself is a single flat-rate purchase
that already happened.

Pre-registered hypothesis (committed before looking at any outcome):
    A stock suspended for a significant cumulative price INCREASE earns
    a LOWER subsequent return than the index over the following ~30 and
    ~90 calendar days -- the price move that triggered the suspension
    partially or fully reverses (mean-reversion / "pump fades").
    Falsified if: no clear underperformance vs. the index at either
    horizon in the holdout phase, or if suspended stocks outperform.

Predictor-before-outcome: trivially satisfied -- the predictor is the
suspension event itself, an already-realized, dated fact; the outcome
window is strictly the calendar time after it.

Filter, verified directly against the purchased data (not assumed):
    reason contains "peningkatan harga" (case-insensitive) -- confirmed
    the exact Bahasa Indonesia phrase IDX uses for this category by
    reading data/raw/suspensions_2026-09-13.json directly. The 10
    "penurunan harga" (price DECREASE) suspensions and the 17 generic
    "cooling down" ones are excluded -- different, untested claims, not
    silently folded in.

Explore/holdout split -- NOT the same May-1-formation-lag calendar
convention H1/H5/H14/H15 use (that convention exists for ANNUAL
financial-statement data; suspensions are dated events with no
reporting lag). Instead, split by the event's own year, which the data
happens to make almost entirely 2025 vs. 2026 (535 of 588 suspensions
overall; the "peningkatan harga" subset is similarly concentrated):
    EXPLORE: suspension_date.year == 2025
    HOLDOUT: suspension_date.year == 2026 (up to whenever this is run --
        an event needs its full horizon to have already elapsed by
        "today" or it's simply excluded, not padded/estimated)

Horizons -- both pre-registered together, not chosen after seeing which
looks better: +30 calendar days (~short-term, does the spike itself
reverse) and +90 calendar days (~does it fully reverse over a quarter).
Baseline price is the nearest close AT OR BEFORE the suspension date
(trading is halted starting then, so that's the last observable price),
`adjclose` for total-return consistency with H5/H16.

Benchmark: IDX Composite (^JKSE), date-matched over the exact same
window as each event (`data/dev_cache/benchmarks_5y.json`, `close` field
-- same convention H16 uses for this same series).

Multiple comparisons: 2 pre-registered horizons, each compared against
the index via win-rate and Welch's t-test. `welch_ttest` treats the two
samples as independent, which is an approximation here -- the stock and
index returns at a given horizon are actually PAIRED (same event window)
-- no paired-test machinery exists in this project yet; disclosed as a
limitation, not silently assumed away. No FDR needed at n=2 tests -- a
plain Bonferroni note (roughly t~2.4 for 2 tests) stated alongside any
result that clears ~1.96 but not the stricter bar, matching H15's own
convention.

A real, disclosed clustering limitation: some symbols are suspended for
"peningkatan harga" more than once (repeat cooling-downs on the same
run-up); this module pools every qualifying EVENT, not one per symbol,
so a stock suspended 3 times in one rally contributes 3 non-independent
rows. Not collapsed here -- flagged, matching this project's convention
of disclosing rather than silently fixing every clustering concern
(see H5's own dropout-bias write-up for precedent).

Trial count: adds 2 pre-registered tests (the two horizons) to the
project total.

Legal/naming note, carried forward exactly as `docs/PLAN.md` states it:
this reports a REGULATORY CATEGORY (IDX's own "unusual price increase"
suspension reason) and a resulting BASE RATE, never a claim that any
named company manipulated its price. Any symbol appearing in this
module's output is cited only as a matter of public IDX record (the
suspension notice itself, `pdf_url` in the purchased data), consistent
with how this project already treats every other worked example.

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/suspensions_2026-09-13.json -- Sectors, purchased 2026-09-13
        (20 credits, full history). Never gitignored.
    data/dev_cache/prices_5y.json, data/dev_cache/benchmarks_5y.json --
        Yahoo, dev-only.

Run:
    .venv/bin/python -m pipeline.hypotheses.h11_suspension_underperformance
    .venv/bin/python -m pipeline.hypotheses.h11_suspension_underperformance --confirm-holdout
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.stats import nearest_value, welch_ttest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
BENCHMARKS_PATH = REPO_ROOT / "data" / "dev_cache" / "benchmarks_5y.json"

MAX_GAP_DAYS = 10
RETURN_FIELD = "adjclose"
HORIZONS_DAYS = [30, 90]
MIN_GROUP_SIZE = 10
# "Today" for deciding whether a horizon has actually elapsed -- the day
# this module was built and the suspension data purchased. Fixed, not
# datetime.now(), so a re-run months from now doesn't silently start
# including different, not-yet-elapsed-at-pre-registration-time events
# into what was meant to be a frozen holdout.
DATA_AS_OF = datetime(2026, 9, 13, tzinfo=timezone.utc)


def _baseline_at_or_before(entry: dict, target: datetime, field: str, max_gap_days: int) -> float | None:
    """Value at the LATEST timestamp <= `target`, within `max_gap_days` --
    unlike `nearest_value`/`nearest_index` (which match the closest
    timestamp in EITHER direction), this must never return a post-`target`
    price for a suspension baseline: trading halts starting at the
    suspension date, so a baseline drawn from a later bar would already
    reflect the very reversal this hypothesis measures, contaminating the
    predictor with outcome information (found by /code-review, 2026-09-13
    -- `nearest_value` was being used for this and could pick either
    direction). Forward-looking lookups (t0+30d/t0+90d) are unaffected and
    keep using `nearest_value` -- picking either direction for an OUTCOME
    date is the same convention every other hypothesis module here uses.
    """
    timestamps = entry["timestamps"]
    values = entry[field]
    target_ts = target.timestamp()
    best_ts = None
    best_idx = None
    for i, t in enumerate(timestamps):
        if t <= target_ts and (best_ts is None or t > best_ts):
            best_ts = t
            best_idx = i
    if best_idx is None or target_ts - best_ts > max_gap_days * 86400:
        return None
    value = values[best_idx]
    return value if value > 0 else None


def _parse_events(suspensions: list[dict]) -> list[dict]:
    events = []
    for r in suspensions:
        reason = (r.get("reason") or "").lower()
        if "peningkatan harga" not in reason:
            continue
        try:
            sym = r["symbol"]
            t0 = datetime.strptime(r["suspension_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        events.append({"sym": sym, "t0": t0})
    return events


def build_rows(events: list[dict], prices5y: dict, jkse: dict | None) -> list[dict]:
    rows = []
    for ev in events:
        sym, t0 = ev["sym"], ev["t0"]
        entry = prices5y.get(sym)
        if not entry:
            continue
        p0 = _baseline_at_or_before(entry, t0, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        j0 = _baseline_at_or_before(jkse, t0, field="close", max_gap_days=MAX_GAP_DAYS) if jkse is not None else None
        row: dict = {"sym": sym, "t0": t0}
        usable = False
        for h in HORIZONS_DAYS:
            t1 = t0 + timedelta(days=h)
            if t1 > DATA_AS_OF:
                row[f"ret_{h}d"] = None
                row[f"jkse_{h}d"] = None
                continue
            p1 = nearest_value(entry, t1, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
            row[f"ret_{h}d"] = (p1 / p0 - 1) if p1 is not None else None
            jkse_ret = None
            if jkse is not None and j0 is not None:
                j1 = nearest_value(jkse, t1, field="close", max_gap_days=MAX_GAP_DAYS)
                if j1 is not None:
                    jkse_ret = j1 / j0 - 1
            row[f"jkse_{h}d"] = jkse_ret
            if row[f"ret_{h}d"] is not None and jkse_ret is not None:
                usable = True
        if usable:
            rows.append(row)
    return rows


def print_horizon(rows: list[dict], horizon: int, phase_label: str) -> None:
    ret_key, jkse_key = f"ret_{horizon}d", f"jkse_{horizon}d"
    pairs = [(r[ret_key], r[jkse_key]) for r in rows if r[ret_key] is not None and r[jkse_key] is not None]
    print(f"\n{phase_label} -- +{horizon}d horizon, n={len(pairs)}")
    if not pairs:
        print("  insufficient data, skipped")
        return
    stock_rets = [s for s, _ in pairs]
    jkse_rets = [j for _, j in pairs]
    wins = sum(1 for s, j in pairs if s > j)
    print(f"  Suspended stock beat the index: {wins} of {len(pairs)} ({100*wins/len(pairs):.1f}%)")
    print(
        f"  Suspended-stock return: mean {sum(stock_rets)/len(stock_rets):+.1%}"
        f"  median {statistics.median(stock_rets):+.1%}"
    )
    print(
        f"  Index return, same windows: mean {sum(jkse_rets)/len(jkse_rets):+.1%}"
        f"  median {statistics.median(jkse_rets):+.1%}"
    )
    if len(pairs) >= MIN_GROUP_SIZE:
        t = welch_ttest(stock_rets, jkse_rets)
        print(f"  Welch t (suspended vs index, treated as independent -- see Limits): t={t.t:+.2f}  diff={t.diff:+.1%}")
    else:
        print(f"  Welch t: insufficient data (need n>={MIN_GROUP_SIZE})")


def run_phase(rows: list[dict], phase_label: str) -> None:
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} qualifying suspension events\n{'=' * 70}")
    for h in HORIZONS_DAYS:
        print_horizon(rows, h, phase_label)


def main() -> None:
    suspensions = json.loads(SUSPENSIONS_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    benchmarks = json.loads(BENCHMARKS_PATH.read_text())
    jkse = benchmarks.get("^JKSE")

    events = _parse_events(suspensions)
    explore_events = [e for e in events if e["t0"].year == 2025]
    holdout_events = [e for e in events if e["t0"].year == 2026]
    print(
        f"H11 -- {len(events)} total 'unusual price increase' suspension events "
        f"({len(explore_events)} in 2025 [explore], {len(holdout_events)} in 2026 [holdout])"
    )

    print("\nH11 -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_events, prices5y, jkse)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_events, prices5y, jkse)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 2 pre-registered horizons. No FDR needed at\n"
            "this trial count -- a result should hold up against a stricter,\n"
            "Bonferroni-style bar of roughly t~2.4 (0.05/2), not just the usual ~1.96,\n"
            "and explore should agree in sign, before being called confirmed."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
