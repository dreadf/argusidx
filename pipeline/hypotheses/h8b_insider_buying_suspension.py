"""
H8b: does insider BUYING in the weeks before a price-spike suspension
predict a BETTER (less negative) post-suspension return -- the mirror
of H8's insider-selling test?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists: proposed by the user after H8 (insider selling before
a spike suspension) came back falsified. Insider buying is a distinct
claim from insider selling, not just "not selling" -- the literature
(Lakonishok & Lee, 2001, *Review of Financial Studies*) finds insider
PURCHASES predict returns more reliably across markets than insider
sales do, on the reasoning that a sale can be liquidity-driven noise
while a purchase is a costlier, more deliberate signal. This tests that
specific claim in the one setting this project already has machinery
for: stocks suspended for an "unusual price increase" (the same 437
events H8/H11 use).

Pre-registered hypothesis (committed before looking at any holdout
result): stocks with insider BUY filings in the 30 days before a
significant cumulative price-increase suspension earn a HIGHER
subsequent return than stocks with no such filings, over the following
30 and 90 calendar days -- insiders adding to their own stake ahead of
a speculative run-up reflects genuine conviction, not manipulation.
Falsified if: no consistent outperformance of the "insider bought"
group vs. the "no insider buying" group in holdout at either horizon,
or if it reverses.

Predictor-before-outcome: identical convention to H8 -- only buy
filings strictly BEFORE the suspension date count toward the predictor.

Data-quality guard, checked directly rather than assumed (found a
difference from H8's own filter worth fixing here rather than silently
inheriting): H8's `_load_insider_sells()` used a `0 < pct <= 100` filter
to exclude one garbled record, but that filter also silently drops any
LEGITIMATE transaction where `share_percentage_transaction` rounds to
0.0 (verified: 69 of 1,388 sell records, 281 of 1,767 buy records, e.g.
BBCA.JK buys of 0.001%-0.03% of its own enormous share count --
confirmed real via `share_percentage_before`/`_after` both showing the
same tiny nonzero value, not a data error). This module's
`_load_insider_buys()` uses `pct <= 100` instead (keeps pct==0.0,
excludes only the one impossible >100% class of record, matching H8's
own single PPRI.JK exclusion pattern) -- a real, disclosed improvement
over H8's filter, not backported to H8 itself to avoid re-touching an
already-closed hypothesis's methodology after the fact.

Small-sample limitation, stated up front: only 29 of 437 qualifying
suspension events (6.6%) have a matching insider-buy filing in their
30-day pre-window -- 19 in 2025 (explore), 10 in 2026 (holdout). The
holdout group just meets this project's MIN_GROUP_SIZE=10 convention;
results are still reported with that caveat front and center.

Reuses `pipeline.hypotheses.h11_suspension_underperformance`'s own
`_parse_events`/`_baseline_at_or_before`, `MAX_GAP_DAYS`, `RETURN_FIELD`,
`HORIZONS_DAYS`, `DATA_AS_OF` -- same convention as H8/H11b.

Explore/holdout split, matching H8/H11's own boundary exactly:
EXPLORE = suspended in 2025, HOLDOUT = suspended in 2026.

Trial count: adds 2 pre-registered tests (the two horizons) to the
project total.

Legal/naming note, unchanged from H8: this reports a checkable, dated,
public-record pattern -- never a claim that any named company or
individual manipulated its price.

Data (already purchased -- no new Sectors call for this module):
    data/raw/suspensions_2026-09-13.json,
    data/raw/insider_buys_2025_2026_2026-09-13.jsonl (60 credits,
        2026-09-13 -- see docs/credit_ledger.md),
    data/dev_cache/prices_5y.json.

Run:
    .venv/bin/python -m pipeline.hypotheses.h8b_insider_buying_suspension
    .venv/bin/python -m pipeline.hypotheses.h8b_insider_buying_suspension --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta
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
INSIDER_BUYS_PATH = REPO_ROOT / "data" / "raw" / "insider_buys_2025_2026_2026-09-13.jsonl"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

PRE_WINDOW_DAYS = 30
MIN_GROUP_SIZE = 10


def _load_insider_buys() -> list[dict]:
    buys = []
    with INSIDER_BUYS_PATH.open() as f:
        for line in f:
            d = json.loads(line)
            pct = d.get("share_percentage_transaction")
            ts = d.get("timestamp")
            sym = d.get("symbol")
            if pct is None or ts is None or sym is None:
                continue
            if pct > 100:
                # Excludes 1 known garbled record (PPRI.JK, pct=929.3%,
                # the buy-side mirror of H8's own excluded sell record).
                # Unlike H8, keeps pct==0.0 -- see module docstring's
                # data-quality guard.
                continue
            buys.append({"sym": sym, "date": ts[:10], "pct": pct})
    return buys


def _had_insider_buying(event: dict, buys: list[dict]) -> bool:
    t0 = event["t0"]
    window_start = (t0 - timedelta(days=PRE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    window_end = t0.strftime("%Y-%m-%d")
    return any(b["sym"] == event["sym"] and window_start <= b["date"] < window_end for b in buys)


def build_rows(events: list[dict], prices5y: dict, buys: list[dict]) -> list[dict]:
    rows = []
    for ev in events:
        sym, t0 = ev["sym"], ev["t0"]
        entry = prices5y.get(sym)
        if not entry:
            continue
        p0 = _baseline_at_or_before(entry, t0, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        row: dict = {"sym": sym, "insider_bought": _had_insider_buying(ev, buys)}
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
    bought = [r[key] for r in rows if r["insider_bought"] and r[key] is not None]
    not_bought = [r[key] for r in rows if not r["insider_bought"] and r[key] is not None]
    print(f"\n{phase_label} -- +{horizon}d horizon")
    for label, group in [("insider BOUGHT before suspension", bought), ("no insider buying found", not_bought)]:
        if not group:
            print(f"  {label:<34}: n=0")
            continue
        mean_ret = sum(group) / len(group)
        median_ret = median_of([{"v": v} for v in group], "v")
        print(f"  {label:<34}: n={len(group):>4}  mean={mean_ret:+.1%}  median={median_ret:+.1%}")

    if len(bought) >= MIN_GROUP_SIZE and len(not_bought) >= MIN_GROUP_SIZE:
        t = welch_ttest(bought, not_bought)
        print(f"  Welch t (bought vs not-bought): t={t.t:+.2f}  diff={t.diff:+.1%}")
    else:
        print(f"  Welch t: insufficient data for a formal test (need n>={MIN_GROUP_SIZE} each; "
              f"have {len(bought)} bought, {len(not_bought)} not-bought) -- reported descriptively above only")


def run_phase(rows: list[dict], phase_label: str) -> None:
    n_bought = sum(1 for r in rows if r["insider_bought"])
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} suspension events ({n_bought} with prior insider buying)\n{'=' * 70}")
    for h in HORIZONS_DAYS:
        print_horizon(rows, h, phase_label)


def main() -> None:
    suspensions = json.loads(SUSPENSIONS_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    buys = _load_insider_buys()

    events = _parse_events(suspensions)
    explore_events = [e for e in events if e["t0"].year == 2025]
    holdout_events = [e for e in events if e["t0"].year == 2026]
    print(
        f"H8b -- {len(events)} total 'unusual price increase' suspension events "
        f"({len(explore_events)} in 2025 [explore], {len(holdout_events)} in 2026 [holdout])"
    )

    print("\nH8b -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_events, prices5y, buys)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_events, prices5y, buys)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 2 pre-registered horizons. Holdout 'insider\n"
            "bought' group (n=10) only just meets MIN_GROUP_SIZE -- treat any result\n"
            "here as a candidate lead, not a fully confirmed finding on the same\n"
            "footing as H1/H4/H5/H10."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
