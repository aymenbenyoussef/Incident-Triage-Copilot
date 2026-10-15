import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from servers.observe import mcp
from sim.generate import build


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    build("bad_deploy", path)
    monkeypatch.setenv("TRIAGE_DB", path)


async def test_search_logs_finds_errors():
    async with Client(mcp) as c:
        r = await c.call_tool("search_logs", {"service": "api", "level": "ERROR"})
        assert r.data["untrusted_data"] is True
        assert any("NullPointer" in e["message"] for e in r.data["entries"])


async def test_unknown_service_rejected():
    async with Client(mcp) as c:
        with pytest.raises(ToolError):
            await c.call_tool("search_logs", {"service": "mars"})


async def test_minutes_out_of_range_rejected():
    async with Client(mcp) as c:
        with pytest.raises(ToolError):
            await c.call_tool("search_logs", {"service": "api", "minutes": 9999})


async def test_deploy_history_shows_bad_version():
    async with Client(mcp) as c:
        r = await c.call_tool("list_recent_deploys", {"service": "api", "hours": 2})
        assert r.structured_content["result"][0]["version"] == "v2.3.0"


async def test_sql_injection_attempt_is_rejected():
    async with Client(mcp) as c:
        with pytest.raises(ToolError):
            await c.call_tool("search_logs", {"service": "api'; DROP TABLE logs;--"})


async def test_health_resource():
    async with Client(mcp) as c:
        res = await c.read_resource("service://api/health")
        assert "errors_last_10m" in res[0].text