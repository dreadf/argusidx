#!/usr/bin/env python3
"""
Guard against the em dash (U+2014, "—") reaching GitHub or the app.

Style rule from the project owner (2026-09-27): no em dash anywhere in the
repository or the shipped product. Scans every git-tracked file, skipping
binary/generated formats by extension.

This is a style gate, not a correctness one: a hit is always a real em
dash, so unlike check_no_advice_language.py there is nothing to judge by
hand. Fix by rewriting, then re-run.

The default (no-args) scan is an exclude list, not an allowlist: an
extensionless or unusually-named tracked file (e.g. `.env.example`) is
scanned unless its extension is explicitly known-binary. An allowlist here
would silently skip exactly the kind of small config file most likely to
carry a stray em dash unnoticed.

Usage:
    python scripts/check_no_em_dash.py                # scans `git ls-files`
    python scripts/check_no_em_dash.py <file> [<file> ...]
    python scripts/check_no_em_dash.py --dir some/dir  # walk a directory instead of git
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EM_DASH = "—"

# Extensions this rule skips: binary formats, and generated/vendored output
# an em dash inside would not mean anything (a font, an image, a lockfile).
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".zip", ".gz", ".tar", ".jsonl",
    ".lock",
}

# Paths this rule doesn't apply to: generated/vendored output and lockfiles,
# which this project doesn't hand-edit and wouldn't want reformatted.
SKIP_PATH_PARTS = {"node_modules", ".next"}
SKIP_NAMES = {"package-lock.json"}


def find_em_dashes(text: str) -> list[tuple[int, str]]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if EM_DASH in line:
            hits.append((lineno, line.strip()))
    return hits


def _skippable(p: Path) -> bool:
    return p.suffix in BINARY_EXTENSIONS or p.name in SKIP_NAMES or any(part in SKIP_PATH_PARTS for part in p.parts)


def git_tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    paths = [Path(line) for line in out.stdout.splitlines()]
    return [p for p in paths if not _skippable(p)]


def iter_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file() and not _skippable(p))
        elif path.is_file():
            files.append(path)
    return files


def main() -> int:
    args = sys.argv[1:]
    if not args:
        paths = git_tracked_files()
    elif args[0] == "--dir":
        paths = iter_files([Path(p) for p in args[1:]])
    else:
        paths = iter_files([Path(p) for p in args])

    any_hits = False
    for file in paths:
        try:
            text = file.read_text(errors="ignore")
        except (FileNotFoundError, IsADirectoryError):
            continue
        hits = find_em_dashes(text)
        if hits:
            any_hits = True
            print(f"\n{file}:")
            for lineno, line in hits:
                print(f"  {lineno}: {line}")

    if any_hits:
        print("\ncheck_no_em_dash: em dash (U+2014) found above. Rewrite with a comma,")
        print("colon, semicolon or parentheses; no em dash anywhere in this repo.")
        return 1

    print("check_no_em_dash: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
