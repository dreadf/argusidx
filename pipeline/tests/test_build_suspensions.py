"""
Tests for pipeline/appdata/build_suspensions.py.
"""
from pipeline.appdata.build_suspensions import (
    REASON_RULES,
    build_base_rates,
    build_suspensions_by_symbol,
    categorize_reason,
)


def test_groups_events_by_symbol():
    records = [
        {"symbol": "A.JK", "suspension_date": "2026-01-01", "reason": "r1", "pdf_url": "u1"},
        {"symbol": "B.JK", "suspension_date": "2026-02-01", "reason": "r2", "pdf_url": "u2"},
        {"symbol": "A.JK", "suspension_date": "2026-03-01", "reason": "r3", "pdf_url": "u3"},
    ]
    result = build_suspensions_by_symbol(records)
    assert set(result.keys()) == {"A.JK", "B.JK"}
    assert len(result["A.JK"]) == 2
    assert len(result["B.JK"]) == 1


def test_most_recent_first_per_company():
    records = [
        {"symbol": "A.JK", "suspension_date": "2026-01-01", "reason": "old", "pdf_url": "u1"},
        {"symbol": "A.JK", "suspension_date": "2026-06-01", "reason": "new", "pdf_url": "u2"},
    ]
    result = build_suspensions_by_symbol(records)
    assert [r["reason"] for r in result["A.JK"]] == ["new", "old"]


def test_events_carry_category_fields():
    records = [
        {"symbol": "A.JK", "suspension_date": "2026-01-01", "reason": "Belum menyampaikan laporan keuangan auditan tahunan", "pdf_url": "u1"},
    ]
    result = build_suspensions_by_symbol(records)
    event = result["A.JK"][0]
    assert event["category"] == "late_financial_reporting"
    assert event["group"] == "governance_or_compliance"
    assert "category_label_id" in event
    assert "group_label_id" in event


def test_categorize_unusual_price_movement():
    result = categorize_reason("Terjadinya peningkatan harga kumulatif yang signifikan pada saham UDNG.JK")
    assert result["category"] == "unusual_price_movement"
    assert result["group"] == "unusual_price_movement"


def test_categorize_price_move_with_cooling_down_stays_price_movement():
    # A reason naming both a price surge and cooling-down is attributed to
    # the price movement (the actual trigger), not the cooling-down status -
    # order in REASON_RULES matters and this locks it in.
    result = categorize_reason(
        "Terjadinya peningkatan harga kumulatif yang signifikan pada saham MGLV.JK, "
        "dalam rangka cooling down sebagai bentuk perlindungan bagi investor"
    )
    assert result["category"] == "unusual_price_movement"


def test_categorize_unmatched_reason_falls_back_to_other():
    result = categorize_reason("Some entirely novel reason never seen before")
    assert result["category"] == "other"
    assert result["group"] == "other"


def test_all_real_reason_patterns_are_categorized_not_other():
    # Regression: every one of the 16 real normalized patterns found in the
    # owned 2026-09-13 pull must hit a real rule, never the "other" fallback.
    real_patterns = [
        "Belum memenuhi ketentuan V.1.1. dan/atau V.1.2. peraturan bursa nomor I-A",
        "Belum menyampaikan laporan keuangan auditan tahunan",
        "Bursa menilai bahwa terdapat keraguan atas kelangsungan usaha perseroan",
        "Dalam rangka cooling down sebagai bentuk perlindungan bagi investor",
        "Dalam rangka pengalihan saham hasil pelaksanaan pembelian kembali saham (buyback) dalam rangka delisting perseroan",
        "Efek Perseroan telah berada dalam papan pemantauan khusus selama lebih dari 1 (satu) tahun berturut-turut",
        "Keterlambatan pembayaran biaya pencatatan tahunan 2025",
        "Perseroan telah menunda pembayaran amortisasi pokok ke-12 dan bunga ke-24 dari Obligasi I",
        "Sehubungan dengan adanya ketidakpastian atas kelangsungan usaha",
        "Suspend more than 6 month",
        "Terdapat rencana perubahan status Perseroan dari Perusahaan Terbuka menjadi Perusahaan Tertutup (Go Private)",
        "Terjadinya peningkatan harga kumulatif yang signifikan pada saham TICKER",
        "Terjadinya penurunan harga kumulatif yang signifikan pada saham TICKER",
    ]
    for reason in real_patterns:
        result = categorize_reason(reason)
        assert result["category"] != "other", f"unexpectedly uncategorized: {reason}"


def test_reason_rules_have_labels_for_every_category_and_group():
    from pipeline.appdata.build_suspensions import CATEGORY_LABELS_ID, GROUP_LABELS_ID

    for _, category, group in REASON_RULES:
        assert category in CATEGORY_LABELS_ID
        assert group in GROUP_LABELS_ID


def test_base_rates_only_include_suspended_companies():
    by_symbol = {"A.JK": [{"date": "2026-01-01"}]}
    universe = ["A.JK", "B.JK", "C.JK"]
    result = build_base_rates(by_symbol, universe)
    assert set(result.keys()) == {"A.JK"}


def test_base_rates_percentile_against_full_universe():
    # Universe of 4: counts are A=3, B=1, C=0, D=0.
    # Percentile is against the FULL universe (denominator 4, self included) -
    # standard percentile-rank behavior, so even the market's own maximum
    # doesn't show 100% when it's one of the 4 being ranked.
    # A.JK (3) beats the other 3 (0, 0, 1) -> 3/4 = 75%.
    # B.JK (1) beats only the 2 zero-count companies -> 2/4 = 50%.
    by_symbol = {
        "A.JK": [{"date": "2026-01-01"}, {"date": "2026-02-01"}, {"date": "2026-03-01"}],
        "B.JK": [{"date": "2026-01-01"}],
    }
    universe = ["A.JK", "B.JK", "C.JK", "D.JK"]
    result = build_base_rates(by_symbol, universe)
    assert result["A.JK"]["count"] == 3
    assert result["A.JK"]["more_than_pct"] == 75.0
    assert result["B.JK"]["count"] == 1
    assert result["B.JK"]["more_than_pct"] == 50.0
    assert result["A.JK"]["universe_count"] == 4
