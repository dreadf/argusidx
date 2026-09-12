"""
H1b: does the free-float -> max-drawdown relationship survive size control?

STATUS: exploratory, not confirmatory -- same caveat as H1 (see EXPERIMENT.md).
No held-out period; a second data point on the same untested population.

Pre-registered hypothesis (committed before looking at this result):
    H1's uncontrolled result already shows free float negatively correlated
    with max drawdown (rho=-0.185, t=-5.50: wider float -> deeper drawdowns).
    H1's *volatility* version of this relationship turned out to be
    concentrated in small caps and to nearly vanish among large caps once
    market cap was controlled for. H1b asks whether the *drawdown* version
    does the same.
    Falsified if: the drawdown relationship holds roughly evenly across all
    four size buckets (i.e. it is NOT a small-cap-specific effect like the
    volatility one was).

Data: entirely already-owned, zero incremental cost.
    data/raw/free_float_2026-09-06.json   -- Sectors, purchased for H1
    data/raw/market_cap_2026-09-06.json   -- Sectors, purchased for H1
    data/dev_cache/prices_1y.json         -- Yahoo, free, cached for H1

Run:
    python -m pipeline.hypotheses.h1b_float_drawdown_size
"""
from __future__ import annotations

from pipeline.hypotheses.h1_free_float import (
    build_1y_rows,
    load_free_float,
    load_market_cap,
)
from pipeline.stats import median_of, quintiles, spearman


def print_drawdown_size_control(rows: list[dict], mcap: dict[str, float]) -> None:
    sized = [r | {"mc": mcap[r["sym"]]} for r in rows if r["sym"] in mcap]
    print(f"H1b -- float vs max drawdown, size-controlled, n={len(sized)}\n")

    c_uncontrolled = spearman([r["ff"] for r in sized], [r["mdd"] for r in sized])
    print(f"  Uncontrolled: rho={c_uncontrolled.rho:+.3f}  t={c_uncontrolled.t:+.2f}")

    print("\n  Double sort -- within each size bucket, does float still predict drawdown?")
    size_buckets = quintiles(sized, "mc", n_buckets=4)
    labels = ["smallest", "small-mid", "mid-large", "largest"]
    for label, bucket in zip(labels, size_buckets):
        c = spearman([r["ff"] for r in bucket], [r["mdd"] for r in bucket])
        ff_buckets = quintiles(bucket, "ff", n_buckets=3)
        lo = median_of(ff_buckets[0], "mdd")
        hi = median_of(ff_buckets[-1], "mdd")
        print(
            f"    {label:>10}: n={len(bucket):>4}  rho={c.rho:+.3f}  t={c.t:+.2f}"
            f"  low_ff_mdd={lo:.1%}  high_ff_mdd={hi:.1%}"
        )


def main() -> None:
    ff = load_free_float()
    mcap = load_market_cap()
    rows = build_1y_rows(ff)

    print_drawdown_size_control(rows, mcap)

    print(
        "\nTrial count: 2 (H1, H1b). H1b reuses H1's exact dataset and split, "
        "so it is not an independent confirmation -- it is a second measurement "
        "on the same sample, testing a related but distinct question (drawdown, "
        "not volatility)."
    )


if __name__ == "__main__":
    main()
