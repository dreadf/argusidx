import json

import pytest

from pipeline import sectors_mcp
from pipeline.sectors_mcp import SectorsMCP, SectorsMCPError, _parse_body


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setattr(sectors_mcp, "_api_key", lambda: "test-key")


class FakeServer:
    """Records posted messages and replies like an MCP server."""

    def __init__(self, tool_result=None):
        self.sent = []
        self.tool_result = tool_result or {
            "content": [{"type": "text", "text": json.dumps({"ok": True})}]
        }

    def __call__(self, payload, headers):
        self.sent.append((payload, headers))
        method = payload.get("method")
        if method == "initialize":
            return {"result": {"serverInfo": {"name": "sectors-mcp"}}}, {"mcp-session-id": "sess-1"}
        if method == "notifications/initialized":
            return {}, {}
        if method == "tools/list":
            return {"result": {"tools": [{"name": "fetch-foreign-flow"}]}}, {}
        if method == "tools/call":
            return {"result": self.tool_result}, {}
        raise AssertionError(method)


def make(tmp_path, server=None):
    server = server or FakeServer()
    return SectorsMCP(post=server, call_log=tmp_path / "log.jsonl"), server


def test_initialize_sends_bearer_and_keeps_session(tmp_path):
    client, server = make(tmp_path)
    client.initialize()
    first_headers = server.sent[0][1]
    assert first_headers["Authorization"] == "Bearer test-key"
    assert "User-Agent" in first_headers  # Cloudflare 1010 guard
    client.list_tools()
    assert server.sent[-1][1]["Mcp-Session-Id"] == "sess-1"


def test_list_tools_is_not_billed_and_needs_no_flag(tmp_path):
    client, _ = make(tmp_path)
    assert client.list_tools() == [{"name": "fetch-foreign-flow"}]
    assert not (tmp_path / "log.jsonl").exists()


def test_billed_call_refused_without_flag(tmp_path):
    client, server = make(tmp_path)
    with pytest.raises(SectorsMCPError, match="allow_billed"):
        client.call_tool("fetch-listing-performance", {"symbol": "GOTO"})
    assert server.sent == []  # nothing left the process


def test_billed_call_returns_json_and_logs(tmp_path):
    client, _ = make(tmp_path)
    out = client.call_tool("fetch-listing-performance", {"symbol": "GOTO"}, allow_billed=True)
    assert out == {"ok": True}
    line = json.loads((tmp_path / "log.jsonl").read_text().splitlines()[0])
    assert line["tool"] == "fetch-listing-performance"
    assert line["arguments"] == {"symbol": "GOTO"}
    assert line["is_error"] is False


def test_data_floor_blocks_before_sending(tmp_path):
    client, server = make(tmp_path)
    with pytest.raises(ValueError, match="data floor"):
        client.call_tool(
            "fetch-foreign-flow", {"symbol": "BBCA", "start": "2020-12-31"}, allow_billed=True
        )
    assert server.sent == []


def test_floor_does_not_apply_to_listing_performance(tmp_path):
    client, _ = make(tmp_path)
    client.call_tool(
        "fetch-listing-performance", {"symbol": "OLDCO", "start": "2005-06-01"}, allow_billed=True
    )


def test_tool_error_raises_and_is_logged(tmp_path):
    server = FakeServer(tool_result={"isError": True, "content": [{"type": "text", "text": "boom"}]})
    client, _ = make(tmp_path, server)
    with pytest.raises(SectorsMCPError, match="tool error"):
        client.call_tool("fetch-foreign-flow", {"symbol": "BBCA"}, allow_billed=True)
    assert json.loads((tmp_path / "log.jsonl").read_text())["is_error"] is True


def test_non_json_result_raises(tmp_path):
    server = FakeServer(tool_result={"content": [{"type": "text", "text": "not json"}]})
    client, _ = make(tmp_path, server)
    with pytest.raises(SectorsMCPError, match="not JSON"):
        client.call_tool("fetch-foreign-flow", {"symbol": "BBCA"}, allow_billed=True)


def test_jsonrpc_error_raises(tmp_path):
    def post(payload, headers):
        return {"error": {"code": -32601, "message": "nope"}}, {}

    client = SectorsMCP(post=post, call_log=tmp_path / "log.jsonl")
    with pytest.raises(SectorsMCPError, match="nope"):
        client.initialize()


def test_parse_body_json_and_sse():
    assert _parse_body('{"a": 1}', "application/json") == {"a": 1}
    sse = 'event: message\ndata: {"a": 2}\n\n'
    assert _parse_body(sse, "text/event-stream") == {"a": 2}
    with pytest.raises(SectorsMCPError):
        _parse_body("event: ping\n\n", "text/event-stream")
