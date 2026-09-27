#!/usr/bin/env python3
"""
Cheap guard against committing a live API key or similar secret.

Scans the staged diff (or, for testing, a file/stdin) for lines that look
like a credential assignment. Not a substitute for real secret-scanning:
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
#
# The keyword can be followed by a closing quote/bracket before the
# `:`/`=` (['"\]\)\s]* below) so this catches JSON ("api_key": "...") and
# Python subscript assignment (os.environ['KEY'] = '...'), not just a
# bare shell-style KEY=value line. "authoriz" is included because it's
# this project's own auth style (sectors_client.py sends the raw key in
# an Authorization header) -- the one shape a real leak here would most
# likely take was, until this fix, the one shape this scanner couldn't see.
# Each pattern captures the credential value itself as `value`, so ALLOW
# (below) can be checked against just that value rather than the whole
# line -- checking the whole line let `example`/`xxx`/`<...>` ANYWHERE on
# a line (e.g. a trailing "# example config" comment) suppress detection
# of a real key earlier on the same line.
PATTERNS = [
    re.compile(
        r"(?i)(api[_-]?key|secret|token|password|passwd|authoriz\w*)"
        # Optional "Bearer " (or similar auth scheme word) between the
        # `:`/`=` and the actual credential -- an `Authorization: Bearer
        # <token>` header (this project's own Sectors-client style; see
        # pipeline/sectors_client.py) previously matched nothing here: the
        # scheme word "Bearer" itself would attempt to satisfy the value
        # capture, fail the {16,} length requirement, and the pattern gave
        # up rather than looking past it for the real token (found by
        # /code-review, 2026-09-12).
        r"['\"\]\)\s]*[:=]\s*['\"]?(?:[A-Za-z]+\s+)?(?P<value>[A-Za-z0-9_\-/+]{16,})['\"]?"
    ),
    re.compile(r"(?P<value>AKIA[0-9A-Z]{16})"),  # AWS access key id
    re.compile(r"(?P<value>sk-[A-Za-z0-9]{20,})"),  # OpenAI/Anthropic-style secret key
    re.compile(r"(?P<value>ghp_[A-Za-z0-9]{36})"),  # GitHub personal access token
]

# Values that are clearly templates/placeholders, not real secrets.
# Applied to the matched credential VALUE only (see above), not the line.
ALLOW = re.compile(r"(?i)(your[_-]?key|example|placeholder|xxx+)")

# After removing every ALLOW match from the value, anything left this long
# is assumed to still be a real secret. Catches a real key concatenated
# with a placeholder word with no separating space -- e.g.
# "aB3xK9...jL0nP_example_suffix" -- which `ALLOW.search(value)` alone
# would wrongly allow, because the value's own character class
# ([A-Za-z0-9_-/+]) lets a real key and a trailing placeholder word merge
# into one indistinguishable blob. A bare `search` for "example" anywhere
# in that blob can't tell "this whole value is a placeholder" apart from
# "a real secret happens to sit next to the word example".
MIN_REAL_SECRET_LEN = 12


def _is_placeholder(value: str) -> bool:
    remainder = ALLOW.sub("", value)
    remainder = re.sub(r"[_\-/]", "", remainder)  # separators left behind
    return len(remainder) < MIN_REAL_SECRET_LEN


def find_secrets(text: str) -> list[str]:
    hits = []
    for line in text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        for pattern in PATTERNS:
            # finditer, not search: a line can carry two credential-shaped
            # values matched by the SAME pattern (e.g. a placeholder
            # example followed by a real key later on the same line).
            # search() only ever sees the first one -- if that one turned
            # out to be a placeholder, the old code moved on to the next
            # PATTERN entirely, never inspecting the second match of this
            # same pattern (found by /code-review, 2026-09-12).
            if any(
                not _is_placeholder(m.groupdict().get("value") or m.group(0))
                for m in pattern.finditer(content)
            ):
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
