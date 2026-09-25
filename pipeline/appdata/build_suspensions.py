"""Build data/app/suspensions.json from the purchased suspension history.

Feeds the stock page's "flags & suspension history" section
(docs/PRODUCT.md §4, point 3; §6 "Suspension history"). Reuses the full-history
pull already fetched and logged in docs/credit_ledger.md (2026-09-13, 20
credits, approved) - this module spends nothing new, it only reshapes data
already owned.

docs/PRODUCT.md is explicit that a raw suspension list is just reformatted
Sectors data (excluded by the hackathon rules) and only becomes derived
insight paired with (1) a base rate - how this company's suspension count
compares to the rest of the market - and (2) reason categories, since
"unusual price movement" and "late financial reporting" mean very different
things. Both are computed here, not left for the frontend to guess at.

Run: .venv/bin/python -m pipeline.appdata.build_suspensions
"""
from __future__ import annotations

import bisect
import json
from collections import defaultdict

from pipeline.appdata.common import APP_DIR, RAW_DIR, SUSPENSIONS_GLOB, UNIVERSE_GLOB, latest_dated_file

# Checked against all 588 real events in the owned 2026-09-13 pull: stripping
# the ticker mention from each reason string collapses 373 unique strings
# down to 16 real patterns (verified via
# `re.sub(r"saham [A-Z]{2,5}\.JK", "saham TICKER", reason)` over every
# record). Every one of those 16 patterns matches exactly one rule below -
# zero events fall through to "other" empirically, so "other" exists only as
# an honest fallback if a future refresh introduces a new pattern, never
# silently absorbing real data now. Order matters: checked top to bottom,
# first match wins (e.g. a "cooling down" clause that also names a price
# increase is attributed to the price movement, its actual trigger).
REASON_RULES: list[tuple[str, str, str]] = [
    ("peningkatan harga kumulatif", "unusual_price_movement", "unusual_price_movement"),
    ("penurunan harga kumulatif", "unusual_price_movement", "unusual_price_movement"),
    ("cooling down", "cooling_down", "unusual_price_movement"),
    ("laporan keuangan", "late_financial_reporting", "governance_or_compliance"),
    ("kelangsungan usaha", "going_concern_doubt", "governance_or_compliance"),
    ("V.1.1", "listing_requirement_not_met", "governance_or_compliance"),
    ("V.1.2", "listing_requirement_not_met", "governance_or_compliance"),
    ("biaya pencatatan", "listing_fee_delay", "governance_or_compliance"),
    ("papan pemantauan khusus", "special_monitoring_board", "governance_or_compliance"),
    ("obligasi", "bond_payment_delay", "governance_or_compliance"),
    ("amortisasi", "bond_payment_delay", "governance_or_compliance"),
    ("delisting", "delisting_related", "delisting_related"),
    ("go private", "delisting_related", "delisting_related"),
    ("tidak tercatat di bursa", "delisting_related", "delisting_related"),
    ("suspend more than 6 month", "extended_suspension", "extended_suspension"),
]

CATEGORY_LABELS_ID: dict[str, str] = {
    "unusual_price_movement": "Kenaikan/penurunan harga tidak wajar",
    "cooling_down": "Cooling down setelah kenaikan harga tidak wajar",
    "late_financial_reporting": "Terlambat menyampaikan laporan keuangan",
    "going_concern_doubt": "Bursa meragukan kelangsungan usaha",
    "listing_requirement_not_met": "Belum memenuhi ketentuan pencatatan",
    "listing_fee_delay": "Terlambat membayar biaya pencatatan tahunan",
    "special_monitoring_board": "Lebih dari 1 tahun di papan pemantauan khusus",
    "bond_payment_delay": "Terlambat membayar kewajiban obligasi",
    "delisting_related": "Terkait proses delisting",
    "extended_suspension": "Suspensi berkepanjangan (lebih dari 6 bulan)",
    "other": "Alasan lain yang belum dikategorikan",
}

GROUP_LABELS_ID: dict[str, str] = {
    "unusual_price_movement": "Pergerakan harga tidak wajar",
    "governance_or_compliance": "Pelaporan atau kepatuhan",
    "delisting_related": "Terkait delisting",
    "extended_suspension": "Suspensi berkepanjangan",
    "other": "Lainnya",
}


def categorize_reason(reason: str) -> dict:
    lowered = reason.lower()
    for substring, category, group in REASON_RULES:
        if substring.lower() in lowered:
            return {
                "category": category,
                "category_label_id": CATEGORY_LABELS_ID[category],
                "group": group,
                "group_label_id": GROUP_LABELS_ID[group],
            }
    return {
        "category": "other",
        "category_label_id": CATEGORY_LABELS_ID["other"],
        "group": "other",
        "group_label_id": GROUP_LABELS_ID["other"],
    }


def build_suspensions_by_symbol(records: list[dict]) -> dict[str, list[dict]]:
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        event = {
            "date": record["suspension_date"],
            "reason": record["reason"],
            "pdf_url": record["pdf_url"],
        }
        event.update(categorize_reason(record["reason"]))
        by_symbol[record["symbol"]].append(event)
    # Most recent first, per company.
    for symbol in by_symbol:
        by_symbol[symbol].sort(key=lambda r: r["date"], reverse=True)
    return dict(by_symbol)


def build_base_rates(by_symbol: dict[str, list[dict]], universe_symbols: list[str]) -> dict[str, dict]:
    """Per-company: how its suspension count compares to the rest of the
    market. Percentile is computed against the FULL universe (companies with
    zero suspensions count as zero), not just the companies that have ever
    been suspended - "more than Y% of the market" means the whole market."""
    counts = {symbol: len(by_symbol.get(symbol, [])) for symbol in universe_symbols}
    sorted_counts = sorted(counts.values())
    universe_size = len(universe_symbols)

    result = {}
    for symbol, count in counts.items():
        if count == 0:
            continue
        fewer_than = bisect.bisect_left(sorted_counts, count)
        result[symbol] = {
            "count": count,
            "universe_count": universe_size,
            "more_than_pct": round(100 * fewer_than / universe_size, 1),
        }
    return result


def main() -> None:
    source_path = latest_dated_file(RAW_DIR, SUSPENSIONS_GLOB)
    as_of = source_path.stem.replace("suspensions_", "")
    records = json.loads(source_path.read_text())

    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    universe_rows = json.loads(universe_path.read_text())
    universe_symbols = [row["symbol"] for row in universe_rows]

    by_symbol = build_suspensions_by_symbol(records)
    base_rates = build_base_rates(by_symbol, universe_symbols)

    universe_count = len(universe_symbols)
    universe_set = set(universe_symbols)
    companies_with_suspensions = sum(1 for s in by_symbol if s in universe_set)

    output = {
        "as_of": as_of,
        "source_file": source_path.name,
        "total_events": len(records),
        "universe_count": universe_count,
        "companies_with_suspensions": companies_with_suspensions,
        "base_rate_pct": round(100 * companies_with_suspensions / universe_count, 1),
        "by_symbol": by_symbol,
        "base_rates": base_rates,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "suspensions.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {source_path.name} (as_of {as_of})")
    print(f"{len(records)} events across {len(by_symbol)} companies ({companies_with_suspensions} in the universe)")
    print(f"Base rate: {output['base_rate_pct']}% of {universe_count} companies ever suspended")


if __name__ == "__main__":
    main()
