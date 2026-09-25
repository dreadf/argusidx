"""
Reusable statistics for hypothesis testing.

Pure functions, no I/O, no credentials. Every hypothesis module builds on
these rather than reimplementing them, so a bug fixed here is fixed
everywhere (see RULES.md process rule 3: fix the class, not the instance).
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone


def _assert_all_positive(closes: list[float], caller: str) -> None:
    """Shared guard: every close must be > 0, or every ratio downstream
    (log, division, drawdown) is either undefined or silently wrong.

    Single implementation so a future change to this rule (or its error
    message) can't drift between callers -- log_returns and max_drawdown
    used to each carry their own copy of this exact loop, which is
    precisely the kind of duplication this module's own docstring warns
    against ("a bug fixed here is fixed everywhere").

    No non-positive price has been observed in this project's data as of
    the current dev caches -- spot-checked, not tracked by an automated
    test or logged verification, so treat this as inferred, not settled;
    guarded so a future bad source
    fails loudly instead of quietly corrupting log_returns (which used to
    silently drop the whole transition around a bad price -- shrinking
    no_move_fraction's denominator and desynchronizing the series
    annualized_volatility and max_drawdown each compute their own way
    from the same closes) or max_drawdown (a non-positive peak divides by
    zero; a non-positive *current* price alone reports a "drawdown" past
    -100%, e.g. peak=100, c=-5 gives c/peak - 1 = -1.05).
    """
    for c in closes:
        if c <= 0:
            raise ValueError(f"{caller}: non-positive price {c} in series")


def log_returns(closes: list[float]) -> list[float]:
    """Daily log returns from a series of closing prices.

    Raises on a non-positive price rather than silently skipping it --
    see _assert_all_positive.
    """
    _assert_all_positive(closes, "log_returns")
    return [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]


def annualized_volatility(closes: list[float], trading_days: int = 252) -> float:
    """Standard deviation of daily log returns, annualized."""
    rets = log_returns(closes)
    if len(rets) < 2:
        return float("nan")
    return statistics.pstdev(rets) * math.sqrt(trading_days)


def max_drawdown(closes: list[float]) -> float:
    """Worst peak-to-trough decline, as a negative fraction (e.g. -0.487).

    Raises on a non-positive price -- see _assert_all_positive.
    """
    if not closes:
        return float("nan")
    _assert_all_positive(closes, "max_drawdown")
    peak = closes[0]
    worst = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = c / peak - 1
        if dd < worst:
            worst = dd
    return worst


def total_return(closes: list[float]) -> float:
    if len(closes) < 2 or closes[0] == 0:
        return float("nan")
    return closes[-1] / closes[0] - 1


def no_move_fraction(closes: list[float]) -> float:
    """Share of days the price did not move at all (stale-price diagnostic).

    NOT a liquidity or trading-frequency measure -- see docs/DATA.md.
    This only sees days a price exists; a day the stock never traded
    produces no bar at all and is invisible here, not counted as "no
    movement". Using this to check whether stocks "genuinely trade" is
    exactly the mistake documented in EXPERIMENT.md's H1 entry.
    """
    rets = log_returns(closes)
    if not rets:
        return float("nan")
    return sum(1 for r in rets if abs(r) < 1e-9) / len(rets)


@dataclass
class CorrResult:
    rho: float
    t: float
    n: int


def _average_ranks(x: list[float]) -> list[float]:
    """Ranks (0-indexed), with tied values assigned their average rank.

    Standard convention for Spearman correlation. Distinct sequential
    ranks (ignoring ties) fabricate structure: six identical x-values
    against a monotonic y previously reported rho=+1.0 -- a perfect
    correlation from zero information -- with the sign flipping purely
    with input order. Several fields in this project's real data have
    ties (free_float, max_drawdown, no_move_fraction all repeat), so this
    is not just an edge case.
    """
    order = sorted(range(len(x)), key=lambda k: x[k])
    ranks = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> CorrResult:
    """Spearman rank correlation plus its t-statistic.

    Rank correlation is used throughout rather than Pearson correlation
    because small-cap price series are dominated by extreme outliers that
    distort ordinary correlation (see EXPERIMENT.md, H1 methodology).

    For n < 3 there is no meaningful t-statistic (and at n=2, rho is
    mathematically always +/-1 regardless of the data -- a correlation
    estimate containing no information). Returns NaN for both rather than
    a spurious perfect correlation; reachable whenever a hypothesis module
    slices data into small subgroups.
    """
    n = len(a)
    if n != len(b):
        # A bare `assert` here is stripped entirely under `python -O`, silently
        # disabling this check exactly where the module's own convention
        # (_assert_all_positive) is to fail loudly, not silently.
        raise ValueError(f"spearman: inputs must be the same length (got {n} and {len(b)})")
    if n < 3:
        return CorrResult(rho=float("nan"), t=float("nan"), n=n)
    x, y = _average_ranks(a), _average_ranks(b)
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = math.sqrt(
        sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)
    )
    rho = num / den if den else 0.0
    if abs(rho) >= 1:
        # Perfect correlation: t is +/- infinity, sign matching rho.
        # (Previously always +inf regardless of sign -- a perfect
        # negative correlation reported the same t as a perfect positive one.)
        t = math.copysign(float("inf"), rho)
    else:
        t = rho * math.sqrt((n - 2) / (1 - rho**2))
    return CorrResult(rho=rho, t=t, n=n)


def quintiles(rows: list[dict], sort_key: str, n_buckets: int = 5) -> list[list[dict]]:
    """Sort rows by sort_key and cut into n_buckets equal-ish groups.

    Buckets are sized as evenly as possible: any remainder is spread one
    row per bucket starting from the first, rather than dumped entirely
    into the last one. (The previous version gave the last bucket
    everything left over -- n=9 into 5 buckets produced sizes
    [1,1,1,1,5] -- so the "first bucket vs last bucket" comparison every
    hypothesis module here makes was drawing its last-bucket median from
    a bucket several times wider than the first.)

    If n < n_buckets, some buckets are unavoidably empty (there is no way
    to split 2 rows into 5 non-empty groups) -- callers should expect
    this; median_of returns NaN for an empty bucket rather than raising.
    """
    ordered = sorted(rows, key=lambda r: r[sort_key])
    n = len(ordered)
    base, remainder = divmod(n, n_buckets)
    buckets = []
    start = 0
    for i in range(n_buckets):
        size = base + (1 if i < remainder else 0)
        buckets.append(ordered[start : start + size])
        start += size
    return buckets


def closes_in_year(entry: dict, year: int, field: str = "close") -> list[float]:
    """Values from a dev-cache entry ({"timestamps": [...], "close": [...],
    "adjclose": [...]}, see pipeline/dev/fetch_yahoo_prices.py) falling in
    a given calendar year (UTC).

    Single implementation so this epoch-to-year slicing -- previously
    copy-pasted across h1_stress.py (twice) and h1_free_float.py's
    print_year_by_year -- can't drift between callers. `field` defaults to
    "close" (H1 uses raw price; H5 explicitly switches to "adjclose" --
    see docs/DATA.md's close-vs-adjclose note for why that split is
    deliberate, not an oversight).
    """
    timestamps = entry["timestamps"]
    values = entry[field]
    if len(timestamps) != len(values):
        # zip() would silently truncate to the shorter array and desync
        # which timestamp pairs with which price -- fail loudly instead,
        # same convention as _assert_all_positive above.
        raise ValueError(
            f"closes_in_year: timestamps ({len(timestamps)}) and {field!r} "
            f"({len(values)}) have different lengths"
        )
    return [
        v
        for t, v in zip(timestamps, values)
        if datetime.fromtimestamp(t, timezone.utc).year == year
    ]


def nearest_value(
    entry: dict, target: datetime, field: str = "close", max_gap_days: int = 10
) -> float | None:
    """Value closest to `target` in a dev-cache entry ({"timestamps": [...],
    "close": [...], "adjclose": [...]}), or None if nothing falls within
    `max_gap_days`.

    Same shared-helper reasoning as closes_in_year (single implementation,
    not copy-pasted per hypothesis module). `field` defaults to "close";
    H5 passes "adjclose" explicitly since its return calculation must
    include dividends -- see docs/DATA.md's close-vs-adjclose note.

    Delegates the actual nearest-timestamp scan to `nearest_index` --
    previously duplicated the same loop independently (found by
    /code-review, 2026-09-12), which meant a future fix to the scan
    itself (tie-breaking, or switching to a binary search on the sorted
    timestamps) would have to be made in two places to stay in sync.
    """
    timestamps = entry["timestamps"]
    values = entry[field]
    if len(timestamps) != len(values):
        raise ValueError(
            f"nearest_value: timestamps ({len(timestamps)}) and {field!r} "
            f"({len(values)}) have different lengths"
        )
    idx = nearest_index(entry, target, max_gap_days=max_gap_days)
    if idx is None:
        return None
    best_value = values[idx]
    if best_value <= 0:
        # Same fail-loudly convention as _assert_all_positive: a
        # non-positive price flowing silently into a caller's
        # shares*price or ratio calculation (h5_value_size.py does
        # both) would corrupt a result with no error at all.
        raise ValueError(f"nearest_value: non-positive price {best_value} at matched date")
    return best_value


def nearest_index(entry: dict, target: datetime, max_gap_days: int = 10) -> int | None:
    """Index of the timestamp closest to `target` in a dev-cache entry
    ({"timestamps": [...], ...}), or None if nothing falls within
    `max_gap_days`. Same date-matching logic as `nearest_value`, but
    returns the position rather than a field's value at that position --
    needed by H15 (pipeline/hypotheses/h15_technical_fundamental_interactions.py)
    to look up a precomputed `rsi()`/`moving_average()` array (computed
    once per symbol, not per row) at the formation date, rather than
    recomputing the indicator from scratch for every row.
    """
    timestamps = entry["timestamps"]
    target_ts = target.timestamp()
    best_gap = None
    best_idx = None
    for i, t in enumerate(timestamps):
        gap = abs(t - target_ts)
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best_idx = i
    if best_gap is not None and best_gap <= max_gap_days * 86400:
        return best_idx
    return None


def moving_average(closes: list[float], window: int) -> list[float | None]:
    """Trailing simple moving average, aligned to `closes` (same length).

    `out[i]` is the average of `closes[i-window+1 : i+1]`, or None where
    there isn't yet `window` bars of history. Used by H14
    (pipeline/hypotheses/h14_technical_indicators.py) for the price-vs-
    200-day-MA trend signal -- a single shared implementation rather than
    a copy computed per sample point, matching this module's own "fix it
    once" convention.
    """
    if window < 1:
        raise ValueError(f"moving_average: window must be >= 1, got {window}")
    n = len(closes)
    out: list[float | None] = [None] * n
    if n < window:
        return out
    running_sum = sum(closes[:window])
    out[window - 1] = running_sum / window
    for i in range(window, n):
        running_sum += closes[i] - closes[i - window]
        out[i] = running_sum / window
    return out


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Wilder's Relative Strength Index, aligned to `closes` (same length).

    `out[i]` is None until index `period` (the first index with `period`
    prior daily changes to average). Standard Wilder smoothing: the first
    average gain/loss is a simple mean over the first `period` changes,
    every subsequent one is exponentially smoothed
    ((prev*(period-1) + new) / period) -- the same formula used by every
    mainstream charting platform, not an invented variant, since H14 tests
    the actual indicator retail traders read.

    RSI is defined as 100 when avg_loss is 0 and avg_gain > 0 (price only
    went up), and 50 when both are 0 (price never moved) -- the
    conventional edge-case handling, since RS = avg_gain/avg_loss is
    undefined (0/0) or infinite otherwise.
    """
    n = len(closes)
    out: list[float | None] = [None] * n
    if n <= period:
        return out
    deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    def _value(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _value(avg_gain, avg_loss)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = _value(avg_gain, avg_loss)
    return out


def placebo_correlation(values: list[float], outcomes: list[float], seed: int) -> CorrResult:
    """Spearman correlation between `outcomes` and a seeded shuffle of
    `values` -- the shuffle breaks any real pairing, so a real effect
    should collapse to rho~0. If it doesn't, the statistical pipeline
    itself may be manufacturing correlation from noise.

    Single implementation so this exact pattern -- previously
    copy-pasted between h1_stress.py's test3_placebo and h5_stress.py's
    placebo check -- can't drift (this module's own "fix it once"
    convention). Deliberately returns the CorrResult rather than
    printing or gating: callers each print their own labelled message
    and decide their own pass/fail wording, keeping this module free of
    I/O per its own docstring.
    """
    shuffled = values[:]
    random.Random(seed).shuffle(shuffled)
    return spearman(shuffled, outcomes)


def split_half(rows: list, seed: int) -> tuple[list, list]:
    """Seeded random 50/50 split of `rows` into two halves.

    Single implementation so this exact pattern -- previously
    copy-pasted between h1_stress.py and h5_stress.py -- can't drift
    between callers (this module's own "fix it once" convention). Odd
    `n` gives the second half one extra row (floor division on the
    first), matching both callers' original behavior.

    Does NOT address clustered/panel data on its own -- if `rows`
    contains repeated observations of the same entity (e.g. one row per
    year for the same stock), a plain row-level shuffle can split one
    entity's rows across both halves, which breaks the independence the
    two halves are supposed to have. Callers with that shape (h5_stress.py)
    must collapse to one row per entity before calling this.
    """
    rnd = random.Random(seed)
    shuffled = rows[:]
    rnd.shuffle(shuffled)
    half = len(shuffled) // 2
    return shuffled[:half], shuffled[half:]


def payout_ratio_from_totals(dividend_per_share: float | None, earnings: float | None, shares: float | None) -> float | None:
    """Payout ratio = dividend-per-share / EPS, where EPS = earnings / shares.

    **Verified** against the live schema (`https://api.sectors.app/schema/`,
    2026-09-13): `total_dividend[year]` is documented as "Total dividends
    paid PER SHARE for the year"; `earnings[year]` is documented as
    "Annual net profit/loss in IDR" -- i.e. company-TOTAL, not EPS.
    Dividing dividend directly by earnings (this project's original
    construction, in both H4 and H10 before this fix) is off by a factor
    of shares outstanding, not a payout ratio at all -- independently
    **verified** by sanity-checking BBCA's FY2024 `total_dividend`/
    `earnings`/`outstanding_shares` figures against the already-
    purchased snapshot `payout_ratio` field: the naive division gave
    5e-12, while the corrected formula gives 0.624, close to (not
    identical to -- the snapshot is a TTM figure, not FY2024-specific,
    so an exact match isn't expected) the snapshot's 0.80. Same order
    of magnitude, which is what this check was actually establishing --
    stated precisely rather than implying a like-for-like match. Single
    implementation here per
    this module's own "fix it once" convention -- H4 and H10 each had
    their own copy of this fix before being consolidated (found by
    /code-review, 2026-09-13).

    Returns None if any input is missing or if earnings/shares aren't
    both positive (payout ratio is undefined for a loss-making company or
    a non-payer), matching this module's None-for-undefined convention.
    """
    if dividend_per_share is None or earnings is None or shares is None:
        return None
    if earnings <= 0 or shares <= 0:
        return None
    eps = earnings / shares  # always > 0: both operands already guarded above
    return dividend_per_share / eps


def sector_neutral_rank(rows: list[dict], field: str, group_key: str) -> list[dict]:
    """Returns `rows` (only those with a non-None `field`) with a new
    `f"{field}_rank"` in [0, 1]: each row's percentile rank of `field`
    WITHIN its own `group_key` group (e.g. sub_sector), not across the
    whole pool.

    Added for H10 (pipeline/hypotheses/h10_broad_feature_screen.py) --
    strips systematic sector-level differences (a bank's P/E is not
    comparable to a miner's) while keeping the full pooled sample size,
    the "sector-neutral rank" design already committed to in the plan
    before this was written. A group of size 1 gets rank 0.5 (the
    convention this uses for "no information to rank against"), matching
    the tie-handling spirit of `_average_ranks` rather than an arbitrary
    0 or 1.
    """
    usable = [r for r in rows if r.get(field) is not None]
    groups: dict[object, list[dict]] = {}
    for r in usable:
        groups.setdefault(r[group_key], []).append(r)
    out = []
    for group_rows in groups.values():
        n = len(group_rows)
        if n == 1:
            out.append(dict(group_rows[0], **{f"{field}_rank": 0.5}))
            continue
        ranks = _average_ranks([r[field] for r in group_rows])
        for r, rank in zip(group_rows, ranks):
            out.append(dict(r, **{f"{field}_rank": rank / (n - 1)}))
    return out


def median_of(rows: list[dict], field: str) -> float:
    """Median of a field across rows.

    NaN for an empty list, matching the NaN-for-insufficient-data
    convention used elsewhere in this module -- rather than the
    StatisticsError statistics.median raises on empty input, which was
    reachable whenever quintiles() returned an empty bucket (n < n_buckets).
    """
    if not rows:
        return float("nan")
    return statistics.median(r[field] for r in rows)


@dataclass
class TTestResult:
    mean_a: float
    mean_b: float
    diff: float  # mean_a - mean_b
    t: float
    n_a: int
    n_b: int


def normal_two_sided_p(z: float) -> float:
    """Two-sided p-value for a z/t statistic under the standard-normal
    approximation -- this project already treats every t-statistic
    (spearman, welch_ttest) against the asymptotic ~1.96 threshold as if
    it were normal, so this makes that existing convention explicit and
    numeric rather than introducing a new one. `math.erfc`, stdlib only
    -- no scipy dependency, matching this module's existing constraint
    (see welch_ttest's docstring).

    NaN in, NaN out (matching this module's NaN-for-insufficient-data
    convention elsewhere).
    """
    if math.isnan(z):
        return float("nan")
    return math.erfc(abs(z) / math.sqrt(2))


def benjamini_hochberg(p_values: list[float], q: float = 0.10) -> list[bool]:
    """Benjamini-Hochberg FDR control: which entries of `p_values` are
    declared significant at false-discovery rate `q`.

    Standard procedure: sort ascending, find the LARGEST rank k such
    that p_(k) <= (k/m)*q, then reject every hypothesis with p <= p_(k)
    -- not just the ones individually satisfying the per-rank threshold.
    A NaN p-value (insufficient data) is never rejected.

    Added for H10 (pipeline/hypotheses/h10_broad_feature_screen.py),
    which pre-registered BH correction rather than the plain ~1.96
    per-test threshold every earlier hypothesis module here used --
    the first module in this project to test enough features at once
    (7) that per-test-uncorrected significance would be misleading.
    """
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    threshold = 0.0
    for rank, idx in enumerate(order, start=1):
        p = p_values[idx]
        if not math.isnan(p) and p <= (rank / m) * q:
            threshold = p
    return [(not math.isnan(p)) and p <= threshold for p in p_values]


def welch_ttest(a: list[float], b: list[float]) -> TTestResult:
    """Welch's t-test (unequal-variance two-sample t-test) for whether two
    groups' means differ.

    Added for H15 (pipeline/hypotheses/h15_technical_fundamental_interactions.py)
    to compare a factor-combination group's mean return against a
    single-factor group's -- the direct test of whether combining two
    factors adds something a single factor alone doesn't. Welch's, not
    Student's, because the two groups here (e.g. "cheap AND oversold" vs
    "cheap alone") are never guaranteed equal variance or size.

    No p-value computed (no scipy dependency in this project) -- callers
    read `t` against the same ~1.96 asymptotic-normal threshold every
    other hypothesis module here already uses for its correlation
    t-statistics, for consistency rather than a false precision this
    project's tools don't support.

    Returns NaN for `t`/`diff` if either group has fewer than 2 elements
    (no variance to compute), matching this module's NaN-for-insufficient-
    data convention elsewhere (spearman, annualized_volatility).
    """
    n_a, n_b = len(a), len(b)
    if n_a < 2 or n_b < 2:
        return TTestResult(
            mean_a=statistics.mean(a) if a else float("nan"),
            mean_b=statistics.mean(b) if b else float("nan"),
            diff=float("nan"),
            t=float("nan"),
            n_a=n_a,
            n_b=n_b,
        )
    mean_a, mean_b = statistics.mean(a), statistics.mean(b)
    var_a, var_b = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(var_a / n_a + var_b / n_b)
    t = (mean_a - mean_b) / se if se else 0.0
    return TTestResult(mean_a=mean_a, mean_b=mean_b, diff=mean_a - mean_b, t=t, n_a=n_a, n_b=n_b)
