"""Resolves H1's free-float/volatility finding to every owned company
(docs/PRODUCT.md §5.2's "stock page — resolved to *this* stock" rendering;
§0 rule 7's current, re-verified boundary condition).

The rule, quoted directly from docs/PRODUCT.md §5.2 (not re-derived from
memory) — H1b's tested partitioning, corrected 2026-09-10 to drop the
retracted small-cap-only reading:
    - 4 market-cap size buckets (quartiles): smallest, small_mid, mid_large,
      largest.
    - Within each size bucket, 3 free-float terciles: low, mid, high.
    - 3 of the 4 size buckets are statistically significant: smallest,
      small_mid, largest. The 4th, mid_large, is not.
    - In a significant bucket: high tercile -> "Applies, risky side" (wider
      float, more volatile); low tercile -> "Applies, calm side"; mid
      tercile -> genuinely in between, no risky/calm framing (the plan
      explicitly permits this: "not every finding needs a 'does not apply'
      case").
    - In the non-significant bucket (mid_large): "weaker evidence for this
      size range" regardless of tercile.
    - Every rendering also carries the calendar-period caveat (2024-2026
      only, absent 2022-2023) - the frontend applies this uniformly, not
      per-bucket, since it's the same for every stock.

**Important scope note, disclosed rather than glossed over:** H1b's
original test only covered companies with usable 1-year Yahoo price
history (a few hundred, since the OUTCOME variable - max drawdown - needs
price data this app never ships). This module only needs the PREDICTOR
side (market_cap, free_float), which is real, owned Sectors data for all
962 companies - no price data, no Yahoo, no new cost. Applying the same
quartile/tercile PARTITIONING RULE to the full current universe is an
honest, live extension of the tested method, not a byte-for-byte replay of
H1b's original historical sample's exact cut points - percentile-based
cutoffs are inherently relative to whatever population they're computed
over (the same is true of any tercile/quartile rule, e.g. income brackets
recomputed yearly). Stated as such in the output, not implied to be more
precise than it is.

Uses `pipeline.stats.quintiles` (shared, generic - CLAUDE.md designates
`pipeline/stats.py` as common ground, not owned by either track) rather
than duplicating a bucketing helper that already exists.

Run: .venv/bin/python -m pipeline.appdata.build_h1_applicability
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file
from pipeline.stats import quintiles

SIZE_BUCKET_LABELS = ["smallest", "small_mid", "mid_large", "largest"]
SIGNIFICANT_SIZE_BUCKETS = {"smallest", "small_mid", "largest"}
FLOAT_TERCILE_LABELS = ["low", "mid", "high"]


def build_h1_applicability(rows: list[dict]) -> dict[str, dict]:
    """rows: raw universe sweep records (each with `symbol` and
    `query_values`). Returns {symbol: {size_bucket, size_bucket_significant,
    free_float_tercile}} for every company with both market_cap and
    free_float - both required for a valid size/float placement."""
    usable = []
    for row in rows:
        qv = row["query_values"]
        mc = qv.get("market_cap")
        ff = qv.get("free_float")
        if mc is None or ff is None:
            continue
        usable.append({"symbol": row["symbol"], "_mc": mc, "_ff": ff})

    size_buckets = quintiles(usable, "_mc", n_buckets=4)

    result: dict[str, dict] = {}
    for size_label, bucket_rows in zip(SIZE_BUCKET_LABELS, size_buckets):
        ff_terciles = quintiles(bucket_rows, "_ff", n_buckets=3)
        for tercile_label, tercile_rows in zip(FLOAT_TERCILE_LABELS, ff_terciles):
            for row in tercile_rows:
                result[row["symbol"]] = {
                    "size_bucket": size_label,
                    "size_bucket_significant": size_label in SIGNIFICANT_SIZE_BUCKETS,
                    "free_float_tercile": tercile_label,
                }
    return result


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())

    by_symbol = build_h1_applicability(rows)

    output = {
        "as_of": as_of,
        "source_file": universe_path.name,
        "note": (
            "H1's free-float/volatility finding (docs/PRODUCT.md §5.2), resolved per "
            "stock using the CURRENT full universe - a live application of the tested "
            "size-bucket/float-tercile rule, not a replay of the original study's exact "
            "historical cut points. Always carries the 2024-2026 calendar-period caveat."
        ),
        "evaluable_count": len(by_symbol),
        "universe_count": len(rows),
        "by_symbol": by_symbol,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "h1_applicability.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}: {len(by_symbol)} of {len(rows)} companies resolved")


if __name__ == "__main__":
    main()
