"""
Shared helpers for the 2026-09-27 stress tests (EXPERIMENT.md, "Pre-registration,
2026-09-27 -- stress tests of the newest hypotheses and situations"): Wilson
interval, a difference of two proportions, a stock-cluster bootstrap, a
permutation p-value, and the minimum detectable effect.

Constants are the pre-registered ones: B = 2,000 bootstrap replicates, 10,000
permutation shuffles, seed 20260927, Wilson 95% intervals. Standard library
only (pipeline/ has no numpy); every random draw comes from a `random.Random`
seeded with SEED, so a re-run prints the same numbers.

Nothing here reads data. The Student-t tail probability is imported from
`h6_foreign_list` (the project's exact-t p-value) rather than reimplemented.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Callable, Sequence

from pipeline.hypotheses.h6_foreign_list import _t_cdf_upper_two_sided

SEED = 20260927
BOOTSTRAP_B = 2000
PERMUTATIONS = 10000
Z_95 = 1.959963984540054
WIDE_POINTS = 20.0  # an interval wider than this many percentage points is "lebar"


def wilson(count: int, n: int, z: float = Z_95) -> tuple[float, float] | None:
    """Wilson score interval for a proportion, as fractions in [0, 1]; None if n == 0."""
    if n <= 0:
        return None
    p = count / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate(count: int, n: int) -> dict:
    """{count, n, rate, wilson_low, wilson_high} (fractions); rate and bounds are None when n == 0."""
    w = wilson(count, n)
    return {
        "count": count,
        "n": n,
        "rate": (count / n) if n else None,
        "wilson_low": w[0] if w else None,
        "wilson_high": w[1] if w else None,
    }


def newcombe_diff(c1: int, n1: int, c2: int, n2: int, z: float = Z_95) -> dict | None:
    """p1 - p2 with a Newcombe (hybrid score) interval built from the two Wilson intervals.

    Treats the two samples as independent. When one group is a subset of the other
    (a situation against all payers) that overstates the variance, so the interval
    is conservative, not liberal. `includes_zero` is the decision the ST3 rule uses.
    """
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = c1 / n1, c2 / n2
    l1, u1 = wilson(c1, n1, z)
    l2, u2 = wilson(c2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return {"diff": d, "low": lo, "high": hi, "includes_zero": lo <= 0 <= hi}


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (q in [0, 1]) of an already sorted sequence."""
    if not sorted_values:
        return float("nan")
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def percentile_interval(values: Sequence[float], level: float = 0.95) -> tuple[float, float]:
    s = sorted(values)
    a = (1 - level) / 2
    return percentile(s, a), percentile(s, 1 - a)


def cluster_bootstrap(
    clusters: dict[str, list],
    stat: Callable[[list], float | None],
    b: int = BOOTSTRAP_B,
    seed: int = SEED,
) -> dict:
    """Resample whole clusters (stocks) with replacement `b` times; percentile interval of `stat`.

    `clusters` maps a stock to its list of items (events); `stat` takes the pooled list of
    items of one replicate and returns a number (or None to skip the replicate). Returns
    the point estimate on the original sample, the 2.5th/97.5th percentiles, the number of
    clusters and the number of replicates that produced a value.
    """
    keys = sorted(clusters)
    pooled = [x for k in keys for x in clusters[k]]
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(b):
        sample: list = []
        for _k in range(len(keys)):
            sample.extend(clusters[keys[rng.randrange(len(keys))]])
        v = stat(sample)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            draws.append(v)
    lo, hi = percentile_interval(draws) if draws else (float("nan"), float("nan"))
    return {"estimate": stat(pooled), "low": lo, "high": hi, "n_clusters": len(keys), "n_valid_replicates": len(draws)}


def moving_block_bootstrap(
    series: Sequence,
    stat: Callable[[list], float | None],
    block_len: int = 20,
    b: int = BOOTSTRAP_B,
    seed: int = SEED,
) -> dict:
    """Overlapping moving-block bootstrap (Kunsch 1989): resample blocks of
    `block_len` CONSECUTIVE items, with replacement, concatenated back up to
    the original length. Unlike `cluster_bootstrap` (which resamples whole,
    already-independent clusters), this is for a single ordered time series
    where nearby observations are themselves correlated (e.g. a market state
    label and its next-20-day outcome, which overlaps with its neighbours'
    outcome windows) -- resampling individual points with replacement would
    treat that overlap as independent information and understate the true
    variance. `stat` takes one resampled list and returns a number (or None
    to skip that replicate, matching `cluster_bootstrap`'s convention).

    Added for T1 (`pipeline/hypotheses/t1_market_state.py`), which
    pre-registered this exact method (`kind-juggling-hoare.md` plan
    section 4.7 / EXPERIMENT.md, 2026-09-27) for its market-level
    difference-in-differences statistic.
    """
    n = len(series)
    if n == 0:
        return {"estimate": None, "low": float("nan"), "high": float("nan"), "n": 0, "n_valid_replicates": 0}
    rng = random.Random(seed)
    n_blocks_needed = math.ceil(n / block_len)
    max_start = max(0, n - block_len)  # last valid block start index (inclusive)
    draws: list[float] = []
    for _ in range(b):
        sample: list = []
        for _ in range(n_blocks_needed):
            start = rng.randrange(0, max_start + 1)
            sample.extend(series[start : start + block_len])
        v = stat(sample[:n])
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            draws.append(v)
    lo, hi = percentile_interval(draws) if draws else (float("nan"), float("nan"))
    return {"estimate": stat(list(series)), "low": lo, "high": hi, "n": n, "n_valid_replicates": len(draws)}


def cluster_bootstrap_rate(clusters: dict[str, tuple[int, int]], b: int = BOOTSTRAP_B, seed: int = SEED) -> dict:
    """Cluster bootstrap of a pooled proportion; `clusters` maps stock -> (count, n) over its events."""
    items = {k: [v] for k, v in clusters.items() if v[1] > 0}

    def stat(sample: list) -> float | None:
        n = sum(x[1] for x in sample)
        return (sum(x[0] for x in sample) / n) if n else None

    return cluster_bootstrap(items, stat, b, seed)


def permutation_position(real: float, perm: Sequence[float]) -> dict:
    """Where `real` falls among permuted statistics.

    p_two_sided = (1 + #{|perm| >= |real|}) / (B + 1); p_upper = the same for perm >= real;
    percentile = share of permuted values strictly below `real`.
    """
    b = len(perm)
    two = sum(1 for p in perm if abs(p) >= abs(real))
    upper = sum(1 for p in perm if p >= real)
    below = sum(1 for p in perm if p < real)
    return {
        "real": real,
        "n_perm": b,
        "p_two_sided": (1 + two) / (b + 1),
        "p_upper": (1 + upper) / (b + 1),
        "percentile": below / b if b else float("nan"),
        "perm_mean": statistics.fmean(perm) if perm else float("nan"),
        "perm_sd": statistics.stdev(perm) if len(perm) > 1 else float("nan"),
    }


def t_quantile_two_sided(p_two_sided: float, df: int) -> float:
    """The t with two-sided tail probability `p_two_sided` (bisection on the exact-t tail)."""
    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _t_cdf_upper_two_sided(mid, df) > p_two_sided:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def mde_mean(sd: float, n: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable true mean for a one-sample two-sided t-test: (t_{1-a/2} + t_{power}) * sd / sqrt(n).

    Power 80% and alpha 0.05 are the conventional defaults (the pre-registration asks for
    "the minimum detectable effect" without fixing them; stated where printed).
    """
    df = n - 1
    if df < 2 or not sd or math.isnan(sd):
        return float("nan")
    t_alpha = t_quantile_two_sided(alpha, df)
    t_power = t_quantile_two_sided(2 * (1 - power), df)
    return (t_alpha + t_power) * sd / math.sqrt(n)


def is_wide(*widths_fraction: float | None) -> bool:
    """True if any given interval is wider than WIDE_POINTS percentage points."""
    return any(w is not None and w * 100 > WIDE_POINTS for w in widths_fraction)


def fmt_pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.{digits}f}%"


def fmt_rate(r: dict) -> str:
    """'121 of 999 (12.1%) [Wilson 10.2%-14.3%]'."""
    if not r["n"]:
        return f"{r['count']} of 0"
    return f"{r['count']} of {r['n']} ({fmt_pct(r['rate'])}) [Wilson {fmt_pct(r['wilson_low'])}-{fmt_pct(r['wilson_high'])}]"


def check_frozen(label: str, got, frozen) -> bool:
    """Print a reproduction line, `got` next to the frozen value; return whether they are equal."""
    ok = got == frozen
    print(f"  reproduction {label}: got {got} | frozen {frozen} | {'OK' if ok else 'MISMATCH'}")
    return ok
