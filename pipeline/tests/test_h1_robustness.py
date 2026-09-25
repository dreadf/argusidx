from pipeline.hypotheses.h1_robustness import (
    bootstrap_rho,
    bucket_medians,
    cluster_bootstrap_rho,
    loso,
    median_diff_ci,
)


def _rows() -> list[dict]:
    rows = []
    for i in range(60):
        sector = "A" if i < 20 else "B" if i < 40 else "C"
        rows.append({"sym": f"S{i}", "sector": sector, "ff": i / 60, "vol": i / 60 + (i % 3) * 0.01})
    return rows


def test_loso_drops_exactly_one_sector_each():
    rows = _rows()
    out = loso(rows)
    assert [r["sector"] for r in out] == ["A", "B", "C"]
    for r in out:
        assert r["excl"].n == len(rows) - r["n_sector"]
        assert r["excl"].rho > 0.9


def test_bootstrap_is_seeded_and_brackets_a_strong_effect():
    rows = _rows()
    a = bootstrap_rho(rows, seed=1, n_boot=200)
    assert a == bootstrap_rho(rows, seed=1, n_boot=200)
    assert a[0] <= a[1]
    assert a[0] > 0.8


def test_cluster_bootstrap_resamples_whole_sectors():
    rows = _rows()
    lo, hi = cluster_bootstrap_rho(rows, seed=2, n_boot=200)
    assert lo <= hi and lo > 0.5


def test_median_diff_point_estimate():
    point, lo, hi = median_diff_ci([5.0, 6.0, 7.0], [1.0, 2.0, 3.0], seed=0, n_boot=200)
    assert point == 4.0
    assert lo <= point <= hi


def test_bucket_medians_counts_buckets():
    rows = _rows()
    meds = bucket_medians(rows, 3)
    assert len(meds) == 3 and meds[0] < meds[-1]
