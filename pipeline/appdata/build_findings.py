"""Build data/app/findings.json from docs/FINDINGS.md's scoreboard
table.

Parses the live markdown table directly rather than hand-transcribing a
copy - the table's content is genuinely curated research conclusions (not
derivable from raw data), owned collaboratively, and already changed twice
in one session (H4, H11 added). Parsing the source directly means this
never silently drifts from it.

Every row also gets a plain-Bahasa translation from
findings_translations.py - the source table's own labels are research
shorthand ("(H10, new 2026-09-12)"), not beginner-facing copy (user
feedback, 2026-09-13). A belief with no translation entry fails the
build loudly rather than shipping untranslated jargon.

Every row also gets its evidence (hypothesis id, real sample size,
period tested, the one limit that matters most) from
findings_evidence.py - the scoreboard previously carried only a
belief/verdict/label, with no way for a reader to see what was actually
tested (BACKLOG.md's 2026-09-19 audit). Same fail-loudly discipline as
translations: a belief with no evidence entry stops the build.

Run: .venv/bin/python -m pipeline.appdata.build_findings
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, REPO_ROOT
from pipeline.appdata.findings_evidence import EVIDENCE
from pipeline.appdata.findings_translations import TRANSLATIONS

FINDINGS_DOC = REPO_ROOT / "docs" / "FINDINGS.md"

TABLE_HEADER = "| What people believe | | Verdict |"

VERDICT_MAP = {
    "✓": "yes",
    "✗": "no",
    "~": "mixed_or_inconclusive",
}


def _clean_cell(cell: str) -> str:
    return cell.strip().replace("**", "")


def parse_scoreboard(markdown_text: str) -> list[dict]:
    lines = markdown_text.splitlines()
    try:
        header_idx = next(i for i, line in enumerate(lines) if line.strip() == TABLE_HEADER)
    except StopIteration:
        raise ValueError(f"Honesty scoreboard table header not found in {FINDINGS_DOC}")

    # header_idx+1 is the `|---|---|---|` separator; rows start after that.
    rows = []
    for line in lines[header_idx + 2:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break  # table ended
        cells = [c for c in stripped.split("|")][1:-1]  # drop empty ends from leading/trailing "|"
        if len(cells) != 3:
            continue
        belief, verdict_symbol, label = (_clean_cell(c) for c in cells)
        verdict_symbol_clean = verdict_symbol.strip()
        verdict = VERDICT_MAP.get(verdict_symbol_clean)
        if verdict is None:
            raise ValueError(f"Unrecognized verdict symbol {verdict_symbol_clean!r} in row: {belief!r}")
        rows.append({"belief": belief, "verdict": verdict, "label": label})
    return rows


def attach_translations(scoreboard: list[dict]) -> list[dict]:
    translated = []
    missing = []
    for row in scoreboard:
        translation = TRANSLATIONS.get(row["belief"])
        if translation is None:
            missing.append(row["belief"])
            continue
        translated.append({**row, **translation})
    if missing:
        raise ValueError(
            "Missing plain-Bahasa translation in findings_translations.py for: "
            + "; ".join(repr(b) for b in missing)
        )
    return translated


def attach_evidence(scoreboard: list[dict]) -> list[dict]:
    with_evidence = []
    missing = []
    for row in scoreboard:
        evidence = EVIDENCE.get(row["belief"])
        if evidence is None:
            missing.append(row["belief"])
            continue
        with_evidence.append({**row, "evidence": evidence})
    if missing:
        raise ValueError(
            "Missing evidence entry in findings_evidence.py for: "
            + "; ".join(repr(b) for b in missing)
        )
    return with_evidence


def main() -> None:
    markdown_text = FINDINGS_DOC.read_text()
    scoreboard = attach_evidence(attach_translations(parse_scoreboard(markdown_text)))

    output = {
        "source_file": "docs/FINDINGS.md",
        "scoreboard": scoreboard,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "findings.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {FINDINGS_DOC}")
    print(f"{len(scoreboard)} rows")
    for row in scoreboard:
        print(f"  [{row['verdict']:22s}] {row['belief']}")


if __name__ == "__main__":
    main()
