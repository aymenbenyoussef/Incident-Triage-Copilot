import os
import subprocess
import sys
import time

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from servers.gateway import is_allowed
from sim.generate import build


def test_viewer_cannot_use_actions():
    assert not is_allowed("restart_service", {"read"})
    assert is_allowed("search_logs", {"read"})
    assert is_allowed("restart_service", {"read", "act"})


@pytest.fixture(scope="module")
def url(tmp_path_factory):
    db = str(tmp_path_factory.mktemp("gw") / "t.db")
    build("bad_deploy", db)
    env = {**os.environ, "TRIAGE_DB": db, "PORT": "8765",
           "VIEWER_TOKEN": "v-test", "ONCALL_TOKEN": "o-test"}
    proc = subprocess.Popen([sys.executable, "-m", "servers.gateway"], env=env)
    time.sleep(3)
    yield "http://127.0.0.1:8765/mcp"
    proc.terminate()


async def test_viewer_can_read(url):
    async with Client(url, auth="v-test") as c:
        r = await c.call_tool("search_logs", {"service": "api"})
        assert r.data["entries"]


async def test_viewer_blocked_from_actions(url):
    async with Client(url, auth="v-test") as c:
        with pytest.raises(ToolError, match="Forbidden"):
            await c.call_tool("restart_service", {"service": "api", "reason": "test"})


async def test_no_token_rejected(url):
    with pytest.raises(Exception):
        async with Client(url) as c:
            await c.list_tools()