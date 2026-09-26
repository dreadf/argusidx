"""
Sectors MCP client -- a plain program speaking MCP over streamable HTTP, no AI.

The build pipeline uses this to fetch Sectors data through the same tools
an AI agent would call (`fetch-foreign-flow`, `fetch-listing-performance`,
...). `pipeline/sectors_client.py` is the REST twin; both hit the same
backend and bill the same credits.

Auth: `Authorization: Bearer <key>` here. The REST API wants the raw key
with no "Bearer" -- easy to reverse (docs/PLAN.md 8.1).

Standing project rule (CLAUDE.md): no Sectors call without stating its
cost and getting explicit approval first. `initialize` and `tools/list`
are not billed data calls; `call_tool` is, so it requires
`allow_billed=True` and appends every call to a JSONL call log that the
credit ledger entry is written from.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable

from pipeline.guards import assert_within_data_floor
from pipeline.sectors_client import _api_key

MCP_URL = "https://sectors-mcp.supertype.ai/mcp"
PROTOCOL_VERSION = "2025-03-26"
RETRIES = 3
RETRY_SLEEP = 1.0
CALL_LOG = Path(__file__).resolve().parent.parent / "data" / "mcp_call_log.jsonl"

# Tools backed by per-stock daily endpoints, which return empty arrays
# (still billed) before the 2021-01-01 floor. Date-like args are checked.
FLOORED_TOOLS = frozenset({"fetch-daily-price", "fetch-foreign-flow"})
FLOORED_ARGS = ("start", "date")

PostFn = Callable[[dict, dict], tuple[dict, dict]]


class SectorsMCPError(Exception):
    pass


def _parse_body(raw: str, content_type: str) -> dict:
    """Decode a JSON body, or the last `data:` event of an SSE stream."""
    if "text/event-stream" in content_type:
        events = [
            line[len("data:") :].strip()
            for line in raw.splitlines()
            if line.startswith("data:")
        ]
        if not events:
            raise SectorsMCPError("empty event stream from MCP server")
        return json.loads(events[-1])
    return json.loads(raw)


def _http_post(payload: dict, headers: dict) -> tuple[dict, dict]:
    """POST one JSON-RPC message. Returns (parsed body or {}, response headers)."""
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(
            MCP_URL,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                content_type = resp.headers.get("Content-Type", "")
                response_headers = {k.lower(): v for k, v in resp.headers.items()}
                body = _parse_body(raw, content_type) if raw.strip() else {}
                return body, response_headers
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < RETRIES - 1:
                last_error = e
                time.sleep(RETRY_SLEEP * (attempt + 1))
                continue
            raise SectorsMCPError(f"HTTP {e.code} from MCP server") from e
        except urllib.error.URLError as e:
            last_error = e
            time.sleep(RETRY_SLEEP * (attempt + 1))
    raise SectorsMCPError(f"MCP server unreachable: {last_error}")


class SectorsMCP:
    def __init__(self, post: PostFn | None = None, call_log: Path | None = None):
        self._post = post or _http_post
        self._call_log = call_log if call_log is not None else CALL_LOG
        self._session_id: str | None = None
        self._next_id = 0
        self._initialized = False

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            # Cloudflare returns error 1010 for urllib's default User-Agent.
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {_api_key()}",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params
        body, response_headers = self._post(payload, self._headers())
        session = response_headers.get("mcp-session-id")
        if session:
            self._session_id = session
        if "error" in body:
            raise SectorsMCPError(f"{method}: {body['error']}")
        return body.get("result", {})

    def initialize(self) -> dict:
        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "argusidx-pipeline", "version": "1.0"},
            },
        )
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            self._headers(),
        )
        self._initialized = True
        return result

    def list_tools(self) -> list[dict]:
        """Tool schemas. Not a billed data call."""
        if not self._initialized:
            self.initialize()
        return self._request("tools/list", {}).get("tools", [])

    def call_tool(
        self, name: str, arguments: dict, *, allow_billed: bool = False
    ) -> dict:
        """Call one Sectors tool. Billed; the caller must have approval.

        Returns the parsed JSON payload of the tool result (the MCP text
        content is expected to hold JSON); anything else raises.
        """
        if not allow_billed:
            raise SectorsMCPError(
                f"{name}: billed call refused without allow_billed=True "
                "(state the cost and get approval first, CLAUDE.md)"
            )
        if name in FLOORED_TOOLS:
            for arg in FLOORED_ARGS:
                value = arguments.get(arg)
                if isinstance(value, str):
                    assert_within_data_floor(date.fromisoformat(value))
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        self._log_call(name, arguments, bool(result.get("isError")))
        if result.get("isError"):
            raise SectorsMCPError(f"{name}: tool error: {result.get('content')}")
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        if not texts:
            raise SectorsMCPError(f"{name}: no text content in tool result")
        try:
            return json.loads(texts[0])
        except json.JSONDecodeError as e:
            raise SectorsMCPError(f"{name}: tool result is not JSON: {texts[0][:200]}") from e

    def _log_call(self, name: str, arguments: dict, is_error: bool) -> None:
        self._call_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": name,
            "arguments": arguments,
            "is_error": is_error,
        }
        with self._call_log.open("a") as f:
            f.write(json.dumps(entry) + "\n")
