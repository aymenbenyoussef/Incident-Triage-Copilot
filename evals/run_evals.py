import asyncio
import os

from agent.agent import investigate
from sim.generate import SCENARIOS, build

VIEWER = os.getenv("VIEWER_TOKEN", "viewer-dev-token")
DB = os.getenv("TRIAGE_DB", "data/prod.db")
RUNS = 3

# A report is "correct" if it mentions ANY of these keywords (case-insensitive).
EXPECTED = {
    "bad_deploy": ["v2.3.0"],
    "memory_leak": ["memory leak", "outofmemory", "out of memory", "heap"],
    "db_pool_exhaustion": ["connection pool", "pool exhausted"],
    "upstream_timeout": ["payment", "upstream", "third-party"],
    "disk_full": ["disk", "no space"],
}

PROMPTS = {
    "bad_deploy": (
        "Investigate the API service. Call search_logs with "
        "service='api', level='ERROR', minutes=30, then get_metrics with "
        "service='api', metric='latency_ms', minutes=30, and finally "
        "list_recent_deploys with service='api'."
    ),
    "memory_leak": (
        "Investigate the API service. Call search_logs with "
        "service='api', level='ERROR', minutes=30, then get_metrics with "
        "service='api', metric='memory', minutes=30. Also check recent "
        "deploys with list_recent_deploys(service='api')."
    ),
    "db_pool_exhaustion": (
        "Investigate the database connection issue. Call search_logs with "
        "service='db', level='ERROR', minutes=30, then get_metrics with "
        "service='api', metric='latency_ms', minutes=30. Also check "
        "list_recent_deploys(service='api')."
    ),
    "upstream_timeout": (
        "Investigate the payment dependency. Call search_logs with "
        "service='api', level='ERROR', minutes=30, then search_logs with "
        "service='web', level='ERROR', minutes=30, and get_metrics with "
        "service='api', metric='latency_ms', minutes=30."
    ),
    "disk_full": (
        "Investigate database disk usage. Call search_logs with "
        "service='db', level='ERROR', minutes=30, then get_metrics with "
        "service='db', metric='disk_pct', minutes=30, and check "
        "list_recent_deploys(service='db')."
    ),
}


async def no_approval(message, response_type, params, context):
    from fastmcp.client.elicitation import ElicitResult
    return ElicitResult(action="decline")


async def main():
    lines = ["| Scenario | Correct | Avg tool calls |", "|---|---|---|"]
    total_ok = total = 0
    for scenario in SCENARIOS:
        ok, calls = 0, []
        for _ in range(RUNS):
            build(scenario, DB)
            r = await investigate(PROMPTS[scenario],
                                  token=VIEWER, handler=no_approval)
            text = r["report"].lower()
            ok += any(k in text for k in EXPECTED[scenario])
            calls.append(r["tool_calls"])
        total_ok += ok
        total += RUNS
        lines.append(f"| {scenario} | {ok}/{RUNS} | {sum(calls)/len(calls):.1f} |")
    lines.append(f"| **Overall** | **{100*total_ok/total:.0f}%** | |")
    table = "\n".join(lines)
    print(table)
    with open("evals/results.md", "w") as f:
        f.write(table + "\n")


if __name__ == "__main__":
    asyncio.run(main())