import json

import pytest

from pipeline.appdata.fetch_sectors_closes import PAGE, fetch_closes


def _fake(total):
    calls = []

    def call(args):
        calls.append(args)
        off = args["offset"]
        rows = [{"symbol": f"S{i}.JK", "close": 100 + i} for i in range(off, min(off + PAGE, total))]
        return {"results": rows, "pagination": {"total_count": total, "has_next": off + PAGE < total}}

    return call, calls


def test_paginates_saves_and_does_not_rebill(tmp_path):
    path = tmp_path / "c.json"
    call, calls = _fake(65)
    assert fetch_closes(["2025-04-30"], path, call) == 3
    store = json.loads(path.read_text())
    assert store["2025-04-30"]["complete"] and store["2025-04-30"]["total_count"] == 65
    assert sum(len(p) for p in store["2025-04-30"]["pages"].values()) == 65
    call2, calls2 = _fake(65)
    assert fetch_closes(["2025-04-30"], path, call2) == 0 and calls2 == []


def test_resumes_after_interruption(tmp_path):
    path = tmp_path / "c.json"
    call, _ = _fake(95)
    with pytest.raises(RuntimeError):
        fetch_closes(["2025-04-30"], path, call, max_calls=2)
    call2, calls2 = _fake(95)
    assert fetch_closes(["2025-04-30"], path, call2) == 2
    assert [c["offset"] for c in calls2] == [60, 90]


def test_stops_on_runaway_page_count(tmp_path):
    call, _ = _fake(10_000)
    with pytest.raises(RuntimeError, match="pages"):
        fetch_closes(["2025-04-30"], tmp_path / "c.json", call, max_calls=1000)
