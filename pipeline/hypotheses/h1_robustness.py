"""
H1 robustness: three more stress tests of an EXISTING finding.

STATUS: run once; every result is reported regardless of outcome.

Same convention as h1_stress.py: attacking H1 cannot add a trial by
itself. A test only counts as a new trial if it produces a NEW POSITIVE
claim ("the effect is strongest in sector X" would be fishing). Every
interpretation below is fixed BEFORE running and is a boundary condition
on H1, never a new claim. No new data, no credits: free float
(Sectors, owned), the 1-year Yahoo dev cache (build-time only), market
cap (owned) and the `sector` field from the owned universe sweep.

Baseline being stressed (reproduces h1_free_float.py exactly):
    Spearman(free_float, 1y volatility), n=913, rho=+0.177, t=+5.42;
    within market-cap quartiles: smallest +0.215, small-mid +0.139,
    mid-large +0.086 (t=1.29, not significant), largest +0.170.

Pre-registered interpretations:

Test 1 -- Leave-one-sector-out (LOSO). Drop each of the 11 sectors in
    turn and recompute the pooled rho; also drop the "property / mining /
    financials" group together (Properties & Real Estate, Basic
    Materials, Energy, Financials), the story a reader would suspect.
    ROBUST TO SECTOR if every exclusion keeps rho > 0 with t > 2 and
    rho >= half the baseline (>= 0.0885). SECTOR-DRIVEN if any single
    exclusion pushes rho below half the baseline or t below 2. Also
    reported: each sector alone (descriptive; sectors of 37-149 stocks
    have low power, so a non-significant single sector is NOT evidence
    against the effect there).
Test 2 -- Bootstrap CI. 2,000 seeded stock-level resamples of the
    Spearman rho for the smallest-cap bucket (and the other three buckets
    and the pooled sample for context), plus a sector-cluster bootstrap
    (resample whole sectors) for the pooled and smallest-cap samples,
    because stocks in one sector are not independent. POSITIVE if the 95%
    percentile interval excludes zero.
Test 3 -- Bucketing and threshold sensitivity. Terciles, quartiles,
    quintiles (the baseline) and deciles of free float; and a thin-float
    cut at 5/10/15/20/25/30%. CONSISTENT if the high-float group has the
    higher median volatility in every scheme. For thresholds a 95%
    bootstrap interval for the difference in medians is reported.
    Baseline quintile medians are not monotone (Q1 53.7%, Q2 52.5%, Q3
    68.6%): a step, not a smooth slope; that is reported, not smoothed.

Run:
    .venv/bin/python -m pipeline.hypotheses.h1_robustness
"""
from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict

from pipeline.hypotheses.h1_free_float import (
    REPO_ROOT,
    build_1y_rows,
    load_free_float,
    load_market_cap,
)
from pipeline.stats import quintiles, spearman

UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"
SEED = 0
N_BOOT = 2000
GROUP_EXCLUDE = ["Properties & Real Estate", "Basic Materials", "Energy", "Financials"]


def load_sectors() -> dict[str, str]:
    universe = json.loads(UNIVERSE_PATH.read_text())
    return {r["symbol"]: (r.get("query_values") or {}).get("sector") for r in universe}


def rho_of(rows: list[dict]) -> float:
    return spearman([r["ff"] for r in rows], [r["vol"] for r in rows]).rho


def loso(rows: list[dict]) -> list[dict]:
    """Pooled rho after excluding each sector, plus each sector alone."""
    by_sector: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_sector[r["sector"]].append(r)
    out = []
    for sector in sorted(by_sector):
        kept = [r for r in rows if r["sector"] != sector]
        c_excl = spearman([r["ff"] for r in kept], [r["vol"] for r in kept])
        only = by_sector[sector]
        c_only = spearman([r["ff"] for r in only], [r["vol"] for r in only])
        out.append({"sector": sector, "n_sector": len(only), "excl": c_excl, "only": c_only})
    return out


def bootstrap_rho(rows: list[dict], seed: int, n_boot: int = N_BOOT) -> tuple[float, float]:
    """95% percentile interval for Spearman rho, resampling stocks."""
    rnd = random.Random(seed)
    n = len(rows)
    draws = []
    for _ in range(n_boot):
        sample = [rows[rnd.randrange(n)] for _ in range(n)]
        draws.append(rho_of(sample))
    draws.sort()
    return draws[int(0.025 * n_boot)], draws[int(0.975 * n_boot) - 1]


def cluster_bootstrap_rho(rows: list[dict], seed: int, n_boot: int = N_BOOT) -> tuple[float, float]:
    """95% percentile interval for rho, resampling whole sectors."""
    rnd = random.Random(seed)
    by_sector: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_sector[r["sector"]].append(r)
    names = sorted(by_sector)
    draws = []
    for _ in range(n_boot):
        sample = []
        for _ in names:
            sample.extend(by_sector[names[rnd.randrange(len(names))]])
        draws.append(rho_of(sample))
    draws.sort()
    return draws[int(0.025 * n_boot)], draws[int(0.975 * n_boot) - 1]


def median_diff_ci(high: list[float], low: list[float], seed: int, n_boot: int = N_BOOT) -> tuple[float, float, float]:
    """Difference of medians (high minus low) and its 95% bootstrap interval."""
    rnd = random.Random(seed)
    point = statistics.median(high) - statistics.median(low)
    diffs = []
    for _ in range(n_boot):
        h = [high[rnd.randrange(len(high))] for _ in high]
        lo = [low[rnd.randrange(len(low))] for _ in low]
        diffs.append(statistics.median(h) - statistics.median(lo))
    diffs.sort()
    return point, diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]


def bucket_medians(rows: list[dict], n_buckets: int) -> list[float]:
    return [statistics.median(r["vol"] for r in b) for b in quintiles(rows, "ff", n_buckets)]


def test1(rows: list[dict], baseline: float) -> None:
    print("Test 1 -- leave-one-sector-out (pooled rho, free float vs 1y volatility)\n")
    print(f"  baseline: n={len(rows)}  rho={baseline:+.3f}\n")
    print(f"  {'sector excluded':<28}{'n_left':>7}{'rho':>8}{'t':>7}   | sector alone: n / rho / t")
    results = loso(rows)
    worst = min(results, key=lambda r: r["excl"].rho)
    for r in results:
        print(f"  {r['sector']:<28}{r['excl'].n:>7}{r['excl'].rho:>+8.3f}{r['excl'].t:>+7.2f}   |"
              f" {r['n_sector']:>4} / {r['only'].rho:>+.3f} / {r['only'].t:>+5.2f}")
    kept = [r for r in rows if r["sector"] not in GROUP_EXCLUDE]
    c = spearman([r["ff"] for r in kept], [r["vol"] for r in kept])
    print(f"\n  property + mining + financials all excluded ({'; '.join(GROUP_EXCLUDE)}):")
    print(f"    n={c.n}  rho={c.rho:+.3f}  t={c.t:+.2f}")
    floor = baseline / 2
    robust = all(r["excl"].rho >= floor and r["excl"].t > 2 for r in results)
    print(f"\n  Lowest single-sector-excluded rho: {worst['excl'].rho:+.3f} (dropping {worst['sector']})."
          f" Floor for 'robust' = {floor:+.4f}.")
    print(f"  Pre-registered verdict: {'ROBUST TO SECTOR' if robust else 'SECTOR-DRIVEN (see rows above)'}")
    neg = [r["sector"] for r in results if r["only"].rho < 0]
    print(f"  Sectors where the effect alone is negative: {', '.join(neg) if neg else 'none'}")


def test2(rows: list[dict], mcap: dict[str, float]) -> None:
    print("\nTest 2 -- bootstrap intervals (95% percentile, 2,000 seeded resamples)\n")
    sized = [r | {"mc": mcap[r["sym"]]} for r in rows if r["sym"] in mcap]
    labels = ["smallest", "small-mid", "mid-large", "largest"]
    print(f"  {'sample':<12}{'n':>5}{'rho':>8}   stock-level 95% CI       sector-cluster 95% CI")
    for label, bucket in [("pooled", sized)] + list(zip(labels, quintiles(sized, "mc", 4))):
        lo, hi = bootstrap_rho(bucket, SEED)
        clo, chi = cluster_bootstrap_rho(bucket, SEED)
        print(f"  {label:<12}{len(bucket):>5}{rho_of(bucket):>+8.3f}   [{lo:+.3f}, {hi:+.3f}]"
              f"        [{clo:+.3f}, {chi:+.3f}]")


def test3(rows: list[dict]) -> None:
    print("\nTest 3 -- bucketing and threshold sensitivity\n")
    print("  Median 1y volatility by free-float bucket (thinnest first):")
    consistent = True
    for k, name in [(3, "terciles"), (4, "quartiles"), (5, "quintiles (baseline)"), (10, "deciles")]:
        meds = bucket_medians(rows, k)
        ups = sum(1 for a, b in zip(meds, meds[1:]) if b > a)
        consistent &= meds[-1] > meds[0]
        print(f"  {name:<22} " + " ".join(f"{m:.0%}" for m in meds) + f"   (rises in {ups} of {k - 1} steps)")
    print("\n  Thin-float cut (free float below threshold vs the rest):")
    print(f"  {'threshold':<10}{'n_thin':>7}{'thin vol':>10}{'rest vol':>10}   rest minus thin, 95% CI")
    for thr in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        thin = [r["vol"] for r in rows if r["ff"] < thr]
        rest = [r["vol"] for r in rows if r["ff"] >= thr]
        if len(thin) < 10:
            print(f"  <{thr:.0%}     n_thin={len(thin)}: too few, skipped")
            continue
        point, lo, hi = median_diff_ci(rest, thin, SEED)
        consistent &= point > 0
        print(f"  <{thr:<8.0%}{len(thin):>7}{statistics.median(thin):>10.1%}{statistics.median(rest):>10.1%}"
              f"   {point:+.1%}  [{lo:+.1%}, {hi:+.1%}]")
    print(f"\n  Pre-registered verdict: {'CONSISTENT (high float has higher volatility in every scheme)' if consistent else 'NOT CONSISTENT'}")


def main() -> None:
    ff = load_free_float()
    rows = build_1y_rows(ff)
    sectors = load_sectors()
    for r in rows:
        r["sector"] = sectors.get(r["sym"])
    missing = [r["sym"] for r in rows if r["sector"] is None]
    if missing:
        raise SystemExit(f"{len(missing)} stocks have no sector in the universe file: {missing[:5]}")
    baseline = rho_of(rows)
    test1(rows, baseline)
    test2(rows, load_market_cap())
    test3(rows)
    print("\nTrial count unchanged: stress tests of H1, boundary conditions only.")


if __name__ == "__main__":
    main()
