import logging
import os
import time

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

from servers.actions import mcp as actions
from servers.observe import mcp as observe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("gateway")

ACTION_TOOLS = {"restart_service", "rollback_deploy"}


def is_allowed(tool_name: str, scopes: set[str]) -> bool:
    """Pure function so it is trivial to unit-test."""
    return tool_name not in ACTION_TOOLS or "act" in scopes


class RoleCheck(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        token = get_access_token()
        scopes = set(token.scopes) if token else set()
        if not is_allowed(context.message.name, scopes):
            log.warning("DENIED %s for %s", context.message.name, token.client_id if token else "anon")
            raise ToolError("Forbidden: this action requires the 'oncall' role.")
        return await call_next(context)


class CallLogger(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        token = get_access_token()
        who = token.client_id if token else "anon"
        try:
            return await call_next(context)
        finally:
            ms = (time.perf_counter() - start) * 1000
            log.info("tool=%s actor=%s duration_ms=%.0f", context.message.name, who, ms)


# DEVELOPMENT ONLY: static tokens. Use OAuth/JWT in a real deployment.
auth = StaticTokenVerifier(tokens={
    os.getenv("VIEWER_TOKEN", "viewer-dev-token"): {"client_id": "viewer-bot", "scopes": ["read"]},
    os.getenv("ONCALL_TOKEN", "oncall-dev-token"): {"client_id": "oncall-alice", "scopes": ["read", "act"]},
})

gateway = FastMCP(name="Incident Gateway", auth=auth, mask_error_details=True)
gateway.add_middleware(RateLimitingMiddleware(max_requests_per_second=5, burst_capacity=10))
gateway.add_middleware(CallLogger())
gateway.add_middleware(RoleCheck())

gateway.mount(observe)
gateway.mount(actions)

if __name__ == "__main__":
    gateway.run(
        transport="http",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )