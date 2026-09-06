#!/usr/bin/env python3
"""
Cheap guard against committing a live API key or similar secret.

Scans the staged diff (or, for testing, a file/stdin) for lines that look
like a credential assignment. Not a substitute for real secret-scanning —
just insurance against repeating the exact mistake this project already
made once outside the repo (see docs/PLAN.md 10, RULES.md housekeeping):
a key typed somewhere it shouldn't have been.

Usage:
    python scripts/check_no_secrets.py            # scans `git diff --cached`
    python scripts/check_no_secrets.py some_file   # scans a file instead
    git diff --cached | python scripts/check_no_secrets.py --stdin

Wire up as a local pre-commit hook (not committed to the repo, since
.git/hooks/ isn't tracked):
    ln -s ../../scripts/check_no_secrets.py .git/hooks/pre-commit
"""
from __future__ import annotations

import re
import subprocess
import sys

# Deliberately broad: a credential-shaped assignment (KEY/TOKEN/SECRET/etc.
# followed by a long opaque string), or a handful of well-known vendor
# prefixes. False positives are cheap; a missed key is not.
PATTERNS = [
    re.compile(
        r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"]?"
        r"[A-Za-z0-9_\-/+]{16,}['\"]?"
    ),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI/Anthropic-style secret key
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub personal access token
]

# Lines that are clearly templates/placeholders, not real secrets.
ALLOW = re.compile(r"(?i)(your[_-]?key|example|placeholder|xxx+|<[^>]+>|^\s*$)")


def find_secrets(text: str) -> list[str]:
    hits = []
    for line in text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        if ALLOW.search(content):
            continue
        for pattern in PATTERNS:
            if pattern.search(content):
                hits.append(content.strip())
                break
    return hits


def main() -> int:
    if "--stdin" in sys.argv:
        text = sys.stdin.read()
    elif len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            text = f.read()
        # Treat every line as "added" when scanning a plain file directly.
        text = "\n".join(f"+{line}" for line in text.splitlines())
    else:
        result = subprocess.run(
            ["git", "diff", "--cached", "-U0"],
            capture_output=True,
            text=True,
            check=True,
        )
        text = result.stdout

    hits = find_secrets(text)
    if hits:
        print("check_no_secrets: possible credential(s) in staged changes:\n")
        for hit in hits:
            print(f"  {hit}")
        print("\nRemove it, or add it to ALLOW in scripts/check_no_secrets.py "
              "if this is a genuine false positive.")
        return 1

    print("check_no_secrets: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
