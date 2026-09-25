"""
H13: do Acceleration-board IPOs underperform Main-board IPOs over the
following 180/365/720 calendar days?

STATUS: explore phase only until --confirm-holdout is passed (mirrors
h5_value_size.py's discipline).

Why this exists (docs/PLAN.md's H13, "candidate, free to test" since
2026-09-09): IDX's listing boards carry genuinely different listing
requirements (Acceleration is the lowest bar, aimed at smaller/earlier-
stage companies; Main is the highest). `docs/SOURCES.md` already cites
published IDX-market findings that ~2/3 of Acceleration-board IPOs from
2020-2024 posted negative returns at 360/720 days -- this project holds
266 owned 2021+ listings with `listing_date`/`listing_board` already
purchased, and prices already in the free Yahoo dev cache. Zero
additional cost to test whether the same pattern shows up in OUR data
(a different, if overlapping, sample and measurement window from the
cited literature -- not a replication in the strict sense).

Pre-registered hypothesis (committed before looking at any outcome):
    IPOs listed on the ACCELERATION board earn a LOWER subsequent
    return, and are more often NEGATIVE, than IPOs listed on the MAIN
    board, over the same 180/365/720 calendar-day horizons from first
    trade. Falsified if: no clear underperformance of Acceleration vs.
    Main at the pre-registered horizons in the holdout phase, or if
    Acceleration outperforms.

Predictor-before-outcome: trivially satisfied -- `listing_board` is
assigned at listing, an already-realized fact; the outcome window is
strictly the calendar time after the stock's first trade.

"Listing price" proxy: the nearest close within `MAX_GAP_DAYS` of
`listing_date` in the Yahoo cache (first observed trading price), NOT
the actual IPO offer price (Sectors' `/v2/listing-performance/` would
give price-since-listing directly but costs credits per symbol and
isn't needed for this free research pass -- see docs/PLAN.md's H13
note on shipping this with real Sectors prices later, ~60-120 credits,
a separate decision). This is a real, disclosed proxy, not the
literature's own offer-price basis -- a different measurement, not a
strict replication.

Explore/holdout split, BY LISTING YEAR (not the May-1-formation-lag
convention H1/H5/H10 use -- that exists for annual financial-statement
reporting lag, which doesn't apply here; `listing_board` is known
immediately):
    EXPLORE: listed 2021-2022 (Acceleration n=19, Main n=21, per a free
        pre-check of the owned universe file)
    HOLDOUT: listed 2023-2024 (Acceleration n=20, Main n=21)
2025-2026 listings are excluded entirely, not just per-horizon -- none
of their 720-day horizons have elapsed yet as of this module's
DATA_AS_OF, and including only their 180-day results while dropping the
rest would bias the sample toward whichever listings happen to be old
enough, silently.

Horizons -- all three pre-registered together, matching the cited
literature's own choice of 360/720 days (this module additionally tests
180d as a shorter-term check), not chosen after seeing which looks best:
180, 365, 720 calendar days. A horizon is excluded per-event (not
padded/estimated) if it would fall after DATA_AS_OF.

Comparison: Acceleration vs. Main only -- the two boards the cited
literature actually contrasts. Development/Watchlist/New Economy are
reported descriptively (their raw negative-rate and mean/median) for
completeness but are NOT part of the pre-registered falsification test,
since no specific literature-backed directional claim was made for them
here.

A repeat of H11's own lesson, applied up front rather than discovered
after running it wrong once: report BOTH the negative-rate/median (the
"typical IPO" experience) AND the mean/Welch-t (which a few extreme
winners or losers can dominate) -- H11 found these can tell different
stories, and this module checks for the same divergence rather than
assuming it away.

Multiple comparisons: 3 pre-registered horizons, each compared via
negative-rate and Welch's t. No FDR needed at this trial count (matching
H11's convention) -- a plain Bonferroni-style note (roughly t~2.4 for 3
tests) stated alongside any result that clears ~1.96 but not the
stricter bar.

Trial count: adds 3 pre-registered tests (the three horizons) to the
project total.

Data (already purchased/free -- no new Sectors call for this module):
    data/raw/universe_2026-09-13.json -- `listing_date`, `listing_board`.
    data/dev_cache/prices_5y.json -- Yahoo, dev-only.

Run:
    .venv/bin/python -m pipeline.hypotheses.h13_ipo_board_performance
    .venv/bin/python -m pipeline.hypotheses.h13_ipo_board_performance --confirm-holdout
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.stats import median_of, nearest_value, welch_ttest

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

MAX_GAP_DAYS = 10
RETURN_FIELD = "adjclose"
HORIZONS_DAYS = [180, 365, 720]
MIN_GROUP_SIZE = 10
# Fixed "today" for deciding whether a horizon has elapsed -- see
# h11_suspension_underperformance.py's identical convention and rationale
# (a re-run months later must not silently start including different,
# not-yet-elapsed-at-pre-registration-time events).
DATA_AS_OF = datetime(2026, 9, 13, tzinfo=timezone.utc)

EXPLORE_YEARS = ["2021", "2022"]
HOLDOUT_YEARS = ["2023", "2024"]
ALL_BOARDS = ["Acceleration", "Development", "Main", "Watchlist", "New Economy"]


def _parse_listings(universe: list[dict]) -> list[dict]:
    listings = []
    for r in universe:
        qv = r.get("query_values") or {}
        ld = qv.get("listing_date")
        board = qv.get("listing_board")
        if not ld or ld < "2021-01-01" or not board:
            continue
        try:
            t0 = datetime.strptime(ld, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        listings.append({"sym": r.get("symbol"), "board": board, "t0": t0, "year": ld[:4]})
    return listings


def build_rows(listings: list[dict], prices5y: dict) -> list[dict]:
    rows = []
    for ev in listings:
        entry = prices5y.get(ev["sym"])
        if not entry:
            continue
        p0 = nearest_value(entry, ev["t0"], field=RETURN_FIELD, max_gap_days=MAX_GAP_DAYS)
        if p0 is None:
            continue
        row: dict = {"sym": ev["sym"], "board": ev["board"], "year": ev["year"]}
        usable = False
        for h in HORIZONS_DAYS:
            t1 = ev["t0"] + timedelta(days=h)
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


def _board_stats(rows: list[dict], board: str, horizon: int) -> tuple[int, float, float, float] | None:
    key = f"ret_{horizon}d"
    rets = [r[key] for r in rows if r["board"] == board and r[key] is not None]
    if not rets:
        return None
    n = len(rets)
    neg_rate = sum(1 for x in rets if x < 0) / n
    mean_ret = sum(rets) / n
    median_ret = median_of([{"v": x} for x in rets], "v")
    return n, neg_rate, mean_ret, median_ret


def print_phase(rows: list[dict], phase_label: str) -> None:
    print(f"\n{'=' * 70}\n{phase_label} phase -- {len(rows)} listings with usable data\n{'=' * 70}")
    for h in HORIZONS_DAYS:
        print(f"\n{phase_label} -- +{h}d horizon:")
        for board in ALL_BOARDS:
            stats = _board_stats(rows, board, h)
            if stats is None:
                print(f"    {board:>12}: no data")
                continue
            n, neg_rate, mean_ret, median_ret = stats
            print(f"    {board:>12}: n={n:>3}  negative_rate={neg_rate:.1%}  mean={mean_ret:+.1%}  median={median_ret:+.1%}")

        key = f"ret_{h}d"
        accel = [r[key] for r in rows if r["board"] == "Acceleration" and r[key] is not None]
        main = [r[key] for r in rows if r["board"] == "Main" and r[key] is not None]
        if len(accel) >= MIN_GROUP_SIZE and len(main) >= MIN_GROUP_SIZE:
            t = welch_ttest(accel, main)
            print(f"    Acceleration vs Main (Welch t): t={t.t:+.2f}  diff={t.diff:+.1%}")
        else:
            print(f"    Acceleration vs Main (Welch t): insufficient data (need n>={MIN_GROUP_SIZE} each)")


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())

    listings = _parse_listings(universe)
    explore_listings = [ev for ev in listings if ev["year"] in EXPLORE_YEARS]
    holdout_listings = [ev for ev in listings if ev["year"] in HOLDOUT_YEARS]
    print(
        f"H13 -- {len(listings)} total 2021+ listings with a known board "
        f"({len(explore_listings)} in {EXPLORE_YEARS} [explore], "
        f"{len(holdout_listings)} in {HOLDOUT_YEARS} [holdout])"
    )

    print("\nH13 -- EXPLORE phase (methodology may still change)")
    explore_rows = build_rows(explore_listings, prices5y)
    print_phase(explore_rows, "EXPLORE")

    if "--confirm-holdout" in sys.argv:
        print("\n" + "=" * 70)
        print("HOLDOUT CONFIRMATION -- methodology frozen above; touched once.")
        holdout_rows = build_rows(holdout_listings, prices5y)
        print_phase(holdout_rows, "HOLDOUT")
        print(
            "\nMultiple-comparisons note: 3 pre-registered horizons. A result should\n"
            "hold up against a stricter, Bonferroni-style bar of roughly t~2.4\n"
            "(0.05/3), not just the usual ~1.96, and explore should agree in sign\n"
            "(same direction, Acceleration underperforming Main), before being\n"
            "called confirmed."
        )
    else:
        print(
            "\n(Holdout not run this pass. Re-run with --confirm-holdout only "
            "once the explore-phase methodology above is final.)"
        )


if __name__ == "__main__":
    main()
