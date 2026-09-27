#!/usr/bin/env python3
"""
Guard against financial-advice language reaching the product.

CLAUDE.md's hard constraint: "No financial-advice language anywhere: UI
copy, README, commit messages, video script. This is an information tool.
It never recommends buying, selling, or holding." docs/PLAN.md §14 makes
this a required build gate, not a style preference.

Scans for imperative/recommendation phrasing in both Bahasa Indonesia and
English. Deliberately broad, same philosophy as check_no_secrets.py: false
positives are cheap (a human reviews each hit: some are legitimate, e.g.
a disclaimer sentence that names the very question it refuses to answer);
a missed real recommendation is not. A bare word like "beli"/"jual"/"buy"/
"sell" is NOT itself flagged: "diperjualbelikan" (tradable) and "beat
gold" style factual language would false-positive constantly: only
imperative/recommendation-shaped phrases around them are.

Usage:
    python scripts/check_no_advice_language.py <file> [<file> ...]
    python scripts/check_no_advice_language.py --dir frontend/src
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = [
    # Indonesian: direct recommendation / imperative framing
    re.compile(r"(?i)\bsebaiknya\b"),
    re.compile(r"(?i)\brekomendasi\b"),
    re.compile(r"(?i)\bdirekomendasikan\b"),
    re.compile(r"(?i)\bdisarankan\b"),
    re.compile(r"(?i)\bmenyarankan\b"),
    re.compile(r"(?i)\blayak (di)?beli\b"),
    re.compile(r"(?i)\bharus (membeli|menjual|beli|jual|menahan)\b"),
    re.compile(r"(?i)\bwaktu(nya)? (yang )?tepat (untuk )?(membeli|menjual|beli|jual|bertransaksi)\b"),
    re.compile(r"(?i)\bsaatnya (membeli|menjual|beli|jual)\b"),
    re.compile(r"(?i)\b(beli|jual) sekarang\b"),
    re.compile(r"(?i)\bpatut (dibeli|dijual|dimiliki)\b"),
    re.compile(r"(?i)\bhindari saham\b"),
    re.compile(r"(?i)\blebih baik (membeli|menjual|beli|jual|menahan)\b"),
    # The four alarm-style words below (a market-pressure state pill, an
    # avoidance directive, a danger word, and a caution phrase) must never
    # reach the product as an imperative; the Pasar/Kesimpulan state labels
    # use "tertekan" and "risiko aktif" instead. Added 2026-09-27, bare-word
    # and deliberately broad, like the rest of this file. This comment
    # deliberately doesn't spell the words out, in case this file's own
    # extension is ever added to a future scan. OJK's programme name built
    # on the first word is the one legitimate exception, masked out below
    # rather than narrowing the pattern.
    re.compile(r"(?i)\bwaspada\b"),
    re.compile(r"(?i)\bhindari\b"),
    re.compile(r"(?i)\bbahaya\b"),
    re.compile(r"(?i)\bhati[- ]?hati\b"),
    # English: direct recommendation / imperative framing
    re.compile(r"(?i)\byou should (buy|sell|hold)\b"),
    re.compile(r"(?i)\bwe recommend\b"),
    re.compile(r"(?i)\brecommended (buy|sell|hold)\b"),
    re.compile(r"(?i)\ba good (buy|time to buy|time to sell)\b"),
    re.compile(r"(?i)\bworth buying\b"),
    re.compile(r"(?i)\b(buy|sell) now\b"),
    re.compile(r"(?i)\bstrong buy\b"),
    re.compile(r"(?i)\bbetter to (buy|sell|hold)\b"),
]

# Legitimate uses of an otherwise-flagged word: OJK's own consumer-protection
# programme name, quoted verbatim in the product's tip-claims copy. Stripped
# out of the line before matching (not a whole-line skip) so any other,
# unrelated advice pattern on the same line still gets caught.
ALLOWLIST_PHRASES = [
    re.compile(r"(?i)waspada investasi"),
]

DEFAULT_EXTENSIONS = {".tsx", ".ts", ".md"}


def find_advice_language(text: str) -> list[tuple[int, str]]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        masked = line
        for allowed in ALLOWLIST_PHRASES:
            masked = allowed.sub("", masked)
        for pattern in PATTERNS:
            if pattern.search(masked):
                hits.append((lineno, line.strip()))
                break
    return hits


def iter_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file() and p.suffix in DEFAULT_EXTENSIONS and "node_modules" not in p.parts)
        elif path.is_file():
            files.append(path)
    return files


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("Usage: check_no_advice_language.py <file>... | --dir <dir>...")
        return 2

    if args[0] == "--dir":
        paths = [Path(p) for p in args[1:]]
    else:
        paths = [Path(p) for p in args]

    files = iter_files(paths)
    any_hits = False
    for file in files:
        text = file.read_text(errors="ignore")
        hits = find_advice_language(text)
        if hits:
            any_hits = True
            print(f"\n{file}:")
            for lineno, line in hits:
                print(f"  {lineno}: {line}")

    if any_hits:
        print("\ncheck_no_advice_language: possible advice-sounding language found above.")
        print("Review each hit: a disclaimer naming the question it refuses to answer")
        print("is fine; an actual recommendation is not. Rewrite or add context.")
        return 1

    print("check_no_advice_language: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
