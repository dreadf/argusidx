"""
H5 timing-precision diagnostic: is the size leg's one confirmed year
(formation 2024 -> return May-Sep 2025) concentrated around the BI
rate-cut date inside that window, or spread evenly across it?

STATUS: diagnostic on an ALREADY-OBSERVED result, run once, reported
regardless of outcome. This is NOT a new trial and does not touch H5's
own holdout discipline (h5_value_size.py) -- it computes no new
value/size-vs-return correlation and reports no headline number; it only
splits one already-measured window's return into two sub-periods to ask
a mechanism question about a result already on record.

## Why this exists (see the working plan, "Part A", 2026-09-11)

H5's size leg is confirmed in only one of its two holdout years
(2024->2025: t=-7.48; 2025->2026: t=-0.51 -- see EXPERIMENT.md). Verified
this session (read-only checks against owned data, not assumed): there is
NO way to add a genuinely new, independent formation year before the
2026-09-30 freeze. `pe[2021]` is confirmed absent from every field in the
purchased universe (checked every field with "equity", "book_value",
"net_income", or "earnings" in its name -- none can reconstruct it), and
the next new formation year (2026) needs `pe[2026]`, not public until
~Q1-Q2 2027, long past the freeze. **This diagnostic cannot resolve that
weakness and is not presented as doing so.** It can only make the
best-supported explanation for the one confirmed year (a rate-cut-driven
small-cap rotation, EXPERIMENT.md's H5 entry) more or less internally
consistent.

## What is being tested

Bank Indonesia cut its benchmark rate three times in 2025: 15 Jan,
**21 May**, and 15-16 Jul (each -25bp; see EXPERIMENT.md's H5 entry and
docs/SOURCES.md). Only the 21 May and 15-16 Jul cuts fall inside the
2024-formation outcome window (1 May - 4 Sep 2025) -- 15 Jan is before
the window opens. This splits that single window's return at the 21 May
cut date (nearest Yahoo close, via `stats.nearest_value`, the same helper
h5_value_size.py already uses for the same cache) into a pre-cut and a
post-cut sub-period, and re-measures the size-vs-return correlation in
each half separately.

**Pre-registered interpretation (written before running):**
- If the size effect is concentrated in the post-cut sub-period (rho more
  negative / more significant after 21 May than before), that is
  consistent with -- but does not prove -- the rate-cut explanation
  already on record.
- If the effect is roughly evenly split across both sub-periods, or
  stronger BEFORE the cut, that weakens the rate-cut story without
  necessarily replacing it with anything better -- inconclusive, not
  falsifying (a single window split two ways is a low-power test either
  way, with n roughly halved along a dimension -- calendar time within
  one year -- that was never itself pre-registered as a predictor).
- Either outcome leaves the actual product decision unchanged: size stays
  scoreboard-only, not shipped as a feature, because the core weakness
  (confirmed in only one of two holdout years) is untouched by this
  check.

Uses the same value/size proxies, same `adjclose` return field, and same
2024 formation year as h5_value_size.py's own confirmed result --
calls `h5_value_size.build_rows_for_year` directly with its `midpoint`
parameter (added for this diagnostic) rather than duplicating that
function's pe/shares filtering and price lookups, matching how
h5_stress.py already reuses the same function.

Cost: $0 -- pure computation on the owned Yahoo dev cache, no Sectors or
    new Yahoo call.

Run:
    .venv/bin/python -m pipeline.hypotheses.h5_timing_diagnostic
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pipeline.hypotheses.h5_value_size import PRICES_5Y_PATH, UNIVERSE_PATH, build_rows_for_year
from pipeline.stats import median_of, quintiles, spearman

FORMATION_YEAR = 2024  # the one holdout year size is confirmed in
RATE_CUT_DATE = datetime(2025, 5, 21, tzinfo=timezone.utc)


def print_sub_period_test(rows: list[dict], ret_field: str, label: str) -> None:
    print(f"\n{label} -- n={len(rows)}")
    if len(rows) < 10:
        print("  insufficient data, skipped")
        return
    c = spearman([r["size"] for r in rows], [r[ret_field] for r in rows])
    print(f"  size vs {ret_field}: rho={c.rho:+.3f}  t={c.t:+.2f}")
    print("  Size quintiles (Q1=smallest, Q5=largest):")
    for i, bucket in enumerate(quintiles(rows, "size"), start=1):
        print(
            f"    Q{i}: n={len(bucket):>4}  size_median={median_of(bucket, 'size'):,.0f}"
            f"  {ret_field}_median={median_of(bucket, ret_field):+.1%}"
        )


def main() -> None:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    rows = build_rows_for_year(universe, prices5y, FORMATION_YEAR, midpoint=RATE_CUT_DATE)

    print(
        f"H5 timing-precision diagnostic -- formation {FORMATION_YEAR}, "
        f"window split at the {RATE_CUT_DATE.date()} BI rate cut (n={len(rows)})"
    )
    print(
        "\nThis is a diagnostic on an already-observed result, not a new trial "
        "and not a fix for the 'confirmed in only one year' weakness -- see "
        "the module docstring."
    )

    print_sub_period_test(rows, "ret", "Full window (1 May - 4 Sep 2025) -- for reference, matches EXPERIMENT.md")
    print_sub_period_test(rows, "ret_pre", f"Pre-cut sub-period (1 May - {RATE_CUT_DATE.date()})")
    print_sub_period_test(rows, "ret_post", f"Post-cut sub-period ({RATE_CUT_DATE.date()} - 4 Sep 2025)")


if __name__ == "__main__":
    main()
