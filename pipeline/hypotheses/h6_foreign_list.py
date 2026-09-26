"""
H6 -- "Asing borong -> harga naik": do the stocks on a day's top-30 foreign
net-buy list do better over the next 5 trading days than the top-30 net-sell
list?

Pre-registered in EXPERIMENT.md ("Pre-registration, 2026-09-26 -- H6")
before any list data was pulled. One falsifiable test, counted as one trial.

- Lists: Sectors REST `/v2/foreign-flow/?date=D`, page 1 in both orders
  (buy = default descending net, sell = `order_by=net_foreign_inflow`).
  No MCP tool exists for this endpoint. 2 credits per date.
- Dates: ^JKSE trading days from 2025-01-31, every 6th from a seeded offset
  (seed 20260926), so 5-day outcome windows never overlap.
- Outcome: adjclose D+1 -> D+6 minus the same-window ^JKSE return
  (research prices only, never shipped).
- Statistic: per date, mean excess return of buy list minus sell list
  (winsorised at the pooled 1st/99th percentile); a one-sample t-test
  across dates, per phase, with the exact Student-t p-value (n is small).
- Decision: CONFIRMED only if holdout spread > 0 with p < 0.05 (two-sided)
  and explore has the same sign.

Run (fetch is billed: 126 credits, resumable, never re-bills a saved call):
    .venv/bin/python -m pipeline.hypotheses.h6_foreign_list fetch
Run (analysis, once, after the fetch):
    .venv/bin/python -m pipeline.hypotheses.h6_foreign_list analyze
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
BENCHMARKS_PATH = REPO_ROOT / "data" / "dev_cache" / "benchmarks_5y.json"
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
LISTS_PATH = REPO_ROOT / "data" / "raw" / "foreign_flow_lists_2026-09-26.json"

GRID_START = date(2025, 1, 31)
GRID_STEP = 6
GRID_SEED = 20260926
HORIZON = 5  # outcome: close(D+1) -> close(D+6)
EXPLORE_END = date(2025, 9, 30)
LIST_SIZE = 30
ALPHA = 0.05
MAX_CALLS = 126  # 63 dates x 2 lists, the approved spend


# ---------------------------------------------------------------- dates
def trading_grid(days: list[date]) -> list[date]:
    """Every GRID_STEP-th trading day from a seeded offset, with room for the outcome."""
    eligible = [d for d in days if d >= GRID_START]
    offset = random.Random(GRID_SEED).randrange(GRID_STEP)
    picks = eligible[offset::GRID_STEP]
    index = {d: i for i, d in enumerate(days)}
    return [d for d in picks if index[d] + HORIZON + 1 < len(days)]


def split_dates(dates: list[date]) -> tuple[list[date], list[date]]:
    return [d for d in dates if d <= EXPLORE_END], [d for d in dates if d > EXPLORE_END]


def jkse_days() -> list[date]:
    b = json.loads(BENCHMARKS_PATH.read_text())["^JKSE"]
    return [datetime.fromtimestamp(t, timezone.utc).date() for t in b["timestamps"]]


# ---------------------------------------------------------------- fetch
def _get_with_rate_limit_wait(get, params: dict, pause: float) -> dict:
    """429s are free (docs/PLAN.md 8.4), so waiting and retrying never double-bills."""
    for attempt in range(6):
        try:
            body = get("/foreign-flow/", params)
            time.sleep(pause)
            return body
        except Exception as e:  # SectorsAPIError text carries the HTTP code
            if "429" not in str(e) or attempt == 5:
                raise
            time.sleep(max(pause, 1.0) * 15 * (attempt + 1))
    raise AssertionError("unreachable")


def fetch_lists(
    dates: list[date],
    path: Path,
    get: Callable[[str, dict], dict],
    max_calls: int = MAX_CALLS,
    pause: float = 0.0,
) -> int:
    """Pull buy and sell page 1 per date. Saves after every call, skips saved
    ones (no re-billing), and refuses to exceed `max_calls` new calls."""
    store: dict = json.loads(path.read_text()) if path.exists() else {}
    todo = [
        (d, side)
        for d in dates
        for side in ("buy", "sell")
        if side not in store.get(d.isoformat(), {})
    ]
    if len(todo) > max_calls:
        raise RuntimeError(f"{len(todo)} calls needed, cap is {max_calls}")
    for d, side in todo:
        params = {"date": d.isoformat(), "limit": str(LIST_SIZE)}
        if side == "sell":
            params["order_by"] = "net_foreign_inflow"
        body = _get_with_rate_limit_wait(get, params, pause)
        store.setdefault(d.isoformat(), {})[side] = body.get("results", [])
        path.write_text(json.dumps(store))
    return len(todo)


# ---------------------------------------------------------------- stats
def _t_cdf_upper_two_sided(t: float, df: int) -> float:
    """Two-sided Student-t p-value by Simpson integration of the pdf."""
    t = abs(t)
    if math.isnan(t):
        return float("nan")
    log_c = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)

    def pdf(x: float) -> float:
        return math.exp(log_c - (df + 1) / 2 * math.log1p(x * x / df))

    n = 4000
    h = t / n
    total = pdf(0) + pdf(t) + sum((4 if i % 2 else 2) * pdf(i * h) for i in range(1, n))
    central = total * h / 3  # integral 0..t
    return max(0.0, min(1.0, 1 - 2 * central))


def one_sample_t(values: list[float]) -> dict:
    n = len(values)
    if n < 3:
        return {"n": n, "mean": float("nan"), "t": float("nan"), "p": float("nan")}
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    if sd == 0:
        return {"n": n, "mean": mean, "t": float("nan"), "p": float("nan")}
    t = mean / (sd / math.sqrt(n))
    return {"n": n, "mean": mean, "t": t, "p": _t_cdf_upper_two_sided(t, n - 1)}


def winsorize_bounds(values: list[float], lo: float = 0.01, hi: float = 0.99) -> tuple[float, float]:
    s = sorted(values)
    return s[int(lo * (len(s) - 1))], s[int(math.ceil(hi * (len(s) - 1)))]


# ------------------------------------------------------------- outcomes
def _close_by_day(entry: dict) -> dict[date, float]:
    field = "adjclose" if entry.get("adjclose") else "close"
    out = {}
    for ts, px in zip(entry["timestamps"], entry[field]):
        if px and px > 0:
            out[datetime.fromtimestamp(ts, timezone.utc).date()] = px
    return out


def window_return(px_by_day: dict[date, float], a: date, b: date) -> float | None:
    if a in px_by_day and b in px_by_day:
        return px_by_day[b] / px_by_day[a] - 1
    return None


def list_returns(
    symbols: list[str],
    prices: dict[str, dict[date, float]],
    day_a: date,
    day_b: date,
) -> tuple[list[tuple[str, float]], int]:
    """(symbol, return) for symbols with prices at both ends, and the missing count."""
    got, missing = [], 0
    for s in symbols:
        r = window_return(prices.get(s, {}), day_a, day_b) if s in prices else None
        if r is None:
            missing += 1
        else:
            got.append((s, r))
    return got, missing


def build_date_rows(
    d: date,
    lists: dict,
    days: list[date],
    prices: dict[str, dict[date, float]],
    index_px: dict[date, float],
) -> dict | None:
    """Per-date stock rows for both lists: excess return, prior returns, list flag."""
    i = days.index(d)
    d1, d6 = days[i + 1], days[i + 1 + HORIZON]
    bench = window_return(index_px, d1, d6)
    if bench is None:
        return None
    prev1, prev20 = days[i - 1] if i >= 1 else None, days[i - 20] if i >= 20 else None
    rows, missing = [], 0
    for side, flag in (("buy", 1), ("sell", 0)):
        for item in lists.get(d.isoformat(), {}).get(side, []):
            s = item["symbol"]
            px = prices.get(s)
            r = window_return(px, d1, d6) if px else None
            if r is None:
                missing += 1
                continue
            rows.append(
                {
                    "symbol": s,
                    "buy": flag,
                    "excess": r - bench,
                    "same_day": window_return(px, prev1, d) if prev1 else None,
                    "past20": window_return(px, prev20, d) if prev20 else None,
                    "beat": r > bench,
                }
            )
    return {"date": d, "rows": rows, "missing": missing}


def date_spread(rows: list[dict], lo: float, hi: float) -> float | None:
    """Mean winsorised excess of the buy list minus the sell list, or None."""
    def clip(x: float) -> float:
        return min(max(x, lo), hi)

    buy = [clip(r["excess"]) for r in rows if r["buy"]]
    sell = [clip(r["excess"]) for r in rows if not r["buy"]]
    if not buy or not sell:
        return None
    return statistics.fmean(buy) - statistics.fmean(sell)


def analyze_phase(date_rows: list[dict], lo: float, hi: float) -> dict:
    spreads = [s for s in (date_spread(d["rows"], lo, hi) for d in date_rows) if s is not None]
    result = one_sample_t(spreads)
    all_rows = [r for d in date_rows for r in d["rows"]]
    buy = [r for r in all_rows if r["buy"]]
    sell = [r for r in all_rows if not r["buy"]]
    med = lambda rs: statistics.median(r["excess"] for r in rs) if rs else float("nan")
    share = lambda rs: sum(r["beat"] for r in rs) / len(rs) if rs else float("nan")
    mean_of = lambda rs, k: statistics.fmean(v for v in (r[k] for r in rs) if v is not None) if rs else float("nan")
    result.update(
        {
            "n_dates": len(spreads),
            "n_dates_with_empty_list": len(date_rows) - len(spreads),
            "missing_prices": sum(d["missing"] for d in date_rows),
            "median_excess_buy": med(buy),
            "median_excess_sell": med(sell),
            "share_beating_index_buy": share(buy),
            "share_beating_index_sell": share(sell),
            "descriptive_same_day_buy": mean_of(buy, "same_day"),
            "descriptive_same_day_sell": mean_of(sell, "same_day"),
            "descriptive_past20_buy": mean_of(buy, "past20"),
            "descriptive_past20_sell": mean_of(sell, "past20"),
        }
    )
    return result


def verdict(explore: dict, holdout: dict) -> str:
    if math.isnan(holdout["p"]) or math.isnan(explore["mean"]):
        return "NOT confirmed (insufficient data)"
    same_sign = (explore["mean"] > 0) == (holdout["mean"] > 0)
    if holdout["p"] < ALPHA and holdout["mean"] > 0 and same_sign:
        return "CONFIRMED"
    if holdout["p"] < ALPHA and holdout["mean"] < 0:
        return "OPPOSITE of the belief (significant negative holdout spread)"
    return "NOT confirmed"



# ---------------------------------------------------------- regression
def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve a x = b by Gauss-Jordan with partial pivoting (small systems)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[piv][c]) < 1e-12:
            raise ValueError("singular design matrix")
        m[c], m[piv] = m[piv], m[c]
        m[c] = [v / m[c][c] for v in m[c]]
        for r in range(n):
            if r != c:
                f = m[r][c]
                m[r] = [rv - f * cv for rv, cv in zip(m[r], m[c])]
    return [m[i][n] for i in range(n)]


def fe_regression(groups: list[list[tuple[float, list[float]]]]) -> dict:
    """OLS of y on x with group (date) fixed effects and errors clustered by group.

    groups: per date, a list of (y, [x1, x2, ...]). Returns the coefficient,
    cluster-robust t and exact-t p for the FIRST regressor (list membership).
    """
    demeaned = []
    for g in groups:
        if len(g) < 2:
            continue
        k = len(g[0][1])
        my = statistics.fmean(y for y, _ in g)
        mx = [statistics.fmean(x[j] for _, x in g) for j in range(k)]
        demeaned.append([(y - my, [x[j] - mx[j] for j in range(k)]) for y, x in g])
    if len(demeaned) < 3:
        return {"coef": float("nan"), "t": float("nan"), "p": float("nan"), "clusters": len(demeaned)}
    k = len(demeaned[0][0][1])
    xtx = [[0.0] * k for _ in range(k)]
    xty = [0.0] * k
    for g in demeaned:
        for y, x in g:
            for i in range(k):
                xty[i] += x[i] * y
                for j in range(k):
                    xtx[i][j] += x[i] * x[j]
    beta = _solve(xtx, xty)
    meat = [[0.0] * k for _ in range(k)]
    for g in demeaned:
        score = [0.0] * k
        for y, x in g:
            resid = y - sum(b * xi for b, xi in zip(beta, x))
            for i in range(k):
                score[i] += x[i] * resid
        for i in range(k):
            for j in range(k):
                meat[i][j] += score[i] * score[j]
    # V = xtx^-1 meat xtx^-1 ; only [0][0] is needed
    inv_cols = [_solve(xtx, [1.0 if r == c else 0.0 for r in range(k)]) for c in range(k)]
    inv = [[inv_cols[c][r] for c in range(k)] for r in range(k)]
    var00 = sum(inv[0][i] * meat[i][j] * inv[j][0] for i in range(k) for j in range(k))
    g = len(demeaned)
    var00 *= g / (g - 1)  # small-sample cluster correction
    se = math.sqrt(var00) if var00 > 0 else float("nan")
    t = beta[0] / se if se and not math.isnan(se) else float("nan")
    return {"coef": beta[0], "t": t, "p": _t_cdf_upper_two_sided(t, g - 1), "clusters": g}


# ------------------------------------------------------------------ main
def _load_prices() -> tuple[dict[str, dict[date, float]], dict[date, float]]:
    raw = json.loads(PRICES_5Y_PATH.read_text())
    prices = {s: _close_by_day(e) for s, e in raw.items() if e.get("timestamps")}
    index_px = _close_by_day(json.loads(BENCHMARKS_PATH.read_text())["^JKSE"])
    return prices, index_px


def _shares_by_year() -> dict[str, dict[int, float]]:
    out = {}
    for row in json.loads(UNIVERSE_PATH.read_text()):
        qv = row["query_values"]
        out[row["symbol"]] = {
            y: qv[f"outstanding_shares[{y}]"] for y in range(2021, 2026) if qv.get(f"outstanding_shares[{y}]")
        }
    return out


def main(argv: list[str]) -> None:
    days = jkse_days()
    dates = trading_grid(days)
    explore, holdout = split_dates(dates)
    print(f"grid: {len(dates)} dates ({len(explore)} explore, {len(holdout)} holdout)")
    if argv[:1] == ["fetch"]:
        from pipeline import sectors_client

        n = fetch_lists(dates, LISTS_PATH, sectors_client.get, pause=2.0)
        print(f"billed calls made this run: {n}")
        return
    if argv[:1] != ["analyze"]:
        raise SystemExit("usage: h6_foreign_list.py fetch|analyze")
    lists = json.loads(LISTS_PATH.read_text())
    prices, index_px = _load_prices()
    shares = _shares_by_year()
    per_date = [build_date_rows(d, lists, days, prices, index_px) for d in dates]
    per_date = [x for x in per_date if x]
    for d in per_date:  # size = price on D x prior-year outstanding shares (no snapshot field)
        for r in d["rows"]:
            sh = shares.get(r["symbol"], {}).get(d["date"].year - 1)
            px = prices.get(r["symbol"], {}).get(d["date"])
            r["size"] = px * sh if sh and px else None
    all_excess = [r["excess"] for d in per_date for r in d["rows"]]
    lo, hi = winsorize_bounds(all_excess)
    phases = {
        "explore": [d for d in per_date if d["date"] <= EXPLORE_END],
        "holdout": [d for d in per_date if d["date"] > EXPLORE_END],
    }
    results = {}
    for name, rows in phases.items():
        results[name] = analyze_phase(rows, lo, hi)
        groups = [
            [
                (min(max(r["excess"], lo), hi), [float(r["buy"]), r["past20"], math.log(r["size"])])
                for r in d["rows"]
                if r["past20"] is not None and r["size"]
            ]
            for d in rows
        ]
        results[name]["regression_buy_coef"] = fe_regression(groups)
        for half in ("large", "small"):
            spreads = []
            for d in rows:
                sizes = sorted(r["size"] for r in d["rows"] if r["size"])
                if not sizes:
                    continue
                cut = statistics.median(sizes)
                sub = [r for r in d["rows"] if r["size"] and (r["size"] >= cut) == (half == "large")]
                sp = date_spread(sub, lo, hi)
                if sp is not None:
                    spreads.append(sp)
            results[name][f"spread_{half}_half"] = one_sample_t(spreads)
    ex, ho = results["explore"], results["holdout"]
    print("explore:", ex)
    print("holdout:", ho)
    print("verdict:", verdict(ex, ho))


if __name__ == "__main__":
    main(sys.argv[1:])
