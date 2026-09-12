"""
H5 stress tests: attacking an existing finding, not proposing a new one.

STATUS: run once; every result below is reported regardless of outcome
(RULES.md verification item 6: ship the null if it's null). Mirrors
pipeline/hypotheses/h1_stress.py's design -- H5 had an explore/holdout
split (a stronger check than H1 originally had) but never got the same
placebo/split-half battery H1 did. This closes that gap.

Why running this against holdout-year rows does not violate H5's own
holdout discipline (h5_value_size.py's docstring: the frozen holdout
must not be re-run to fish for a better number). The two are different
questions, not the same question asked twice:
  - The holdout discipline protects an OUT-OF-SAMPLE PREDICTIVE claim --
    "does the pre-registered relationship hold on data the methodology
    never saw." That can only be tested once, honestly, per methodology
    version.
  - A placebo/split-half test asks a question about the STATISTICAL
    METHOD itself -- "could this pipeline manufacture a correlation like
    this from pure noise," "is the sign and significance stable under an
    arbitrary resample of the data already collected." Running this
    twice, or a hundred times, cannot let anyone selectively report a
    more favorable *predictive* number, because these tests never touch
    or restate the headline value/size-vs-return correlations from
    h5_value_size.py's own explore/holdout tables -- they run entirely
    separate computations (shuffled labels; a different random split)
    and are reported in full, gates and all, exactly once here.

Uses the FULL POOLED sample -- all four formation years (2022-2025),
explore and holdout combined -- collapsed to ONE ROW PER SYMBOL (see
`_collapse_to_symbol_level`) before either test. [Verified this session:
build_rows_for_year() returns a fresh row per (symbol, formation year)
pair with no dedup, so pooling all 4 years gave 2319 rows collapsing to
770 distinct symbols -- confirmed by running build_pooled_rows() and
counting.] A stock present across multiple formation years contributes
one row per year -- these are repeated observations of the same company,
not independent draws. Left uncollapsed, that would (a) let a split-half
test "pass" because
the same handful of companies' persistent characteristics leaked into
both halves, not because the relationship is genuinely stable across
different companies, and (b) inflate the placebo test's t-statistics,
which assume independent observations. Collapsing to one row per symbol
(averaging earnings_yield/size/ret across whatever years that symbol
has) is the standard fix for this when a full cluster-robust variance
estimator isn't worth building for a diagnostic check.

**Inherited limitation, not introduced here:** the collapsed sample
still only contains symbols with `pe > 0` in at least one formation year
(h5_value_size.py's own value-proxy filter). Both the value-leg and
size-leg stress results below describe profitable companies only, same
as h5_value_size.py's own explore/holdout tables -- this module doesn't
narrow the scope further, but doesn't widen it either.

Pre-registered interpretations (written before this was run):

Test 1 -- Placebo. Seeded shuffle of earnings_yield, and separately of
    size, across the symbol-level rows -- each with its OWN seed, so the
    two shuffles are independent permutations, not the same reordering
    applied twice. Gate: rho MUST collapse to ~0 for both. If either
    doesn't, stop -- the pipeline is manufacturing correlation and
    nothing else here is trustworthy.
Test 2 -- Random split-half. Seeded 50/50 split of the symbol-level
    sample (a third, distinct seed). FALSIFIED-AS-ROBUST (for either
    leg) if the two halves disagree in sign or one loses significance --
    that's a real stability concern for that leg specifically, not
    evidence the whole module is broken.

Run:
    .venv/bin/python -m pipeline.hypotheses.h5_stress
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict

from pipeline.hypotheses.h5_value_size import (
    EXPLORE_YEARS,
    HOLDOUT_YEARS,
    PRICES_5Y_PATH,
    UNIVERSE_PATH,
    build_rows_for_year,
)
from pipeline.stats import placebo_correlation, spearman, split_half

SEED_VALUE_SHUFFLE = 0
SEED_SIZE_SHUFFLE = 1
SEED_SPLIT_HALF = 2
MIN_ROWS_FOR_TEST = 10


def build_pooled_rows() -> list[dict]:
    universe = json.loads(UNIVERSE_PATH.read_text())
    prices5y = json.loads(PRICES_5Y_PATH.read_text())
    pooled: list[dict] = []
    for year in EXPLORE_YEARS + HOLDOUT_YEARS:
        pooled.extend(build_rows_for_year(universe, prices5y, year))
    return pooled


def _collapse_to_symbol_level(rows: list[dict]) -> list[dict]:
    """One row per symbol -- see the module docstring for why. Averages
    earnings_yield/size/ret across whatever formation years that symbol
    has in the pooled sample."""
    by_sym: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_sym[r["sym"]].append(r)
    collapsed = []
    for sym, group in by_sym.items():
        # Each row in `group` should be one (symbol, formation year) pair
        # from build_rows_for_year -- if the same year ever appeared
        # twice for one symbol (a corrupted/duplicated universe entry),
        # averaging would silently treat it as two independent years
        # instead of a data bug. Cheap to catch here; expensive to miss.
        years = [r["year"] for r in group]
        if len(years) != len(set(years)):
            raise ValueError(f"h5_stress: duplicate formation year for symbol {sym}: {years}")
        collapsed.append(
            {
                "sym": sym,
                "earnings_yield": statistics.mean(r["earnings_yield"] for r in group),
                "size": statistics.mean(r["size"] for r in group),
                "ret": statistics.mean(r["ret"] for r in group),
            }
        )
    return collapsed


def _print_placebo_gate(label: str, c) -> None:
    if math.isnan(c.rho):
        print(f"  shuffled {label}: rho=nan (n={c.n} too small for a meaningful correlation)")
        print("  GATE: SKIPPED -- insufficient data, not a pass or fail")
        return
    print(f"  shuffled {label} vs real return: rho={c.rho:+.4f}  t={c.t:+.2f}")
    print(f"  GATE: {'PASS' if abs(c.rho) < 0.1 else 'FAIL -- STOP, pipeline may be manufacturing correlation'}")


def test1_placebo(rows: list[dict]) -> None:
    print("\nTest 1 -- placebo (shuffled earnings_yield, shuffled size -- independent permutations)\n")
    rets = [r["ret"] for r in rows]
    _print_placebo_gate(
        "earnings_yield", placebo_correlation([r["earnings_yield"] for r in rows], rets, SEED_VALUE_SHUFFLE)
    )
    _print_placebo_gate("size", placebo_correlation([r["size"] for r in rows], rets, SEED_SIZE_SHUFFLE))


def test2_split_half(rows: list[dict]) -> None:
    print("\nTest 2 -- random split-half (symbol-level sample)\n")
    a, b = split_half(rows, SEED_SPLIT_HALF)
    for name, part in [("half A", a), ("half B", b)]:
        if len(part) < MIN_ROWS_FOR_TEST:
            print(f"  {name}: n={len(part)} -- insufficient data, skipped")
            continue
        rets = [r["ret"] for r in part]
        c_val = spearman([r["earnings_yield"] for r in part], rets)
        c_size = spearman([r["size"] for r in part], rets)
        print(
            f"  {name}: n={c_val.n}  value rho={c_val.rho:+.3f} t={c_val.t:+.2f}"
            f"  |  size rho={c_size.rho:+.3f} t={c_size.t:+.2f}"
        )


def main() -> None:
    pooled = build_pooled_rows()
    rows = _collapse_to_symbol_level(pooled)
    print(
        f"H5 stress tests -- {len(pooled)} pooled rows across 4 formation years, "
        f"collapsed to {len(rows)} distinct symbols (pe>0 filter inherited from h5_value_size.py)"
    )

    test1_placebo(rows)
    test2_split_half(rows)

    print(
        "\nSummary: these tests check the STATISTICAL METHOD, not H5's predictive\n"
        "claim (see the module docstring for why that distinction matters). A\n"
        "placebo PASS means the pipeline isn't inventing correlation from noise.\n"
        "Split-half agreement across the two legs is not equally strong evidence:\n"
        "the value leg is already confirmed in H5's own explore+holdout tables\n"
        "(EXPERIMENT.md), so split-half agreement there corroborates an existing\n"
        "result. The size leg is still an unconfirmed, single-year-driven lead --\n"
        "split-half agreement here does NOT resolve that concern, because a random\n"
        "row-level (well: symbol-level) split mixes years together and cannot\n"
        "detect a result that depends on which YEAR a row comes from. That\n"
        "year-concentration question is answered separately, in h5_value_size.py's\n"
        "own year-by-year breakdown, not by this module."
    )


if __name__ == "__main__":
    main()
