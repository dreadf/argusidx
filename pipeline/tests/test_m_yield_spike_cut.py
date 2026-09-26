"""Tests for pipeline/hypotheses/m_yield_spike_cut.py (definitions in EXPERIMENT.md, 2026-09-26 batch 1)."""
from pipeline.hypotheses.m_yield_spike_cut import build_yield_spike_cut, is_yield_spike


def _qv(y_now: float | None, priors: tuple, year: int = 2024, div=None, div_next="skip"):
    qv = {f"total_yield[{year}]": y_now}
    for k, p in enumerate(priors, start=1):
        qv[f"total_yield[{year - k}]"] = p
    if div is not None:
        qv[f"total_dividend[{year}]"] = div
    if div_next != "skip":
        qv[f"total_dividend[{year + 1}]"] = div_next
    return qv


def test_exactly_one_and_a_half_times_the_mean_triggers_just_below_does_not():
    assert is_yield_spike(_qv(3.0, (2.0, 2.0, 2.0)), 2024)
    assert not is_yield_spike(_qv(2.99, (2.0, 2.0, 2.0)), 2024)


def test_needs_all_three_prior_years_and_a_current_value():
    assert not is_yield_spike(_qv(3.0, (2.0, None, 2.0)), 2024)
    assert not is_yield_spike(_qv(None, (2.0, 2.0, 2.0)), 2024)
    assert not is_yield_spike({"total_yield[2024]": 3.0}, 2024)


def test_zero_average_never_triggers():
    assert not is_yield_spike(_qv(0.0, (0.0, 0.0, 0.0)), 2024)
    assert not is_yield_spike(_qv(1.0, (0.0, 0.0, 0.0)), 2024)


def _u(*qvs):
    return [{"symbol": f"S{i}", "query_values": q} for i, q in enumerate(qvs)]


def test_cut_both_ways_missing_next_year_dividend():
    universe = _u(
        _qv(3.0, (2.0, 2.0, 2.0), div=10.0, div_next=9.0),  # cut
        _qv(3.0, (2.0, 2.0, 2.0), div=10.0, div_next=10.0),  # equal -> not a cut
        _qv(3.0, (2.0, 2.0, 2.0), div=10.0, div_next=None),  # missing
        _qv(3.0, (2.0, 2.0, 2.0), div=10.0),  # field absent -> missing
        _qv(3.0, (2.0, 2.0, 2.0), div=None, div_next=5.0),  # no dividend in Y -> left out
        _qv(2.0, (2.0, 2.0, 2.0), div=10.0, div_next=1.0),  # not triggered
    )
    out = build_yield_spike_cut(universe, [2024])[2024]
    assert out["triggered"] == 5
    assert out["cut_missing_counted_as_cut"] == {"n": 4, "count": 3, "rate": 0.75}
    assert out["cut_missing_left_out"] == {"n": 2, "count": 1, "rate": 0.5}


def test_year_2025_reports_triggers_but_no_outcome():
    universe = _u(_qv(3.0, (2.0, 2.0, 2.0), year=2025, div=10.0))
    out = build_yield_spike_cut(universe, [2025])[2025]
    assert out["triggered"] == 1
    assert out["cut_missing_counted_as_cut"] == {"n": 0, "count": 0, "rate": None}
    assert out["cut_missing_left_out"]["n"] == 0
