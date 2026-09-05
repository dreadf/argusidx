"""
Reusable statistics for hypothesis testing.

Pure functions, no I/O, no credentials. Every hypothesis module builds on
these rather than reimplementing them, so a bug fixed here is fixed
everywhere (see RULES.md process rule 3: fix the class, not the instance).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


def log_returns(closes: list[float]) -> list[float]:
    """Daily log returns from a series of closing prices."""
    return [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
        if closes[i - 1] > 0 and closes[i] > 0
    ]


def annualized_volatility(closes: list[float], trading_days: int = 252) -> float:
    """Standard deviation of daily log returns, annualized."""
    rets = log_returns(closes)
    if len(rets) < 2:
        return float("nan")
    return statistics.pstdev(rets) * math.sqrt(trading_days)


def max_drawdown(closes: list[float]) -> float:
    """Worst peak-to-trough decline, as a negative fraction (e.g. -0.487)."""
    if not closes:
        return float("nan")
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
    """Share of days the price did not move at all (stale-price diagnostic)."""
    rets = log_returns(closes)
    if not rets:
        return float("nan")
    return sum(1 for r in rets if abs(r) < 1e-9) / len(rets)


@dataclass
class CorrResult:
    rho: float
    t: float
    n: int


def spearman(a: list[float], b: list[float]) -> CorrResult:
    """Spearman rank correlation plus its t-statistic.

    Rank correlation is used throughout rather than Pearson correlation
    because small-cap price series are dominated by extreme outliers that
    distort ordinary correlation (see EXPERIMENT.md, H1 methodology).
    """
    n = len(a)
    assert n == len(b), "spearman: inputs must be the same length"
    ra = sorted(range(n), key=lambda k: a[k])
    rb = sorted(range(n), key=lambda k: b[k])
    x = [0] * n
    y = [0] * n
    for i, v in enumerate(ra):
        x[v] = i
    for i, v in enumerate(rb):
        y[v] = i
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = math.sqrt(
        sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)
    )
    rho = num / den if den else 0.0
    t = rho * math.sqrt((n - 2) / (1 - rho**2)) if abs(rho) < 1 else float("inf")
    return CorrResult(rho=rho, t=t, n=n)


def quintiles(rows: list[dict], sort_key: str, n_buckets: int = 5) -> list[list[dict]]:
    """Sort rows by sort_key and cut into n_buckets equal-ish groups."""
    ordered = sorted(rows, key=lambda r: r[sort_key])
    n = len(ordered)
    size = n // n_buckets
    buckets = []
    for i in range(n_buckets):
        start = i * size
        end = (i + 1) * size if i < n_buckets - 1 else n
        buckets.append(ordered[start:end])
    return buckets


def median_of(rows: list[dict], field: str) -> float:
    return statistics.median(r[field] for r in rows)
