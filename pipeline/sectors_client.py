"""
Minimal Sectors API v2 client.

Not under pipeline/dev/ -- Sectors is the core, required data source
(RULES.md), unlike the Yahoo dev-only fetcher, so this may eventually be
reused by the shipped app once a backend exists (docs/PLAN.md 8.1-8.2).

Only what Phase 0 needs today. No speculative endpoint coverage.

Auth: raw key in the `Authorization` header, no "Bearer" prefix -- the
MCP server wants Bearer, the REST API does not (docs/PLAN.md 8.1).

Standing project rule (docs/PLAN.md 3.2): no Sectors call without
stating its cost and getting explicit go-ahead first. This module makes
calls possible; it does not decide when to make one.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

BASE_URL = "https://api.sectors.app/v2"
RETRIES = 3
RETRY_SLEEP = 1.0


class SectorsAPIError(Exception):
    pass


def _load_dotenv(path: Path) -> None:
    """Minimal `.env` loader: one KEY=value per line.

    Handles the variations that previously produced a silently wrong key
    -- each of these used to yield a broken Authorization header with no
    hint at the cause beyond a generic Cloudflare 403 (docs/credit_ledger.md
    already notes one mis-sourced-.env incident):
      - a leading `export ` prefix (shell-style .env files)
      - matching single or double quotes around the value
      - a trailing ` # inline comment`
    Does not override a value already set in the real environment.
    """
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith(('"', "'")):
            # Find the MATCHING closing quote rather than requiring the
            # whole value to end with one -- a quoted value followed by a
            # trailing ` # comment` (e.g. `KEY="realkey" # from portal`)
            # previously satisfied neither the old startswith/endswith
            # check nor the comment-stripping branch below, leaving the
            # literal quote characters embedded in the parsed key (found
            # by /code-review, 2026-09-12). Anything after the closing
            # quote (a comment, trailing whitespace) is simply discarded.
            quote = value[0]
            end = value.find(quote, 1)
            value = value[1:end] if end != -1 else value[1:]
        else:
            # Strip a trailing ` # comment` -- only outside quotes, so a
            # legitimately quoted value containing "#" is left alone.
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        if key:
            os.environ.setdefault(key, value)


def _api_key() -> str:
    _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    key = os.environ.get("SECTORS_API_KEY")
    if not key:
        raise SectorsAPIError(
            "SECTORS_API_KEY is not set. Copy .env.example to .env and fill "
            "it in with your Sectors API key."
        )
    return key


def get(path: str, params: dict[str, str] | None = None) -> dict:
    """GET a Sectors v2 endpoint and return the parsed JSON body.

    Retries with backoff on 429/5xx (free, per docs/PLAN.md 8.4's
    two-layer fallback rule). 400/401/403 are free but mean something is
    wrong with the request itself, so they raise immediately rather than
    retrying.

    CAUTION -- not fully idempotent against the credit ledger: docs/PLAN.md
    8.4's "free" rule is about the error response itself, not about
    whether Sectors already ran and billed the query before the 5xx was
    generated (e.g. a proxy timeout after the backend succeeded). A retry
    in that situation bills a second credit for one logical call. Harmless
    for cheap, low-frequency calls (Phase 0/1); worth checking the ledger
    against the portal after any paginate()-driven sweep, where the call
    count is much higher.
    """
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    # Cloudflare (fronting this API) returns error 1010 for urllib's default
    # User-Agent -- a browser-like one is required, same trap already hit
    # fetching the public schema and in pipeline/dev/fetch_yahoo_prices.py.
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": _api_key(),
            "User-Agent": "Mozilla/5.0",
        },
    )

    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < RETRIES - 1:
                time.sleep(RETRY_SLEEP * (attempt + 1))
                last_error = e
                continue
            raise SectorsAPIError(f"{e.code} {e.reason} for {url}") from e
        except urllib.error.URLError as e:
            last_error = e
            time.sleep(RETRY_SLEEP * (attempt + 1))

    raise SectorsAPIError(f"request failed after {RETRIES} attempts: {last_error}")


def paginate(
    path: str,
    params: dict[str, str],
    page_size: int = 200,
    on_page: Callable[[list[dict]], None] | None = None,
    start_offset: int = 0,
) -> list[dict]:
    """GET every page of a `/v2/companies/`-style paginated endpoint.

    Terminates on the response's own `has_next` / `next_offset` fields
    (confirmed present in the Phase 0 response, docs/PLAN.md 3.1's
    "persist every pull" rule already captured this shape in
    data/raw/phase0_field_density_2026-09-06.json) rather than assuming
    a fixed page count from the universe size.

    Each page is a separately billed call -- this makes exactly as many
    calls as pages exist, no more, no fewer. Caller is responsible for
    having already approved the expected page count and cost.

    `on_page`, if given, is called with each page's `results` list right
    after it's fetched -- e.g. `lambda page: f.write(...)` to persist
    incrementally to disk. `start_offset`, if given, resumes from that
    offset instead of 0 -- pair the two to make a genuinely resumable
    pull: save each page as it arrives, and on a re-run pass
    `start_offset=<rows already saved>` so already-billed pages are
    never re-fetched (and re-billed). Note `on_page` ALONE only prevents
    DATA LOSS on a crash, not RE-BILLING on retry -- a real gap found by
    /code-review, 2026-09-13: `on_page` shipped first (in response to a
    47-page /v2/filings/ pull that billed 32 pages, hit a 429, and lost
    everything because nothing was saved until the end) but the naive
    retry still re-fetched from offset 0, re-billing those same 32
    pages. `start_offset` closes that gap for any FUTURE caller of this
    function directly (the incident itself used a one-off scratch
    script with manual pagination, not this function). Both parameters
    default to their prior behavior -- purely additive, no change to
    existing callers.

    The return value holds only the pages fetched in THIS call: with
    `start_offset > 0` it does not include rows saved by an earlier run.
    """
    all_results: list[dict] = []
    page_params = dict(params)
    page_params["limit"] = str(page_size)
    offset = start_offset
    while True:
        page_params["offset"] = str(offset)
        response = get(path, page_params)
        results = response.get("results", [])
        all_results.extend(results)
        if on_page is not None:
            on_page(results)
        pagination = response.get("pagination", {})
        if not pagination.get("has_next"):
            break
        next_offset = pagination.get("next_offset")
        if next_offset is None or next_offset <= offset:
            # Malformed pagination info -- stop rather than loop forever
            # or bill for a page we can't correctly address.
            raise SectorsAPIError(
                f"paginate: has_next=true but next_offset={next_offset!r} "
                f"did not advance past offset={offset}"
            )
        offset = next_offset
    return all_results
