"""Build data/app/flags.json from the purchased universe sweep.

All four anomaly flags (docs/PRODUCT.md §6). Each threshold has a stated
rationale, and EXPERIMENT.md ("Results, batch 2", F1) reports how many
stocks each flag marks at -20% / as shipped / +20% of its threshold, with
no outcome read and no threshold changed afterwards:
  - payout above earnings: prior-year dividend paid is more than the year's
    earnings (ratio above 100%). Since 2026-09-26 this uses H4's own
    construct (2025 dividend x shares / 2025 earnings) rather than the
    trailing snapshot `payout_ratio`, which disagreed with H4 for 17 of the
    29 stocks it flagged (EXPERIMENT.md, batch 1 I2). The count moved from
    29 to the H4-construct count; the old snapshot version is kept as
    `build_payout_snapshot_flag` for that comparison.
  - near the high, earnings down: within 10% of the all-time high while
    2025 earnings are below 2024's (a round 10% band).
  - yield far above own average: at least 1.5x the company's own average
    dividend yield ("at least 50% above").
  - LQ45 member with free float under 25% (a quarter of shares).
The counts of the older version (29/326, 14/852, 89/462) were once
reverse-derived to match the plan's hand-verified numbers; that is now
disclosed rather than defended. The 4th flag
(free float < 25% while in LQ45) needed a real re-sweep with `indices`
added (2026-09-13, ~6 credits, see docs/credit_ledger.md) - the field
existed in the live schema but not the original 2026-09-12 sweep.

Run: .venv/bin/python -m pipeline.appdata.build_flags
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file
from pipeline.stats import payout_ratio_from_totals

PAYOUT_RATIO_THRESHOLD = 1.0  # exactly 100% does NOT trip the flag (§26)
NEAR_ATH_THRESHOLD = 0.10  # within 10% of all-time high
YIELD_ABOVE_AVG_MULTIPLIER = 1.5  # "far above" = at least 50% above own average
LQ45_LOW_FLOAT_THRESHOLD = 0.25  # free float strictly under 25%


PAYOUT_YEAR = 2025


def build_payout_above_earnings(rows: list[dict]) -> dict:
    """H4's construct: PAYOUT_YEAR dividend x shares / PAYOUT_YEAR earnings above 100%."""
    evaluable = []
    flagged = []
    for row in rows:
        qv = row["query_values"]
        ratio = payout_ratio_from_totals(
            qv.get(f"total_dividend[{PAYOUT_YEAR}]"),
            qv.get(f"earnings[{PAYOUT_YEAR}]"),
            qv.get(f"outstanding_shares[{PAYOUT_YEAR}]"),
        )
        if ratio is None:
            continue
        evaluable.append(row["symbol"])
        if ratio > PAYOUT_RATIO_THRESHOLD:
            flagged.append({"symbol": row["symbol"], "company_name": row.get("company_name"), "payout_ratio": ratio})
    flagged.sort(key=lambda r: r["payout_ratio"], reverse=True)
    return {"flagged": flagged, "evaluable_count": len(evaluable), "flagged_count": len(flagged)}


def build_payout_snapshot_flag(rows: list[dict]) -> dict:
    """The pre-2026-09-26 flag on the trailing snapshot `payout_ratio` (kept for the I2 comparison)."""
    evaluable = []
    flagged = []
    for row in rows:
        ratio = row["query_values"].get("payout_ratio")
        if ratio is None:
            continue
        evaluable.append(row["symbol"])
        if ratio > PAYOUT_RATIO_THRESHOLD:
            flagged.append({"symbol": row["symbol"], "company_name": row.get("company_name"), "payout_ratio": ratio})
    flagged.sort(key=lambda r: r["payout_ratio"], reverse=True)
    return {"flagged": flagged, "evaluable_count": len(evaluable), "flagged_count": len(flagged)}


def build_near_ath_earnings_decline(rows: list[dict]) -> dict:
    evaluable = []
    flagged = []
    for row in rows:
        qv = row["query_values"]
        ath = qv.get("all_time_high_price")
        current = qv.get("last_close_price")
        earnings_2025 = qv.get("earnings[2025]")
        earnings_2024 = qv.get("earnings[2024]")
        if ath is None or current is None or ath == 0 or earnings_2025 is None or earnings_2024 is None:
            continue
        evaluable.append(row["symbol"])
        pct_below_ath = (ath - current) / ath
        if pct_below_ath <= NEAR_ATH_THRESHOLD and earnings_2025 < earnings_2024:
            flagged.append({
                "symbol": row["symbol"],
                "company_name": row.get("company_name"),
                "pct_below_ath": pct_below_ath,
                "earnings_2025": earnings_2025,
                "earnings_2024": earnings_2024,
            })
    flagged.sort(key=lambda r: r["pct_below_ath"])
    return {"flagged": flagged, "evaluable_count": len(evaluable), "flagged_count": len(flagged)}


def build_yield_far_above_average(rows: list[dict]) -> dict:
    evaluable = []
    flagged = []
    for row in rows:
        qv = row["query_values"]
        yield_ttm = qv.get("yield_ttm")
        yield_avg = qv.get("dividend_yield_avg")
        if yield_ttm is None or yield_avg is None or yield_avg == 0:
            continue
        evaluable.append(row["symbol"])
        if yield_ttm >= YIELD_ABOVE_AVG_MULTIPLIER * yield_avg:
            flagged.append({
                "symbol": row["symbol"],
                "company_name": row.get("company_name"),
                "yield_ttm": yield_ttm,
                "yield_avg": yield_avg,
            })
    flagged.sort(key=lambda r: r["yield_ttm"] / r["yield_avg"], reverse=True)
    return {"flagged": flagged, "evaluable_count": len(evaluable), "flagged_count": len(flagged)}


def build_lq45_low_float(rows: list[dict]) -> dict:
    """Evaluable population is LQ45 members only - free float has no
    special meaning for a non-member, so this is never "X of 962"."""
    evaluable = []
    flagged = []
    for row in rows:
        qv = row["query_values"]
        indices = qv.get("indices")
        # An empty list ("confirmed not in any index") and an absent/null
        # field ("we don't know") are different facts (§26) - only treat
        # a row as an LQ45 member when `indices` is an actual list
        # containing it, never when the field is simply missing.
        if not isinstance(indices, list) or "LQ45" not in indices:
            continue
        free_float = qv.get("free_float")
        if free_float is None:
            continue
        evaluable.append(row["symbol"])
        if free_float < LQ45_LOW_FLOAT_THRESHOLD:
            flagged.append({"symbol": row["symbol"], "company_name": row.get("company_name"), "free_float": free_float})
    flagged.sort(key=lambda r: r["free_float"])
    return {"flagged": flagged, "evaluable_count": len(evaluable), "flagged_count": len(flagged)}


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())

    flags = {
        "as_of": as_of,
        "source_file": universe_path.name,
        "payout_above_earnings": build_payout_above_earnings(rows),
        "near_ath_earnings_decline": build_near_ath_earnings_decline(rows),
        "yield_far_above_average": build_yield_far_above_average(rows),
        "lq45_low_float": build_lq45_low_float(rows),
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "flags.json"
    out_path.write_text(json.dumps(flags, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {universe_path.name} (as_of {as_of})")
    for key in ("payout_above_earnings", "near_ath_earnings_decline", "yield_far_above_average", "lq45_low_float"):
        f = flags[key]
        print(f"  {key}: {f['flagged_count']} of {f['evaluable_count']}")


if __name__ == "__main__":
    main()
