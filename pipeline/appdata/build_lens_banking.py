"""Build data/app/lens_banking.json — the Banking lens (docs/PRODUCT.md §9).

Scope note: only the 4 ratios with a defensible single "healthier
direction" get a peer-rank comparison (CASA ratio, capital adequacy
ratio, net interest margin - all higher-is-healthier; NPL ratio -
lower-is-healthier). Loan-to-deposit ratio is deliberately NOT ranked:
a real outlier found in the 2026-09-13 re-sweep (Bank Aladin Syariah,
LDR=920x - a small digital bank, not a units bug elsewhere in the field)
confirms LDR has no single "better" direction anyway (too low is
inefficient, too high is a liquidity risk) - ranking it would manufacture
a false claim of monotonicity. Shown as a plain stated number instead.

Peer rank, not a market average: an earlier draft computed a simple mean
for cross-bank comparison and found it distorted beyond usefulness by
that same LDR outlier (mean 21.28 instead of a sane ~0.7-0.9) - the same
"N of M peers" pattern already used elsewhere in this product
(build_stock_pages.py) is robust to a single absurd value in a way a
raw average is not.

Run: .venv/bin/python -m pipeline.appdata.build_lens_banking
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file

RANKED_FIELDS = {
    # field: higher_is_healthier
    "casa_ratio[2025]": True,
    "capital_adequacy_ratio[2025]": True,
    "net_interest_margin[2025]": True,
}


def _compute_npl_ratio(qv: dict) -> float | None:
    npl = qv.get("non_performing_loan[2025]")
    net_loan = qv.get("net_loan[2025]")
    if npl is None or net_loan is None or net_loan == 0:
        return None
    return npl / net_loan


def _compute_loan_growth(qv: dict) -> float | None:
    current = qv.get("net_loan[2025]")
    prior = qv.get("net_loan[2024]")
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / prior


def build_lens_banking(rows: list[dict]) -> dict:
    banks = [r for r in rows if r["query_values"].get("sub_sector") == "Banks"]

    # Precompute NPL ratio for every bank once, so peer-rank comparisons
    # below don't recompute it per-comparison.
    npl_by_symbol = {r["symbol"]: _compute_npl_ratio(r["query_values"]) for r in banks}

    results = {}
    for row in banks:
        symbol = row["symbol"]
        qv = row["query_values"]
        entry = {
            "company_name": row["company_name"],
            "loan_to_deposit_ratio": qv.get("loan_to_deposit_ratio[2025]"),
            "loan_growth": _compute_loan_growth(qv),
            "ratios": {},
        }

        for field, higher_is_healthier in RANKED_FIELDS.items():
            own_value = qv.get(field)
            if own_value is None:
                entry["ratios"][field] = None
                continue
            comparable = [
                peer["query_values"][field]
                for peer in banks
                if peer["symbol"] != symbol and peer["query_values"].get(field) is not None
            ]
            better_than = sum(
                1 for v in comparable if (own_value > v if higher_is_healthier else own_value < v)
            )
            entry["ratios"][field] = {
                "value": own_value,
                "better_than_count": better_than,
                "comparable_count": len(comparable),
            }

        own_npl = npl_by_symbol[symbol]
        if own_npl is None:
            entry["ratios"]["npl_ratio"] = None
        else:
            comparable_npl = [v for s, v in npl_by_symbol.items() if s != symbol and v is not None]
            better_than = sum(1 for v in comparable_npl if own_npl < v)  # lower NPL is healthier
            entry["ratios"]["npl_ratio"] = {
                "value": own_npl,
                "better_than_count": better_than,
                "comparable_count": len(comparable_npl),
            }

        results[symbol] = entry

    return results


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())

    lens = build_lens_banking(rows)

    output = {"as_of": as_of, "source_file": universe_path.name, "banks": lens}

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "lens_banking.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {universe_path.name} (as_of {as_of})")
    print(f"{len(lens)} banks")

    bbca = lens.get("BBCA.JK")
    if bbca:
        print("\nBBCA sanity check:")
        print(json.dumps(bbca, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
