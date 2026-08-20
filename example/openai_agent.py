import asyncio
import json
import re
from typing import Any

from mcp import Client
from openai import AsyncOpenAI

OPENAI_API_KEY = ""
MODEL = "gpt-5.4-mini"
MCP_URL = "http://127.0.0.1:8001/mcp"
TARGET_MCP_TOOL = "users.get_user_name_by_email"
USER_EMAIL = "alice@example.com"

AGENT_INSTRUCTIONS = """
You are testing a local Django MCP server.
You must call the provided user lookup tool with the email from the user request.
Never invent a name and never answer from prior knowledge.
After the tool returns, answer with the user's name. If found is false, say that no user was found.
""".strip()


def openai_tool_name(mcp_tool_name: str) -> str:
    """Convert an MCP tool name to the character set accepted by OpenAI tools."""
    return re.sub(r"[^a-zA-Z0-9_-]", "__", mcp_tool_name)[:64]


def serialize_tool_result(result: Any) -> str:
    payload = result.structured_content
    if payload is None:
        payload = [block.model_dump(mode="json", by_alias=True) for block in result.content]
    return json.dumps(
        {"is_error": result.is_error, "result": payload},
        ensure_ascii=False,
        default=str,
    )


async def main() -> None:
    if not OPENAI_API_KEY:
        raise SystemExit("Set OPENAI_API_KEY at the top of openai_agent.py first.")

    openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async with Client(MCP_URL) as mcp_client:
        available_tools = await mcp_client.list_tools()
        target = next(
            (tool for tool in available_tools.tools if tool.name == TARGET_MCP_TOOL),
            None,
        )
        if target is None:
            raise RuntimeError(f"MCP tool is not available: {TARGET_MCP_TOOL}")

        alias = openai_tool_name(target.name)
        tools = [
            {
                "type": "function",
                "name": alias,
                "description": target.description or "",
                "parameters": target.input_schema,
                "strict": False,
            }
        ]

        response = await openai.responses.create(
            model=MODEL,
            instructions=AGENT_INSTRUCTIONS,
            input=f"Find the user name for email {USER_EMAIL}.",
            tools=tools,
            tool_choice="required",
        )

        for _ in range(5):
            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                print(response.output_text)
                return

            tool_outputs = []
            for tool_call in tool_calls:
                if tool_call.name != alias:
                    raise RuntimeError(f"Unexpected OpenAI tool call: {tool_call.name}")
                arguments = json.loads(tool_call.arguments)
                result = await mcp_client.call_tool(TARGET_MCP_TOOL, arguments)
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": serialize_tool_result(result),
                    }
                )

            response = await openai.responses.create(
                model=MODEL,
                instructions=AGENT_INSTRUCTIONS,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools,
                tool_choice="auto",
            )

    raise RuntimeError("The agent exceeded the maximum number of tool-call rounds.")


if __name__ == "__main__":
    asyncio.run(main())
