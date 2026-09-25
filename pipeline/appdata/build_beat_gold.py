"""Build data/app/beat_gold.json — the one-time, dated "beat gold" base-rate
result (docs/PRODUCT.md §7.3; research done as EXPERIMENT.md/docs/PLAN.md's
H16, 2026-09-12, by the hypothesis-testing session).

**Why this is compliant despite reading Yahoo dev-cache data**, restated
because it's the one place in the whole app-build where that's true:
`CLAUDE.md` bans Yahoo from shipping IN THE PRODUCT — the live frontend
never calls Yahoo, and nothing under `pipeline/dev/` is imported by
`frontend/`. This script is neither: it's a build-time-only precompute step
(same category as every other `pipeline/appdata/build_*.py` module) that
reads the already-fetched, free, dev-only cache
(`data/dev_cache/prices_5y.json`, `benchmarks_5y.json` — gitignored,
re-fetchable, zero cost) ONCE, and freezes only DERIVED FACTS (booleans and
percentages, never a raw price series) into `data/app/beat_gold.json`. That
frozen fact file is what the frontend actually reads. docs/PRODUCT.md §7.3
states explicitly why gold can never be reproduced from Sectors data at
all, and that this one disclosed, dated statistic is the deliberate
exception to "Sectors data must be core" — not an accidental live Yahoo
dependency.

Computation duplicates the small pieces of
`pipeline/hypotheses/h16_stock_vs_benchmarks.py` needed here (the
BI_RATE_TABLE and its compounding logic) rather than importing that module,
matching this session's established precedent
(`pipeline/appdata/lens_fields.py`'s docstring) of not depending on files
under the hypothesis-testing session's active territory. `pipeline/stats.py`
IS imported (`nearest_value`) since `CLAUDE.md` designates it explicitly as
shared, not owned by either track.

Verified against docs/PLAN.md's own recorded H16 result before shipping:
n=887, beat index 49.7%, beat gold 15.9%, beat BI-rate deposit 42.4%, 47.1%
negative annualized return — this script's own output must match those
exactly or something has drifted (see the pipeline test).

Run: .venv/bin/python -m pipeline.appdata.build_beat_gold
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone

from pipeline.appdata.common import APP_DIR, RAW_DIR, REPO_ROOT, UNIVERSE_GLOB, latest_dated_file
from pipeline.stats import nearest_value

PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
BENCHMARKS_PATH = REPO_ROOT / "data" / "dev_cache" / "benchmarks_5y.json"

MIN_YEARS = 1.0
MAX_GAP_DAYS = 10
RETURN_FIELD = "adjclose"
RESEARCH_DATE = "2026-09-12"  # when H16 was run / the Yahoo cache this reads was fetched


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=timezone.utc)


# Duplicated from pipeline/hypotheses/h16_stock_vs_benchmarks.py by design -
# see module docstring. Any change to BI policy history belongs there first.
BI_RATE_TABLE: list[tuple[datetime, float, str]] = [
    (_dt(2021, 1, 1), 0.0350, "snippet -- held since early 2021"),
    (_dt(2022, 8, 1), 0.0375, "snippet"),
    (_dt(2022, 9, 1), 0.0425, "snippet"),
    (_dt(2022, 10, 1), 0.0475, "snippet"),
    (_dt(2022, 11, 1), 0.0525, "snippet"),
    (_dt(2022, 12, 1), 0.0550, "snippet"),
    (_dt(2023, 2, 1), 0.0575, "snippet"),
    (_dt(2023, 9, 1), 0.0600, "snippet -- held through 2024"),
    (_dt(2025, 1, 15), 0.0575, "fetched -- docs/SOURCES.md"),
    (_dt(2025, 5, 21), 0.0550, "fetched -- docs/SOURCES.md"),
    (_dt(2025, 7, 15), 0.0525, "fetched -- docs/SOURCES.md"),
    (_dt(2025, 12, 17), 0.0475, "fetched -- bi.go.id, 2026-09-12 (one intermediate cut not pinned down)"),
    (_dt(2026, 5, 20), 0.0525, "fetched -- bi.go.id, 2026-09-12"),
    (_dt(2026, 6, 9), 0.0550, "fetched -- bi.go.id, 2026-09-12"),
    (_dt(2026, 6, 18), 0.0575, "fetched -- bi.go.id, 2026-09-12"),
]


def bi_deposit_return(start: datetime, end: datetime) -> float:
    total = 1.0
    for i, (eff_date, rate, _prov) in enumerate(BI_RATE_TABLE):
        seg_start = max(eff_date, start)
        next_date = BI_RATE_TABLE[i + 1][0] if i + 1 < len(BI_RATE_TABLE) else end
        seg_end = min(next_date, end)
        if seg_end <= seg_start:
            continue
        days = (seg_end - seg_start).total_seconds() / 86400
        total *= (1 + rate) ** (days / 365.25)
    return total - 1.0


def _annualize(total_return: float, years: float) -> float:
    return (1 + total_return) ** (1 / years) - 1


def build_rows(prices5y: dict, benchmarks: dict, sub_sectors: dict[str, str], company_names: dict[str, str]) -> list[dict]:
    jkse = benchmarks.get("^JKSE")
    gold_usd = benchmarks.get("GC=F")
    usdidr = benchmarks.get("USDIDR=X")
    rows = []
    for sym, entry in prices5y.items():
        closes = entry.get("close")
        adjcloses = entry.get(RETURN_FIELD)
        timestamps = entry.get("timestamps")
        if not closes or not adjcloses or not timestamps:
            continue
        if any(c <= 0 for c in closes):
            continue
        start_ts, end_ts = timestamps[0], timestamps[-1]
        years = (end_ts - start_ts) / 86400 / 365.25
        if years < MIN_YEARS:
            continue
        p0, p1 = adjcloses[0], adjcloses[-1]
        if p0 <= 0 or p1 <= 0:
            continue
        stock_ann = _annualize(p1 / p0 - 1, years)

        start_dt = datetime.fromtimestamp(start_ts, timezone.utc)
        end_dt = datetime.fromtimestamp(end_ts, timezone.utc)

        jkse_ann = None
        if jkse:
            j0 = nearest_value(jkse, start_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            j1 = nearest_value(jkse, end_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            if j0 is not None and j1 is not None:
                jkse_ann = _annualize(j1 / j0 - 1, years)

        gold_ann = None
        if gold_usd and usdidr:
            g0 = nearest_value(gold_usd, start_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            g1 = nearest_value(gold_usd, end_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            fx0 = nearest_value(usdidr, start_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            fx1 = nearest_value(usdidr, end_dt, field="close", max_gap_days=MAX_GAP_DAYS)
            if g0 is not None and g1 is not None and fx0 is not None and fx1 is not None:
                gold_idr_0, gold_idr_1 = g0 * fx0, g1 * fx1
                gold_ann = _annualize(gold_idr_1 / gold_idr_0 - 1, years)

        bi_ann = _annualize(bi_deposit_return(start_dt, end_dt), years)

        rows.append({
            "sym": sym,
            "company_name": company_names.get(sym),
            "years": years,
            "stock_ann": stock_ann,
            "jkse_ann": jkse_ann,
            "gold_ann": gold_ann,
            "bi_ann": bi_ann,
            "sub_sector": sub_sectors.get(sym),
        })
    return rows


def compute_typical_and_sector_median(rows: list[dict]) -> tuple[float, dict[str, float]]:
    """Shared by build_summary and build_per_symbol so both always agree on
    exactly the same "typical stock" and per-sector medians - previously
    each recomputed these independently from `rows`, which worked only
    because nobody had yet changed one copy without the other."""
    all_ann = [r["stock_ann"] for r in rows]
    typical = statistics.median(all_ann)
    by_sector: dict[str, list[float]] = {}
    for r in rows:
        if r["sub_sector"]:
            by_sector.setdefault(r["sub_sector"], []).append(r["stock_ann"])
    sector_median = {sec: statistics.median(vals) for sec, vals in by_sector.items()}
    return typical, sector_median


def build_summary(rows: list[dict], typical: float, sector_median: dict[str, float]) -> dict:
    """Aggregate, dated, disclosed facts only - no per-day series."""
    n = len(rows)
    all_ann = [r["stock_ann"] for r in rows]
    mean_ann = statistics.mean(all_ann)

    def win_rate(field: str) -> dict:
        pairs = [(r["stock_ann"], r[field]) for r in rows if r.get(field) is not None]
        wins = sum(1 for s, b in pairs if s > b)
        n_pairs = len(pairs)
        return {"wins": wins, "n": n_pairs, "pct": round(100 * wins / n_pairs, 1) if n_pairs else None}

    sector_pairs = [(r["stock_ann"], sector_median[r["sub_sector"]]) for r in rows if r["sub_sector"]]
    sector_wins = sum(1 for s, m in sector_pairs if s > m)

    negative = sum(1 for a in all_ann if a < 0)

    return {
        "research_date": RESEARCH_DATE,
        "n": n,
        "beat_index": win_rate("jkse_ann"),
        "beat_gold": win_rate("gold_ann"),
        "beat_deposit": win_rate("bi_ann"),
        "beat_typical_stock": {
            "wins": sum(1 for a in all_ann if a > typical),
            "n": n,
            "pct": round(100 * sum(1 for a in all_ann if a > typical) / n, 1) if n else None,
        },
        "beat_sector_peer": {
            "wins": sector_wins,
            "n": len(sector_pairs),
            "pct": round(100 * sector_wins / len(sector_pairs), 1) if sector_pairs else None,
        },
        "median_annualized_return_pct": round(100 * typical, 1),
        "mean_annualized_return_pct": round(100 * mean_ann, 1),
        "negative_return": {"count": negative, "n": n, "pct": round(100 * negative / n, 1)},
    }


def build_per_symbol(rows: list[dict], sector_median: dict[str, float], typical: float) -> dict[str, dict]:
    result = {}
    for r in rows:
        sym = r["sym"]
        result[sym] = {
            "company_name": r["company_name"],
            "years": round(r["years"], 1),
            "beat_index": None if r["jkse_ann"] is None else r["stock_ann"] > r["jkse_ann"],
            "beat_gold": None if r["gold_ann"] is None else r["stock_ann"] > r["gold_ann"],
            "beat_deposit": r["stock_ann"] > r["bi_ann"],
            "beat_typical_stock": r["stock_ann"] > typical,
            "beat_sector_peer": (
                None if not r["sub_sector"] or r["sub_sector"] not in sector_median
                else r["stock_ann"] > sector_median[r["sub_sector"]]
            ),
        }
    return result


def main() -> None:
    if not PRICES_5Y_PATH.exists() or not BENCHMARKS_PATH.exists():
        raise FileNotFoundError(
            f"{PRICES_5Y_PATH} / {BENCHMARKS_PATH} not found - dev_cache is gitignored and machine-local; "
            "re-fetch via pipeline/dev/ (free, Yahoo) if missing, never invent this data"
        )
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    benchmarks = json.loads(BENCHMARKS_PATH.read_text())

    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    universe = json.loads(universe_path.read_text())
    sub_sectors = {row["symbol"]: row["query_values"].get("sub_sector") for row in universe}
    company_names = {row["symbol"]: row["company_name"] for row in universe}

    rows = build_rows(prices5y, benchmarks, sub_sectors, company_names)
    typical, sector_median = compute_typical_and_sector_median(rows)
    summary = build_summary(rows, typical, sector_median)
    per_symbol = build_per_symbol(rows, sector_median, typical)

    output = {
        "as_of": RESEARCH_DATE,
        "note": (
            "Computed once from development-only Yahoo Finance price history "
            "(never live in this product) - a disclosed, dated research result, "
            "not a live capability. Gold has no Sectors-API equivalent at all."
        ),
        "summary": summary,
        "by_symbol": per_symbol,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "beat_gold.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")
    print(f"n={summary['n']}, beat_gold={summary['beat_gold']['pct']}%, beat_index={summary['beat_index']['pct']}%, "
          f"beat_deposit={summary['beat_deposit']['pct']}%, negative_return={summary['negative_return']['pct']}%")


if __name__ == "__main__":
    main()
