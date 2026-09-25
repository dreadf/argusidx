"""Build data/app/ipo_boards.json -- H13's IPO listing-board performance
result (docs/PLAN.md's H13; research done 2026-09-13, EXPERIMENT.md's
"H13 -- Do Acceleration-board IPOs underperform Main-board IPOs?" section).

**Why this ships despite reading Yahoo dev-cache data** -- same shape as
`build_beat_gold.py` and `build_base_rates.py` (read either docstring
first): build-time-only precompute, reads `data/dev_cache/prices_5y.json`
ONCE, freezes only derived facts (negative rates, medians, means -- never
a raw price series) into `data/app/ipo_boards.json`.

**This IS a falsifiable, pre-registered hypothesis** (unlike Chunk M's
three base rates) -- H13 is counted in the project's trial counter and
went through an explore/holdout split. Its verdict is **falsified on the
pre-registered Welch-t test at every horizon, in both phases** -- not
significant at any of the 6 (horizon x phase) cells, despite a large,
consistent negative-rate/median gap in the same direction throughout.
Ship BOTH halves of that story, exactly as EXPERIMENT.md reports it --
never present only the favorable frequency framing and drop the
falsification, and never invent a verdict stronger than "falsified on
the formal test, but the frequency pattern is large, consistent, and
matches independently-published literature closely enough to read as
real underpowered evidence, not noise."

"Listing price" is a same-day-close proxy from the Yahoo cache, NOT the
actual IPO offer price -- a real, disclosed limitation, not the cited
literature's own basis (see the hypothesis module's docstring for the
full disclosure). Sectors' `/v2/listing-performance/` would give the real
figure but costs credits per symbol (docs/PRODUCT.md's ~60-120 credit
estimate) -- NOT spent here; this ships the free-research version only,
disclosed as a proxy.

Only Acceleration vs Main is part of the pre-registered falsification
test (the two boards the cited literature contrasts). Development,
Watchlist and New Economy are shipped as descriptive-only figures,
clearly marked as such, per the module's own convention.

Computation duplicates `pipeline/hypotheses/h13_ipo_board_performance.py`
(same not-importing-from-the-hypothesis-session's-territory precedent as
`build_beat_gold.py`). `pipeline/stats.py`'s `nearest_value`, `median_of`
and `welch_ttest` ARE imported, since CLAUDE.md designates `stats.py` as
shared.

Verified against EXPERIMENT.md's own recorded H13 holdout table before
shipping -- this script's output must match those exactly or something
has drifted (see the pipeline test): holdout +180d Acceleration n=20
neg=60.0% median=-35.8%, Main n=21 neg=47.6% median=+2.8%; +365d
Acceleration neg=80.0% median=-73.0%, Main neg=33.3% median=+18.6%;
+720d Acceleration n=20 neg=65.0% median=-33.7%, Main n=18 neg=27.8%
median=+6.7%.

Run: .venv/bin/python -m pipeline.appdata.build_ipo_boards
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from pipeline.appdata.common import APP_DIR, REPO_ROOT
from pipeline.stats import median_of, nearest_value, welch_ttest

UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"

RESEARCH_DATE = "2026-09-13"
MAX_GAP_DAYS = 10
RETURN_FIELD = "adjclose"
HORIZONS_DAYS = [180, 365, 720]
MIN_GROUP_SIZE = 10
DATA_AS_OF = datetime(2026, 9, 13, tzinfo=timezone.utc)

EXPLORE_YEARS = ["2021", "2022"]
HOLDOUT_YEARS = ["2023", "2024"]
ALL_BOARDS = ["Acceleration", "Development", "Main", "Watchlist", "New Economy"]
TESTED_BOARDS = ["Acceleration", "Main"]  # the only pre-registered comparison


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


def _board_stats(rows: list[dict], board: str, horizon: int) -> dict | None:
    key = f"ret_{horizon}d"
    rets = [r[key] for r in rows if r["board"] == board and r[key] is not None]
    if not rets:
        return None
    n = len(rets)
    neg_rate = sum(1 for x in rets if x < 0) / n
    mean_ret = sum(rets) / n
    median_ret = median_of([{"v": x} for x in rets], "v")
    return {
        "n": n,
        "negative_rate_pct": round(100 * neg_rate, 1),
        "mean_return_pct": round(100 * mean_ret, 1),
        "median_return_pct": round(100 * median_ret, 1),
    }


def build_phase(rows: list[dict]) -> dict:
    horizons = {}
    for h in HORIZONS_DAYS:
        by_board = {}
        for board in ALL_BOARDS:
            stats = _board_stats(rows, board, h)
            if stats is not None:
                by_board[board] = stats

        key = f"ret_{h}d"
        accel = [r[key] for r in rows if r["board"] == "Acceleration" and r[key] is not None]
        main = [r[key] for r in rows if r["board"] == "Main" and r[key] is not None]
        welch = None
        if len(accel) >= MIN_GROUP_SIZE and len(main) >= MIN_GROUP_SIZE:
            t = welch_ttest(accel, main)
            welch = {"t": round(t.t, 2), "diff_pct": round(100 * t.diff, 1)}

        horizons[f"{h}d"] = {"by_board": by_board, "acceleration_vs_main_welch_t": welch}
    return {"n": len(rows), "horizons": horizons}


def main() -> None:
    if not PRICES_5Y_PATH.exists():
        raise FileNotFoundError(
            f"{PRICES_5Y_PATH} not found - dev_cache is gitignored and machine-local; "
            "re-fetch via pipeline/dev/ (free, Yahoo) if missing, never invent this data"
        )
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())

    listings = _parse_listings(universe)
    explore_listings = [ev for ev in listings if ev["year"] in EXPLORE_YEARS]
    holdout_listings = [ev for ev in listings if ev["year"] in HOLDOUT_YEARS]

    explore_rows = build_rows(explore_listings, prices5y)
    holdout_rows = build_rows(holdout_listings, prices5y)

    output = {
        "as_of": RESEARCH_DATE,
        "note": (
            "H13, a pre-registered, falsifiable hypothesis counted in the project's "
            "trial counter -- not a descriptive base rate. Verdict: falsified on the "
            "pre-registered Welch-t test at every horizon, in both explore and holdout "
            "phases (no cell clears even the plain ~1.96 threshold). But every one of "
            "the 6 (horizon x phase) Welch-t values is negative-signed, and the "
            "negative-rate/median gap between Acceleration and Main is large and "
            "consistent across all of them, matching independently-published "
            "literature's own ~2/3 figure for Acceleration closely enough to read as "
            "real underpowered evidence (group sizes of 13-21), not noise. Reported as "
            "both, not picking whichever framing looks cleaner. 'Listing price' is a "
            "same-day-close proxy from development-only Yahoo Finance data, never live "
            "in this product, NOT the actual IPO offer price. `listing_board` is the "
            "company's CURRENT board, not necessarily its board at IPO (2021+ listings "
            "carry 'Watchlist', a status assigned after listing), so board groups may "
            "partly reflect where stocks ended up; the likely direction of that bias is "
            "to exaggerate the Acceleration-vs-Main gap (inferred, not verified). Only Acceleration vs Main "
            "is part of the pre-registered test; Development/Watchlist/New Economy are "
            "descriptive only, no directional claim was pre-registered for them."
        ),
        "tested_boards": TESTED_BOARDS,
        "explore": build_phase(explore_rows),
        "holdout": build_phase(holdout_rows),
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "ipo_boards.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")
    for h in HORIZONS_DAYS:
        hd = output["holdout"]["horizons"][f"{h}d"]
        accel = hd["by_board"].get("Acceleration")
        main = hd["by_board"].get("Main")
        if accel and main:
            print(f"holdout +{h}d: Accel n={accel['n']} neg={accel['negative_rate_pct']}%  Main n={main['n']} neg={main['negative_rate_pct']}%")


if __name__ == "__main__":
    main()
