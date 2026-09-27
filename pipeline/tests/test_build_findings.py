"""
Tests for pipeline/appdata/build_findings.py.
"""
import pytest

from pipeline.appdata.build_findings import attach_evidence, attach_translations, parse_scoreboard

SAMPLE = """
### 5.3 The honesty scoreboard: a verdict list, not a report

Belief in plain words → a large check/x → a three-word verdict.

| What people believe | | Verdict |
|---|---|---|
| Cheap stocks (low P/E) do better | **✓** | Yes, modestly (H5, H10) |
| Oversold (RSI < 30) means a bounce | **✗** | No (H14) |
| Small companies earn more | ~ | Inconclusive |

Scannable in seconds, no numeracy required; each row expands on tap.
"""


def test_parses_all_rows_with_correct_verdicts():
    result = parse_scoreboard(SAMPLE)
    assert len(result) == 3
    assert result[0] == {
        "belief": "Cheap stocks (low P/E) do better",
        "verdict": "yes",
        "label": "Yes, modestly (H5, H10)",
    }
    assert result[1]["verdict"] == "no"
    assert result[2]["verdict"] == "mixed_or_inconclusive"


def test_strips_bold_markdown_from_cells():
    result = parse_scoreboard(SAMPLE)
    assert "**" not in result[0]["belief"]
    assert "**" not in result[0]["label"]


def test_missing_table_header_raises():
    with pytest.raises(ValueError):
        parse_scoreboard("# No table here\n")


def test_unrecognized_verdict_symbol_raises():
    bad = SAMPLE.replace("**✓**", "**?**", 1)
    with pytest.raises(ValueError):
        parse_scoreboard(bad)


def test_attach_translations_adds_bahasa_fields():
    rows = [{"belief": "Thin float means wild swings", "verdict": "no", "label": "Backwards (H1)"}]
    result = attach_translations(rows)
    assert result[0]["belief_id"]
    assert result[0]["label_id"]
    assert "(H1)" not in result[0]["label_id"]


def test_attach_translations_fails_loudly_on_untranslated_row():
    """A belief added to docs/FINDINGS.md's table with no matching entry
    in findings_translations.py must fail the build, not ship
    English/research-shorthand copy silently (2026-09-13 user feedback)."""
    rows = [{"belief": "A brand new untranslated belief", "verdict": "no", "label": "No (H99)"}]
    with pytest.raises(ValueError, match="A brand new untranslated belief"):
        attach_translations(rows)


def test_attach_evidence_adds_evidence_field():
    rows = [{"belief": "Thin float means wild swings", "verdict": "no", "label": "Backwards (H1)"}]
    result = attach_evidence(rows)
    assert result[0]["evidence"]["hypothesis_id"] == "H1"
    assert "n=913" in result[0]["evidence"]["n"]


def test_attach_evidence_fails_loudly_on_missing_row():
    """A belief added to docs/FINDINGS.md's table with no matching entry
    in findings_evidence.py must fail the build, not ship a scoreboard
    row with no evidence behind it (2026-09-19 usability audit)."""
    rows = [{"belief": "A brand new belief with no evidence yet", "verdict": "no", "label": "No (H99)"}]
    with pytest.raises(ValueError, match="A brand new belief with no evidence yet"):
        attach_evidence(rows)


def test_every_translation_has_short_copy_without_banned_words():
    """The redesigned scoreboard shows title_short_id/result_short_id. Both
    must exist for every belief, and never carry an em dash or the word
    'campuran' (user feedback 2026-09-14/20)."""
    from pipeline.appdata.findings_translations import TRANSLATIONS

    for belief, entry in TRANSLATIONS.items():
        for key in ("title_short_id", "result_short_id"):
            text = entry[key]
            assert text, (belief, key)
            assert "\u2014" not in text, (belief, key)
            assert "campuran" not in text.lower(), (belief, key)
            assert len(text) <= 80, (belief, key, len(text))
