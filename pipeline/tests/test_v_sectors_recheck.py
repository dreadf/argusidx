from pipeline.hypotheses.v_sectors_recheck import sectors_price_table, verdicts


def test_price_table_uses_one_series_for_close_and_adjclose():
    closes = {
        "2025-04-30": {"pages": {"0": [{"symbol": "AAAA.JK", "close": 100}, {"symbol": "BBBB", "close": 0}]}},
        "2025-09-04": {"pages": {"0": [{"symbol": "AAAA.JK", "close": 110}]}},
    }
    table, counts = sectors_price_table(closes)
    assert counts == {"2025-04-30": 2, "2025-09-04": 1}
    assert list(table) == ["AAAA.JK"]  # a non-positive close is dropped
    assert table["AAAA.JK"]["close"] == table["AAAA.JK"]["adjclose"] == [100.0, 110.0]
    assert table["AAAA.JK"]["timestamps"][0] < table["AAAA.JK"]["timestamps"][1]


def test_decision_rule_needs_same_sign_and_the_bonferroni_p(monkeypatch):
    a = {"x": {"rho": 0.10, "p": 0.001}, "y": {"rho": 0.10, "p": 0.001}, "z": {"rho": 0.10, "p": 0.001}}
    b = {"x": {"rho": 0.10}, "y": {"rho": 0.10}, "z": {"rho": 0.10}}
    c = {"x": {"rho": 0.09, "p": 0.01}, "y": {"rho": -0.09, "p": 0.001}, "z": {"rho": 0.20, "p": 0.03}}
    import pipeline.hypotheses.v_sectors_recheck as v

    monkeypatch.setattr(v, "FEATURES", ("x", "y", "z"))
    out = v.verdicts(a, b, c)
    assert out["x"] == {"replicated": True, "price_source_inconsistent": False}
    assert out["y"]["replicated"] is False  # opposite sign
    assert out["z"] == {"replicated": False, "price_source_inconsistent": True}  # p above 0.0167, rho gap 0.10
