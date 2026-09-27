"""
H8 (cheap version): does insider selling in the weeks before a
price-spike suspension predict a DEEPER post-suspension decline?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (docs/PLAN.md's H8, "the gorengan fingerprint," blocked
at ~100+ credits for its original broker-concentration design): H11's
own companion probe (4 anecdotal case studies, 2026-09-13) found
insiders selling meaningful stakes in the weeks before real price-spike
suspensions -- a different, cheaper mechanism than broker-level
tracking. This module promotes that anecdote to a real, pre-registered
test across ALL 437 qualifying suspension events, using a bulk
`/v2/filings/` pull (1 credit per call regardless of filters, 79
credits actually spent for the full 2025-2026 insider-sell history --
see docs/credit_ledger.md for the cost-overrun disclosure) instead of
per-event queries.

Pre-registered hypothesis (committed before looking at any holdout
result): stocks with insider SELL filings in the 30 days before a
significant cumulative price-increase suspension earn a LOWER
subsequent return than stocks with no such filings, over the following
30 and 90 calendar days -- insiders cashing out ahead of/during a
speculative run-up is a real warning sign, not noise. Falsified if: no
consistent underperformance of the "insider sold" group vs. the "no
insider selling" group in holdout at either horizon, or if it reverses.

Predictor-before-outcome: trivially satisfied -- only sell filings
strictly BEFORE the suspension date (`< t0`, matched by calendar date on
the filing's own `timestamp`) count toward the predictor; nothing after
t0 is used, unlike H11b's now-fixed prior-suspension-count mistake this
project already caught and corrected.

Data-quality guard, verified: 1 of 1,388 pulled insider-sell filings had
an impossible `share_percentage_transaction` > 100% (a garbled/duplicate
record -- PPRI.JK, same holder/date as a sane adjacent record with a
plausible 0.93%). Excluded via a `<= 100` sanity filter, matching this
project's established fail-loud-on-bad-data convention (see
`pipeline.stats._assert_all_positive`'s precedent) rather than silently
including an impossible value in a sum.

Small-sample limitation, stated up front rather than discovered after
running it: only 29 of 437 qualifying suspension events (6.6%) have a
matching insider-sell filing in their 30-day pre-window -- 22 in 2025
(explore), 7 in 2026 (holdout). This is well below this project's usual
MIN_GROUP_SIZE=10 convention for the holdout group specifically;
results are reported honestly as descriptive/underpowered wherever the
holdout group falls short, not silently upgraded to "confirmed."

Reuses `pipeline.hypotheses.h11_suspension_underperformance`'s own
`_parse_events`/`_baseline_at_or_before`, `MAX_GAP_DAYS`, `RETURN_FIELD`,
`HORIZONS_DAYS`, `DATA_AS_OF` rather than reimplementing them (same
"fix it once" convention H11b already applied).

Explore/holdout split, matching H11's own boundary exactly: EXPLORE =
suspended in 2025, HOLDOUT = suspended in 2026.

Trial count: adds 2 pre-registered tests (the two horizons) to the
project total.

Legal/naming note, unchanged from the rest of this project: this
reports a checkable, dated, public-record pattern (an official IDX
filing, followed by an official IDX suspension notice): never a claim
that any named company or individual manipulated its price. Any symbol
appearing in this module's output is cited only as a matter of public
record.

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/suspensions_2026-09-13.json,
    data/raw/insider_sells_2025_2026_2026-09-13.jsonl (79 credits,
        2026-09-13 -- see docs/credit_ledger.md),
    data/dev_cache/prices_5y.json.

Run:
    .venv/bin/python -m pipeline.hypotheses.h8_insider_selling_gorengan
    .venv/bin/python -m pipeline.hypotheses.h8_insider_selling_gorengan --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.hypotheses.h11_suspension_underperformance import (
    DATA_AS_OF,
    HORIZONS_DAYS,
    MAX_GAP_DAYS,
    RETURN_FIELD,
    _baseline_at_or_before,
    _parse_events,
)
from pipeline.stats import median_of, nearest_value, welch_ttest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"
INSIDER_SELLS_PATH = REPO_ROOT / "data" / "raw" / "insider_sells_2025_2026_2026-09-13.jsonl"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

PRE_WINDOW_DAYS = 30
MIN_GROUP_SIZE = 10


def _load_insider_sells() -> list[dict]:
    sells = []
    with INSIDER_SELLS_PATH.open() as f:
        for line in f:
            d = json.loads(line)
            pct = d.get("share_percentage_transaction")
            ts = d.get("timestamp")
            sym = d.get("symbol")
            if pct is None or ts is None or sym is None:
                continue
            if not (0 < pct <= 100):
                # Excludes 1 known garbled record (PPRI.JK, pct=930.2%)
                # -- see module docstring's data-quality guard.
                continue
            sells.append({"sym": sym, "date": ts[:10], "pct": pct})
    return sells


def _had_insider_selling(event: dict, sells: list[dict]) -> bool:
    t0 = event["t0"]
    window_start = (t0 - timedelta(days=PRE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    window_end = t0.strftime("%Y-%m-%d")
    return any(s["sym"] == event["sym"] and window_start <= s["date"] < window_end for s in sells)


def build_rows(events: list[dict], prices5y: dict, sells: list[dict]) -> list[dict]:
    rows = []
    for ev in events:
        sym, t0 = ev["sym"], ev["t0"]
        entry = prices5y.get(sym)
        if not entry:
            continue
        p0 = _baseline_at_or_before(entry, t0, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        row: dict = {"sym": sym, "insider_sold": _had_insider_selling(ev, sells)}
        usable = False
        for h in HORIZONS_DAYS:
            t1 = t0 + timedelta(days=h)
            if t1 > DATA_AS_OF:
                row[f"ret_{h}d"] = None
                continue
            p1 = nearest_value(entry, t1, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
            row[f"ret_{h}d"] = (p1 / p0 - 1) if p1 is not None else None
            if row[f"ret_{h}d"] is not None:
                usable = True
        if usable:
            rows.append(row)
    return rows


def print_horizon(rows: list[dict], horizon: int, phase_label: str) -> None:
    key = f"ret_{horizon}d"
    sold = [r[key] for r in rows if r["insider_sold"] and r[key] is not None]
    not_sold = [r[key] for r in rows if not r["insider_sold"] and r[key] is not None]
    print(f"\n{phase_label} -- +{horizon}d horizon")
    for label, group in [("insider SOLD before suspension", sold), ("no insider selling found", not_sold)]:
        if not group:
            print(f"  {label:<32}: n=0")
            continue
        mean_ret = sum(group) / len(group)
        median_ret = median_of([{"v": v} for v in group], "v")
        print(f"  {label:<32}: n={len(group):>4}  mean={mean_ret:+.1%}  median={median_ret:+.1%}")

    if len(sold) >= MIN_GROUP_SIZE and len(not_sold) >= MIN_GROUP_SIZE:
        t = welch_ttest(sold, not_sold)
        print(f"  Welch t (sold vs not-sold): t={t.t:+.2f}  diff={t.diff:+.1%}")
    else:
        print(f"  Welch t: insufficient data for a formal test (need n>={MIN_GROUP_SIZE} each; "
              f"have {len(sold)} sold, {len(not_sold)} not-sold) -- reported descriptively above only")


def run_phase(rows: list[dict], phase_label: str) -> None:
    n_sold = sum(1 for r in rows if r["insider_sold"])
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} suspension events ({n_sold} with prior insider selling)\n{'=' * 70}")
    for h in HORIZONS_DAYS:
        print_horizon(rows, h, phase_label)


def main() -> None:
    suspensions = json.loads(SUSPENSIONS_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    sells = _load_insider_sells()

    events = _parse_events(suspensions)
    explore_events = [e for e in events if e["t0"].year == 2025]
    holdout_events = [e for e in events if e["t0"].year == 2026]
    print(
        f"H8 (cheap) -- {len(events)} total 'unusual price increase' suspension events "
        f"({len(explore_events)} in 2025 [explore], {len(holdout_events)} in 2026 [holdout])"
    )

    print("\nH8 -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_events, prices5y, sells)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_events, prices5y, sells)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 2 pre-registered horizons. Given the small\n"
            "'insider sold' group size (7 in holdout), treat any result here as a\n"
            "candidate lead, not a statistically confirmed finding, regardless of\n"
            "what the t-statistic says."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
