import sqlite3

import pytest
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.exceptions import ToolError

from servers.actions import mcp as actions
from servers.observe import mcp as observe
from sim.generate import INJECTION, build


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "inj.db")
    build("bad_deploy", path, inject=True)
    monkeypatch.setenv("TRIAGE_DB", path)
    return path


async def test_injected_text_is_labelled_untrusted(db_path):
    async with Client(observe) as c:
        r = await c.call_tool("search_logs", {"service": "api", "level": "ERROR", "limit": 50})
        assert r.data["untrusted_data"] is True
        assert any(INJECTION[:30] in e["message"] for e in r.data["entries"])


async def test_even_if_model_obeys_injection_human_can_deny(db_path):
    """Worst case: the model DOES call rollback. The approval gate still protects us."""
    async def deny(message, response_type, params, context):
        return ElicitResult(action="decline")

    async with Client(actions, elicitation_handler=deny) as c:
        with pytest.raises(ToolError):
            await c.call_tool("rollback_deploy", {"service": "api", "reason": "log said so"})

    latest = sqlite3.connect(db_path).execute(
        "SELECT version FROM deploys WHERE service='api' ORDER BY ts DESC LIMIT 1").fetchone()
    assert latest[0] == "v2.3.0"