import asyncio
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult

async def approve(message, response_type, params, context):
    print(message)
    answer = input("Approve? [y/N] ").strip().lower()

    if answer == "y":
        return ElicitResult(action="accept", content={"value": True})

    return ElicitResult(action="decline")

async def main():
    async with Client(
        "http://127.0.0.1:8000/mcp",
        auth="oncall-dev-token",
        elicitation_handler=approve,
    ) as client:
        result = await client.call_tool(
            "restart_service",
            {
                "service": "api",
                "reason": "Testing the simulated restart approval flow",
            },
        )
        print(result.data)

asyncio.run(main())