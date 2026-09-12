"""
Regression tests for check_no_secrets.py -- each case here corresponds to
a real false negative found and fixed on 2026-09-07 (see the git history
around that date, or ask the project's assistant conversation log). All
"secret" values below are fabricated, not real credentials.

Run:
    python -m pytest scripts/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_no_secrets import find_secrets  # noqa: E402

FAKE = "aB3xK9mN2pQ7rT5vW8yZ1cE4gH6jL0nP"  # fabricated, not a real credential


def as_diff(line: str) -> str:
    """Wrap a line as a git-diff-style addition, matching how find_secrets is fed."""
    return f"+{line}"


def test_catches_plain_env_assignment():
    assert find_secrets(as_diff(f"SECTORS_API_KEY={FAKE}"))


def test_catches_json_quoted_key():
    assert find_secrets(as_diff(f'"api_key": "{FAKE}"'))


def test_catches_python_subscript_assignment():
    assert find_secrets(as_diff(f"os.environ['SECTORS_API_KEY'] = '{FAKE}'"))


def test_catches_authorization_header_bare():
    assert find_secrets(as_diff(f"Authorization: {FAKE}"))


def test_catches_authorization_header_dict():
    assert find_secrets(as_diff(f'headers = {{"Authorization": "{FAKE}"}}'))


def test_allow_word_elsewhere_on_line_no_longer_hides_a_real_key():
    """Regression: ALLOW used to be checked against the whole line, so a
    trailing '# example config' comment hid a real key earlier on the
    same line. It must now be checked against the matched value only."""
    assert find_secrets(as_diff(f"SECTORS_API_KEY={FAKE}  # from api.example.com"))


def test_allow_word_near_key_still_hides_a_real_key():
    """Same as above but with '<real key>' appended after the match --
    still must be caught, since the placeholder text isn't part of the
    captured credential value."""
    assert find_secrets(as_diff(f'API_KEY = "{FAKE}"   # TODO replace with <real key>'))


def test_genuine_placeholder_is_allowed():
    """Regression: the original 'your_key_here' (13 chars) never reached the
    ALLOW/_is_placeholder logic at all -- PATTERNS[0] requires >=16 chars, so
    the test passed only because nothing matched, not because the
    placeholder path was exercised. Long enough to match, short enough after
    stripping ALLOW words that _is_placeholder still says "not a real key"."""
    assert not find_secrets(as_diff("SECTORS_API_KEY=your_key_goes_here"))


def test_genuine_placeholder_example_value_is_allowed():
    assert not find_secrets(as_diff("SECTORS_API_KEY=example_placeholder_value"))


def test_non_credential_line_is_clean():
    assert not find_secrets(as_diff("print('hello world')"))


def test_authorization_bearer_header_is_caught():
    """Regression: found by /code-review 2026-09-12. The scheme word
    "Bearer" between the ':' and the actual token previously made the
    whole pattern fail to match at all -- "Bearer" itself would attempt
    to satisfy the value capture, fail the 16-char minimum, and the
    pattern gave up instead of looking past it for the real token."""
    assert find_secrets(as_diff(f"Authorization: Bearer {FAKE}"))


def test_second_match_of_same_pattern_on_one_line_is_still_caught():
    """Regression: found by /code-review 2026-09-12. find_secrets used
    pattern.search() (first match only) per pattern per line -- if a
    line's FIRST credential-shaped value under a pattern was a
    placeholder, the old code moved to the next pattern entirely,
    never inspecting a second, real value matched by that same pattern
    later on the same line."""
    assert find_secrets(as_diff(f"API_KEY=your_key_here API_KEY={FAKE}"))


def test_real_key_adjacent_to_allow_word_is_still_caught():
    """Regression: found by /code-review 2026-09-07. The value's own
    character class lets a real key and a trailing placeholder word merge
    with no separator into one blob (e.g. KEY_example_suffix), and a bare
    ALLOW.search() over that whole blob wrongly treated it as a
    placeholder. Fixed by requiring what's left after removing every
    ALLOW match to be short -- a real key leaves a long remainder."""
    assert find_secrets(as_diff(f"SECTORS_API_KEY={FAKE}_example_suffix_not_a_placeholder"))
    assert find_secrets(
        as_diff(f"curl https://api.sectors.app/v2/x?api_key={FAKE}-example_test")
    )
