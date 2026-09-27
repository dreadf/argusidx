"""
R2a -- does the number of active warnings on a stock predict a subsequent
large fall? (+1 trial if common support qualifies; otherwise descriptive.)

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-27: T1, R1 and
R2a") before this module was run. Consumes R1's merged warning list
(fell_30 merges into long_below_peak on the real panel; 7 warnings remain)
and the shared stock x month-start panel (_warnings_panel.py).

- Cells: size tercile x 60-day realised-volatility tercile, each cut
  cross-sectionally WITHIN each formation month (same per-month convention
  the panel already uses for the payout tercile), both measured strictly
  before formation.
- Common support: a cell counts only if each of the 0/1/2/3+ active-warning
  groups has >=30 observations in BOTH explore and holdout. Fewer than 2
  qualifying cells -> R2a is descriptive, not a trial.
- Outcomes within 126 trading days of formation: D (>=30% fall at any
  point in the window), U (>=30% rise), L (a suspension announced inside
  the window, `data/raw/suspensions_*.json`). A stock in this panel is by
  construction still in the current universe, so "delisted" cannot be
  observed here -- a disclosed survivorship limit, same one already stated
  on Cara-Menguji ("Hanya perusahaan yang masih tercatat...").
- Split: explore = formations from 2022-05-01 whose whole 126-day window
  completes before 2024-01-01 (embargoed otherwise, same mechanic as T1).
  Holdout = formations from 2024-01-01 with a complete window.
- Pass (holdout, cell-weighted, qualifying cells only): (1) D-U rises
  monotonically with the count (0 < 1 < 2 < 3+); (2) D-U for the 2+ group
  beats D-U for the single strongest warning, chosen using EXPLORE data
  only (a plain pooled D-U among rows where exactly that one warning is
  active) -- so the choice can't be reverse-engineered from holdout.

Run:
    .venv/bin/python -m pipeline.hypotheses.r2a_warning_count
"""
from __future__ import annotations

import json
import statistics
from datetime import date, datetime, timezone

from pipeline.appdata.common import RAW_DIR, SUSPENSIONS_GLOB, latest_dated_file
from pipeline.hypotheses._warnings_panel import (
    WARNING_KEYS,
    build_panel,
    load_prices,
    load_universe,
    usable_closes_with_dates,
)
from pipeline.hypotheses.r1_warning_overlap import PANEL_END, active_sets, find_merges

FALL_THRESHOLD = 0.70  # D: price <= 70% of formation close within the window (a 30%+ fall)
RISE_THRESHOLD = 1.30  # U: price >= 130% of formation close within the window (a 30%+ rise)
OUTCOME_WINDOW = 126
HOLDOUT_START = "2024-01-01"
MIN_CELL_GROUP = 30
MIN_QUALIFYING_CELLS = 2
MAX_BUCKET = 3  # 0, 1, 2, 3(+)


def merged_warning_keys(rows: list[dict]) -> list[str]:
    """R1's merge rule, applied here so R2a never has to be re-run by hand
    if R1's real-data merges change (single source of truth: the panel
    itself, not a hardcoded list)."""
    sets = active_sets(rows)
    merges = find_merges(sets)
    dropped = {general for _specific, general, _j in merges}
    return [k for k in WARNING_KEYS if k not in dropped]


def load_suspensions() -> dict[str, list[str]]:
    path = latest_dated_file(RAW_DIR, SUSPENSIONS_GLOB)
    rows = json.loads(path.read_text())
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["symbol"], []).append(r["suspension_date"])
    for sym in out:
        out[sym].sort()
    return out


def compute_outcomes(rows: list[dict], prices: dict, suspensions: dict[str, list[str]]) -> tuple[list[dict], int]:
    """Attaches d/u/l/window_start/window_end to rows with a complete
    126-trading-day window; drops (counts, doesn't keep) rows whose window
    runs past the price cache's own end."""
    pairs_cache: dict[str, list[tuple[float, float]]] = {}
    kept: list[dict] = []
    dropped_end = 0
    for r in rows:
        symbol = r["symbol"]
        if symbol not in pairs_cache:
            pairs_cache[symbol] = usable_closes_with_dates(prices[symbol])
        pairs = pairs_cache[symbol]
        idx = r["formation_idx"]
        end_idx = idx + OUTCOME_WINDOW
        if end_idx >= len(pairs):
            dropped_end += 1
            continue
        base = pairs[idx][1]
        window = pairs[idx + 1 : end_idx + 1]
        window_closes = [c for _t, c in window]
        d = 1 if any(c <= base * FALL_THRESHOLD for c in window_closes) else 0
        u = 1 if any(c >= base * RISE_THRESHOLD for c in window_closes) else 0
        w_start_date = datetime.fromtimestamp(window[0][0], timezone.utc).date().isoformat()
        w_end_date = datetime.fromtimestamp(window[-1][0], timezone.utc).date().isoformat()
        susp_dates = suspensions.get(symbol, [])
        l = 1 if any(w_start_date <= sd <= w_end_date for sd in susp_dates) else 0
        kept.append(dict(r, d=d, u=u, l=l, window_start=w_start_date, window_end=w_end_date))
    return kept, dropped_end


def split_explore_holdout(rows: list[dict]) -> tuple[list[dict], list[dict], int]:
    explore, holdout = [], []
    dropped_embargo = 0
    for r in rows:
        if r["month_start"] >= HOLDOUT_START:
            holdout.append(r)
        elif r["window_end"] < HOLDOUT_START:
            explore.append(r)
        else:
            dropped_embargo += 1
    return explore, holdout, dropped_embargo


def _attach_tercile_field(month_rows: list[dict], field: str, out_field: str) -> None:
    usable = [r for r in month_rows if r.get(field) is not None]
    if len(usable) < 3:
        for r in month_rows:
            r[out_field] = None
        return
    ordered = sorted(usable, key=lambda r: r[field])
    n = len(ordered)
    thirds = [ordered[: n // 3], ordered[n // 3 : 2 * n // 3], ordered[2 * n // 3 :]]
    assigned = set()
    for tercile_idx, group in enumerate(thirds):
        for r in group:
            r[out_field] = tercile_idx
            assigned.add(id(r))
    for r in month_rows:
        if id(r) not in assigned:
            r[out_field] = None


def attach_terciles(rows: list[dict]) -> None:
    """Size and 60-day-volatility terciles, each cut cross-sectionally
    within its own formation month (mutates `rows` in place)."""
    by_month: dict[str, list[dict]] = {}
    for r in rows:
        by_month.setdefault(r["month_start"], []).append(r)
    for month_rows in by_month.values():
        _attach_tercile_field(month_rows, "size", "size_tercile")
        _attach_tercile_field(month_rows, "vol_60", "vol_tercile")


def warning_count(row: dict, keys: list[str]) -> int:
    return sum(1 for k in keys if row["warnings"][k])


def count_bucket(n: int) -> int:
    return min(n, MAX_BUCKET)


def qualifying_cells(explore: list[dict], holdout: list[dict], keys: list[str]) -> tuple[list[tuple[int, int]], dict]:
    """Cells (size_tercile, vol_tercile) where every count bucket (0/1/2/3+)
    has >=MIN_CELL_GROUP rows in BOTH periods. Returns (qualifying cells,
    a {(period, cell, bucket): n} detail dict for reporting)."""
    cells = {
        (r["size_tercile"], r["vol_tercile"])
        for r in explore + holdout
        if r["size_tercile"] is not None and r["vol_tercile"] is not None
    }
    detail: dict[tuple[str, tuple[int, int], int], int] = {}
    qualifying = []
    for cell in sorted(cells):
        ok = True
        for period_name, period_rows in (("explore", explore), ("holdout", holdout)):
            for bucket in range(MAX_BUCKET + 1):
                n = sum(
                    1
                    for r in period_rows
                    if (r["size_tercile"], r["vol_tercile"]) == cell and count_bucket(warning_count(r, keys)) == bucket
                )
                detail[(period_name, cell, bucket)] = n
                if n < MIN_CELL_GROUP:
                    ok = False
        if ok:
            qualifying.append(cell)
    return qualifying, detail


def cell_weighted_du_by_bucket(rows: list[dict], cells: list[tuple[int, int]], keys: list[str]) -> dict[int, float | None]:
    """D-U per active-warning bucket, weighted by each qualifying cell's own
    observation count in `rows` (the caller passes holdout rows for the
    pass rule, or explore rows for the exploratory check)."""
    out: dict[int, float | None] = {}
    for bucket in range(MAX_BUCKET + 1):
        total_n = 0
        weighted_sum = 0.0
        for cell in cells:
            group = [
                r
                for r in rows
                if (r["size_tercile"], r["vol_tercile"]) == cell and count_bucket(warning_count(r, keys)) == bucket
            ]
            if not group:
                continue
            du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
            weighted_sum += du * len(group)
            total_n += len(group)
        out[bucket] = (weighted_sum / total_n) if total_n else None
    return out


def choose_champion_warning(explore: list[dict], keys: list[str]) -> tuple[str | None, float | None]:
    """The single warning (among `keys`) with the highest pooled D-U among
    explore rows where exactly that one warning is active alone (count==1).
    Chosen on EXPLORE ONLY, before any holdout comparison."""
    best_key, best_du = None, None
    for k in keys:
        group = [r for r in explore if count_bucket(warning_count(r, keys)) == 1 and r["warnings"][k]]
        if len(group) < MIN_CELL_GROUP:
            continue
        du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
        if best_du is None or du > best_du:
            best_key, best_du = k, du
    return best_key, best_du


def cell_weighted_du_two_plus(rows: list[dict], cells: list[tuple[int, int]], keys: list[str]) -> float | None:
    """D-U for the '2+' group (active-warning count >= 2, i.e. buckets 2 and
    3+ combined -- distinct from the per-bucket breakdown used for the
    monotonicity check), cell-weighted over the qualifying cells."""
    total_n = 0
    weighted_sum = 0.0
    for cell in cells:
        group = [
            r
            for r in rows
            if (r["size_tercile"], r["vol_tercile"]) == cell and count_bucket(warning_count(r, keys)) >= 2
        ]
        if not group:
            continue
        du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
        weighted_sum += du * len(group)
        total_n += len(group)
    return (weighted_sum / total_n) if total_n else None


def cell_weighted_du_for_champion(holdout: list[dict], cells: list[tuple[int, int]], champion: str, keys: list[str]) -> float | None:
    total_n = 0
    weighted_sum = 0.0
    for cell in cells:
        group = [
            r
            for r in holdout
            if (r["size_tercile"], r["vol_tercile"]) == cell
            and count_bucket(warning_count(r, keys)) == 1
            and r["warnings"][champion]
        ]
        if not group:
            continue
        du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
        weighted_sum += du * len(group)
        total_n += len(group)
    return (weighted_sum / total_n) if total_n else None


def main() -> None:
    prices = load_prices()
    universe = load_universe()
    rows, panel_stats = build_panel(prices, universe, end=PANEL_END)
    print(f"Panel: {panel_stats}")

    keys = merged_warning_keys(rows)
    print(f"Warning keys after R1's merge: {keys}")

    suspensions = load_suspensions()
    rows, dropped_end = compute_outcomes(rows, prices, suspensions)
    print(f"Outcomes computed for {len(rows)} rows; {dropped_end} dropped (window runs past the cache's end)")

    attach_terciles(rows)

    explore, holdout, dropped_embargo = split_explore_holdout(rows)
    print(f"Explore: {len(explore)}, holdout: {len(holdout)}, dropped at embargo: {dropped_embargo}")
    print(f"L (suspension inside the window): explore {sum(r['l'] for r in explore)}, holdout {sum(r['l'] for r in holdout)}")

    cells, detail = qualifying_cells(explore, holdout, keys)
    print(f"\nQualifying cells (size_tercile, vol_tercile), >= {MIN_CELL_GROUP} per bucket in both periods: {cells}")
    if len(cells) < MIN_QUALIFYING_CELLS:
        print(f"\n**R2a: fewer than {MIN_QUALIFYING_CELLS} qualifying cells -- DESCRIPTIVE, not a trial.**")
        print("Each warning is shown alone; no count/combination claim is made.")
        for period_name, period_rows in (("explore", explore), ("holdout", holdout)):
            print(f"\n{period_name} D-U by single warning (pooled, not cell-weighted):")
            for k in keys:
                group = [r for r in period_rows if r["warnings"][k]]
                if group:
                    du = statistics.mean(r["d"] for r in group) - statistics.mean(r["u"] for r in group)
                    print(f"  {k:<28}: n={len(group):>5}  D-U={du:+.3f}")
        return

    holdout_du = cell_weighted_du_by_bucket(holdout, cells, keys)
    explore_du = cell_weighted_du_by_bucket(explore, cells, keys)
    print("\nHoldout cell-weighted D-U by active-warning count (qualifying cells only):")
    for b in range(MAX_BUCKET + 1):
        label = f"{b}" if b < MAX_BUCKET else f"{b}+"
        print(f"  {label}: {holdout_du[b]}")
    print("\nExplore cell-weighted D-U by active-warning count (for reference, not the decision):")
    for b in range(MAX_BUCKET + 1):
        label = f"{b}" if b < MAX_BUCKET else f"{b}+"
        print(f"  {label}: {explore_du[b]}")

    monotonic = all(
        holdout_du[b] is not None and holdout_du[b + 1] is not None and holdout_du[b] < holdout_du[b + 1]
        for b in range(MAX_BUCKET)
    )
    print(f"\nMonotonic on holdout (0 < 1 < 2 < 3+): {monotonic}")

    champion, champion_explore_du = choose_champion_warning(explore, keys)
    print(f"\nStrongest single warning, chosen on explore: {champion} (explore D-U {champion_explore_du})")
    champion_holdout_du = cell_weighted_du_for_champion(holdout, cells, champion, keys) if champion else None
    two_plus_holdout_du = cell_weighted_du_two_plus(holdout, cells, keys)
    beats_champion = (
        champion_holdout_du is not None
        and two_plus_holdout_du is not None
        and two_plus_holdout_du > champion_holdout_du
    )
    print(f"Holdout D-U, champion warning alone (count==1): {champion_holdout_du}")
    print(f"Holdout D-U, 2+ warnings (count>=2): {two_plus_holdout_du}")
    print(f"2+ beats the champion on holdout: {beats_champion}")

    confirmed = monotonic and beats_champion
    print(f"\n**R2a: {'CONFIRMED' if confirmed else 'NOT confirmed'}**")


if __name__ == "__main__":
    main()
