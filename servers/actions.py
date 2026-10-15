import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from pydantic import Field

Service = Literal["web", "api", "db"]

mcp = FastMCP(
    name="Actions",
    instructions="Risky actions. Every call requires explicit human approval.",
    mask_error_details=True,
)


def _db() -> str:
    return os.getenv("TRIAGE_DB", "data/prod.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _actor() -> str:
    token = get_access_token()
    return token.client_id if token else "local"


def _audit(actor: str, tool: str, args: dict, outcome: str) -> None:
    conn = sqlite3.connect(_db())
    conn.execute("INSERT INTO audit VALUES (?,?,?,?,?)",
                 (_now(), actor, tool, json.dumps(args), outcome))
    conn.commit()
    conn.close()


async def _require_approval(ctx: Context, tool: str, args: dict, summary: str) -> str:
    actor = _actor()
    result = await ctx.elicit(f"{summary}\nApprove?", response_type=bool)
    approved = result.action == "accept" and bool(result.data)
    _audit(actor, tool, args, "approved" if approved else "denied")
    if not approved:
        raise ToolError("Denied: a human did not approve this action.")
    return actor


@mcp.tool(annotations={"destructiveHint": True})
async def restart_service(
    service: Service,
    reason: str = Field(max_length=200, description="Why the restart is needed"),
    ctx: Context = None,
) -> str:
    """Restart a service (simulated). Requires human approval."""
    args = {"service": service, "reason": reason}
    actor = await _require_approval(ctx, "restart_service", args,
                                    f"Restart '{service}'? Reason: {reason}")
    conn = sqlite3.connect(_db())
    conn.execute("INSERT INTO logs VALUES (?,?,?,?)",
                 (_now(), service, "INFO", f"service restarted by {actor} (simulated)"))
    conn.commit()
    conn.close()
    return f"{service} restarted (simulated)."


@mcp.tool(annotations={"destructiveHint": True})
async def rollback_deploy(
    service: Service,
    reason: str = Field(max_length=200),
    ctx: Context = None,
) -> str:
    """Roll a service back to its previous version (simulated). Requires human approval."""
    conn = sqlite3.connect(_db())
    rows = conn.execute(
        "SELECT version FROM deploys WHERE service = ? ORDER BY ts DESC LIMIT 2", (service,)
    ).fetchall()
    conn.close()
    if len(rows) < 2:
        raise ToolError("No previous version to roll back to.")
    current, previous = rows[0][0], rows[1][0]

    args = {"service": service, "reason": reason, "from": current, "to": previous}
    actor = await _require_approval(ctx, "rollback_deploy", args,
                                    f"Roll back '{service}' from {current} to {previous}? Reason: {reason}")
    conn = sqlite3.connect(_db())
    conn.execute("INSERT INTO deploys VALUES (?,?,?,?)", (_now(), service, previous, f"rollback:{actor}"))
    conn.commit()
    conn.close()
    return f"{service} rolled back from {current} to {previous} (simulated)."


if __name__ == "__main__":
    mcp.run()