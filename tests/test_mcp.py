"""The MCP endpoint: the protocol handshake, each tool, and bad input. No keys, no network."""

import json

import pytest

pytest.importorskip("fastapi")
from test_web import client  # noqa: E402,F401  (the web app on a store with two real-shaped runs)


def rpc(client, method, params=None, rid=1):
    body = {"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})}
    return client.post("/mcp", json=body).json()


def call(client, name, **arguments):
    return rpc(client, "tools/call", {"name": name, "arguments": arguments})["result"]


def test_handshake_and_tool_list(client):
    init = rpc(client, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}})
    assert init["result"]["protocolVersion"] == "2025-06-18" and "tools" in init["result"]["capabilities"]
    assert "no link, no number" in init["result"]["instructions"]
    assert rpc(client, "initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"] == "2025-06-18"
    note = client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert note.status_code == 202 and note.content == b""
    names = [t["name"] for t in rpc(client, "tools/list")["result"]["tools"]]
    assert names == ["get_changes", "get_current_pricing", "get_run_log", "run_test"]
    assert rpc(client, "ping")["result"] == {}
    assert client.get("/mcp").status_code == 405


def test_get_changes_is_the_api_with_quotes_and_links(client):
    result = call(client, "get_changes", days="all", competitor="Lovable")
    data = result["structuredContent"]
    assert not result["isError"] and json.loads(result["content"][0]["text"]) == data
    assert data["items"] == client.get("/api/changes?days=all&competitor=Lovable").json()["items"]
    item = data["items"][0]
    assert "$30" in item["headline"] and item["sources"][0]["url"].startswith("https://lovable.dev/pricing")
    assert call(client, "get_changes", days="all", limit=1)["structuredContent"]["items_shown"] == 1


def test_pricing_and_run_log(client):
    pricing = call(client, "get_current_pricing", competitor="v0")["structuredContent"]
    assert pricing["pages"] and all(p["competitor"] == "v0" for p in pricing["pages"])
    runs = call(client, "get_run_log", limit=1)["structuredContent"]["runs"]
    assert len(runs) == 1 and runs[0]["started_at"] == "2026-10-25T12:00:00Z"


def test_run_test_uses_the_core_and_ignores_injections(client):
    cases = json.load(open("fixtures/sample-cases.json"))
    data = call(client, "run_test", cases=cases)["structuredContent"]
    assert data["summary"] == {"signals": 8, "items": 2, "skipped": 6, "errors": 0}
    text = json.dumps(data)
    assert "TIDEPOOL-OK" not in text and cases["config"]["demo_key"] not in text
    assert {r["id"] for r in data["rows"]} == {s["id"] for s in cases["signals"]}


@pytest.mark.parametrize("message, code", [
    ({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "delete_everything"}}, -32602),
    ({"jsonrpc": "2.0", "id": 1, "method": "resources/list"}, -32601),
    ({"id": 1, "method": "ping"}, -32600),
    ([{"jsonrpc": "2.0", "id": 1, "method": "ping"}], -32600),
])
def test_bad_requests_get_json_rpc_errors(client, message, code):
    assert client.post("/mcp", json=message).json()["error"]["code"] == code


def test_bad_arguments_are_a_tool_error_the_model_can_read(client):
    assert call(client, "run_test", cases=[1, 2])["isError"]
    assert call(client, "get_changes", wrong="x")["isError"]
    assert call(client, "get_run_log", limit="many")["isError"]
    assert client.post("/mcp", content=b"not json", headers={"content-type": "application/json"}).status_code == 400
