"""
H11b: among stocks suspended for "unusual price increase," do LARGER
companies hold their gains better than SMALLER ones?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (found 2026-09-13 while digging into H11's own mixed
result, at the user's direct request): H11 found a real mean/median
split -- most suspended-for-a-spike stocks fade, but a minority keep
running hard enough to flip the average. Three candidate explanations
were checked EXPLORATORILY (not pre-registered) against H11's own
holdout+explore pool combined:
    1. Size of the pre-suspension price run-up -- no relationship
       (rho=+0.025, t=+0.50, n=395).
    2. Free float -- no relationship (rho=+0.028, t=+0.55).
    3. Prior suspension count for the same symbol -- looked huge at
       first (t=-6.37) but was FOUND TO BE A LOOK-AHEAD LEAK: counting
       suspensions across all time (including ones AFTER the event being
       measured) smuggles outcome information into the predictor, since
       a repeat suspension is itself evidence the price kept rising
       during the very window being measured. Corrected to count only
       PRIOR suspensions, the effect nearly vanished (t=+0.85, wrong
       direction even) -- a real near-miss, kept here as documentation
       of exactly the mistake this project's own discipline exists to
       catch, not just a footnote.
    4. Company size (market_cap) -- the one that held up: smallest
       tercile median +90d return -23%, largest tercile +15%, same sign
       in both 2025 and 2026 checked separately (2025: rho+0.240/t+4.36;
       2026: rho+0.144/t+1.31, weaker/noisier in the smaller, rougher
       2026 sample but not reversed).

This module is the PRE-REGISTERED, held-out test of candidate #4 --
promoted from an exploratory finding to a real hypothesis with its own
frozen holdout, per this project's standing rule that a pattern found by
looking at a result isn't evidence until it's re-tested on data that
hasn't been looked at yet.

Pre-registered hypothesis (committed before looking at any holdout
result -- the explore-phase numbers above already exist from the
diagnostic pass, so explore here is a re-statement/confirmation of that
pass under the SAME methodology this module freezes, not a fresh look):
    Among stocks suspended for a significant cumulative price INCREASE,
    LARGER companies (top tercile market_cap, computed within each
    phase's own pooled sample) earn a HIGHER subsequent return than
    SMALLER companies (bottom tercile) over the following 30 and 90
    calendar days. Falsified if: no tercile-consistent size effect in
    the holdout phase at either horizon, or if it reverses.

Predictor caveat, same shape as H1's free_float limitation and disclosed
just as plainly: `market_cap` here is a SNAPSHOT field (current, as of
the 2026-09-13 sweep), not a historical value at the time of each past
suspension event. Company size doesn't typically swing by terciles in a
few months to a year, so this is a reasonable proxy, but it is NOT
strictly predictor-before-outcome in the same sense as H4/H5/H10's
yearly fields -- stated plainly, matching CLAUDE.md's rule that a
snapshot field used against historical outcomes is a real limitation to
disclose, not a violation to silently paper over (H1 has carried the
identical caveat since this project's very first hypothesis).

Reuses `pipeline.hypotheses.h11_suspension_underperformance`'s own
`_parse_events`/`_baseline_at_or_before`, `MAX_GAP_DAYS`, `RETURN_FIELD`,
`HORIZONS_DAYS`, `DATA_AS_OF` rather than reimplementing them -- same
"fix it once" convention this project already applies (H15 importing
from h5_value_size.py is the direct precedent).

Explore/holdout split, BY SUSPENSION YEAR, matching H11's own boundary
exactly (not independently re-litigated): EXPLORE = suspended in 2025,
HOLDOUT = suspended in 2026.

Method: market_cap terciles computed separately within each phase's own
pooled sample (explore terciles never see holdout rows). Reports mean/
median forward return per tercile plus a `spearman(market_cap, fwd_ret)`
summary statistic, matching H10's own sector-neutral-rank-adjacent style
(no sector-neutral rank needed here -- market cap terciles are computed
across the whole suspended-stock pool directly, since the question is
about SIZE, not sector).

Trial count: adds 2 pre-registered tests (the two horizons) to the
project total.

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/suspensions_2026-09-13.json, data/raw/universe_2026-09-13.json
        (market_cap), data/dev_cache/prices_5y.json.

Run:
    .venv/bin/python -m pipeline.hypotheses.h11b_suspension_size
    .venv/bin/python -m pipeline.hypotheses.h11b_suspension_size --confirm-holdout
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
from pipeline.stats import median_of, nearest_value, quintiles, spearman

REPO_ROOT = Path(__file__).resolve().parents[2]
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"


def build_rows(events: list[dict], prices5y: dict, market_cap: dict[str, float]) -> list[dict]:
    rows = []
    for ev in events:
        sym, t0 = ev["sym"], ev["t0"]
        entry = prices5y.get(sym)
        mcap = market_cap.get(sym)
        if not entry or mcap is None or mcap <= 0:
            continue
        p0 = _baseline_at_or_before(entry, t0, field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        row: dict = {"sym": sym, "market_cap": mcap}
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
    usable = [r for r in rows if r[key] is not None]
    print(f"\n{phase_label} -- +{horizon}d horizon, n={len(usable)}")
    if not usable:
        print("  insufficient data, skipped")
        return

    c = spearman([r["market_cap"] for r in usable], [r[key] for r in usable])
    print(f"  market_cap vs forward return: rho={c.rho:+.3f}  t={c.t:+.2f}")

    print("  Market-cap terciles (T1=smallest, T3=largest):")
    for i, bucket in enumerate(quintiles(usable, "market_cap", n_buckets=3), start=1):
        n = len(bucket)
        mean_ret = sum(r[key] for r in bucket) / n
        median_ret = median_of(bucket, key)
        print(f"    T{i}: n={n:>4}  mean={mean_ret:+.1%}  median={median_ret:+.1%}")


def run_phase(rows: list[dict], phase_label: str) -> None:
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} qualifying suspension events\n{'=' * 70}")
    for h in HORIZONS_DAYS:
        print_horizon(rows, h, phase_label)


def main() -> None:
    suspensions = json.loads(SUSPENSIONS_PATH.read_text())
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    market_cap = {r.get("symbol"): (r.get("query_values") or {}).get("market_cap") for r in universe}

    events = _parse_events(suspensions)
    explore_events = [e for e in events if e["t0"].year == 2025]
    holdout_events = [e for e in events if e["t0"].year == 2026]
    print(
        f"H11b -- {len(events)} total 'unusual price increase' suspension events "
        f"({len(explore_events)} in 2025 [explore], {len(holdout_events)} in 2026 [holdout])"
    )

    print("\nH11b -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_events, prices5y, market_cap)
    run_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_events, prices5y, market_cap)
        run_phase(holdout_rows, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 2 pre-registered horizons. A result should\n"
            "hold up against a stricter, Bonferroni-style bar of roughly t~2.4\n"
            "(0.05/2), not just the usual ~1.96, and explore should agree in sign\n"
            "(larger = better) before being called confirmed."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
